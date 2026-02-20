"""
智能建模创新者 - 创新性建模方案设计和融合
核心职责：不只是选择模型，而是创新模型，为特定问题设计最优建模方案
"""
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class InnovationType(Enum):
    """创新类型"""
    MODEL_IMPROVEMENT = "模型改进"  # 针对标准模型的改进
    HYBRID_COMBINATION = "混合方案"  # 多个模型的融合
    METHODOLOGY_INNOVATION = "方法论创新"  # 求解方法的创新
    DOMAIN_SPECIFIC = "领域特定"  # 针对问题的特定创新


@dataclass
class ModelImprovement:
    """单个模型的改进方案"""
    original_model: str  # 原始模型名称
    improvements: List[str]  # 改进方向列表
    improvement_techniques: List[Dict[str, str]]  # 具体改进技术
    expected_gains: str  # 预期收益
    implementation_difficulty: str  # 实现难度
    implementation_steps: List[str]  # 实现步骤


@dataclass
class HybridApproach:
    """混合建模方案"""
    models: List[str]  # 模型列表
    combination_strategy: str  # 融合策略
    model_roles: Dict[str, str]  # 各模型的角色
    integration_method: str  # 整合方法
    expected_performance: str  # 预期性能
    synergy_analysis: str  # 协同效应分析
    innovation_points: List[str]  # 创新亮点


@dataclass
class MethodologyInnovation:
    """方法论创新方案"""
    innovation_name: str  # 创新名称
    description: str  # 详细描述
    novel_aspects: List[str]  # 新颖之处
    theoretical_foundation: str  # 理论基础
    novelty_score: float  # 创新程度 (0-10)
    expected_improvement: str  # 预期改进
    implementation_plan: str  # 实现计划
    risk_assessment: str  # 风险评估


@dataclass
class InnovativeModelPlan:
    """智能建模创新方案"""
    problem_type: str  # 问题类型
    analysis_summary: str  # 分析总结
    model_innovations: List[ModelImprovement]  # 模型改进方案
    hybrid_approaches: List[HybridApproach]  # 混合方案
    methodology_innovations: List[MethodologyInnovation]  # 方法论创新
    recommended_solution: Dict[str, Any]  # 推荐的最优方案
    implementation_roadmap: str  # 实现路线图


