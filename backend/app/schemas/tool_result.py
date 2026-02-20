from pydantic import BaseModel
from typing import Any, Optional


class ToolResult(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


class EDADataSummary(BaseModel):
    """EDA 数据探索的结构化摘要"""
    dataset_shape: Optional[tuple[int, int]] = None
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    missing_ratio: dict[str, float] = {}
    correlation_highlights: list[str] = []
    data_quality_issues: list[str] = []
    key_statistics: str = ""
    suggested_models: list[str] = []


class QuestionSolution(BaseModel):
    """单个问题的建模方案"""

    description: str = ""
    alternative_models: Optional[list[str]] = None
    baseline_model: Optional[str] = None
    improvement_model: Optional[str] = None
    innovation_model: Optional[str] = None

    def to_text(self) -> str:
        """将方案转换为文本描述"""
        parts = [self.description]

        if self.baseline_model:
            parts.append(f"基线模型: {self.baseline_model}")
        if self.improvement_model:
            parts.append(f"改进模型: {self.improvement_model}")
        if self.innovation_model:
            parts.append(f"创新模型: {self.innovation_model}")
        if self.alternative_models:
            parts.append(f"备选模型: {', '.join(self.alternative_models)}")

        return "\n".join(parts)
