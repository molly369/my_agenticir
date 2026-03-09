# """
# degradation_analyzer_simple.py
# 专门用于分析单张图像降质类型和程度的简化脚本 - 无日志版本
# """

# from pathlib import Path
# import argparse
# import json
# import sys
# import logging
# import shutil
# from datetime import datetime

# # 添加项目路径到系统路径
# project_root = Path(__file__).parent.parent
# sys.path.append(str(project_root))

# # 导入必要的模块
# from llm import DepictQA


# class SilentDepictQA(DepictQA):
#     """重写DepictQA类，禁用所有日志输出"""
    
#     def __call__(self, *args, **kwargs):
#         original_level = self.logger.level
#         self.logger.setLevel(logging.ERROR)
#         result = super().__call__(*args, **kwargs)
#         self.logger.setLevel(original_level)
#         return result


# class DegradationAnalyzer:
#     """
#     图像降质分析器 - 完全静默版本
#     """
    
#     def __init__(self):
#         """初始化分析器"""
#         self.logger = logging.getLogger("silent_logger")
#         self.logger.addHandler(logging.NullHandler())
#         self.logger.setLevel(logging.ERROR)
        
#         self.depictqa = SilentDepictQA(logger=self.logger, silent=True)
        
#         # DepictQA 完整的降质类型列表
#         self.degradations = [
#             "motion blur",              # 运动模糊
#             "defocus blur",             # 失焦模糊
#             "rain",                      # 雨
#             "haze",                      # 雾霾
#             "dark",                      # 过暗
#             "noise",                     # 噪声
#             "jpeg compression artifact", # JPEG压缩伪影
#             "low resolution"             # 低分辨率  ← 添加了这一项
#         ]
        
#         self.levels = ["very low", "low", "medium", "high", "very high"]
        
#         self.level_to_score = {
#             "very low": 1,
#             "low": 2,
#             "medium": 3,
#             "high": 4,
#             "very high": 5
#         }
    
#     def find_latest_result(self):
#         """获取最新result.png的路径"""
#         output_dir = Path("/root/autodl-tmp/AgenticIR/output")
        
#         if not output_dir.exists():
#             return None
        
#         subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
#         if not subdirs:
#             return None
        
#         latest_dir = max(subdirs, key=lambda d: d.stat().st_mtime)
#         result_path = latest_dir / "result.png"
        
#         return result_path if result_path.exists() else None
    
#     def analyze(self, use_latest: bool = False) -> dict:
#         """
#         分析图像的降质情况
        
#         Args:
#             use_latest: 是否强制使用最新的result.png并复制到analyze_waiting.png
#                         如果为False但analyze_waiting.png不存在，也会自动使用最新的result.png
#         """
#         analyze_waiting_path = Path("/root/autodl-tmp/AgenticIR/dataset/analyze_waiting.png")
        
#         # 确定要分析的图像
#         if use_latest or not analyze_waiting_path.exists():
#             # 强制使用最新result.png 或者 analyze_waiting.png不存在时自动使用
#             latest_path = self.find_latest_result()
#             if not latest_path:
#                 raise FileNotFoundError("未找到最新的result.png")
            
#             # 复制到analyze_waiting.png
#             analyze_waiting_path.parent.mkdir(parents=True, exist_ok=True)
#             shutil.copy2(latest_path, analyze_waiting_path)
#             image_path = analyze_waiting_path
#             print(f"✅ 已复制最新图像到: {image_path}")
#         else:
#             # 使用现有的analyze_waiting.png
#             image_path = analyze_waiting_path
#             print(f"✅ 使用现有的analyze_waiting.png: {image_path}")
        
#         # 调用 DepictQA 进行评估
#         print(f"🔍 正在分析图像: {image_path.name}")
        
#         # 尝试不同的参数传递方式
#         try:
#             # 方法1：直接传Path对象
#             evaluation_str = self.depictqa(img_path=image_path, task="eval_degradation")
#         except TypeError:
#             try:
#                 # 方法2：传字符串
#                 evaluation_str = self.depictqa(img_path=str(image_path), task="eval_degradation")
#             except TypeError:
#                 # 方法3：可能参数名不同
#                 evaluation_str = self.depictqa(image_path=image_path, task="eval_degradation")
        
#         # 解析结果
#         if isinstance(evaluation_str, str):
#             evaluation = eval(evaluation_str)
#         else:
#             evaluation = evaluation_str
        
