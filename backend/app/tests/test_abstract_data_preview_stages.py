"""
AbstractStage._collect_abstract_context 和 DataPreviewStage 测试

覆盖:
  - AbstractStage._collect_abstract_context(): 上下文收集逻辑
  - AbstractStage._extract_keywords(): 关键词提取（补充已有纯函数测试）
  - AbstractStage.execute(): 完整执行流程（mock LLM）
  - DataPreviewStage.execute(): 数据文件扫描、摘要生成、截断、异常处理
"""

import sys
import os
import asyncio
from dataclasses import dataclass, field
from unittest.mock import MagicMock, AsyncMock, patch

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.HumanMessage = MagicMock
        _mock.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock

import pytest  # noqa: E402
import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402

from app.core.workflow.stages.abstract_stage import AbstractStage  # noqa: E402
from app.core.workflow.stages.data_preview_stage import DataPreviewStage  # noqa: E402
from app.core.workflow.stages.artifact_keys import ArtifactKeys  # noqa: E402
from app.core.workflow.stages.stage_constants import (  # noqa: E402
    DATA_PREVIEW_MAX_FILE_SIZE,
    DATA_SUMMARY_MAX_LENGTH,
)


# ================================================================
# 测试辅助: Mock PipelineContext
# ================================================================


class _MockPipelineContext:
    """轻量级 PipelineContext mock，仅包含测试所需属性"""

    def __init__(
        self,
        *,
        task_id: str = "test_task_001",
        work_dir: str = "",
        problem=None,
        coordinator_response=None,
        modeler_response=None,
        solution_results=None,
        user_output=None,
        artifacts=None,
        llms=None,
    ):
        self.task_id = task_id
        self.work_dir = work_dir
        self.problem = problem
        self.coordinator_response = coordinator_response
        self.modeler_response = modeler_response
        self.solution_results = solution_results or {}
        self.user_output = user_output
        self.artifacts = artifacts if artifacts is not None else {}
        self.llms = llms or {}
        self.send_progress = AsyncMock()


# ================================================================
# AbstractStage._collect_abstract_context 测试
# ================================================================


