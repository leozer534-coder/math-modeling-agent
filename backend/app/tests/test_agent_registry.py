"""Agent 注册表单元测试

覆盖: agents/__init__.py 中的分组注册表和全量导出
验证核心 Agent 正确注册、分组正确、可导入，
实验性 Agent 通过懒加载按需导入。
"""

import pytest


class TestAgentGroups:
    """Agent 分组注册表测试"""

    def test_core_agents_group(self):
        """测试核心 Agent 分组包含 4 个成员"""
        from app.core.agents import CORE_AGENTS
        assert len(CORE_AGENTS) == 4
        expected_keys = {"coordinator", "modeler", "coder", "writer"}
        assert set(CORE_AGENTS.keys()) == expected_keys

    def test_analysis_agents_group(self):
        """测试分析 Agent 分组（PatternDiscoveryEngine 已移至实验性子包）"""
        from app.core.agents import ANALYSIS_AGENTS
        assert len(ANALYSIS_AGENTS) == 3
        expected_keys = {"problem_analyzer", "problem_insight_analyzer", "data_understanding_expert"}
        assert set(ANALYSIS_AGENTS.keys()) == expected_keys

    def test_modeling_agents_group(self):
        """测试建模 Agent 分组"""
        from app.core.agents import MODELING_AGENTS
        assert len(MODELING_AGENTS) == 3
        expected_keys = {"model_selector", "smart_modeler", "experiment_designer"}
        assert set(MODELING_AGENTS.keys()) == expected_keys

    def test_coding_agents_group(self):
        """测试编码 Agent 分组（实验性 Agent 已移至子包）"""
        from app.core.agents import CODING_AGENTS
        assert len(CODING_AGENTS) == 0

    def test_writing_agents_group(self):
        """测试写作 Agent 分组（实验性 Agent 已移至子包）"""
        from app.core.agents import WRITING_AGENTS
        assert len(WRITING_AGENTS) == 1
        expected_keys = {"abstract_generator"}
        assert set(WRITING_AGENTS.keys()) == expected_keys

    def test_validation_agents_group(self):
        """测试验证 Agent 分组（实验性 Agent 已移至子包）"""
        from app.core.agents import VALIDATION_AGENTS
        assert len(VALIDATION_AGENTS) == 3
        expected_keys = {"validation_expert", "reviewer", "benchmark_analyzer"}
        assert set(VALIDATION_AGENTS.keys()) == expected_keys

    def test_interactive_agents_group(self):
        """测试交互 Agent 分组"""
        from app.core.agents import INTERACTIVE_AGENTS
        assert len(INTERACTIVE_AGENTS) == 1
        assert "interactive_coordinator" in INTERACTIVE_AGENTS


class TestAllAgents:
    """全量 Agent 注册表测试（不含实验性 Agent）"""

    def test_all_agents_count(self):
        """测试 ALL_AGENTS 包含所有非实验性 Agent（4+3+3+0+1+3+1=15 个角色）"""
        from app.core.agents import ALL_AGENTS
        assert len(ALL_AGENTS) == 15

    def test_all_agents_is_union_of_groups(self):
        """测试 ALL_AGENTS 是所有非实验性分组的并集"""
        from app.core.agents import (
            ALL_AGENTS,
            ANALYSIS_AGENTS,
            CODING_AGENTS,
            CORE_AGENTS,
            INTERACTIVE_AGENTS,
            MODELING_AGENTS,
            VALIDATION_AGENTS,
            WRITING_AGENTS,
        )
        union = {
            **CORE_AGENTS, **ANALYSIS_AGENTS, **MODELING_AGENTS,
            **CODING_AGENTS, **WRITING_AGENTS, **VALIDATION_AGENTS,
            **INTERACTIVE_AGENTS,
        }
        assert set(ALL_AGENTS.keys()) == set(union.keys())

    def test_no_duplicate_keys_across_groups(self):
        """测试各分组之间无重复 key"""
        from app.core.agents import (
            ANALYSIS_AGENTS,
            CODING_AGENTS,
            CORE_AGENTS,
            INTERACTIVE_AGENTS,
            MODELING_AGENTS,
            VALIDATION_AGENTS,
            WRITING_AGENTS,
        )
        all_keys = []
        for group in [CORE_AGENTS, ANALYSIS_AGENTS, MODELING_AGENTS,
                       CODING_AGENTS, WRITING_AGENTS, VALIDATION_AGENTS, INTERACTIVE_AGENTS]:
            all_keys.extend(group.keys())
        assert len(all_keys) == len(set(all_keys)), "存在重复的 Agent key"

    def test_all_values_are_classes(self):
        """测试所有注册值都是类（可调用）"""
        from app.core.agents import ALL_AGENTS
        for key, agent_class in ALL_AGENTS.items():
            assert isinstance(agent_class, type), f"{key} 的值不是类: {type(agent_class)}"


