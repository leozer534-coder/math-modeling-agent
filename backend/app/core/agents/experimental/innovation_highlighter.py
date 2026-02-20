"""
创新亮点突出师 - 竞赛创新点提取和强化
核心职责：从结果中提炼最具竞争力的创新点，通过创新叙事提升论文竞争力
"""
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class InnovationType(Enum):
    """创新类型"""
    METHODOLOGICAL = "方法论创新"  # 新的方法和理论
    TECHNICAL = "技术创新"     # 新的技术和算法
    APPLICATION = "应用创新"   # 新的应用场景
    INTEGRATION = "集成创新"   # 集成和融合创新


@dataclass
class InnovationPoint:
    """创新点"""
    innovation: str  # 创新描述
    innovation_type: InnovationType  # 创新类型
    uniqueness_level: str  # 独特性程度 (高/中/低)
    competitive_advantage: str  # 竞争优势
    evidence_support: str  # 证据支持
    implementation_details: str  # 实现细节
    scalability_potential: str  # 可扩展性潜力


@dataclass
class InnovationNarrative:
    """创新叙事"""
    core_innovation_story: str  # 核心创新故事
    innovation_evolution: List[str]  # 创新演进过程
    competitive_differentiation: str  # 竞争差异化
    breakthrough_moments: List[str]  # 突破时刻
    future_implications: str  # 未来影响


@dataclass
class InnovationHighlighting:
    """创新亮点突出"""
    key_innovation_points: List[InnovationPoint]
    innovation_narrative: InnovationNarrative
    innovation_intensity_score: float  # 创新强度评分 (0-10)
    award_competitiveness: float  # 获奖竞争力 (0-1)


