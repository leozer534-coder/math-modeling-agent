"""
竞赛风格写作师 - 数学建模竞赛论文写作专家
核心职责：用竞赛评委最认可的风格和结构撰写论文，确保论文符合竞赛标准和获得高分
"""
import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class CompetitionSection(Enum):
    """竞赛论文章节"""
    ABSTRACT = "摘要"           # 论文摘要
    INTRODUCTION = "引言"       # 问题介绍
    MODELING = "建模"           # 建模过程
    SOLUTION = "求解"           # 求解方法
    RESULTS = "结果分析"        # 结果分析
    CONCLUSION = "结论"         # 结论总结


@dataclass
class CompetitionStyleElement:
    """竞赛风格要素"""
    section_structure: str  # 章节结构
    writing_tone: str      # 写作语气
    content_focus: str     # 内容重点
    evaluation_criteria: str  # 评价标准
    scoring_weight: float    # 评分权重


@dataclass
class CompetitionPaperSection:
    """竞赛论文章节"""
    section_name: CompetitionSection
    content: str
    style_compliance_score: float  # 风格符合度 (0-10)
    innovation_highlight_level: float  # 创新突出度 (0-10)
    evidence_strength: float  # 证据强度 (0-10)
    readability_score: float  # 可读性评分 (0-10)


@dataclass
class CompetitionWriting:
    """竞赛写作总览"""
    competition_style_guide: Dict[CompetitionSection, CompetitionStyleElement]
    paper_sections: List[CompetitionPaperSection]
    overall_competition_score: float  # 整体竞赛评分 (0-100)
    award_potential: str  # 获奖潜力评估