#         # 构建结果字典
#         result = {
#             "image_path": str(image_path),
#             "image_name": image_path.name,
#             "degradations": {},
#             "degradation_scores": {},
#             "severe_degradations": [],
#             "all_degradations_detected": [],  # 记录实际检测到的所有降质类型
#             "timestamp": datetime.now().isoformat()
#         }
        
#         # 初始化所有降质类型为默认值（如果DepictQA没有返回某个类型）
#         default_severity = "very low"
#         default_score = 1
        
#         for degradation in self.degradations:
#             result["degradations"][degradation] = default_severity
#             result["degradation_scores"][degradation] = default_score
        
#         # 更新实际检测到的降质类型
#         for degradation, severity in evaluation:
#             if degradation in result["degradations"]:
#                 result["degradations"][degradation] = severity
#                 score = self.level_to_score[severity]
#                 result["degradation_scores"][degradation] = score
#                 result["all_degradations_detected"].append({
#                     "degradation": degradation,
#                     "severity": severity,
#                     "score": score
#                 })
                
#                 # 记录严重的降质（medium及以上）
#                 if score >= 3:
#                     result["severe_degradations"].append({
#                         "degradation": degradation,
#                         "severity": severity,
#                         "score": score
#                     })
        
#         return result
    
#     def print_results(self, result: dict):
#         """打印分析结果"""
#         print("\n" + "="*70)
#         print(f"📸 图像: {result['image_name']}")
#         print("="*70)
#         print("\n📊 降质分析结果:")
#         print("-"*50)
        
#         markers = {"very low": "✔", "low": "✔", "medium": "▲", "high": "✖", "very high": "✖"}
        
#         # 按分数排序显示
#         sorted_degradations = sorted(
#             result["degradation_scores"].items(), 
#             key=lambda x: x[1], 
#             reverse=True
#         )
        
#         for degradation, score in sorted_degradations:
#             severity = result["degradations"][degradation]
#             marker = markers.get(severity, "?")
#             # 突出显示低分辨率
#             if degradation == "low resolution":
#                 print(f"  {marker} {degradation:25}: {severity.upper()} ({score}/5) 📏")
#             else:
#                 print(f"  {marker} {degradation:25}: {severity.upper()} ({score}/5)")
        
#         # 显示严重降质汇总
#         if result["severe_degradations"]:
#             print("\n🔴 严重降质检测 (分数≥3):")
#             for item in result["severe_degradations"]:
#                 warning = "⚠️" if item["degradation"] == "low resolution" else "•"
#                 print(f"    {warning} {item['degradation']}: {item['severity']} ({item['score']}/5)")
#         else:
#             print("\n✅ 未检测到严重降质")
        
#         # 显示总体评估
#         avg_score = sum(result["degradation_scores"].values()) / len(result["degradation_scores"])
#         print(f"\n📈 总体降质评分: {avg_score:.2f}/5")
        
#         if avg_score <= 2:
#             quality = "优质"
#             color = "✅"
#         elif avg_score <= 3:
#             quality = "良好"
#             color = "👍"
#         elif avg_score <= 4:
#             quality = "一般"
#             color = "👌"
#         else:
#             quality = "较差"
#             color = "⚠️"
        
#         print(f"{color} 图像质量评估: {quality}")
#         print("\n" + "="*70)
    
#     def get_formatted_output(self, result: dict) -> str:
#         """获取格式化的输出字符串"""
#         lines = []
#         lines.append("\n" + "="*70)
#         lines.append(f"📸 图像: {result['image_name']}")
#         lines.append("="*70)
#         lines.append("\n📊 降质分析结果:")
#         lines.append("-"*50)
        
#         markers = {"very low": "✔", "low": "✔", "medium": "▲", "high": "✖", "very high": "✖"}
        
#         sorted_degradations = sorted(
#             result["degradation_scores"].items(), 
#             key=lambda x: x[1], 
#             reverse=True
#         )
        
#         for degradation, score in sorted_degradations:
#             severity = result["degradations"][degradation]
#             marker = markers.get(severity, "?")
#             lines.append(f"  {marker} {degradation:25}: {severity.upper()} ({score}/5)")
        
#         if result["severe_degradations"]:
#             lines.append("\n🔴 严重降质检测:")
#             for item in result["severe_degradations"]:
#                 lines.append(f"    • {item['degradation']}: {item['severity']} ({item['score']}/5)")
#         else:
#             lines.append("\n✅ 未检测到严重降质")
        
