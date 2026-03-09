# # direct_pipeline.py
# from pathlib import Path
# import shutil
# from typing import List, Tuple
# import sys
# import argparse
# from datetime import datetime

# # 导入工具
# from executor.super_resolution import sr_toolbox
# from executor.denoising import denoising_toolbox
# from executor.motion_deblurring import motion_deblurring_toolbox
# from executor.defocus_deblurring import defocus_deblurring_toolbox
# from executor.dehazing import dehazing_toolbox
# from executor.deraining import deraining_toolbox
# from executor.brightening import brightening_toolbox
# from executor.jpeg_compression_artifact_removal import jpeg_compression_artifact_removal_toolbox
# from executor.tool import Tool


# class DirectPipeline:
#     """
#     直接执行指定工具流水线的类，跳过降质识别和大模型调度
    
#     Args:
#         input_path (Path): 输入图像路径
#         output_dir (Path): 输出目录
#         pipeline (List[Tuple[str, str]]): 流水线定义，每个元素为(subtask, tool_name)
#         pipeline_name (str): 流水线名称，用于输出目录命名
#         move_original_to_backup (bool): 是否将原图移动到backup文件夹
#     """
    
#     def __init__(self, input_path: Path, output_dir: Path, pipeline: List[Tuple[str, str]], 
#                  pipeline_name: str = "custom", move_original_to_backup: bool = True):
#         self.input_path = Path(input_path).resolve()
#         self.output_dir = Path(output_dir).resolve()
#         self.pipeline = pipeline
#         self.pipeline_name = pipeline_name
#         self.move_original_to_backup = move_original_to_backup
        
#         # 创建输出目录结构（带时间戳）
#         self._prepare_directories()
        
#         # 获取所有可用的工具
#         self.toolbox_router = self._build_toolbox_router()
        
#     def _build_toolbox_router(self) -> dict:
#         """构建工具路由表"""
#         router = {}
        
#         # 注册所有子任务的工具
#         subtask_toolboxes = [
#             ('super-resolution', sr_toolbox),
#             ('denoising', denoising_toolbox),
#             ('motion deblurring', motion_deblurring_toolbox),
#             ('defocus deblurring', defocus_deblurring_toolbox),
#             ('dehazing', dehazing_toolbox),
#             ('deraining', deraining_toolbox),
#             ('brightening', brightening_toolbox),
#             ('jpeg compression artifact removal', jpeg_compression_artifact_removal_toolbox)
#         ]
        
#         for subtask_name, toolbox in subtask_toolboxes:
#             router[subtask_name] = {tool.tool_name: tool for tool in toolbox}
            
#         return router
    
#     def _prepare_directories(self):
#         """准备输出目录结构（带时间戳）"""
#         # 生成时间戳（格式：YYMMDD_HHMMSS，例如 260304_110922）
#         self.timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        
#         # 创建主输出目录：{pipeline_name}-{timestamp}
#         self.work_dir = self.output_dir / f"{self.pipeline_name}-{self.timestamp}"
#         self.work_dir.mkdir(parents=True, exist_ok=False)  # exist_ok=False 确保不会覆盖已有目录
        
#         # 创建backup目录（用于存放原始图像）
#         self.backup_dir = self.work_dir / "backup"
#         self.backup_dir.mkdir(exist_ok=True)
        
#         print(f"创建输出目录: {self.work_dir}")
#         print(f"创建备份目录: {self.backup_dir}")
        
#         # 创建img_tree目录
#         self.img_tree_dir = self.work_dir / "img_tree"
#         self.img_tree_dir.mkdir(exist_ok=True)
        
#         # 复制输入图像到初始位置
#         self.current_input_dir = self.img_tree_dir / "0-img"
#         self.current_input_dir.mkdir(exist_ok=True)
#         self.current_input_path = self.current_input_dir / "input.png"
#         shutil.copy(self.input_path, self.current_input_path)
        
#         # 保存流水线配置信息
#         self._save_pipeline_info()
        
