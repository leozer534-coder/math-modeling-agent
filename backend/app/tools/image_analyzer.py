"""
图像分析工具 - Image Analyzer
支持视觉模型分析图片和图表，用于处理含图的数学建模问题

功能：
1. 分析题目中的图片和示意图
2. 提取图表中的数据
3. 识别公式和手写内容
4. 理解流程图和关系图
"""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from litellm import acompletion

from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


@dataclass
class ImageAnalysisResult:
    """图像分析结果"""
    description: str  # 图像描述
    extracted_text: Optional[str] = None  # 提取的文字
    extracted_data: Optional[Dict[str, Any]] = None  # 提取的数据
    chart_type: Optional[str] = None  # 图表类型（如果是图表）
    formulas: List[str] = None  # 识别的公式
    insights: List[str] = None  # 对建模的洞察
    
    def __post_init__(self):
        if self.formulas is None:
            self.formulas = []
        if self.insights is None:
            self.insights = []


class ImageAnalyzer:
    """
    图像分析器 - 使用视觉语言模型分析图像
    
    支持多种视觉模型：
    - OpenAI GPT-4o, GPT-4o-mini
    - Claude 3 系列
    - Gemini Pro Vision
    - 通过LiteLLM支持更多模型
    """
    
    # 推荐的视觉模型
    VISION_MODELS = [
        "gpt-4o",
        "gpt-4o-mini", 
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
    ]
    
    def __init__(
        self,
        task_id: str,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None
    ):
        self.task_id = task_id
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        
    async def analyze_image(
        self,
        image_source: str,
        analysis_type: str = "general",
        custom_prompt: Optional[str] = None
    ) -> ImageAnalysisResult:
        """
        分析单张图片
        
        Args:
            image_source: 图片来源（URL、文件路径或base64）
            analysis_type: 分析类型 (general, chart, formula, diagram)
            custom_prompt: 自定义分析提示
            
        Returns:
            ImageAnalysisResult: 分析结果
        """
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="🖼️ 正在分析图像...")
        )
        
        # 准备图片内容
        image_content = await self._prepare_image_content(image_source)
        
        # 构建分析提示
        prompt = custom_prompt or self._get_analysis_prompt(analysis_type)
        
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": """你是一位专业的图像分析专家，专门为数学建模项目分析图表和图片。
                
你的任务是：
1. 详细描述图像内容
2. 提取关键信息和数据
3. 识别图表类型、公式或关系
4. 提供对数学建模有价值的洞察

