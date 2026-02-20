"""
数学建模工作流核心模块

包含:
- WorkflowPhase: 工作流阶段枚举
- PhaseResult: 阶段执行结果
- WorkflowState: 工作流状态管理
- MathModelWorkFlow: 主工作流类
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.config.setting import settings
from app.core.agents import CoderAgent, CoordinatorAgent, ModelerAgent, WriterAgent
from app.core.flows import Flows
from app.core.llm.llm_factory import LLMFactory
from app.models.user_output import UserOutput
from app.schemas.A2A import (
    CoordinatorToModeler,
    ModelComparisonEntry,
    ModelComparisonResult,
    ModelerToCoder,
)
from app.schemas.request import Problem
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.common_utils import create_work_dir, get_config_template
from app.utils.log_util import logger


class WorkflowPhase(str, Enum):
    """工作流阶段枚举"""

    INIT = "init"
    COORDINATE = "coordinate"
    SETUP = "setup"
    DATA_PREVIEW = "data_preview"
    EDA = "eda"
    MODEL = "model"
    SOLVE = "solve"
    VALIDATE = "validate"
    SENSITIVITY = "sensitivity"
    MODEL_COMPARISON = "model_comparison"
    WRITE = "write"
    REVIEW = "review"
    REVISE = "revise"
    FINALIZE = "finalize"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseResult:
    """阶段执行结果"""

    success: bool = False
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class WorkflowState:
    """工作流状态管理"""

    task_id: str = ""
    current_phase: WorkflowPhase = WorkflowPhase.INIT
    phases_completed: list[str] = field(default_factory=list)
    phase_results: dict[str, PhaseResult] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    progress: int = 0
    progress_message: str = ""

    def update_progress(self, message: str, percent: int) -> None:
        """更新进度信息"""
        self.progress = percent
        self.progress_message = message

    def get_elapsed_time(self) -> float:
        """获取已经过的时间（秒）"""
        return time.time() - self.start_time

    def complete_phase(self, phase: str, result: PhaseResult) -> None:
        """标记阶段完成"""
        self.phases_completed.append(phase)
        self.phase_results[phase] = result


class MathModelWorkFlow:
    """数学建模主工作流

    协调 Coordinator -> Modeler -> Coder -> Writer 四阶段流水线，
    支持并行求解、反馈环路、质量评审等特性。
    """

    task_id: str
    work_dir: str
    ques_count: int = 0

    def __init__(self, agent_configs: dict | None = None):
        self.state: Optional[WorkflowState] = None
        self._code_interpreter = None
        self._agents: dict[str, Any] = {}
        self._llms: dict[str, Any] = {}
        self._user_output: Optional[UserOutput] = None
        self._problem: Optional[Problem] = None
        self._agent_configs = agent_configs
        self.questions: dict[str, str | int] = {}

    # ================================================================
    # 检查点（Checkpoint）— 断点续跑支持
    # ================================================================

    def _checkpoint_path(self) -> str:
        """检查点文件路径"""
        return os.path.join(self.work_dir, "checkpoint.json")

    def _save_checkpoint(self, stage: str, data: dict) -> None:
        """保存检查点到磁盘。

        Args:
            stage: 当前完成的阶段名称（coordinator / modeler）
            data: 需要持久化的数据字典
        """
        cp_path = self._checkpoint_path()
        # 读取已有检查点（追加模式）
        existing: dict = {}
        if os.path.exists(cp_path):
            try:
                with open(cp_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing[stage] = data
        with open(cp_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info("检查点已保存: stage=%s, path=%s", stage, cp_path)

    def _load_checkpoint(self) -> dict | None:
        """加载检查点。存在则返回字典，否则返回 None。"""
        cp_path = self._checkpoint_path()
        if not os.path.exists(cp_path):
            return None
        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("检查点已加载: stages=%s", list(data.keys()))
            return data
        except Exception as e:
            logger.warning("检查点加载失败，将重新执行: %s", e)
            return None

    def _clear_checkpoint(self) -> None:
        """任务完成后清除检查点文件。"""
        cp_path = self._checkpoint_path()
        if os.path.exists(cp_path):
            os.remove(cp_path)
            logger.info("检查点已清除: %s", cp_path)

    async def execute(self, problem: Problem):
        """执行数学建模工作流（支持断点续跑）"""
        self.task_id = problem.task_id
        self.work_dir = create_work_dir(self.task_id)
        self._problem = problem

        self.state = WorkflowState(task_id=self.task_id)

        llm_factory = LLMFactory(
            self.task_id, agent_configs=self._agent_configs
        )
        coordinator_llm, modeler_llm, coder_llm, writer_llm = (
            llm_factory.get_all_llms()
        )

        # ===== 检查点恢复 =====
        checkpoint = self._load_checkpoint()
        coordinator_response = None
        modeler_response = None

        if checkpoint and "coordinator" in checkpoint:
            try:
                coordinator_response = CoordinatorToModeler.model_validate(
                    checkpoint["coordinator"]
                )
                self.questions = coordinator_response.questions
                self.ques_count = coordinator_response.ques_count
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="[检查点恢复] 问题拆解结果已从缓存加载"),
                )
                logger.info("从检查点恢复 coordinator_response")
            except Exception as e:
                logger.warning("检查点 coordinator 恢复失败，将重新执行: %s", e)
                coordinator_response = None

        if checkpoint and "modeler" in checkpoint and coordinator_response is not None:
            try:
                modeler_response = ModelerToCoder.model_validate(
                    checkpoint["modeler"]
                )
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="[检查点恢复] 建模方案已从缓存加载"),
                )
                logger.info("从检查点恢复 modeler_response")
            except Exception as e:
                logger.warning("检查点 modeler 恢复失败，将重新执行: %s", e)
                modeler_response = None

        # ===== Coordinator 阶段 =====
        if coordinator_response is None:
            coordinator_agent = CoordinatorAgent(self.task_id, coordinator_llm)

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="识别用户意图和拆解问题ing..."),
            )

            try:
                coordinator_response = await coordinator_agent.run(problem.ques_all)
                self.questions = coordinator_response.questions
                self.ques_count = coordinator_response.ques_count
            except Exception as e:
                logger.error("CoordinatorAgent 执行失败: %s", e)
                raise

            # 保存检查点
            self._save_checkpoint(
                "coordinator", coordinator_response.model_dump()
            )

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="识别用户意图和拆解问题完成,任务转交给建模手"),
            )

        # ===== Modeler 阶段 =====
        if modeler_response is None:
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="建模手开始建模ing..."),
            )

            modeler_agent = ModelerAgent(self.task_id, modeler_llm)
            modeler_response = await modeler_agent.run(coordinator_response)

            # 保存检查点
            self._save_checkpoint(
                "modeler", modeler_response.model_dump()
            )

        self._user_output = UserOutput(
            work_dir=self.work_dir,
            ques_count=self.ques_count,
            comp_template=problem.comp_template,
        )

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="正在创建代码沙盒环境"),
        )

        notebook_serializer = NotebookSerializer(work_dir=self.work_dir)
        self._code_interpreter = await create_interpreter(
            kind="local",
            task_id=self.task_id,
            work_dir=self.work_dir,
            notebook_serializer=notebook_serializer,
            timeout=3000,
        )

        scholar = OpenAlexScholar(
            task_id=self.task_id, email=settings.OPENALEX_EMAIL
        )

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="创建完成"),
        )

        coder_agent = CoderAgent(
            task_id=problem.task_id,
            model=coder_llm,
            work_dir=self.work_dir,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            code_interpreter=self._code_interpreter,
        )

        writer_agent = WriterAgent(
            task_id=problem.task_id,
            model=writer_llm,
            comp_template=problem.comp_template,
            format_output=problem.format_output,
            scholar=scholar,
        )

        self._agents = {
            "coordinator": coordinator_agent,
            "modeler": modeler_agent,
            "coder": coder_agent,
            "writer": writer_agent,
        }

        flows = Flows(self.questions)

        try:
            # ===== 求解阶段 =====
            solution_flows = flows.get_solution_flows(self.questions, modeler_response)
            config_template = get_config_template(problem.comp_template, problem.format_output)

            for key, value in solution_flows.items():
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"代码手开始求解{key}"),
                )

                coder_response = await coder_agent.run(
                    prompt=value["coder_prompt"], subtask_title=key
                )

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"代码手求解成功{key}", type="success"),
                )

                writer_prompt = flows.get_writer_prompt(
                    key,
                    coder_response.code_response,
                    self._code_interpreter,
                    config_template,
                )

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"论文手开始写{key}部分"),
                )

                writer_response = await writer_agent.run(
                    writer_prompt,
                    available_images=coder_response.created_images,
                    sub_title=key,
                )

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"论文手完成{key}部分"),
                )

                self._user_output.set_res(key, writer_response)

            logger.info(self._user_output.get_res())

            # ===== 写作阶段 =====
            write_flows = flows.get_write_flows(
                self._user_output,
                config_template,
                problem.ques_all,
                comp_template=problem.comp_template,
            )
            for key, value in write_flows.items():
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"论文手开始写{key}部分"),
                )

                writer_response = await writer_agent.run(prompt=value, sub_title=key)
                self._user_output.set_res(key, writer_response)

            logger.info(self._user_output.get_res())
            self._user_output.save_result()

            # 任务成功完成，清除检查点
            self._clear_checkpoint()
        finally:
            # ===== 关闭沙盒（确保异常时也能清理 Jupyter 内核） =====
            if self._code_interpreter is not None:
                await self._code_interpreter.cleanup()

    # ================================================================
    # 多模型对比分析 — 静态辅助方法
    # ================================================================

    @staticmethod
    def _extract_multi_model_results(
        code_output: str | None,
    ) -> list[dict[str, Any]]:
        """从代码输出中解析多模型结果

        支持两种格式:
        1. 'Model: <name>' 或 '模型: <name>' 行分隔
        2. '=== <name> ===' 分块分隔

        Args:
            code_output: Coder 的文本输出

        Returns:
            list[dict]: 每个元素包含 {"name": ..., "metrics": {...}}
        """
        if not code_output:
            return []

        models: list[dict[str, Any]] = []

        # 模式 1: === ModelName ===
        separator_blocks = re.split(r"===\s*(.+?)\s*===", code_output)
        if len(separator_blocks) >= 3:
            # separator_blocks: ['前文', 'ModelName1', '指标块1', 'ModelName2', '指标块2', ...]
            for i in range(1, len(separator_blocks), 2):
                name = separator_blocks[i].strip()
                metrics_text = separator_blocks[i + 1] if i + 1 < len(separator_blocks) else ""
                metrics = Flows.extract_metrics_from_code_output(metrics_text)
                if name:
                    models.append({"name": name, "metrics": metrics})
            return models

        # 模式 2: Model: name 或 模型: name
        model_pattern = re.compile(
            r"(?:Model|模型)\s*[:：]\s*(.+)", re.IGNORECASE
        )
        lines = code_output.split("\n")
        current_model: str | None = None
        current_block: list[str] = []

        for line in lines:
            match = model_pattern.match(line.strip())
            if match:
                # 保存上一个模型块
                if current_model is not None:
                    block_text = "\n".join(current_block)
                    metrics = Flows.extract_metrics_from_code_output(block_text)
                    models.append({"name": current_model, "metrics": metrics})
                current_model = match.group(1).strip()
                current_block = []
            elif current_model is not None:
                current_block.append(line)

        # 保存最后一个模型块
        if current_model is not None:
            block_text = "\n".join(current_block)
            metrics = Flows.extract_metrics_from_code_output(block_text)
            models.append({"name": current_model, "metrics": metrics})

        return models

    @staticmethod
    def _generate_comparison_table(
        metrics_dict: dict[str, dict[str, float]],
        question_key: str,
    ) -> str:
        """生成 Markdown 对比表格

        Args:
            metrics_dict: {模型名: {指标名: 数值}}
            question_key: 问题键名（如 "ques1"）

        Returns:
            str: Markdown 格式的对比表格
        """
        if not metrics_dict:
            return ""

        # 收集所有指标名称
        all_metrics: list[str] = []
        for model_metrics in metrics_dict.values():
            for metric_name in model_metrics:
                if metric_name not in all_metrics:
                    all_metrics.append(metric_name)

        if not all_metrics:
            return ""

        # 构建表头
        header = "| 模型 | " + " | ".join(all_metrics) + " |"
        separator = "|---" + "|---" * len(all_metrics) + "|"

        # 构建数据行
        rows: list[str] = []
        for model_name, model_metrics in metrics_dict.items():
            cells = []
            for metric in all_metrics:
                value = model_metrics.get(metric)
                if value is not None:
                    cells.append(f"{value:.4f}")
                else:
                    cells.append("-")
            row = f"| {model_name} | " + " | ".join(cells) + " |"
            rows.append(row)

        return "\n".join([header, separator, *rows])

    @staticmethod
    def _compute_baseline_improvement(
        metrics_dict: dict[str, dict[str, float]],
    ) -> dict[str, float] | None:
        """计算改进幅度（最后一个模型相对于第一个模型）

        Args:
            metrics_dict: {模型名: {指标名: 数值}}

        Returns:
            dict[str, float] | None: 各指标的改进幅度（相对值），
                                     如果只有一个模型或为空则返回 None
        """
        if not metrics_dict or len(metrics_dict) < 2:
            return None

        model_names = list(metrics_dict.keys())
        baseline_name = model_names[0]
        improved_name = model_names[-1]

        baseline_metrics = metrics_dict[baseline_name]
        improved_metrics = metrics_dict[improved_name]

        # 计算共有指标的改进幅度
        improvement: dict[str, float] = {}
        for metric_name in baseline_metrics:
            if metric_name in improved_metrics:
                baseline_val = baseline_metrics[metric_name]
                improved_val = improved_metrics[metric_name]
                if abs(baseline_val) > 1e-10:
                    improvement[metric_name] = (
                        (improved_val - baseline_val) / baseline_val
                    )
                else:
                    # 基线为 0 时使用绝对差值
                    improvement[metric_name] = improved_val - baseline_val

        return improvement if improvement else None

    @staticmethod
    def _determine_best_model(
        metrics_dict: dict[str, dict[str, float]],
    ) -> str | None:
        """根据指标确定最优模型

        优先级: R² > Accuracy > F1 > AUC > -RMSE > -MAE > -MSE

        Args:
            metrics_dict: {模型名: {指标名: 数值}}

        Returns:
            str | None: 最优模型名称
        """
        if not metrics_dict:
            return None

        # 越大越好的指标
        higher_better = ("R²", "Accuracy", "F1", "AUC", "Precision", "Recall", "Silhouette")
        # 越小越好的指标（取负值比较）
        lower_better = ("RMSE", "MAE", "MSE", "MAPE")

        best_model: str | None = None
        best_score: float = float("-inf")

        for model_name, model_metrics in metrics_dict.items():
            score = 0.0
            has_metric = False

            # 优先使用越大越好的指标
            for metric in higher_better:
                if metric in model_metrics:
                    score = model_metrics[metric]
                    has_metric = True
                    break

            # 没有越大越好的指标时，使用越小越好的指标（取负值）
            if not has_metric:
                for metric in lower_better:
                    if metric in model_metrics:
                        score = -model_metrics[metric]
                        has_metric = True
                        break

            if has_metric and score > best_score:
                best_score = score
                best_model = model_name

        return best_model

    @staticmethod
    def _compute_overall_ranking(
        model_scores: dict[str, list[float]],
    ) -> list[str] | None:
        """计算全局模型排名（按平均得分降序）

        Args:
            model_scores: {模型名: [各问题得分]}

        Returns:
            list[str] | None: 按平均得分降序排列的模型名列表
        """
        if not model_scores:
            return None

        avg_scores = {
            name: sum(scores) / len(scores)
            for name, scores in model_scores.items()
            if scores
        }

        if not avg_scores:
            return None

        ranking = sorted(avg_scores.keys(), key=lambda n: avg_scores[n], reverse=True)
        return ranking

    @staticmethod
    def _generate_comparison_summary(
        per_question: list[ModelComparisonEntry],
        overall_ranking: list[str] | None,
    ) -> str:
        """生成对比总结文本

        Args:
            per_question: 各问题的对比结果
            overall_ranking: 全局排名

        Returns:
            str: 对比总结文本
        """
        if not per_question:
            return "未能提取到多模型对比数据。"

        # 收集所有评估过的模型
        all_models: set[str] = set()
        for entry in per_question:
            all_models.update(entry.models_evaluated)

        lines: list[str] = []
        lines.append(
            f"共对 {len(per_question)} 个问题进行了多模型对比分析，"
            f"涉及 {len(all_models)} 个模型：{', '.join(sorted(all_models))}。"
        )

        # 各问题最优模型
        for entry in per_question:
            if entry.best_model:
                lines.append(
                    f"- {entry.question_key}: 最优模型为 {entry.best_model}"
                )

        # 全局排名
        if overall_ranking:
            ranking_str = " > ".join(overall_ranking)
            lines.append(f"\n综合排名: {ranking_str}")

        return "\n".join(lines)

    @staticmethod
    def _format_comparison_for_writer(
        result: "ModelComparisonResult | None",
    ) -> str:
        """格式化对比数据为 Writer 可用文本

        Args:
            result: ModelComparisonResult 实例

        Returns:
            str: 格式化后的文本
        """
        if result is None:
            return ""

        lines: list[str] = ["## 多模型对比分析数据\n"]

        # 各问题对比
        for entry in result.per_question:
            lines.append(f"### {entry.question_key}")
            if entry.models_evaluated:
                lines.append(f"评估模型: {', '.join(entry.models_evaluated)}")
            if entry.best_model:
                lines.append(f"最优模型: {entry.best_model}")
            if entry.comparison_table_markdown:
                lines.append(f"\n{entry.comparison_table_markdown}\n")
            if entry.improvement_over_baseline:
                for metric, value in entry.improvement_over_baseline.items():
                    lines.append(f"- {metric} 改进幅度: {value:.2%}")
            lines.append("")

        # 全局排名
        if result.overall_ranking:
            ranking_str = " > ".join(result.overall_ranking)
            lines.append("### 综合模型排名")
            lines.append(ranking_str)

        # 总结
        if result.comparison_summary:
            lines.append("\n### 总结")
            lines.append(result.comparison_summary)

        return "\n".join(lines)
