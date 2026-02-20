"""
Research Planner - 研究规划器
==============================

功能：
1. 根据问题分析生成背景研究计划
2. 明确文献与参考资料类型
3. 规划假设验证路径
4. 与RAG知识库与Web搜索工具联动
"""

import json
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.llm.llm_gateway import chat_completion
from app.core.research.assumption_generator import AssumptionGenerator
from app.core.research.rag_store import RAGStore
from app.core.research.web_search_tool import WebSearchTool
from app.utils.log_util import logger


@dataclass
class ResearchPlan:
    """研究规划结果"""

    problem_id: str
    research_objectives: List[str]
    literature_types: List[Dict[str, Any]]
    search_queries: List[str]
    verification_steps: List[Dict[str, Any]]
    timeline: Dict[str, float]
    priority_order: List[str]


class ResearchPlanner:
    """研究规划器"""

    def __init__(
        self,
        run_id: Optional[str] = None,
        rag_store: Optional[RAGStore] = None,
        web_search_tool: Optional[WebSearchTool] = None,
        assumption_generator: Optional[AssumptionGenerator] = None,
    ) -> None:
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.rag_store = rag_store
        self.web_search_tool = web_search_tool
        self.assumption_generator = assumption_generator or AssumptionGenerator(
            run_id=self.run_id
        )

    async def create_plan(self, problem_analysis: Dict[str, Any]) -> ResearchPlan:
        """
        创建研究计划

        Args:
            problem_analysis: 问题分析结果

        Returns:
            研究计划
        """
        analysis = self._normalize_analysis(problem_analysis)
        problem_id = (
            self._ensure_str(analysis.get("problem_id"))
            or f"prob_{uuid.uuid4().hex[:8]}"
        )

        hypotheses = await self._collect_hypotheses(analysis)
        tool_context = await self._collect_tool_context()
        prompt = self._build_plan_prompt(analysis, hypotheses, tool_context)

        response = await chat_completion(
            messages=[
                {"role": "system", "content": self._get_planner_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            run_id=self.run_id,
            agent_id="research_planner",
        )

        plan = self._parse_plan_response(
            response.content, problem_id, analysis, hypotheses
        )

        if not plan.verification_steps and hypotheses:
            plan.verification_steps = await self.plan_verification_path(hypotheses)

        if not plan.search_queries:
            plan.search_queries = self._build_search_queries(analysis)

        if not plan.priority_order:
            plan.priority_order = self._fallback_priority(plan)

        return plan

    async def prioritize_research(self, plan: ResearchPlan) -> ResearchPlan:
        """
        调整研究优先级排序

        Args:
            plan: 研究计划

        Returns:
            调整后的研究计划
        """
        if not plan.research_objectives:
            return plan

        prompt = self._build_priority_prompt(plan)
        response = await chat_completion(
            messages=[
                {"role": "system", "content": self._get_priority_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            run_id=self.run_id,
            agent_id="research_planner",
        )

        priority_order = self._parse_priority_response(response.content)
        if priority_order:
            plan.priority_order = priority_order
        elif not plan.priority_order:
            plan.priority_order = self._fallback_priority(plan)

        return plan

    async def suggest_sources(self, topic: str) -> List[Dict[str, Any]]:
        """
        推荐主题相关的参考来源

        Args:
            topic: 研究主题

        Returns:
            来源建议列表
        """
        sources: List[Dict[str, Any]] = []

        if self.rag_store:
            try:
                count = await self.rag_store.count()
                if count > 0:
                    sources.append(
                        {
                            "source_type": "rag_store",
                            "title": "内部知识库",
                            "detail": f"可用文档数量: {count}",
                            "confidence": 0.6,
                        }
                    )
            except Exception as e:
                logger.warning("RAG store unavailable: %s", e)

        if self.web_search_tool:
            try:
                results = await self.web_search_tool.search(topic, num_results=5)
                for r in results:
                    sources.append(
                        {
                            "source_type": "web",
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet,
                            "provider": r.source,
                            "relevance_score": r.relevance_score,
                        }
                    )
            except Exception as e:
                logger.warning("Web search failed: %s", e)

        if sources:
            return sources

        prompt = self._build_source_prompt(topic)
        response = await chat_completion(
            messages=[
                {"role": "system", "content": self._get_source_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            run_id=self.run_id,
            agent_id="research_planner",
        )

        return self._parse_source_response(response.content)

    async def plan_verification_path(
        self, hypotheses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        规划假设验证路径

        Args:
            hypotheses: 假设列表

        Returns:
            假设验证步骤
        """
        if not hypotheses:
            return []

        prompt = self._build_verification_prompt(hypotheses)
        response = await chat_completion(
            messages=[
                {"role": "system", "content": self._get_verification_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            run_id=self.run_id,
            agent_id="research_planner",
        )

        steps = self._parse_verification_response(response.content)
        if steps:
            return steps

        return self._fallback_verification_steps(hypotheses)

    def _normalize_analysis(self, analysis: Any) -> Dict[str, Any]:
        if isinstance(analysis, dict):
            return analysis
        if is_dataclass(analysis):
            return asdict(analysis)
        if hasattr(analysis, "__dict__"):
            return dict(analysis.__dict__)
        return {}

    async def _collect_hypotheses(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        hypotheses = self._extract_hypotheses(analysis)
        if hypotheses:
            return hypotheses

        problem_text = self._ensure_str(
            analysis.get("original_text") or analysis.get("core_question")
        )
        problem_type = self._normalize_problem_type(analysis.get("problem_type"))
        data_description = self._format_list_text(analysis.get("available_data"))

        if not problem_text or not self.assumption_generator:
            return []

        try:
            candidates = await self.assumption_generator.identify_required_assumptions(
                problem_description=problem_text,
                problem_type=problem_type or "optimization",
                data_description=data_description or None,
            )
            hypotheses = [
                {
                    "statement": c.statement,
                    "category": c.category.value,
                    "necessity_score": c.necessity_score,
                    "potential_citations": c.potential_citations,
                }
                for c in candidates[:6]
            ]
        except Exception as e:
            logger.warning("Assumption generation failed: %s", e)
            hypotheses = []

        return hypotheses

    async def _collect_tool_context(self) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "rag_store": {"available": False, "doc_count": 0},
            "web_search": {"available": False},
        }

        if self.rag_store:
            try:
                count = await self.rag_store.count()
                context["rag_store"] = {"available": True, "doc_count": count}
            except Exception as e:
                logger.warning("RAG store count failed: %s", e)

        if self.web_search_tool:
            context["web_search"] = {"available": True}

        return context

    def _extract_hypotheses(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw = (
            analysis.get("hypotheses")
            or analysis.get("assumptions")
            or analysis.get("competing_hypotheses")
            or []
        )

        if not isinstance(raw, list):
            return []

        output: List[Dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                output.append(item)
            elif is_dataclass(item):
                output.append(asdict(item))
            elif hasattr(item, "__dict__"):
                output.append(dict(item.__dict__))

        return output

    def _get_planner_system_prompt(self) -> str:
        return (
            "你是数学建模比赛研究规划专家，负责制定可执行的背景研究计划。\n"
            "要求输出严格JSON，字段必须齐全，避免空泛。\n"
            "研究目标要具体，文献类型要可检索，搜索查询要可直接使用。\n"
            "假设验证路径要包含方法、数据与可检验指标。时间线用小时(float)。"
        )

    def _build_plan_prompt(
        self,
        analysis: Dict[str, Any],
        hypotheses: List[Dict[str, Any]],
        tool_context: Dict[str, Any],
    ) -> str:
        core_question = self._ensure_str(analysis.get("core_question"))
        problem_text = self._ensure_str(analysis.get("original_text"))
        problem_type = self._normalize_problem_type(analysis.get("problem_type"))
        objectives = analysis.get("key_objectives", [])
        constraints = analysis.get("constraints", [])
        data = analysis.get("available_data", [])
        variables = analysis.get("key_variables", {})
        success = analysis.get("success_criteria", [])
        recommended = self._ensure_str(analysis.get("recommended_perspective"))

        return (
            "## 问题分析\n"
            f"核心问题: {core_question}\n"
            f"问题类型: {problem_type}\n"
            f"问题原文: {problem_text[:800]}\n\n"
            f"目标: {json.dumps(objectives, ensure_ascii=False)}\n"
            f"约束: {json.dumps(constraints, ensure_ascii=False)}\n"
            f"可用数据: {json.dumps(data, ensure_ascii=False)}\n"
            f"关键变量: {json.dumps(variables, ensure_ascii=False)}\n"
            f"成功标准: {json.dumps(success, ensure_ascii=False)}\n"
            f"推荐视角: {recommended}\n\n"
            "## 候选假设/假设\n"
            f"{json.dumps(hypotheses, ensure_ascii=False)}\n\n"
            "## 工具可用性\n"
            f"RAG知识库: {json.dumps(tool_context.get('rag_store', {}), ensure_ascii=False)}\n"
            f"Web搜索工具: {json.dumps(tool_context.get('web_search', {}), ensure_ascii=False)}\n\n"
            "## 任务\n"
            "请制定研究计划，以JSON格式返回：\n"
            "```json\n"
            "{\n"
            "  \\\"research_objectives\\\": [\\\"研究目标1\\\"],\n"
            "  \\\"literature_types\\\": [\n"
            "    {\\\"type\\\": \\\"综述/教材/期刊论文/行业报告/官方统计/数据集/标准规范\\\", \\\"purpose\\\": \\\"用途\\\", \\\"priority\\\": \\\"high/medium/low\\\", \\\"examples\\\": [\\\"示例\\\"]}\n"
            "  ],\n"
            "  \\\"search_queries\\\": [\\\"可直接检索的查询\\\"],\n"
            "  \\\"verification_steps\\\": [\n"
            "    {\\\"hypothesis\\\": \\\"假设\\\", \\\"methods\\\": [\\\"方法\\\"], \\\"data_needed\\\": [\\\"数据\\\"], \\\"acceptance_criteria\\\": \\\"判定标准\\\"}\n"
            "  ],\n"
            "  \\\"timeline\\\": {\\\"background_research\\\": 2.0, \\\"data_check\\\": 1.0, \\\"assumption_validation\\\": 2.0, \\\"summary\\\": 1.0},\n"
            "  \\\"priority_order\\\": [\\\"优先事项1\\\", \\\"优先事项2\\\"]\n"
            "}\n"
            "```"
        )

    def _parse_plan_response(
        self,
        content: str,
        problem_id: str,
        analysis: Dict[str, Any],
        hypotheses: List[Dict[str, Any]],
    ) -> ResearchPlan:
        data = self._extract_json(content)
        fallback = self._fallback_plan(problem_id, analysis, hypotheses)
        if not data:
            return fallback

        research_objectives = self._ensure_list_str(data.get("research_objectives"))
        literature_types = self._ensure_list_dict(data.get("literature_types"))
        search_queries = self._ensure_list_str(data.get("search_queries"))
        verification_steps = self._ensure_list_dict(data.get("verification_steps"))
        timeline = self._ensure_timeline(data.get("timeline"))
        priority_order = self._ensure_list_str(data.get("priority_order"))

        if not research_objectives:
            research_objectives = fallback.research_objectives
        if not literature_types:
            literature_types = fallback.literature_types
        if not search_queries:
            search_queries = fallback.search_queries
        if not timeline:
            timeline = fallback.timeline
        if not priority_order:
            priority_order = fallback.priority_order

        return ResearchPlan(
            problem_id=problem_id,
            research_objectives=research_objectives,
            literature_types=literature_types,
            search_queries=search_queries,
            verification_steps=verification_steps,
            timeline=timeline,
            priority_order=priority_order,
        )

    def _fallback_plan(
        self,
        problem_id: str,
        analysis: Dict[str, Any],
        hypotheses: List[Dict[str, Any]],
    ) -> ResearchPlan:
        objectives = self._ensure_list_str(analysis.get("key_objectives"))
        core_question = self._ensure_str(analysis.get("core_question"))
        if not objectives:
            if core_question:
                objectives = [core_question]
            else:
                objectives = ["澄清问题背景与关键变量"]

        literature_types = [
            {
                "type": "综述/教材",
                "purpose": "建立领域基础与常用模型",
                "priority": "high",
                "examples": ["经典教材", "近三年综述"],
            },
            {
                "type": "期刊论文",
                "purpose": "获取常见建模框架与参数范围",
                "priority": "high",
                "examples": ["核心期刊论文", "高被引文章"],
            },
            {
                "type": "官方统计/数据集",
                "purpose": "确认数据口径与可用性",
                "priority": "medium",
                "examples": ["官方统计年鉴", "公开数据平台"],
            },
            {
                "type": "行业报告/标准规范",
                "purpose": "补充实际约束与指标定义",
                "priority": "medium",
                "examples": ["行业白皮书", "技术规范"],
            },
        ]

        search_queries = self._build_search_queries(analysis)
        verification_steps = self._fallback_verification_steps(hypotheses)
        timeline = {
            "background_research": 2.5,
            "data_check": 1.5,
            "assumption_validation": 2.0,
            "summary": 1.0,
        }
        priority_order = self._fallback_priority(
            ResearchPlan(
                problem_id=problem_id,
                research_objectives=objectives,
                literature_types=literature_types,
                search_queries=search_queries,
                verification_steps=verification_steps,
                timeline=timeline,
                priority_order=[],
            )
        )

        return ResearchPlan(
            problem_id=problem_id,
            research_objectives=objectives,
            literature_types=literature_types,
            search_queries=search_queries,
            verification_steps=verification_steps,
            timeline=timeline,
            priority_order=priority_order,
        )

    def _build_search_queries(self, analysis: Dict[str, Any]) -> List[str]:
        core_question = self._ensure_str(analysis.get("core_question"))
        problem_type = self._normalize_problem_type(analysis.get("problem_type"))
        variables = analysis.get("key_variables", {})

        queries: List[str] = []
        if core_question:
            queries.append(f"{core_question} 数学建模")
            queries.append(f"{core_question} 常用模型")

        if problem_type:
            queries.append(f"{problem_type} 问题 评价指标")
            queries.append(f"{problem_type} 模型 竞赛范例")

        if isinstance(variables, dict):
            for key in list(variables.keys())[:5]:
                queries.append(f"{key} 数据 获取")
                queries.append(f"{key} 参数 范围")

        return self._dedupe_list(queries)

    def _fallback_priority(self, plan: ResearchPlan) -> List[str]:
        priorities: List[str] = []
        priorities.extend(plan.research_objectives)
        if plan.literature_types:
            priorities.append("确定关键文献与数据来源")
        if plan.verification_steps:
            priorities.append("验证关键假设的可行性")
        if plan.search_queries:
            priorities.append("扩展检索关键词并覆盖不同视角")
        return self._dedupe_list(priorities)

    def _get_priority_system_prompt(self) -> str:
        return (
            "你是数学建模研究主管，负责排序研究优先级。"
            "输出严格JSON，仅返回priority_order列表。"
        )

    def _build_priority_prompt(self, plan: ResearchPlan) -> str:
        return (
            "请基于以下研究计划排序优先级：\n"
            f"研究目标: {json.dumps(plan.research_objectives, ensure_ascii=False)}\n"
            f"文献类型: {json.dumps(plan.literature_types, ensure_ascii=False)}\n"
            f"验证步骤: {json.dumps(plan.verification_steps, ensure_ascii=False)}\n"
            f"时间线: {json.dumps(plan.timeline, ensure_ascii=False)}\n\n"
            "以JSON格式返回：\n"
            "```json\n"
            "{\\\"priority_order\\\": [\\\"优先事项1\\\", \\\"优先事项2\\\"]}\n"
            "```"
        )

    def _parse_priority_response(self, content: str) -> List[str]:
        data = self._extract_json(content)
        if not data:
            return []
        return self._ensure_list_str(data.get("priority_order"))

    def _get_source_system_prompt(self) -> str:
        return (
            "你是数学建模研究助理，擅长推荐可检索的参考来源类型与检索提示。"
            "输出严格JSON，避免空泛描述。"
        )

    def _build_source_prompt(self, topic: str) -> str:
        return (
            "请为以下主题推荐参考来源，以JSON格式返回：\n"
            f"主题: {topic}\n\n"
            "```json\n"
            "{\n"
            "  \\\"sources\\\": [\n"
            "    {\\\"type\\\": \\\"期刊论文/综述/教材/官方统计/行业报告/标准规范/数据集/开源代码\\\", \\\"name\\\": \\\"示例来源\\\", \\\"reason\\\": \\\"用途\\\", \\\"search_hint\\\": \\\"检索提示\\\"}\n"
            "  ]\n"
            "}\n"
            "```"
        )

    def _parse_source_response(self, content: str) -> List[Dict[str, Any]]:
        data = self._extract_json(content)
        if not data:
            return []
        sources = self._ensure_list_dict(data.get("sources"))
        return sources

    def _get_verification_system_prompt(self) -> str:
        return (
            "你是数学建模验证专家，负责为假设规划可执行的验证路径。"
            "输出严格JSON，包含方法、数据需求与判定标准。"
        )

    def _build_verification_prompt(self, hypotheses: List[Dict[str, Any]]) -> str:
        return (
            "请为以下假设设计验证步骤：\n"
            f"{json.dumps(hypotheses, ensure_ascii=False)}\n\n"
            "以JSON格式返回：\n"
            "```json\n"
            "{\n"
            "  \\\"verification_steps\\\": [\n"
            "    {\\\"hypothesis\\\": \\\"假设\\\", \\\"methods\\\": [\\\"敏感性分析\\\"], \\\"data_needed\\\": [\\\"历史数据\\\"], \\\"acceptance_criteria\\\": \\\"指标稳定且符合预期\\\"}\n"
            "  ]\n"
            "}\n"
            "```"
        )

    def _parse_verification_response(self, content: str) -> List[Dict[str, Any]]:
        data = self._extract_json(content)
        if not data:
            return []
        return self._ensure_list_dict(data.get("verification_steps"))

    def _fallback_verification_steps(
        self, hypotheses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        for hyp in hypotheses[:6]:
            statement = self._ensure_str(hyp.get("statement"))
            if not statement:
                continue
            steps.append(
                {
                    "hypothesis": statement,
                    "methods": ["敏感性分析", "对比实验", "交叉验证"],
                    "data_needed": ["历史数据", "参数范围"],
                    "acceptance_criteria": "关键指标稳定且与经验结论一致",
                }
            )
        return steps

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError as e:
            logger.warning("JSON parse failed: %s", e)
        return None

    def _ensure_list_str(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _ensure_list_dict(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        if isinstance(value, dict):
            return [value]
        return []

    def _ensure_timeline(self, value: Any) -> Dict[str, float]:
        if not isinstance(value, dict):
            return {}
        timeline: Dict[str, float] = {}
        for key, raw in value.items():
            timeline[key] = self._coerce_float(raw, default=0.0)
        return timeline

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def _normalize_problem_type(self, value: Any) -> str:
        if isinstance(value, Enum):
            return str(value.value)
        if hasattr(value, "value"):
            return str(getattr(value, "value"))
        if value is None:
            return ""
        return str(value)

    def _ensure_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _format_list_text(self, value: Any) -> str:
        items = self._ensure_list_str(value)
        return "、".join(items)

    def _dedupe_list(self, items: List[str]) -> List[str]:
        seen: set[str] = set()
        output: List[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            output.append(normalized)
        return output