请用中文回答，确保分析准确、全面。"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    image_content
                ]
            }
        ]
        
        try:
            # 调用视觉模型
            kwargs = {
                "api_key": self.api_key,
                "model": self.model,
                "messages": messages,
                "max_tokens": 2000,
                "timeout": 60
            }
            
            if self.base_url:
                kwargs["base_url"] = self.base_url
                
            response = await acompletion(**kwargs)
            content = response.choices[0].message.content
            
            # 解析响应
            result = self._parse_analysis_response(content, analysis_type)
            
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"✅ 图像分析完成：{result.description[:100]}...")
            )
            
            return result
            
        except Exception as e:
            logger.error("图像分析失败: %s", e)
            return ImageAnalysisResult(
                description=f"图像分析失败: {str(e)}",
                insights=["建议手动查看图像内容"]
            )
    
    async def analyze_multiple_images(
        self,
        image_sources: List[str],
        context: str = ""
    ) -> List[ImageAnalysisResult]:
        """
        分析多张图片
        
        Args:
            image_sources: 图片来源列表
            context: 分析上下文
            
        Returns:
            分析结果列表
        """
        results = []
        for i, source in enumerate(image_sources):
            logger.info("分析图片 %s/%s", i + 1, len(image_sources))
            result = await self.analyze_image(source, "general", context)
            results.append(result)
        return results
    
    async def extract_chart_data(
        self,
        image_source: str
    ) -> Dict[str, Any]:
        """
        从图表中提取数据
        
        Args:
            image_source: 图表图片来源
            
        Returns:
            提取的数据字典
        """
        prompt = """请分析这个图表并提取数据。

请以JSON格式返回以下信息：
```json
{
    "chart_type": "图表类型（如折线图、柱状图、饼图等）",
    "title": "图表标题",
    "x_label": "X轴标签",
    "y_label": "Y轴标签", 
    "data_points": [
        {"x": "x值", "y": "y值"},
        ...
    ],
    "trends": "数据趋势描述",
    "key_values": {
        "max": "最大值",
        "min": "最小值",
        "average": "平均值（如果可以估算）"
    }
}
```

如果某些信息无法确定，请标注为null。"""
        
        result = await self.analyze_image(image_source, "chart", prompt)
        return result.extracted_data or {}
    
    async def extract_formulas(
        self,
        image_source: str
    ) -> List[str]:
        """
        从图片中识别数学公式
        
        Args:
            image_source: 图片来源
            
        Returns:
            识别的公式列表（LaTeX格式）
        """
        prompt = """请识别这张图片中的所有数学公式。

对于每个公式：
1. 用LaTeX格式表示
2. 简要说明公式的含义

请以JSON格式返回：
```json
{
    "formulas": [
        {
            "latex": "LaTeX表示",
            "description": "公式含义"
        }
    ]
}
```"""
        
        result = await self.analyze_image(image_source, "formula", prompt)
        return result.formulas
    
    async def _prepare_image_content(self, image_source: str) -> Dict[str, Any]:
        """准备图片内容用于API调用"""
        
        # 如果是URL
        if image_source.startswith(("http://", "https://")):
            return {
                "type": "image_url",
                "image_url": {"url": image_source}
            }
        
        # 如果是base64编码
        if image_source.startswith("data:image"):
            return {
                "type": "image_url",
                "image_url": {"url": image_source}
            }
        
        # 如果是文件路径
        path = Path(image_source)
        if path.exists():
            with open(path, "rb") as f:
                image_data = f.read()
            
            # 检测图片类型
            suffix = path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }
            mime_type = mime_types.get(suffix, "image/png")
            
            base64_image = base64.b64encode(image_data).decode("utf-8")
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            }
        
        # 假设是原始base64
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_source}"
            }
        }
    
    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """获取分析提示"""
        prompts = {
            "general": """请详细分析这张图片，包括：
1. 图片内容描述
2. 相关的数据或信息
3. 对数学建模的启示
4. 可能需要关注的细节""",

            "chart": """请分析这个图表，包括：
1. 图表类型
2. 数据趋势
3. 关键数据点
4. 对建模的价值""",

            "formula": """请识别图片中的数学公式和符号，包括：
1. 所有可见的公式（用LaTeX格式）
2. 公式的含义
3. 变量说明""",

            "diagram": """请分析这个图示/流程图，包括：
1. 图示类型
2. 各部分的关系
3. 流程或结构说明
4. 对建模的参考价值"""
        }
        return prompts.get(analysis_type, prompts["general"])
    
    def _parse_analysis_response(
        self, 
        content: str, 
        analysis_type: str
    ) -> ImageAnalysisResult:
        """解析分析响应"""
        import json
        
        result = ImageAnalysisResult(description=content)
        
        # 尝试提取JSON数据
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())
                
                if analysis_type == "chart":
                    result.extracted_data = data
                    result.chart_type = data.get("chart_type")
                elif analysis_type == "formula":
                    result.formulas = [
                        f.get("latex", "") for f in data.get("formulas", [])
                    ]
        except (json.JSONDecodeError, IndexError):
            pass
        
        return result


def create_image_analyzer(
    task_id: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None
) -> ImageAnalyzer:
    """
    创建图像分析器实例
    
    Args:
        task_id: 任务ID
        api_key: API密钥
        model: 视觉模型名称
        base_url: API基础URL
        
    Returns:
        ImageAnalyzer实例
    """
    return ImageAnalyzer(
        task_id=task_id,
        api_key=api_key,
        model=model,
        base_url=base_url
    )
