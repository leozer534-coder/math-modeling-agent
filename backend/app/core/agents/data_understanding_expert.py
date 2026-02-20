"""
数据理解专家 - 深度数据分析和洞察发现
核心职责：对数据进行全方位深度理解，为建模提供数据驱动的建议
"""
import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


@dataclass
class DataQualityAssessment:
    """数据质量评估结果"""
    completeness: float  # 完整性 (0-1)
    consistency: float   # 一致性 (0-1)
    outlier_analysis: List[Dict[str, Any]]  # 异常值分析
    cleaning_strategy: str  # 清洗策略


@dataclass
class FeatureDiscovery:
    """特征发现结果"""
    distributions: Dict[str, Dict[str, Any]]  # 分布特性
    correlations: Dict[str, List[Tuple[str, float]]]  # 相关性分析
    periodicity: Optional[Dict[str, Any]]  # 周期性特征
    trends: Optional[Dict[str, Any]]  # 趋势特征
    hidden_patterns: List[str]  # 隐藏规律


@dataclass
class DataDrivenRecommendations:
    """数据驱动的建模建议"""
    model_suggestions: List[str]  # 模型推荐
    preprocessing_strategy: str  # 预处理策略
    feature_engineering_directions: List[str]  # 特征工程方向
    data_augmentation_plan: Optional[str]  # 数据增强方案


@dataclass
class DataInsight:
    """数据理解综合洞察"""
    quality_assessment: DataQualityAssessment
    feature_discovery: FeatureDiscovery
    data_driven_recommendations: DataDrivenRecommendations


