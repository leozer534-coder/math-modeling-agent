"""工作流管线配置模块单元测试

覆盖: get_pipeline_config / _standard_config / _enhanced_config / _award_config
验证各工作流模式的阶段组合、顺序、超时、可选性及不可变性。
"""

import sys
from unittest.mock import MagicMock

# ================== langchain_core Mock 注入 ==================
# 必须在导入 app.* 模块之前注入，防止 ImportError
for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock_mod = MagicMock()
        _mock_mod.HumanMessage = MagicMock
        _mock_mod.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock_mod

import pytest

from app.core.workflow.configs import (
    _award_config,
    _enhanced_config,
    _standard_config,
    get_pipeline_config,
)
from app.core.workflow.pipeline import StageConfig
from app.core.workflow.stages import (
    AbstractStage,
    CoderStage,
    ConsistencyCheckStage,
    CoordinatorStage,
    DataPreviewStage,
    EDAStage,
    FinalizeStage,
    ImprovementLoopStage,
    ModelSelectionStage,
    ModelerStage,
    ProblemAnalysisStage,
    ReviewStage,
    SetupStage,
    SmartModelerStage,
    SymbolTableStage,
    ValidationStage,
    WriterStage,
)


# ============================================================
# 辅助工具
# ============================================================

def _stage_classes(configs: list[StageConfig]) -> list[type]:
    """提取配置列表中的 stage_class 顺序列表。"""
    return [c.stage_class for c in configs]


def _find_config(configs: list[StageConfig], stage_class: type) -> StageConfig:
    """在配置列表中查找指定 stage_class 的 StageConfig，找不到则抛出 AssertionError。"""
    for c in configs:
        if c.stage_class is stage_class:
            return c
    raise AssertionError(f"{stage_class.__name__} 未在配置列表中找到")


# ============================================================
# 1. get_pipeline_config 路由测试
# ============================================================


@pytest.mark.unit
class TestGetPipelineConfig:
    """get_pipeline_config 路由分发测试。"""

    def test_standard_mode(self):
        """验证: 传 'standard' 应返回标准模式配置（16 个阶段）。"""
        configs = get_pipeline_config("standard")
        assert len(configs) == 16

    def test_enhanced_mode(self):
        """验证: 传 'enhanced' 应返回增强模式配置（17 个阶段）。"""
        configs = get_pipeline_config("enhanced")
        assert len(configs) == 17

    def test_award_mode(self):
        """验证: 传 'award' 应返回获奖模式配置（17 个阶段）。"""
        configs = get_pipeline_config("award")
        assert len(configs) == 17

    def test_unknown_mode_defaults_to_standard(self):
        """验证: 传未知模式应回退到标准配置。"""
        configs = get_pipeline_config("nonexistent_mode")
        standard_configs = get_pipeline_config("standard")
        # 阶段数量和类型应与标准模式一致
        assert len(configs) == len(standard_configs)
        assert _stage_classes(configs) == _stage_classes(standard_configs)

    def test_custom_timeout(self):
        """验证: 传 stage_timeout=1200 应覆盖默认超时。"""
        configs = get_pipeline_config("standard", stage_timeout=1200)
        # Coordinator 应使用自定义超时
        coord = _find_config(configs, CoordinatorStage)
        assert coord.timeout == 1200
        # DataPreview 有独立超时，不受影响
        dp = _find_config(configs, DataPreviewStage)
        assert dp.timeout == 120.0


# ============================================================
# 2. _standard_config 测试
# ============================================================


