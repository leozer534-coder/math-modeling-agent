"""
工作流增强器 - Workflow Enhancer
================================

在不修改现有 Agent 的情况下增强工作流能力

功能模块：
1. ProblemAnalysisEnhancer - 问题分析增强
2. CodeQualityEnhancer - 代码质量增强  
3. PaperQualityEnhancer - 论文质量增强
4. AgentCoordinator - 多智能体协作优化
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.utils.log_util import logger


try:
    from app.core.evaluation import (  # noqa: F401
        BenchmarkResult,
        PaperBenchmark,
        PaperBundle,
    )
    from app.core.memory import MemoryManager, create_memory_manager  # noqa: F401
except ImportError:
    MemoryManager = None
    PaperBenchmark = None


class EnhancementType(str, Enum):
    """增强类型"""
    PROBLEM_ANALYSIS = "problem_analysis"
    CODE_QUALITY = "code_quality"
    PAPER_QUALITY = "paper_quality"
    COORDINATION = "coordination"


@dataclass
class EnhancementResult:
    """增强结果"""
    enhancement_type: EnhancementType
    original_input: Any
    enhanced_output: Any
    improvements: List[str]
    suggestions: List[str]
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ================== 问题分析增强器 ==================

class ProblemAnalysisEnhancer:
    """
    问题分析增强器
    
    基于历史经验增强问题分析能力
    """
    
    def __init__(self, memory_manager: Optional["MemoryManager"] = None):
        self._memory = memory_manager
    
    async def enhance(
        self,
        problem_description: str,
        problem_type: str = "optimization"
    ) -> EnhancementResult:
        """
        增强问题分析
        
        Args:
            problem_description: 问题描述
            problem_type: 问题类型
            
        Returns:
            增强结果
        """
        improvements = []
        suggestions = []
        enhanced_context = ""
        
        # 检索历史经验
        if self._memory:
            try:
                experience = await self._memory.get_experience_for_problem(
                    problem_type=problem_type,
                    problem_description=problem_description[:500]
                )
                
                similar_cases = experience.get("similar_cases", [])
                if similar_cases:
                    improvements.append(f"发现 {len(similar_cases)} 个类似历史案例")
                    enhanced_context += "\n\n## 历史经验参考\n"
                    for case in similar_cases[:3]:
                        enhanced_context += f"- {case.get('content', '')[:200]}\n"
                
                lessons = experience.get("lessons_learned", [])
                if lessons:
                    improvements.append(f"整合 {len(lessons)} 条经验教训")
                    enhanced_context += "\n## 经验教训\n"
                    for lesson in lessons[:5]:
                        enhanced_context += f"- {lesson}\n"
                
                suggested_models = experience.get("suggested_models", [])
                if suggested_models:
                    suggestions.append(f"推荐模型: {', '.join(suggested_models[:3])}")
                    
            except Exception as e:
                logger.warning("检索历史经验失败: %s", e)
        
        # 添加通用分析建议
        suggestions.extend(self._get_analysis_suggestions(problem_type))
        
        return EnhancementResult(
            enhancement_type=EnhancementType.PROBLEM_ANALYSIS,
            original_input=problem_description,
            enhanced_output=problem_description + enhanced_context,
            improvements=improvements,
            suggestions=suggestions
        )
    
    def _get_analysis_suggestions(self, problem_type: str) -> List[str]:
        """获取分析建议"""
        type_suggestions = {
            "optimization": [
                "明确目标函数和约束条件",
                "考虑使用多种优化算法对比"
            ],
            "prediction": [
                "分析数据的时序特征",
                "考虑多模型融合提高准确率"
            ],
            "classification": [
                "检查类别平衡性",
                "使用交叉验证评估模型"
            ],
            "evaluation": [
                "确保指标权重合理性",
                "进行敏感性分析"
            ],
        }
        return type_suggestions.get(problem_type, [])


# ================== 代码质量增强器 ==================

class CodeQualityEnhancer:
    """
    代码质量增强器
    
    自动优化代码质量
    """
    
    def __init__(self):
        self._quality_checks = [
            self._check_imports,
            self._check_documentation,
            self._check_structure,
        ]
    
    async def enhance(self, code: str) -> EnhancementResult:
        """
        增强代码质量
        
        Args:
            code: 原始代码
            
        Returns:
            增强结果
        """
        improvements = []
        suggestions = []
        enhanced_code = code
        
        # 运行质量检查
        for check in self._quality_checks:
            result = check(code)
            suggestions.extend(result.get("suggestions", []))
            if result.get("fix"):
                enhanced_code = result["fix"](enhanced_code)
                improvements.append(result.get("improvement", ""))
        
        # 添加标准头部注释
        if not enhanced_code.startswith('"""') and not enhanced_code.startswith("'''"):
            header = '''"""
数学建模代码
生成时间: {}
"""\n\n'''.format(datetime.now().strftime("%Y-%m-%d %H:%M"))
            enhanced_code = header + enhanced_code
            improvements.append("添加了文件头部注释")
        
        return EnhancementResult(
            enhancement_type=EnhancementType.CODE_QUALITY,
            original_input=code,
            enhanced_output=enhanced_code,
            improvements=improvements,
            suggestions=suggestions
        )
    
    def _check_imports(self, code: str) -> Dict[str, Any]:
        """检查导入语句"""
        suggestions = []
        
        common_imports = {
            "numpy": "import numpy as np",
            "pandas": "import pandas as pd",
            "matplotlib": "import matplotlib.pyplot as plt",
        }
        
        for lib, import_stmt in common_imports.items():
            if lib in code and import_stmt not in code:
                suggestions.append(f"建议使用标准导入格式: {import_stmt}")
        
        return {"suggestions": suggestions}
    
    def _check_documentation(self, code: str) -> Dict[str, Any]:
        """检查文档"""
        suggestions = []
        
        # 检查函数是否有文档字符串
        import re
        functions = re.findall(r"def (\w+)\(", code)
        docstrings = code.count('"""') // 2
        
        if functions and docstrings < len(functions) * 0.5:
            suggestions.append("建议为主要函数添加文档字符串")
        
        return {"suggestions": suggestions}
    
    def _check_structure(self, code: str) -> Dict[str, Any]:
        """检查代码结构"""
        suggestions = []
        
        lines = code.split("\n")
        if len(lines) > 100:
            suggestions.append("代码较长，建议拆分为多个函数或模块")
        
        # 检查是否有主入口
        if "if __name__" not in code and len(lines) > 20:
            suggestions.append("建议添加 if __name__ == '__main__': 主入口")
        
        return {"suggestions": suggestions}