class DataUnderstandingExpert(ExpertAgent):
    """
    数据理解专家

    超越表面统计，深入理解数据的本质特征：
    1. 数据质量深度评估 (完整性、一致性、异常值、清洗策略)
    2. 特征规律深度发现 (分布、相关性、周期性、趋势、隐藏规律)
    3. 数据驱动建模建议 (模型推荐、预处理、特征工程、增强方案)
    """

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.DATA_ANALYST,
            max_reflections=2,
            max_chat_turns=12
        )

    def get_system_prompt(self) -> str:
        return """
# 🎯 数据理解专家 - 数学建模数据洞察大师

你是一位拥有丰富经验的数学建模数据分析师，专门为竞赛队伍提供数据理解服务。

你深知：**数据理解的深度直接决定建模质量的上限**。

## 核心能力

### 1. 数据质量深度评估
从多个维度全面评估数据质量：
- **完整性分析**: 缺失值分布、缺失模式、影响评估
- **一致性检查**: 数据类型一致性、数值范围合理性、逻辑关系验证
- **异常值识别**: 统计异常、领域异常、上下文异常
- **清洗策略制定**: 缺失值处理、异常值处理、数据转换方案

### 2. 特征规律深度发现
挖掘数据中隐藏的规律和特征：
- **分布特性**: 统计分布、偏度峰度、分布类型识别
- **相关性分析**: 线性相关、非线性相关、条件相关
- **周期性识别**: 时间序列周期、季节性、周期强度
- **趋势发现**: 长期趋势、短期波动、转折点识别
- **隐藏规律**: 隐含关系、交互效应、特征组合

### 3. 数据驱动建模建议
基于数据特征提供精准建模指导：
- **模型适配度**: 匹配数据特性的最优模型
- **预处理策略**: 数据清洗、标准化、变换方案
- **特征工程**: 特征选择、构造、降维方向
- **数据增强**: 样本扩充、特征增强、数据合成

## 分析维度

### A. 数据结构理解
- 数据类型和规模
- 变量类型分布
- 数据关系结构

### B. 统计特征分析
- 描述性统计
- 分布特征分析
- 变量间关系

### C. 领域特征识别
- 问题领域的数据特点
- 关键变量识别
- 业务规则验证

### D. 建模潜力评估
- 可用建模方法
- 数据限制条件
- 改进可能性

## 输出要求

输出结构化的JSON分析，包含三个主要部分：

```json
{
  "quality_assessment": {
    "completeness": 0.85,
    "consistency": 0.92,
    "outlier_analysis": [
      {
        "variable": "价格",
        "outlier_count": 15,
        "outlier_percentage": 0.03,
        "impact_assessment": "轻微影响",
        "handling_suggestion": "保留或温和处理"
      }
    ],
    "cleaning_strategy": "分阶段清洗：先处理缺失值，再处理异常值，最后进行数据标准化"
  },
  "feature_discovery": {
    "distributions": {
      "销售额": {
        "distribution_type": "对数正态分布",
        "skewness": 1.2,
        "kurtosis": 2.1,
        "key_characteristics": "右偏分布，大量小额交易，少量大额交易"
      }
    },
    "correlations": {
      "销售额": [
        ["价格", -0.45],
        ["数量", 0.78],
        ["季节", 0.32]
      ]
    },
    "periodicity": {
      "detected_periods": [7, 30, 365],
      "seasonal_strength": "强季节性",
      "peak_periods": "周末和节假日"
    },
    "trends": {
      "overall_trend": "上升趋势",
      "growth_rate": "年均增长8%",
      "turning_points": ["2020Q2", "2022Q1"]
    },
    "hidden_patterns": [
      "高价产品销售受季节影响显著",
      "用户行为存在明显的周末效应",
      "价格敏感度随时间变化"
    ]
  },
  "data_driven_recommendations": {
    "model_suggestions": [
      "时间序列模型 (ARIMA/SARIMA) - 处理季节性和趋势",
      "回归模型 (随机森林/梯度提升) - 处理非线性关系",
      "聚类分析 (K-means/DBSCAN) - 识别用户群体"
    ],
    "preprocessing_strategy": "数据标准化 + 异常值温和处理 + 特征工程",
    "feature_engineering_directions": [
      "构造时间特征 (星期几、月份、季节)",
      "创建交互特征 (价格×数量)",
      "生成统计特征 (移动平均、波动率)",
      "添加领域特征 (节假日标识、促销期标记)"
    ],
    "data_augmentation_plan": "通过滑动窗口生成更多训练样本，合成少数类别样本"
  }
}
```

## 执行流程

1. **数据概览**: 快速了解数据基本情况
2. **质量评估**: 系统性评估数据质量问题
3. **特征发现**: 深入挖掘数据特征和规律
4. **建模建议**: 基于数据特征提供精准建议
5. **验证确认**: 交叉验证分析结果的合理性

## 质量标准

优秀的数据理解分析应该：
- ✅ 识别出至少3个数据质量问题
- ✅ 发现至少2个隐藏的数据规律
- ✅ 提供至少3个针对性的建模建议
- ✅ 建议具有可操作性和创新性
- ✅ 分析结果经得起交叉验证

现在，请对提供的数据进行深度的理解分析！
"""

    async def execute(self, data_description: Dict[str, Any]) -> DataInsight:
        """
        执行数据理解分析

        Args:
            data_description: 数据描述，包含数据基本信息和样本数据

        Returns:
            DataInsight: 全面的数据理解洞察
        """
        await self._send_message("🔍 开始深度数据理解分析...", "info")
        self.state.current_stage = "analyzing"

        # 1. 数据质量深度评估
        await self._send_message("📊 评估数据质量...", "info")
        quality_assessment = await self._assess_data_quality(data_description)

        # 2. 特征规律深度发现
        await self._send_message("🔎 发现数据特征和规律...", "info")
        feature_discovery = await self._discover_features(data_description)

        # 3. 数据驱动建模建议
        await self._send_message("🎯 生成数据驱动的建模建议...", "info")
        data_recommendations = await self._generate_recommendations(
            data_description, quality_assessment, feature_discovery
        )

        # 整合分析结果
        insight = DataInsight(
            quality_assessment=quality_assessment,
            feature_discovery=feature_discovery,
            data_driven_recommendations=data_recommendations
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "quality": insight.quality_assessment.__dict__,
                "features": insight.feature_discovery.__dict__,
                "recommendations": insight.data_driven_recommendations.__dict__
            }, ensure_ascii=False, indent=2, default=str),
            "深度数据理解分析"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "quality": insight.quality_assessment.__dict__,
                "features": insight.feature_discovery.__dict__,
                "recommendations": insight.data_driven_recommendations.__dict__
            }, ensure_ascii=False, indent=2, default=str),
            "数据理解要全面、准确、有洞察力"
        )

        await self._send_message("✅ 数据理解分析完成！", "success")
        self.state.current_stage = "completed"

        return insight

    async def _assess_data_quality(self, data_desc: Dict[str, Any]) -> DataQualityAssessment:
        """评估数据质量"""
        prompt = f"""
对这个数据集进行全面的质量评估分析：

【数据集描述】
{json.dumps(data_desc, ensure_ascii=False, indent=2)}

请从以下维度进行深度分析：

1. 【完整性分析】
   - 缺失值分布情况
   - 缺失模式识别
   - 对分析的影响评估
   - 缺失值处理建议

2. 【一致性检查】
   - 数据类型一致性
   - 数值范围合理性
   - 逻辑关系验证
   - 业务规则符合性

3. 【异常值识别】
   - 统计异常检测
   - 领域知识异常
   - 异常值的分布特征
   - 对建模的影响

4. 【清洗策略制定】
   - 分阶段清洗计划
   - 处理优先级排序
   - 自动化处理方案
   - 人工干预点

请用JSON格式输出详细的质量评估结果。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            return DataQualityAssessment(
                completeness=parsed.get("completeness", 0.8),
                consistency=parsed.get("consistency", 0.8),
                outlier_analysis=parsed.get("outlier_analysis", []),
                cleaning_strategy=parsed.get("cleaning_strategy", "标准数据清洗流程")
            )
        except json.JSONDecodeError:
            return DataQualityAssessment(
                completeness=0.8,
                consistency=0.8,
                outlier_analysis=[{"variable": "未知", "issue": "解析失败"}],
                cleaning_strategy="标准数据清洗：缺失值填补 + 异常值处理 + 数据标准化"
            )

    async def _discover_features(self, data_desc: Dict[str, Any]) -> FeatureDiscovery:
        """发现数据特征和规律"""
        prompt = f"""