@pytest.mark.unit
class TestStandardConfig:
    """标准模式配置测试。"""

    @pytest.fixture
    def stages(self) -> list[StageConfig]:
        """返回标准配置列表。"""
        return _standard_config()

    def test_stage_count(self, stages):
        """验证: 标准模式应有 16 个 StageConfig。"""
        assert len(stages) == 16

    def test_stage_order(self, stages):
        """验证: 关键 Stage 的顺序正确。"""
        expected_order = [
            CoordinatorStage,
            SetupStage,
            DataPreviewStage,
            EDAStage,
            ProblemAnalysisStage,
            ModelSelectionStage,
            SmartModelerStage,
            ModelerStage,
            SymbolTableStage,
            CoderStage,
            ValidationStage,
            ImprovementLoopStage,
            WriterStage,
            AbstractStage,
            ReviewStage,
            FinalizeStage,
        ]
        actual_order = _stage_classes(stages)
        assert actual_order == expected_order

    def test_required_stages_not_optional(self, stages):
        """验证: 核心必选阶段的 optional 应为 False。"""
        required_stage_classes = (
            CoordinatorStage,
            SetupStage,
            EDAStage,
            ModelerStage,
            CoderStage,
            WriterStage,
            FinalizeStage,
        )
        for cls in required_stage_classes:
            config = _find_config(stages, cls)
            assert config.optional is False, (
                f"{cls.__name__} 应为必选阶段 (optional=False)"
            )

    def test_optional_stages(self, stages):
        """验证: 可选阶段的 optional 应为 True。"""
        optional_stage_classes = (
            DataPreviewStage,
            ProblemAnalysisStage,
            ModelSelectionStage,
            SmartModelerStage,
            SymbolTableStage,
            ValidationStage,
            ImprovementLoopStage,
            AbstractStage,
            ReviewStage,
        )
        for cls in optional_stage_classes:
            config = _find_config(stages, cls)
            assert config.optional is True, (
                f"{cls.__name__} 应为可选阶段 (optional=True)"
            )

    def test_coder_timeout_zero(self, stages):
        """验证: CoderStage 的 timeout 应为 0（内部有子任务超时控制）。"""
        coder = _find_config(stages, CoderStage)
        assert coder.timeout == 0

    def test_data_preview_timeout(self, stages):
        """验证: DataPreviewStage 的 timeout 应为 120.0。"""
        dp = _find_config(stages, DataPreviewStage)
        assert dp.timeout == 120.0

    def test_progress_range(self, stages):
        """验证: 所有 Stage 的 progress_start 应小于 progress_end。"""
        for config in stages:
            assert config.progress_start < config.progress_end, (
                f"{config.stage_class.__name__}: "
                f"progress_start({config.progress_start}) "
                f">= progress_end({config.progress_end})"
            )

    def test_progress_coverage(self, stages):
        """验证: 第一个 Stage 从 0 开始，最后一个 Stage 到 100 结束。"""
        assert stages[0].progress_start == 0
        assert stages[-1].progress_end == 100

    def test_default_timeout(self, stages):
        """验证: 使用默认 timeout 的阶段应为 600.0。"""
        # 选择 CoordinatorStage 作为代表，它使用默认 timeout
        coord = _find_config(stages, CoordinatorStage)
        assert coord.timeout == 600.0

    def test_all_configs_are_stage_config_instances(self, stages):
        """验证: 所有元素应为 StageConfig 实例。"""
        for config in stages:
            assert isinstance(config, StageConfig)


# ============================================================
# 3. _enhanced_config 测试
# ============================================================


@pytest.mark.unit
class TestEnhancedConfig:
    """增强模式配置测试。"""

    @pytest.fixture
    def stages(self) -> list[StageConfig]:
        """返回增强配置列表。"""
        return _enhanced_config()

    def test_has_consistency_check(self, stages):
        """验证: 增强模式应包含 ConsistencyCheckStage。"""
        classes = _stage_classes(stages)
        assert ConsistencyCheckStage in classes

    def test_consistency_check_position(self, stages):
        """验证: ConsistencyCheckStage 应在 ReviewStage 之前。"""
        classes = _stage_classes(stages)
        cc_idx = classes.index(ConsistencyCheckStage)
        review_idx = classes.index(ReviewStage)
        assert cc_idx < review_idx, (
            f"ConsistencyCheckStage (idx={cc_idx}) "
            f"应在 ReviewStage (idx={review_idx}) 之前"
        )

    def test_consistency_check_optional(self, stages):
        """验证: ConsistencyCheckStage 应为 optional=True。"""
        cc = _find_config(stages, ConsistencyCheckStage)
        assert cc.optional is True

    def test_consistency_check_timeout(self, stages):
        """验证: ConsistencyCheckStage 的 timeout 应为 60.0。"""
        cc = _find_config(stages, ConsistencyCheckStage)
        assert cc.timeout == 60.0

    def test_stage_count(self, stages):
        """验证: 增强模式应比标准模式多 1 个 Stage（共 17 个）。"""
        standard = _standard_config()
        assert len(stages) == len(standard) + 1
        assert len(stages) == 17

    def test_inherits_standard_stages(self, stages):
        """验证: 标准模式的所有 Stage 类型应在增强模式中出现。"""
        standard_classes = set(_stage_classes(_standard_config()))
        enhanced_classes = set(_stage_classes(stages))
        assert standard_classes.issubset(enhanced_classes), (
            f"缺失的 Stage 类型: {standard_classes - enhanced_classes}"
        )

    def test_review_progress_adjusted(self, stages):
        """验证: ReviewStage 的进度区间在增强模式中被调整为 93-96。"""
        review = _find_config(stages, ReviewStage)
        assert review.progress_start == 93
        assert review.progress_end == 96

    def test_finalize_progress_unchanged(self, stages):
        """验证: FinalizeStage 的进度区间保持 97-100。"""
        finalize = _find_config(stages, FinalizeStage)
        assert finalize.progress_start == 97
        assert finalize.progress_end == 100