# ================== 论文质量增强器 ==================

class PaperQualityEnhancer:
    """
    论文质量增强器
    
    基于 Benchmark 评分提供改进建议
    """
    
    def __init__(self):
        self._benchmark = PaperBenchmark() if PaperBenchmark else None
    
    async def enhance(
        self,
        paper_content: str,
        task_id: str = "unknown",
        **kwargs
    ) -> EnhancementResult:
        """
        增强论文质量
        
        Args:
            paper_content: 论文内容
            task_id: 任务ID
            
        Returns:
            增强结果
        """
        improvements = []
        suggestions = []
        
        # 运行 Benchmark 评测
        if self._benchmark:
            try:
                bundle = PaperBundle(
                    task_id=task_id,
                    paper_content=paper_content,
                    **kwargs
                )
                result = self._benchmark.evaluate(bundle)
                
                grade_str = result.grade.value if hasattr(result.grade, "value") else str(result.grade)
                improvements.append(f"论文评分: {result.overall_score:.1f}/100 ({grade_str})")
                suggestions.extend(result.suggestions)
                
                # 添加维度分析
                for dim, score in result.dimension_scores.items():
                    if score < 70:
                        suggestions.append(f"{dim}得分较低({score:.0f})，建议重点改进")
                        
            except Exception as e:
                logger.warning("论文评测失败: %s", e)
        
        # 添加通用改进建议
        suggestions.extend(self._get_general_suggestions(paper_content))
        
        return EnhancementResult(
            enhancement_type=EnhancementType.PAPER_QUALITY,
            original_input=paper_content[:500] + "...",
            enhanced_output=paper_content,  # 论文内容不做自动修改
            improvements=improvements,
            suggestions=suggestions[:8]  # 限制建议数量
        )
    
    def _get_general_suggestions(self, content: str) -> List[str]:
        """获取通用改进建议"""
        suggestions = []
        
        # 长度检查
        if len(content) < 5000:
            suggestions.append("论文内容较短，建议充实各章节内容")
        
        # 关键章节检查
        required_sections = ["摘要", "模型假设", "模型建立", "模型求解", "结果分析"]
        missing = [s for s in required_sections if s not in content]
        if missing:
            suggestions.append(f"缺少关键章节: {', '.join(missing[:3])}")
        
        return suggestions


# ================== 智能体协调器 ==================