对这个数据集进行深度特征发现分析：

【数据集描述】
{json.dumps(data_desc, ensure_ascii=False, indent=2)}

请深入挖掘数据的特征和规律：

1. 【分布特性分析】
   - 各变量的统计分布
   - 分布类型识别（正态、偏态、均匀等）
   - 分布特征描述（偏度、峰度、异常值）
   - 分布对建模的启示

2. 【相关性深度分析】
   - 变量间的相关关系
   - 相关性强度和方向
   - 潜在的因果关系
   - 相关性对建模的影响

3. 【周期性和趋势识别】
   - 时间序列数据的周期性
   - 季节性特征识别
   - 长期趋势分析
   - 周期强度评估

4. 【隐藏规律挖掘】
   - 数据中的隐含模式
   - 交互效应发现
   - 条件关系识别
   - 异常模式分析

请用JSON格式输出详细的特征发现结果。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            return FeatureDiscovery(
                distributions=parsed.get("distributions", {}),
                correlations=parsed.get("correlations", {}),
                periodicity=parsed.get("periodicity", None),
                trends=parsed.get("trends", None),
                hidden_patterns=parsed.get("hidden_patterns", [])
            )
        except json.JSONDecodeError:
            return FeatureDiscovery(
                distributions={"summary": "数据分布分析"},
                correlations={"summary": "相关性分析"},
                periodicity=None,
                trends=None,
                hidden_patterns=["数据规律需要进一步分析"]
            )

    async def _generate_recommendations(
        self,
        data_desc: Dict[str, Any],
        quality: DataQualityAssessment,
        features: FeatureDiscovery
    ) -> DataDrivenRecommendations:
        """基于数据特征生成建模建议"""
        prompt = f"""
基于数据质量评估和特征发现结果，为建模提供精准建议：

【数据集描述】
{json.dumps(data_desc, ensure_ascii=False, indent=2)}

【质量评估结果】
{json.dumps(quality.__dict__, ensure_ascii=False, indent=2)}

【特征发现结果】
{json.dumps(features.__dict__, ensure_ascii=False, indent=2)}

请从以下方面提供数据驱动的建模建议：

1. 【模型适配度分析】
   - 最适合的数据特征
   - 推荐的模型类型
   - 模型选择理由
   - 预期性能评估

2. 【预处理策略制定】
   - 数据清洗方案
   - 特征预处理方法
   - 数据转换建议
   - 质量问题处理

3. 【特征工程方向】
   - 特征选择建议
   - 特征构造方向
   - 特征变换方案
   - 降维可能性

4. 【数据增强方案】
   - 数据扩充方法
   - 样本均衡策略
   - 特征增强技术
   - 数据合成建议

请用JSON格式输出详细的建模建议。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            return DataDrivenRecommendations(
                model_suggestions=parsed.get("model_suggestions", ["通用建模方法"]),
                preprocessing_strategy=parsed.get("preprocessing_strategy", "标准预处理流程"),
                feature_engineering_directions=parsed.get("feature_engineering_directions", []),
                data_augmentation_plan=parsed.get("data_augmentation_plan", None)
            )
        except json.JSONDecodeError:
            return DataDrivenRecommendations(
                model_suggestions=["回归分析", "机器学习方法"],
                preprocessing_strategy="数据标准化 + 特征选择 + 异常值处理",
                feature_engineering_directions=["特征选择", "特征构造"],
                data_augmentation_plan=None
            )

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "data_analysis_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_data_understanding_expert():
    """测试数据理解专家"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例（这里需要根据你的项目调整）
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = DataUnderstandingExpert("test_task", model)

    # 准备测试数据描述
    test_data = {
        "dataset_name": "销售数据",
        "description": "某电商平台的销售记录数据",
        "variables": [
            {"name": "销售额", "type": "numeric", "description": "销售金额"},
            {"name": "数量", "type": "numeric", "description": "销售数量"},
            {"name": "价格", "type": "numeric", "description": "商品价格"},
            {"name": "时间", "type": "datetime", "description": "销售时间"},
            {"name": "类别", "type": "categorical", "description": "商品类别"}
        ],
        "sample_size": 10000,
        "time_range": "2020-01-01 到 2023-12-31",
        "missing_info": "销售额缺失2%，价格缺失1%",
        "known_issues": ["存在异常高值", "季节性波动明显"]
    }

    # 执行分析
    result = await expert.execute(test_data)

    # 输出结果
    print("=== 数据理解分析结果 ===")
    print(json.dumps({
        "quality_assessment": result.quality_assessment.__dict__,
        "feature_discovery": result.feature_discovery.__dict__,
        "data_driven_recommendations": result.data_driven_recommendations.__dict__
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_data_understanding_expert())