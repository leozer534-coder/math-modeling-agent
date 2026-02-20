"""Pipeline Stage 共享常量

将散布在各 Stage 中的硬编码魔术数字统一管理，方便调优和维护。
"""

# ---- 迭代/重试限制 ----
MAX_REMODEL_ATTEMPTS = 2          # CoderStage: 重建模最大次数
MAX_REVISE_ITERATIONS = 2         # ReviewStage: 修订最大迭代次数
IMPROVEMENT_MAX_ITERATIONS = 2    # ImprovementLoopStage: 改进循环最大次数

# ---- 质量阈值 ----
REVIEW_QUALITY_THRESHOLD = 4      # ReviewStage: 评审合格阈值 (1-5 分制)
REVIEW_WEAK_THRESHOLD = 3.5       # ReviewStage: 弱章节判定阈值

# ---- 数据处理 ----
DATA_PREVIEW_MAX_FILE_SIZE = 100 * 1024 * 1024  # DataPreviewStage: 文件大小限制 (100MB)
DATA_SUMMARY_MAX_LENGTH = 8000                   # DataPreviewStage: 数据摘要截断长度

# ---- EDA 分析 ----
EDA_CORRELATION_THRESHOLD = 0.5   # EDAStage: 相关性阈值
EDA_HIGH_MISSING_RATE = 0.2       # EDAStage: 高缺失率阈值

# ---- 文本截断长度 ----
TEXT_TRUNCATION_XSHORT = 500      # 极短截断
TEXT_TRUNCATION_SHORT = 1000      # 短截断
TEXT_TRUNCATION_MEDIUM = 2000     # 中等截断
TEXT_TRUNCATION_LONG = 3000       # 长截断