# ============================================================
# 4. _award_config 测试
# ============================================================


@pytest.mark.unit
class TestAwardConfig:
    """获奖模式配置测试。"""

    @pytest.fixture
    def stages(self) -> list[StageConfig]:
        """返回获奖配置列表。"""
        return _award_config()

    def test_review_required(self, stages):
        """验证: ReviewStage 应为 optional=False。"""
        review = _find_config(stages, ReviewStage)
        assert review.optional is False

    def test_validation_required(self, stages):
        """验证: ValidationStage 应为 optional=False。"""
        validation = _find_config(stages, ValidationStage)
        assert validation.optional is False

    def test_model_selection_required(self, stages):
        """验证: ModelSelectionStage 应为 optional=False。"""
        ms = _find_config(stages, ModelSelectionStage)
        assert ms.optional is False

    def test_smart_modeler_required(self, stages):
        """验证: SmartModelerStage 应为 optional=False。"""
        sm = _find_config(stages, SmartModelerStage)
        assert sm.optional is False

    def test_default_timeout_900(self, stages):
        """验证: 获奖模式默认 timeout 应为 900.0。"""
        # Coordinator 使用默认 timeout 参数
        coord = _find_config(stages, CoordinatorStage)
        assert coord.timeout == 900.0

    def test_custom_timeout_overrides(self):
        """验证: 自定义 timeout 应覆盖默认的 900.0。"""
        stages = _award_config(stage_timeout=1500)
        coord = _find_config(stages, CoordinatorStage)
        assert coord.timeout == 1500

    def test_has_consistency_check(self, stages):
        """验证: 获奖模式继承增强模式的 ConsistencyCheckStage。"""
        classes = _stage_classes(stages)
        assert ConsistencyCheckStage in classes

    def test_non_required_stages_still_optional(self, stages):
        """验证: 非获奖必选的 optional 阶段仍应为 optional=True。"""
        still_optional_classes = (
            DataPreviewStage,
            ProblemAnalysisStage,
            SymbolTableStage,
            ImprovementLoopStage,
            AbstractStage,
            ConsistencyCheckStage,
        )
        for cls in still_optional_classes:
            config = _find_config(stages, cls)
            assert config.optional is True, (
                f"{cls.__name__} 在获奖模式下应仍为可选阶段 (optional=True)"
            )

    def test_stage_count(self, stages):
        """验证: 获奖模式阶段数量与增强模式一致（17 个）。"""
        assert len(stages) == 17


# ============================================================
# 5. 不可变性测试
# ============================================================