#         avg_score = sum(result["degradation_scores"].values()) / len(result["degradation_scores"])
#         lines.append(f"\n📈 总体降质评分: {avg_score:.2f}/5")
#         lines.append("\n" + "="*70)
        
#         return "\n".join(lines)


# def main():
#     parser = argparse.ArgumentParser(description="分析图像的降质类型和程度")
#     parser.add_argument("--latest", "-l", action="store_true", 
#                        help="强制使用最新的result.png并复制到analyze_waiting.png")
#     parser.add_argument("--output", "-o", type=str, help="保存结果到JSON文件")
#     parser.add_argument("--quiet", "-q", action="store_true", help="只输出JSON结果")
    
#     args = parser.parse_args()
    
#     try:
#         analyzer = DegradationAnalyzer()
#         result = analyzer.analyze(use_latest=args.latest)
        
#         if args.quiet:
#             # 只输出JSON
#             print(json.dumps(result, ensure_ascii=False, indent=2))
#         else:
#             # 输出格式化结果
#             analyzer.print_results(result)
        
#         if args.output:
#             with open(args.output, "w", encoding="utf-8") as f:
#                 json.dump(result, f, ensure_ascii=False, indent=2)
#             if not args.quiet:
#                 print(f"\n✅ 结果已保存到: {args.output}")
        
#         return result
        
#     except Exception as e:
#         print(f"❌ 错误: {e}")
#         return None


# if __name__ == "__main__":
#     main()

"""
degradation_analyzer_simple.py
专门用于分析单张图像降质类型和程度的简化脚本 - 无日志版本
"""

from pathlib import Path
import argparse
import json
import sys
import logging
import shutil
from datetime import datetime

# 添加项目路径到系统路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入必要的模块
from llm import DepictQA


class SilentDepictQA(DepictQA):
    """重写DepictQA类，禁用所有日志输出"""
    
    def __call__(self, *args, **kwargs):
        original_level = self.logger.level
        self.logger.setLevel(logging.ERROR)
        result = super().__call__(*args, **kwargs)
        self.logger.setLevel(original_level)
        return result