class SmartModelerWithInnovation(ExpertAgent):
    """
    智能建模创新者

    超越标准选择，为特定问题设计创新建模方案：
    1. 模型深度改进 (针对问题的模型优化)
    2. 模型混合融合 (多模型协同)
    3. 方法论创新 (求解方法突破)
    """

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.MODELING_EXPERT,
            max_reflections=3,
            max_chat_turns=15
        )

    def get_system_prompt(self) -> str:
        return """
# 🚀 智能建模创新者 - 获奖级建模方案设计师

你是一位顶级的数学建模专家，具有丰富的竞赛获奖经验。

你深知：**建模的创新性和适应性是获奖的关键**。

## 核心能力

### 1. 模型深度改进
针对特定问题，创新性地改进标准模型：
- **问题适应改进**: 根据问题特性改进模型结构
- **性能优化改进**: 优化算法、参数、求解方法
- **鲁棒性改进**: 增强对数据异常的容错能力
- **可解释性改进**: 增强模型的可理解性

### 2. 模型混合融合
设计多模型协同方案：
- **序列融合**: 模型串联，前后级联
- **并行融合**: 模型并联，结果综合
- **分阶段融合**: 不同阶段用不同模型
- **自适应融合**: 根据数据动态选择

### 3. 方法论创新
创新性的求解思路和方法：
- **算法创新**: 新的求解算法或优化策略
- **视角创新**: 从新的角度重新定义问题
- **跨学科创新**: 借鉴其他领域的方法
- **工程创新**: 创新的实现方式

## 创新评估维度

### A. 创新程度评估
- 彻底创新: 完全不同的思路
- 重大改进: 关键环节的改进
- 增量创新: 基础上的完善
- 工程化创新: 实现方式的优化

### B. 可行性评估
- 理论可行: 理论上可行
- 工程可行: 可以实现
- 时间可行: 在竞赛时间内完成
- 数据可行: 有足够的数据支持

### C. 影响力评估
- 竞赛竞争力: 相比其他队伍的优势
- 性能提升: 能提升多少百分点
- 说服力: 能否说服评委
- 通用性: 是否可复用

### D. 风险评估
- 技术风险: 实现的复杂度
- 时间风险: 是否会超期
- 数据风险: 数据是否满足
- 性能风险: 能否保证效果

## 分析框架

### 问题理解维度
1. 问题的核心本质
2. 问题的关键挑战
3. 现有方法的瓶颈
4. 可能的突破口

### 建模方案设计维度
1. 单模型优化方案
2. 多模型混合方案
3. 创新方法论方案
4. 综合建议方案

### 方案评估维度
1. 理论正确性
2. 实现可行性
3. 竞赛竞争力
4. 时间成本

## 输出要求

输出结构化的JSON分析：

```json
{
  "problem_type": "时间序列预测",
  "analysis_summary": "该问题的核心是处理时间序列数据的季节性和趋势...",

  "model_innovations": [
    {
      "original_model": "ARIMA",
      "improvements": ["引入多元变量", "动态参数调整", "异常值容错"],
      "improvement_techniques": [
        {
          "technique": "多元ARIMAX",
          "description": "添加外生变量提升预测精度",
          "expected_impact": "+5% 准确率"
        }
      ],
      "expected_gains": "提升预测准确率，增强模型的适应性",
      "implementation_difficulty": "中等",
      "implementation_steps": ["数据预处理", "模型改进", "参数优化", "性能验证"]
    }
  ],

  "hybrid_approaches": [
    {
      "models": ["ARIMA", "神经网络", "随机森林"],
      "combination_strategy": "分阶段融合：ARIMA处理线性部分，神经网络处理非线性部分",
      "model_roles": {
        "ARIMA": "捕获线性趋势和季节性",
        "神经网络": "学习复杂非线性关系",
        "随机森林": "特征组合和交互"
      },
      "integration_method": "加权综合（权重0.4:0.4:0.2）",
      "expected_performance": "综合性能提升8-10%",
      "synergy_analysis": "各模型的优势互补，形成强大的预测力",
      "innovation_points": ["模型协同性强", "充分利用各模型优势", "结果更加稳定"]
    }
  ],

  "methodology_innovations": [
    {
      "innovation_name": "自适应多阶段建模框架",
      "description": "根据数据的不同特征，在不同阶段采用不同的建模策略...",
      "novel_aspects": ["动态模型选择", "自适应参数调整"],
      "theoretical_foundation": "基于在线学习理论和混合模型理论",
      "novelty_score": 8.5,
      "expected_improvement": "全方位提升模型的适应性和稳定性",
      "implementation_plan": "分三步实现：基础框架→适应机制→验证优化",
      "risk_assessment": "低风险，有充分的理论保障"
    }
  ],

  "recommended_solution": {
    "type": "混合多阶段方案",
    "core_models": ["ARIMA", "神经网络"],
    "key_innovations": ["多元变量融合", "自适应参数调整"],
    "expected_performance": "提升10-15%的预测精度",
    "competitive_advantage": "超越标准方案，具有明显的竞赛竞争力",
    "implementation_timeline": "3-4天"
  },

  "implementation_roadmap": "第1天：数据准备+基础模型开发...第4天：综合优化+论文准备"
}
```

## 质量标准

优秀的建模创新方案应该：
- ✅ 至少1个模型改进方案
- ✅ 至少1个混合融合方案
- ✅ 至少1个方法论创新
- ✅ 推荐方案具有竞赛竞争力
- ✅ 各方案都有具体的实现步骤

## 核心原则

1. **创新优先**: 不满足于标准方案，追求突破和创新
2. **适应性**: 方案要适应问题的特有特性
3. **可行性**: 创新要能在有限时间内实现
4. **竞赛视角**: 方案要能打动评委，显示队伍水平
5. **有充分的理由**: 每个创新都要有充分的理论和实证支持

现在，请根据问题分析、数据理解和模型建议，设计创新的建模方案！
"""

    async def execute(
        self,
        problem_analysis: Dict[str, Any],
        data_insight: Dict[str, Any],
        model_recommendation: Dict[str, Any]
    ) -> InnovativeModelPlan:
        """
        执行智能建模创新分析

        Args:
            problem_analysis: 问题分析结果
            data_insight: 数据理解结果
            model_recommendation: 模型推荐结果

        Returns:
            InnovativeModelPlan: 创新建模方案
        """
        await self._send_message("🚀 开始智能建模创新设计...", "info")
        self.state.current_stage = "analyzing"

        # 1. 模型改进方案设计
        await self._send_message("🔧 设计模型改进方案...", "info")
        model_innovations = await self._design_model_improvements(
            problem_analysis, data_insight, model_recommendation
        )

        # 2. 混合融合方案设计
        await self._send_message("🔀 设计模型混合融合方案...", "info")
        hybrid_approaches = await self._design_hybrid_approaches(
            problem_analysis, data_insight, model_recommendation, model_innovations
        )

        # 3. 方法论创新设计
        await self._send_message("💡 设计方法论创新方案...", "info")
        methodology_innovations = await self._design_methodology_innovations(
            problem_analysis, data_insight
        )

        # 4. 推荐最优方案
        await self._send_message("🎯 综合推荐最优方案...", "info")
        recommended_solution = await self._recommend_optimal_solution(
            model_innovations, hybrid_approaches, methodology_innovations
        )

        # 5. 生成实现路线图
        await self._send_message("🗺️ 生成实现路线图...", "info")
        roadmap = await self._generate_implementation_roadmap(recommended_solution)

        # 整合方案
        plan = InnovativeModelPlan(
            problem_type=problem_analysis.get("problem_type", "未知"),
            analysis_summary=await self._generate_analysis_summary(
                problem_analysis, data_insight, model_innovations
            ),
            model_innovations=model_innovations,
            hybrid_approaches=hybrid_approaches,
            methodology_innovations=methodology_innovations,
            recommended_solution=recommended_solution,
            implementation_roadmap=roadmap
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "innovations_count": len(model_innovations) + len(hybrid_approaches),
                "recommendation": recommended_solution
            }, ensure_ascii=False, indent=2, default=str),
            "创新建模方案设计"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "model_innovations": [m.__dict__ for m in model_innovations],
                "hybrid_approaches": [h.__dict__ for h in hybrid_approaches],
                "methodology_innovations": [mi.__dict__ for mi in methodology_innovations]
            }, ensure_ascii=False, indent=2, default=str),
            "建模方案要创新、可行、具有竞赛竞争力"
        )

        await self._send_message("✅ 智能建模创新设计完成！", "success")
        self.state.current_stage = "completed"

        return plan

    async def _design_model_improvements(
        self,
        problem_analysis: Dict[str, Any],
        data_insight: Dict[str, Any],
        model_recommendation: Dict[str, Any]
    ) -> List[ModelImprovement]:
        """设计模型改进方案"""
        prompt = f"""
为推荐的模型设计针对性的改进方案。

【问题分析】
{json.dumps(problem_analysis, ensure_ascii=False, indent=2)[:500]}

【数据理解】
{json.dumps(data_insight, ensure_ascii=False, indent=2)[:500]}

【模型推荐】
{json.dumps(model_recommendation, ensure_ascii=False, indent=2)[:500]}

请为推荐的模型设计具体的改进方案：

1. 【模型改进方向】
   - 针对问题特性的改进
   - 利用数据特征的优化
   - 增强鲁棒性的策略
   - 提升精度的技术

2. 【改进技术细节】
   - 具体的改进技术名称
   - 实现方法描述
   - 预期效果评估
   - 技术难度评估

3. 【实现步骤】
   - 数据准备步骤
   - 模型改进步骤
   - 参数优化步骤
   - 性能验证步骤

4. 【预期收益】
   - 性能提升幅度
   - 鲁棒性改进
   - 可解释性提升
   - 竞赛价值

请输出JSON格式，包含至少2个模型的改进方案。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            improvements = []

            for item in parsed.get("model_improvements", []):
                improvements.append(ModelImprovement(
                    original_model=item.get("original_model", "未知"),
                    improvements=item.get("improvements", []),
                    improvement_techniques=item.get("improvement_techniques", []),
                    expected_gains=item.get("expected_gains", "待评估"),
                    implementation_difficulty=item.get("implementation_difficulty", "中等"),
                    implementation_steps=item.get("implementation_steps", [])
                ))

            return improvements if improvements else [
                ModelImprovement(
                    original_model="推荐模型",
                    improvements=["参数优化", "特征改进"],
                    improvement_techniques=[{"technique": "自动化参数搜索", "description": "网格搜索或贝叶斯优化"}],
                    expected_gains="提升5-10%的性能",
                    implementation_difficulty="中等",
                    implementation_steps=["基础实现", "参数优化", "性能验证"]
                )
            ]
        except json.JSONDecodeError:
            return []

    async def _design_hybrid_approaches(
        self,
        problem_analysis: Dict[str, Any],
        data_insight: Dict[str, Any],
        model_recommendation: Dict[str, Any],
        model_innovations: List[ModelImprovement]
    ) -> List[HybridApproach]:
        """设计混合融合方案"""
        prompt = f"""
