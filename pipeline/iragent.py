from pathlib import Path
import shutil
import logging
from time import localtime, strftime
import cv2
import json
import random
from typing import Optional

from llm import GPT4, DepictQA
from . import prompts
from executor import executor, Tool
from utils.img_tree import ImgTree
from utils.logger import get_logger
from utils.misc import sorted_glob
from utils.custom_types import *


class IRAgent:
    """
    Args:
        input_path (Path): Path to the input image.
        output_dir (Path): Path to the output directory, in which a directory will be created.
        llm_config_path (Path, optional): Path to the config file of LLM. Defaults to Path("config.yml").
        evaluate_degradation_by (str, optional): The method of degradation evaluation, "depictqa" or "gpt4v". Defaults to "depictqa".#降级评估方式
        with_retrieval (bool, optional): Whether to schedule with retrieval. Defaults to True.
        schedule_experience_path (Path | None, optional): Path to the experience hub. Defaults to Path( "memory/schedule_experience.json").
        with_reflection (bool, optional): Whether to reflect on the results of tools. Defaults to True.
        reflect_by (str, optional): The method of reflection on results of tools, "depictqa" or "gpt4v". Defaults to "depictqa".
        with_rollback (bool, optional): Whether to roll back when failing in one subtask. Defaults to True.
        silent (bool, optional): Whether to suppress the console output. Defaults to False.
    """

    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        llm_config_path: Path = Path("config.yml"),
        evaluate_degradation_by: str = "depictqa",
        with_retrieval: bool = True,
        schedule_experience_path: Optional[Path] = Path(
            "memory/schedule_experience.json"
        ),
        with_reflection: bool = True,
        reflect_by: str = "depictqa",
        with_rollback: bool = True,
        silent: bool = False,
        manual_degradations: Optional[list] = None,
        # ========== 新增：交互式迭代相关参数 ==========
        interactive: bool = False,  # 是否启用交互模式
        max_iterations: int = 5,  # 最大迭代次数
        # ===========================================
    ) -> None:
        # paths
        self._prepare_dir(input_path, output_dir)
        # state
        self._init_state()
        # config
        self._config(
            evaluate_degradation_by,
            with_retrieval,
            with_reflection,
            reflect_by,
            with_rollback
        )
        # components
        self._create_components(llm_config_path, schedule_experience_path, silent)
        # constants
        self._set_constants()
        
        # ========== 新增：交互式迭代相关属性 ==========
        self.interactive = interactive
        self.max_iterations = max_iterations
        self.iteration_history = []  # 记录每次迭代的结果和反馈
        # ===========================================
        
        # store degradation types for record
        self.initial_evaluation = None
        self.manual_degradations = manual_degradations  # 保存用户指定的降质类型

    def _init_state(self) -> None:
        self.plan: list[Subtask] = []
        self.work_mem: dict = {
            "plan": {"initial": [], "adjusted": [
                # {
                #     "failed": [...] + [...],
                #     "new": [...] + [...]
                # }
            ]},
            "execution_path": {"subtasks": [], "tools": []},
            "n_invocations": 0,
            "tree": {
                "img_path": str(self.img_tree_dir / "0-img" / "input.png"),
                "best_descendant": None,
                "children": {
                    # `subtask1`: {
                    #     "best_tool": ...,
                    #     "tools": {
                    #         `tool1`: {
                    #             "degradation": ...,
                    #             "severity": ...,
                    #             "img_path": ...,
                    #             "best_descendant": ...,
                    #             "children": {...}
                    #         },
                    #         ...
                    #     }
                    # }
                },
            },
        }
        self.cur_node = self.work_mem["tree"]

    def _config(
        self,
        evaluate_degradation_by: str,
        with_retrieval: bool,
        with_reflection: bool,
        reflect_by: str,
        with_rollback: bool
    ) -> None:
        assert evaluate_degradation_by in {"gpt4v", "depictqa"}
        self.evaluate_degradation_by = evaluate_degradation_by
        self.with_retrieval = with_retrieval
        assert reflect_by in {"gpt4v", "depictqa"}
        self.with_reflection = with_reflection
        self.reflect_by = reflect_by
        self.with_rollback = with_rollback

    def _create_components(
        self,
        llm_config_path: Path,
        schedule_experience_path: Optional[Path],
        silent: bool,
    ) -> None:
        # logger
        self.qa_logger = get_logger(
            logger_name="IRAgent QA",
            log_file=self.qa_path,
            console_log_level=logging.WARNING,
            file_format_str="%(message)s",
            silent=silent,
        )
        workflow_format_str = "%(asctime)s - %(levelname)s\n%(message)s\n"
        self.workflow_logger: logging.Logger = get_logger(
            logger_name="IRAgent Workflow",
            log_file=self.workflow_path,
            console_format_str=workflow_format_str,
            file_format_str=workflow_format_str,
            silent=silent,
        )

        # LLM
        self.gpt4 = GPT4(
            config_path=llm_config_path,
            logger=self.qa_logger,
            silent=silent,
            system_message=prompts.system_message,
        )
        self.depictqa = None
        if self.evaluate_degradation_by == "depictqa" or self.reflect_by == "depictqa":
            self.depictqa = DepictQA(logger=self.qa_logger, silent=silent)

        # experience
        if self.with_retrieval:
            assert (
                schedule_experience_path is not None
            ), "Experience should be provided."
            with open(schedule_experience_path, "r") as f:
                self.schedule_experience: str = json.load(f)["distilled"]

        # executor
        self.executor = executor
        random.seed(0)

    def _set_constants(self) -> None:
        self.degra_subtask_dict: dict[Degradation, Subtask] = {
            "low resolution": "super-resolution",
            "noise": "denoising",
            "motion blur": "motion deblurring",
            "defocus blur": "defocus deblurring",
            "haze": "dehazing",
            "rain": "deraining",
            "dark": "brightening",
            "jpeg compression artifact": "jpeg compression artifact removal",
        }
        self.subtask_degra_dict: dict[Subtask, Degradation] = {
            v: k for k, v in self.degra_subtask_dict.items()
        }
        self.degradations = set(self.degra_subtask_dict.keys())
        self.subtasks = set(self.degra_subtask_dict.values())
        self.levels: list[Level] = ["very low", "low", "medium", "high", "very high"]

    def run(self, plan: Optional[list[Subtask]]=None, cache: Optional[Path]=None) -> None:
        if plan is not None:
            self.plan = plan.copy()
            # 记录初始计划，即使是从命令行传入的
            self.work_mem["plan"]["initial"] = plan.copy()
            
        else:
            self.propose()  # 自动识别降质类型
        while self.plan:
            success = self.execute_subtask(cache)
            if self.with_rollback and not success:  # 注意这里保持 plan is None 的条件
                self.roll_back()
                self.reschedule()
        self._record_res()

    # ========== 修改：带交互的主运行方法（三问题模式） ==========
    def run_with_interaction(self) -> None:
        """支持用户交互的迭代式修复流程（三问题模式）"""
        iteration = 0
        
        while iteration < self.max_iterations:
            print(f"\n{'='*60}")
            print(f"🌟 迭代 {iteration + 1}/{self.max_iterations}")
            print(f"{'='*60}")
            
            # 运行一次修复流程
            self.run()
            
            # 保存当前结果
            result_path = self.res_path
            self.iteration_history.append({
                'iteration': iteration + 1,
                'result_path': str(result_path),
                'plan': self.work_mem['plan']['initial'].copy(),
                'execution_path': self.work_mem['execution_path'].copy()
            })
            
            if not self.interactive or iteration >= self.max_iterations - 1:
                break
                
            print(f"\n📸 当前结果保存在: {result_path}")
            
            # 清空输入缓冲区
            try:
                import termios
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            except:
                pass
            
            # 获取用户反馈（三问题模式）
            user_feedback = self._get_user_feedback()
            
            if user_feedback['satisfied']:
                print("\n✨ 用户满意，终止迭代。")
                break
            else:
                print("\n🔄 用户不满意，准备重新规划...")
                
                # 准备下一次迭代，传入是否使用原始图像
                self._prepare_next_iteration(
                    user_comments=user_feedback['comments'],
                    use_original=user_feedback['use_original']
                )
                iteration += 1
        
        self._save_iteration_history()
        print(f"\n{'='*60}")
        print("✨ 迭代完成")
        print(f"{'='*60}")
    # ===========================================

    def propose(self) -> None:
        """Sets the initial plan."""
        evaluation = self.evaluate_degradation()
        
        # 保存初始降质评估结果
        self.initial_evaluation = evaluation
        
        agenda = self.extract_agenda(evaluation)
        plan = self.schedule(agenda)

        self.work_mem["plan"]["initial"] = plan.copy()
        self._dump_summary()
        self.workflow_logger.info(f"Plan: {plan}")
        self.plan = plan

    def extract_agenda(self, evaluation: list[tuple[Degradation, Level]]
                       ) -> list[Subtask]:
        agenda = []
        img_shape = cv2.imread(self.cur_node["img_path"]).shape[:2]
        if max(img_shape) < 300:  # heuristically set
            agenda.append("super-resolution")
        for degradation, severity in evaluation:
            if self.levels.index(severity) >= 2:  # "medium" and above
                agenda.append(self.degra_subtask_dict[degradation])
        # stupid gpt is sensitive to presentation order when scheduling
        # shuffle to avoid the bias
        random.shuffle(agenda)
        return agenda

    def evaluate_degradation(self) -> list[tuple[Degradation, Level]]:
        """Evaluates the severities of the seven degradations
        (motion blur, defocus blur, rain, haze, dark, noise, jpeg compression artifact).
        """
        # 如果有用户指定的降质类型，直接返回对应的medium级别
        if self.manual_degradations is not None:
            evaluation = [(deg, "medium") for deg in self.manual_degradations]
            self.workflow_logger.info(f"Using manual degradations: {evaluation}")
            return evaluation
        
        if self.evaluate_degradation_by == "gpt4v":
            evaluation = self.evaluate_degradation_by_gpt4v()
        else:
            evaluation = eval(
                self.depictqa(Path(self.cur_node["img_path"]), task="eval_degradation")
            )
        self.workflow_logger.info(f"Evaluation: {evaluation}")
        return evaluation

    def evaluate_degradation_by_gpt4v(self) -> list[tuple[Degradation, Level]]:
        def check_evaluation(evaluation: object):
            assert isinstance(evaluation, list), "Evaluation should be a list."
            rsp_degradations = set()
            for ele in evaluation:
                assert isinstance(
                    ele, dict
                ), "Each element in evaluation should be a dict."
                assert set(ele.keys()) == {
                    "degradation",
                    "thought",
                    "severity",
                }, f"Invalid keys: {ele.keys()}."
                degradation = ele["degradation"]
                rsp_degradations.add(degradation)
                severity = ele["severity"]
                assert severity in self.levels, f"Invalid severity: {severity}."
            assert rsp_degradations == self.degradations - {
                "low resolution"
            }, f"Invalid degradation: {rsp_degradations}."

        evaluation = eval(
            self.gpt4(
                prompt=prompts.gpt_evaluate_degradation_prompt,
                img_path=Path(self.cur_node["img_path"]),
                format_check=check_evaluation,
            )
        )
        evaluation = [(ele["degradation"], ele["severity"]) for ele in evaluation]
        return evaluation

    def schedule(self, agenda: list[Subtask], ps: str = "") -> list[Subtask]:
        if len(agenda) <= 1:
            return agenda

        degradations = [self.subtask_degra_dict[subtask] for subtask in agenda]
        if self.with_retrieval:
            plan = self.schedule_w_retrieval(degradations, agenda, ps)
        else:
            plan = self.schedule_wo_retrieval(degradations, agenda, ps)
        return plan

    def schedule_w_retrieval(
        self, degradations: list[Degradation], agenda: list[Subtask], ps: str
    ) -> list[Subtask]:
        def check_order(schedule: object):
            assert isinstance(schedule, dict), "Schedule should be a dict."
            assert set(schedule.keys()) == {"thought", "order"}, \
                f"Invalid keys: {schedule.keys()}."
            order = schedule["order"]
            assert set(order) == set(agenda), \
                f"{order} is not a permutation of {agenda}."

        schedule = self.gpt4(
            prompt=prompts.schedule_w_retrieval_prompt.format(
                degradations=degradations, agenda=agenda, 
                experience=self.schedule_experience
            ) + ps,
            format_check=check_order,
        )
        schedule = eval(schedule)
        self.workflow_logger.info(f"Insights: {schedule['thought']}")
        return schedule["order"]

    def reason_to_schedule(
        self, degradations: list[Degradation], agenda: list[Subtask]
    ) -> str:
        insights = self.gpt4(
            prompt=prompts.reason_to_schedule_prompt.format(
                degradations=degradations, agenda=agenda
            ),
        )
        self.workflow_logger.info(f"Insights: {insights}")
        return insights

    def schedule_wo_retrieval(
        self, degradations: list[Degradation], agenda: list[Subtask], ps: str
    ) -> list[Subtask]:
        insights: str = self.reason_to_schedule(degradations, agenda)

        def check_order(order: object):
            assert isinstance(order, list), "Order should be a list."
            assert set(order) == set(agenda), f"{order} is not a permutation of {agenda}."

        order = self.gpt4(
            prompt=prompts.schedule_wo_retrieval_prompt.format(
                degradations=degradations, agenda=agenda, insights=insights
            ) + ps,
            format_check=check_order,
        )
        return eval(order)

    def execute_subtask(self, cache: Optional[Path]) -> bool:
        """Invokes tools to try to execute the top subtask in `self.plan` on `self.cur_node["img_path"]`, the directory of which is "0-img". Returns success or not. Updates `self.plan` and `self.cur_node`. Generates a directory parallel to "0-img", containing multiple directories, each of which contains outputs of a tool.\n
        Before:
.
├── 0-img
│ └── {input_path}
└── ...

text
After:
.
├── 0-img
│ └── {input_path}
├── {subtask_dir}
| ├── {tool_dir} 1
| │ └── 0-img
| │ └── output.png
| ├── ...
| └── {tool_dir} n
| └── 0-img
| └── output.png
└── ...

text
"""

        subtask = self.plan.pop(0)
        subtask_dir, degradation, toolbox = self._prepare_for_subtask(subtask)
        res_degra_level_dict: dict[str, list[Path]] = {}
        success = True

        for tool in toolbox:
            self.work_mem["n_invocations"] += 1
            # prepare directory
            tool_dir = subtask_dir / f"tool-{tool.tool_name}"
            output_dir = tool_dir / "0-img"
            output_dir.mkdir(parents=True)

            # invoke tool
            if cache is None:
                tool(
                    input_dir=Path(self.cur_node["img_path"]).parent,
                    output_dir=output_dir,
                    silent=True,
                )
            else:
                dst_path = output_dir / "output.png"
                rel_path = dst_path.relative_to(self.img_tree_dir)
                src_path = cache / rel_path
                dst_path.symlink_to(src_path)
            output_path = sorted_glob(output_dir)[0]

            if self.with_reflection:
                degra_level = self.evaluate_tool_result(output_path, degradation)
                self._record_tool_res(output_path, degra_level)
                res_degra_level_dict.setdefault(degra_level, []).append(output_path)
                if degra_level == "very low":
                    res_degra_level = "very low"
                    best_tool_name = tool.tool_name
                    # best_img_path = output_path
                    break
            else:
                best_tool_name = tool.tool_name
                # best_img_path = output_path
                res_degra_level = "none"
                self._record_tool_res(output_path, "none")
                break

        else:  # no result with "very low" degradation level
            for res_level in self.levels[1:]:
                if res_level in res_degra_level_dict:
                    candidates = res_degra_level_dict[res_level]
                    self.workflow_logger.info("Searching for the best tool...")
                    best_img_path = self.search_best_by_comp(candidates)
                    best_tool_name = self._get_name_stem(best_img_path.parents[1].name)
                    if res_level != "low":  # fail
                        success = False
                    res_degra_level = res_level
                    break

        self.cur_node["children"][subtask]["best_tool"] = best_tool_name
        self.cur_node = self.cur_node["children"][subtask]["tools"][best_tool_name]
        if self.with_rollback and not success:
            self.cur_node["best_descendant"] = str(best_img_path)
            done_subtasks, _ = self._get_execution_path(Path(self.cur_node['img_path']))
            self.work_mem["plan"]["adjusted"].append({
                "failed": f"{done_subtasks} + {self.plan}", "new": None
            })

        self._dump_summary()
        self._render_img_tree()
        self.workflow_logger.info(
            f"{subtask.capitalize()} result: "
            f"{self._img_nickname(self.cur_node['img_path'])} "
            f"with {res_degra_level} severity.")
            
        return success

    def evaluate_tool_result(self, img_path: Path, degradation: Degradation) -> Level:
        if self.reflect_by == "gpt4v":
            level = self.evaluate_tool_result_by_gpt4v(img_path, degradation)
        else:
            level = eval(
                self.depictqa(
                    img_path=img_path, task="eval_degradation", degradation=degradation
                )
            )[0][1]
        return level

    def evaluate_tool_result_by_gpt4v(
        self, img_path: Path, degradation: Degradation
    ) -> Level:
        def check_tool_res_evaluation(evaluation: object):
            assert isinstance(evaluation, dict), "Evaluation should be a dict."
            assert set(evaluation.keys()) == {
                "thought",
                "severity",
            }, f"Invalid keys: {evaluation.keys()}."
            severity = evaluation["severity"]
            assert severity in self.levels, f"Invalid severity: {severity}."

        degra_level = eval(
            self.gpt4(
                prompt=prompts.gpt_evaluate_tool_result_prompt.format(
                    degradation=degradation
                ),
                img_path=img_path,
                format_check=check_tool_res_evaluation,
            )
        )["severity"]
        return degra_level

    def search_best_by_comp(self, candidates: list[Path]) -> Path:
        """Compares multiple images to decide the best one."""

        best_img = candidates[0]
        for i in range(1, len(candidates)):
            cur_img = candidates[i]
            self.workflow_logger.info(
                f"Comparing {self._img_nickname(best_img)} and {self._img_nickname(cur_img)}..."
            )

            choice = self.compare_quality(best_img, cur_img)

            if choice == "latter":
                best_img = cur_img
                self.workflow_logger.info(
                    f"{self._img_nickname(best_img)} is better."
                )
            elif choice == "former":
                self.workflow_logger.info(
                    f"{self._img_nickname(best_img)} is better."
                )
            else:  # neither; keep the former
                self.workflow_logger.info(
                    f"Hard to decide. Keeping {self._img_nickname(best_img)}."
                )
        self.workflow_logger.info(
            f"{self._img_nickname(best_img)} is selected as the best."
        )
        return best_img

    def compare_quality(self, img1: Path, img2: Path) -> str:
        if self.reflect_by == "gpt4v":
            choice = self.compare_quality_by_gpt4v(img1, img2)
        else:
            choice = self.depictqa(img_path=[img1, img2], task="comp_quality")
        return choice

    def compare_quality_by_gpt4v(self, img1: Path, img2: Path) -> str:
        def check_comparison(comparison: object):
            assert isinstance(comparison, dict), "Comparison should be a dict."
            assert set(comparison.keys()) == {
                "thought",
                "choice",
            }, f"Invalid keys: {comparison.keys()}."
            assert comparison["choice"] in {
                "former",
                "latter",
                "neither",
            }, f"Invalid choice: {comparison['choice']}."

        comparison: dict = eval(
            self.gpt4(
                prompt=prompts.gpt_compare_prompt,
                img_path=[img1, img2],
                format_check=check_comparison,
            )
        )
        return comparison["choice"]

    def roll_back(self) -> None:
        # backtrack
        self._backtrack()
        step = 1
        while self._fully_expanded():
            self.workflow_logger.info(
                f"All execution paths from {self._img_nickname(self.cur_node['img_path'])} "
                f"lead to severe degradation.")
            self._set_best_desc()
            if self.cur_node != self.work_mem["tree"]:
                step += 1
                self._backtrack()
            else:
                break
        self.workflow_logger.info(
            f"Roll back for {step} step(s) "
            f"to {self._img_nickname(self.cur_node['img_path'])} "
            f"with agenda {self.plan}."
        )

        # compromise
        if self._fully_expanded():  # back to root
            self._to_best_desc(Path(self.cur_node["best_descendant"]))
            self.workflow_logger.info(
                "All execution paths from the input lead to severe degradation.\n"
                f"Compromise: jump to {self._img_nickname(self.cur_node['img_path'])} "
                f"with agenda {self.plan}."
            )
            assert not self._fully_expanded() or not self.plan, \
                "Invalid compromise: cannot go on or terminate."

        # check
        done_subtasks, _ = self._get_execution_path(Path(self.cur_node['img_path']))
        done_subtasks, plan = set(done_subtasks), set(self.plan)
        assert done_subtasks & plan == set(), \
            f"Invalid plan: {done_subtasks} & {plan} != ∅."
        assert done_subtasks | plan == set(self.work_mem["plan"]["initial"]), (
            f"Invalid plan: {done_subtasks} | {plan} != "
            f"{self.work_mem['plan']['initial']}.")

    def _fully_expanded(self) -> bool:
        return len(self.plan) == len(self.cur_node["children"])

    def _set_best_desc(self) -> None:
        candidates = [
            Path(subtask_res["tools"][subtask_res["best_tool"]]["best_descendant"])
            for subtask_res in self.cur_node["children"].values()
        ]
        self.workflow_logger.info("Searching for the best descendant...")
        best_img_path = self.search_best_by_comp(candidates)
        self.cur_node["best_descendant"] = str(best_img_path)

    def _to_best_desc(self, best_desc_path: Path):
        self.cur_node = self._img_path_to_node(best_desc_path)
        done_subtasks, _ = self._get_execution_path(best_desc_path)
        self.plan = list(set(self.plan) - set(done_subtasks))

    def _backtrack(self) -> None:
        """Returns to the parent of the current node (update plan and cur_node)."""
        this_subtask = self.degra_subtask_dict[self.cur_node["degradation"]]
        self.plan.insert(0, this_subtask)

        parent_img_path = next(
            Path(self.cur_node["img_path"]).parents[3].glob("0-img/*.png")
        )
        self.cur_node = self._img_path_to_node(parent_img_path)
        self.workflow_logger.info(
            f"Back to {self._img_nickname(self.cur_node['img_path'])}.")

    def _img_path_to_node(self, img_path: Path) -> dict:
        subtasks, tools = self._get_execution_path(img_path)
        node = self.work_mem["tree"]
        for subtask, tool in zip(subtasks, tools):
            node = node["children"][subtask]["tools"][tool]
        return node

    def reschedule(self) -> None:
        if not self.plan:
            return

        if not self.cur_node["children"]:
            # compromise, pick up the failed plan
            done_subtasks, _ = self._get_execution_path(Path(self.cur_node['img_path']))
            for adjusted_plan in self.work_mem["plan"]["adjusted"]:
                failed = adjusted_plan["failed"]
                failed_done, failed_planned = failed.split(" + ")
                failed_done, failed_planned = eval(failed_done), eval(failed_planned)
                if failed_done == done_subtasks:
                    self.plan = failed_planned
                    self.workflow_logger.info(f"Pick up the failed plan {failed_done} + {failed_planned}.")
                    break
            else:
                raise Exception(f"Invalid rescheduling: no failed plan found when processing {self.work_dir}.")

        elif len(self.plan) == len(self.cur_node["children"]) + 1:
            next_agenda = list(self.cur_node["children"])
            next_plan = self.schedule(next_agenda)
            top_subtask = list(set(self.plan)-set(next_agenda))[0]
            self.plan = [top_subtask] + next_plan

        else:
            done_top_subtasks = list(self.cur_node["children"])
            assert len(self.plan) - len(done_top_subtasks) > 1
            if len(done_top_subtasks) == 1:
                failed_tries_str = done_top_subtasks[0]
            else:
                failed_tries_str = 'any of ' + ', '.join(done_top_subtasks)
            reschedule_ps = prompts.reschedule_ps_prompt.format(
                failed_tries=failed_tries_str)
            self.plan = self.schedule(agenda=self.plan, ps=reschedule_ps)

            if self.plan[0] in done_top_subtasks:
                invalid_plan = self.plan.copy()
                for i, subtask in enumerate(self.plan):
                    if subtask not in done_top_subtasks:
                        self.plan[0], self.plan[i] = self.plan[i], self.plan[0]
                        break
                self.workflow_logger.warning(
                    f"Invalid rescheduling: the first subtask of {invalid_plan} "
                    f"in {done_top_subtasks}. Swapping it with {self.plan[0]}.")

        # record update
        done_subtasks, _ = self._get_execution_path(Path(self.cur_node['img_path']))
        assert set(done_subtasks+self.plan) == set(self.work_mem["plan"]["initial"]), \
            (f"Invalid adjusted plan: {done_subtasks} ∪ {self.plan} "
             f"!= {self.work_mem['plan']['initial']}.")
        self.work_mem["plan"]["adjusted"][-1]["new"] = f"{done_subtasks} + {self.plan}"
        self._dump_summary()

        self.workflow_logger.info(f"Adjusted plan: {self.plan}.")

    def _prepare_for_subtask(
        self, subtask: Subtask
    ) -> tuple[Path, Degradation, list[Tool]]:
        self.workflow_logger.info(
            f"Executing {subtask} on {self._img_nickname(self.cur_node['img_path'])}..."
        )

        subtask_dir = Path(self.cur_node["img_path"]).parents[1] / f"subtask-{subtask}"
        subtask_dir.mkdir()

        degradation = self.subtask_degra_dict[subtask]
        toolbox = self.executor.toolbox_router[subtask]
        random.shuffle(toolbox)

        return subtask_dir, degradation, toolbox

    def _record_tool_res(self, img_path: Path, degra_level: Level) -> None:
        tool_name = self._get_name_stem(img_path.parents[1].name)
        subtask = self._get_name_stem(img_path.parents[2].name)
        degradation = self.subtask_degra_dict[subtask]

        # log
        self.workflow_logger.info(
            f"Severity of {degradation} of {self._img_nickname(img_path)} "
            f"is {degra_level}."
        )

        # update working memory
        cur_children = self.cur_node["children"]
        if subtask not in cur_children:
            cur_children[subtask] = {"best_tool": None, "tools": {}}
        assert tool_name not in cur_children[subtask]["tools"]
        cur_children[subtask]["tools"][tool_name] = {
            "degradation": degradation,
            "severity": degra_level,
            "img_path": str(img_path),
            "best_descendant": None,
            "children": {},
        }

    def _write_record_log(self) -> None:
        """
        生成record.log文件，和workflow.log放在同一个目录下
        统一为两行：
        第一行：降质类型（用户指定的所有类型，或自动评估中low及以上的类型）
        第二行：修复流水线
        """
        record_log_path = self.log_dir / "record.log"

        # 调试信息
        print(f"Debug - manual_degradations: {self.manual_degradations}")
        print(f"Debug - initial_evaluation: {self.initial_evaluation}")

        # 第一行：降质类型
        if self.manual_degradations is not None:
            # 用户指定的降质类型（全部记录，无论程度）
            degradation_types = self.manual_degradations
        elif self.initial_evaluation:
            # 自动评估的降质类型（只取low及以上的）
            degradation_types = []
            for degradation, severity in self.initial_evaluation:
                if self.levels.index(severity) >= 1:  # low及以上
                    degradation_types.append(degradation)
        else:
            degradation_types = []

        line1 = f'degradation_types:{json.dumps(degradation_types)}'

        # 第二行：修复流水线
        subtasks, tools = self._get_execution_path(self.res_path)
        pipeline_parts = [f"{subtask}@{tool}" for subtask, tool in zip(subtasks, tools)]
        pipeline_str = "-".join(pipeline_parts) if pipeline_parts else "none"
        line2 = f"Restoration result: {pipeline_str}"

        # 写入文件
        with open(record_log_path, 'w') as f:
            f.write(line1 + '\n')
            f.write(line2 + '\n')

        self.workflow_logger.info(f"Record log saved to {record_log_path}")

    def _record_res(self) -> None:
        self.res_path = Path(self.cur_node["img_path"])
        self.workflow_logger.info(
            f"Restoration result: {self._img_nickname(self.res_path)}.")
        subtasks, tools = self._get_execution_path(self.res_path)
        self.work_mem["execution_path"]["subtasks"] = subtasks
        self.work_mem["execution_path"]["tools"] = tools
        self._dump_summary()
        shutil.copy(self.res_path, self.work_dir / "result.png")
        print(f"Result saved in {self.res_path}.")

        # 写入record.log文件
        self._write_record_log()

    def _get_execution_path(self, img_path: Path) -> tuple[list[Subtask], list[ToolName]]:
        """Returns the execution path of the restored image (list of subtask and tools)."""
        exe_path = self._img_tree.get_execution_path(img_path)
        if not exe_path:
            return [], []
        subtasks, tools = zip(*exe_path)
        return list(subtasks), list(tools)

    def _prepare_dir(self, input_path: Path, output_dir: Path) -> None:
        """Sets attributes: `work_dir, img_tree_dir, log_dir, qa_path, workflow_path, summary_path`. Creates necessary directories, which will be like
        output_dir
        └── {task_id}(work_dir)
            ├── img_tree
            │   └── 0-img
            │       └── input.png
            └── logs
                ├── summary.json
                ├── workflow.log
                ├── llm_qa.md
                └── img_tree.html

        text
        """

        task_id = f"{input_path.stem}-{strftime('%y%m%d_%H%M%S', localtime())}"
        self.work_dir = output_dir / task_id
        self.work_dir.mkdir(parents=True)

        self.img_tree_dir = self.work_dir / "img_tree"
        self.img_tree_dir.mkdir()

        self.log_dir = self.work_dir / "logs"
        self.log_dir.mkdir()
        self.qa_path = self.log_dir / "llm_qa.md"
        self.workflow_path = self.log_dir / "workflow.log"
        self.work_mem_path = self.log_dir / "summary.json"

        rqd_input_dir = self.img_tree_dir / "0-img"
        rqd_input_dir.mkdir()
        rqd_input_path = rqd_input_dir / "input.png"
        self.root_input_path = rqd_input_path
        shutil.copy(input_path, rqd_input_path)

        self._render_img_tree()

    def _img_nickname(self, img_path: str | Path) -> str:
        """Image name to display in log, showing the execution path."""        
        if isinstance(img_path, str):
            img_path = Path(img_path)
        subtasks, tools = self._get_execution_path(img_path)
        if not subtasks:
            return "input"
        return "-".join([f"{subtask}@{tool}" 
                         for subtask, tool in zip(subtasks, tools)])

    def _get_name_stem(self, name: str) -> str:
        return name[name.find("-") + 1 :]

    @property
    def _img_tree(self) -> ImgTree:
        return ImgTree(self.img_tree_dir, html_dir=self.log_dir)

    def _render_img_tree(self) -> None:
        self._img_tree.to_html()

    def _dump_summary(self) -> None:
        with open(self.work_mem_path, "w") as f:
            json.dump(self.work_mem, f, indent=2)

    # ========== 修改：交互式迭代辅助方法（三问题模式） ==========
    def _get_user_feedback(self) -> dict:
        """获取用户对当前结果的反馈（三问题模式）"""
        import sys
        import time

        print("\n" + "="*50)
        print("请检查当前修复结果：")
        print("="*50)

        # 清空输入缓冲区
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except:
            pass

        time.sleep(0.5)  # 等待一下确保输出完成

        # 问题1：是否满意？
        while True:
            try:
                print("\n📋 问题1/3")
                print("是否满意当前修复结果？(y/n): ", end='', flush=True)
                satisfied_input = input().strip().lower()
                
                if satisfied_input == '':
                    print("❌ 输入不能为空，请输入 y 或 n")
                    continue
                    
                if satisfied_input in ['y', 'n', 'yes', 'no']:
                    satisfied = satisfied_input in ['y', 'yes']
                    break
                else:
                    print(f"❌ 无效输入: '{satisfied_input}'，请输入 y 或 n")
                    
            except KeyboardInterrupt:
                print("\n\n用户中断")
                raise
            except Exception as e:
                print(f"❌ 输入错误: {e}，请重试")
                continue

        comments = ""
        use_original = False

        # 如果不满意，继续问问题2和3
        if not satisfied:
            # 问题2：改进建议
            while True:
                try:
                    print("\n📋 问题2/3")
                    print("请描述不满意的地方或改进建议: ", end='', flush=True)
                    comments = input().strip()
                    
                    if comments == '':
                        print("❌ 建议不能为空，请描述您的不满或建议")
                        continue
                        
                    break
                    
                except KeyboardInterrupt:
                    print("\n\n用户中断")
                    raise
                except Exception as e:
                    print(f"❌ 输入错误: {e}，请重试")
                    continue
            
            # 问题3：是否从原始图像开始
            while True:
                try:
                    print("\n📋 问题3/3")
                    print("是否从原始图像重新开始？(y/n，默认n): ", end='', flush=True)
                    use_original_input = input().strip().lower()
                    
                    if use_original_input == '':
                        use_original = False  # 默认不从原始图像开始
                        break
                        
                    if use_original_input in ['y', 'n', 'yes', 'no']:
                        use_original = use_original_input in ['y', 'yes']
                        break
                    else:
                        print(f"❌ 无效输入: '{use_original_input}'，请输入 y 或 n")
                        
                except KeyboardInterrupt:
                    print("\n\n用户中断")
                    raise
                except Exception as e:
                    print(f"❌ 输入错误: {e}，请重试")
                    continue

        # 显示反馈总结
        print("\n" + "="*50)
        print("📝 反馈总结:")
        print(f"  满意: {'✅' if satisfied else '❌'}")
        if not satisfied:
            print(f"  建议: {comments}")
            print(f"  从原始图像开始: {'✅' if use_original else '❌'}")
        print("="*50 + "\n")

        return {
            'satisfied': satisfied, 
            'comments': comments,
            'use_original': use_original
        }

    def _prepare_next_iteration(self, user_comments: str, use_original: bool = False) -> None:
        """基于用户反馈准备下一次迭代

        Args:
            user_comments: 用户反馈
            use_original: 是否使用原始图像作为输入
        """

        print(f"\n🔄 准备下一次迭代...")
        print(f"  反馈: {user_comments}")
        print(f"  使用原始图像: {'✅' if use_original else '❌'}")

        # 保存当前状态作为经验
        self._add_to_experience(user_comments)

        # 使用LLM重新规划修复策略
        new_plan = self._replan_with_feedback(user_comments)

        # 重置状态，根据选择决定输入图像
        self._reset_for_next_iteration(new_plan, use_original)

    def _reset_for_next_iteration(self, new_plan: list[Subtask], use_original: bool = False) -> None:
        """重置代理状态以进行下一次迭代

        Args:
            new_plan: 新的修复计划
            use_original: 是否使用原始图像作为输入
        """

        if use_original:
            # 使用原始图像
            next_input_path = self.root_input_path
            print(f"\n📸 使用原始图像作为输入: {next_input_path}")
        else:
            # 使用当前结果
            next_input_path = self.work_dir / f"iteration_{len(self.iteration_history)}_input.png"
            shutil.copy(self.res_path, next_input_path)
            print(f"\n📸 使用当前结果作为输入: {next_input_path}")

        # 创建新的工作目录
        new_task_id = f"{self.root_input_path.stem}-iter{len(self.iteration_history)}-{strftime('%y%m%d_%H%M%S', localtime())}"
        new_work_dir = self.work_dir.parent / new_task_id
        print(f"📁 创建工作目录: {new_work_dir}")

        # 重新初始化状态
        self._prepare_dir(next_input_path, new_work_dir.parent)
        self._init_state()

        # 设置新的计划
        self.plan = new_plan.copy()
        self.work_mem["plan"]["initial"] = new_plan.copy()
        self.work_mem["plan"]["previous_iterations"] = self.iteration_history.copy()

        print(f"✅ 下一次迭代准备完成")
        print(f"📋 新计划: {new_plan}")

    def _replan_with_feedback(self, feedback: str) -> list[Subtask]:
        """让LLM基于用户反馈重新规划修复策略"""

        # 获取历史执行信息
        history_summary = self._format_iteration_history()

        # 构建提示词
        replan_prompt = f"""
        Previous restoration attempts:
        {history_summary}

        User feedback on the latest result:
        "{feedback}"

        Based on this feedback, please propose a new restoration plan. 
        Consider:
        1. What degradations might have been missed or insufficiently addressed?
        2. Should we try different tools for certain subtasks?
        3. Is the order of subtasks optimal?

        The available subtasks are: {list(self.subtasks)}

        Please provide a new plan as a list of subtasks in execution order.
        Your output must be a JSON object with two fields:
        - "thought": your analysis of the feedback and reasoning for the new plan
        - "plan": a list of subtasks in the order you recommend
        """

        def check_replan(response: object):
            assert isinstance(response, dict), "Response should be a dict"
            assert "thought" in response, "Response must contain 'thought'"
            assert "plan" in response, "Response must contain 'plan'"
            assert isinstance(response["plan"], list), "Plan must be a list"
            for subtask in response["plan"]:
                assert subtask in self.subtasks, f"Invalid subtask: {subtask}"

        # 调用GPT重新规划
        response = eval(self.gpt4(
            prompt=replan_prompt,
            format_check=check_replan
        ))

        self.workflow_logger.info(f"Replanning insights: {response['thought']}")
        self.workflow_logger.info(f"New plan: {response['plan']}")

        return response["plan"]

    def _format_iteration_history(self) -> str:
        """格式化迭代历史用于LLM提示"""
        if not self.iteration_history:
            return "No previous attempts."

        history_str = ""
        for i, record in enumerate(self.iteration_history):
            history_str += f"\nIteration {i+1}:\n"
            history_str += f"  Plan: {record['plan']}\n"
            history_str += f"  Execution path: {record['execution_path']}\n"

        return history_str

    def _add_to_experience(self, feedback: str) -> None:
        """将用户反馈添加到经验库（可选）"""
        # 这里可以实现将成功/失败的案例添加到经验库的逻辑
        # 用于未来改进调度策略
        pass

    def _save_iteration_history(self) -> None:
        """保存所有迭代历史到文件"""
        history_path = self.log_dir / "iteration_history.json"
        with open(history_path, 'w') as f:
            json.dump({
                'iterations': self.iteration_history,
                'final_result': str(self.res_path) if hasattr(self, 'res_path') else None
            }, f, indent=2)
        self.workflow_logger.info(f"Iteration history saved to {history_path}")
    # ===========================================