class TestCollectAbstractContext:
    """AbstractStage._collect_abstract_context 静态方法测试"""

    @pytest.mark.unit
    def test_empty_context(self):
        """验证: 空 ctx 返回空 problem_description"""
        ctx = _MockPipelineContext()
        result = AbstractStage._collect_abstract_context(ctx)
        assert result["problem_description"] == ""
        assert result["modeling_results"] == {}

    @pytest.mark.unit
    def test_problem_with_ques_all(self):
        """验证: problem.ques_all 优先用于问题描述"""
        problem = MagicMock()
        problem.ques_all = "这是一个线性规划问题，需要最大化利润..."
        ctx = _MockPipelineContext(problem=problem)
        result = AbstractStage._collect_abstract_context(ctx)
        assert result["problem_description"] == "这是一个线性规划问题，需要最大化利润..."

    @pytest.mark.unit
    def test_problem_without_ques_all_uses_str(self):
        """验证: problem 无 ques_all 时使用 str() 转换"""

        class _SimpleProblem:
            def __str__(self) -> str:
                return "优化问题描述"

        ctx = _MockPipelineContext(problem=_SimpleProblem())
        result = AbstractStage._collect_abstract_context(ctx)
        assert "优化问题描述" in result["problem_description"]

    @pytest.mark.unit
    def test_coordinator_response_fallback(self):
        """验证: 无 problem 时使用 coordinator_response"""
        ctx = _MockPipelineContext(
            coordinator_response="协调器分析了这个预测问题..."
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert "协调器分析了这个预测问题" in result["problem_description"]

    @pytest.mark.unit
    def test_coordinator_response_truncated_to_3000(self):
        """验证: coordinator_response 截断到 3000 字符"""
        long_text = "x" * 5000
        ctx = _MockPipelineContext(coordinator_response=long_text)
        result = AbstractStage._collect_abstract_context(ctx)
        assert len(result["problem_description"]) == 3000

    @pytest.mark.unit
    def test_modeler_response_with_dict(self):
        """验证: modeler_response 有 __dict__ 时使用其字符串化"""

        class _ModelerResponse:
            def __init__(self):
                self.model = "线性规划"
                self.approach = "单纯形法"

        ctx = _MockPipelineContext(modeler_response=_ModelerResponse())
        result = AbstractStage._collect_abstract_context(ctx)
        assert "modeler" in result["modeling_results"]

    @pytest.mark.unit
    def test_modeler_response_without_dict(self):
        """验证: modeler_response 无 __dict__ 时使用 str()"""
        ctx = _MockPipelineContext(modeler_response="线性规划方案")
        result = AbstractStage._collect_abstract_context(ctx)
        assert "modeler" in result["modeling_results"]
        assert "线性规划方案" in result["modeling_results"]["modeler"]

    @pytest.mark.unit
    def test_coordinator_in_modeling_results(self):
        """验证: coordinator_response 也写入 modeling_results"""
        ctx = _MockPipelineContext(
            coordinator_response="协调器输出",
            problem=MagicMock(ques_all="问题描述"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert "coordinator" in result["modeling_results"]

    @pytest.mark.unit
    def test_paper_sections_collected(self):
        """验证: user_output.res 中的论文章节被收集"""
        user_output = MagicMock()
        user_output.res = {"引言": "...", "模型建立": "...", "结论": "..."}
        ctx = _MockPipelineContext(
            user_output=user_output,
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        sections = result["modeling_results"].get("paper_sections", [])
        assert "引言" in sections
        assert "模型建立" in sections

    @pytest.mark.unit
    def test_solution_results_dict_values(self):
        """验证: solution_results 中的 dict 值被正确提取"""
        ctx = _MockPipelineContext(
            solution_results={
                "问题1": {
                    "success": True,
                    "code_output": "最优值 x=3.14",
                },
                "flows": ["stage1"],  # 应被跳过
            },
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        code_results = result.get("code_results", {})
        assert "问题1" in code_results
        assert code_results["问题1"]["success"] is True
        assert "flows" not in code_results

    @pytest.mark.unit
    def test_solution_results_non_dict_values(self):
        """验证: solution_results 中非 dict 值被字符串化"""
        ctx = _MockPipelineContext(
            solution_results={"问题1": "纯文本结果"},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        code_results = result.get("code_results", {})
        assert "问题1" in code_results
        assert "纯文本结果" in code_results["问题1"]

    @pytest.mark.unit
    def test_solution_results_config_template_skipped(self):
        """验证: config_template 键被跳过"""
        ctx = _MockPipelineContext(
            solution_results={"config_template": "template_data"},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        # config_template 被跳过，code_results 为空则不存在
        code_results = result.get("code_results", {})
        assert "config_template" not in code_results

    @pytest.mark.unit
    def test_validation_report_collected(self):
        """验证: artifacts 中的验证报告被收集"""
        ctx = _MockPipelineContext(
            artifacts={ArtifactKeys.VALIDATION_REPORT: {"status": "通过", "score": 0.95}},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert result.get("validation_results") == {"status": "通过", "score": 0.95}

    @pytest.mark.unit
    def test_innovation_points_list(self):
        """验证: 创新点为 list 时直接使用"""
        ctx = _MockPipelineContext(
            artifacts={ArtifactKeys.INNOVATIVE_MODEL_PLAN: ["创新1", "创新2"]},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert result["innovation_points"] == ["创新1", "创新2"]

    @pytest.mark.unit
    def test_innovation_points_string(self):
        """验证: 创新点为字符串时包装为列表"""
        ctx = _MockPipelineContext(
            artifacts={ArtifactKeys.INNOVATIVE_MODEL_PLAN: "混合模型创新"},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert result["innovation_points"] == ["混合模型创新"]

    @pytest.mark.unit
    def test_innovation_points_dataclass(self):
        """验证: 创新点为结构化对象时提取属性"""
        plan = MagicMock()
        plan.model_innovations = ["创新A"]
        plan.methodology_innovations = ["创新B"]
        plan.hybrid_approaches = ["创新C"]
        ctx = _MockPipelineContext(
            artifacts={ArtifactKeys.INNOVATIVE_MODEL_PLAN: plan},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert "创新A" in str(result["innovation_points"])
        assert len(result["innovation_points"]) == 3

    @pytest.mark.unit
    def test_innovation_points_fallback_to_str(self):
        """验证: 结构化对象无创新属性时兜底为字符串"""

        class _PlainPlan:
            def __str__(self) -> str:
                return "兜底创新描述"

        ctx = _MockPipelineContext(
            artifacts={ArtifactKeys.INNOVATIVE_MODEL_PLAN: _PlainPlan()},
            problem=MagicMock(ques_all="问题"),
        )
        result = AbstractStage._collect_abstract_context(ctx)
        assert len(result["innovation_points"]) == 1
        assert "兜底创新描述" in result["innovation_points"][0]

    @pytest.mark.unit
    def test_no_validation_no_innovation(self):
        """验证: 无验证报告和创新点时不包含对应键"""
        ctx = _MockPipelineContext(problem=MagicMock(ques_all="问题"))
        result = AbstractStage._collect_abstract_context(ctx)
        assert "validation_results" not in result
        assert "innovation_points" not in result


# ================================================================
# AbstractStage.execute 测试
# ================================================================


class TestAbstractStageExecute:
    """AbstractStage.execute 完整流程测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_skips_on_empty_problem(self):
        """验证: 无问题描述时跳过摘要生成"""
        stage = AbstractStage()
        ctx = _MockPipelineContext()
        await stage.execute(ctx)
        # 不应写入 abstract_content
        assert ArtifactKeys.ABSTRACT_CONTENT not in ctx.artifacts

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_exception_does_not_propagate(self):
        """验证: 异常不向上传播（可选阶段）"""
        stage = AbstractStage()
        ctx = _MockPipelineContext(
            problem=MagicMock(ques_all="问题描述"),
            llms={"writer": MagicMock()},
        )
        # AbstractGenerator 构造会失败（mock LLM 不完整），但不应抛异常
        await stage.execute(ctx)
        # 应发送跳过进度
        ctx.send_progress.assert_called()

    @pytest.mark.unit
    def test_stage_name(self):
        """验证: Stage 名称正确"""
        stage = AbstractStage()
        assert stage.name == "abstract_generation"


# ================================================================
# DataPreviewStage 测试
# ================================================================


class TestDataPreviewStageName:
    """DataPreviewStage 基础属性测试"""

    @pytest.mark.unit
    def test_stage_name(self):
        """验证: Stage 名称正确"""
        stage = DataPreviewStage()
        assert stage.name == "data_preview"


class TestDataPreviewStageExecute:
    """DataPreviewStage.execute 测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_data_files(self, tmp_path):
        """验证: 无数据文件时 data_summary 为空字符串"""
        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)
        assert ctx.artifacts[ArtifactKeys.DATA_SUMMARY] == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_csv_file_preview(self, tmp_path):
        """验证: CSV 文件被正确读取和预览"""
        # 创建测试 CSV
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4.0, 5.0, 6.0]})
        csv_path = tmp_path / "test_data.csv"
        df.to_csv(csv_path, index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "test_data.csv" in summary
        assert "行数: 3" in summary
        assert "列数: 2" in summary
        assert "x" in summary
        assert "y" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tsv_file_preview(self, tmp_path):
        """验证: TSV 文件被正确读取"""
        df = pd.DataFrame({"a": [10, 20], "b": ["foo", "bar"]})
        tsv_path = tmp_path / "data.tsv"
        df.to_csv(tsv_path, sep="\t", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "data.tsv" in summary
        assert "行数: 2" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_xlsx_file_preview(self, tmp_path):
        """验证: XLSX 文件被正确读取"""
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        xlsx_path = tmp_path / "data.xlsx"
        df.to_excel(xlsx_path, index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "data.xlsx" in summary
        assert "col1" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_files(self, tmp_path):
        """验证: 多个数据文件都被预览"""
        df1 = pd.DataFrame({"x": [1]})
        df2 = pd.DataFrame({"y": [2]})
        df1.to_csv(tmp_path / "file1.csv", index=False)
        df2.to_csv(tmp_path / "file2.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "file1.csv" in summary
        assert "file2.csv" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_data_files_ignored(self, tmp_path):
        """验证: 非数据文件（.txt, .py 等）被忽略"""
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "script.py").write_text("print(1)")
        df = pd.DataFrame({"x": [1]})
        df.to_csv(tmp_path / "data.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "data.csv" in summary
        assert "readme.txt" not in summary
        assert "script.py" not in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_values_reported(self, tmp_path):
        """验证: 缺失值被正确统计"""
        df = pd.DataFrame({"x": [1.0, np.nan, 3.0], "y": [np.nan, np.nan, 6.0]})
        df.to_csv(tmp_path / "missing.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "缺失值统计" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_missing_values(self, tmp_path):
        """验证: 无缺失值时显示'无'"""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        df.to_csv(tmp_path / "clean.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "缺失值: 无" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_numeric_statistics_included(self, tmp_path):
        """验证: 数值列基础统计被包含"""
        df = pd.DataFrame({"x": range(100), "y": np.random.randn(100)})
        df.to_csv(tmp_path / "stats.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "数值列基础统计" in summary
        assert "mean" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_head_preview_included(self, tmp_path):
        """验证: 前5行预览被包含"""
        df = pd.DataFrame({"col": range(10)})
        df.to_csv(tmp_path / "head.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "前5行预览" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unreadable_directory(self):
        """验证: 不可读工作目录不崩溃"""
        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir="/nonexistent/path/xyz_999")
        await stage.execute(ctx)
        assert ctx.artifacts[ArtifactKeys.DATA_SUMMARY] == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_corrupted_file_handled(self, tmp_path):
        """验证: 损坏文件不崩溃，写入失败信息"""
        # 使用 .xlsx 扩展名 + 非法内容，确保 pandas 无法解析
        (tmp_path / "bad.xlsx").write_bytes(b"\x00\x01\x02\x03")

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "bad.xlsx" in summary
        assert "读取失败" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summary_truncation(self, tmp_path):
        """验证: 摘要超过最大长度时被截断"""
        # 创建包含大量列的数据文件以生成超长摘要
        cols = {f"col_{i}": range(100) for i in range(200)}
        df = pd.DataFrame(cols)
        df.to_csv(tmp_path / "wide.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert len(summary) <= DATA_SUMMARY_MAX_LENGTH + 50  # +50 for truncation suffix

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_large_file_partial_read(self, tmp_path):
        """验证: 大文件仅读取前1000行（通过 mock file size）"""
        df = pd.DataFrame({"x": range(50)})
        csv_path = tmp_path / "large.csv"
        df.to_csv(csv_path, index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))

        # 模拟大文件场景
        original_getsize = os.path.getsize
        with patch("os.path.getsize", return_value=DATA_PREVIEW_MAX_FILE_SIZE + 1):
            await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "仅预览前1000行" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_small_file_full_read(self, tmp_path):
        """验证: 小文件读取完整数据"""
        df = pd.DataFrame({"x": range(10)})
        df.to_csv(tmp_path / "small.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "完整数据" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_progress_messages_sent(self, tmp_path):
        """验证: 进度消息被正确发送"""
        df = pd.DataFrame({"x": [1]})
        df.to_csv(tmp_path / "data.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        # 应至少发送两次进度: 开始 + 完成
        assert ctx.send_progress.call_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_insensitive_extensions(self, tmp_path):
        """验证: 扩展名大小写不敏感"""
        df = pd.DataFrame({"x": [1, 2]})
        csv_path = tmp_path / "DATA.CSV"
        df.to_csv(csv_path, index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "DATA.CSV" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_more_than_10_numeric_cols(self, tmp_path):
        """验证: 超过10个数值列时显示'前10列'提示"""
        cols = {f"num_{i}": np.random.randn(20) for i in range(15)}
        df = pd.DataFrame(cols)
        df.to_csv(tmp_path / "many_cols.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "前10列" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_types_listed(self, tmp_path):
        """验证: 每列数据类型被列出"""
        df = pd.DataFrame({
            "int_col": [1, 2],
            "float_col": [1.0, 2.0],
            "str_col": ["a", "b"],
        })
        df.to_csv(tmp_path / "types.csv", index=False)

        stage = DataPreviewStage()
        ctx = _MockPipelineContext(work_dir=str(tmp_path))
        await stage.execute(ctx)

        summary = ctx.artifacts[ArtifactKeys.DATA_SUMMARY]
        assert "数据类型" in summary
        assert "int_col" in summary
        assert "float_col" in summary
        assert "str_col" in summary