@pytest.mark.unit
class TestConfigImmutability:
    """配置函数的不可变性测试。"""

    def test_standard_config_immutability(self):
        """验证: 多次调用 _standard_config 返回独立列表，互不影响。"""
        configs_a = _standard_config()
        configs_b = _standard_config()
        # 列表对象不同
        assert configs_a is not configs_b
        # 修改 a 不影响 b
        original_len = len(configs_b)
        configs_a.pop()
        assert len(configs_b) == original_len

    def test_enhanced_does_not_mutate_standard(self):
        """验证: 调用 _enhanced_config 不影响后续 _standard_config 的结果。"""
        # 先调用标准配置记录基线
        standard_before = _standard_config()
        # 调用增强配置（内部会获取并修改标准配置的副本）
        _enhanced_config()
        # 再次调用标准配置，验证未被污染
        standard_after = _standard_config()

        assert len(standard_before) == len(standard_after)
        assert _stage_classes(standard_before) == _stage_classes(standard_after)

        # 逐个比对关键属性
        for before, after in zip(standard_before, standard_after):
            assert before.stage_class is after.stage_class
            assert before.optional == after.optional
            assert before.timeout == after.timeout
            assert before.progress_start == after.progress_start
            assert before.progress_end == after.progress_end

    def test_award_does_not_mutate_enhanced(self):
        """验证: 调用 _award_config 不影响后续 _enhanced_config 的结果。"""
        enhanced_before = _enhanced_config()
        _award_config()
        enhanced_after = _enhanced_config()

        assert len(enhanced_before) == len(enhanced_after)
        for before, after in zip(enhanced_before, enhanced_after):
            assert before.stage_class is after.stage_class
            assert before.optional == after.optional
            assert before.timeout == after.timeout

    def test_interleaved_cross_mode_calls(self):
        """验证: 交叉调用三种模式配置不会产生状态污染。"""
        # 第一轮: standard -> enhanced -> award
        s1 = _standard_config()
        e1 = _enhanced_config()
        a1 = _award_config()
        # 第二轮: 反序 award -> enhanced -> standard
        a2 = _award_config()
        e2 = _enhanced_config()
        s2 = _standard_config()

        # standard 前后一致
        assert len(s1) == len(s2)
        assert _stage_classes(s1) == _stage_classes(s2)
        for c1, c2 in zip(s1, s2):
            assert c1.optional == c2.optional
            assert c1.timeout == c2.timeout
            assert c1.progress_start == c2.progress_start
            assert c1.progress_end == c2.progress_end

        # enhanced 前后一致
        assert len(e1) == len(e2)
        assert _stage_classes(e1) == _stage_classes(e2)

        # award 前后一致
        assert len(a1) == len(a2)
        assert _stage_classes(a1) == _stage_classes(a2)


# ============================================================
# 6. 边界条件 & 鲁棒性测试
# ============================================================


@pytest.mark.unit
class TestEdgeCases:
    """边界条件和鲁棒性测试。"""

    def test_empty_string_mode_fallback(self):
        """验证: 空字符串模式应回退到标准配置。"""
        configs = get_pipeline_config("")
        standard = get_pipeline_config("standard")
        assert len(configs) == len(standard)
        assert _stage_classes(configs) == _stage_classes(standard)

    def test_case_sensitive_mode(self):
        """验证: 模式名称区分大小写，'Standard' 应回退到标准配置。"""
        configs_upper = get_pipeline_config("Standard")
        configs_lower = get_pipeline_config("standard")
        # 大小写不同但回退后结果一致（都是 standard）
        assert len(configs_upper) == len(configs_lower)
        assert _stage_classes(configs_upper) == _stage_classes(configs_lower)

    def test_none_like_mode_fallback(self):
        """验证: 传入 'None' 字符串应回退到标准配置。"""
        configs = get_pipeline_config("None")
        standard = get_pipeline_config("standard")
        assert _stage_classes(configs) == _stage_classes(standard)


# ============================================================
# 7. Stage 唯一性测试
# ============================================================


