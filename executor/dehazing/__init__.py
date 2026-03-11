import os

from ..tool import Tool
from ..multitask_tools import *


__all__ = ['dehazing_toolbox']


class DehazeFormer(Tool):
    """[Vision Transformers for Single Image Dehazing (TIP 2023)](https://doi.org/10.1109/TIP.2023.3256763)"""    

    def __init__(self):
        super().__init__(
            tool_name="dehazeformer",
            subtask="dehazing",
            work_dir="DehazeFormer",
            script_rel_path="inference.py"
        )

    def _get_cmd_opts(self) -> list[str]:
        return [
            "--data_dir", self.input_dir,
            "--result_dir", self.output_dir,
            # "--save_dir", '/root/autodl-tmp/AgenticIR/executor/dehazing/tools/DehazeFormer/saved_models'
            "--save_dir", '/root/autodl-tmp/AgenticIR/executor/dehazing/tools/DehazeFormer/saved_models/outdoor'
        ]
    

class RIDCP(Tool):
    """[RIDCP: Revitalizing Real Image Dehazing via High-Quality Codebook Priors (CVPR 2023)](https://openaccess.thecvf.com/content/CVPR2023/papers/Wu_RIDCP_Revitalizing_Real_Image_Dehazing_via_High-Quality_Codebook_Priors_CVPR_2023_paper.pdf)"""    

    def __init__(self):
        super().__init__(
            tool_name="ridcp",
            subtask="dehazing",
            work_dir="RIDCP_dehazing",
            script_rel_path="inference_ridcp.py"
        )

    def _get_cmd_opts(self) -> list[str]:
        return [
            "-i", self.input_dir,
            "-o", self.output_dir,
            "-w", 'RIDCP_dehazing/pretrained_models/pretrained_RIDCP.pth',
            "--use_weight",
            "--alpha", "-21.25"
        ]
    
# class RefineDNet(Tool):
#     """[Vision Transformers for Single Image Dehazing (TIP 2023)](https://doi.org/10.1109/TIP.2023.3256763)"""    

#     def __init__(self):
#         super().__init__(
#             tool_name="refinednet",
#             subtask="dehazing",
#             work_dir="RefineDNet",
#             script_rel_path="quick_test.py"
#         )

#     def _get_cmd_opts(self) -> list[str]:
#         return [
#             "--dataroot", self.input_dir,
#             "--save_image",
#             "--dataset_mode", "single",
#             "--results_dir", self.output_dir,
#             "--name",'refined_DCP_outdoor',
#             "--model",'refined_DCP',
#             "--phase",'test',
#             "--preprocess", 'none',
#             "--method_name", 'refined_DCP_outdoor_ep_60',
#             "--epoch", 60
#         ]


