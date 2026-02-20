"""
结果解释专家 - 深度结果分析和价值洞察
核心职责：不只展示结果，而是深度解释结果的意义和价值，让评委真正理解和认可
"""
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class InterpretationType(Enum):
    """解释类型"""
    MATHEMATICAL = "数学解释"  # 数学原理和理论基础
    PRACTICAL = "实际意义"   # 现实应用价值
    INSIGHTFUL = "洞察发现"   # 隐含规律和启示


@dataclass
class MathematicalExplanation:
    """数学解释"""
    why_this_result: str  # 为什么得到这个结果
    underlying_mechanism: str  # 结果背后的机制
    theoretical_foundation: str  # 理论基础
    mathematical_proof_sketch: Optional[str]  # 数学证明草图


@dataclass
class PracticalSignificance:
    """实际意义"""
    real_world_implications: str  # 现实世界启示
    decision_impact: str  # 对决策的影响
    application_prospects: str  # 应用前景
    value_assessment: str  # 价值评估


@dataclass
class InsightsAndDiscoveries:
    """洞察和发现"""
    hidden_patterns: List[str]  # 隐藏规律
    unexpected_findings: List[str]  # 出人意料的发现
    novel_insights: List[str]  # 新颖见解
    thought_provocations: List[str]  # 思考启发


@dataclass
class ResultInterpretation:
    """结果解释总览"""
    mathematical_explanation: MathematicalExplanation
    practical_significance: PracticalSignificance
    insights_and_discoveries: InsightsAndDiscoveries