class TestExperimentalAgentsLazyLoading:
    """实验性 Agent 懒加载测试"""

    def test_experimental_agents_lazy_proxy_exists(self):
        """测试 EXPERIMENTAL_AGENTS 懒加载代理对象存在"""
        from app.core.agents import EXPERIMENTAL_AGENTS
        assert EXPERIMENTAL_AGENTS is not None

    def test_experimental_agents_lazy_loading(self):
        """测试实验性 Agent 的懒加载机制"""
        from app.core.agents import EXPERIMENTAL_AGENTS
        assert len(EXPERIMENTAL_AGENTS) == 6
        expected_keys = {
            "competition_writer", "innovation_highlighter",
            "hyperparameter_tuner", "pattern_discovery_engine",
            "performance_optimizer", "result_interpreter",
        }
        assert set(EXPERIMENTAL_AGENTS.keys()) == expected_keys

    def test_experimental_agents_values_are_classes(self):
        """测试懒加载后的实验性 Agent 值都是类"""
        from app.core.agents import EXPERIMENTAL_AGENTS
        for key, agent_class in EXPERIMENTAL_AGENTS.items():
            assert isinstance(agent_class, type), f"{key} 的值不是类: {type(agent_class)}"

    def test_get_experimental_agent_function(self):
        """测试按类名获取实验性 Agent"""
        from app.core.agents.experimental import get_experimental_agent
        cls = get_experimental_agent("HyperparameterTuningMaster")
        assert cls is not None
        assert isinstance(cls, type)

    def test_get_experimental_agent_invalid_name(self):
        """测试无效类名抛出 KeyError"""
        from app.core.agents.experimental import get_experimental_agent
        with pytest.raises(KeyError):
            get_experimental_agent("NonExistentAgent")

    def test_list_experimental_agents(self):
        """测试列出所有实验性 Agent"""
        from app.core.agents.experimental import list_experimental_agents
        agents = list_experimental_agents()
        assert len(agents) == 6
        assert "HyperparameterTuningMaster" in agents

    def test_get_all_agents_with_experimental(self):
        """测试获取包含实验性 Agent 的全量注册表"""
        from app.core.agents import ALL_AGENTS, get_all_agents_with_experimental
        full = get_all_agents_with_experimental()
        assert len(full) == len(ALL_AGENTS) + 6

    def test_backward_compatible_import_from_agents(self):
        """测试从 app.core.agents 直接导入实验性 Agent（向后兼容）"""
        from app.core.agents import CompetitionExpertWriter
        assert CompetitionExpertWriter is not None
        assert isinstance(CompetitionExpertWriter, type)

    def test_backward_compatible_import_from_experimental(self):
        """测试从 experimental 子包直接导入"""
        from app.core.agents.experimental import InnovationHighlighter
        assert InnovationHighlighter is not None
        assert isinstance(InnovationHighlighter, type)


class TestCoreAgentImports:
    """核心 Agent 导入测试"""

    def test_coordinator_agent_importable(self):
        """测试 CoordinatorAgent 可正确导入"""
        from app.core.agents import CoordinatorAgent
        assert CoordinatorAgent is not None

    def test_modeler_agent_importable(self):
        """测试 ModelerAgent 可正确导入"""
        from app.core.agents import ModelerAgent
        assert ModelerAgent is not None

    def test_coder_agent_importable(self):
        """测试 CoderAgent 可正确导入"""
        from app.core.agents import CoderAgent
        assert CoderAgent is not None

    def test_writer_agent_importable(self):
        """测试 WriterAgent 可正确导入"""
        from app.core.agents import WriterAgent
        assert WriterAgent is not None


class TestBaseInfrastructureImports:
    """基础设施类导入测试"""

    def test_agent_base_importable(self):
        """测试 Agent 基类可导入"""
        from app.core.agents import Agent
        assert Agent is not None

    def test_expert_agent_importable(self):
        """测试 ExpertAgent 可导入"""
        from app.core.agents import ExpertAgent
        assert ExpertAgent is not None

    def test_agent_role_importable(self):
        """测试 AgentRole 枚举可导入"""
        from app.core.agents import AgentRole
        assert AgentRole is not None

    def test_quality_metrics_importable(self):
        """测试 QualityMetrics 可导入"""
        from app.core.agents import QualityMetrics
        assert QualityMetrics is not None


class TestEnhancedAgentImports:
    """增强 Agent 导入测试"""

    def test_problem_analyzer_importable(self):
        from app.core.agents import ProblemAnalyzer
        assert ProblemAnalyzer is not None

    def test_data_understanding_expert_importable(self):
        from app.core.agents import DataUnderstandingExpert
        assert DataUnderstandingExpert is not None

    def test_model_selector_importable(self):
        from app.core.agents import ModelSelector
        assert ModelSelector is not None

    def test_smart_modeler_importable(self):
        from app.core.agents import SmartModelerWithInnovation
        assert SmartModelerWithInnovation is not None

    def test_experiment_designer_importable(self):
        from app.core.agents import ExperimentDesigner
        assert ExperimentDesigner is not None

    def test_competition_writer_importable(self):
        """测试 CompetitionExpertWriter 可通过懒加载导入"""
        from app.core.agents import CompetitionExpertWriter
        assert CompetitionExpertWriter is not None

    def test_reviewer_importable(self):
        from app.core.agents import Reviewer
        assert Reviewer is not None

    def test_validation_expert_importable(self):
        from app.core.agents import ValidationExpert
        assert ValidationExpert is not None