#     def _save_pipeline_info(self):
#         """保存流水线配置信息到文件"""
#         info_file = self.work_dir / "pipeline_info.txt"
#         with open(info_file, 'w', encoding='utf-8') as f:
#             f.write(f"Pipeline Name: {self.pipeline_name}\n")
#             f.write(f"Input Image: {self.input_path}\n")
#             f.write(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
#             f.write(f"Move Original to Backup: {self.move_original_to_backup}\n")
#             f.write("-" * 50 + "\n")
#             f.write("Pipeline Steps:\n")
#             for i, (subtask, tool) in enumerate(self.pipeline, 1):
#                 f.write(f"  Step {i}: {subtask} -> {tool}\n")
        
#     def _get_tool_by_name(self, subtask: str, tool_name: str) -> Tool:
#         """根据子任务和工具名称获取工具实例"""
#         if subtask not in self.toolbox_router:
#             raise ValueError(f"未知的子任务: {subtask}")
        
#         if tool_name not in self.toolbox_router[subtask]:
#             available_tools = list(self.toolbox_router[subtask].keys())
#             raise ValueError(f"子任务 '{subtask}' 中没有工具 '{tool_name}'，可用工具: {available_tools}")
        
#         return self.toolbox_router[subtask][tool_name]
    
#     def run(self):
#         """执行流水线"""
#         try:
#             print(f"开始执行流水线: {self.pipeline}")
#             print(f"输入图像: {self.input_path}")
#             print(f"输出目录: {self.work_dir}")
#             print("-" * 60)
            
#             execution_path = []  # 记录执行路径
            
#             for step_idx, (subtask, tool_name) in enumerate(self.pipeline, 1):
#                 print(f"\n步骤 {step_idx}: {subtask} -> {tool_name}")
                
#                 # 获取工具
#                 tool = self._get_tool_by_name(subtask, tool_name)
                
#                 # 创建步骤目录
#                 step_dir = self.img_tree_dir / f"step{step_idx}-{subtask.replace(' ', '_')}"
#                 step_dir.mkdir(exist_ok=True)
                
#                 tool_dir = step_dir / f"tool-{tool_name}"
#                 output_dir = tool_dir / "0-img"
#                 output_dir.mkdir(parents=True, exist_ok=True)
                
#                 # 执行工具
#                 print(f"  输入: {self.current_input_path}")
#                 tool(
#                     input_dir=self.current_input_dir,
#                     output_dir=output_dir,
#                     silent=False  # 设为False可以看到详细输出
#                 )
                
#                 # 获取输出图像
#                 output_files = list(output_dir.glob("*"))
#                 if not output_files:
#                     raise RuntimeError(f"工具 {tool_name} 没有生成输出文件")
                
#                 output_path = output_files[0]
#                 print(f"  输出: {output_path}")
                
#                 # 更新当前输入为这次输出
#                 self.current_input_dir = output_dir
#                 self.current_input_path = output_path
                
#                 execution_path.append((subtask, tool_name))
                
#             print("-" * 60)
#             print(f"\n流水线执行完成!")
#             print(f"最终结果: {self.current_input_path}")
            
#             # 复制最终结果到工作目录
#             result_path = self.work_dir / "result.png"
#             shutil.copy(self.current_input_path, result_path)
#             print(f"结果已保存: {result_path}")
            
#             # 保存执行路径信息
#             self._save_execution_path(execution_path)
            
#             return result_path
            
#         finally:
#             # 无论程序是否成功运行，都会执行这部分代码
#             self._move_original_to_backup()
    
#     def _save_execution_path(self, execution_path):
#         """保存执行路径信息"""
#         path_file = self.work_dir / "execution_path.txt"
#         with open(path_file, 'w', encoding='utf-8') as f:
#             f.write("Execution Path:\n")
#             for i, (subtask, tool) in enumerate(execution_path, 1):
#                 f.write(f"  Step {i}: {subtask} -> {tool}\n")
#             f.write(f"\nFinal result: {self.current_input_path}")
    
#     def _move_original_to_backup(self):
#         """将原始图像移动到backup文件夹"""
#         if not self.move_original_to_backup:
#             return
        