class DegradationAnalyzer:
    """
    图像降质分析器 - 完全静默版本
    """
    
    def __init__(self):
        """初始化分析器"""
        self.logger = logging.getLogger("silent_logger")
        self.logger.addHandler(logging.NullHandler())
        self.logger.setLevel(logging.ERROR)
        
        self.depictqa = SilentDepictQA(logger=self.logger, silent=True)
        
        # DepictQA 完整的降质类型列表
        self.degradations = [
            "motion blur",              # 运动模糊
            "defocus blur",             # 失焦模糊
            "rain",                      # 雨
            "haze",                      # 雾霾
            "dark",                      # 过暗
            "noise",                     # 噪声
            "jpeg compression artifact", # JPEG压缩伪影
            "low resolution"             # 低分辨率
        ]
        
        self.levels = ["very low", "low", "medium", "high", "very high"]
        
        self.level_to_score = {
            "very low": 1,
            "low": 2,
            "medium": 3,
            "high": 4,
            "very high": 5
        }
        
        # 定义降质类型到五个质量维度的映射权重
        # 每个降质类型对不同维度的影响权重（总和为1）
        self.degradation_to_dimension = {
            "motion blur": {
                "sharpness": 0.7,      # 运动模糊主要影响清晰度
                "structure": 0.3,       # 也影响结构完整性
                "color": 0.0,
                "noise": 0.0,
                "detail": 0.0
            },
            "defocus blur": {
                "sharpness": 0.8,       # 失焦模糊主要影响清晰度
                "detail": 0.2,           # 也影响细节保留
                "color": 0.0,
                "noise": 0.0,
                "structure": 0.0
            },
            "rain": {
                "detail": 0.4,           # 雨影响细节可见性
                "structure": 0.3,         # 也影响结构完整性
                "sharpness": 0.3,         # 也影响清晰度
                "color": 0.0,
                "noise": 0.0
            },
            "haze": {
                "sharpness": 0.4,         # 雾霾影响清晰度
                "color": 0.3,              # 影响色彩还原
                "detail": 0.3,              # 影响细节
                "noise": 0.0,
                "structure": 0.0
            },
            "dark": {
                "color": 0.5,              # 过暗主要影响色彩
                "detail": 0.3,              # 也影响细节
                "noise": 0.2,               # 暗光可能带来噪声
                "sharpness": 0.0,
                "structure": 0.0
            },
            "noise": {
                "noise": 0.8,               # 噪声主要影响噪声控制
                "detail": 0.2,               # 也影响细节
                "color": 0.0,
                "sharpness": 0.0,
                "structure": 0.0
            },
            "jpeg compression artifact": {
                "detail": 0.5,               # 压缩伪影影响细节
                "structure": 0.3,             # 也影响结构
                "noise": 0.2,                  # 块效应可视为一种噪声
                "color": 0.0,
                "sharpness": 0.0
            },
            "low resolution": {
                "detail": 0.6,               # 低分辨率主要影响细节
                "sharpness": 0.4,             # 也影响清晰度
                "color": 0.0,
                "noise": 0.0,
                "structure": 0.0
            }
        }
        
        # 五个质量维度
        self.quality_dimensions = [
            "sharpness",     # 清晰度
            "color",         # 色彩还原
            "noise",         # 噪声控制
            "structure",     # 结构完整
            "detail"         # 细节保留
        ]
        
        self.dimension_names_cn = {
            "sharpness": "清晰度",
            "color": "色彩还原",
            "noise": "噪声控制",
            "structure": "结构完整",
            "detail": "细节保留"
        }
    
    def find_latest_result(self):
        """获取最新result.png的路径"""
        output_dir = Path("/root/autodl-tmp/AgenticIR/output")
        
        if not output_dir.exists():
            return None
        
        subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
        if not subdirs:
            return None
        
        latest_dir = max(subdirs, key=lambda d: d.stat().st_mtime)
        result_path = latest_dir / "result.png"
        
        return result_path if result_path.exists() else None
    
    def analyze(self, use_latest: bool = False) -> dict:
        """
        分析图像的降质情况
        
        Args:
            use_latest: 是否强制使用最新的result.png并复制到analyze_waiting.png
                        如果为False但analyze_waiting.png不存在，也会自动使用最新的result.png
        """
        analyze_waiting_path = Path("/root/autodl-tmp/AgenticIR/dataset/analyze_waiting.png")
        
        # 确定要分析的图像
        if use_latest or not analyze_waiting_path.exists():
            # 强制使用最新result.png 或者 analyze_waiting.png不存在时自动使用
            latest_path = self.find_latest_result()
            if not latest_path:
                raise FileNotFoundError("未找到最新的result.png")
            
            # 复制到analyze_waiting.png
            analyze_waiting_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(latest_path, analyze_waiting_path)
            image_path = analyze_waiting_path
            print(f"✅ 已复制最新图像到: {image_path}")
        else:
            # 使用现有的analyze_waiting.png
            image_path = analyze_waiting_path
            print(f"✅ 使用现有的analyze_waiting.png: {image_path}")
        
        # 调用 DepictQA 进行评估
        print(f"🔍 正在分析图像: {image_path.name}")
        
        # 尝试不同的参数传递方式
        try:
            # 方法1：直接传Path对象
            evaluation_str = self.depictqa(img_path=image_path, task="eval_degradation")
        except TypeError:
            try:
                # 方法2：传字符串
                evaluation_str = self.depictqa(img_path=str(image_path), task="eval_degradation")
            except TypeError:
                # 方法3：可能参数名不同
                evaluation_str = self.depictqa(image_path=image_path, task="eval_degradation")
        
        # 解析结果
        if isinstance(evaluation_str, str):
            evaluation = eval(evaluation_str)
        else:
            evaluation = evaluation_str
        
        # 构建结果字典
        result = {
            "image_path": str(image_path),
            "image_name": image_path.name,
            "degradations": {},
            "degradation_scores": {},
            "severe_degradations": [],
            "all_degradations_detected": [],  # 记录实际检测到的所有降质类型
            "timestamp": datetime.now().isoformat(),
            "dimension_scores": {},           # 五个维度的评分
            "dimension_scores_cn": {},         # 中文维度评分
            "overall_score": 0,                 # 总评分
            "overall_score_cn": ""              # 总评分中文描述
        }
        
        # 初始化所有降质类型为默认值（如果DepictQA没有返回某个类型）
        default_severity = "very low"
        default_score = 1
        
        for degradation in self.degradations:
            result["degradations"][degradation] = default_severity
            result["degradation_scores"][degradation] = default_score
        
        # 更新实际检测到的降质类型
        for degradation, severity in evaluation:
            if degradation in result["degradations"]:
                result["degradations"][degradation] = severity
                score = self.level_to_score[severity]
                result["degradation_scores"][degradation] = score
                result["all_degradations_detected"].append({
                    "degradation": degradation,
                    "severity": severity,
                    "score": score
                })
                
                # 记录严重的降质（medium及以上）
                if score >= 3:
                    result["severe_degradations"].append({
                        "degradation": degradation,
                        "severity": severity,
                        "score": score
                    })
        
        # 计算五个维度的评分
        result = self._calculate_dimension_scores(result)
        
        return result
    
    def _calculate_dimension_scores(self, result: dict) -> dict:
        """
        计算五个质量维度的评分
        
        评分公式：
        1. 每个维度的基础分 = 100
        2. 对于每个降质类型，根据其严重程度和对该维度的影响权重扣分
        3. 扣分公式：扣分 = 降质分数 * 权重 * 影响系数
           - 降质分数范围：1-5 (very low到very high)
           - 影响系数：线性映射，分数1影响10%，分数5影响50%
        4. 最终评分 = max(0, 基础分 - 总扣分)
        5. 总评分 = 五个维度的加权平均（各维度权重相等）
        """
        
        # 初始化各维度评分
        dimension_scores = {dim: 100.0 for dim in self.quality_dimensions}
        
        # 计算每个降质类型对各维度的影响
        for degradation, score in result["degradation_scores"].items():
            if degradation in self.degradation_to_dimension:
                # 影响系数：降质越严重，影响越大 (线性映射：1->0.1, 5->0.5)
                impact_factor = score * 0.1
                
                # 对各维度的影响
                dimension_weights = self.degradation_to_dimension[degradation]
                for dimension, weight in dimension_weights.items():
                    if weight > 0:
                        # 扣分 = 基础分 * 权重 * 影响系数
                        deduction = 100 * weight * impact_factor
                        dimension_scores[dimension] -= deduction
        
        # 确保分数在0-100之间
        for dimension in dimension_scores:
            dimension_scores[dimension] = max(0, min(100, round(dimension_scores[dimension], 1)))
        
        # 计算总评分（各维度等权重）
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        overall_score = round(overall_score, 1)
        
        # 保存结果
        result["dimension_scores"] = dimension_scores
        result["dimension_scores_cn"] = {
            self.dimension_names_cn[dim]: score 
            for dim, score in dimension_scores.items()
        }
        result["overall_score"] = overall_score
        
        # 总评分中文描述
        if overall_score >= 90:
            result["overall_score_cn"] = "极好"
        elif overall_score >= 80:
            result["overall_score_cn"] = "优秀"
        elif overall_score >= 70:
            result["overall_score_cn"] = "良好"
        elif overall_score >= 60:
            result["overall_score_cn"] = "一般"
        elif overall_score >= 50:
            result["overall_score_cn"] = "较差"
        else:
            result["overall_score_cn"] = "很差"
        
        return result
    
    def print_results(self, result: dict):
        """打印分析结果"""
        print("\n" + "="*70)
        print(f"📸 图像: {result['image_name']}")
        print("="*70)
        
        # 打印降质分析结果
        print("\n📊 降质分析结果:")
        print("-"*50)
        
        markers = {"very low": "✔", "low": "✔", "medium": "▲", "high": "✖", "very high": "✖"}
        
        # 按分数排序显示
        sorted_degradations = sorted(
            result["degradation_scores"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for degradation, score in sorted_degradations:
            severity = result["degradations"][degradation]
            marker = markers.get(severity, "?")
            # 突出显示低分辨率
            if degradation == "low resolution":
                print(f"  {marker} {degradation:25}: {severity.upper()} ({score}/5) 📏")
            else:
                print(f"  {marker} {degradation:25}: {severity.upper()} ({score}/5)")
        
        # 显示严重降质汇总
        if result["severe_degradations"]:
            print("\n🔴 严重降质检测 (分数≥3):")
            for item in result["severe_degradations"]:
                warning = "⚠️" if item["degradation"] == "low resolution" else "•"
                print(f"    {warning} {item['degradation']}: {item['severity']} ({item['score']}/5)")
        else:
            print("\n✅ 未检测到严重降质")
        
        # 打印五个维度的评分
        print("\n" + "="*70)
        print("🎯 五维质量评分:")
        print("-"*50)
        
        # 按分数排序显示
        sorted_dimensions = sorted(
            result["dimension_scores_cn"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for dim_name_cn, score in sorted_dimensions:
            # 根据分数显示不同图标
            if score >= 80:
                icon = "🌟"
            elif score >= 60:
                icon = "👍"
            elif score >= 40:
                icon = "👌"
            else:
                icon = "⚠️"
            
            print(f"  {icon} {dim_name_cn:10}: {score}/100")
        
        # 打印总评分
        print("\n" + "="*70)
        total_icon = "🏆" if result["overall_score"] >= 80 else "📊"
        print(f"{total_icon} 图像质量总评分: {result['overall_score']}/100")
        print(f"   质量等级: {result['overall_score_cn']}")
        
        # 显示总体评估（保持原有的）
        avg_score = sum(result["degradation_scores"].values()) / len(result["degradation_scores"])
        print(f"\n📈 总体降质评分: {avg_score:.2f}/5")
        
        if avg_score <= 2:
            quality = "优质"
            color = "✅"
        elif avg_score <= 3:
            quality = "良好"
            color = "👍"
        elif avg_score <= 4:
            quality = "一般"
            color = "👌"
        else:
            quality = "较差"
            color = "⚠️"
        
        print(f"{color} 传统降质评估: {quality}")
        print("\n" + "="*70)
    
    def get_formatted_output(self, result: dict) -> str:
        """获取格式化的输出字符串"""
        lines = []
        lines.append("\n" + "="*70)
        lines.append(f"📸 图像: {result['image_name']}")
        lines.append("="*70)
        
        # 降质分析结果
        lines.append("\n📊 降质分析结果:")
        lines.append("-"*50)
        
        markers = {"very low": "✔", "low": "✔", "medium": "▲", "high": "✖", "very high": "✖"}
        
        sorted_degradations = sorted(
            result["degradation_scores"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for degradation, score in sorted_degradations:
            severity = result["degradations"][degradation]
            marker = markers.get(severity, "?")
            lines.append(f"  {marker} {degradation:25}: {severity.upper()} ({score}/5)")
        
        # 严重降质
        if result["severe_degradations"]:
            lines.append("\n🔴 严重降质检测:")
            for item in result["severe_degradations"]:
                lines.append(f"    • {item['degradation']}: {item['severity']} ({item['score']}/5)")
        else:
            lines.append("\n✅ 未检测到严重降质")
        
        # 五维评分
        lines.append("\n" + "="*70)
        lines.append("🎯 五维质量评分:")
        lines.append("-"*50)
        
        sorted_dimensions = sorted(
            result["dimension_scores_cn"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for dim_name_cn, score in sorted_dimensions:
            if score >= 80:
                icon = "🌟"
            elif score >= 60:
                icon = "👍"
            elif score >= 40:
                icon = "👌"
            else:
                icon = "⚠️"
            lines.append(f"  {icon} {dim_name_cn:10}: {score}/100")
        
        # 总评分
        lines.append("\n" + "="*70)
        lines.append(f"🏆 图像质量总评分: {result['overall_score']}/100")
        lines.append(f"   质量等级: {result['overall_score_cn']}")
        
        # 传统评估
        avg_score = sum(result["degradation_scores"].values()) / len(result["degradation_scores"])
        lines.append(f"\n📈 总体降质评分: {avg_score:.2f}/5")
        
        if avg_score <= 2:
            quality = "优质"
            color = "✅"
        elif avg_score <= 3:
            quality = "良好"
            color = "👍"
        elif avg_score <= 4:
            quality = "一般"
            color = "👌"
        else:
            quality = "较差"
            color = "⚠️"
        
        lines.append(f"{color} 传统降质评估: {quality}")
        lines.append("\n" + "="*70)
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="分析图像的降质类型和程度")
    parser.add_argument("--latest", "-l", action="store_true", 
                       help="强制使用最新的result.png并复制到analyze_waiting.png")
    parser.add_argument("--output", "-o", type=str, help="保存结果到JSON文件")
    parser.add_argument("--quiet", "-q", action="store_true", help="只输出JSON结果")
    
    args = parser.parse_args()
    
    try:
        analyzer = DegradationAnalyzer()
        result = analyzer.analyze(use_latest=args.latest)
        
        if args.quiet:
            # 只输出JSON
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 输出格式化结果
            analyzer.print_results(result)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            if not args.quiet:
                print(f"\n✅ 结果已保存到: {args.output}")
        
        return result
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


if __name__ == "__main__":
    main()