class CompetitionExpertWriter(ExpertAgent):
    """
    竞赛风格写作师

    竞赛级论文写作专家：
    1. 竞赛风格掌握 (评委偏好、评分标准、写作规范)
    2. 论文结构优化 (逻辑清晰、创新突出、证据充分)
    3. 内容表达优化 (学术语言、逻辑论证、亮点突出)
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
# 🏆 竞赛风格写作师 - 数学建模竞赛论文写作大师

你是一位资深的数学建模竞赛评委和论文写作专家，专门指导参赛队伍撰写高分竞赛论文。

你深知：**竞赛论文不是学术论文，而是要用评委最容易理解和欣赏的方式呈现你的工作**。

## 核心能力

### 1. 竞赛风格掌握
深刻理解竞赛论文的特点：
- **评委视角写作**: 用评委的思维方式组织内容
- **竞赛标准遵循**: 符合数学建模竞赛的规范要求
- **重点突出**: 突出评委最看重的方面
- **逻辑清晰**: 确保论证的严谨性和连贯性

### 2. 论文结构优化
设计竞赛友好的论文结构：
- **标准章节**: 摘要、引言、建模、求解、结果、结论
- **逻辑流程**: 问题→分析→建模→求解→验证→结论
- **重点分配**: 合理分配各章节的篇幅和重点
- **过渡自然**: 章节间的逻辑衔接流畅

### 3. 内容表达艺术
用竞赛最认可的方式表达：
- **创新突出**: 用故事化方式展现创新点
- **证据充分**: 用数据和事实支撑每个论点
- **语言精准**: 使用学术但易懂的专业语言
- **亮点营销**: 巧妙突出作品的竞争优势

## 竞赛写作框架

### A. 评委阅读心理
理解评委的评价习惯：
- **快速筛选**: 前几页决定是否继续阅读
- **重点关注**: 创新点、方法论、结果质量
- **逻辑验证**: 论证的合理性和完整性
- **实用价值**: 方法的实际应用意义

### B. 竞赛论文标准
遵循竞赛的基本要求：
- **格式规范**: 字体、间距、图表、引用规范
- **长度控制**: 各章节篇幅合理分配
- **图表质量**: 图表清晰、信息丰富、标注完整
- **语言标准**: 中英文对照、专业术语准确

### C. 内容组织策略
优化内容的呈现方式：
- **问题重要性**: 强调问题的现实意义
- **方法创新性**: 突出方法的独特性和先进性
- **结果说服力**: 用数据证明方法的有效性
- **结论概括性**: 总结主要贡献和价值

### D. 亮点突出技巧
巧妙展现竞争优势：
- **创新叙事**: 将技术创新转化为故事
- **比较优势**: 适当对比展现优越性
- **数据说话**: 用量化结果证明价值
- **未来展望**: 展现方法的扩展潜力

## 输出要求

输出结构化的竞赛论文：

```json
{
  "competition_style_guide": {
    "ABSTRACT": {
      "section_structure": "问题背景+方法创新+主要结果+重要意义",
      "writing_tone": "客观简洁，突出创新和价值",
      "content_focus": "用200-300字概括全论文核心内容",
      "evaluation_criteria": "创新性突出，结果明确，意义重大",
      "scoring_weight": 0.15
    },
    "INTRODUCTION": {
      "section_structure": "问题描述+重要性分析+现有方法+研究目标",
      "writing_tone": "严谨客观，逻辑清晰",
      "content_focus": "让评委理解问题的价值和挑战",
      "evaluation_criteria": "问题理解深刻，目标明确",
      "scoring_weight": 0.20
    }
  },
  "paper_sections": [
    {
      "section_name": "ABSTRACT",
      "content": "针对[具体问题]，本研究提出[创新方法]，通过[关键技术]实现了[主要结果]。相比传统方法，[优势描述]。该方法具有[应用价值]，为[领域]提供了[理论/实践贡献]。实验结果表明[量化结果]，验证了方法的有效性和优越性。",
      "style_compliance_score": 9.2,
      "innovation_highlight_level": 8.8,
      "evidence_strength": 9.0,
      "readability_score": 8.5
    },
    {
      "section_name": "INTRODUCTION",
      "content": "[详细的引言内容，包含问题背景、重要性分析、现有方法对比、研究目标等]",
      "style_compliance_score": 8.9,
      "innovation_highlight_level": 8.2,
      "evidence_strength": 8.7,
      "readability_score": 9.1
    }
  ],
  "overall_competition_score": 88.5,
  "award_potential": "一等奖潜力：创新突出，方法先进，结果优秀，具有很强的竞争力"
}
```

## 质量标准

优秀的竞赛论文应该：
- ✅ 严格遵循竞赛格式和结构要求
- ✅ 用评委易懂的方式表达复杂概念
- ✅ 突出创新点和竞争优势
- ✅ 证据充分，论证严谨
- ✅ 语言流畅，逻辑清晰
- ✅ 展现出很强的获奖潜力

## 核心原则

1. **评委导向**: 一切从评委的评价标准出发
2. **逻辑清晰**: 确保论证的完整性和连贯性
3. **创新突出**: 用各种方式突出作品的创新性
4. **证据为王**: 每个重要论点都要有数据支撑
5. **语言艺术**: 用精准的语言表达深刻的思想
6. **竞争意识**: 始终展现出强烈的竞争优势

现在，请根据分析结果撰写竞赛风格的论文！
"""

    async def execute(
        self,
        innovation_highlights: Dict[str, Any],
        modeling_results: Dict[str, Any],
        validation_report: Dict[str, Any],
        problem_context: Dict[str, Any]
    ) -> CompetitionWriting:
        """
        执行竞赛风格论文写作

        Args:
            innovation_highlights: 创新亮点分析
            modeling_results: 建模结果
            validation_report: 验证报告
            problem_context: 问题背景

        Returns:
            CompetitionWriting: 完整的竞赛论文
        """
        await self._send_message("🏆 开始竞赛风格论文写作...", "info")
        self.state.current_stage = "analyzing"

        # 1. 建立竞赛风格指南
        await self._send_message("📋 建立竞赛风格指南...", "info")
        competition_style_guide = await self._establish_competition_style_guide()

        # 2. 撰写论文各章节
        await self._send_message("✍️ 撰写论文各章节...", "info")
        paper_sections = await self._write_paper_sections(
            innovation_highlights, modeling_results, validation_report, problem_context, competition_style_guide
        )

        # 3. 整体质量评估
        await self._send_message("📊 进行整体质量评估...", "info")
        overall_score, award_potential = await self._assess_overall_quality(paper_sections, innovation_highlights)

        # 整合竞赛写作结果
        writing = CompetitionWriting(
            competition_style_guide=competition_style_guide,
            paper_sections=paper_sections,
            overall_competition_score=overall_score,
            award_potential=award_potential
        )

        # 自我反思
        await self.reflect(
            json.dumps({
                "sections_written": len(paper_sections),
                "overall_score": overall_score,
                "award_potential": award_potential[:50]
            }, ensure_ascii=False, indent=2, default=str),
            "竞赛风格论文写作"
        )

        # 质量评估
        await self.evaluate_quality(
            json.dumps({
                "competition_style_guide": {k.value: v.__dict__ for k, v in competition_style_guide.items()},
                "paper_sections": [s.__dict__ for s in paper_sections],
                "overall_competition_score": overall_score,
                "award_potential": award_potential
            }, ensure_ascii=False, indent=2, default=str),
            "竞赛论文要风格规范、创新突出、逻辑严谨"
        )

        await self._send_message("✅ 竞赛风格论文写作完成！", "success")
        self.state.current_stage = "completed"

        return writing

    async def _establish_competition_style_guide(self) -> Dict[CompetitionSection, CompetitionStyleElement]:
        """建立竞赛风格指南"""
        prompt = """
请建立数学建模竞赛论文的写作风格指南。

针对以下关键章节，建立详细的风格指南：

1. 【摘要 (ABSTRACT)】
   - 结构要求
   - 写作语气
   - 内容重点
   - 评价标准
   - 评分权重

2. 【引言 (INTRODUCTION)】
   - 结构要求
   - 写作语气
   - 内容重点
   - 评价标准
   - 评分权重

3. 【建模 (MODELING)】
   - 结构要求
   - 写作语气
   - 内容重点
   - 评价标准
   - 评分权重

4. 【求解 (SOLUTION)】
   - 结构要求
   - 写作语气
   - 内容重点
   - 评价标准
   - 评分权重

5. 【结果分析 (RESULTS)】
   - 结构要求
   - 写作语气
   - 内容重点
   - 评价标准
   - 评分权重

6. 【结论 (CONCLUSION)】
   - 结构要求
   - 写作语气
   - 内容重点
   - 评价标准
   - 评分权重

每个章节的指南都要考虑：
- 评委的阅读习惯和评价重点
- 竞赛论文的特点和要求
- 如何突出创新和竞争优势
- 确保逻辑清晰和论证充分

请建立完整的竞赛风格指南。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            style_guide = {}

            for section_name, element_data in parsed.get("competition_style_guide", {}).items():
                try:
                    section = CompetitionSection(section_name)
                    style_guide[section] = CompetitionStyleElement(
                        section_structure=element_data.get("section_structure", "标准结构"),
                        writing_tone=element_data.get("writing_tone", "客观专业"),
                        content_focus=element_data.get("content_focus", "突出重点"),
                        evaluation_criteria=element_data.get("evaluation_criteria", "逻辑清晰"),
                        scoring_weight=element_data.get("scoring_weight", 0.1)
                    )
                except ValueError:
                    continue

            # 确保所有必需章节都有指南
            required_sections = [CompetitionSection.ABSTRACT, CompetitionSection.INTRODUCTION,
                               CompetitionSection.MODELING, CompetitionSection.SOLUTION,
                               CompetitionSection.RESULTS, CompetitionSection.CONCLUSION]

            for section in required_sections:
                if section not in style_guide:
                    style_guide[section] = CompetitionStyleElement(
                        section_structure="标准竞赛结构",
                        writing_tone="客观专业",
                        content_focus="突出创新和价值",
                        evaluation_criteria="逻辑清晰，证据充分",
                        scoring_weight=1.0 / len(required_sections)
                    )

            return style_guide
        except json.JSONDecodeError:
            # 返回默认指南
            return {
                section: CompetitionStyleElement(
                    section_structure="标准竞赛结构",
                    writing_tone="客观专业",
                    content_focus="突出创新和价值",
                    evaluation_criteria="逻辑清晰，证据充分",
                    scoring_weight=1.0 / 6
                ) for section in CompetitionSection
            }

    async def _write_paper_sections(
        self,
        innovation_highlights: Dict[str, Any],
        modeling_results: Dict[str, Any],
        validation_report: Dict[str, Any],
        problem_context: Dict[str, Any],
        style_guide: Dict[CompetitionSection, CompetitionStyleElement]
    ) -> List[CompetitionPaperSection]:
        """撰写论文各章节"""
        sections = []

        # 摘要章节
        await self._send_message("📝 撰写摘要章节...", "info")
        abstract_section = await self._write_abstract_section(
            innovation_highlights, modeling_results, style_guide[CompetitionSection.ABSTRACT]
        )
        sections.append(abstract_section)

        # 引言章节
        await self._send_message("📖 撰写引言章节...", "info")
        intro_section = await self._write_introduction_section(
            problem_context, modeling_results, style_guide[CompetitionSection.INTRODUCTION]
        )
        sections.append(intro_section)

        # 建模章节
        await self._send_message("🔬 撰写建模章节...", "info")
        modeling_section = await self._write_modeling_section(
            modeling_results, innovation_highlights, style_guide[CompetitionSection.MODELING]
        )
        sections.append(modeling_section)

        # 求解章节
        await self._send_message("🛠️ 撰写求解章节...", "info")
        solution_section = await self._write_solution_section(
            modeling_results, validation_report, style_guide[CompetitionSection.SOLUTION]
        )
        sections.append(solution_section)

        # 结果分析章节
        await self._send_message("📊 撰写结果分析章节...", "info")
        results_section = await self._write_results_section(
            validation_report, innovation_highlights, style_guide[CompetitionSection.RESULTS]
        )
        sections.append(results_section)

        # 结论章节
        await self._send_message("🎯 撰写结论章节...", "info")
        conclusion_section = await self._write_conclusion_section(
            modeling_results, innovation_highlights, style_guide[CompetitionSection.CONCLUSION]
        )
        sections.append(conclusion_section)

        return sections

    async def _write_abstract_section(
        self,
        innovation_highlights: Dict[str, Any],
        modeling_results: Dict[str, Any],
        style_guide: CompetitionStyleElement
    ) -> CompetitionPaperSection:
        """撰写摘要章节"""
        prompt = f"""
