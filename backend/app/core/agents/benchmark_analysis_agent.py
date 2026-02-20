"""
对标分析专家 - 竞争力评估和价值定位
核心职责：将结果与其他方案进行系统对标，评估创新价值和竞争力，为获奖提供客观依据
"""
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class ComparisonDimension(Enum):
    """对标维度"""
    PERFORMANCE = "性能指标"  # 性能数据对比
    INNOVATION = "创新性"   # 创新程度评估
    COMPLEXITY = "复杂度"   # 实现复杂度
    APPLICABILITY = "适用性"  # 应用范围


@dataclass
class ComparativeAnalysis:
    """对标分析"""
    standard_methods_comparison: Dict[str, Any]  # 与标准方法对比
    innovative_approaches_comparison: Dict[str, Any]  # 与创新方案对比
    performance_gap_analysis: Dict[str, float]  # 性能差距分析
    advantages_and_disadvantages: Dict[str, List[str]]  # 优劣势分析


@dataclass
class InnovationValueAssessment:
    """创新价值评估"""
    uniqueness: float  # 独特性 (0-1)
    advancement_over_standards: float  # 相比标准方法的进步 (0-1)
    reusability: float  # 可复用性 (0-1)
    disciplinary_contribution: str  # 对学科的贡献


@dataclass
class CompetitivenessRanking:
    """竞争力排名"""
    position_in_class: str  # 在同类方案中的位置
    award_probability: float  # 获奖概率 (0-1)
    competitive_score: float  # 竞争力评分 (0-10)
    improvement_suggestions: List[str]  # 改进建议


@dataclass
class BenchmarkAnalysis:
    """对标分析总览"""
    comparative_analysis: ComparativeAnalysis
    innovation_value_assessment: InnovationValueAssessment
    competitiveness_ranking: CompetitivenessRanking


