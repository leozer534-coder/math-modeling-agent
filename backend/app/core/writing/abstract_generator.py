"""
摘要生成器 - 重定向模块

此模块已迁移到 app.core.agents.abstract_generator
保留此文件以确保向后兼容性
"""

from app.core.agents.abstract_generator import (
    AbstractComponent,
    AbstractGenerator,
    AbstractLanguage,
    AbstractQualityAssessment,
    AbstractStyle,
    KillerAbstract,
)


__all__ = [
    "AbstractGenerator",
    "AbstractStyle",
    "AbstractLanguage",
    "AbstractComponent",
    "AbstractQualityAssessment",
    "KillerAbstract",
]