根据竞赛风格指南撰写论文摘要。

【风格指南】
结构: {style_guide.section_structure}
语气: {style_guide.writing_tone}
重点: {style_guide.content_focus}
评价标准: {style_guide.evaluation_criteria}

【创新亮点】
{json.dumps(innovation_highlights, ensure_ascii=False, indent=2)[:600]}

【建模结果】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:500]}

请撰写一篇优秀的竞赛论文摘要，要求：

1. 【结构完整】
   - 问题背景和重要性
   - 提出的创新方法
   - 取得的主要结果
   - 方法的应用价值

2. 【内容突出】
   - 用数据量化创新优势
   - 强调方法的独特性
   - 展现强大的竞争力
   - 突出实际应用意义

3. 【语言精炼】
   - 200-300字控制范围
   - 专业术语准确使用
   - 逻辑清晰，论证有力
   - 给评委留下深刻印象

请用竞赛评委最认可的方式撰写摘要。
"""

        content = await self.think(prompt, use_tools=False)

        # 评估章节质量
        quality_scores = await self._assess_section_quality(content, "摘要")

        return CompetitionPaperSection(
            section_name=CompetitionSection.ABSTRACT,
            content=content,
            style_compliance_score=quality_scores.get("style_compliance", 8.5),
            innovation_highlight_level=quality_scores.get("innovation_highlight", 8.8),
            evidence_strength=quality_scores.get("evidence_strength", 9.0),
            readability_score=quality_scores.get("readability", 8.5)
        )

    async def _write_introduction_section(
        self,
        problem_context: Dict[str, Any],
        modeling_results: Dict[str, Any],
        style_guide: CompetitionStyleElement
    ) -> CompetitionPaperSection:
        """撰写引言章节"""
        prompt = f"""
