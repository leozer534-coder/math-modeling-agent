"""
Pipeline + Stage 统一工作流架构

设计目标:
  将三套独立工作流 (Standard / Enhanced / Award) 统一为可组合的 Pipeline。
  不同模式通过不同的 Stage 组合配置来区分，而非三套独立实现。

核心组件:
  - Stage (Protocol): 可复用执行单元的接口协议
  - PipelineContext: 跨阶段共享的可变状态容器
  - StageConfig: 单个阶段的运行时配置（是否可选、超时、进度区间等）
  - WorkflowPipeline: 按配置组装 Stage 并顺序执行的引擎
"""

import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from app.schemas.request import Problem
from app.schemas.response import ProgressMessage, SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


# ==================== Stage 接口协议 ====================


@runtime_checkable
class Stage(Protocol):
    """阶段接口协议 (Protocol)

    所有 Stage 实现类必须满足此结构化子类型约束:
    - name: 阶段标识符（英文小写，用于日志和产物键）
    - execute(ctx): 异步执行方法，通过读写 PipelineContext 传递数据
    """

    @property
    def name(self) -> str:
        """阶段唯一标识符"""
        ...

    async def execute(self, ctx: "PipelineContext") -> None:
        """执行阶段逻辑

        Args:
            ctx: 管线上下文，阶段从中读取输入、写入输出
        """
        ...


# ==================== 阶段配置 ====================


@dataclass
class StageConfig:
    """单个阶段的运行时配置

    Attributes:
        stage_class: Stage 实现类
        optional: 是否为可选阶段（失败时跳过而非中断管线）
        progress_start: 进度起始百分比 (0-100)
        progress_end: 进度结束百分比 (0-100)
        timeout: 超时秒数（0 表示不限制）
        kwargs: 传递给 Stage 构造函数的额外参数
    """

    stage_class: type
    optional: bool = False
    progress_start: float = 0.0
    progress_end: float = 100.0
    timeout: float = 0.0
    kwargs: dict = field(default_factory=dict)


# ==================== 阶段执行结果 ====================


@dataclass
class StageResult:
    """阶段执行结果"""

    name: str
    success: bool
    duration: float = 0.0
    error: Optional[str] = None
    skipped: bool = False


# ==================== 管线上下文 ====================


@dataclass
class PipelineContext:
    """管线上下文 - 所有阶段共享的可变状态容器

    设计原则:
    - 使用具名属性存储核心数据（类型安全）
    - 使用 artifacts 字典存储阶段特有的中间产物（灵活扩展）
    - 包含进度发送等公用工具方法，避免各 Stage 重复实现
    """

    # ---- 基础信息 ----
    task_id: str = ""
    work_dir: str = ""
    problem: Optional[Problem] = None

    # ---- LLM 相关 ----
    llm_factory: Any = None
    llms: dict[str, Any] = field(default_factory=dict)

    # ---- Agent 实例 ----
    agents: dict[str, Any] = field(default_factory=dict)

    # ---- 代码执行 ----
    code_interpreter: Any = None

    # ---- 协调者输出 ----
    coordinator_response: Any = None
    questions: dict[str, Any] = field(default_factory=dict)
    ques_count: int = 0

    # ---- 建模输出 ----
    modeler_response: Any = None

    # ---- 解题结果 ----
    solution_results: dict[str, Any] = field(default_factory=dict)

    # ---- 论文输出 ----
    user_output: Any = None

    # ---- 阶段产物存储（任意 Stage 可以存取） ----
    artifacts: dict[str, Any] = field(default_factory=dict)

    # ---- 进度追踪 ----
    start_time: float = field(default_factory=time.time)
    current_stage_name: str = ""

    # ---- 用户级 API 配置（多租户隔离） ----
    agent_configs: dict | None = None

    # ---- 工作流模式标识 ----
    workflow_mode: str = "standard"

    async def send_progress(self, message: str, percent: float) -> None:
        """向前端发送进度消息

        Args:
            message: 进度描述文本
            percent: 进度百分比 (0-100)
        """
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content=message, type="info"),
        )
        try:
            await redis_manager.publish_message(
                self.task_id,
                ProgressMessage(
                    percent=percent,
                    phase=self.current_stage_name,
                    message=message,
                    elapsed_time=time.time() - self.start_time,
                ),
            )
        except Exception as e:
            logger.debug("进度消息发送失败（不影响主流程）: %s", e)

    def elapsed_minutes(self) -> float:
        """获取已用时间（分钟）"""
        return (time.time() - self.start_time) / 60.0


