"""
任务恢复测试 - Test Task Recovery

测试范围:
  1. 检查点数据的创建、序列化、反序列化
  2. WorkflowPipeline 恢复模式（configure_resume + 阶段跳过）
  3. WorkflowCheckpointManager 业务逻辑
  4. modeling_router 中的恢复 API 端点
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ==================== 检查点基础功能测试 ====================


class TestCheckpointBasics:
    """检查点基础数据结构测试"""

    def test_checkpoint_manager_import(self):
        """测试检查点管理器导入"""
        from app.core.workflow.checkpoints import (
            Checkpoint,
            CheckpointManager,
            CheckpointStatus,
        )

        assert CheckpointManager is not None
        assert Checkpoint is not None
        assert CheckpointStatus is not None

    def test_get_checkpoint_manager_singleton(self):
        """测试全局检查点管理器单例"""
        from app.core.workflow.checkpoints import get_checkpoint_manager

        manager1 = get_checkpoint_manager()
        manager2 = get_checkpoint_manager()

        assert manager1 is manager2

    def test_checkpoint_status_enum(self):
        """测试检查点状态枚举"""
        from app.core.workflow.checkpoints import CheckpointStatus

        assert CheckpointStatus.CREATED.value == "created"
        assert CheckpointStatus.IN_PROGRESS.value == "in_progress"
        assert CheckpointStatus.COMPLETED.value == "completed"
        assert CheckpointStatus.FAILED.value == "failed"

    def test_create_checkpoint(self):
        """测试创建检查点"""
        from app.core.workflow.checkpoints import CheckpointManager

        manager = CheckpointManager(use_redis=False)

        checkpoint = manager.create_checkpoint(
            task_id="test-task-123",
            stage_name="solve",
            stage_index=3,
            total_stages=7,
            context_snapshot={"test": "data"},
        )

        assert checkpoint.task_id == "test-task-123"
        assert checkpoint.stage_name == "solve"
        assert checkpoint.stage_index == 3
        assert checkpoint.total_stages == 7

    def test_checkpoint_progress_percent(self):
        """测试检查点进度百分比"""
        from app.core.workflow.checkpoints import Checkpoint, CheckpointStatus

        checkpoint = Checkpoint(
            checkpoint_id="test-123",
            task_id="task-123",
            stage_name="test",
            stage_index=3,
            total_stages=10,
            status=CheckpointStatus.IN_PROGRESS,
        )

        assert checkpoint.progress_percent == 30.0

    def test_checkpoint_progress_zero_stages(self):
        """测试零阶段时的进度百分比"""
        from app.core.workflow.checkpoints import Checkpoint, CheckpointStatus

        checkpoint = Checkpoint(
            checkpoint_id="test",
            task_id="task",
            stage_name="test",
            stage_index=0,
            total_stages=0,
            status=CheckpointStatus.CREATED,
        )

        assert checkpoint.progress_percent == 0

    def test_checkpoint_is_resumable(self):
        """测试检查点可恢复性"""
        from app.core.workflow.checkpoints import Checkpoint, CheckpointStatus

        # 进行中的检查点应该可恢复
        checkpoint = Checkpoint(
            checkpoint_id="test",
            task_id="task",
            stage_name="test",
            stage_index=1,
            total_stages=5,
            status=CheckpointStatus.IN_PROGRESS,
            expires_at=(datetime.now() + timedelta(hours=24)).isoformat(),
        )

        assert checkpoint.is_resumable is True

        # 已完成的检查点不可恢复
        checkpoint.status = CheckpointStatus.COMPLETED
        assert checkpoint.is_resumable is False

        # 已过期的检查点不可恢复
        checkpoint.status = CheckpointStatus.IN_PROGRESS
        checkpoint.expires_at = (
            datetime.now() - timedelta(hours=1)
        ).isoformat()
        assert checkpoint.is_resumable is False

    def test_checkpoint_serialization(self):
        """测试检查点序列化与反序列化"""
        from app.core.workflow.checkpoints import Checkpoint, CheckpointStatus

        checkpoint = Checkpoint(
            checkpoint_id="test-123",
            task_id="task-123",
            stage_name="model",
            stage_index=2,
            total_stages=5,
            status=CheckpointStatus.CREATED,
            context_snapshot={"questions": {"ques1": "test"}},
        )

        # 转换为字典
        data = checkpoint.to_dict()

        assert data["checkpoint_id"] == "test-123"
        assert data["status"] == "created"
        assert data["context_snapshot"]["questions"]["ques1"] == "test"

        # 从字典恢复
        restored = Checkpoint.from_dict(data)

        assert restored.checkpoint_id == checkpoint.checkpoint_id
        assert restored.status == checkpoint.status
        assert restored.stage_name == "model"

    def test_checkpoint_file_save_and_load(self, tmp_path):
        """测试检查点文件保存和加载"""
        from app.core.workflow.checkpoints import CheckpointManager

        manager = CheckpointManager(
            storage_dir=str(tmp_path),
            use_redis=False,
        )

        checkpoint = manager.create_checkpoint(
            task_id="file-test-task",
            stage_name="eda",
            stage_index=2,
            total_stages=8,
            context_snapshot={"key": "value"},
        )

        # 保存到文件
        saved = manager._save_to_file(checkpoint)
        assert saved is True

        # 从文件加载
        loaded = manager._load_from_file("file-test-task")
        assert loaded is not None
        assert loaded.task_id == "file-test-task"
        assert loaded.stage_name == "eda"

    def test_checkpoint_file_load_nonexistent(self, tmp_path):
        """测试加载不存在的检查点文件"""
        from app.core.workflow.checkpoints import CheckpointManager

        manager = CheckpointManager(
            storage_dir=str(tmp_path),
            use_redis=False,
        )

        loaded = manager._load_from_file("nonexistent-task")
        assert loaded is None


# ==================== WorkflowCheckpointManager 测试 ====================


class TestWorkflowCheckpointManager:
    """工作流检查点管理器测试"""

    def test_get_resume_stage_basic(self):
        """测试确定恢复起始阶段 - 基础场景"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        manager = WorkflowCheckpointManager()

        # 只完成了 coordinate，应从 data_preview 开始恢复
        # （setup 始终需要重新执行，不视为可跳过）
        result = manager.get_resume_stage(["coordinate", "setup"])
        assert result == "data_preview"

    def test_get_resume_stage_mid_workflow(self):
        """测试确定恢复起始阶段 - 工作流中间中断"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        manager = WorkflowCheckpointManager()

        # 完成到 model 阶段，应从 solve 开始恢复
        completed = ["coordinate", "setup", "data_preview", "eda", "model"]
        result = manager.get_resume_stage(completed)
        assert result == "solve"

    def test_get_resume_stage_all_completed(self):
        """测试所有阶段都完成时返回 None"""
        from app.core.workflow.checkpoint_manager import (
            STANDARD_WORKFLOW_STAGES,
            WorkflowCheckpointManager,
        )

        manager = WorkflowCheckpointManager()

        result = manager.get_resume_stage(STANDARD_WORKFLOW_STAGES)
        assert result is None

    def test_get_resume_stage_empty(self):
        """测试没有完成任何阶段"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        manager = WorkflowCheckpointManager()

        result = manager.get_resume_stage([])
        assert result == "coordinate"

    def test_sanitize_configs(self):
        """测试 API Key 脱敏"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        configs = {
            "coordinator": {
                "api_key": "sk-1234567890abcdef",
                "model": "deepseek-chat",
            },
            "coder": {
                "api_key": "short",
                "model": "gpt-4",
            },
        }

        sanitized = WorkflowCheckpointManager._sanitize_configs(configs)

        # 长 Key 应被部分遮蔽
        assert sanitized["coordinator"]["api_key"] == "sk-1****cdef"
        # 短 Key 不变
        assert sanitized["coder"]["api_key"] == "short"
        # 非敏感字段保持原样
        assert sanitized["coordinator"]["model"] == "deepseek-chat"

    def test_sanitize_configs_none(self):
        """测试 None 配置不报错"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        assert WorkflowCheckpointManager._sanitize_configs(None) is None

    def test_get_stage_index_known(self):
        """测试已知阶段名的索引"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        manager = WorkflowCheckpointManager()

        assert manager._get_stage_index("coordinate") == 0
        assert manager._get_stage_index("model") == 4
        assert manager._get_stage_index("write") == 9

    def test_get_stage_index_unknown(self):
        """测试未知阶段名返回 0"""
        from app.core.workflow.checkpoint_manager import (
            WorkflowCheckpointManager,
        )

        manager = WorkflowCheckpointManager()

        assert manager._get_stage_index("unknown_stage") == 0


# ==================== Pipeline 恢复模式测试 ====================


class TestPipelineResume:
    """WorkflowPipeline 恢复模式测试"""

    def test_configure_resume_sets_skip_stages(self):
        """测试 configure_resume 正确设置跳过阶段"""
        from app.core.workflow.pipeline import (
            WorkflowPipeline,
        )

        pipeline = WorkflowPipeline(
            stage_configs=[],
            workflow_mode="standard",
        )

        pipeline.configure_resume(
            completed_stages=["coordinate", "setup", "eda"],
            questions={"ques1": "test"},
            ques_count=1,
        )

        # setup 应被排除在跳过列表之外
        assert "setup" not in pipeline._skip_stages
        assert "coordinate" in pipeline._skip_stages
        assert "eda" in pipeline._skip_stages

    def test_configure_resume_preserves_data(self):
        """测试 configure_resume 正确保存恢复数据"""
        from app.core.workflow.pipeline import (
            WorkflowPipeline,
        )

        pipeline = WorkflowPipeline(
            stage_configs=[],
            workflow_mode="standard",
        )

        pipeline.configure_resume(
            completed_stages=["coordinate"],
            stage_outputs={"eda_result": "some data"},
            questions={"ques1": "Q1", "ques_count": 2},
            ques_count=2,
            user_output_res={"firstPage": {"content": "test"}},
        )

        assert pipeline._resume_data is not None
        assert pipeline._resume_data["ques_count"] == 2
        assert pipeline._resume_data["questions"]["ques1"] == "Q1"
        assert pipeline._resume_data["stage_outputs"]["eda_result"] == "some data"

    def test_apply_resume_data_injects_context(self):
        """测试 _apply_resume_data 正确注入上下文"""
        from app.core.workflow.pipeline import (
            PipelineContext,
            WorkflowPipeline,
        )

        pipeline = WorkflowPipeline(
            stage_configs=[],
            workflow_mode="standard",
        )

        # 模拟已配置恢复
        pipeline._resume_data = {
            "questions": {"ques1": "Q1", "ques2": "Q2"},
            "ques_count": 2,
            "coordinator_response": "coordinator output",
            "modeler_response": "modeler output",
            "stage_outputs": {"eda_result": "eda data"},
            "user_output_res": {"firstPage": {"content": "page1"}},
        }

        pipeline.ctx = PipelineContext(task_id="test-task")

        pipeline._apply_resume_data()

        # 验证注入结果
        assert pipeline.ctx.questions == {"ques1": "Q1", "ques2": "Q2"}
        assert pipeline.ctx.ques_count == 2
        assert pipeline.ctx.coordinator_response == "coordinator output"
        assert pipeline.ctx.modeler_response == "modeler output"
        assert pipeline.ctx.artifacts["eda_result"] == "eda data"
        assert pipeline.ctx.artifacts["_resume_user_output_res"] == {
            "firstPage": {"content": "page1"}
        }

    @pytest.mark.asyncio
    async def test_execute_skips_completed_stages(self):
        """测试 Pipeline 执行时跳过已完成阶段"""
        from app.core.workflow.pipeline import (
            StageConfig,
            WorkflowPipeline,
        )

        # 创建 Mock Stage 类
        executed_stages = []

        class MockStageA:
            @property
            def name(self):
                return "stage_a"

            async def execute(self, ctx):
                executed_stages.append("stage_a")

        class MockStageB:
            @property
            def name(self):
                return "stage_b"

            async def execute(self, ctx):
                executed_stages.append("stage_b")

        class MockStageC:
            @property
            def name(self):
                return "stage_c"

            async def execute(self, ctx):
                executed_stages.append("stage_c")

        pipeline = WorkflowPipeline(
            stage_configs=[
                StageConfig(stage_class=MockStageA, progress_start=0, progress_end=30),
                StageConfig(stage_class=MockStageB, progress_start=30, progress_end=60),
                StageConfig(stage_class=MockStageC, progress_start=60, progress_end=100),
            ],
            workflow_mode="standard",
        )

        # 配置恢复：跳过 stage_a
        pipeline._skip_stages = {"stage_a"}
        pipeline._resume_data = {
            "questions": {},
            "ques_count": 0,
            "coordinator_response": None,
            "modeler_response": None,
            "stage_outputs": {},
            "user_output_res": {},
        }

        # Mock 掉外部依赖
        mock_problem = MagicMock()
        mock_problem.task_id = "test-resume-task"

        with patch(
            "app.core.workflow.pipeline.redis_manager"
        ) as mock_redis, patch(
            "app.utils.common_utils.create_work_dir",
            return_value="/tmp/test",
        ), patch(
            "app.core.workflow.pipeline.WorkflowPipeline._save_checkpoint_after_stage",
            new_callable=AsyncMock,
        ):
            mock_redis.publish_message = AsyncMock()

            await pipeline.execute(mock_problem)

        # stage_a 应被跳过，stage_b 和 stage_c 应被执行
        assert "stage_a" not in executed_stages
        assert "stage_b" in executed_stages
        assert "stage_c" in executed_stages

        # 检查结果
        assert len(pipeline.results) == 3
        # stage_a 被标记为 skipped
        assert pipeline.results[0].name == "stage_a"
        assert pipeline.results[0].skipped is True
        assert pipeline.results[0].success is True

    @pytest.mark.asyncio
    async def test_execute_saves_checkpoints(self):
        """测试 Pipeline 正常执行时自动保存检查点"""
        from app.core.workflow.pipeline import (
            StageConfig,
            WorkflowPipeline,
        )

        class MockStage:
            @property
            def name(self):
                return "test_stage"

            async def execute(self, ctx):
                pass

        pipeline = WorkflowPipeline(
            stage_configs=[
                StageConfig(
                    stage_class=MockStage,
                    progress_start=0,
                    progress_end=100,
                ),
            ],
            workflow_mode="standard",
        )

        mock_problem = MagicMock()
        mock_problem.task_id = "checkpoint-test"

        save_calls = []

        async def mock_save(stage_name):
            save_calls.append(stage_name)

        with patch(
            "app.core.workflow.pipeline.redis_manager"
        ) as mock_redis, patch(
            "app.utils.common_utils.create_work_dir",
            return_value="/tmp/test",
        ), patch.object(
            WorkflowPipeline,
            "_save_checkpoint_after_stage",
            side_effect=mock_save,
        ):
            mock_redis.publish_message = AsyncMock()

            await pipeline.execute(mock_problem)

        # 应在 test_stage 完成后保存检查点
        assert "test_stage" in save_calls


# ==================== 端到端集成测试 ====================


class TestResumeEndToEnd:
    """恢复流程端到端集成测试（Mock 外部依赖）"""

    @pytest.mark.asyncio
    async def test_full_resume_pipeline_flow(self):
        """测试完整的恢复流程: 检查点加载 -> Pipeline 配置 -> 执行"""
        from app.core.workflow.pipeline import (
            StageConfig,
            WorkflowPipeline,
        )

        # 模拟 3 个阶段，第 1 个已完成
        executed = []

        class StageA:
            @property
            def name(self):
                return "stage_a"

            async def execute(self, ctx):
                executed.append("a")

        class StageB:
            @property
            def name(self):
                return "stage_b"

            async def execute(self, ctx):
                executed.append("b")
                ctx.artifacts["b_result"] = "done"

        class StageC:
            @property
            def name(self):
                return "stage_c"

            async def execute(self, ctx):
                executed.append("c")

        pipeline = WorkflowPipeline(
            stage_configs=[
                StageConfig(stage_class=StageA, progress_start=0, progress_end=30),
                StageConfig(stage_class=StageB, progress_start=30, progress_end=70),
                StageConfig(stage_class=StageC, progress_start=70, progress_end=100),
            ],
            workflow_mode="standard",
        )

        # 配置恢复：stage_a 已完成
        pipeline.configure_resume(
            completed_stages=["stage_a"],
            stage_outputs={},
            questions={"ques1": "test question"},
            ques_count=1,
        )

        mock_problem = MagicMock()
        mock_problem.task_id = "e2e-resume-test"

        with patch(
            "app.core.workflow.pipeline.redis_manager"
        ) as mock_redis, patch(
            "app.utils.common_utils.create_work_dir",
            return_value="/tmp/test",
        ), patch(
            "app.core.workflow.pipeline.WorkflowPipeline"
            "._save_checkpoint_after_stage",
            new_callable=AsyncMock,
        ):
            mock_redis.publish_message = AsyncMock()

            await pipeline.execute(mock_problem)

        # 验证: stage_a 被跳过，stage_b 和 stage_c 被执行
        assert executed == ["b", "c"]

        # 验证上下文数据被正确注入
        assert pipeline.ctx.questions == {"ques1": "test question"}
        assert pipeline.ctx.ques_count == 1

        # 验证 stage_b 的 artifacts 被正确写入
        assert pipeline.ctx.artifacts["b_result"] == "done"