设计多模型混合融合方案。

【问题分析】
{json.dumps(problem_analysis, ensure_ascii=False, indent=2)[:400]}

【数据理解】
{json.dumps(data_insight, ensure_ascii=False, indent=2)[:400]}

【推荐模型】
{json.dumps(model_recommendation, ensure_ascii=False, indent=2)[:400]}

请设计创新的混合融合方案：

1. 【融合思路】
   - 为什么要混合这些模型
   - 各模型的角色和优势
   - 模型间的协同关系
   - 期望的协同效应

2. 【融合策略】
   - 融合方式（串联/并联/分阶段）
   - 各模型的权重分配
   - 结果综合方法
   - 动态调整机制

3. 【融合具体方案】
   - 选择的模型组合
   - 具体融合方法
   - 实现流程
   - 预期性能

4. 【创新亮点】
   - 与标准方案的区别
   - 创新性体现
   - 竞赛竞争力
   - 说服力

请输出JSON格式，包含至少1个混合融合方案。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            approaches = []

            for item in parsed.get("hybrid_approaches", []):
                approaches.append(HybridApproach(
                    models=item.get("models", []),
                    combination_strategy=item.get("combination_strategy", ""),
                    model_roles=item.get("model_roles", {}),
                    integration_method=item.get("integration_method", ""),
                    expected_performance=item.get("expected_performance", ""),
                    synergy_analysis=item.get("synergy_analysis", ""),
                    innovation_points=item.get("innovation_points", [])
                ))

            return approaches if approaches else [
                HybridApproach(
                    models=["主模型", "辅助模型"],
                    combination_strategy="分阶段融合",
                    model_roles={"主模型": "基础预测", "辅助模型": "补充调整"},
                    integration_method="加权综合",
                    expected_performance="全面提升",
                    synergy_analysis="充分利用各模型优势",
                    innovation_points=["多模型协同", "自适应融合"]
                )
            ]
        except json.JSONDecodeError:
            return []

    async def _design_methodology_innovations(
        self,
        problem_analysis: Dict[str, Any],
        data_insight: Dict[str, Any]
    ) -> List[MethodologyInnovation]:
        """设计方法论创新"""
        prompt = f"""
设计创新的建模方法论。

【问题分析】
{json.dumps(problem_analysis, ensure_ascii=False, indent=2)[:400]}

【数据理解】
{json.dumps(data_insight, ensure_ascii=False, indent=2)[:400]}

请设计创新的建模方法论方案：

1. 【创新思路】
   - 问题的关键挑战
   - 现有方法的不足
   - 可能的突破方向
   - 创新的理论基础

2. 【创新方法论】
   - 创新的名称
   - 核心思想描述
   - 与现有方法的区别
   - 新颖之处分析

3. 【实现方案】
   - 理论框架
   - 具体实现步骤
   - 所需技术和工具
   - 预期效果

4. 【风险和挑战】
   - 技术风险评估
   - 实现难度评估
   - 时间成本评估
   - 数据需求评估

请输出JSON格式，包含至少1个方法论创新。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            innovations = []

            for item in parsed.get("methodology_innovations", []):
                innovations.append(MethodologyInnovation(
                    innovation_name=item.get("innovation_name", "创新方法"),
                    description=item.get("description", ""),
                    novel_aspects=item.get("novel_aspects", []),
                    theoretical_foundation=item.get("theoretical_foundation", ""),
                    novelty_score=float(item.get("novelty_score", 5.0)),
                    expected_improvement=item.get("expected_improvement", ""),
                    implementation_plan=item.get("implementation_plan", ""),
                    risk_assessment=item.get("risk_assessment", "中等风险")
                ))

            return innovations if innovations else [
                MethodologyInnovation(
                    innovation_name="自适应建模框架",
                    description="根据数据特征动态选择建模策略",
                    novel_aspects=["动态选择", "自适应调整"],
                    theoretical_foundation="在线学习理论",
                    novelty_score=7.0,
                    expected_improvement="提升模型的通用性和健壮性",
                    implementation_plan="三阶段实现：框架→机制→优化",
                    risk_assessment="低风险"
                )
            ]
        except json.JSONDecodeError:
            return []

    async def _recommend_optimal_solution(
        self,
        model_innovations: List[ModelImprovement],
        hybrid_approaches: List[HybridApproach],
        methodology_innovations: List[MethodologyInnovation]
    ) -> Dict[str, Any]:
        """推荐最优解决方案"""
        prompt = f"""