# ==================== 工作流管线引擎 ====================


class WorkflowPipeline:
    """统一工作流管线引擎

    使用方式:
        pipeline = WorkflowPipeline(
            stage_configs=[...],
            agent_configs=user_agent_configs,
            workflow_mode="standard",
        )
        await pipeline.execute(problem)
    """

    def __init__(
        self,
        stage_configs: list[StageConfig],
        agent_configs: dict | None = None,
        workflow_mode: str = "standard",
    ):
        self.stage_configs = stage_configs
        self._agent_configs = agent_configs
        self._workflow_mode = workflow_mode
        self.ctx: Optional[PipelineContext] = None
        self.results: list[StageResult] = []
        # 恢复模式相关状态
        self._skip_stages: set[str] = set()
        self._resume_data: dict[str, Any] | None = None

    def configure_resume(
        self,
        completed_stages: list[str],
        stage_outputs: dict[str, Any] | None = None,
        questions: dict[str, Any] | None = None,
        ques_count: int = 0,
        coordinator_response: Any = None,
        modeler_response: Any = None,
        user_output_res: dict[str, Any] | None = None,
    ) -> None:
        """配置恢复上下文，使 Pipeline 跳过已完成阶段

        在调用 execute() 之前调用此方法，Pipeline 将：
        1. 跳过 completed_stages 中列出的阶段（setup 除外，始终重新执行）
        2. 将检查点数据注入到 PipelineContext 中

        Args:
            completed_stages: 已完成的阶段名称列表
            stage_outputs: 各阶段的序列化输出（存入 artifacts）
            questions: 问题字典（来自 Coordinator 的分解结果）
            ques_count: 问题数量
            coordinator_response: 协调者的原始响应
            modeler_response: 建模者的原始响应
            user_output_res: UserOutput 的结果字典（论文各章节内容）
        """
        # setup 阶段始终需要重新执行（创建 Agent 和 Interpreter）
        self._skip_stages = {s for s in completed_stages if s != "setup"}
        self._resume_data = {
            "stage_outputs": stage_outputs or {},
            "questions": questions or {},
            "ques_count": ques_count,
            "coordinator_response": coordinator_response,
            "modeler_response": modeler_response,
            "user_output_res": user_output_res or {},
        }
        logger.info(
            "Pipeline 恢复模式已配置: 跳过阶段=%s, ques_count=%s",
            self._skip_stages,
            ques_count,
        )

    def _apply_resume_data(self) -> None:
        """将恢复数据注入到 PipelineContext 中

        在 execute() 初始化上下文后调用，将检查点中保存的
        中间产物恢复到 ctx 对应字段，使后续阶段可以正常读取。
        """
        if self._resume_data is None or self.ctx is None:
            return

        data = self._resume_data

        # 恢复 Coordinator 阶段产物
        if data.get("questions"):
            self.ctx.questions = data["questions"]
        if data.get("ques_count"):
            self.ctx.ques_count = data["ques_count"]
        if data.get("coordinator_response"):
            self.ctx.coordinator_response = data["coordinator_response"]

        # 恢复 Modeler 阶段产物
        if data.get("modeler_response"):
            self.ctx.modeler_response = data["modeler_response"]

        # 恢复各阶段的中间产物到 artifacts
        stage_outputs = data.get("stage_outputs", {})
        for key, value in stage_outputs.items():
            self.ctx.artifacts[key] = value

        # 恢复 UserOutput 章节内容（将在 SetupStage 创建 UserOutput 后注入）
        if data.get("user_output_res"):
            self.ctx.artifacts["_resume_user_output_res"] = data["user_output_res"]

        logger.info("已将检查点数据注入到 PipelineContext")

    async def _save_checkpoint_after_stage(self, stage_name: str) -> None:
        """在阶段成功完成后自动保存检查点

        Args:
            stage_name: 刚完成的阶段名称
        """
        if self.ctx is None:
            return

        try:
            from app.core.workflow.checkpoint_manager import (
                get_workflow_checkpoint_manager,
            )

            cp_manager = get_workflow_checkpoint_manager()

            # 收集已完成的阶段名称
            completed = [r.name for r in self.results if r.success]

            # 收集可序列化的阶段输出
            phase_outputs: dict[str, Any] = {}
            for key, value in self.ctx.artifacts.items():
                # 跳过内部恢复标记和不可序列化对象
                if key.startswith("_"):
                    continue
                try:
                    import json
                    json.dumps(value)
                    phase_outputs[key] = value
                except (TypeError, ValueError):
                    phase_outputs[key] = str(value)[:500]

            # 收集 UserOutput 结果
            user_output_res: dict[str, dict] = {}
            if self.ctx.user_output and hasattr(self.ctx.user_output, "res"):
                for section_key, section_val in self.ctx.user_output.res.items():
                    if hasattr(section_val, "model_dump"):
                        user_output_res[section_key] = section_val.model_dump()
                    elif isinstance(section_val, dict):
                        user_output_res[section_key] = section_val

            # 序列化 Problem
            problem_data = {}
            if self.ctx.problem:
                problem_data = self.ctx.problem.model_dump()

            # 序列化 questions（确保可 JSON 化）
            questions: dict[str, Any] = {}
            if self.ctx.questions:
                for qk, qv in self.ctx.questions.items():
                    try:
                        import json
                        json.dumps(qv)
                        questions[qk] = qv
                    except (TypeError, ValueError):
                        questions[qk] = str(qv)

            await cp_manager.save_workflow_checkpoint(
                task_id=self.ctx.task_id,
                stage_name=stage_name,
                problem_data=problem_data,
                agent_configs=self.ctx.agent_configs,
                workflow_mode=self._workflow_mode,
                completed_phases=completed,
                phase_outputs=phase_outputs,
                questions=questions,
                ques_count=self.ctx.ques_count,
                user_output_res=user_output_res,
            )
        except Exception as e:
            # 检查点保存失败不应中断主流程
            logger.warning("检查点保存失败（不影响主流程）: %s", e)

    async def execute(self, problem: Problem) -> None:
        """执行完整的工作流管线

        支持正常执行和恢复执行两种模式：
        - 正常模式：顺序执行所有阶段
        - 恢复模式：跳过已完成阶段，从中断点继续

        Args:
            problem: 问题定义

        Raises:
            Exception: 必选阶段执行失败时抛出
        """
        from app.utils.common_utils import create_work_dir

        is_resume = bool(self._skip_stages)

        # 初始化上下文
        self.ctx = PipelineContext(
            task_id=problem.task_id,
            work_dir=create_work_dir(problem.task_id),
            problem=problem,
            agent_configs=self._agent_configs,
            workflow_mode=self._workflow_mode,
        )
        self.results = []

        # 恢复模式：注入检查点数据到上下文
        if is_resume:
            self._apply_resume_data()

        try:
            # 逐阶段执行
            for config in self.stage_configs:
                # 预检查：是否需要跳过该阶段
                stage_instance = config.stage_class(**config.kwargs)
                stage_name = stage_instance.name

                if stage_name in self._skip_stages:
                    logger.info("跳过已完成阶段: %s", stage_name)
                    self.results.append(StageResult(
                        name=stage_name,
                        success=True,
                        duration=0.0,
                        skipped=True,
                    ))
                    continue

                result = await self._execute_stage(config)
                self.results.append(result)

                # 必选阶段失败时中断管线
                if not result.success and not config.optional and not result.skipped:
                    raise RuntimeError(
                        f"必选阶段 [{result.name}] 执行失败: {result.error}"
                    )

                # 阶段成功完成后自动保存检查点
                if result.success and not result.skipped:
                    await self._save_checkpoint_after_stage(stage_name)

            # 管线完成
            mode_label = "恢复" if is_resume else ""
            await self.ctx.send_progress("任务完成", 100)
            await redis_manager.publish_message(
                self.ctx.task_id,
                SystemMessage(
                    content=(
                        f"{mode_label}任务完成! "
                        f"总用时: {self.ctx.elapsed_minutes():.1f}分钟"
                    ),
                    type="success",
                ),
            )

            # 标记检查点为已完成
            if is_resume:
                try:
                    from app.core.workflow.checkpoint_manager import (
                        get_workflow_checkpoint_manager,
                    )
                    await get_workflow_checkpoint_manager().mark_completed(
                        self.ctx.task_id
                    )
                except Exception as e:
                    logger.warning("标记检查点完成失败: %s", e)

        except Exception as e:
            logger.error("工作流管线执行失败: %s\n%s", e, traceback.format_exc())
            await redis_manager.publish_message(
                self.ctx.task_id,
                SystemMessage(
                    content=f"任务执行失败: {str(e)[:200]}",
                    type="error",
                ),
            )
            raise

        finally:
            await self._cleanup()

    async def _execute_stage(self, config: StageConfig) -> StageResult:
        """执行单个阶段（含超时保护和可选阶段容错）

        Args:
            config: 阶段配置

        Returns:
            StageResult 执行结果
        """
        import asyncio

        # 实例化 Stage
        stage = config.stage_class(**config.kwargs)
        stage_name = stage.name
        self.ctx.current_stage_name = stage_name

        start_time = time.time()
        logger.info("开始执行阶段: %s (optional=%s)", stage_name, config.optional)

        # 发送阶段开始进度
        await self.ctx.send_progress(
            f"正在执行: {stage_name}...", config.progress_start
        )

        try:
            if config.timeout > 0:
                await asyncio.wait_for(
                    stage.execute(self.ctx),
                    timeout=config.timeout,
                )
            else:
                await stage.execute(self.ctx)

            duration = time.time() - start_time
            logger.info("阶段 %s 完成，耗时: %.2f秒", stage_name, duration)

            return StageResult(
                name=stage_name,
                success=True,
                duration=duration,
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            error_msg = f"阶段 {stage_name} 超时 ({config.timeout}s)"
            logger.error(error_msg)

            if config.optional:
                logger.warning("可选阶段 %s 超时，已跳过", stage_name)
                return StageResult(
                    name=stage_name,
                    success=False,
                    duration=duration,
                    error=error_msg,
                    skipped=True,
                )
            return StageResult(
                name=stage_name,
                success=False,
                duration=duration,
                error=error_msg,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error("阶段 %s 失败: %s", stage_name, error_msg)

            if config.optional:
                logger.warning("可选阶段 %s 失败，已跳过: %s", stage_name, error_msg)
                return StageResult(
                    name=stage_name,
                    success=False,
                    duration=duration,
                    error=error_msg,
                    skipped=True,
                )
            return StageResult(
                name=stage_name,
                success=False,
                duration=duration,
                error=error_msg,
            )

    async def _cleanup(self) -> None:
        """清理管线资源（代码解释器等）"""
        if self.ctx is None:
            return

        try:
            if self.ctx.code_interpreter is not None:
                await self.ctx.code_interpreter.cleanup()
                self.ctx.code_interpreter = None
        except Exception as e:
            logger.warning("清理代码解释器失败: %s", e)

    def get_execution_stats(self) -> dict[str, Any]:
        """获取执行统计信息"""
        stats: dict[str, Any] = {
            "total_time": (
                time.time() - self.ctx.start_time if self.ctx else 0.0
            ),
            "workflow_mode": self._workflow_mode,
            "stages": {},
        }
        for result in self.results:
            stats["stages"][result.name] = {
                "success": result.success,
                "duration": result.duration,
                "skipped": result.skipped,
                "error": result.error,
            }
        return stats

    # ==================== 工厂方法 ====================

    @staticmethod
    def create(
        workflow_mode: str,
        agent_configs: dict | None = None,
        **kwargs,
    ) -> "WorkflowPipeline":
        """根据工作流模式创建管线实例

        Args:
            workflow_mode: 工作流模式 (standard / enhanced / award)
            agent_configs: 用户级 API 配置
            **kwargs: 传递给特定模式配置的额外参数

        Returns:
            配置好的 WorkflowPipeline 实例
        """
        from app.core.workflow.configs import get_pipeline_config

        stage_configs = get_pipeline_config(workflow_mode, **kwargs)

        return WorkflowPipeline(
            stage_configs=stage_configs,
            agent_configs=agent_configs,
            workflow_mode=workflow_mode,
        )