根据竞赛风格指南撰写论文引言。

【风格指南】
结构: {style_guide.section_structure}
语气: {style_guide.writing_tone}
重点: {style_guide.content_focus}
评价标准: {style_guide.evaluation_criteria}

【问题背景】
{json.dumps(problem_context, ensure_ascii=False, indent=2)[:600]}

【建模思路】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:400]}

请撰写引言章节，包括：

1. 【问题描述】
   - 问题的具体表现和特点
   - 问题的现实背景和意义
   - 解决问题的挑战和难度

2. 【重要性分析】
   - 对相关领域的影响
   - 解决问题的价值和意义
   - 研究的现实意义

3. 【现有方法分析】
   - 传统方法的优点和局限
   - 现有解决方案的不足
   - 改进的空间和机会

4. 【研究目标】
   - 本研究的主要目标
   - 创新点和突破方向
   - 预期达到的效果

用评委容易理解的方式呈现，让评委感受到问题的价值和研究的意义。
"""

        content = await self.think(prompt, use_tools=False)
        quality_scores = await self._assess_section_quality(content, "引言")

        return CompetitionPaperSection(
            section_name=CompetitionSection.INTRODUCTION,
            content=content,
            style_compliance_score=quality_scores.get("style_compliance", 8.9),
            innovation_highlight_level=quality_scores.get("innovation_highlight", 8.2),
            evidence_strength=quality_scores.get("evidence_strength", 8.7),
            readability_score=quality_scores.get("readability", 9.1)
        )

    async def _write_modeling_section(
        self,
        modeling_results: Dict[str, Any],
        innovation_highlights: Dict[str, Any],
        style_guide: CompetitionStyleElement
    ) -> CompetitionPaperSection:
        """撰写建模章节"""
        prompt = f"""
