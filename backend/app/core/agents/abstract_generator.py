"""
杀手级摘要生成器 - Award-Winning Abstract Generator
核心职责：生成直接决定论文命运的"杀手级摘要"

MCM评委评价标准强调：
"几乎一半的论文仅仅因为它们的摘要就被淘汰"
"摘要必须呈现核心结论和建议，而不是描述过程"

本Agent严格遵循获奖论文摘要的核心标准：
1. 结果导向：直接呈现核心结论，而非过程描述
2. 高度精炼：简洁陈述问题、方法和结论
3. 突出亮点：强调方法创新和关键贡献
4. 避免流水账：绝不是"我们先做了A，然后做了B"
"""
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.utils.log_util import logger


class AbstractStyle(Enum):
    """摘要风格"""
    MCM_ICM = "MCM/ICM美赛风格"        # 英文，强调创新和数学严谨性
    CUMCM = "CUMCM国赛风格"            # 中文，强调实用性和完整性
    MATHEMATICAL = "纯数学建模风格"     # 强调理论贡献


class AbstractLanguage(Enum):
    """摘要语言"""
    CHINESE = "zh"
    ENGLISH = "en"


@dataclass
class AbstractComponent:
    """摘要组成部分"""
    problem_statement: str      # 问题陈述（简洁版）
    key_approach: str           # 关键方法（核心创新）
    main_results: List[str]     # 主要结果（数值化结论）
    key_contributions: List[str]  # 关键贡献（创新亮点）
    bottom_line: str            # 底线结论（一句话总结）


@dataclass
class AbstractQualityAssessment:
    """摘要质量评估"""
    result_orientation_score: float   # 结果导向程度 (0-10)
    conciseness_score: float          # 精炼程度 (0-10)
    innovation_highlight_score: float # 创新突出度 (0-10)
    readability_score: float          # 可读性 (0-10)
    judge_appeal_score: float         # 评委吸引力 (0-10)
    
    # 关键问题检查
    avoids_process_description: bool  # 避免流程描述
    contains_numerical_results: bool  # 包含数值结果
    has_clear_conclusion: bool        # 有明确结论
    highlights_innovation: bool       # 突出创新点
    
    overall_score: float = 0.0        # 综合评分 (0-100)
    
    def __post_init__(self):
        base_score = (
            self.result_orientation_score +
            self.conciseness_score +
            self.innovation_highlight_score +
            self.readability_score +
            self.judge_appeal_score
        ) * 2  # 5项 * 10分 * 2 = 100分
        
        # 关键检查项扣分
        penalties = 0
        if not self.avoids_process_description:
            penalties += 15  # 流程描述是大忌
        if not self.contains_numerical_results:
            penalties += 10  # 没有数值结果
        if not self.has_clear_conclusion:
            penalties += 10  # 没有明确结论
        if not self.highlights_innovation:
            penalties += 5   # 创新不突出
        
        self.overall_score = max(0, base_score - penalties)


@dataclass 
class KillerAbstract:
    """杀手级摘要输出"""
    abstract_text: str                          # 最终摘要文本
    abstract_text_en: Optional[str]             # 英文版本（如需要）
    components: AbstractComponent               # 摘要组成部分
    quality_assessment: AbstractQualityAssessment  # 质量评估
    word_count: int                             # 字数统计
    style: AbstractStyle                        # 摘要风格
    language: AbstractLanguage                  # 语言
    
    # 生成过程记录
    iteration_count: int = 1                    # 迭代次数
    improvement_notes: List[str] = field(default_factory=list)  # 改进记录