#         try:
#             original_path = self.input_path
#             if original_path.exists():
#                 # 使用时间戳创建唯一文件名
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 filename = original_path.stem
#                 extension = original_path.suffix
#                 new_name = f"{filename}_original_{timestamp}{extension}"
#                 new_path = self.backup_dir / new_name
                
#                 # 移动文件到备份目录
#                 shutil.move(str(original_path), str(new_path))
#                 print(f"\n原始图像已移动到: {new_path}")
                
#                 # 记录移动信息
#                 self._record_backup_info(new_path)
#             else:
#                 print(f"\n警告: 原始图像不存在: {original_path}")
                
#         except Exception as e:
#             print(f"\n警告: 移动原始图像时出错: {e}")
    
#     def _record_backup_info(self, backup_path: Path):
#         """记录备份信息"""
#         backup_info_file = self.backup_dir / "backup_info.txt"
#         with open(backup_info_file, 'w', encoding='utf-8') as f:
#             f.write(f"Original Image Backup Information\n")
#             f.write("=" * 40 + "\n")
#             f.write(f"Original Path: {self.input_path}\n")
#             f.write(f"Backup Path: {backup_path}\n")
#             f.write(f"Backup Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
#             f.write(f"Pipeline Used: {self.pipeline_name}\n")
#             f.write("\nPipeline Steps:\n")
#             for i, (subtask, tool) in enumerate(self.pipeline, 1):
#                 f.write(f"  Step {i}: {subtask} -> {tool}\n")
#             f.write("\n" + "=" * 40 + "\n")
#             f.write("Note: This file was moved to backup after processing.\n")


# def get_pipeline_by_name(pipeline_name: str) -> Tuple[List[Tuple[str, str]], str]:
#     """根据名称返回对应的流水线配置和显示名称"""
    
#     pipelines = {
#         # 老照片修复
#         "oldpic": {
#             "name": "oldpic",
#             "display": "老照片修复",
#             "steps": [
#                 ("denoising", "swinir_15"),      # 先去噪
#                 ("super-resolution", "xrestormer")  # 再超分
#             ]
#         },
        
#         # 天气魔法（去雨+去雾）
#         "weather": {
#             "name": "weather",
#             "display": "天气魔法",
#             "steps": [
#                 ("deraining", "xrestormer"),      # 去雨
#                 ("dehazing", "refinednet")        # 去雾
#             ]
#         },
        
#         # 夜视之眼（去噪+亮度增强）
#         "dark": {
#             "name": "dark",
#             "display": "夜视之眼",
#             "steps": [
#                 ("denoising", "swinir_50"),       # 去噪
#                 ("brightening", "constant_shift") # 亮度调整
#             ]
#         },
        
#         # 去散焦模糊
#         "defocus": {
#             "name": "defocus",
#             "display": "去散焦模糊",
#             "steps": [
#                 ("defocus deblurring", "drbnet")  # 去散焦模糊
#             ]
#         },
        
#         # 去运动模糊
#         "motion": {
#             "name": "motion",
#             "display": "去运动模糊",
#             "steps": [
#                 ("motion deblurring", "xrestormer")  # 去运动模糊
#             ]
#         },
        
#         # 综合修复（去噪+超分+亮度）
#         "full": {
#             "name": "full",
#             "display": "综合修复",
#             "steps": [
#                 ("denoising", "swinir_50"),
#                 ("super-resolution", "edsr"),
#                 ("brightening", "zero_dce")
#             ]
#         },
        
#         # 可以去雾+亮度
#         "haze_bright": {
#             "name": "haze_bright",
#             "display": "去雾+亮度",
#             "steps": [
#                 ("dehazing", "aod_net"),
#                 ("brightening", "constant_shift")
#             ]
#         }
#     }
    
#     # 去除名称中的"pipeline_"前缀（如果有）
#     pipeline_key = pipeline_name.replace("pipeline_", "")
    
#     if pipeline_key not in pipelines:
#         available = list(pipelines.keys())
#         raise ValueError(f"未知的流水线名称: '{pipeline_name}'。可用的流水线: {available}")
    
#     pipeline_info = pipelines[pipeline_key]
#     print(f"选择流水线: {pipeline_info['display']}")
#     return pipeline_info["steps"], pipeline_info["name"]