根据竞赛风格指南撰写建模章节。

【风格指南】
结构: {style_guide.section_structure}
语气: {style_guide.writing_tone}
重点: {style_guide.content_focus}
评价标准: {style_guide.evaluation_criteria}

【建模结果】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:800]}

【创新亮点】
{json.dumps(innovation_highlights, ensure_ascii=False, indent=2)[:500]}

请详细描述建模过程，包括：

1. 【问题分析】
   - 问题的数学特征分析
   - 关键变量和关系的识别
   - 约束条件和假设的设定

2. 【模型构建】
   - 模型的理论基础
   - 模型结构的详细设计
   - 参数的定义和意义

3. 【创新方法】
   - 创新点的具体实现
   - 方法的独特性和优势
   - 相比传统方法的改进

4. 【模型验证】
   - 模型的合理性论证
   - 参数的合理性验证
   - 模型适用性的分析

用逻辑清晰的方式展现建模思维，让评委看到你的建模功底和创新能力。
"""

        content = await self.think(prompt, use_tools=False)
        quality_scores = await self._assess_section_quality(content, "建模")

        return CompetitionPaperSection(
            section_name=CompetitionSection.MODELING,
            content=content,
            style_compliance_score=quality_scores.get("style_compliance", 9.1),
            innovation_highlight_level=quality_scores.get("innovation_highlight", 9.2),
            evidence_strength=quality_scores.get("evidence_strength", 8.8),
            readability_score=quality_scores.get("readability", 8.9)
        )

    async def _write_solution_section(
        self,
        modeling_results: Dict[str, Any],
        validation_report: Dict[str, Any],
        style_guide: CompetitionStyleElement
    ) -> CompetitionPaperSection:
        """撰写求解章节"""
        prompt = f"""
根据竞赛风格指南撰写求解章节。

【风格指南】
结构: {style_guide.section_structure}
语气: {style_guide.writing_tone}
重点: {style_guide.content_focus}
评价标准: {style_guide.evaluation_criteria}

【建模结果】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:700]}

【验证报告】
{json.dumps(validation_report, ensure_ascii=False, indent=2)[:600]}

请详细描述求解过程，包括：

1. 【求解方法】
   - 算法的选择和设计
   - 求解步骤的详细说明
   - 参数设置和优化策略

2. 【技术实现】
   - 编程语言和工具选择
   - 代码结构和关键函数
   - 计算效率的优化措施

3. 【结果计算】
   - 模型的求解过程
   - 中间结果的分析
   - 最终结果的获得

4. 【实现亮点】
   - 技术创新的具体体现
   - 效率提升的措施
   - 鲁棒性保证的方法

