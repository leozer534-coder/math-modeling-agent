"""
Assumption Generator - 假设自动生成与论证
==========================================

功能：
1. 基于问题描述自动识别需要做出的假设
2. 为每个假设生成合理的论证依据
3. 引用文献支持假设的合理性
4. 评估假设对结果的影响程度
5. 生成标准化的假设陈述

关键特性：
- Citation-first: 每个假设必须有引用支持
- 分类管理: 简化假设、合理性假设、一致性假设
- 影响分析: 评估假设变化对结果的敏感度
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.core.llm.llm_gateway import chat_completion
from app.schemas.contracts import (
    Assumption,
    Citation,
    EvidenceSnippet,
)
from app.utils.log_util import logger


class AssumptionCategory(Enum):
    """假设分类"""

    SIMPLIFICATION = "simplification"  # 简化假设：忽略次要因素
    RATIONALITY = "rationality"  # 合理性假设：行为/决策假设
    CONSISTENCY = "consistency"  # 一致性假设：时间/空间不变性
    BOUNDARY = "boundary"  # 边界假设：系统边界定义
    DATA = "data"  # 数据假设：数据质量/完整性


class ImpactLevel(Enum):
    """影响程度"""

    CRITICAL = "critical"  # 关键：假设不成立则结论无效
    HIGH = "high"  # 高：显著影响结果准确性
    MEDIUM = "medium"  # 中：一定影响但可接受
    LOW = "low"  # 低：影响较小


@dataclass
class AssumptionCandidate:
    """假设候选项"""

    statement: str  # 假设陈述
    category: AssumptionCategory
    necessity_score: float  # 必要性评分 0-1
    common_in_literature: bool  # 文献中是否常见
    potential_citations: List[str]  # 潜在引用来源描述


@dataclass
class GeneratedAssumption:
    """生成的完整假设"""

    id: str
    statement: str  # 假设陈述 (简洁版)
    detailed_statement: str  # 详细陈述
    category: AssumptionCategory
    justification: str  # 论证理由
    impact_analysis: str  # 影响分析
    impact_level: ImpactLevel
    confidence: float  # 置信度 0-1
    citations: List[Citation] = field(default_factory=list)
    related_variables: List[str] = field(default_factory=list)
    verification_methods: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_assumption(self) -> Assumption:
        """转换为标准 Assumption 格式"""
        return Assumption(
            id=self.id,
            statement=self.statement,
            justification=self.justification,
            impact_analysis=self.impact_analysis,
            confidence=self.confidence,
            citations=self.citations,
            related_variables=self.related_variables,
        )


class AssumptionGenerator:
    """假设生成器"""

    # 常见假设模板
    COMMON_ASSUMPTION_TEMPLATES: Dict[str, List[str]] = {
        "optimization": [
            "决策者追求{objective}最优化",
            "所有约束条件在{time_range}内保持不变",
            "不考虑{factor}的随机扰动",
            "供需关系在短期内保持稳定",
        ],
        "prediction": [
            "历史数据能够反映未来趋势",
            "影响因素之间相互独立",
            "数据采集过程不存在系统性偏差",
            "预测期内不发生重大结构性变化",
        ],
        "evaluation": [
            "评价指标之间相互独立",
            "专家评分具有一致性和稳定性",
            "评价对象的属性可以量化",
            "评价标准在研究期间保持不变",
        ],
        "simulation": [
            "模型能够近似真实系统的行为",
            "初始条件和边界条件已知且准确",
            "随机过程服从特定分布",
            "系统参数在仿真期间不变",
        ],
    }

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]

    async def identify_required_assumptions(
        self,
        problem_description: str,
        problem_type: str,
        data_description: Optional[str] = None,
        existing_evidence: Optional[List[EvidenceSnippet]] = None,
    ) -> List[AssumptionCandidate]:
        """
        识别问题需要做出的假设

        Args:
            problem_description: 问题描述
            problem_type: 问题类型 (optimization/prediction/evaluation/simulation)
            data_description: 数据描述
            existing_evidence: 已有的证据片段

        Returns:
            假设候选列表
        """
        prompt = self._build_identification_prompt(
            problem_description, problem_type, data_description, existing_evidence
        )

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": self._get_identification_system_prompt(),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            run_id=self.run_id,
            agent_id="assumption_generator",
        )

        return self._parse_candidates(response.content, problem_type)

    async def generate_assumption(
        self,
        candidate: AssumptionCandidate,
        problem_context: str,
        evidence: Optional[List[EvidenceSnippet]] = None,
    ) -> GeneratedAssumption:
        """
        为候选假设生成完整的假设描述和论证

        Args:
            candidate: 假设候选
            problem_context: 问题上下文
            evidence: 相关证据

        Returns:
            完整的假设对象
        """
        prompt = self._build_generation_prompt(candidate, problem_context, evidence)

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": self._get_generation_system_prompt(),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            run_id=self.run_id,
            agent_id="assumption_generator",
        )

        return self._parse_generated_assumption(response.content, candidate)

    async def generate_all_assumptions(
        self,
        problem_description: str,
        problem_type: str,
        data_description: Optional[str] = None,
        evidence: Optional[List[EvidenceSnippet]] = None,
        max_assumptions: int = 8,
    ) -> List[GeneratedAssumption]:
        """
        一站式生成所有假设

        Args:
            problem_description: 问题描述
            problem_type: 问题类型
            data_description: 数据描述
            evidence: 已有证据
            max_assumptions: 最大假设数量

        Returns:
            生成的假设列表
        """
        # 1. 识别需要的假设
        candidates = await self.identify_required_assumptions(
            problem_description, problem_type, data_description, evidence
        )

        # 2. 按必要性排序，取前N个
        candidates = sorted(candidates, key=lambda x: x.necessity_score, reverse=True)
        candidates = candidates[:max_assumptions]

        # 3. 为每个候选生成完整假设
        assumptions: List[GeneratedAssumption] = []
        for candidate in candidates:
            try:
                assumption = await self.generate_assumption(
                    candidate, problem_description, evidence
                )
                assumptions.append(assumption)
            except Exception as e:
                logger.error("Failed to generate assumption: %s", e)
                continue

        # 4. 按类别和影响程度排序
        assumptions = self._sort_assumptions(assumptions)

        return assumptions

    async def validate_assumption_set(
        self,
        assumptions: List[GeneratedAssumption],
        problem_description: str,
    ) -> Tuple[bool, List[str]]:
        """
        验证假设集合的完整性和一致性

        Args:
            assumptions: 假设列表
            problem_description: 问题描述

        Returns:
            (是否通过验证, 问题列表)
        """
        assumption_text = "\n".join(
            [f"{i + 1}. {a.statement}" for i, a in enumerate(assumptions)]
        )

        prompt = f"""分析以下假设集合是否完整且一致：

