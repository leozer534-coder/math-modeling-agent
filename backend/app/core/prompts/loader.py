"""
Prompt 加载器 - Prompt Loader

从配置文件加载 Agent 提示词，支持：
1. TOML 配置文件加载
2. 环境变量覆盖
3. 版本管理
4. 缓存机制
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from app.utils.log_util import logger


# 尝试导入 toml 库
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback
    except ImportError:
        tomllib = None


# ============= 配置 =============

# 配置文件位于 app/config/prompts.toml
PROMPTS_FILE = Path(__file__).parent.parent.parent / "config" / "prompts.toml"
ENV_PREFIX = "PROMPT_"  # 环境变量前缀


# ============= 加载器 =============

class PromptLoader:
    """
    Prompt 加载器
    
    使用示例：
        >>> loader = PromptLoader()
        >>> prompt = loader.get_prompt("coordinator")
        >>> print(prompt)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化加载器
        
        Args:
            config_path: 配置文件路径，默认使用 prompts.toml
        """
        self.config_path = Path(config_path) if config_path else PROMPTS_FILE
        self._cache: Dict[str, Any] = {}
        self._loaded = False
        
    def _load_config(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if self._loaded:
            return self._cache
        
        if not self.config_path.exists():
            logger.warning("Prompt 配置文件不存在: %s", self.config_path)
            return {}
        
        if tomllib is None:
            logger.warning("未安装 tomllib/tomli，无法加载 TOML 配置")
            return {}
        
        try:
            with open(self.config_path, "rb") as f:
                self._cache = tomllib.load(f)
            self._loaded = True
            logger.info("已加载 Prompt 配置: %s", self.config_path)
            return self._cache
        except Exception as e:
            logger.error("加载 Prompt 配置失败: %s", e)
            return {}
    
    def get_prompt(
        self,
        agent_type: str,
        default: Optional[str] = None,
        use_env: bool = True,
    ) -> str:
        """
        获取指定 Agent 的提示词
        
        Args:
            agent_type: Agent 类型 (coordinator, modeler, coder, writer, etc.)
            default: 默认值（配置不存在时使用）
            use_env: 是否检查环境变量覆盖
            
        Returns:
            str: Agent 提示词
        """
        # 优先检查环境变量
        if use_env:
            env_key = f"{ENV_PREFIX}{agent_type.upper()}_PROMPT"
            env_value = os.getenv(env_key)
            if env_value:
                logger.debug("使用环境变量 %s 覆盖 %s prompt", env_key, agent_type)
                return env_value
        
        # 从配置文件加载
        config = self._load_config()
        agent_config = config.get(agent_type, {})
        
        if isinstance(agent_config, dict):
            prompt = agent_config.get("prompt", default or "")
        else:
            prompt = default or ""
        
        if not prompt:
            logger.warning("未找到 %s 的 prompt 配置", agent_type)
        
        return prompt
    
    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """
        获取 Agent 的完整配置
        
        Args:
            agent_type: Agent 类型
            
        Returns:
            Dict: Agent 配置（包含 name, description, prompt 等）
        """
        config = self._load_config()
        return config.get(agent_type, {})
    
    def list_agents(self) -> list:
        """列出所有已配置的 Agent"""
        config = self._load_config()
        # 排除 meta 等非 Agent 配置
        return [k for k in config.keys() if k != "meta"]
    
    def get_version(self) -> str:
        """获取配置版本"""
        config = self._load_config()
        meta = config.get("meta", {})
        return meta.get("version", "unknown")
    
    def reload(self) -> None:
        """重新加载配置"""
        self._cache = {}
        self._loaded = False
        self._load_config()


# ============= 全局实例 =============

_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """获取全局 Prompt 加载器"""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


@lru_cache(maxsize=32)
def load_prompt(agent_type: str, default: str = "") -> str:
    """
    便捷函数：加载 Agent 提示词

    使用示例：
        >>> from app.core.prompts.loader import load_prompt
        >>> coordinator_prompt = load_prompt("coordinator")
    """
    return get_prompt_loader().get_prompt(agent_type, default)