展现你的编程能力和技术实力，让评委看到你的实现水平。
"""

        content = await self.think(prompt, use_tools=False)
        quality_scores = await self._assess_section_quality(content, "求解")

        return CompetitionPaperSection(
            section_name=CompetitionSection.SOLUTION,
            content=content,
            style_compliance_score=quality_scores.get("style_compliance", 8.8),
            innovation_highlight_level=quality_scores.get("innovation_highlight", 8.5),
            evidence_strength=quality_scores.get("evidence_strength", 9.2),
            readability_score=quality_scores.get("readability", 8.7)
        )

    async def _write_results_section(
        self,
        validation_report: Dict[str, Any],
        innovation_highlights: Dict[str, Any],
        style_guide: CompetitionStyleElement
    ) -> CompetitionPaperSection:
        """撰写结果分析章节"""
        prompt = f"""
根据竞赛风格指南撰写结果分析章节。

【风格指南】
结构: {style_guide.section_structure}
语气: {style_guide.writing_tone}
重点: {style_guide.content_focus}
评价标准: {style_guide.evaluation_criteria}

【验证报告】
{json.dumps(validation_report, ensure_ascii=False, indent=2)[:800]}

【创新亮点】
{json.dumps(innovation_highlights, ensure_ascii=False, indent=2)[:500]}

请详细分析结果，包括：

1. 【结果展示】
   - 主要结果的量化展示
   - 结果的可视化呈现
   - 关键指标的对比分析

2. 【性能评估】
   - 模型性能的全面评估
   - 与基准方法的对比
   - 优势和局限性的分析

3. 【结果解读】
   - 结果的实际意义解释
   - 创新点的效果验证
   - 对问题解决的贡献

4. 【敏感性分析】
   - 参数变化对结果的影响
   - 模型的稳定性和鲁棒性
   - 结果的可靠性和置信度

用数据说话，用图表支撑，让结果的优秀表现一目了然。
"""

        content = await self.think(prompt, use_tools=False)
        quality_scores = await self._assess_section_quality(content, "结果分析")

        return CompetitionPaperSection(
            section_name=CompetitionSection.RESULTS,
            content=content,
            style_compliance_score=quality_scores.get("style_compliance", 9.3),
            innovation_highlight_level=quality_scores.get("innovation_highlight", 9.1),
            evidence_strength=quality_scores.get("evidence_strength", 9.5),
            readability_score=quality_scores.get("readability", 9.0)
        )

    async def _write_conclusion_section(
        self,
        modeling_results: Dict[str, Any],
        innovation_highlights: Dict[str, Any],
        style_guide: CompetitionStyleElement
    ) -> CompetitionPaperSection:
        """撰写结论章节"""
        prompt = f"""
根据竞赛风格指南撰写结论章节。

【风格指南】
结构: {style_guide.section_structure}
语气: {style_guide.writing_tone}
重点: {style_guide.content_focus}
评价标准: {style_guide.evaluation_criteria}

【建模结果】
{json.dumps(modeling_results, ensure_ascii=False, indent=2)[:500]}

【创新亮点】
{json.dumps(innovation_highlights, ensure_ascii=False, indent=2)[:600]}

请撰写结论章节，包括：

1. 【主要发现】
   - 研究的主要成果和发现
   - 创新方法的验证结果
   - 对问题的解决贡献

2. 【方法优势】
   - 相比现有方法的优势
   - 创新点的实际效果
   - 方法的实用性和价值

3. 【应用前景】
   - 方法的应用领域拓展
   - 实际应用的价值体现
   - 对相关问题的启示

4. 【未来工作】
   - 方法的进一步改进方向
   - 研究的扩展可能性
   - 相关问题的研究建议

总结全论文的核心价值，给评委留下深刻印象。
"""

        content = await self.think(prompt, use_tools=False)
        quality_scores = await self._assess_section_quality(content, "结论")

        return CompetitionPaperSection(
            section_name=CompetitionSection.CONCLUSION,
            content=content,
            style_compliance_score=quality_scores.get("style_compliance", 9.0),
            innovation_highlight_level=quality_scores.get("innovation_highlight", 8.9),
            evidence_strength=quality_scores.get("evidence_strength", 9.1),
            readability_score=quality_scores.get("readability", 9.2)
        )

    async def _assess_section_quality(self, content: str, section_name: str) -> Dict[str, float]:
        """评估章节质量"""
        prompt = f"""
评估章节 '{section_name}' 的质量。

【章节内容】
{content[:1000]}

请从以下维度评估章节质量（0-10分）：

