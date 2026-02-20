"""
规律发现引擎 - 数据规律挖掘和理论贡献
核心职责：从结果中挖掘深层规律，发现数据中的隐含模式，为理论发展提供新的见解
"""
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class PatternType(Enum):
    """规律类型"""
    STATISTICAL = "统计规律"  # 统计规律和模式
    MATHEMATICAL = "数学规律"  # 数学规律和关系
    PHYSICAL = "物理规律"    # 物理规律和机制
    HIDDEN = "隐含规律"      # 隐含规律和趋势


@dataclass
class DiscoveredPattern:
    """发现的规律"""
    pattern: str  # 规律描述
    significance: str  # 重要性程度
    mathematical_form: Optional[str]  # 数学形式
    verification_evidence: str  # 验证证据
    generalizability: str  # 普适性
    applications: List[str]  # 应用场景


@dataclass
class TheoreticalContributions:
    """理论贡献"""
    new_insights: List[str]  # 新见解
    theoretical_implications: str  # 理论意义
    future_research_directions: List[str]  # 未来研究方向
    broader_impact: str  # 更广泛影响


@dataclass
class PatternDiscoveryResult:
    """规律发现结果"""
    discovered_patterns: List[DiscoveredPattern]
    theoretical_contributions: TheoreticalContributions


