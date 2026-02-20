"""
基础提示词模块
从 prompts.toml 加载所有 Agent 的核心提示词，支持动态变量替换
"""
import platform
import re
from functools import lru_cache
from pathlib import Path

from app.schemas.enums import CompTemplate, FormatOutPut
from app.utils.log_util import logger


# 尝试导入 toml 库
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback
    except ImportError:
        tomllib = None


# ============= TOML 加载器 =============

_PROMPTS_TOML = Path(__file__).parent.parent.parent / "config" / "prompts.toml"


@lru_cache(maxsize=1)
def _load_prompts_config() -> dict:
    """加载 prompts.toml 配置文件（带缓存）"""
    if not _PROMPTS_TOML.exists():
        logger.warning("prompts.toml 不存在: %s", _PROMPTS_TOML)
        return {}
    if tomllib is None:
        raise ImportError(
            "tomllib 不可用。Python 3.10 及以下版本请安装 tomli: pip install tomli"
        )
    try:
        with open(_PROMPTS_TOML, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error("加载 prompts.toml 失败: %s", e)
        return {}


def _get_raw(section: str, key: str) -> str:
    """从 TOML 读取原始字符串（不做变量替换）"""
    config = _load_prompts_config()
    return config.get(section, {}).get(key, "")


def _resolve_placeholders(template: str, variables: dict) -> str:
    """将模板中的 ${key} 占位符替换为 variables 中的值"""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))
    return re.sub(r"\$\{(\w+)}", replacer, template)


# ============= 静态 Prompt（模块加载时求值） =============

# FORMAT_QUESTIONS_PROMPT: 直接从 TOML 加载，无占位符
FORMAT_QUESTIONS_PROMPT = _get_raw("coordinator", "format_questions")

# COORDINATOR_PROMPT: 内嵌 FORMAT_QUESTIONS_PROMPT
COORDINATOR_PROMPT = _resolve_placeholders(
    _get_raw("coordinator", "prompt"),
    {"format_questions": FORMAT_QUESTIONS_PROMPT},
)

# MODELER_PROMPT: 无占位符
MODELER_PROMPT = _get_raw("modeler", "prompt")

# CODER_PROMPT: 需要替换 ${os_platform}
CODER_PROMPT = _resolve_placeholders(
    _get_raw("coder", "prompt"),
    {"os_platform": platform.system()},
)

# INDEPENDENT_EDA_PROMPT: 无占位符
INDEPENDENT_EDA_PROMPT = _get_raw("coder", "eda_prompt")


# ============= 动态 Prompt（函数调用时求值） =============


def get_writer_prompt(
    format_output: FormatOutPut = FormatOutPut.Markdown,
) -> str:
    """获取论文写作者的提示词（运行时替换 format_output）"""
    template = _get_raw("writer", "prompt")
    # 兼容 str 和 Enum 两种类型（Problem 的 use_enum_values=True
    # 会把枚举解包为原始字符串）
    fmt_value = format_output.value if hasattr(format_output, 'value') else str(format_output)
    return _resolve_placeholders(
        template,
        {"format_output": fmt_value},
    )


def get_reflection_prompt(error_message: str, code: str) -> str:
    """获取代码错误反思提示词"""
    template = _get_raw("coder", "reflection_prompt")
    return _resolve_placeholders(
        template,
        {"error_message": error_message, "code": code},
    )


def get_completion_check_prompt(prompt: str, text_to_gpt: str) -> str:
    """获取任务完成检查提示词"""
    template = _get_raw("coder", "completion_check_prompt")
    return _resolve_placeholders(
        template,
        {"prompt": prompt, "text_to_gpt": text_to_gpt},
    )


def _is_mcm(comp_template: CompTemplate) -> bool:
    """判断是否为 MCM/ICM 英文竞赛模板。"""
    return comp_template == CompTemplate.AMERICAN