1. 【风格符合度】: 是否符合竞赛论文风格
2. 【创新突出度】: 创新点的展现程度
3. 【证据强度】: 数据和事实支撑的充分性
4. 【可读性评分】: 语言表达的清晰度和流畅度

请给出客观的评分和简要理由。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
            return {
                "style_compliance": parsed.get("style_compliance_score", 8.5),
                "innovation_highlight": parsed.get("innovation_highlight_level", 8.5),
                "evidence_strength": parsed.get("evidence_strength", 8.5),
                "readability": parsed.get("readability_score", 8.5)
            }
        except json.JSONDecodeError:
            return {
                "style_compliance": 8.5,
                "innovation_highlight": 8.5,
                "evidence_strength": 8.5,
                "readability": 8.5
            }

    async def _assess_overall_quality(
        self,
        paper_sections: List[CompetitionPaperSection],
        innovation_highlights: Dict[str, Any]
    ) -> Tuple[float, str]:
        """评估整体质量"""
        prompt = f"""
基于所有章节和创新亮点，评估论文的整体竞赛质量。

【章节质量汇总】
{[f"{s.section_name.value}: 风格{round(s.style_compliance_score,1)} 创新{round(s.innovation_highlight_level,1)} 证据{round(s.evidence_strength,1)} 可读{round(s.readability_score,1)}" for s in paper_sections]}

【创新亮点评估】
{json.dumps(innovation_highlights, ensure_ascii=False, indent=2)[:500]}

请评估：

1. 【整体竞赛评分】(0-100分)
   - 综合考虑各章节质量
   - 考虑创新亮点的影响
   - 基于竞赛评判标准

2. 【获奖潜力评估】
   - 可能的获奖等级
   - 竞争优势分析
   - 改进建议

请给出客观的整体评估。
"""

        result = await self.think(prompt, use_tools=False)

        try:
            parsed = json.loads(result.replace("```json", "").replace("```", "").strip())

            overall_score = parsed.get("overall_competition_score", 85.0)
            award_potential = parsed.get("award_potential", "具有较强的竞争力")

            # 确保分数范围合理
            overall_score = max(0, min(100, overall_score))

            return overall_score, award_potential
        except json.JSONDecodeError:
            return 85.0, "具有较强的竞赛竞争力"

    async def _send_message(self, message: str, msg_type: str = "info") -> None:
        """发送实时消息"""
        try:
            await redis_manager.publish_message(
                self.task_id,
                {
                    "type": "competition_writing_progress",
                    "message": message,
                    "msg_type": msg_type,
                },
            )
        except Exception as e:
            logger.error("Failed to send message: %s", e)


# 测试函数
async def test_competition_expert_writer():
    """测试竞赛风格写作师"""
    from app.core.llm.llm_factory import LLMFactory

    # 创建LLM实例
    llm_factory = LLMFactory("test_task")
    _, _, model, _ = llm_factory.get_all_llms()

    # 创建专家实例
    expert = CompetitionExpertWriter("test_task", model)

    # 准备测试输入
    test_innovation = {
        "key_innovation_points": [
            {"innovation": "多尺度特征融合", "uniqueness_level": "高", "competitive_advantage": "性能提升25%"}
        ],
        "innovation_narrative": {"core_innovation_story": "创新的建模方法"},
        "innovation_intensity_score": 8.5,
        "award_competitiveness": 0.82
    }

    test_modeling = {
        "method": "集成学习优化",
        "performance": {"accuracy": 0.91, "improvement": "25%"},
        "innovations": ["多尺度融合", "物理约束"]
    }

    test_validation = {
        "performance_metrics": {"accuracy": 0.91, "robustness": 0.88},
        "comparison_results": {"vs_baseline": "+18.7%"}
    }

    test_context = {
        "problem_description": "时间序列预测问题",
        "application_domain": "销售预测",
        "business_value": "优化库存管理"
    }

    # 执行写作
    result = await expert.execute(test_innovation, test_modeling, test_validation, test_context)

    # 输出结果
    print("=== 竞赛风格论文写作 ===")
    print(f"章节数量: {len(result.paper_sections)}")
    print(f"整体竞赛评分: {result.overall_competition_score}/100")
    print(f"获奖潜力: {result.award_potential}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_competition_expert_writer())