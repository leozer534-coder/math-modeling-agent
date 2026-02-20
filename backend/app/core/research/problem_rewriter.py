"""
Problem Rewriter - 问题重构器
==============================

功能：
1. 识别问题核心要素
2. 分解复杂任务为子问题
3. 提供多元解读（至少3种切入角度）
4. 分析各角度的利弊
5. 生成结构化问题描述
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.llm.llm_gateway import chat_completion
from app.utils.log_util import logger


class ProblemType(Enum):
    OPTIMIZATION = "optimization"
    PREDICTION = "prediction"
    CLASSIFICATION = "classification"
    EVALUATION = "evaluation"
    SCHEDULING = "scheduling"
    RESOURCE_ALLOCATION = "resource_allocation"
    PATH_PLANNING = "path_planning"
    SIMULATION = "simulation"
    GAME_THEORY = "game_theory"
    UNKNOWN = "unknown"


@dataclass
class SubProblem:
    id: str
    title: str
    description: str
    dependencies: List[str]
    estimated_difficulty: str
    suggested_approaches: List[str]


@dataclass
class ProblemPerspective:
    name: str
    description: str
    core_model_types: List[str]
    advantages: List[str]
    disadvantages: List[str]
    data_requirements: List[str]
    recommended_when: str


@dataclass
class ProblemAnalysis:
    problem_id: str
    original_text: str
    core_question: str
    problem_type: ProblemType
    key_objectives: List[str]
    constraints: List[str]
    available_data: List[str]
    sub_problems: List[SubProblem]
    perspectives: List[ProblemPerspective]
    recommended_perspective: str
    key_variables: Dict[str, str]
    success_criteria: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ProblemRewriter:
    def __init__(self, run_id: Optional[str] = None) -> None:
        self.run_id = run_id or str(uuid.uuid4())[:8]

    async def analyze_problem(
        self,
        problem_text: str,
        attachments: Optional[List[str]] = None,
    ) -> ProblemAnalysis:
        core_analysis = await self._extract_core_elements(problem_text)
        sub_problems = await self._decompose_problem(problem_text, core_analysis)
        perspectives = await self._generate_perspectives(problem_text, core_analysis)
        recommended = self._recommend_perspective(perspectives)

        return ProblemAnalysis(
            problem_id=f"prob_{uuid.uuid4().hex[:8]}",
            original_text=problem_text,
            core_question=core_analysis.get("core_question", ""),
            problem_type=self._classify_problem_type(core_analysis),
            key_objectives=core_analysis.get("objectives", []),
            constraints=core_analysis.get("constraints", []),
            available_data=core_analysis.get("data", []),
            sub_problems=sub_problems,
            perspectives=perspectives,
            recommended_perspective=recommended,
            key_variables=core_analysis.get("variables", {}),
            success_criteria=core_analysis.get("success_criteria", []),
        )

    async def _extract_core_elements(self, problem_text: str) -> Dict[str, Any]:
        prompt = f"""分析以下数学建模问题，提取核心要素：

## 问题原文
{problem_text[:3000]}