@pytest.mark.unit
class TestStageUniqueness:
    """Stage 类在配置中的唯一性测试。"""

    def test_standard_no_duplicate_stages(self):
        """验证: 标准模式中每个 stage_class 只出现一次。"""
        classes = _stage_classes(_standard_config())
        assert len(classes) == len(set(classes)), (
            f"存在重复的 Stage 类型: "
            f"{[c.__name__ for c in classes if classes.count(c) > 1]}"
        )

    def test_enhanced_no_duplicate_stages(self):
        """验证: 增强模式中每个 stage_class 只出现一次。"""
        classes = _stage_classes(_enhanced_config())
        assert len(classes) == len(set(classes)), (
            f"存在重复的 Stage 类型: "
            f"{[c.__name__ for c in classes if classes.count(c) > 1]}"
        )

    def test_award_no_duplicate_stages(self):
        """验证: 获奖模式中每个 stage_class 只出现一次。"""
        classes = _stage_classes(_award_config())
        assert len(classes) == len(set(classes)), (
            f"存在重复的 Stage 类型: "
            f"{[c.__name__ for c in classes if classes.count(c) > 1]}"
        )


# ============================================================
# 8. 进度区间连续性 & 单调性测试
# ============================================================


@pytest.mark.unit
class TestProgressContinuity:
    """进度区间的连续性和单调递增性测试。"""

    @pytest.mark.parametrize("mode", ["standard", "enhanced", "award"])
    def test_progress_start_monotonic_non_decreasing(self, mode):
        """验证: 各阶段的 progress_start 应单调不递减。"""
        stages = get_pipeline_config(mode)
        for i in range(1, len(stages)):
            prev = stages[i - 1]
            curr = stages[i]
            assert curr.progress_start >= prev.progress_start, (
                f"[{mode}] {curr.stage_class.__name__} 的 progress_start"
                f"({curr.progress_start}) 小于前一阶段 "
                f"{prev.stage_class.__name__} 的 progress_start"
                f"({prev.progress_start})"
            )

    @pytest.mark.parametrize("mode", ["standard", "enhanced", "award"])
    def test_progress_no_large_gap(self, mode):
        """验证: 相邻阶段的进度区间不应有超过 10% 的间隙。"""
        stages = get_pipeline_config(mode)
        max_gap = 10
        for i in range(1, len(stages)):
            prev_end = stages[i - 1].progress_end
            curr_start = stages[i].progress_start
            gap = curr_start - prev_end
            assert gap <= max_gap, (
                f"[{mode}] {stages[i - 1].stage_class.__name__} -> "
                f"{stages[i].stage_class.__name__} 间隙过大: "
                f"prev_end={prev_end}, curr_start={curr_start}, gap={gap}"
            )

    @pytest.mark.parametrize("mode", ["standard", "enhanced", "award"])
    def test_all_progress_within_0_100(self, mode):
        """验证: 所有阶段的进度值应在 [0, 100] 范围内。"""
        stages = get_pipeline_config(mode)
        for config in stages:
            assert 0 <= config.progress_start <= 100, (
                f"[{mode}] {config.stage_class.__name__} "
                f"progress_start={config.progress_start} 超出 [0,100]"
            )
            assert 0 <= config.progress_end <= 100, (
                f"[{mode}] {config.stage_class.__name__} "
                f"progress_end={config.progress_end} 超出 [0,100]"
            )

    @pytest.mark.parametrize("mode", ["standard", "enhanced", "award"])
    def test_progress_start_lt_end(self, mode):
        """验证: 每个阶段的 progress_start 应严格小于 progress_end。"""
        stages = get_pipeline_config(mode)
        for config in stages:
            assert config.progress_start < config.progress_end, (
                f"[{mode}] {config.stage_class.__name__}: "
                f"start({config.progress_start}) >= end({config.progress_end})"
            )


# ============================================================
# 9. 增强模式补充测试
# ============================================================