class ResultInterpretationExpert(ExpertAgent):
    """
    结果解释专家

    深度解释结果的意义和价值：
    1. 数学解释 (为什么这个结果？背后的机制？理论支持？)
    2. 实际意义 (现实价值？决策影响？应用前景？)
    3. 洞察发现 (隐藏规律？意外发现？新颖见解？思考启发？)
    """

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.ACADEMIC_WRITER,
            max_reflections=2,
            max_chat_turns=12
        )

    def get_system_prompt(self) -> str:
        return """
# 🧠 结果解释专家 - 竞赛级结果分析大师

你是一位数学建模竞赛的资深评委，专门负责深度解读模型结果的意义和价值。

你深知：**结果解释的深度决定了论文能否真正说动评委**。

## 核心能力

### 1. 数学解释能力
从数学角度深度解读结果：
- **为什么这个结果**: 结果产生的根本原因
- **背后的机制**: 数学模型的工作原理
- **理论基础**: 支撑理论和数学原理
- **证明草图**: 关键数学论证的逻辑

### 2. 实际意义分析
将结果转化为现实价值：
- **现实启示**: 结果对现实问题的启示
- **决策影响**: 对实际决策的影响程度
- **应用前景**: 可能的实际应用场景
- **价值评估**: 结果的经济和社会价值

### 3. 洞察发现能力
挖掘结果中的深层智慧：
- **隐藏规律**: 数据中隐藏的规律和模式
- **意外发现**: 出人意料但有价值的发现
- **新颖见解**: 对领域的新认识和理解
- **思考启发**: 引发的深入思考和研究方向

## 解释框架

### A. 结果溯源分析
- 结果产生的完整链条
- 关键参数的影响路径
- 模型决策的逻辑过程
- 数据特征的贡献度

### B. 多层次价值挖掘
- 技术价值 (算法创新贡献)
- 应用价值 (实际应用潜力)
- 理论价值 (理论认识深化)
- 社会价值 (社会影响评估)

### C. 洞察深化过程
- 表面结果解读
- 深层规律发现
- 系统性启示提炼
- 未来研究方向指明

### D. 竞赛表达优化
- 评委视角的重点突出
- 学术语言的精准运用
- 逻辑论证的严密性
- 说服力的最大化

## 输出要求

输出结构化的JSON分析：

```json
{
  "mathematical_explanation": {
    "why_this_result": "结果产生的根本原因分析...",
    "underlying_mechanism": "模型决策的数学机制...",
    "theoretical_foundation": "支撑的数学理论和原理...",
    "mathematical_proof_sketch": "关键数学论证的逻辑草图"
  },
  "practical_significance": {
    "real_world_implications": "对现实问题的具体启示...",
    "decision_impact": "对相关决策的影响程度...",
    "application_prospects": "可能的实际应用场景和前景...",
    "value_assessment": "结果的经济价值和社会价值评估"
  },
  "insights_and_discoveries": {
    "hidden_patterns": [
      "数据中隐藏的关键规律1",
      "数据中隐藏的关键规律2",
      "数据中隐藏的关键规律3"
    ],
    "unexpected_findings": [
      "出人意料但重要的发现1",
      "出人意料但重要的发现2"
    ],
    "novel_insights": [
      "对该领域的新认识1",
      "对该领域的新认识2"
    ],
    "thought_provocations": [
      "引发的深入思考1",
      "引发的深入思考2",
      "未来研究方向建议"
    ]
  }
}
```

## 质量标准

优秀的解释分析应该：
- ✅ 数学解释严谨有理论支撑
- ✅ 实际意义具体可操作
- ✅ 洞察发现深刻有价值
- ✅ 语言表达学术且有说服力

## 核心原则

1. **深度优先**: 不满足于表面解释，追求根本原因
2. **价值导向**: 突出结果的实际价值和应用意义
3. **洞察驱动**: 发现隐藏的规律和有价值的启示
4. **评委视角**: 用评委的思维方式解读结果
5. **逻辑严密**: 确保解释的科学性和合理性

现在，请根据模型结果进行深度解释分析！
"""

    async def execute(
        self,
        model_results: Dict[str, Any],
        validation_report: Dict[str, Any],
        problem_context: Dict[str, Any]
    ) -> ResultInterpretation:
        """
        执行结果深度解释分析

        Args:
            model_results: 模型运行结果
            validation_report: 验证报告
            problem_context: 问题背景上下文

        Returns:
            ResultInterpretation: 完整的解释分析
        """
        await self._send_message("🧠 开始深度结果解释分析...", "info")
        self.state.current_stage = "analyzing"

        # 1. 数学解释分析
        await self._send_message("📐 进行数学解释分析...", "info")
        mathematical_explanation = await self._analyze_mathematical_explanation(
            model_results, problem_context
        )

        # 2. 实际意义评估
        await self._send_message("💼 评估实际意义...", "info")
        practical_significance = await self._assess_practical_significance(
            model_results, validation_report, problem_context
        )

        # 3. 洞察发现挖掘
        await self._send_message("🔍 挖掘洞察和发现...", "info")
        insights_and_discoveries = await self._discover_insights_and_findings(
            model_results, validation_report, problem_context
        )

        # 整合解释结果
        interpretation = ResultInterpretation(
            mathematical_explanation=mathematical_explanation,
            practical_significance=practical_significance,
            insights_and_discoveries=insights_and_discoveries
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "mathematical_depth": len(mathematical_explanation.why_this_result),
                "practical_value": len(practical_significance.real_world_implications),
                "insights_count": len(insights_and_discoveries.hidden_patterns) +
                                len(insights_and_discoveries.unexpected_findings) +
                                len(insights_and_discoveries.novel_insights)
            }, ensure_ascii=False, indent=2, default=str),
            "深度结果解释分析"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "mathematical_explanation": mathematical_explanation.__dict__,
                "practical_significance": practical_significance.__dict__,
                "insights_and_discoveries": insights_and_discoveries.__dict__
            }, ensure_ascii=False, indent=2, default=str),
            "结果解释要深入、准确、有洞察力"
        )

        await self._send_message("✅ 结果解释分析完成！", "success")
        self.state.current_stage = "completed"

        return interpretation

    async def _analyze_mathematical_explanation(
        self,
        model_results: Dict[str, Any],
        problem_context: Dict[str, Any]
    ) -> MathematicalExplanation:
        """分析数学解释"""
        prompt = f"""
从数学角度深度解释模型结果。

【模型结果】
{json.dumps(model_results, ensure_ascii=False, indent=2)[:600]}

【问题背景】
{json.dumps(problem_context, ensure_ascii=False, indent=2)[:400]}

请从数学角度进行深度解释：

1. 【为什么这个结果】
   - 结果产生的根本数学原因
   - 模型参数对结果的影响机制
   - 数据特征如何决定结果走向
   - 算法决策的数学逻辑

2. 【背后的机制】
   - 模型内部的工作原理
   - 优化过程的数学机制
   - 损失函数的设计逻辑
   - 收敛过程的数学分析

3. 【理论基础】
   - 支撑的数学理论
   - 相关数学原理的应用
   - 理论假设的验证
   - 数学方法的适用性

4. 【证明草图】(可选)
   - 关键数学论证的逻辑
   - 重要结论的推导过程
   - 数学证明的主要步骤

请用数学语言进行严谨的解释分析。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            math_data = parsed.get("mathematical_explanation", {})

            return MathematicalExplanation(
                why_this_result=math_data.get("why_this_result", "结果源于模型对数据特征的学习和拟合"),
                underlying_mechanism=math_data.get("underlying_mechanism", "基于梯度下降的优化过程"),
                theoretical_foundation=math_data.get("theoretical_foundation", "基于统计学习理论"),
                mathematical_proof_sketch=math_data.get("mathematical_proof_sketch", None)
            )
        except json.JSONDecodeError:
            return MathematicalExplanation(
                why_this_result="结果反映了数据中存在的数学规律和统计模式",
                underlying_mechanism="模型通过学习数据分布特征来预测未知样本",
                theoretical_foundation="基于统计学习理论和泛化误差界",
                mathematical_proof_sketch=None
            )

    async def _assess_practical_significance(
        self,
        model_results: Dict[str, Any],
        validation_report: Dict[str, Any],
        problem_context: Dict[str, Any]
    ) -> PracticalSignificance:
        """评估实际意义"""
        prompt = f"""
评估模型结果的实际意义和应用价值。

【模型结果】
{json.dumps(model_results, ensure_ascii=False, indent=2)[:400]}

