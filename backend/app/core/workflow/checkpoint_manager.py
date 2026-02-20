"""
工作流检查点管理器 - 负责工作流级别的断点保存与恢复

在工作流的关键节点自动保存检查点，支持从中断点恢复执行。
检查点数据包含完整的工作流上下文（Problem、Agent 配置、阶段产物等），
确保恢复后能正确重建上下文并继续后续阶段。

与底层 CheckpointManager（checkpoints.py）的关系：
- CheckpointManager: 通用的检查点 CRUD（Redis/文件持久化）
- WorkflowCheckpointManager: 面向业务的高层封装，负责序列化工作流上下文

使用示例：
    >>> manager = get_workflow_checkpoint_manager()
    >>> await manager.save_workflow_checkpoint(
    ...     task_id="task-123",
    ...     stage_name="model",
    ...     problem_data=problem.model_dump(),
    ...     agent_configs=configs,
    ...     workflow_mode="standard",
    ...     completed_phases=["coordinate", "setup", "eda"],
    ...     phase_outputs={"coordinate": {...}, "eda": "..."},
    ...     questions={"ques1": "...", "ques_count": 2},
    ...     ques_count=2,
    ... )
    >>> data = await manager.load_workflow_checkpoint("task-123")
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.workflow.checkpoints import (
    CheckpointManager,
    CheckpointStatus,
    get_checkpoint_manager,
)
from app.utils.log_util import logger


# 标准工作流阶段序列（有序，用于确定恢复起点和进度计算）
STANDARD_WORKFLOW_STAGES: list[str] = [
    "coordinate",     # 协调者分析问题
    "setup",          # 环境设置
    "data_preview",   # 数据预览（可选）
    "eda",            # 数据探索分析
    "model",          # 建模方案设计
    "solve",          # 代码求解
    "validate",       # 模型验证（可选）
    "sensitivity",    # 敏感性分析（可选）
    "model_comparison",  # 多模型对比分析（可选）
    "write",          # 论文写作
    "review",         # 质量评审（可选）
    "revise",         # 论文修订（可选）
    "finalize",       # 完成
]

TOTAL_STANDARD_STAGES: int = len(STANDARD_WORKFLOW_STAGES)


class WorkflowCheckpointManager:
    """
    工作流级别的检查点管理器

    封装底层 CheckpointManager，提供面向工作流的高层接口。
    负责将工作流上下文序列化为可持久化的检查点数据，
    并在恢复时提供重建工作流上下文所需的全部信息。
    """

    def __init__(self) -> None:
        self._manager: CheckpointManager = get_checkpoint_manager()

    async def save_workflow_checkpoint(
        self,
        task_id: str,
        stage_name: str,
        problem_data: dict,
        agent_configs: Optional[dict],
        workflow_mode: str,
        completed_phases: List[str],
        phase_outputs: Dict[str, Any],
        questions: Dict[str, Any],
        ques_count: int,
        user_output_res: Optional[Dict[str, dict]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        在工作流关键节点保存检查点

        每次调用会覆盖同一 task_id 的前一个检查点（保留最新状态）。
        同时追加到历史记录列表中，支持查看阶段进展轨迹。

        Args:
            task_id: 任务ID
            stage_name: 当前完成的阶段名称（如 "coordinate", "model" 等）
            problem_data: 序列化后的 Problem 数据（Problem.model_dump()）
            agent_configs: 用户级 Agent API 配置（多租户隔离）
            workflow_mode: 工作流模式（"standard" / "enhanced" / "auto"）
            completed_phases: 已完成的阶段名称列表
            phase_outputs: 各阶段的序列化输出（可 JSON 化的字典）
            questions: 问题字典（来自 Coordinator 的分解结果）
            ques_count: 问题数量
            user_output_res: UserOutput 的结果字典（论文各章节内容）
            metadata: 额外元数据

        Returns:
            是否保存成功
        """
        stage_index = self._get_stage_index(stage_name)

        # 构建完整的上下文快照
        context_snapshot: Dict[str, Any] = {
            "problem_data": problem_data,
            "agent_configs": self._sanitize_configs(agent_configs),
            "workflow_mode": workflow_mode,
            "completed_phases": completed_phases,
            "phase_outputs": phase_outputs,
            "questions": questions,
            "ques_count": ques_count,
            "user_output_res": user_output_res or {},
            "saved_at": datetime.now().isoformat(),
        }

        checkpoint = self._manager.create_checkpoint(
            task_id=task_id,
            stage_name=stage_name,
            stage_index=stage_index,
            total_stages=TOTAL_STANDARD_STAGES,
            context_snapshot=context_snapshot,
            metadata=metadata or {"workflow_type": "standard"},
        )
        checkpoint.status = CheckpointStatus.COMPLETED

        success = await self._manager.save(checkpoint)
        if success:
            logger.info(
                "工作流检查点已保存: task=%s, stage=%s (%s/%s), 已完成阶段数=%s",
                task_id,
                stage_name,
                stage_index + 1,
                TOTAL_STANDARD_STAGES,
                len(completed_phases),
            )
        return success

    async def load_workflow_checkpoint(
        self, task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        加载工作流检查点，返回可用于恢复的上下文数据

        Args:
            task_id: 任务ID

        Returns:
            检查点上下文数据字典，包含恢复所需的所有信息；
            如果不存在或不可恢复则返回 None
        """
        checkpoint = await self._manager.load(task_id)
        if not checkpoint:
            logger.warning("未找到任务 %s 的检查点", task_id)
            return None

        if not checkpoint.is_resumable:
            logger.warning("任务 %s 的检查点不可恢复（状态: %s）", task_id, checkpoint.status.value)
            return None

        context = checkpoint.context_snapshot
        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "task_id": checkpoint.task_id,
            "stage_name": checkpoint.stage_name,
            "stage_index": checkpoint.stage_index,
            "total_stages": checkpoint.total_stages,
            "status": checkpoint.status.value,
            # 工作流恢复所需的核心数据
            "problem_data": context.get("problem_data", {}),
            "agent_configs": context.get("agent_configs"),
            "workflow_mode": context.get("workflow_mode", "standard"),
            "completed_phases": context.get("completed_phases", []),
            "phase_outputs": context.get("phase_outputs", {}),
            "questions": context.get("questions", {}),
            "ques_count": context.get("ques_count", 0),
            "user_output_res": context.get("user_output_res", {}),
            # 时间元数据
            "created_at": checkpoint.created_at,
            "updated_at": checkpoint.updated_at,
            "progress_percent": checkpoint.progress_percent,
        }

    async def list_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        """
        列出指定任务的所有检查点历史

        从 Redis 的检查点历史列表中读取，按保存时间排列。

        Args:
            task_id: 任务ID

        Returns:
            检查点摘要列表
        """
        history_key = f"checkpoint_history:{task_id}"
        try:
            from app.services.redis_manager import redis_manager

            client = await redis_manager.get_client()
            raw_list = await client.lrange(history_key, 0, -1)

            checkpoints: List[Dict[str, Any]] = []
            for raw in raw_list:
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    checkpoints.append({
                        "checkpoint_id": data.get("checkpoint_id"),
                        "stage_name": data.get("stage_name"),
                        "stage_index": data.get("stage_index"),
                        "status": data.get("status"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                    })
                except (json.JSONDecodeError, TypeError):
                    continue
            return checkpoints
        except Exception as e:
            logger.warning("获取检查点历史失败: %s", e)
            return []

    async def mark_resuming(self, task_id: str) -> bool:
        """
        标记检查点为恢复中状态

        Args:
            task_id: 任务ID

        Returns:
            是否标记成功
        """
        return await self._manager.update_status(
            task_id, CheckpointStatus.IN_PROGRESS
        )

    async def mark_completed(self, task_id: str) -> bool:
        """
        标记检查点为已完成状态（工作流恢复执行完毕后调用）

        Args:
            task_id: 任务ID

        Returns:
            是否标记成功
        """
        return await self._manager.update_status(
            task_id, CheckpointStatus.COMPLETED
        )

    def get_resume_stage(self, completed_phases: List[str]) -> Optional[str]:
        """
        根据已完成的阶段列表，确定恢复的起始阶段

        遍历标准阶段序列，找到第一个未完成的阶段。
        注意：setup 阶段始终需要重新执行（创建 Agent 和 Interpreter），
        因此不会被视为"可跳过"的已完成阶段。

        Args:
            completed_phases: 已完成的阶段名称列表

        Returns:
            应该从哪个阶段开始恢复；如果所有阶段都完成则返回 None
        """
        completed_set = set(completed_phases)
        for stage in STANDARD_WORKFLOW_STAGES:
            # setup 阶段始终需要重新执行
            if stage == "setup":
                continue
            if stage not in completed_set:
                return stage
        return None

    @staticmethod
    def _sanitize_configs(configs: Optional[dict]) -> Optional[dict]:
        """
        清理 Agent 配置中的敏感信息（API Key 脱敏处理）

        保留配置结构但对 API Key 进行部分遮蔽，
        恢复时需要从 UserConfigService 重新获取完整配置。

        Args:
            configs: 原始 Agent 配置字典

        Returns:
            脱敏后的配置字典
        """
        if not configs:
            return configs

        sanitized = {}
        for agent_type, cfg in configs.items():
            sanitized[agent_type] = dict(cfg) if isinstance(cfg, dict) else cfg
            if isinstance(sanitized[agent_type], dict) and "api_key" in sanitized[agent_type]:
                key = sanitized[agent_type]["api_key"]
                if key and len(key) > 8:
                    # 只保留前4位和后4位，中间用 * 遮蔽
                    sanitized[agent_type]["api_key"] = (
                        key[:4] + "****" + key[-4:]
                    )
        return sanitized

    def _get_stage_index(self, stage_name: str) -> int:
        """获取阶段在标准序列中的索引"""
        try:
            return STANDARD_WORKFLOW_STAGES.index(stage_name)
        except ValueError:
            logger.warning("未知阶段名称: %s，使用索引 0", stage_name)
            return 0


# ============= 全局单例 =============

_workflow_checkpoint_manager: Optional[WorkflowCheckpointManager] = None


def get_workflow_checkpoint_manager() -> WorkflowCheckpointManager:
    """获取全局工作流检查点管理器单例"""
    global _workflow_checkpoint_manager
    if _workflow_checkpoint_manager is None:
        _workflow_checkpoint_manager = WorkflowCheckpointManager()
    return _workflow_checkpoint_manager