# def list_available_pipelines():
#     """列出所有可用的流水线"""
#     pipelines = {
#         "oldpic": "老照片修复 (去噪 + 超分)",
#         "weather": "天气魔法 (去雨 + 去雾)",
#         "dark": "夜视之眼 (去噪 + 亮度增强)",
#         "defocus": "去散焦模糊",
#         "motion": "去运动模糊",
#         "full": "综合修复 (去噪 + 超分 + 亮度)",
#         "haze_bright": "去雾 + 亮度增强"
#     }
    
#     print("\n可用的流水线:")
#     for name, desc in pipelines.items():
#         print(f"  {name:<12} - {desc}")
#     print()


# def main():
#     # 创建命令行参数解析器
#     parser = argparse.ArgumentParser(description='直接执行图像修复流水线')
    
#     parser.add_argument('--pipeline', '-p', 
#                        type=str,
#                        default='dark',
#                        help='要执行的流水线名称 (默认: dark)')
    
#     parser.add_argument('--input', '-i',
#                        type=str,
#                        default='dataset/example.png',
#                        help='输入图像路径 (默认: dataset/example.png)')
    
#     # parser.add_argument('--output', '-o',
#     #                    type=str,
#     #                    default='output_direct',
#     #                    help='输出根目录 (默认: output_direct)')
#     parser.add_argument('--output', '-o',
#                        type=str,
#                        default='output',
#                        help='输出根目录 (默认: output)')
    
#     parser.add_argument('--list', '-l',
#                        action='store_true',
#                        help='列出所有可用的流水线')
    
#     parser.add_argument('--custom', '-c',
#                        type=str,
#                        nargs='+',
#                        help='自定义流水线，格式: subtask1 tool1 subtask2 tool2 ...')
    
#     parser.add_argument('--name', '-n',
#                        type=str,
#                        default=None,
#                        help='自定义输出目录名称（不包含时间戳）')
    
#     parser.add_argument('--no-backup', 
#                        action='store_true',
#                        help='不将原图移动到backup文件夹')
    
#     args = parser.parse_args()
    
#     # 如果只是列出流水线，则列出后退出
#     if args.list:
#         list_available_pipelines()
#         return
    
#     # 获取流水线配置
#     if args.custom:
#         # 解析自定义流水线
#         if len(args.custom) % 2 != 0:
#             raise ValueError("自定义流水线参数必须成对出现: subtask tool [subtask tool ...]")
        
#         pipeline = []
#         for i in range(0, len(args.custom), 2):
#             subtask = args.custom[i].replace('_', ' ')  # 将下划线替换为空格
#             tool = args.custom[i+1]
#             pipeline.append((subtask, tool))
        
#         # 自定义流水线的名称
#         if args.name:
#             pipeline_name = args.name
#         else:
#             # 根据工具生成名称
#             tool_names = [tool for _, tool in pipeline]
#             pipeline_name = "custom_" + "_".join(tool_names)
        
#         print(f"使用自定义流水线: {pipeline}")
#         print(f"流水线名称: {pipeline_name}")
        
#     else:
#         # 使用预定义流水线
#         try:
#             pipeline, pipeline_name = get_pipeline_by_name(args.pipeline)
#         except ValueError as e:
#             print(e)
#             list_available_pipelines()
#             return
    
#     # 输入图像路径
#     input_image = Path(args.input)
#     if not input_image.exists():
#         print(f"错误: 输入图像不存在: {input_image}")
#         return
    
#     # 输出根目录
#     output_root = Path(args.output)
    
#     print(f"输入图像: {input_image}")
#     print(f"输出根目录: {output_root}")
#     print(f"流水线: {pipeline}")
#     print(f"备份原图: {'否' if args.no_backup else '是'}")
#     print("-" * 60)
    
#     # 创建并运行流水线
#     try:
#         pipeline_runner = DirectPipeline(
#             input_path=input_image,
#             output_dir=output_root,
#             pipeline=pipeline,
#             pipeline_name=pipeline_name,
#             move_original_to_backup=not args.no_backup  # 默认是True
#         )
        