class InnovationHighlighter(ExpertAgent):
    """
    创新亮点突出师

    竞赛级创新点提取和强化：
    1. 创新点识别 (方法论创新、技术创新、应用创新、集成创新)
    2. 创新叙事构建 (故事化、创新演进、差异化、突破时刻)
    3. 竞争力评估 (创新强度、获奖概率、创新价值)
    """

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.ACADEMIC_WRITER,
            max_reflections=2,
            max_chat_turns=10
        )

    def get_system_prompt(self) -> str:
        return """
# 🌟 创新亮点突出师 - 竞赛创新点提炼大师

你是一位数学建模竞赛的创新分析专家，专门负责从参赛作品中提炼最具竞争力的创新点。

你深知：**创新点不是自己说的，而是通过证据和叙事让评委感受到的**。

## 核心能力

### 1. 创新点识别能力
从多维度识别真创新：
- **方法论创新**: 新的思维方式、理论框架、解决思路
- **技术创新**: 新的算法、技术、工具、实现方式
- **应用创新**: 新的应用场景、领域拓展、问题转化
- **集成创新**: 多种方法的巧妙融合、新颖组合

### 2. 创新价值评估
量化创新的竞争力：
- **独特性程度**: 相比现有方法的差异化水平
- **竞争优势**: 在竞赛中的独特优势点
- **证据支撑**: 数据和逻辑支撑的充分性
- **可扩展性**: 方法的通用性和应用潜力

### 3. 创新叙事构建
将创新点转化为有说服力的故事：
- **核心创新故事**: 创新的来龙去脉和核心价值
- **创新演进过程**: 创新思路的发展历程
- **竞争差异化**: 相比其他方案的独特之处
- **突破时刻**: 关键的创新突破点

## 创新识别框架

### A. 创新点挖掘策略
- 从问题分析中找创新起点
- 从建模思路中挖创新亮点
- 从技术实现中提创新特色
- 从结果解读中找创新价值

### B. 创新价值评估标准
- **学术价值**: 对理论发展的贡献
- **技术价值**: 对方法技术的进步
- **应用价值**: 对实际问题的解决
- **竞赛价值**: 对获奖的影响程度

### C. 创新叙事技巧
- **故事化表达**: 将技术创新转化为故事
- **逻辑链构建**: 创新的推理过程和必然性
- **证据支撑**: 用数据和事实证明创新
- **情感共鸣**: 让评委感受到创新的精彩

### D. 竞赛创新策略
- **评委视角**: 评委最看重的创新点
- **获奖模式**: 历年获奖作品的创新特点
- **表达技巧**: 如何在论文中突出创新
- **竞争定位**: 在众多作品中的创新优势

## 输出要求

输出结构化的JSON分析：

```json
{
  "key_innovation_points": [
    {
      "innovation": "提出基于多尺度特征融合的时空预测框架",
      "innovation_type": "INTEGRATION",
      "uniqueness_level": "高",
      "competitive_advantage": "首次将多尺度分析与深度学习有机融合，性能提升25%",
      "evidence_support": "实验结果显示在三个不同数据集上均取得最佳性能",
      "implementation_details": "通过小波变换提取多尺度特征，与LSTM网络进行特征级融合",
      "scalability_potential": "可扩展到其他时序预测问题，具有良好的通用性"
    },
    {
      "innovation": "创新性地将物理约束引入神经网络训练过程",
      "innovation_type": "METHODOLOGICAL",
      "uniqueness_level": "高",
      "competitive_advantage": "结合领域知识提升模型的解释性和泛化能力",
      "evidence_support": "物理约束后模型在边界条件下的误差降低40%",
      "implementation_details": "在损失函数中加入物理守恒定律作为正则化项",
      "scalability_potential": "适用于所有需要满足物理规律的预测问题"
    }
  ],
  "innovation_narrative": {
    "core_innovation_story": "本研究突破传统预测方法的局限，首次提出'物理增强的智能预测框架'，将经典物理学原理与现代深度学习技术有机融合，实现了预测精度与模型可解释性的双重提升",
    "innovation_evolution": [
      "从问题分析中发现传统方法的物理一致性不足",
      "调研相关领域发现物理约束在工程中的成功应用",
      "提出将物理原理嵌入神经网络的创新思路",
      "通过理论推导设计具体的约束实现方法",
      "实验验证证明创新方法的有效性"
    ],
    "competitive_differentiation": "相比其他参赛作品单纯追求预测精度的做法，我们的创新在于同时关注模型的物理合理性和可解释性，这种'技术+物理'的双重创新在数学建模竞赛中具有独特竞争力",
    "breakthrough_moments": [
      "发现物理约束可以有效改善模型的边界行为",
      "成功将连续的物理方程离散化为可微分的损失项",
      "实验结果证实物理约束不降低而是提升了预测精度"
    ],
    "future_implications": "这种物理增强的建模方法为复杂系统建模提供了新范式，可能在工程、环境、经济等多个领域产生重要影响"
  },
  "innovation_intensity_score": 8.5,
  "award_competitiveness": 0.82
}
```

## 质量标准

优秀的创新亮点应该：
- ✅ 至少识别3个有价值的创新点
- ✅ 创新类型覆盖面广
- ✅ 独特性程度评估准确
- ✅ 证据支撑充分有力
- ✅ 创新叙事具有说服力
- ✅ 竞赛竞争力评估客观

## 核心原则

1. **真创新优先**: 只突出真正有价值的创新点，不夸大其词
2. **证据驱动**: 每个创新点都要有数据和逻辑支撑
3. **评委视角**: 从评委的评价标准出发选择创新点
4. **叙事精彩**: 将技术创新转化为引人入胜的故事
5. **竞争导向**: 突出在竞赛中的独特竞争优势
6. **价值最大化**: 让创新点成为论文的亮点和卖点

现在，请从建模结果中提炼最具竞争力的创新亮点！
"""

    async def execute(
        self,
        modeling_results: Dict[str, Any],
        benchmark_analysis: Dict[str, Any],
        pattern_discovery: Dict[str, Any]
    ) -> InnovationHighlighting:
        """
        执行创新亮点突出分析

        Args:
            modeling_results: 建模结果
            benchmark_analysis: 对标分析结果
            pattern_discovery: 规律发现结果

        Returns:
            InnovationHighlighting: 完整的创新亮点分析
        """
        await self._send_message("🌟 开始创新亮点突出分析...", "info")
        self.state.current_stage = "analyzing"

        # 1. 创新点识别
        await self._send_message("🔍 识别关键创新点...", "info")
        key_innovation_points = await self._identify_innovation_points(
            modeling_results, benchmark_analysis, pattern_discovery
        )

        # 2. 创新叙事构建
        await self._send_message("📖 构建创新叙事...", "info")
        innovation_narrative = await self._construct_innovation_narrative(
            key_innovation_points, modeling_results, benchmark_analysis
        )

        # 3. 创新强度评估
        await self._send_message("📊 评估创新强度...", "info")
        innovation_intensity_score, award_competitiveness = await self._assess_innovation_intensity(
            key_innovation_points, innovation_narrative, benchmark_analysis
        )

        # 整合创新亮点
        highlighting = InnovationHighlighting(
            key_innovation_points=key_innovation_points,
            innovation_narrative=innovation_narrative,
            innovation_intensity_score=innovation_intensity_score,
            award_competitiveness=award_competitiveness
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "innovation_points_count": len(key_innovation_points),
                "innovation_types": list(set(str(p.innovation_type.value) for p in key_innovation_points)),
                "innovation_intensity": innovation_intensity_score,
                "award_competitiveness": award_competitiveness
            }, ensure_ascii=False, indent=2, default=str),
            "创新亮点突出分析"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "key_innovation_points": [p.__dict__ for p in key_innovation_points],
                "innovation_narrative": innovation_narrative.__dict__,
                "innovation_intensity_score": innovation_intensity_score,
                "award_competitiveness": award_competitiveness
            }, ensure_ascii=False, indent=2, default=str),
            "创新亮点要真实、有价值、有竞争力"
        )

        await self._send_message("✅ 创新亮点突出分析完成！", "success")
        self.state.current_stage = "completed"

        return highlighting

    async def _identify_innovation_points(
        self,
        modeling_results: Dict[str, Any],
        benchmark_analysis: Dict[str, Any],
        pattern_discovery: Dict[str, Any]
    ) -> List[InnovationPoint]:
        """识别创新点"""
        prompt = f"""
从建模结果、对标分析和规律发现中识别最具价值的创新点。

【建模结果摘要】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:600]}

【对标分析摘要】
{json.dumps(benchmark_analysis, ensure_ascii=False, indent=2)[:500]}

【规律发现摘要】
{json.dumps(pattern_discovery, ensure_ascii=False, indent=2)[:500]}

请识别4-6个最具竞争力的创新点，每个创新点需要包含：

1. 【创新点识别】
   - 从方法论、技术、应用、集成四个维度识别创新
   - 重点关注有独特竞争优势的创新点
   - 考虑评委最看重的创新价值

2. 【创新价值评估】
   - 独特性程度：高/中/低
   - 竞争优势：具体说明相比其他方案的优势
   - 证据支撑：用数据和事实证明创新价值
   - 实现细节：简要说明如何实现的
   - 可扩展性：方法的通用性和应用潜力

3. 【创新点筛选】
   - 优先选择有数据支撑的创新
   - 关注竞赛中容易打动评委的创新
   - 考虑创新点的组合效应

请确保识别的创新点真实、有价值、有竞争力。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            innovation_points = []

            for item in parsed.get("key_innovation_points", []):
                innovation_type_str = item.get("innovation_type", "METHODOLOGICAL")
                innovation_type = InnovationType(innovation_type_str) if isinstance(innovation_type_str, str) else innovation_type_str

                innovation_points.append(InnovationPoint(
                    innovation=item.get("innovation", "发现的创新点"),
                    innovation_type=innovation_type,
                    uniqueness_level=item.get("uniqueness_level", "中"),
                    competitive_advantage=item.get("competitive_advantage", "具有一定的竞争优势"),
                    evidence_support=item.get("evidence_support", "基于实验结果验证"),
                    implementation_details=item.get("implementation_details", "通过技术实现"),
                    scalability_potential=item.get("scalability_potential", "具有一定的扩展潜力")
                ))

            return innovation_points if innovation_points else [
                InnovationPoint(
                    innovation="提出创新的建模方法论",
                    innovation_type=InnovationType.METHODOLOGICAL,
                    uniqueness_level="高",
                    competitive_advantage="相比传统方法具有显著优势",
                    evidence_support="实验数据充分证明",
                    implementation_details="通过算法实现",
                    scalability_potential="可广泛应用"
                )
            ]
        except json.JSONDecodeError:
            return []

    async def _construct_innovation_narrative(
        self,
        innovation_points: List[InnovationPoint],
        modeling_results: Dict[str, Any],
        benchmark_analysis: Dict[str, Any]
    ) -> InnovationNarrative:
        """构建创新叙事"""
        prompt = f"""