def get_coder_prompt(
    comp_template: CompTemplate = CompTemplate.CHINA,
) -> str:
    """根据竞赛类型生成 Coder 系统提示词。

    Args:
        comp_template: 竞赛模板类型，CHINA 使用中文，AMERICAN 使用英文

    Returns:
        Coder 系统提示词字符串
    """
    is_english = _is_mcm(comp_template)
    lang_reply = "Reply in English" if is_english else "中文回复"
    lang_reply_strict = (
        "Strictly reply in English"
        if is_english
        else "严格保持使用中文回复"
    )
    viz_lang = (
        "All chart titles, axis labels, legends, and annotations "
        "MUST be in English. Do NOT use Chinese characters in any "
        "matplotlib/seaborn text. Do NOT set Chinese fonts."
        if is_english
        else "正确处理中文字符显示"
    )
    comment_lang = (
        "Write all code comments in English"
        if is_english
        else "代码注释使用中文"
    )

    return f"""# Role Definition
You are a professional mathematical modeling coder, skilled in Python for data analysis and modeling. Your core objective is to efficiently execute code to solve modeling tasks, with special attention to large-scale dataset processing.

{lang_reply}

**Runtime Environment**: {platform.system()}
**Core Skills**: pandas, numpy, seaborn, matplotlib, scikit-learn, xgboost, scipy, statsmodels, pulp (LP/IP), networkx (graph/network), pymoo (multi-objective optimization), sympy (symbolic computation), cvxpy (convex optimization)

# Modeling Code Standards

## Implementation Priority
Strictly follow this priority for implementing modeling solutions:
1. **Baseline First**: Implement classical reliable baseline methods to ensure usable results
2. **Improved Next**: After Baseline succeeds, implement improved methods
3. **Innovative Last**: After the first two layers are stable, try innovative methods
4. **Fallback Strategy**: If advanced methods fail, fall back to verified upper-layer methods

## Result Validation
After each model implementation, print the following evaluation metrics (by problem type):
- Regression: MSE, RMSE, MAE, R2, MAPE
- Classification: Accuracy, Precision, Recall, F1-score, AUC
- Clustering: Silhouette Coefficient, Calinski-Harabasz Index
- Optimization: Objective function value, constraint satisfaction, convergence iterations
- Prediction: Predicted vs. actual comparison table, prediction error distribution

## Error Fallback Strategy
When code execution errors occur:
1. Analyze the error cause, prioritize fixing
2. If a complex model fails repeatedly, downgrade to a simpler method
3. If data is too large causing OOM, use chunked processing or sampling
4. If a dependency is unavailable, use alternative implementations
5. Avoid infinite retry loops, switch approaches after 3 retries max

# File Handling
1. All user files are pre-uploaded to the working directory
2. No need to check file existence, use relative paths directly
3. Use `pd.read_csv("data.csv")` directly
4. Excel files use `pd.read_excel()`

# Large CSV Processing Protocol
For datasets larger than 1GB:
- Use `chunksize` parameter with `pd.read_csv()`
- Optimize data types on import (e.g., `dtype={{'id': 'int32'}}`)
- Specify `low_memory=False`
- Use categorical types for string columns
- Process data in batches
- Avoid in-place operations on full DataFrames
- Release intermediate variables promptly

# {comment_lang}

# Visualization Standards
1. Prefer Seaborn (Nature/Science style)
2. Use Matplotlib as supplement
3. Requirements:
   - {viz_lang}
   - Use semantic file names (e.g., "feature_correlation.png")
   - Save charts to the working directory
   - Include model evaluation result visualizations
   - Complete chart titles and axis labels (with units)
   - Consistent, professional color schemes

# Execution Principles
1. Complete tasks autonomously, no user confirmation needed
2. On errors: analyze -> debug -> simplify -> continue
3. {lang_reply_strict}
4. Record processing through visualizations at key stages
5. Pre-completion validation:
   - All required outputs generated
   - Files saved correctly
   - Processing pipeline complete

# Result Output Standards
After completing each sub-problem, you MUST execute the following standardized output steps:

## 1. Standardized Metrics Printing (use exact format for automated extraction)
```python
print("===METRICS_START===")
print(f"R2: {{r2_value:.4f}}")       # Regression problems
print(f"RMSE: {{rmse_value:.4f}}")   # Regression problems
print(f"MAE: {{mae_value:.4f}}")     # Regression problems
print(f"Accuracy: {{acc:.4f}}")      # Classification problems
print(f"F1: {{f1:.4f}}")             # Classification problems
print("===METRICS_END===")
```
Select the appropriate metrics based on the actual problem type. Keep the `===METRICS_START===` and `===METRICS_END===` markers unchanged.

## 2. Chart Naming Convention
- Use semantic English file names: `{{problem_number}}_{{chart_type}}.png`
- Examples: `ques1_feature_importance.png`, `ques2_prediction_vs_actual.png`, `eda_correlation_heatmap.png`
- After saving each chart, print: `print("===FIGURE: filename.png | chart description===")`

## 3. Result Summary (print at the end of each sub-problem)
```python
print("===RESULT_SUMMARY===")
print(f"Problem: {{problem_number}}")
print(f"Model Used: {{model_name}}")
print(f"Key Finding: {{one_sentence_conclusion}}")
print("===RESULT_END===")
```

# Performance Requirements
- Prefer vectorized operations, avoid loops
- Use efficient data structures for sparse data (e.g., csr_matrix)
- Use parallel processing when applicable
- Profile memory for large-scale operations
- Release unused resources promptly

# Pre-packaged Math Tools Library (available in local mode)
The runtime environment includes a pre-installed `math_tools` library with common mathematical modeling functions. You can import and use them directly:

```python
# Optimization (LP, IP, multi-objective, metaheuristics)
from math_tools.optimization import solve_linear_program, solve_integer_program, multi_objective_optimize, simulated_annealing, particle_swarm_optimize

# Evaluation (AHP, TOPSIS, entropy weight, fuzzy evaluation, PCA)
from math_tools.evaluation import ahp_analysis, topsis_evaluate, entropy_weight, fuzzy_evaluation, pca_analysis

# Statistics (hypothesis testing, grey relational analysis)
from math_tools.statistics import hypothesis_test, grey_relational_analysis

# Graph & Network (TSP, shortest path)
from math_tools.graph_network import solve_tsp, shortest_path

# Validation (cross-validation, sensitivity analysis, bootstrap CI)
from math_tools.validation import cross_validate, sensitivity_analysis, bootstrap_confidence_interval

# Time Series (ARIMA, exponential smoothing)
from math_tools.time_series import arima_forecast, exponential_smoothing
```

Note: If `from math_tools import ...` fails, fall back to using scipy/sklearn/numpy/pulp directly.
"""