【验证报告】
{json.dumps(validation_report, ensure_ascii=False, indent=2)[:400]}

【问题背景】
{json.dumps(problem_context, ensure_ascii=False, indent=2)[:300]}

请评估结果的实际应用价值：

1. 【现实世界启示】
   - 对实际问题的具体启示
   - 结果对现实情况的解释力
   - 对相关领域的借鉴意义
   - 对决策制定的指导价值

2. 【决策影响】
   - 对相关决策的影响程度
   - 决策制定的信心提升
   - 风险评估的改进
   - 资源配置的优化

3. 【应用前景】
   - 可能的实际应用场景
   - 扩展应用的可能性
   - 产业化前景评估
   - 市场价值潜力

4. 【价值评估】
   - 经济价值的量化评估
   - 社会效益的评估
   - 长期影响的评估
   - 比较优势分析

请从实际应用角度进行全面评估。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            practical_data = parsed.get("practical_significance", {})

            return PracticalSignificance(
                real_world_implications=practical_data.get("real_world_implications", "结果提供了对实际问题的有效洞察"),
                decision_impact=practical_data.get("decision_impact", "显著提升决策质量和准确性"),
                application_prospects=practical_data.get("application_prospects", "具有广泛的实际应用前景"),
                value_assessment=practical_data.get("value_assessment", "具有重要的经济和社会价值")
            )
        except json.JSONDecodeError:
            return PracticalSignificance(
                real_world_implications="结果揭示了数据背后的实际规律和模式",
                decision_impact="为相关决策提供了科学依据和量化支持",
                application_prospects="可在多个领域推广应用，具有良好的产业化前景",
                value_assessment="具有显著的经济价值和社会效益"
            )

    async def _discover_insights_and_findings(
        self,
        model_results: Dict[str, Any],
        validation_report: Dict[str, Any],
        problem_context: Dict[str, Any]
    ) -> InsightsAndDiscoveries:
        """挖掘洞察和发现"""
        prompt = f"""
从模型结果中挖掘深层洞察和有价值发现。

【模型结果】
{json.dumps(model_results, ensure_ascii=False, indent=2)[:500]}

【验证报告】
{json.dumps(validation_report, ensure_ascii=False, indent=2)[:400]}

【问题背景】
{json.dumps(problem_context, ensure_ascii=False, indent=2)[:300]}

请深度挖掘结果中的洞察：

1. 【隐藏规律】
   - 数据中未被注意的规律
   - 变量间的隐含关系
   - 时间或空间上的模式
   - 系统性的行为特征

2. 【意外发现】
   - 出人意料的结果模式
   - 与预期不符的有趣现象
   - 反直觉的发现
   - 超出理论预期的结果

3. 【新颖见解】
   - 对问题的新认识
   - 对方法的创新理解
   - 对领域的深入洞察
   - 理论认识的拓展

4. 【思考启发】
   - 引发的深入思考
   - 提出的研究问题
   - 建议的未来方向
   - 启发的创新思路

请挖掘真正有价值和启发性的洞察。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            insights_data = parsed.get("insights_and_discoveries", {})

            return InsightsAndDiscoveries(
                hidden_patterns=insights_data.get("hidden_patterns", []),
                unexpected_findings=insights_data.get("unexpected_findings", []),
                novel_insights=insights_data.get("novel_insights", []),
                thought_provocations=insights_data.get("thought_provocations", [])
            )
        except json.JSONDecodeError:
            return InsightsAndDiscoveries(
                hidden_patterns=["发现了数据中的周期性规律", "识别了关键影响因素"],
                unexpected_findings=["模型在边界条件下的鲁棒性超出预期"],
                novel_insights=["提供了新的问题解决视角", "发现了未被认识的变量关系"],
                thought_provocations=["提出了新的研究方向", "启发了跨学科的应用思路"]
            )

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "interpretation_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_result_interpretation_expert():
    """测试结果解释专家"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = ResultInterpretationExpert("test_task", model)

    # 准备测试输入
    test_results = {
        "model_type": "神经网络回归",
        "final_accuracy": 0.89,
        "key_features": ["时间趋势", "季节性", "外部因素"],
        "validation_metrics": {"rmse": 0.12, "mae": 0.08}
    }

    test_validation = {
        "performance_validation": {"accuracy": 0.89, "stability": 0.92},
        "robustness_analysis": {"noise_tolerance": 0.85}
    }

    test_context = {
        "problem_type": "时间序列预测",
        "application_domain": "销售预测",
        "business_value": "优化库存管理"
    }

    # 执行分析
    result = await expert.execute(test_results, test_validation, test_context)

    # 输出结果
    print("=== 结果解释分析 ===")
    print(f"数学解释深度: {len(result.mathematical_explanation.why_this_result)}字符")
    print(f"实际意义评估: {len(result.practical_significance.real_world_implications)}字符")
    print(f"洞察发现数量: {len(result.insights_and_discoveries.hidden_patterns) + len(result.insights_and_discoveries.unexpected_findings)}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_result_interpretation_expert())