class RefineDNet(Tool):
    """[Vision Transformers for Single Image Dehazing (TIP 2023)]"""    

    def __init__(self):
        super().__init__(
            tool_name="refinednet",
            subtask="dehazing",
            work_dir="RefineDNet",
            script_rel_path="quick_test.py"
        )

    def _get_cmd_opts(self) -> list[str]:
        # 获取输入图像
        input_files = list(self.input_dir.glob("*.png")) + \
                     list(self.input_dir.glob("*.jpg")) + \
                     list(self.input_dir.glob("*.jpeg"))
        
        if not input_files:
            raise FileNotFoundError(f"No input image found in {self.input_dir}")
        
        return [
            "--dataroot", str(self.input_dir),
            "--save_image",
            "--dataset_mode", "single",
            "--results_dir", str(self.output_dir),
            "--name", "refined_DCP_outdoor",
            "--model", "refined_DCP",
            "--phase", "test",
            "--preprocess", "none",
            "--method_name", "refined_DCP_outdoor_ep_60",
            "--epoch", "60"
        ]

    def _invoke(self) -> None:
        """重写 _invoke 方法，处理图像尺寸检查失败的情况"""
        self._preprocess()
        
        # 检查输入图像尺寸
        input_files = list(self.input_dir.glob("*.png")) + \
                     list(self.input_dir.glob("*.jpg")) + \
                     list(self.input_dir.glob("*.jpeg"))
        
        if input_files:
            import cv2
            img = cv2.imread(str(input_files[0]))
            if img is not None:
                h, w = img.shape[:2]
                min_size = min(h, w)
                print(f"Input image size: {w}x{h}, min size: {min_size}")
                
                # 如果图像太小，直接复制输入作为输出
                if min_size < 256:
                    print(f"Image too small ({min_size} < 256) for RefineDNet. Copying input as output.")
                    import shutil
                    output_file = self.output_dir / "output.png"
                    shutil.copy2(input_files[0], output_file)
                    print(f"Created output by copying input: {output_file}")
                    return
        
        # 正常执行命令
        opts = self._get_cmd_opts()
        cmd = [
            "conda", "run", "-n", "dehazeformer", "python",
            str(self.script_path)
        ] + opts
        
        print("下面输出cmd:")
        print(' '.join(str(c) for c in cmd))
        
        import subprocess
        result = subprocess.run(cmd, cwd=self.work_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise RuntimeError(f"Tool execution failed: {result.stderr}")
        
        print(f"Command succeeded")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        
        self._postprocess()

    def _postcheck(self) -> None:
        """检查输出文件"""
        output_dir = self.output_dir
        
        if not output_dir.exists():
            raise FileNotFoundError(f"Output directory {output_dir} does not exist.")
        
        # 查找输出文件
        output_files = list(output_dir.glob("*_dehz.png")) + \
                      list(output_dir.glob("*.png")) + \
                      list(output_dir.glob("*.jpg"))
        
        # 检查子目录
        subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
        for subdir in subdirs:
            output_files.extend(list(subdir.glob("*_dehz.png")))
            output_files.extend(list(subdir.glob("*.png")))
        
        print(f"Found output files: {[f.name for f in output_files]}")
        
        if not output_files:
            # 如果没有输出文件，检查是否因为尺寸问题跳过了
            print("No output files found. Checking if image was too small...")
            input_files = list(self.input_dir.glob("*.png")) + \
                         list(self.input_dir.glob("*.jpg"))
            
            if input_files:
                import cv2
                img = cv2.imread(str(input_files[0]))
                if img is not None:
                    h, w = img.shape[:2]
                    if min(h, w) < 256:
                        # 如果是因为尺寸问题，这里应该有复制操作
                        # 但为了安全，再次复制
                        import shutil
                        output_file = output_dir / "output.png"
                        shutil.copy2(input_files[0], output_file)
                        print(f"Image was too small. Copied input as output: {output_file}")
                        self.output_path = output_file
                        return
            
            raise FileNotFoundError(f"No output image found in {output_dir}")
        
        # 选择输出文件
        dehz_files = [f for f in output_files if "_dehz" in f.name]
        if dehz_files:
            self.output_path = dehz_files[0]
        else:
            output_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            self.output_path = output_files[0]
        
        # 创建标准的 output.png
        standard_output = output_dir / "output.png"
        if not standard_output.exists():
            import shutil
            shutil.copy2(self.output_path, standard_output)
            print(f"Created standard output: {standard_output}")
    
class VIFNet(Tool):
    """VIFNet: An End-to-end Visible-Infrared Fusion Network for Image Dehazing
    
    Args:
        pretrained_on (str): 预训练数据集，可选 'airsim' 或 'nh'
    """

    def __init__(self, pretrained_on: str):
        super().__init__(
            tool_name=f"vifnet_{pretrained_on}",
            subtask="dehazing",
            work_dir="VIFNet",
            script_rel_path="test.py",  # 如果有专门的推理脚本
        )
        
        opt_dict = {
            'airsim': {
                'tool_name': 'vifnet_airsim',
                'model_path': '/root/autodl-tmp/AgenticIR/executor/dehazing/tools/VIFNet/trained_models1.0/vifnet.pk.best.best'
            },
            'nh': {
                'tool_name': 'vifnet_nh', 
                'model_path':'/root/autodl-tmp/AgenticIR/executor/dehazing/tools/VIFNet/trained_modelsNH/vifnet.pk.best.best'  
            }
        }   
        self.model_name = opt_dict[pretrained_on]
            
        info = opt_dict[pretrained_on]
      
        self.model_path = info['model_path']
    def _get_cmd_opts(self) -> list[str]:
        return [
            "--haze_dir", self.input_dir,  # RGB输入图像目录  在父类Tool中设置
            "--nir_dir", self.ir_input_dir,  # IR输入图像目录
            "--output_dir", self.output_dir,  # 输出结果目录
            '--model_path',self.model_path
            ]
    
    @property
    def ir_input_dir(self):
        """NIR图像专用输入目录"""
        return "/root/autodl-tmp/AgenticIR/test_tool/input_IR"
       
        
        
subtask = 'dehazing'
dehazing_toolbox = [
    # XRestormer(subtask=subtask),
    # RIDCP(),
    DehazeFormer(),
    RefineDNet(),
    VIFNet(pretrained_on='airsim'),
    VIFNet(pretrained_on='nh'),
    # MAXIM(subtask=subtask),
]
