from pathlib import Path
from .iragent import IRAgent
import argparse
import shutil
from datetime import datetime
import os

def main():
    parser = argparse.ArgumentParser(description='Image Restoration Agent')
    parser.add_argument('--degradations', type=str,
                        help='Degradations to process, separated by comma. Example: "low resolution,noise"')
    parser.add_argument('--input', type=str, default='dataset/example.png',
                        help='Input image path')
    parser.add_argument('--output', type=str, default='output',
                        help='Output directory')
    parser.add_argument('--interactive', action='store_true',
                        help='Enable interactive mode for iterative refinement')
    parser.add_argument('--max-iterations', type=int, default=5,
                        help='Maximum number of iterations in interactive mode')
    
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    # 创建备份目录（如果不存在）
    backup_dir = Path("dataset/backup")
    backup_dir.mkdir(exist_ok=True)

    # 处理用户指定的降质类型
    manual_degradations = None
    
    try:
        if args.degradations:
            degradations = [deg.strip() for deg in args.degradations.split(',')]
            
            valid_degradations = set([
                "low resolution", "noise", "motion blur", "defocus blur", 
                "haze", "rain", "dark", "jpeg compression artifact"
            ])
            for deg in degradations:
                if deg not in valid_degradations:
                    print(f"Error: Invalid degradation '{deg}'. Valid options are: {list(valid_degradations)}")
                    return
            
            manual_degradations = degradations
            print(f"Using manual degradations: {manual_degradations}")
        else:
            print("Auto-detecting degradations...")
        
        # 创建 agent 实例
        agent = IRAgent(
            input_path=input_path, 
            output_dir=output_dir,
            evaluate_degradation_by="depictqa",
            with_retrieval=True,
            with_reflection=True,
            reflect_by="depictqa",
            with_rollback=True,
            silent=False,
            manual_degradations=manual_degradations,
            interactive=args.interactive,  # 新增参数
            max_iterations=args.max_iterations  # 新增参数
        )
        
        # 运行 agent（现在会处理交互式迭代）
        agent.run_with_interaction()
            
    finally:
        # 移动原始文件到备份目录
        if input_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = input_path.stem
            extension = input_path.suffix
            new_name = f"{filename}_processed_{timestamp}{extension}"
            new_path = backup_dir / new_name
            shutil.move(str(input_path), str(new_path))
            print(f"Original image moved to: {new_path}")
            
if __name__ == "__main__":
    main()