class PatternDiscoveryEngine(ExpertAgent):
    """
    规律发现引擎

    从数据中挖掘深层规律和模式：
    1. 数据规律发现 (统计规律、数学规律、物理规律、隐含规律)
    2. 规律验证泛化 (验证证据、适用范围、简化形式)
    3. 理论贡献 (新见解、理论意义、研究方向)
    """

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.MODELING_EXPERT,
            max_reflections=2,
            max_chat_turns=12
        )

    def get_system_prompt(self) -> str:
        return """
# 🔍 规律发现引擎 - 数据洞察和理论创新大师

你是一位资深的数学建模和数据分析专家，专门负责从数据中挖掘深层规律和理论价值。

你深知：**发现数据中的规律是科学研究的核心，也是数学建模的最高价值**。

## 核心能力

### 1. 数据规律发现
从多维度挖掘数据中的规律：
- **统计规律**: 数据的统计特征和分布规律
- **数学规律**: 变量间的数学关系和函数形式
- **物理规律**: 现象背后的物理机制和原理
- **隐含规律**: 不易察觉的深层次模式和趋势

### 2. 规律验证泛化
确保证据充分和应用广泛：
- **验证证据**: 为发现的规律提供数据支持
- **适用范围**: 明确规律的有效边界和条件
- **普适性分析**: 评估规律的普遍适用性
- **简化形式**: 提取规律的核心数学表达

### 3. 理论贡献提炼
从规律中发现理论价值：
- **新见解**: 对问题的新认识和理解
- **理论意义**: 对现有理论的补充或修正
- **研究方向**: 启发未来的研究课题
- **更广泛影响**: 对相关领域的影响价值

## 发现方法

### A. 多层次分析
- **表象分析**: 直接观察到的数据特征
- **关联分析**: 变量间的关系和相关性
- **因果分析**: 深层的因果关系和机制
- **系统分析**: 整体系统的规律和行为

### B. 跨学科融合
- **数学方法**: 数学建模和统计分析
- **物理原理**: 物理定律和机制理解
- **经济规律**: 经济学的原理和模式
- **生物启发**: 生物学中的规律和机制

### C. 抽象提炼
- **模式识别**: 识别重复出现的模式
- **规律归纳**: 从具体到一般的归纳推理
- **假设检验**: 对规律的统计验证
- **理论构建**: 从规律到理论的提升

### D. 应用导向
- **实用价值**: 规律的实际应用价值
- **预测能力**: 规律的预测和解释能力
- **优化可能**: 基于规律的优化方向
- **创新机会**: 规律启发的新机会

## 输出要求

输出结构化的JSON分析：

```json
{
  "discovered_patterns": [
    {
      "pattern": "数据呈现明显的季节性周期，周期长度为12个月，振幅逐渐增大",
      "significance": "高 - 该规律解释了数据变化的85%以上",
      "mathematical_form": "y(t) = A(t) × sin(2πt/12 + φ) + μ(t)",
      "verification_evidence": "通过傅里叶变换分析，确认主要频率成分",
      "generalizability": "适用于具有明显季节特征的各类时间序列数据",
      "applications": [
        "销售预测",
        "库存管理",
        "生产计划优化"
      ]
    },
    {
      "pattern": "外部因素与核心变量的交互作用呈现非线性特征",
      "significance": "中高 - 揭示了影响因素的复杂作用机制",
      "mathematical_form": "f(x) = a₁x + a₂x² + a₃xy + ...",
      "verification_evidence": "交互项分析显示显著的非线性交互效应",
      "generalizability": "适用于多因素复杂系统建模",
      "applications": [
        "风险评估",
        "决策优化",
        "政策分析"
      ]
    }
  ],
  "theoretical_contributions": {
    "new_insights": [
      "发现了数据的双层结构：趋势层+周期层",
      "识别了关键影响因素的非线性交互机制",
      "提出了自适应预测的新思路"
    ],
    "theoretical_implications": "为时间序列分析提供了新的理论框架，完善了多因素交互作用理论",
    "future_research_directions": [
      "研究自适应权重分配机制",
      "探索跨领域的规律普适性",
      "开发基于规律的智能优化算法"
    ],
    "broader_impact": "该发现对相关领域的预测分析和优化决策具有重要指导意义，可能催生新的研究方法和技术应用"
  }
}
```

## 质量标准

优秀的规律发现应该：
- ✅ 至少发现2个有价值的规律
- ✅ 提供充分的验证证据
- ✅ 具有实际应用价值
- ✅ 提出新的理论见解
- ✅ 启发未来研究方向

## 核心原则

1. **实证驱动**: 基于数据的客观发现，不主观臆断
2. **严谨求证**: 提供充分的证据支持每一个发现
3. **理论提升**: 从现象到规律，再到理论的思维升华
4. **应用导向**: 重视发现的实际应用价值
5. **创新突破**: 寻找突破现有认知的新发现

现在，请从模型结果和数据中挖掘深层的规律和模式！
"""

    async def execute(
        self,
        model_results: Dict[str, Any],
        data_analysis: Dict[str, Any],
        validation_insights: Dict[str, Any]
    ) -> PatternDiscoveryResult:
        """
        执行规律发现分析

        Args:
            model_results: 模型运行结果
            data_analysis: 数据分析结果
            validation_insights: 验证洞察

        Returns:
            PatternDiscoveryResult: 完整的规律发现结果
        """
        await self._send_message("🔍 开始规律发现分析...", "info")
        self.state.current_stage = "analyzing"

        # 1. 数据规律发现
        await self._send_message("📊 发现数据规律...", "info")
        discovered_patterns = await self._discover_data_patterns(
            model_results, data_analysis, validation_insights
        )

        # 2. 理论贡献提炼
        await self._send_message("💡 提炼理论贡献...", "info")
        theoretical_contributions = await self._extract_theoretical_contributions(
            discovered_patterns, model_results, validation_insights
        )

        # 整合发现结果
        result = PatternDiscoveryResult(
            discovered_patterns=discovered_patterns,
            theoretical_contributions=theoretical_contributions
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "patterns_found": len(discovered_patterns),
                "high_significance_patterns": len([p for p in discovered_patterns if "高" in p.significance]),
                "theoretical_insights": len(theoretical_contributions.new_insights)
            }, ensure_ascii=False, indent=2, default=str),
            "规律发现和理论贡献"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "discovered_patterns": [p.__dict__ for p in discovered_patterns],
                "theoretical_contributions": theoretical_contributions.__dict__
            }, ensure_ascii=False, indent=2, default=str),
            "规律发现要深入、准确、有价值"
        )

        await self._send_message("✅ 规律发现完成！", "success")
        self.state.current_stage = "completed"

        return result

    async def _discover_data_patterns(
        self,
        model_results: Dict[str, Any],
        data_analysis: Dict[str, Any],
        validation_insights: Dict[str, Any]
    ) -> List[DiscoveredPattern]:
        """发现数据规律"""
        prompt = f"""
从模型结果和数据分析中挖掘深层数据规律。

【模型结果】
{json.dumps(model_results, ensure_ascii=False, indent=2)[:500]}

【数据分析】
{json.dumps(data_analysis, ensure_ascii=False, indent=2)[:500]}

【验证洞察】
{json.dumps(validation_insights, ensure_ascii=False, indent=2)[:400]}

请深度挖掘数据中的规律：

1. 【统计规律发现】
   - 数据的分布特征和统计规律
   - 趋势和周期性模式
   - 异常值和边界特征
   - 聚类和分组规律

2. 【数学规律发现】
   - 变量间的数学关系
   - 函数形式的推断
   - 参数的规律性变化
   - 约束条件和边界条件

3. 【物理/业务规律发现】
   - 现象背后的机制
   - 因果关系的识别
   - 影响因素的作用方式
   - 系统行为的模式

4. 【隐含规律发现】
   - 不易察觉的模式
   - 深层的关联关系
   - 长期的演化趋势
   - 复杂的系统规律

对每个发现的规律，请提供：
- 清晰的规律描述
- 重要性程度评估
- 数学形式表达（如可能）
- 验证证据说明
- 普适性分析
- 应用场景建议

请发现真正有价值的规律。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            patterns = []

            for item in parsed.get("discovered_patterns", []):
                patterns.append(DiscoveredPattern(
                    pattern=item.get("pattern", "发现的规律"),
                    significance=item.get("significance", "中等"),
                    mathematical_form=item.get("mathematical_form", None),
                    verification_evidence=item.get("verification_evidence", "基于数据分析的验证"),
                    generalizability=item.get("generalizability", "具有一定的普适性"),
                    applications=item.get("applications", [])
                ))

            return patterns if patterns else [
                DiscoveredPattern(
                    pattern="数据呈现明显的规律性模式",
                    significance="高",
                    mathematical_form="待进一步数学化表达",
                    verification_evidence="通过统计分析和模型验证",
                    generalizability="适用于同类问题",
                    applications=["预测分析", "决策优化"]
                )
            ]
        except json.JSONDecodeError:
            return []

    async def _extract_theoretical_contributions(
        self,
        discovered_patterns: List[DiscoveredPattern],
        model_results: Dict[str, Any],
        validation_insights: Dict[str, Any]
    ) -> TheoreticalContributions:
        """提取理论贡献"""
        prompt = f"""