请以JSON格式提取：
{{
    "core_question": "用一句话概括核心问题",
    "problem_type": "optimization/prediction/classification/evaluation/scheduling/resource_allocation/path_planning/simulation/game_theory",
    "objectives": ["目标1", "目标2"],
    "constraints": ["约束1", "约束2"],
    "data": ["可用数据1", "可用数据2"],
    "variables": {{"变量1": "含义", "变量2": "含义"}},
    "success_criteria": ["成功标准1", "成功标准2"]
}}"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，擅长分析问题结构。返回严格的JSON格式。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            run_id=self.run_id,
            agent_id="problem_rewriter",
        )

        try:
            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response.content[json_start:json_end])
        except json.JSONDecodeError:
            logger.warning("Failed to parse core elements")

        return {}

    async def _decompose_problem(
        self, problem_text: str, core_analysis: Dict[str, Any]
    ) -> List[SubProblem]:
        prompt = f"""将以下问题分解为可独立解决的子问题：

## 问题概述
{core_analysis.get("core_question", problem_text[:500])}

## 目标
{json.dumps(core_analysis.get("objectives", []), ensure_ascii=False)}

请以JSON格式返回子问题列表：
{{
    "sub_problems": [
        {{
            "id": "sp1",
            "title": "子问题标题",
            "description": "详细描述",
            "dependencies": [],
            "estimated_difficulty": "easy/medium/hard",
            "suggested_approaches": ["方法1", "方法2"]
        }}
    ]
}}"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，擅长问题分解。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            run_id=self.run_id,
            agent_id="problem_rewriter",
        )

        sub_problems: List[SubProblem] = []
        try:
            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response.content[json_start:json_end])
                for sp in data.get("sub_problems", []):
                    sub_problems.append(
                        SubProblem(
                            id=sp.get("id", f"sp_{len(sub_problems) + 1}"),
                            title=sp.get("title", ""),
                            description=sp.get("description", ""),
                            dependencies=sp.get("dependencies", []),
                            estimated_difficulty=sp.get(
                                "estimated_difficulty", "medium"
                            ),
                            suggested_approaches=sp.get("suggested_approaches", []),
                        )
                    )
        except json.JSONDecodeError:
            logger.warning("Failed to parse sub-problems")

        return sub_problems

    async def _generate_perspectives(
        self, problem_text: str, core_analysis: Dict[str, Any]
    ) -> List[ProblemPerspective]:
        prompt = f"""为以下问题提供至少3种不同的建模视角：

## 问题
{core_analysis.get("core_question", problem_text[:500])}

## 问题类型
{core_analysis.get("problem_type", "未知")}

请以JSON格式返回多种视角：
{{
    "perspectives": [
        {{
            "name": "视角名称",
            "description": "视角描述",
            "core_model_types": ["模型类型1", "模型类型2"],
            "advantages": ["优势1", "优势2"],
            "disadvantages": ["劣势1", "劣势2"],
            "data_requirements": ["数据需求1"],
            "recommended_when": "适用场景"
        }}
    ]
}}"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，擅长从多角度分析问题。提供至少3种不同视角。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            run_id=self.run_id,
            agent_id="problem_rewriter",
        )

        perspectives: List[ProblemPerspective] = []
        try:
            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response.content[json_start:json_end])
                for p in data.get("perspectives", []):
                    perspectives.append(
                        ProblemPerspective(
                            name=p.get("name", ""),
                            description=p.get("description", ""),
                            core_model_types=p.get("core_model_types", []),
                            advantages=p.get("advantages", []),
                            disadvantages=p.get("disadvantages", []),
                            data_requirements=p.get("data_requirements", []),
                            recommended_when=p.get("recommended_when", ""),
                        )
                    )
        except json.JSONDecodeError:
            logger.warning("Failed to parse perspectives")

        return perspectives

    def _classify_problem_type(self, core_analysis: Dict[str, Any]) -> ProblemType:
        type_str = core_analysis.get("problem_type", "unknown")
        try:
            return ProblemType(type_str)
        except ValueError:
            return ProblemType.UNKNOWN

    def _recommend_perspective(self, perspectives: List[ProblemPerspective]) -> str:
        if not perspectives:
            return ""
        best = max(
            perspectives,
            key=lambda p: len(p.advantages) - len(p.disadvantages),
        )
        return best.name

    def format_for_paper(self, analysis: ProblemAnalysis) -> str:
        lines: List[str] = []

        lines.append("## 问题重述\n")
        lines.append(f"### 问题背景\n{analysis.original_text[:500]}...\n")

        lines.append(f"\n### 核心问题\n{analysis.core_question}\n")

        lines.append("\n### 问题目标\n")
        for i, obj in enumerate(analysis.key_objectives, 1):
            lines.append(f"{i}. {obj}")

        lines.append("\n\n### 约束条件\n")
        for constraint in analysis.constraints:
            lines.append(f"- {constraint}")

        if analysis.sub_problems:
            lines.append("\n\n### 问题分解\n")
            for sp in analysis.sub_problems:
                lines.append(f"**{sp.title}**: {sp.description}")

        return "\n".join(lines)


async def rewrite_problem(
    problem_text: str,
    run_id: Optional[str] = None,
) -> ProblemAnalysis:
    rewriter = ProblemRewriter(run_id=run_id)
    return await rewriter.analyze_problem(problem_text)