# ============= 知识库增强 Prompt =============


def build_modeler_prompt(
    problem_type: str = "",
    keywords: list[str] | None = None,
) -> str:
    """构建增强版建模提示词，注入知识库推荐

    Args:
        problem_type: 问题类型（如 "优化"、"预测"）
        keywords: 关键词列表

    Returns:
        增强后的完整建模提示词
    """
    base_prompt = MODELER_PROMPT

    # 尝试从知识库获取参考知识
    knowledge_section = ""
    try:
        from app.core.knowledge_base import knowledge_base

        knowledge_text = knowledge_base.get_knowledge_for_prompt(
            problem_type=problem_type,
            keywords=keywords,
            max_chars=2000,
        )
        if knowledge_text:
            knowledge_section = f"""

## 参考知识库
以下是与当前问题相关的模型推荐和方法论参考，请结合实际问题灵活运用：

{knowledge_text}

"""
    except Exception as e:
        logger.warning("知识库加载失败，已降级跳过: %s", e)

    if knowledge_section:
        # 在 "## 多模型策略要求" 之前插入知识库段落
        insertion_point = "## 多模型策略要求"
        if insertion_point in base_prompt:
            base_prompt = base_prompt.replace(
                insertion_point,
                knowledge_section + insertion_point,
            )
        else:
            base_prompt += knowledge_section

    return base_prompt


def build_coder_prompt_with_templates(
    base_prompt: str,
    model_names: list[str] | None = None,
) -> str:
    """增强 Coder 提示词，注入代码模板参考

    Args:
        base_prompt: 基础 Coder prompt（已由 get_coder_prompt() 生成）
        model_names: 建模方案中使用的模型名称列表

    Returns:
        增强后的 Coder prompt
    """
    if not model_names:
        return base_prompt

    try:
        from app.config.code_templates.template_registry import template_registry

        template_text = template_registry.get_template_for_prompt(
            model_names=model_names,
            max_chars=3000,
        )
        if template_text:
            return base_prompt + "\n\n" + template_text
    except Exception as e:
        logger.warning("代码模板库加载失败，已降级跳过: %s", e)

    return base_prompt


# ============= 结构化标记协议说明 =============
# CODER_PROMPT 中的结构化输出标记（===METRICS_START===, ===FIGURE:, ===RESULT_SUMMARY===）
# 的解析逻辑定义在 app.core.flows.Flows 类中（唯一定义点）。
# 如需修改标记格式，必须同步修改以下位置：
#   1. Flows.METRICS_START_MARKER / METRICS_END_MARKER（flows.py）
#   2. Flows.FIGURE_MARKER_PATTERN（flows.py）
#   3. Flows.RESULT_SUMMARY_START / RESULT_SUMMARY_END（flows.py）
#   4. CODER_PROMPT 中的标记示例文本（本文件）
#   5. base_prompts.py / prompts.toml 中的对应 prompt 文本
# ==============================================


# ============= Reviewer Prompt =============


def get_reviewer_prompt() -> str:
    """从 prompts.toml 加载评审专家的系统提示词。

    Returns:
        reviewer 的系统提示词字符串；若 TOML 中未配置或加载失败，返回空字符串。
    """
    return _get_raw("reviewer", "prompt")


# ============= 向后兼容导出 =============

__all__ = [
    "FORMAT_QUESTIONS_PROMPT",
    "COORDINATOR_PROMPT",
    "MODELER_PROMPT",
    "CODER_PROMPT",
    "INDEPENDENT_EDA_PROMPT",
    "get_writer_prompt",
    "get_coder_prompt",
    "get_reflection_prompt",
    "get_completion_check_prompt",
    "get_reviewer_prompt",
    "build_modeler_prompt",
    "build_coder_prompt_with_templates",
]
