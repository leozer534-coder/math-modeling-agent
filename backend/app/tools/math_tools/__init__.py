"""
数学建模专用工具链

竞赛常用数学工具函数集合，供 CoderAgent 在沙箱中直接导入使用。
使用相对导入，以同时兼容两种场景:
  1. 主应用内: from app.tools.math_tools import ...
  2. Jupyter 内核内: sys.path 注入 tools/ 后 from math_tools import ...
"""
from .optimization import (
    solve_linear_program,
    solve_integer_program,
    multi_objective_optimize,
    simulated_annealing,
    particle_swarm_optimize,
)
from .evaluation import (
    ahp_analysis,
    topsis_evaluate,
    entropy_weight,
    fuzzy_evaluation,
    pca_analysis,
)
from .statistics import (
    hypothesis_test,
    grey_relational_analysis,
)
from .graph_network import (
    solve_tsp,
    shortest_path,
)
from .validation import (
    cross_validate,
    sensitivity_analysis,
    bootstrap_confidence_interval,
)
from .time_series import (
    arima_forecast,
    exponential_smoothing,
)

__all__ = [
    "solve_linear_program", "solve_integer_program", "multi_objective_optimize",
    "simulated_annealing", "particle_swarm_optimize",
    "ahp_analysis", "topsis_evaluate", "entropy_weight", "fuzzy_evaluation", "pca_analysis",
    "hypothesis_test", "grey_relational_analysis",
    "solve_tsp", "shortest_path",
    "cross_validate", "sensitivity_analysis", "bootstrap_confidence_interval",
    "arima_forecast", "exponential_smoothing",
]