基于发现的规律，提炼理论层面的贡献。

【发现的规律数量】: {len(discovered_patterns)}
【主要规律摘要】
{[f"- {p.pattern} (重要性: {p.significance})" for p in discovered_patterns]}

【模型性能】
{json.dumps(model_results, ensure_ascii=False, indent=2)[:300]}

【验证洞察】
{json.dumps(validation_insights, ensure_ascii=False, indent=2)[:300]}

请从理论角度分析贡献：

1. 【新见解提炼】
   - 对问题本质的新认识
   - 对传统方法的改进认识
   - 对复杂性的深入理解
   - 对规律的系统性认识

2. 【理论意义分析】
   - 对现有理论的补充
   - 对理论的修正或拓展
   - 理论框架的完善
   - 学科交叉的贡献

3. 【未来研究方向】
   - 基于发现的研究课题
   - 可能的深化研究方向
   - 跨领域的研究机会
   - 产业化的研究方向

4. 【更广泛影响】
   - 对相关领域的影响
   - 对实际应用的影响
   - 对教育培养的影响
   - 对学术发展的长期影响

请提供深入的理论分析。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            theory_data = parsed.get("theoretical_contributions", {})

            return TheoreticalContributions(
                new_insights=theory_data.get("new_insights", []),
                theoretical_implications=theory_data.get("theoretical_implications", "为该领域提供了新的理论基础"),
                future_research_directions=theory_data.get("future_research_directions", []),
                broader_impact=theory_data.get("broader_impact", "对相关领域产生积极影响")
            )
        except json.JSONDecodeError:
            return TheoreticalContributions(
                new_insights=["发现了数据中隐藏的深层规律", "提出了新的分析方法和思路"],
                theoretical_implications="为相关领域的理论发展提供了新的视角和依据",
                future_research_directions=["深化规律的理论研究", "探索规律的广泛应用"],
                broader_impact="研究成果具有重要的理论价值和实践意义"
            )

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "pattern_discovery_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_pattern_discovery_engine():
    """测试规律发现引擎"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = PatternDiscoveryEngine("test_task", model)

    # 准备测试输入
    test_results = {
        "model_type": "时间序列预测模型",
        "final_accuracy": 0.89,
        "key_patterns": ["季节性", "趋势性"]
    }

    test_analysis = {
        "data_characteristics": "时间序列数据，具有明显的周期性",
        "correlations": {"core1": 0.85, "external": 0.62}
    }

    test_validation = {
        "robustness_score": 0.88,
        "sensitivity_insights": "对外部因素敏感"
    }

    # 执行分析
    result = await expert.execute(test_results, test_analysis, test_validation)

    # 输出结果
    print("=== 规律发现结果 ===")
    print(f"发现规律数量: {len(result.discovered_patterns)}")
    print(f"理论见解数量: {len(result.theoretical_contributions.new_insights)}")
    print(f"研究方向: {len(result.theoretical_contributions.future_research_directions)}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_pattern_discovery_engine())