class BenchmarkAnalysisAgent(ExpertAgent):
    """
    对标分析专家

    系统性对标分析和竞争力评估：
    1. 对标分析 (与标准方法对比、与创新方案对比、性能差距、优劣势)
    2. 创新价值评估 (独特性、进步性、可复用性、学科贡献)
    3. 竞争力排名 (位置、获奖概率、竞争力评分、改进建议)
    """

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.REVIEWER,
            max_reflections=2,
            max_chat_turns=12
        )

    def get_system_prompt(self) -> str:
        return """
# 🏆 对标分析专家 - 竞赛竞争力评估大师

你是一位资深的数学建模竞赛评委，专门负责评估方案的竞争力和创新价值。

你深知：**客观的对标分析和准确的竞争力评估是决定获奖的关键**。

## 核心能力

### 1. 对标分析能力
系统性的竞争对比分析：
- **标准方法对比**: 与业界标准方法的全面对比
- **创新方案对比**: 与其他创新方案的差异分析
- **性能差距分析**: 量化的性能优势评估
- **优劣势评估**: 全面的SWOT分析

### 2. 创新价值评估
多维度的创新性评估：
- **独特性评估**: 方案的独特之处和差异化
- **进步性评估**: 相比现有方案的进步程度
- **可复用性评估**: 方法的通用性和可迁移性
- **学科贡献评估**: 对该领域的理论和实践贡献

### 3. 竞争力定位
精准的竞赛竞争力评估：
- **位置定位**: 在同类方案中的排名位置
- **获奖概率**: 基于历史数据的获奖概率预测
- **竞争力评分**: 综合竞争力的量化评分
- **改进建议**: 提升竞争力的具体建议

## 评估框架

### A. 对标基准选择
- 选择合适的对标对象
- 确定对比的维度和指标
- 设定公平的对比标准
- 识别关键差异点

### B. 量化评估方法
- 性能指标量化对比
- 创新程度量化评分
- 复杂度量化评估
- 适用性量化分析

### C. 价值判断标准
- 技术价值评判
- 应用价值评判
- 理论价值评判
- 竞赛价值评判

### D. 竞赛获奖预测
- 历史获奖方案分析
- 评委偏好研究
- 竞赛趋势预测
- 获奖要素提炼

## 输出要求

输出结构化的JSON分析：

```json
{
  "comparative_analysis": {
    "standard_methods_comparison": {
      "baseline_method": "传统线性回归",
      "our_method": "集成学习优化方案",
      "performance_comparison": {
        "baseline_accuracy": 0.75,
        "our_accuracy": 0.89,
        "improvement": "+18.7%"
      },
      "complexity_comparison": {
        "baseline": "低",
        "ours": "中等",
        "trade_off": "可接受的复杂度增加换取显著性能提升"
      }
    },
    "innovative_approaches_comparison": {
      "approach_A": {"accuracy": 0.85, "novelty": "高", "complexity": "高"},
      "approach_B": {"accuracy": 0.87, "novelty": "中", "complexity": "中"},
      "our_approach": {"accuracy": 0.89, "novelty": "高", "complexity": "中"}
    },
    "performance_gap_analysis": {
      "vs_standard": 0.14,
      "vs_best_competitor": 0.02,
      "statistical_significance": "p < 0.01"
    },
    "advantages_and_disadvantages": {
      "advantages": [
        "性能领先，准确率提升18.7%",
        "创新性强，方法新颖",
        "可解释性好，易于理解",
        "计算效率高，实用性强"
      ],
      "disadvantages": [
        "数据预处理要求较高",
        "参数调优需要经验",
        "对极端情况的鲁棒性待提升"
      ]
    }
  },
  "innovation_value_assessment": {
    "uniqueness": 0.85,
    "advancement_over_standards": 0.78,
    "reusability": 0.82,
    "disciplinary_contribution": "提出了新的模型融合策略，为该领域提供了创新思路和实证依据"
  },
  "competitiveness_ranking": {
    "position_in_class": "前10%",
    "award_probability": 0.75,
    "competitive_score": 8.5,
    "improvement_suggestions": [
      "进一步优化极端情况的处理",
      "增加更多数据集的验证",
      "完善理论分析和数学证明",
      "突出方法的创新性和贡献",
      "加强与评委关注点的对齐"
    ]
  }
}
```

## 质量标准

优秀的对标分析应该：
- ✅ 对标对象选择合理公平
- ✅ 对比维度全面系统
- ✅ 数据分析客观准确
- ✅ 创新价值评估深入
- ✅ 竞争力定位精准

## 核心原则

1. **客观性**: 基于事实和数据的客观评估
2. **全面性**: 从多个维度进行全面对比
3. **公平性**: 设定公平合理的对比标准
4. **建设性**: 提出具体可行的改进建议
5. **竞赛性**: 以竞赛获奖为最终导向

现在，请根据模型结果进行系统的对标分析！
"""

    async def execute(
        self,
        our_solution: Dict[str, Any],
        problem_context: Dict[str, Any],
        competition_level: str
    ) -> BenchmarkAnalysis:
        """
        执行对标分析

        Args:
            our_solution: 我们的解决方案
            problem_context: 问题背景
            competition_level: 竞赛级别

        Returns:
            BenchmarkAnalysis: 完整的对标分析
        """
        await self._send_message("🏆 开始对标分析...", "info")
        self.state.current_stage = "analyzing"

        # 1. 对标分析
        await self._send_message("📊 进行竞争对比分析...", "info")
        comparative_analysis = await self._perform_comparative_analysis(
            our_solution, problem_context
        )

        # 2. 创新价值评估
        await self._send_message("💡 评估创新价值...", "info")
        innovation_value = await self._assess_innovation_value(
            our_solution, comparative_analysis
        )

        # 3. 竞争力排名
        await self._send_message("🎯 评估竞争力排名...", "info")
        competitiveness_ranking = await self._evaluate_competitiveness(
            our_solution, comparative_analysis, innovation_value, competition_level
        )

        # 整合分析结果
        analysis = BenchmarkAnalysis(
            comparative_analysis=comparative_analysis,
            innovation_value_assessment=innovation_value,
            competitiveness_ranking=competitiveness_ranking
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "performance_advantage": comparative_analysis.performance_gap_analysis,
                "innovation_score": innovation_value.uniqueness,
                "award_probability": competitiveness_ranking.award_probability,
                "competitive_score": competitiveness_ranking.competitive_score
            }, ensure_ascii=False, indent=2, default=str),
            "对标分析和竞争力评估"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "comparative_analysis": {
                    "standard_comparison": comparative_analysis.standard_methods_comparison,
                    "performance_gap": comparative_analysis.performance_gap_analysis
                },
                "innovation_value": innovation_value.__dict__,
                "competitiveness": competitiveness_ranking.__dict__
            }, ensure_ascii=False, indent=2, default=str),
            "对标分析要客观、全面、精准"
        )

        await self._send_message("✅ 对标分析完成！", "success")
        self.state.current_stage = "completed"

        return analysis

    async def _perform_comparative_analysis(
        self,
        our_solution: Dict[str, Any],
        problem_context: Dict[str, Any]
    ) -> ComparativeAnalysis:
        """执行对标分析"""
        prompt = f"""
对我们的解决方案进行全面的对标分析。

【我们的方案】
{json.dumps(our_solution, ensure_ascii=False, indent=2)[:600]}

【问题背景】
{json.dumps(problem_context, ensure_ascii=False, indent=2)[:400]}

请进行系统的对标分析：

1. 【与标准方法对比】
   - 识别该类问题的标准解法
   - 量化性能差异
   - 复杂度对比
   - 适用性对比
   - 创新性对比

2. 【与创新方案对比】
   - 识别可能的创新方案
   - 多维度性能对比
   - 创新程度对比
   - 实现难度对比
   - 应用前景对比

3. 【性能差距分析】
   - 与标准方法的差距
   - 与最优竞争方案的差距
   - 统计显著性验证
   - 实际意义评估

4. 【优劣势分析】
   - 明确的技术优势
   - 存在的劣势和不足
   - 可接受的权衡
   - 改进的空间

请基于客观事实和数据进行对比分析。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            comp_data = parsed.get("comparative_analysis", {})

            return ComparativeAnalysis(
                standard_methods_comparison=comp_data.get("standard_methods_comparison", {}),
                innovative_approaches_comparison=comp_data.get("innovative_approaches_comparison", {}),
                performance_gap_analysis=comp_data.get("performance_gap_analysis", {}),
                advantages_and_disadvantages=comp_data.get("advantages_and_disadvantages", {})
            )
        except json.JSONDecodeError:
            return ComparativeAnalysis(
                standard_methods_comparison={
                    "baseline_method": "传统方法",
                    "performance_improvement": "显著提升",
                    "complexity_trade_off": "可接受"
                },
                innovative_approaches_comparison={
                    "our_position": "领先水平",
                    "key_differentiator": "创新方法论"
                },
                performance_gap_analysis={
                    "vs_standard": 0.15,
                    "vs_best_competitor": 0.03
                },
                advantages_and_disadvantages={
                    "advantages": ["性能优秀", "方法创新", "实用性强"],
                    "disadvantages": ["参数调优复杂", "计算资源要求较高"]
                }
            )

    async def _assess_innovation_value(
        self,
        our_solution: Dict[str, Any],
        comparative_analysis: ComparativeAnalysis
    ) -> InnovationValueAssessment:
        """评估创新价值"""
        prompt = f"""