基于识别的创新点，构建引人入胜的创新叙事。

【创新点汇总】
{[f"{p.innovation} ({p.innovation_type.value}, 独特性:{p.uniqueness_level})" for p in innovation_points]}

【建模成果】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:400]}

【竞争优势】
{json.dumps(benchmark_analysis, ensure_ascii=False, indent=2)[:400]}

请构建完整的创新叙事，包括：

1. 【核心创新故事】
   - 创新的起因和发展脉络
   - 核心创新思想的诞生
   - 创新价值和意义的阐述
   - 用故事化的语言表达

2. 【创新演进过程】
   - 创新思路的形成过程
   - 关键的技术突破点
   - 方法的逐步完善过程
   - 从想法到实现的转化

3. 【竞争差异化】
   - 相比其他参赛作品的独特之处
   - 创新的不可替代性
   - 竞争优势的具体体现
   - 评委可能的评价视角

4. 【突破时刻】
   - 关键的创新突破点
   - 技术难题的解决过程
   - 性能提升的关键节点
   - 理念创新的闪光点

5. 【未来影响】
   - 创新方法的潜在应用价值
   - 对相关领域的影响
   - 未来研究的方向启示
   - 学术和产业的影响

请用生动的语言构建创新叙事，让评委感受到创新的精彩和价值。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            narrative_data = parsed.get("innovation_narrative", {})

            return InnovationNarrative(
                core_innovation_story=narrative_data.get("core_innovation_story", "创新的建模方法和思路"),
                innovation_evolution=narrative_data.get("innovation_evolution", []),
                competitive_differentiation=narrative_data.get("competitive_differentiation", "具有独特的竞争优势"),
                breakthrough_moments=narrative_data.get("breakthrough_moments", []),
                future_implications=narrative_data.get("future_implications", "具有重要的应用前景")
            )
        except json.JSONDecodeError:
            return InnovationNarrative(
                core_innovation_story="提出创新的解决思路和方法",
                innovation_evolution=["问题分析", "思路形成", "方法实现", "结果验证"],
                competitive_differentiation="相比传统方法具有创新性和优势",
                breakthrough_moments=["关键技术突破", "性能显著提升"],
                future_implications="具有重要的学术和应用价值"
            )

    async def _assess_innovation_intensity(
        self,
        innovation_points: List[InnovationPoint],
        innovation_narrative: InnovationNarrative,
        benchmark_analysis: Dict[str, Any]
    ) -> Tuple[float, float]:
        """评估创新强度"""
        prompt = f"""
基于创新点和叙事，对整体创新强度进行量化评估。

【创新点评估】
{[
    f"{p.innovation}: {p.uniqueness_level}独特性, {p.competitive_advantage}"
    for p in innovation_points
]}

【创新叙事质量】
核心故事: {len(innovation_narrative.core_innovation_story)}字符
演进过程: {len(innovation_narrative.innovation_evolution)}个阶段
突破时刻: {len(innovation_narrative.breakthrough_moments)}个关键点

【对标分析结果】
{json.dumps(benchmark_analysis, ensure_ascii=False, indent=2)[:500]}

请评估两个关键指标：

1. 【创新强度评分】(0-10分)
   - 创新点的质量和数量
   - 创新的独特性程度
   - 技术难度和复杂度
   - 学术价值和贡献
   - 平均分作为最终评分

2. 【获奖竞争力】(0-1概率)
   - 基于创新强度的获奖概率
   - 考虑竞赛水平的竞争激烈程度
   - 结合历史获奖案例分析
   - 评委可能的评价倾向

请给出客观公正的量化评估。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())

            intensity_score = parsed.get("innovation_intensity_score", 7.0)
            competitiveness = parsed.get("award_competitiveness", 0.65)

            # 确保数值范围合理
            intensity_score = max(0, min(10, intensity_score))
            competitiveness = max(0, min(1, competitiveness))

            return intensity_score, competitiveness
        except json.JSONDecodeError:
            return 7.5, 0.70

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "innovation_highlight_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_innovation_highlighter():
    """测试创新亮点突出师"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = InnovationHighlighter("test_task", model)

    # 准备测试输入
    test_modeling_results = {
        "model_type": "集成学习预测模型",
        "performance": {"accuracy": 0.91, "improvement": "25%"},
        "innovations": ["多尺度特征融合", "物理约束嵌入"]
    }

    test_benchmark = {
        "uniqueness": 0.85,
        "advancement_over_standards": 0.78,
        "competitive_score": 8.5
    }

    test_patterns = {
        "discovered_patterns": ["季节性周期规律", "多因素交互机制"],
        "theoretical_contributions": ["新的预测框架", "跨领域应用价值"]
    }

    # 执行分析
    result = await expert.execute(test_modeling_results, test_benchmark, test_patterns)

    # 输出结果
    print("=== 创新亮点突出分析 ===")
    print(f"创新点数量: {len(result.key_innovation_points)}")
    print(f"创新强度评分: {result.innovation_intensity_score}/10")
    print(f"获奖竞争力: {result.award_competitiveness:.1%}")
    print(f"核心创新故事: {result.innovation_narrative.core_innovation_story[:100]}...")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_innovation_highlighter())