@pytest.mark.unit
class TestEnhancedConfigExtra:
    """增强模式补充测试。"""

    def test_consistency_check_immediately_before_review(self):
        """验证: ConsistencyCheckStage 应紧邻 ReviewStage 之前（相邻，无间隔）。"""
        stages = _enhanced_config()
        classes = _stage_classes(stages)
        cc_idx = classes.index(ConsistencyCheckStage)
        review_idx = classes.index(ReviewStage)
        assert review_idx - cc_idx == 1, (
            f"ConsistencyCheckStage (idx={cc_idx}) 与 ReviewStage (idx={review_idx}) "
            f"之间不应有其他 Stage"
        )

    def test_enhanced_custom_timeout_forwarded(self):
        """验证: 增强模式自定义 stage_timeout 应正确传递到基础阶段。"""
        stages = _enhanced_config(stage_timeout=1200)
        coord = _find_config(stages, CoordinatorStage)
        assert coord.timeout == 1200
        # ConsistencyCheck 有独立超时，不受 stage_timeout 影响
        cc = _find_config(stages, ConsistencyCheckStage)
        assert cc.timeout == 60.0

    def test_enhanced_consistency_check_progress(self):
        """验证: ConsistencyCheckStage 的进度区间为 91-93。"""
        stages = _enhanced_config()
        cc = _find_config(stages, ConsistencyCheckStage)
        assert cc.progress_start == 91
        assert cc.progress_end == 93

    def test_enhanced_standard_stages_unaffected(self):
        """验证: 增强模式中标准阶段的超时值与标准模式一致。"""
        standard = _standard_config()
        enhanced = _enhanced_config()

        # 对比除 ReviewStage/FinalizeStage（进度被调整）外的共有阶段
        adjusted_classes = {ReviewStage, FinalizeStage, ConsistencyCheckStage}
        for s_cfg in standard:
            if s_cfg.stage_class in adjusted_classes:
                continue
            e_cfg = _find_config(enhanced, s_cfg.stage_class)
            assert e_cfg.timeout == s_cfg.timeout, (
                f"{s_cfg.stage_class.__name__} timeout 不一致: "
                f"standard={s_cfg.timeout}, enhanced={e_cfg.timeout}"
            )


# ============================================================
# 10. 获奖模式补充测试
# ============================================================


@pytest.mark.unit
class TestAwardConfigExtra:
    """获奖模式补充测试。"""

    def test_exactly_four_stages_promoted_to_required(self):
        """验证: 获奖模式恰好将 4 个标准可选阶段提升为必选。"""
        enhanced = _enhanced_config()
        award = _award_config()

        promoted_count = 0
        for e_cfg, a_cfg in zip(
            sorted(enhanced, key=lambda c: c.stage_class.__name__),
            sorted(award, key=lambda c: c.stage_class.__name__),
        ):
            if e_cfg.stage_class is a_cfg.stage_class:
                if e_cfg.optional is True and a_cfg.optional is False:
                    promoted_count += 1

        assert promoted_count == 4, (
            f"应恰好有 4 个阶段从 optional 提升为必选，实际: {promoted_count}"
        )

    def test_award_special_timeouts_preserved(self):
        """验证: 获奖模式不应覆盖 DataPreview/Coder/ConsistencyCheck 的特殊超时。"""
        stages = _award_config()

        dp = _find_config(stages, DataPreviewStage)
        assert dp.timeout == 120.0, (
            f"DataPreviewStage 超时应保持 120.0，实际: {dp.timeout}"
        )

        coder = _find_config(stages, CoderStage)
        assert coder.timeout == 0, (
            f"CoderStage 超时应保持 0，实际: {coder.timeout}"
        )

        cc = _find_config(stages, ConsistencyCheckStage)
        assert cc.timeout == 60.0, (
            f"ConsistencyCheckStage 超时应保持 60.0，实际: {cc.timeout}"
        )

    def test_award_inherits_enhanced_structure(self):
        """验证: 获奖模式的阶段顺序应与增强模式完全一致。"""
        enhanced_classes = _stage_classes(_enhanced_config())
        award_classes = _stage_classes(_award_config())
        assert enhanced_classes == award_classes, (
            "获奖模式的阶段顺序应与增强模式一致"
        )

    def test_award_900_timeout_applied_to_normal_stages(self):
        """验证: 获奖模式的 900.0 超时应用于使用默认超时的阶段。"""
        stages = _award_config()

        # 这些阶段在标准模式下使用 _DEFAULT_STAGE_TIMEOUT，
        # 获奖模式下应替换为 900.0
        normal_timeout_stages = (
            CoordinatorStage,
            SetupStage,
            EDAStage,
            ModelerStage,
            WriterStage,
            FinalizeStage,
        )
        for cls in normal_timeout_stages:
            config = _find_config(stages, cls)
            assert config.timeout == 900.0, (
                f"{cls.__name__} 在获奖模式下超时应为 900.0，实际: {config.timeout}"
            )
