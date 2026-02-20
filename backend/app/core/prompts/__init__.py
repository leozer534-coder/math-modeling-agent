"""
提示词模块 - 包含所有的AI提示词模板

支持两种加载方式：
1. 传统方式：直接导入常量
2. 配置化：通过 loader 从 TOML 文件加载
"""

# 导入原来的提示词（从 prompts.toml 加载）
from app.core.prompts.base_prompts import (
    CODER_PROMPT,
    COORDINATOR_PROMPT,
    FORMAT_QUESTIONS_PROMPT,
    INDEPENDENT_EDA_PROMPT,
    MODELER_PROMPT,
    build_coder_prompt_with_templates,
    build_modeler_prompt,
    get_coder_prompt,
    get_completion_check_prompt,
    get_reflection_prompt,
    get_reviewer_prompt,
    get_writer_prompt,
)

# 导入新的交互式提示词
from app.core.prompts.interactive_prompts import (
    INTERACTIVE_COORDINATOR_PROMPT,
    INTERACTIVE_USER_GUIDANCE,
)

# 导入配置化加载器
from app.core.prompts.loader import (
    PromptLoader,
    get_prompt_loader,
    load_prompt,
)


__all__ = [
    # 原来的提示词（从 prompts.toml 加载）
    'FORMAT_QUESTIONS_PROMPT',
    'COORDINATOR_PROMPT',
    'MODELER_PROMPT',
    'CODER_PROMPT',
    'INDEPENDENT_EDA_PROMPT',
    'get_writer_prompt',
    'get_coder_prompt',
    'get_reflection_prompt',
    'get_completion_check_prompt',
    'get_reviewer_prompt',
    'build_modeler_prompt',
    'build_coder_prompt_with_templates',
    # 新的交互式提示词
    'INTERACTIVE_COORDINATOR_PROMPT',
    'INTERACTIVE_USER_GUIDANCE',
    # 配置化加载器
    'PromptLoader',
    'get_prompt_loader',
    'load_prompt',
]