class AgentCoordinator:
    """
    多智能体协作协调器
    
    优化任务分配和协作流程
    """
    
    def __init__(self):
        self._task_queue: List[Dict[str, Any]] = []
        self._completed_tasks: List[Dict[str, Any]] = []
        self._agent_status: Dict[str, str] = {}
    
    async def schedule_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """
        调度任务
        
        Args:
            task_type: 任务类型
            task_data: 任务数据
            priority: 优先级 (1-10, 10最高)
            
        Returns:
            任务ID
        """
        import uuid
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        task = {
            "id": task_id,
            "type": task_type,
            "data": task_data,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        self._task_queue.append(task)
        self._task_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info("任务已调度: %s (类型: %s, 优先级: %s)", task_id, task_type, priority)
        
        return task_id
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行任务"""
        for task in self._task_queue:
            if task["status"] == "pending":
                task["status"] = "running"
                return task
        return None
    
    def complete_task(self, task_id: str, result: Any = None) -> None:
        """标记任务完成"""
        for task in self._task_queue:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["result"] = result
                task["completed_at"] = datetime.now().isoformat()
                self._completed_tasks.append(task)
                self._task_queue.remove(task)
                logger.info("任务完成: %s", task_id)
                break
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            "pending_tasks": len([t for t in self._task_queue if t["status"] == "pending"]),
            "running_tasks": len([t for t in self._task_queue if t["status"] == "running"]),
            "completed_tasks": len(self._completed_tasks),
            "agent_status": self._agent_status
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """获取优化建议"""
        suggestions = []
        
        # 分析任务完成情况
        if self._completed_tasks:
            avg_time = sum(1 for t in self._completed_tasks) / len(self._completed_tasks)
            if avg_time > 10:
                suggestions.append("任务执行时间较长，考虑并行处理")
        
        # 检查任务队列
        pending = len([t for t in self._task_queue if t["status"] == "pending"])
        if pending > 5:
            suggestions.append(f"有 {pending} 个待处理任务，建议优化调度策略")
        
        return suggestions


# ================== 工作流增强器（主类） ==================

class WorkflowEnhancer:
    """
    工作流增强器
    
    整合所有增强模块，提供统一接口
    """
    
    def __init__(
        self,
        memory_manager: Optional["MemoryManager"] = None,
        enable_problem_enhancement: bool = True,
        enable_code_enhancement: bool = True,
        enable_paper_enhancement: bool = True
    ):
        self.problem_enhancer = ProblemAnalysisEnhancer(memory_manager) if enable_problem_enhancement else None
        self.code_enhancer = CodeQualityEnhancer() if enable_code_enhancement else None
        self.paper_enhancer = PaperQualityEnhancer() if enable_paper_enhancement else None
        self.coordinator = AgentCoordinator()
        
        self._enhancement_history: List[EnhancementResult] = []
    
    async def enhance_problem_analysis(
        self,
        problem_description: str,
        problem_type: str = "optimization"
    ) -> EnhancementResult:
        """增强问题分析"""
        if not self.problem_enhancer:
            return None
        
        result = await self.problem_enhancer.enhance(problem_description, problem_type)
        self._enhancement_history.append(result)
        return result
    
    async def enhance_code(self, code: str) -> EnhancementResult:
        """增强代码质量"""
        if not self.code_enhancer:
            return None
        
        result = await self.code_enhancer.enhance(code)
        self._enhancement_history.append(result)
        return result
    
    async def enhance_paper(
        self,
        paper_content: str,
        task_id: str = "unknown",
        **kwargs
    ) -> EnhancementResult:
        """增强论文质量"""
        if not self.paper_enhancer:
            return None
        
        result = await self.paper_enhancer.enhance(paper_content, task_id, **kwargs)
        self._enhancement_history.append(result)
        return result
    
    def get_all_suggestions(self) -> List[str]:
        """获取所有改进建议"""
        suggestions = []
        for result in self._enhancement_history:
            suggestions.extend(result.suggestions)
        suggestions.extend(self.coordinator.get_optimization_suggestions())
        return list(set(suggestions))  # 去重
    
    def get_enhancement_summary(self) -> Dict[str, Any]:
        """获取增强总结"""
        return {
            "total_enhancements": len(self._enhancement_history),
            "by_type": {
                t.value: len([r for r in self._enhancement_history if r.enhancement_type == t])
                for t in EnhancementType
            },
            "total_improvements": sum(len(r.improvements) for r in self._enhancement_history),
            "total_suggestions": sum(len(r.suggestions) for r in self._enhancement_history),
            "workflow_status": self.coordinator.get_workflow_status()
        }


# 便捷函数
def create_workflow_enhancer(
    memory_manager: Optional["MemoryManager"] = None
) -> WorkflowEnhancer:
    """创建工作流增强器"""
    return WorkflowEnhancer(memory_manager)
