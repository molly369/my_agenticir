# from pathlib import Path
# from .iragent import IRAgent
# import argparse
# import shutil
# from datetime import datetime
# import os

# def main():
#     parser = argparse.ArgumentParser(description='Image Restoration Agent')
#     # 使用字符串参数而不是选项列表
#     parser.add_argument('--degradations', type=str,
#                         help='Degradations to process, separated by comma. Example: "low resolution,noise"')
#     # 添加输入和输出路径参数
#     parser.add_argument('--input', type=str, default='dataset/example.png',
#                         help='Input image path')
#     parser.add_argument('--output', type=str, default='output',
#                         help='Output directory')
    
#     args = parser.parse_args()

#     input_path = Path(args.input).resolve()
#     output_dir = Path(args.output).resolve()

#     # 创建备份目录（如果不存在）
#     backup_dir = Path("dataset/backup")
#     backup_dir.mkdir(exist_ok=True)

#     agent = IRAgent(
#         input_path=input_path, 
#         output_dir=output_dir,
#         evaluate_degradation_by="depictqa",
#         with_retrieval=True,
#         with_reflection=True,
#         reflect_by="depictqa",
#         with_rollback=True,
#         silent=False,
#         manual_degradations=manual_degradations  # 确保这里传入了值
#     )
    
#     try:
#         # 如果有命令行参数，直接使用指定的降质类型
#         if args.degradations:
#             # 使用逗号分隔参数
#             degradations = [deg.strip() for deg in args.degradations.split(',')]
            
#             # 验证降质类型
#             valid_degradations = set(agent.degra_subtask_dict.keys())
#             for deg in degradations:
#                 if deg not in valid_degradations:
#                     print(f"Error: Invalid degradation '{deg}'. Valid options are: {list(valid_degradations)}")
#                     return
            
#             # 将降质类型转换为对应的子任务
#             # plan = [agent.degra_subtask_dict[deg] for deg in degradations]
#             # print(f"Using manual plan: {plan}")
#             # agent.run(plan=plan)
#             agenda = [agent.degra_subtask_dict[deg] for deg in degradations]
            
#             # 使用GPT4基于经验确定最佳执行顺序
#             plan = agent.schedule(agenda)
#             print(f"Using GPT4-scheduled plan: {plan}")
#             agent.run(plan=plan)
            
            
            
            
#         else:
#             print("Auto-detecting degradations...")
#             agent.run()
            
#     finally:
#         # 无论程序是否成功运行，都会执行这部分代码
#         # 重命名原始图像以避免冲突
#         if input_path.exists():
#             # 使用时间戳创建唯一文件名
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             filename = input_path.stem
#             extension = input_path.suffix
#             new_name = f"{filename}_processed_{timestamp}{extension}"
#             new_path = backup_dir / new_name
            
#             # 移动文件到备份目录
#             shutil.move(str(input_path), str(new_path))
#             print(f"Original image moved to: {new_path}")
            
# if __name__ == "__main__":
#     main() 
# # python -m pipeline.infer --degradations "low resolution,noise"
# #（List of degradations to process: "low resolution", "noise", "motion blur", "defocus blur", "haze", "rain", "dark", "jpeg compression artifact"）

from pathlib import Path
from .iragent import IRAgent
import argparse
import shutil
from datetime import datetime
import os

def main():
    parser = argparse.ArgumentParser(description='Image Restoration Agent')
    # 使用字符串参数而不是选项列表
    parser.add_argument('--degradations', type=str,
                        help='Degradations to process, separated by comma. Example: "low resolution,noise"')
    # 添加输入和输出路径参数
    parser.add_argument('--input', type=str, default='dataset/example.png',
                        help='Input image path')
    parser.add_argument('--output', type=str, default='output',
                        help='Output directory')
    
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    # 创建备份目录（如果不存在）
    backup_dir = Path("dataset/backup")
    backup_dir.mkdir(exist_ok=True)

    # 处理用户指定的降质类型
    manual_degradations = None  # 先初始化为 None
    
    try:
        # 如果有命令行参数，直接使用指定的降质类型
        if args.degradations:
            # 使用逗号分隔参数
            degradations = [deg.strip() for deg in args.degradations.split(',')]
            
            # 验证降质类型
            valid_degradations = set([
                "low resolution", "noise", "motion blur", "defocus blur", 
                "haze", "rain", "dark", "jpeg compression artifact"
            ])
            for deg in degradations:
                if deg not in valid_degradations:
                    print(f"Error: Invalid degradation '{deg}'. Valid options are: {list(valid_degradations)}")
                    return
            
            manual_degradations = degradations  # 赋值给变量
            print(f"Using manual degradations: {manual_degradations}")
            
        else:
            print("Auto-detecting degradations...")
        
        # 创建 agent 实例，传入 manual_degradations
        agent = IRAgent(
            input_path=input_path, 
            output_dir=output_dir,
            evaluate_degradation_by="depictqa",
            with_retrieval=True,
            with_reflection=True,
            reflect_by="depictqa",
            with_rollback=True,
            silent=False,
            manual_degradations=manual_degradations  # 现在这个变量有值了
        )
        
        # 运行 agent
        if manual_degradations:
            # 将降质类型转换为对应的子任务
            agenda = [agent.degra_subtask_dict[deg] for deg in manual_degradations]
            
            # 使用GPT4基于经验确定最佳执行顺序
            plan = agent.schedule(agenda)
            print(f"Using GPT4-scheduled plan: {plan}")
            agent.run(plan=plan)
        else:
            agent.run()
            
    finally:
        # 无论程序是否成功运行，都会执行这部分代码
        # 重命名原始图像以避免冲突
        if input_path.exists():
            # 使用时间戳创建唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = input_path.stem
            extension = input_path.suffix
            new_name = f"{filename}_processed_{timestamp}{extension}"
            new_path = backup_dir / new_name
            
            # 移动文件到备份目录
            shutil.move(str(input_path), str(new_path))
            print(f"Original image moved to: {new_path}")
            
if __name__ == "__main__":
    main()