#         result = pipeline_runner.run()
#         print(f"\n成功! 结果保存在: {result}")
        
#     except Exception as e:
#         print(f"执行出错: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)


# if __name__ == "__main__":
#     main()

from pathlib import Path
import shutil
from typing import List, Tuple
import sys
import argparse
from datetime import datetime
import logging
import json

# 导入工具
from executor.super_resolution import sr_toolbox
from executor.denoising import denoising_toolbox
from executor.motion_deblurring import motion_deblurring_toolbox
from executor.defocus_deblurring import defocus_deblurring_toolbox
from executor.dehazing import dehazing_toolbox
from executor.deraining import deraining_toolbox
from executor.brightening import brightening_toolbox
from executor.jpeg_compression_artifact_removal import jpeg_compression_artifact_removal_toolbox
from executor.tool import Tool


class DirectPipeline:
    """
    直接执行指定工具流水线的类，跳过降质识别和大模型调度
    生成与 IRAgent 统一的目录结构和日志格式
    
    Args:
        input_path (Path): 输入图像路径
        output_dir (Path): 输出根目录
        pipeline (List[Tuple[str, str]]): 流水线定义，每个元素为(subtask, tool_name)
        pipeline_name (str): 流水线名称，用于输出目录命名
        move_original_to_backup (bool): 是否将原图移动到backup文件夹
    """
    
    def __init__(self, input_path: Path, output_dir: Path, pipeline: List[Tuple[str, str]], 
                 pipeline_name: str = "custom", move_original_to_backup: bool = True):
        self.input_path = Path(input_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.pipeline = pipeline
        self.pipeline_name = pipeline_name
        self.move_original_to_backup = move_original_to_backup
        
        # 创建输出目录结构（与 IRAgent 统一）
        self._prepare_directories()
        
        # 设置日志（与 IRAgent 相同格式）
        self._setup_logging()
        
        # 获取所有可用的工具
        self.toolbox_router = self._build_toolbox_router()
        
        # 降质类型映射（用于模拟评估结果）
        self.degra_subtask_dict = {
            "low resolution": "super-resolution",
            "noise": "denoising",
            "motion blur": "motion deblurring",
            "defocus blur": "defocus deblurring",
            "haze": "dehazing",
            "rain": "deraining",
            "dark": "brightening",
            "jpeg compression artifact": "jpeg compression artifact removal",
        }
        
    def _setup_logging(self):
        """设置日志，生成与 IRAgent 相同格式的 workflow.log"""
        # 日志格式：与 IRAgent 完全一致
        workflow_format = "%(asctime)s - %(levelname)s\n%(message)s\n"
        
        # 创建 logger
        self.logger = logging.getLogger(f"DirectPipeline-{self.pipeline_name}")
        self.logger.setLevel(logging.INFO)
        
        # 移除已有的处理器
        self.logger.handlers.clear()
        
        # 文件处理器 - 写入 logs/workflow.log
        file_handler = logging.FileHandler(self.workflow_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(workflow_format))
        self.logger.addHandler(file_handler)
        
        # 控制台处理器（可选）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(workflow_format))
        self.logger.addHandler(console_handler)
        
    def _build_toolbox_router(self) -> dict:
        """构建工具路由表"""
        router = {}
        
        # 注册所有子任务的工具
        subtask_toolboxes = [
            ('super-resolution', sr_toolbox),
            ('denoising', denoising_toolbox),
            ('motion deblurring', motion_deblurring_toolbox),
            ('defocus deblurring', defocus_deblurring_toolbox),
            ('dehazing', dehazing_toolbox),
            ('deraining', deraining_toolbox),
            ('brightening', brightening_toolbox),
            ('jpeg compression artifact removal', jpeg_compression_artifact_removal_toolbox)
        ]
        
        for subtask_name, toolbox in subtask_toolboxes:
            router[subtask_name] = {tool.tool_name: tool for tool in toolbox}
            
        return router
    
    def _prepare_directories(self):
        """准备输出目录结构（与 IRAgent 统一）"""
        # 生成时间戳（格式：YYMMDD_HHMMSS，例如 260304_110922）
        self.timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        
        # 创建主输出目录：{pipeline_name}-{timestamp}
        self.work_dir = self.output_dir / f"{self.pipeline_name}-{self.timestamp}"
        self.work_dir.mkdir(parents=True, exist_ok=False)
        
        print(f"创建输出目录: {self.work_dir}")
        
        # 创建 img_tree 目录
        self.img_tree_dir = self.work_dir / "img_tree"
        self.img_tree_dir.mkdir(exist_ok=True)
        
        # 创建 logs 目录
        self.log_dir = self.work_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志文件路径
        self.workflow_path = self.log_dir / "workflow.log"
        
        # 复制输入图像到初始位置：img_tree/0-img/input.png
        self.current_input_dir = self.img_tree_dir / "0-img"
        self.current_input_dir.mkdir(exist_ok=True)
        self.current_input_path = self.current_input_dir / "input.png"
        shutil.copy(self.input_path, self.current_input_path)
        
    def _get_tool_by_name(self, subtask: str, tool_name: str) -> Tool:
        """根据子任务和工具名称获取工具实例"""
        if subtask not in self.toolbox_router:
            raise ValueError(f"未知的子任务: {subtask}")
        
        if tool_name not in self.toolbox_router[subtask]:
            available_tools = list(self.toolbox_router[subtask].keys())
            raise ValueError(f"子任务 '{subtask}' 中没有工具 '{tool_name}'，可用工具: {available_tools}")
        
        return self.toolbox_router[subtask][tool_name]
    
    def _generate_mock_evaluation(self) -> list:
        """生成模拟的降质评估结果（格式与 IRAgent 相同）"""
        # 根据流水线名称生成对应的降质类型评估
        pipeline_to_degradations = {
            "oldpic": [("noise", "very high"), ("jpeg compression artifact", "medium")],
            "weather": [("rain", "high"), ("haze", "medium")],
            "dark": [("noise", "very high"), ("dark", "high")],
            "defocus": [("defocus blur", "high")],
            "motion": [("motion blur", "high")],
            "full": [("noise", "very high"), ("low resolution", "high"), ("dark", "medium")],
            "haze_bright": [("haze", "high"), ("dark", "medium")]
        }
        
        # 默认评估
        default = [("noise", "medium"), ("low resolution", "medium")]
        
        evaluation = pipeline_to_degradations.get(self.pipeline_name, default)
        
        # 格式化为 IRAgent 的输出格式
        return evaluation
    
    def run(self):
        """执行流水线，生成与 IRAgent 相同的日志格式"""
        try:
            # 1. 模拟降质评估（与 IRAgent 的 Evaluation 部分对应）
            evaluation = self._generate_mock_evaluation()
            self.logger.info(f"Evaluation: {evaluation}")
            
            # 2. 模拟生成 Insights（与 IRAgent 的 Insights 部分对应）
            insights = self._generate_insights()
            self.logger.info(f"Insights: {insights}")
            
            # 3. 记录计划（与 IRAgent 的 Plan 部分对应）
            plan = [subtask for subtask, _ in self.pipeline]
            self.logger.info(f"Plan: {plan}")
            
            execution_path = []
            
            # 4. 执行每一步
            for step_idx, (subtask, tool_name) in enumerate(self.pipeline, 1):
                self.logger.info(f"Executing {subtask} on input...")
                
                # 获取工具
                tool = self._get_tool_by_name(subtask, tool_name)
                
                # 创建步骤目录
                step_dir = self.img_tree_dir / f"step{step_idx}-{subtask.replace(' ', '_')}"
                step_dir.mkdir(exist_ok=True)
                
                tool_dir = step_dir / f"tool-{tool_name}"
                output_dir = tool_dir / "0-img"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 执行工具
                self.logger.info(f"  Severity of {self._get_degradation(subtask)} of {subtask}@{tool_name} is medium.")
                
                tool(
                    input_dir=self.current_input_dir,
                    output_dir=output_dir,
                    silent=True
                )
                
                # 获取输出图像
                output_files = list(output_dir.glob("*"))
                if not output_files:
                    raise RuntimeError(f"工具 {tool_name} 没有生成输出文件")
                
                output_path = output_files[0]
                
                # 更新当前输入
                self.current_input_dir = output_dir
                self.current_input_path = output_path
                
                execution_path.append((subtask, tool_name))
            
            # 5. 记录最终结果（与 IRAgent 的 Restoration result 部分对应）
            result_name = "-".join([f"{subtask}@{tool}" for subtask, tool in execution_path])
            self.logger.info(f"Restoration result: {result_name}.")
            
            # 6. 复制最终结果
            result_path = self.work_dir / "result.png"
            shutil.copy(self.current_input_path, result_path)
            
            return result_path
            
        finally:
            self._move_original_to_backup()
    
    def _get_degradation(self, subtask: str) -> str:
        """根据子任务获取对应的降质类型"""
        subtask_degra_dict = {
            "super-resolution": "low resolution",
            "denoising": "noise",
            "motion deblurring": "motion blur",
            "defocus deblurring": "defocus blur",
            "dehazing": "haze",
            "deraining": "rain",
            "brightening": "dark",
            "jpeg compression artifact removal": "jpeg compression artifact",
        }
        return subtask_degra_dict.get(subtask, subtask)
    
    def _generate_insights(self) -> str:
        """生成模拟的 Insights（格式与 IRAgent 相同）"""
        insights_map = {
            "oldpic": "For old photos, it's recommended to apply denoising first to remove noise artifacts, then super-resolution to enhance details.",
            "weather": "For weather-degraded images, deraining should be applied before dehazing to avoid interference.",
            "dark": "For low-light images, denoising should be performed before brightening to prevent noise amplification.",
            "defocus": "Defocus blur can be effectively removed using dedicated deblurring models.",
            "motion": "Motion blur removal works best with models trained specifically for this degradation.",
            "full": "For multiple degradations, process noise first, then super-resolution, and finally brightness enhancement.",
            "haze_bright": "Remove haze first, then enhance brightness for optimal results."
        }
        return insights_map.get(self.pipeline_name, "Standard processing order applies.")
    
    def _move_original_to_backup(self):
        """将原始图像移动到backup文件夹"""
        if not self.move_original_to_backup:
            return
        
        try:
            original_path = self.input_path
            if original_path.exists():
                backup_dir = self.work_dir / "backup"
                backup_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = original_path.stem
                extension = original_path.suffix
                new_name = f"{filename}_original_{timestamp}{extension}"
                new_path = backup_dir / new_name
                
                shutil.move(str(original_path), str(new_path))
                print(f"\n原始图像已移动到: {new_path}")
            else:
                print(f"\n警告: 原始图像不存在: {original_path}")
                
        except Exception as e:
            print(f"\n警告: 移动原始图像时出错: {e}")


def get_pipeline_by_name(pipeline_name: str) -> Tuple[List[Tuple[str, str]], str]:
    """根据名称返回对应的流水线配置和显示名称"""
    
    pipelines = {
        "oldpic": {
            "name": "oldpic",
            "display": "老照片修复",
            "steps": [
                ("denoising", "swinir_15"),
                ("super-resolution", "xrestormer")
            ]
        },
        "weather": {
            "name": "weather",
            "display": "天气魔法",
            "steps": [
                ("deraining", "xrestormer"),
                ("dehazing", "refinednet")
            ]
        },
        "dark": {
            "name": "dark",
            "display": "夜视之眼",
            "steps": [
                ("denoising", "swinir_50"),
                ("brightening", "constant_shift")
            ]
        },
        "defocus": {
            "name": "defocus",
            "display": "去散焦模糊",
            "steps": [
                ("defocus deblurring", "drbnet")
            ]
        },
        "motion": {
            "name": "motion",
            "display": "去运动模糊",
            "steps": [
                ("motion deblurring", "xrestormer")
            ]
        },
        "full": {
            "name": "full",
            "display": "综合修复",
            "steps": [
                ("denoising", "swinir_50"),
                ("super-resolution", "edsr"),
                ("brightening", "zero_dce")
            ]
        },
        "haze_bright": {
            "name": "haze_bright",
            "display": "去雾+亮度",
            "steps": [
                ("dehazing", "aod_net"),
                ("brightening", "constant_shift")
            ]
        }
    }
    
    pipeline_key = pipeline_name.replace("pipeline_", "")
    
    if pipeline_key not in pipelines:
        available = list(pipelines.keys())
        raise ValueError(f"未知的流水线名称: '{pipeline_name}'。可用的流水线: {available}")
    
    pipeline_info = pipelines[pipeline_key]
    print(f"选择流水线: {pipeline_info['display']}")
    return pipeline_info["steps"], pipeline_info["name"]


def list_available_pipelines():
    """列出所有可用的流水线"""
    pipelines = {
        "oldpic": "老照片修复 (去噪 + 超分)",
        "weather": "天气魔法 (去雨 + 去雾)",
        "dark": "夜视之眼 (去噪 + 亮度增强)",
        "defocus": "去散焦模糊",
        "motion": "去运动模糊",
        "full": "综合修复 (去噪 + 超分 + 亮度)",
        "haze_bright": "去雾 + 亮度增强"
    }
    
    print("\n可用的流水线:")
    for name, desc in pipelines.items():
        print(f"  {name:<12} - {desc}")
    print()


def main():
    parser = argparse.ArgumentParser(description='直接执行图像修复流水线')
    
    parser.add_argument('--pipeline', '-p', 
                       type=str,
                       default='dark',
                       help='要执行的流水线名称 (默认: dark)')
    
    parser.add_argument('--input', '-i',
                       type=str,
                       default='dataset/example.png',
                       help='输入图像路径 (默认: dataset/example.png)')
    
    parser.add_argument('--output', '-o',
                       type=str,
                       default='output',
                       help='输出根目录 (默认: output)')
    
    parser.add_argument('--list', '-l',
                       action='store_true',
                       help='列出所有可用的流水线')
    
    parser.add_argument('--custom', '-c',
                       type=str,
                       nargs='+',
                       help='自定义流水线，格式: subtask1 tool1 subtask2 tool2 ...')
    
    parser.add_argument('--name', '-n',
                       type=str,
                       default=None,
                       help='自定义输出目录名称（不包含时间戳）')
    
    parser.add_argument('--no-backup', 
                       action='store_true',
                       help='不将原图移动到backup文件夹')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_pipelines()
        return
    
    if args.custom:
        if len(args.custom) % 2 != 0:
            raise ValueError("自定义流水线参数必须成对出现: subtask tool [subtask tool ...]")
        
        pipeline = []
        for i in range(0, len(args.custom), 2):
            subtask = args.custom[i].replace('_', ' ')
            tool = args.custom[i+1]
            pipeline.append((subtask, tool))
        
        if args.name:
            pipeline_name = args.name
        else:
            tool_names = [tool for _, tool in pipeline]
            pipeline_name = "custom_" + "_".join(tool_names)
        
        print(f"使用自定义流水线: {pipeline}")
        print(f"流水线名称: {pipeline_name}")
        
    else:
        try:
            pipeline, pipeline_name = get_pipeline_by_name(args.pipeline)
        except ValueError as e:
            print(e)
            list_available_pipelines()
            return
    
    input_image = Path(args.input)
    if not input_image.exists():
        print(f"错误: 输入图像不存在: {input_image}")
        return
    
    output_root = Path(args.output)
    
    print(f"输入图像: {input_image}")
    print(f"输出根目录: {output_root}")
    print(f"流水线: {pipeline}")
    print(f"备份原图: {'否' if args.no_backup else '是'}")
    print("-" * 60)
    
    try:
        pipeline_runner = DirectPipeline(
            input_path=input_image,
            output_dir=output_root,
            pipeline=pipeline,
            pipeline_name=pipeline_name,
            move_original_to_backup=not args.no_backup
        )
        
        result = pipeline_runner.run()
        print(f"\n成功! 结果保存在: {result}")
        print(f"日志保存在: {pipeline_runner.workflow_path}")
        
    except Exception as e:
        print(f"执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()