## 问题描述
{problem_description}

## 假设列表
{assumption_text}

请检查：
1. 是否覆盖了所有必要的假设？
2. 假设之间是否存在矛盾？
3. 是否有隐含假设未被明确列出？
4. 假设的强度是否合适？

以JSON格式返回：
{{
    "is_valid": true/false,
    "issues": ["问题1", "问题2"],
    "missing_assumptions": ["缺失的假设1"],
    "suggestions": ["建议1"]
}}
"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，负责审核假设的完整性和合理性。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            run_id=self.run_id,
            agent_id="assumption_validator",
        )

        try:
            # 提取JSON
            content = response.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                issues = result.get("issues", []) + result.get(
                    "missing_assumptions", []
                )
                return result.get("is_valid", True), issues
        except json.JSONDecodeError:
            logger.warning("Failed to parse validation response")

        return True, []

    def format_assumptions_for_paper(
        self,
        assumptions: List[GeneratedAssumption],
        include_justification: bool = True,
    ) -> str:
        """
        将假设格式化为论文格式

        Args:
            assumptions: 假设列表
            include_justification: 是否包含论证

        Returns:
            格式化的假设文本
        """
        lines: List[str] = []
        lines.append("## 模型假设\n")
        lines.append("为使问题便于处理，本文做出以下假设：\n")

        for i, assumption in enumerate(assumptions, 1):
            lines.append(f"**假设 {i}**: {assumption.statement}")

            if include_justification and assumption.justification:
                lines.append(f"\n*论证*: {assumption.justification}")

            if assumption.citations:
                citation_refs = ", ".join(
                    [f"[{c.get('source_id', '')}]" for c in assumption.citations]
                )
                lines.append(f" {citation_refs}")

            lines.append("\n")

        return "\n".join(lines)

    def _get_identification_system_prompt(self) -> str:
        return """你是数学建模专家，擅长识别问题中需要做出的假设。

你的任务是分析问题，识别出所有必要的假设。假设应该：
1. 必要性：确实需要这个假设才能解决问题
2. 合理性：假设符合常识或有文献支持
3. 可验证性：假设可以通过敏感性分析验证

假设类型包括：
- simplification: 简化假设，忽略次要因素
- rationality: 合理性假设，关于行为或决策
- consistency: 一致性假设，时空不变性
- boundary: 边界假设，系统边界定义
- data: 数据假设，关于数据质量

请以JSON格式返回假设候选列表。"""

    def _get_generation_system_prompt(self) -> str:
        return """你是数学建模论文写作专家，擅长撰写严谨的假设陈述和论证。

假设陈述应该：
1. 简洁明确，避免歧义
2. 使用数学语言或专业术语
3. 明确假设的适用范围

论证应该：
1. 解释为什么这个假设是合理的
2. 如有可能，引用相关文献
3. 分析假设不成立时的影响

请以JSON格式返回完整的假设描述。"""

    def _build_identification_prompt(
        self,
        problem_description: str,
        problem_type: str,
        data_description: Optional[str],
        evidence: Optional[List[EvidenceSnippet]],
    ) -> str:
        prompt_parts = [
            f"## 问题描述\n{problem_description}",
            f"\n## 问题类型\n{problem_type}",
        ]

        if data_description:
            prompt_parts.append(f"\n## 数据描述\n{data_description}")

        if evidence:
            evidence_text = "\n".join([e["content"][:200] for e in evidence[:3]])
            prompt_parts.append(f"\n## 相关证据\n{evidence_text}")

        # 添加模板参考
        templates = self.COMMON_ASSUMPTION_TEMPLATES.get(problem_type, [])
        if templates:
            template_text = "\n".join([f"- {t}" for t in templates])
            prompt_parts.append(f"\n## 常见假设模板参考\n{template_text}")

        prompt_parts.append(
            """
\n## 任务
请识别这个问题需要做出的假设，以JSON格式返回：
```json
{
    "candidates": [
        {
            "statement": "假设陈述",
            "category": "simplification/rationality/consistency/boundary/data",
            "necessity_score": 0.9,
            "common_in_literature": true,
            "potential_citations": ["来源描述"]
        }
    ]
}
```"""
        )

        return "\n".join(prompt_parts)

    def _build_generation_prompt(
        self,
        candidate: AssumptionCandidate,
        problem_context: str,
        evidence: Optional[List[EvidenceSnippet]],
    ) -> str:
        prompt_parts = [
            f"## 问题上下文\n{problem_context}",
            f"\n## 假设候选\n- 陈述: {candidate.statement}",
            f"- 类别: {candidate.category.value}",
            f"- 必要性: {candidate.necessity_score}",
        ]

        if evidence:
            evidence_text = "\n".join([e["content"][:300] for e in evidence[:3]])
            prompt_parts.append(f"\n## 相关证据\n{evidence_text}")

        prompt_parts.append(
            """
\n## 任务
为这个假设生成完整的描述和论证，以JSON格式返回：
```json
{
    "statement": "简洁的假设陈述（一句话）",
    "detailed_statement": "详细的假设陈述（包含条件和范围）",
    "justification": "论证理由（为什么这个假设合理）",
    "impact_analysis": "影响分析（假设不成立会如何影响结果）",
    "impact_level": "critical/high/medium/low",
    "confidence": 0.85,
    "related_variables": ["变量1", "变量2"],
    "verification_methods": ["验证方法1"]
}
```"""
        )

        return "\n".join(prompt_parts)

    def _parse_candidates(
        self, content: str, problem_type: str
    ) -> List[AssumptionCandidate]:
        """解析候选假设"""
        candidates: List[AssumptionCandidate] = []

        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(content[json_start:json_end])

                for item in data.get("candidates", []):
                    try:
                        category = AssumptionCategory(
                            item.get("category", "simplification")
                        )
                    except ValueError:
                        category = AssumptionCategory.SIMPLIFICATION

                    candidates.append(
                        AssumptionCandidate(
                            statement=item.get("statement", ""),
                            category=category,
                            necessity_score=float(item.get("necessity_score", 0.5)),
                            common_in_literature=item.get(
                                "common_in_literature", False
                            ),
                            potential_citations=item.get("potential_citations", []),
                        )
                    )
        except json.JSONDecodeError as e:
            logger.error("Failed to parse candidates: %s", e)

        return candidates

    def _parse_generated_assumption(
        self, content: str, candidate: AssumptionCandidate
    ) -> GeneratedAssumption:
        """解析生成的假设"""
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(content[json_start:json_end])

                try:
                    impact_level = ImpactLevel(data.get("impact_level", "medium"))
                except ValueError:
                    impact_level = ImpactLevel.MEDIUM

                return GeneratedAssumption(
                    id=f"asm_{uuid.uuid4().hex[:8]}",
                    statement=data.get("statement", candidate.statement),
                    detailed_statement=data.get("detailed_statement", ""),
                    category=candidate.category,
                    justification=data.get("justification", ""),
                    impact_analysis=data.get("impact_analysis", ""),
                    impact_level=impact_level,
                    confidence=float(data.get("confidence", 0.7)),
                    related_variables=data.get("related_variables", []),
                    verification_methods=data.get("verification_methods", []),
                )
        except json.JSONDecodeError as e:
            logger.error("Failed to parse generated assumption: %s", e)

        # 降级：返回基础假设
        return GeneratedAssumption(
            id=f"asm_{uuid.uuid4().hex[:8]}",
            statement=candidate.statement,
            detailed_statement=candidate.statement,
            category=candidate.category,
            justification="基于问题背景的合理假设",
            impact_analysis="需要通过敏感性分析验证",
            impact_level=ImpactLevel.MEDIUM,
            confidence=candidate.necessity_score,
        )

    def _sort_assumptions(
        self, assumptions: List[GeneratedAssumption]
    ) -> List[GeneratedAssumption]:
        """按类别和影响程度排序"""
        category_order = {
            AssumptionCategory.BOUNDARY: 0,
            AssumptionCategory.SIMPLIFICATION: 1,
            AssumptionCategory.DATA: 2,
            AssumptionCategory.RATIONALITY: 3,
            AssumptionCategory.CONSISTENCY: 4,
        }

        impact_order = {
            ImpactLevel.CRITICAL: 0,
            ImpactLevel.HIGH: 1,
            ImpactLevel.MEDIUM: 2,
            ImpactLevel.LOW: 3,
        }

        return sorted(
            assumptions,
            key=lambda a: (
                category_order.get(a.category, 99),
                impact_order.get(a.impact_level, 99),
            ),
        )


# 便捷函数
async def generate_assumptions(
    problem_description: str,
    problem_type: str = "optimization",
    data_description: Optional[str] = None,
    max_assumptions: int = 8,
    run_id: Optional[str] = None,
) -> List[GeneratedAssumption]:
    """
    便捷函数：生成问题所需的所有假设

    Args:
        problem_description: 问题描述
        problem_type: 问题类型 (optimization/prediction/evaluation/simulation)
        data_description: 数据描述
        max_assumptions: 最大假设数量
        run_id: 运行ID

    Returns:
        生成的假设列表
    """
    generator = AssumptionGenerator(run_id=run_id)
    return await generator.generate_all_assumptions(
        problem_description=problem_description,
        problem_type=problem_type,
        data_description=data_description,
        max_assumptions=max_assumptions,
    )