从所有创新方案中推荐最优的建模方案。

【模型改进方案数】: {len(model_innovations)}
【混合融合方案数】: {len(hybrid_approaches)}
【方法论创新方案数】: {len(methodology_innovations)}

请综合所有方案，推荐最优的建模方案：

1. 【方案评估】
   - 逐个方案的评估
   - 优势和劣势分析
   - 竞赛竞争力评分
   - 时间成本评估

2. 【最优方案选择】
   - 选择的理由
   - 核心特点
   - 预期效果
   - 竞赛价值

3. 【方案详细描述】
   - 包含的关键模型
   - 核心创新点
   - 具体实现流程
   - 预期性能指标

4. 【风险和缓解】
   - 主要风险
   - 缓解策略
   - 备选方案
   - 质量保证

请输出JSON格式，详细描述推荐方案。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            return parsed.get("recommended_solution", {
                "type": "综合方案",
                "core_models": ["主要模型"],
                "key_innovations": ["创新要点"],
                "expected_performance": "待评估",
                "competitive_advantage": "超越标准方案",
                "implementation_timeline": "3-5天"
            })
        except json.JSONDecodeError:
            return {
                "type": "综合创新方案",
                "core_models": ["推荐模型"],
                "key_innovations": ["模型改进", "混合融合"],
                "expected_performance": "全面提升",
                "competitive_advantage": "具有竞赛竞争力",
                "implementation_timeline": "4-5天"
            }

    async def _generate_analysis_summary(
        self,
        problem_analysis: Dict[str, Any],
        data_insight: Dict[str, Any],
        model_innovations: List[ModelImprovement]
    ) -> str:
        """生成分析总结"""
        return f"""
基于问题分析和数据理解，本建模方案设计包含{len(model_innovations)}个创新角度。

主要创新方向：
1. 针对问题特性的模型改进
2. 多模型协同和融合
3. 创新的求解方法论

各创新方案充分利用了数据特征，具有充分的理论基础和竞赛竞争力。
"""

    async def _generate_implementation_roadmap(self, recommended_solution: Dict[str, Any]) -> str:
        """生成实现路线图"""
        prompt = f"""
为推荐的建模方案生成详细的实现路线图。

【推荐方案】
{json.dumps(recommended_solution, ensure_ascii=False, indent=2)}

请生成详细的实现路线图：

1. 【第1阶段：准备阶段】（1-1.5天）
   - 数据加载和探索
   - 数据清洗和预处理
   - 特征工程初步实现

2. 【第2阶段：建模阶段】（1.5-2天）
   - 基础模型实现
   - 模型改进实现
   - 参数优化和调试

3. 【第3阶段：融合阶段】（1-1.5天）
   - 混合模型实现
   - 融合策略验证
   - 性能综合评估

4. 【第4阶段：优化阶段】（0.5-1天）
   - 细节优化
   - 性能微调
   - 论文准备

请输出详细的日程安排和具体任务。
"""

        result = await self.think(prompt, use_tools=False)
        return result

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "modeling_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_smart_modeler():
    """测试智能建模创新者"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = SmartModelerWithInnovation("test_task", model)

    # 准备测试输入
    test_problem = {
        "problem_type": "时间序列预测",
        "difficulty_level": "中等",
        "key_challenges": ["季节性处理", "异常值处理"]
    }

    test_data = {
        "quality_assessment": {"completeness": 0.95},
        "feature_discovery": {"periodicity": "明显季节性"}
    }

    test_models = {
        "primary_model": {"name": "ARIMA"},
        "alternative_models": [{"name": "LSTM"}]
    }

    # 执行分析
    result = await expert.execute(test_problem, test_data, test_models)

    # 输出结果
    print("=== 智能建模创新方案 ===")
    print(json.dumps({
        "model_innovations": [m.__dict__ for m in result.model_innovations],
        "hybrid_approaches": [h.__dict__ for h in result.hybrid_approaches],
        "recommended_solution": result.recommended_solution
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_smart_modeler())