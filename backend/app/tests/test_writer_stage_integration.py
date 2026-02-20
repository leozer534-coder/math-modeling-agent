"""
WriterStage 和 ImprovementLoopStage 集成测试

覆盖目标:
  - WriterStage.execute() 的各种 artifact 注入分支
  - ImprovementLoopStage.execute() 的各种早退和循环分支

重要: langchain_core mock 必须在任何 app.* 导入之前注入到 sys.modules，
否则 ImprovementLoopStage 模块顶层的 ``from langchain_core.messages import ...``
会因未安装 langchain_core 而触发 ImportError。
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ================== 关键: 在导入 app 模块前 mock langchain_core ==================
if "langchain_core" not in sys.modules:
    _mock_lc = MagicMock()
    sys.modules["langchain_core"] = _mock_lc
    sys.modules["langchain_core.messages"] = _mock_lc.messages

from app.core.workflow.stages.artifact_keys import ArtifactKeys  # noqa: E402
from app.core.workflow.stages.improvement_loop_stage import (  # noqa: E402
    ImprovementLoopStage,
)
from app.core.workflow.stages.stage_constants import (  # noqa: E402
    IMPROVEMENT_MAX_ITERATIONS,
)
from app.core.workflow.stages.writer_stage import WriterStage  # noqa: E402


# ================== 辅助: 构造 mock PipelineContext ==================


def _make_ctx(
    *,
    task_id: str = "test-task-001",
    workflow_mode: str = "standard",
    artifacts: dict | None = None,
    write_flows: dict | None = None,
    writer_responses=None,
    has_coder: bool = True,
    has_modeler_llm: bool = True,
):
    """构造最小化的 mock PipelineContext。

    所有外部依赖 (LLM / Redis / 文件系统) 均由 MagicMock 替代，
    测试可在无网络环境下运行。
    """
    ctx = MagicMock()
    ctx.task_id = task_id
    ctx.workflow_mode = workflow_mode
    ctx.artifacts = artifacts if artifacts is not None else {}
    ctx.send_progress = AsyncMock()
    ctx.ques_count = 2

    # problem
    ctx.problem = MagicMock()
    ctx.problem.ques_all = "问题1: 求解线性规划\n问题2: 灵敏度分析"

    # user_output
    ctx.user_output = MagicMock()
    ctx.user_output.res = {}
    ctx.user_output.set_res = MagicMock()
    ctx.user_output.get_result_to_save = MagicMock(return_value={})

    # solution_results (WriterStage 使用)
    if write_flows is None:
        write_flows = {"firstPage": "摘要提示", "RepeatQues": "重述提示"}

    mock_flows = MagicMock()
    # 每次调用都返回一个新的 dict 副本，防止多测试间交叉污染
    mock_flows.get_write_flows = MagicMock(return_value=dict(write_flows))
    ctx.solution_results = {
        "flows": mock_flows,
        "config_template": "default_template",
    }

    # writer agent
    writer_agent = MagicMock()
    if writer_responses is None:
        writer_agent.run = AsyncMock(return_value="写作结果内容")
    elif isinstance(writer_responses, list):
        writer_agent.run = AsyncMock(side_effect=writer_responses)
    else:
        writer_agent.run = AsyncMock(return_value=writer_responses)

    # coder agent
    coder_agent = MagicMock()
    coder_agent.run = AsyncMock(
        return_value=MagicMock(
            needs_remodel=False,
            code_response="改进代码执行成功",
        )
    )

    # agents 字典
    agents: dict = {"writer": writer_agent}
    if has_coder:
        agents["coder"] = coder_agent
    ctx.agents = agents

    # llms 字典 (ImprovementLoopStage._quick_validate 使用)
    llms: dict = {}
    if has_modeler_llm:
        mock_llm = AsyncMock()
        mock_llm_response = MagicMock()
        mock_llm_response.content = "通过"
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        llms["modeler"] = mock_llm
    ctx.llms = llms

    return ctx


# ==================== WriterStage 集成测试 ====================


class TestWriterStageExecute:
    """WriterStage.execute() 集成测试。"""

    @pytest.mark.asyncio
    async def test_basic_write_flow_no_artifacts(self):
        """验证: 无 artifact 注入时，基本写作流程正常完成，
        writer_agent.run() 按章节数调用。"""
        # Arrange
        write_flows = {
            "firstPage": "摘要提示",
            "RepeatQues": "重述提示",
            "judge": "评价提示",
        }
        ctx = _make_ctx(write_flows=write_flows)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        assert writer.run.call_count == 3
        assert ctx.user_output.set_res.call_count == 3
        # 至少发送了"正在撰写论文其他部分..."和"论文撰写完成"
        assert ctx.send_progress.call_count >= 2

    @pytest.mark.asyncio
    async def test_review_feedback_injection(self):
        """验证: 有评审反馈时，反馈内容被追加到每个写作 prompt。"""
        # Arrange
        write_flows = {"firstPage": "摘要提示"}
        artifacts = {
            ArtifactKeys.REVIEW_FEEDBACK: {
                "overall_rating": 3,
                "suggestions": ["增加数据分析深度", "完善模型假设"],
            }
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        call_kwargs = writer.run.call_args.kwargs
        prompt_text = call_kwargs["prompt"]
        assert "评审改进建议" in prompt_text
        assert "增加数据分析深度" in prompt_text
        assert "完善模型假设" in prompt_text

    @pytest.mark.asyncio
    async def test_symbol_table_injection(self):
        """验证: 有符号表且 write_flows 含 symbolExplain 时，符号定义被注入。"""
        # Arrange
        write_flows = {"symbolExplain": "符号说明提示", "firstPage": "摘要提示"}
        artifacts = {
            ArtifactKeys.SYMBOL_TABLE_TEXT: "x: 决策变量\ny: 目标函数值",
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert - 在 symbolExplain 章节的调用中检查注入内容
        writer = ctx.agents["writer"]
        found = False
        for call in writer.run.call_args_list:
            if call.kwargs.get("sub_title") == "symbolExplain":
                assert "符号定义参考" in call.kwargs["prompt"]
                assert "决策变量" in call.kwargs["prompt"]
                found = True
                break
        assert found, "未找到 symbolExplain 对应的 writer.run 调用"

    @pytest.mark.asyncio
    async def test_symbol_table_not_injected_without_key(self):
        """验证: 有符号表但 write_flows 不含 symbolExplain 时，不注入。"""
        # Arrange
        write_flows = {"firstPage": "摘要提示"}
        artifacts = {
            ArtifactKeys.SYMBOL_TABLE_TEXT: "x: 决策变量",
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert - firstPage 的 prompt 不应包含符号定义
        writer = ctx.agents["writer"]
        call_kwargs = writer.run.call_args.kwargs
        assert "符号定义参考" not in call_kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_sensitivity_analysis_injection_model_test(self):
        """验证: 有灵敏度分析结果时，优先注入到 modelTest 章节。"""
        # Arrange
        write_flows = {"modelTest": "模型检验提示", "firstPage": "摘要提示"}
        artifacts = {
            ArtifactKeys.SENSITIVITY_ANALYSIS: {
                "sensitive_parameters": [
                    {"name": "alpha", "description": "学习率"},
                ],
                "stability_assessment": "模型稳定",
                "recommendations": ["降低学习率"],
            },
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        for call in writer.run.call_args_list:
            if call.kwargs.get("sub_title") == "modelTest":
                assert "灵敏度分析结果" in call.kwargs["prompt"]
                assert "alpha" in call.kwargs["prompt"]
                break
        else:
            pytest.fail("未找到 modelTest 对应的 writer.run 调用")

    @pytest.mark.asyncio
    async def test_sensitivity_analysis_fallback_to_judge(self):
        """验证: 无 modelTest 时，灵敏度分析回退注入到 judge 章节。"""
        # Arrange - 没有 modelTest，也没有 analysisQues，只有 judge
        write_flows = {"judge": "评价提示", "firstPage": "摘要提示"}
        artifacts = {
            ArtifactKeys.SENSITIVITY_ANALYSIS: {
                "sensitive_parameters": [],
                "stability_assessment": "稳定",
            },
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        for call in writer.run.call_args_list:
            if call.kwargs.get("sub_title") == "judge":
                assert "灵敏度分析结果" in call.kwargs["prompt"]
                break
        else:
            pytest.fail("未找到 judge 对应的 writer.run 调用")

    @pytest.mark.asyncio
    async def test_code_metrics_injection(self):
        """验证: 有代码指标/图表/结论时，注入到 judge 和 firstPage 章节。"""
        # Arrange
        write_flows = {"judge": "评价提示", "firstPage": "摘要提示"}
        artifacts = {
            ArtifactKeys.CODE_METRICS: {
                "ques1": {"RMSE": 0.0123, "R2": 0.9876},
            },
            ArtifactKeys.CODE_FIGURES: {
                "ques1": [{"filename": "fig1.png", "description": "结果图"}],
            },
            ArtifactKeys.RESULT_SUMMARIES: {
                "ques1": [{"model": "线性回归", "conclusion": "拟合效果良好"}],
            },
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert - judge 章节包含求解结果汇总
        writer = ctx.agents["writer"]
        judge_found = False
        first_page_found = False
        for call in writer.run.call_args_list:
            kw = call.kwargs
            if kw.get("sub_title") == "judge":
                assert "求解结果汇总" in kw["prompt"]
                assert "RMSE" in kw["prompt"]
                judge_found = True
            elif kw.get("sub_title") == "firstPage":
                assert "关键结论" in kw["prompt"]
                assert "拟合效果良好" in kw["prompt"]
                first_page_found = True
        assert judge_found, "judge 章节未注入代码指标"
        assert first_page_found, "firstPage 章节未注入关键结论"

    @pytest.mark.asyncio
    async def test_validation_report_injection(self):
        """验证: 有验证报告时，注入到 modelTest 或 judge 章节。"""
        # Arrange
        write_flows = {"modelTest": "模型检验提示"}
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "summary": "模型通过交叉验证",
                "metrics": {"accuracy": 0.95, "f1": 0.92},
            },
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        call_kwargs = writer.run.call_args.kwargs
        assert "模型验证报告" in call_kwargs["prompt"]
        assert "模型通过交叉验证" in call_kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_chapter_write_failure_does_not_break_others(self):
        """验证: 单个章节写作失败不中断其他章节的写作。"""
        # Arrange - 第一个章节失败，后两个成功
        write_flows = {
            "firstPage": "摘要",
            "judge": "评价",
            "RepeatQues": "重述",
        }
        writer_responses = [
            Exception("LLM 调用超时"),
            "评价写作完成",
            "重述写作完成",
        ]
        ctx = _make_ctx(
            write_flows=write_flows, writer_responses=writer_responses
        )
        stage = WriterStage()

        # Act - 不应抛出异常
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        # 3 次调用：首次失败但不中断
        assert writer.run.call_count == 3
        # 成功的 2 个章节调用了 set_res
        assert ctx.user_output.set_res.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_reraises_on_critical_error(self):
        """验证: _do_execute 内部抛出异常时，execute() 应 re-raise。"""
        # Arrange - solution_results 缺少 flows 键导致 KeyError
        ctx = _make_ctx()
        ctx.solution_results = {}
        stage = WriterStage()

        # Act & Assert
        with pytest.raises(KeyError):
            await stage.execute(ctx)

    @pytest.mark.asyncio
    async def test_model_comparison_injection(self):
        """验证: 有 code_metrics 且 write_flows 含 model_comparison 时注入指标。"""
        # Arrange
        write_flows = {
            "model_comparison": "多模型对比提示",
            "firstPage": "摘要提示",
        }
        artifacts = {
            ArtifactKeys.CODE_METRICS: {
                "ques1": {"RMSE": 0.05, "MAE": 0.03},
            },
        }
        ctx = _make_ctx(write_flows=write_flows, artifacts=artifacts)
        stage = WriterStage()

        # Act
        await stage.execute(ctx)

        # Assert
        writer = ctx.agents["writer"]
        for call in writer.run.call_args_list:
            if call.kwargs.get("sub_title") == "model_comparison":
                assert "模型评估指标汇总" in call.kwargs["prompt"]
                break
        else:
            pytest.fail("未找到 model_comparison 对应的 writer.run 调用")


# ==================== ImprovementLoopStage 集成测试 ====================


class TestImprovementLoopStageExecute:
    """ImprovementLoopStage.execute() 集成测试。"""

    @pytest.mark.asyncio
    async def test_skip_when_no_validation_report(self):
        """验证: 无 validation_report 时直接跳过，不发送进度。"""
        # Arrange
        ctx = _make_ctx(artifacts={})
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert
        ctx.send_progress.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_when_validation_passed(self):
        """验证: validation_report 状态为"通过"时跳过。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "通过"},
                "improvement_recommendations": [
                    {"priority": "高", "recommendation": "无需改进"}
                ],
            }
        }
        ctx = _make_ctx(artifacts=artifacts)
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert - 直接 return，不发送进度
        ctx.send_progress.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_when_no_recommendations(self):
        """验证: 验证未通过但无改进建议时跳过。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [],
            }
        }
        ctx = _make_ctx(artifacts=artifacts)
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert - 发送了"检测到验证未通过..."后就 return
        assert ctx.send_progress.call_count == 1
        first_msg = ctx.send_progress.call_args_list[0].args[0]
        assert "验证未通过" in first_msg

    @pytest.mark.asyncio
    async def test_skip_when_no_coder_agent(self):
        """验证: 无 CoderAgent 时跳过改进循环。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [
                    {
                        "priority": "高",
                        "category": "精度",
                        "recommendation": "增加训练轮数",
                    }
                ],
            }
        }
        ctx = _make_ctx(artifacts=artifacts, has_coder=False)
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert - 发送了一条进度后 return，没有进入循环
        assert ctx.send_progress.call_count == 1

    @pytest.mark.asyncio
    async def test_improvement_loop_passes_after_first_iteration(self):
        """验证: 改进循环第一次迭代验证通过后立即退出。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [
                    {
                        "priority": "高",
                        "category": "精度",
                        "recommendation": "优化算法参数",
                    }
                ],
            }
        }
        ctx = _make_ctx(artifacts=artifacts, has_modeler_llm=True)
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert
        coder = ctx.agents["coder"]
        assert coder.run.call_count == 1
        # 验证报告应被更新为"通过"
        report = artifacts[ArtifactKeys.VALIDATION_REPORT]
        assert report["overall_assessment"]["validation_status"] == "通过"
        assert report["overall_assessment"]["improvement_iterations"] == 1

    @pytest.mark.asyncio
    async def test_improvement_continues_when_not_pass(self):
        """验证: 验证未通过时继续迭代直至达到最大次数。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [
                    {
                        "priority": "高",
                        "category": "鲁棒性",
                        "recommendation": "添加异常处理",
                    }
                ],
            }
        }
        ctx = _make_ctx(artifacts=artifacts, has_modeler_llm=True)
        # LLM 始终返回"未通过"
        llm_resp = MagicMock()
        llm_resp.content = "未通过"
        ctx.llms["modeler"].ainvoke = AsyncMock(return_value=llm_resp)
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert - 应迭代 MAX_ITERATIONS 次
        coder = ctx.agents["coder"]
        assert coder.run.call_count == IMPROVEMENT_MAX_ITERATIONS
        # 验证报告状态不变（仍未通过）
        report = artifacts[ArtifactKeys.VALIDATION_REPORT]
        assert report["overall_assessment"]["validation_status"] == "未通过"

    @pytest.mark.asyncio
    async def test_iteration_failure_does_not_interrupt_loop(self):
        """验证: 单次迭代失败不中断整个改进循环。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [
                    {
                        "priority": "高",
                        "category": "鲁棒性",
                        "recommendation": "添加异常处理",
                    }
                ],
            }
        }
        ctx = _make_ctx(artifacts=artifacts)
        # 每次 coder.run 都抛出异常
        ctx.agents["coder"].run = AsyncMock(
            side_effect=Exception("沙箱执行超时")
        )
        stage = ImprovementLoopStage()

        # Act - 不应向外抛出异常
        await stage.execute(ctx)

        # Assert
        assert ctx.agents["coder"].run.call_count == IMPROVEMENT_MAX_ITERATIONS
        # 最后一条进度消息应包含"改进循环完成"
        last_msg = ctx.send_progress.call_args_list[-1].args[0]
        assert "改进循环完成" in last_msg

    @pytest.mark.asyncio
    async def test_quick_validate_no_modeler_llm(self):
        """验证: 无 modeler LLM 时 _quick_validate 返回"有条件通过"，
        循环不会因验证通过而提前退出。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [
                    {
                        "priority": "高",
                        "category": "精度",
                        "recommendation": "增加迭代次数",
                    }
                ],
            }
        }
        ctx = _make_ctx(
            artifacts=artifacts, has_modeler_llm=False, has_coder=True
        )
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert - 没有 LLM 做验证，"有条件通过" != "通过"，
        # 所以循环不会提前退出
        coder = ctx.agents["coder"]
        assert coder.run.call_count == IMPROVEMENT_MAX_ITERATIONS

    @pytest.mark.asyncio
    async def test_quick_validate_no_code_response(self):
        """验证: improvement_response 无 code_response 属性时，
        _quick_validate 返回"有条件通过"。"""
        # Arrange
        artifacts = {
            ArtifactKeys.VALIDATION_REPORT: {
                "overall_assessment": {"validation_status": "未通过"},
                "improvement_recommendations": [
                    {
                        "priority": "高",
                        "category": "完整性",
                        "recommendation": "补充缺失步骤",
                    }
                ],
            }
        }
        ctx = _make_ctx(artifacts=artifacts, has_modeler_llm=True)
        # coder.run 返回一个没有 code_response 属性的对象
        plain_response = MagicMock(spec=[])  # spec=[] 使 hasattr 全部返回 False
        ctx.agents["coder"].run = AsyncMock(return_value=plain_response)
        stage = ImprovementLoopStage()

        # Act
        await stage.execute(ctx)

        # Assert - "有条件通过" != "通过"，循环执行全部次数
        coder = ctx.agents["coder"]
        assert coder.run.call_count == IMPROVEMENT_MAX_ITERATIONS

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self):
        """验证: 循环外的意外错误（如 artifacts 类型错误）会向上传播。"""
        # Arrange - validation_report 为非 dict 类型，
        # 调用 .get("overall_assessment", {}) 会抛出 AttributeError
        ctx = _make_ctx(
            artifacts={ArtifactKeys.VALIDATION_REPORT: "不是字典"}
        )
        stage = ImprovementLoopStage()

        # Act & Assert
        with pytest.raises(AttributeError):
            await stage.execute(ctx)