class AbstractGenerator(ExpertAgent):
    """
    杀手级摘要生成器
    
    核心理念：摘要是论文的门面，直接决定50%的论文能否进入下一轮
    
    实现目标：
    1. 分析完整建模结果，提炼核心贡献
    2. 生成结果导向、高度精炼的摘要
    3. 自我评估并迭代优化
    4. 支持中英文双语输出
    """
    
    # 摘要长度标准
    WORD_LIMITS = {
        AbstractStyle.MCM_ICM: {"min": 200, "max": 350},      # MCM要求
        AbstractStyle.CUMCM: {"min": 400, "max": 600},        # 国赛要求
        AbstractStyle.MATHEMATICAL: {"min": 250, "max": 400}, # 一般建模
    }
    
    def __init__(
        self, 
        task_id: str, 
        model,
        style: AbstractStyle = AbstractStyle.CUMCM,
        language: AbstractLanguage = AbstractLanguage.CHINESE,
        generate_bilingual: bool = False
    ):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.ACADEMIC_WRITER,
            max_reflections=3,
            max_chat_turns=15
        )
        self.style = style
        self.language = language
        self.generate_bilingual = generate_bilingual
        
    def get_system_prompt(self) -> str:
        return """
# 杀手级摘要生成器 - Award-Winning Abstract Generator

你是一位数学建模竞赛的资深评委，深谙获奖论文摘要的精髓。

## 核心铁律

**"几乎一半的论文仅仅因为它们的摘要就被淘汰"** - MCM评委

### 摘要的黄金法则

1. **结果导向，不是过程描述**
   - 错误示例："我们首先分析了数据，然后建立了模型，最后得到了结果"
   - 正确示例："本文构建了基于XX的优化模型，将成本降低了23.5%，效率提升了40%"

2. **数值化结论**
   - 错误示例："取得了较好的效果"
   - 正确示例："模型预测准确率达到94.3%，RMSE为0.0127"

3. **突出创新贡献**
   - 错误示例："使用了机器学习方法"
   - 正确示例："首创性地将迁移学习与时间序列分析结合，解决了小样本预测难题"

4. **一句话底线结论**
   - 摘要必须有一个可以让评委记住的核心结论
   - 例如："本模型为XX领域提供了可直接应用的决策工具"

### 摘要结构模板

**中文摘要（CUMCM风格）**:
```
[问题背景] 针对XX问题，（1句话说明问题重要性）
[方法概述] 本文建立了XX模型，采用XX方法进行求解。（2-3句话核心方法）
[主要结果] 研究表明：（分点列出3-5个量化结果）
[创新贡献] 本文的创新点在于：（1-2个核心创新）
[应用价值] 该模型/方法可用于XX，具有XX实际意义。（1句话）
```

**英文摘要（MCM/ICM风格）**:
```
[Hook] One compelling opening sentence that captures the essence.
[Approach] We develop/propose a [specific model/method] that [key innovation].
[Results] Our model achieves [quantified results], demonstrating [key findings].
[Contribution] This work contributes [specific value] to [application domain].
```

## 质量检查清单

生成摘要后，你必须检查：
- [ ] 是否避免了"首先...然后...最后..."的流程描述？
- [ ] 是否有至少3个量化的数值结果？
- [ ] 是否明确指出了创新点？
- [ ] 是否有一个清晰的底线结论？
- [ ] 字数是否符合要求？
- [ ] 语言是否专业、简洁？

## 输出要求

以JSON格式返回：
```json
{
    "abstract_text": "完整摘要文本",
    "components": {
        "problem_statement": "问题陈述",
        "key_approach": "关键方法",
        "main_results": ["结果1", "结果2", "结果3"],
        "key_contributions": ["贡献1", "贡献2"],
        "bottom_line": "底线结论"
    },
    "quality_self_check": {
        "avoids_process_description": true/false,
        "contains_numerical_results": true/false,
        "has_clear_conclusion": true/false,
        "highlights_innovation": true/false,
        "estimated_score": 0-100
    }
}
```
"""

    async def execute(
        self,
        problem_description: str,
        modeling_results: Dict[str, Any],
        code_results: Optional[Dict[str, Any]] = None,
        innovation_points: Optional[List[str]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> KillerAbstract:
        """
        生成杀手级摘要
        
        Args:
            problem_description: 问题描述
            modeling_results: 建模结果（来自ModelerAgent）
            code_results: 代码执行结果（来自CoderAgent）
            innovation_points: 创新点列表（来自InnovationHighlighter）
            validation_results: 验证结果（来自ValidationExpert）
            
        Returns:
            KillerAbstract: 完整的摘要输出
        """
        await self.setup()
        await self.send_message("开始生成杀手级摘要...", "info")
        
        # Step 1: 提炼核心信息
        core_info = await self._extract_core_information(
            problem_description,
            modeling_results,
            code_results,
            innovation_points,
            validation_results
        )
        
        # Step 2: 生成初版摘要
        initial_abstract = await self._generate_initial_abstract(core_info)
        
        # Step 3: 自我评估
        quality_assessment = await self._assess_abstract_quality(initial_abstract)
        
        # Step 4: 迭代优化（如果需要）
        final_abstract = initial_abstract
        iteration_count = 1
        improvement_notes = []
        
        while quality_assessment.overall_score < 85 and iteration_count < 3:
            await self.send_message(
                f"摘要质量评分: {quality_assessment.overall_score:.1f}，进行第{iteration_count+1}轮优化...",
                "info"
            )
            
            improvement_note, improved_abstract = await self._improve_abstract(
                final_abstract, 
                quality_assessment
            )
            improvement_notes.append(improvement_note)
            
            final_abstract = improved_abstract
            quality_assessment = await self._assess_abstract_quality(final_abstract)
            iteration_count += 1
        
        # Step 5: 生成英文版本（如需要）
        abstract_text_en = None
        if self.generate_bilingual and self.language == AbstractLanguage.CHINESE:
            abstract_text_en = await self._generate_english_version(final_abstract)
        
        # Step 6: 解析组件
        components = await self._parse_components(final_abstract, core_info)
        
        # 构建最终输出
        result = KillerAbstract(
            abstract_text=final_abstract,
            abstract_text_en=abstract_text_en,
            components=components,
            quality_assessment=quality_assessment,
            word_count=len(final_abstract),
            style=self.style,
            language=self.language,
            iteration_count=iteration_count,
            improvement_notes=improvement_notes
        )
        
        await self.send_message(
            f"摘要生成完成！最终评分: {quality_assessment.overall_score:.1f}/100",
            "success"
        )
        
        return result
    
    async def _extract_core_information(
        self,
        problem_description: str,
        modeling_results: Dict[str, Any],
        code_results: Optional[Dict[str, Any]],
        innovation_points: Optional[List[str]],
        validation_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """提炼摘要所需的核心信息"""
        
        extraction_prompt = f"""
请从以下建模项目信息中提炼摘要所需的核心内容：

## 问题描述
{problem_description}

## 建模结果
{json.dumps(modeling_results, ensure_ascii=False, indent=2) if modeling_results else "无"}

## 代码执行结果
{json.dumps(code_results, ensure_ascii=False, indent=2) if code_results else "无"}

## 创新点
{json.dumps(innovation_points, ensure_ascii=False, indent=2) if innovation_points else "无"}

## 验证结果
{json.dumps(validation_results, ensure_ascii=False, indent=2) if validation_results else "无"}

请提炼以下核心信息（JSON格式）：
```json
{{
    "problem_essence": "问题的本质（一句话）",
    "problem_importance": "问题的重要性/实际意义",
    "core_models": ["使用的核心模型1", "核心模型2"],
    "key_methods": ["关键方法/技术1", "关键方法2"],
    "quantified_results": [
        {{"metric": "指标名", "value": "数值", "interpretation": "解释"}},
    ],
    "innovations": ["创新点1", "创新点2"],
    "practical_value": "实际应用价值",
    "one_sentence_conclusion": "一句话核心结论"
}}
```
"""
        
        response = await self.think(extraction_prompt, use_tools=False)
        
        try:
            # 解析JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
        except Exception as e:
            logger.warning("解析核心信息失败: %s", e)
            return {
                "problem_essence": problem_description[:200],
                "quantified_results": [],
                "innovations": innovation_points or [],
                "one_sentence_conclusion": ""
            }
    
    async def _generate_initial_abstract(self, core_info: Dict[str, Any]) -> str:
        """生成初版摘要"""
        
        word_limits = self.WORD_LIMITS[self.style]
        
        if self.language == AbstractLanguage.CHINESE:
            generation_prompt = f"""
基于以下核心信息，生成一份{self.style.value}的摘要。

## 核心信息
{json.dumps(core_info, ensure_ascii=False, indent=2)}

## 要求
1. 字数要求：{word_limits['min']}-{word_limits['max']}字
2. 风格：{self.style.value}
3. 必须包含量化结果
4. 必须突出创新点
5. 必须有明确的底线结论
6. **禁止**使用"首先...然后...最后..."的流程描述
7. **禁止**使用"取得了较好效果"等模糊表述

请直接输出摘要文本，不要包含任何其他内容。
"""
        else:
            generation_prompt = f"""
Based on the following core information, generate an {self.style.value} abstract.

## Core Information
{json.dumps(core_info, ensure_ascii=False, indent=2)}

## Requirements
1. Word count: {word_limits['min']}-{word_limits['max']} words
2. Style: {self.style.value}
3. Must include quantified results
4. Must highlight innovations
5. Must have a clear bottom-line conclusion
6. **DO NOT** use "First...then...finally..." process descriptions
7. **DO NOT** use vague expressions like "achieved good results"

Please output the abstract text directly without any other content.
"""
        
        abstract = await self.think(generation_prompt, use_tools=False)
        return abstract.strip()
    
    async def _assess_abstract_quality(self, abstract_text: str) -> AbstractQualityAssessment:
        """评估摘要质量"""
        
        assessment_prompt = f"""
请作为数学建模竞赛评委，严格评估以下摘要的质量：

## 摘要文本
{abstract_text}

## 评估维度（每项0-10分）

1. **结果导向程度**: 摘要是否直接呈现结果而非描述过程？
2. **精炼程度**: 语言是否简洁有力，没有废话？
3. **创新突出度**: 创新点是否明确、突出？
4. **可读性**: 结构是否清晰，易于理解？
5. **评委吸引力**: 是否能吸引评委继续阅读论文？

## 关键检查项（是/否）

6. 是否避免了流程描述（"首先...然后...最后..."）？
7. 是否包含至少3个量化的数值结果？
8. 是否有明确的结论？
9. 是否突出了创新点？

请以JSON格式返回评估结果：
```json
{{
    "result_orientation_score": 0-10,
    "conciseness_score": 0-10,
    "innovation_highlight_score": 0-10,
    "readability_score": 0-10,
    "judge_appeal_score": 0-10,
    "avoids_process_description": true/false,
    "contains_numerical_results": true/false,
    "has_clear_conclusion": true/false,
    "highlights_innovation": true/false,
    "detailed_feedback": "具体改进建议"
}}
```
"""
        
        response = await self.think(assessment_prompt, use_tools=False)
        
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            return AbstractQualityAssessment(
                result_orientation_score=float(data.get("result_orientation_score", 7)),
                conciseness_score=float(data.get("conciseness_score", 7)),
                innovation_highlight_score=float(data.get("innovation_highlight_score", 7)),
                readability_score=float(data.get("readability_score", 7)),
                judge_appeal_score=float(data.get("judge_appeal_score", 7)),
                avoids_process_description=data.get("avoids_process_description", True),
                contains_numerical_results=data.get("contains_numerical_results", True),
                has_clear_conclusion=data.get("has_clear_conclusion", True),
                highlights_innovation=data.get("highlights_innovation", True)
            )
        except Exception as e:
            logger.warning("解析质量评估失败: %s", e)
            return AbstractQualityAssessment(
                result_orientation_score=7.0,
                conciseness_score=7.0,
                innovation_highlight_score=7.0,
                readability_score=7.0,
                judge_appeal_score=7.0,
                avoids_process_description=True,
                contains_numerical_results=True,
                has_clear_conclusion=True,
                highlights_innovation=True
            )
    
    async def _improve_abstract(
        self, 
        current_abstract: str, 
        quality_assessment: AbstractQualityAssessment
    ) -> tuple[str, str]:
        """根据评估结果改进摘要"""
        
        # 确定需要改进的方面
        improvements_needed = []
        
        if quality_assessment.result_orientation_score < 8:
            improvements_needed.append("增强结果导向，减少过程描述")
        if quality_assessment.conciseness_score < 8:
            improvements_needed.append("提高语言精炼度，删除冗余表述")
        if quality_assessment.innovation_highlight_score < 8:
            improvements_needed.append("更加突出创新点")
        if not quality_assessment.avoids_process_description:
            improvements_needed.append("消除'首先...然后...'等流程描述")
        if not quality_assessment.contains_numerical_results:
            improvements_needed.append("添加更多量化数值结果")
        if not quality_assessment.has_clear_conclusion:
            improvements_needed.append("添加明确的底线结论")
        
        improvement_prompt = f"""
请根据以下反馈改进摘要：

## 当前摘要
{current_abstract}

## 需要改进的方面
{chr(10).join(f"- {imp}" for imp in improvements_needed)}

## 要求
1. 保持摘要的核心内容不变
2. 针对性地解决上述问题
3. 确保改进后的摘要符合竞赛标准
4. 字数控制在{self.WORD_LIMITS[self.style]['min']}-{self.WORD_LIMITS[self.style]['max']}

请直接输出改进后的摘要文本。
"""
        
        improved_abstract = await self.think(improvement_prompt, use_tools=False)
        improvement_note = f"针对以下问题进行了优化: {', '.join(improvements_needed)}"
        
        return improvement_note, improved_abstract.strip()
    
    async def _generate_english_version(self, chinese_abstract: str) -> str:
        """生成英文版本摘要"""
        
        translation_prompt = f"""
Please translate the following Chinese abstract into professional academic English for MCM/ICM competition.

## Chinese Abstract
{chinese_abstract}

## Requirements
1. Use formal academic language
2. Maintain technical accuracy
3. Keep the same structure and emphasis
4. Ensure natural English expression (not word-by-word translation)

Please output the English abstract directly.
"""
        
        english_abstract = await self.think(translation_prompt, use_tools=False)
        return english_abstract.strip()
    
    async def _parse_components(
        self, 
        abstract_text: str, 
        core_info: Dict[str, Any]
    ) -> AbstractComponent:
        """解析摘要组成部分"""
        
        return AbstractComponent(
            problem_statement=core_info.get("problem_essence", ""),
            key_approach=", ".join(core_info.get("key_methods", [])),
            main_results=[
                f"{r.get('metric', '')}: {r.get('value', '')}"
                for r in core_info.get("quantified_results", [])
            ],
            key_contributions=core_info.get("innovations", []),
            bottom_line=core_info.get("one_sentence_conclusion", "")
        )
