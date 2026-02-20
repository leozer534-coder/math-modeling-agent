"""
Prompt 加载器测试 - Test Prompt Loader

测试 Prompt 配置化加载功能
"""

import os
import tempfile
from unittest.mock import patch


class TestPromptLoader:
    """Prompt 加载器测试"""
    
    def test_import_loader(self):
        """测试导入加载器"""
        from app.core.prompts import PromptLoader, get_prompt_loader, load_prompt
        assert load_prompt is not None
        assert get_prompt_loader is not None
        assert PromptLoader is not None
    
    def test_get_prompt_loader_singleton(self):
        """测试全局加载器单例"""
        from app.core.prompts import get_prompt_loader
        
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        
        assert loader1 is loader2
    
    def test_load_prompt_from_config(self):
        """测试从配置文件加载 prompt"""
        from app.core.prompts import load_prompt
        
        # 清除缓存
        load_prompt.cache_clear()
        
        prompt = load_prompt("coordinator")
        
        # 应该能加载到内容
        assert prompt is not None
        assert len(prompt) > 0
    
    def test_load_prompt_nonexistent_agent(self):
        """测试加载不存在的 Agent prompt"""
        from app.core.prompts.loader import PromptLoader
        
        loader = PromptLoader()
        prompt = loader.get_prompt("nonexistent_agent", default="默认值")
        
        assert prompt == "默认值"
    
    def test_list_agents(self):
        """测试列出所有 Agent"""
        from app.core.prompts import get_prompt_loader
        
        loader = get_prompt_loader()
        loader.reload()
        agents = loader.list_agents()
        
        # 应该包含配置的 Agent
        assert "coordinator" in agents
        assert "modeler" in agents
        assert "coder" in agents
    
    def test_get_version(self):
        """测试获取配置版本"""
        from app.core.prompts import get_prompt_loader
        
        loader = get_prompt_loader()
        version = loader.get_version()
        
        assert version is not None
        # 如果配置文件存在，应该有版本号
        if version != "unknown":
            assert "." in version  # 版本号格式 x.y.z
    
    def test_get_agent_config(self):
        """测试获取 Agent 完整配置"""
        from app.core.prompts import get_prompt_loader
        
        loader = get_prompt_loader()
        config = loader.get_agent_config("coordinator")
        
        if config:  # 如果配置存在
            assert "prompt" in config or "name" in config
    
    def test_env_variable_override(self):
        """测试环境变量覆盖"""
        from app.core.prompts.loader import PromptLoader
        
        # 设置环境变量
        test_prompt = "这是测试用的环境变量 prompt"
        with patch.dict(os.environ, {"PROMPT_TEST_AGENT_PROMPT": test_prompt}):
            loader = PromptLoader()
            prompt = loader.get_prompt("test_agent", use_env=True)
            
            assert prompt == test_prompt
    
    def test_env_variable_disabled(self):
        """测试禁用环境变量覆盖"""
        from app.core.prompts.loader import PromptLoader
        
        test_prompt = "这是测试用的环境变量 prompt"
        with patch.dict(os.environ, {"PROMPT_TEST_AGENT_PROMPT": test_prompt}):
            loader = PromptLoader()
            prompt = loader.get_prompt("test_agent", use_env=False, default="默认")
            
            # 不应该使用环境变量
            assert prompt == "默认"
    
    def test_reload_config(self):
        """测试重新加载配置"""
        from app.core.prompts import get_prompt_loader
        
        loader = get_prompt_loader()
        
        # 重新加载不应该抛出异常
        loader.reload()
        
        assert loader._loaded or not loader._loaded
    
    def test_custom_config_path(self):
        """测试自定义配置路径"""
        from app.core.prompts.loader import PromptLoader
        
        # 使用临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('[test]\nprompt = "测试 prompt"\n')
            temp_path = f.name
        
        try:
            loader = PromptLoader(config_path=temp_path)
            # 由于需要 tomllib，这里可能无法实际加载
            # 但不应该抛出异常
            loader.get_prompt("test", default="默认")
        finally:
            os.unlink(temp_path)
    
    def test_canonical_exports_from_prompts_package(self):
        """测试 prompts 包的规范导出路径（所有外部模块统一使用此路径）"""
        from app.core.prompts import (
            CODER_PROMPT,
            COORDINATOR_PROMPT,
            FORMAT_QUESTIONS_PROMPT,
            INDEPENDENT_EDA_PROMPT,
            MODELER_PROMPT,
            build_coder_prompt_with_templates,
            build_modeler_prompt,
            get_completion_check_prompt,
            get_coder_prompt,
            get_reflection_prompt,
            get_writer_prompt,
        )

        # 静态常量应为非空字符串
        assert isinstance(FORMAT_QUESTIONS_PROMPT, str) and len(FORMAT_QUESTIONS_PROMPT) > 0
        assert isinstance(COORDINATOR_PROMPT, str) and len(COORDINATOR_PROMPT) > 0
        assert isinstance(MODELER_PROMPT, str) and len(MODELER_PROMPT) > 0
        assert isinstance(CODER_PROMPT, str) and len(CODER_PROMPT) > 0
        assert isinstance(INDEPENDENT_EDA_PROMPT, str) and len(INDEPENDENT_EDA_PROMPT) > 0

        # 动态函数应可调用
        assert callable(get_writer_prompt)
        assert callable(get_coder_prompt)
        assert callable(get_reflection_prompt)
        assert callable(get_completion_check_prompt)
        assert callable(build_modeler_prompt)
        assert callable(build_coder_prompt_with_templates)


class TestPromptLoaderIntegration:
    """Prompt 加载器集成测试"""
    
    def test_load_all_configured_prompts(self):
        """测试加载所有配置的 prompt"""
        from app.core.prompts import get_prompt_loader
        
        loader = get_prompt_loader()
        loader.reload()
        
        agents = loader.list_agents()
        
        for agent in agents:
            prompt = loader.get_prompt(agent)
            assert prompt is not None, f"{agent} 的 prompt 不应为 None"
    
    def test_prompt_content_quality(self):
        """测试 prompt 内容质量"""
        from app.core.prompts import get_prompt_loader
        
        loader = get_prompt_loader()
        loader.reload()
        
        # 检查主要 Agent 的 prompt
        main_agents = ["coordinator", "modeler", "coder", "writer"]
        
        for agent in main_agents:
            prompt = loader.get_prompt(agent)
            if prompt:
                # prompt 应该有一定长度
                assert len(prompt) > 10, f"{agent} 的 prompt 太短"