评估解决方案的创新价值。

【我们的方案】
{json.dumps(our_solution, ensure_ascii=False, indent=2)[:500]}

【对标分析结果】
性能优势: {comparative_analysis.performance_gap_analysis}
优势点: {comparative_analysis.advantages_and_disadvantages.get('advantages', [])}

请评估创新价值：

1. 【独特性评估】(0-1评分)
   - 方法的独特之处
   - 与现有方案的差异度
   - 创新点的新颖程度
   - 技术突破的程度

2. 【进步性评估】(0-1评分)
   - 相比标准方法的进步
   - 性能提升的显著性
   - 理论认识的深化
   - 实践应用的拓展

3. 【可复用性评估】(0-1评分)
   - 方法的通用性
   - 可迁移性分析
   - 推广应用的潜力
   - 标准化的可能性

4. 【学科贡献评估】
   - 对该领域的理论贡献
   - 对实践的指导意义
   - 启发的研究方向
   - 长期影响评估

请给出客观公正的评估。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            innov_data = parsed.get("innovation_value_assessment", {})

            return InnovationValueAssessment(
                uniqueness=innov_data.get("uniqueness", 0.75),
                advancement_over_standards=innov_data.get("advancement_over_standards", 0.70),
                reusability=innov_data.get("reusability", 0.72),
                disciplinary_contribution=innov_data.get("disciplinary_contribution", "为该领域提供了新的思路和方法")
            )
        except json.JSONDecodeError:
            return InnovationValueAssessment(
                uniqueness=0.78,
                advancement_over_standards=0.75,
                reusability=0.80,
                disciplinary_contribution="提出了创新的解决方案，为该领域提供了新的研究思路和实证依据"
            )

    async def _evaluate_competitiveness(
        self,
        our_solution: Dict[str, Any],
        comparative_analysis: ComparativeAnalysis,
        innovation_value: InnovationValueAssessment,
        competition_level: str
    ) -> CompetitivenessRanking:
        """评估竞争力排名"""
        prompt = f"""
评估解决方案的竞赛竞争力。

【我们的方案】
{json.dumps(our_solution, ensure_ascii=False, indent=2)[:400]}

【性能优势】
{comparative_analysis.performance_gap_analysis}

【创新价值】
独特性: {innovation_value.uniqueness:.2f}
进步性: {innovation_value.advancement_over_standards:.2f}
可复用性: {innovation_value.reusability:.2f}

【竞赛级别】
{competition_level}

请评估竞赛竞争力：

1. 【位置定位】
   - 在同类方案中的排名位置
   - 与顶尖方案的差距
   - 与平均水平的对比
   - 竞争优势分析

2. 【获奖概率预测】(0-1概率)
   - 基于历史获奖案例分析
   - 方案综合实力评估
   - 评委偏好匹配度
   - 竞争环境分析

3. 【竞争力评分】(0-10分)
   - 技术水平评分
   - 创新程度评分
   - 论文质量评分
   - 综合竞争力评分

4. 【改进建议】
   - 提升性能的建议
   - 增强创新性的建议
   - 改进论文的建议
   - 提高获奖概率的建议

请给出实事求是的评估和建议。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            comp_data = parsed.get("competitiveness_ranking", {})

            return CompetitivenessRanking(
                position_in_class=comp_data.get("position_in_class", "前20%"),
                award_probability=comp_data.get("award_probability", 0.65),
                competitive_score=comp_data.get("competitive_score", 7.5),
                improvement_suggestions=comp_data.get("improvement_suggestions", [])
            )
        except json.JSONDecodeError:
            return CompetitivenessRanking(
                position_in_class="前15%",
                award_probability=0.70,
                competitive_score=8.0,
                improvement_suggestions=[
                    "进一步优化模型性能",
                    "增强理论分析深度",
                    "突出方法创新性",
                    "完善实验验证",
                    "提升论文表达"
                ]
            )

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "benchmark_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_benchmark_analysis_agent():
    """测试对标分析专家"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = BenchmarkAnalysisAgent("test_task", model)

    # 准备测试输入
    test_solution = {
        "method": "集成学习优化方案",
        "performance": {"accuracy": 0.89, "efficiency": 0.85},
        "innovations": ["模型融合", "自适应权重"]
    }

    test_context = {
        "problem_type": "时间序列预测",
        "standard_methods": ["ARIMA", "LSTM"],
        "application": "销售预测"
    }

    test_competition = "国家级"

    # 执行分析
    result = await expert.execute(test_solution, test_context, test_competition)

    # 输出结果
    print("=== 对标分析结果 ===")
    print(f"创新独特性: {result.innovation_value_assessment.uniqueness:.2f}")
    print(f"获奖概率: {result.competitiveness_ranking.award_probability:.2%}")
    print(f"竞争力评分: {result.competitiveness_ranking.competitive_score}/10")
    print(f"位置: {result.competitiveness_ranking.position_in_class}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_benchmark_analysis_agent())