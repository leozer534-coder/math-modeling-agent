"""
数学建模知识库系统 - 为各个Agent提供智能决策支持
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ModelKnowledge:
    """模型知识项"""
    name: str
    category: str
    description: str
    applicable_problems: List[str]
    advantages: List[str]
    disadvantages: List[str]
    complexity: str  # 低/中/高
    implementation_difficulty: str
    data_requirements: Dict[str, str]
    key_parameters: List[str]
    validation_methods: List[str]
    common_pitfalls: List[str]
    implementation_steps: Optional[List[str]] = None
    related_models: Optional[List[str]] = None


@dataclass
class EvaluationMetricKnowledge:
    """评价指标知识项"""
    name: str
    metric_type: str
    description: str
    formula: str
    interpretation: str
    range: str
    when_to_use: List[str]
    advantages: List[str]
    limitations: List[str]
    related_metrics: List[str]


@dataclass
class ValidationMethodKnowledge:
    """验证方法知识项"""
    name: str
    description: str
    applicable_scenarios: List[str]
    implementation_steps: List[str]
    computational_cost: str
    robustness: str
    sample_size_requirement: str
    common_issues: List[str]


class MathModelingKnowledgeBase:
    """数学建模知识库"""

    def __init__(self):
        self.models: Dict[str, ModelKnowledge] = self._initialize_models()
        self.metrics: Dict[str, EvaluationMetricKnowledge] = self._initialize_metrics()
        self.validation_methods: Dict[str, ValidationMethodKnowledge] = self._initialize_validation_methods()
        self.best_practices: Dict[str, List[str]] = self._initialize_best_practices()
        self.problem_type_guidelines: Dict[str, Dict[str, Any]] = self._initialize_problem_guidelines()

    def _initialize_models(self) -> Dict[str, ModelKnowledge]:
        """初始化模型知识库"""
        return {
            "linear_programming": ModelKnowledge(
                name="线性规划",
                category="优化",
                description="所有约束条件和目标函数都是决策变量的线性函数的优化问题",
                applicable_problems=["资源分配", "生产计划", "运输问题", "投资组合", "人员安排"],
                advantages=["理论完善", "求解算法成熟", "计算效率高", "结果可解释性好"],
                disadvantages=["适用范围有限", "无法处理非线性关系", "对数据质量要求高"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["目标函数系数", "约束条件系数", "约束右端项"],
                validation_methods=["敏感性分析", "参数扰动测试", "边界条件验证"],
                common_pitfalls=["约束条件遗漏", "目标函数定义错误", "单位不一致"]
            ),
            "integer_programming": ModelKnowledge(
                name="整数规划",
                category="优化",
                description="决策变量全部或部分限制为整数的线性或非线性规划问题",
                applicable_problems=["选址问题", "人员调度", "背包问题", "集合覆盖", "车辆路径规划"],
                advantages=["可处理离散决策", "适用范围广", "结果直观"],
                disadvantages=["求解困难", "计算复杂度高", "大规模问题求解难"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "数值型"},
                key_parameters=["松弛变量", "分支界参数", "求解器参数"],
                validation_methods=["分支界验证", "启发式算法验证", "小规模精确求解"],
                common_pitfalls=["整数约束遗漏", "过度约束", "数值不稳定"]
            ),
            "nonlinear_programming": ModelKnowledge(
                name="非线性规划",
                category="优化",
                description="目标函数或约束条件包含非线性项的优化问题",
                applicable_problems=["工程设计", "参数优化", "经济建模", "过程控制"],
                advantages=["适用范围广", "可处理复杂关系", "更贴近实际"],
                disadvantages=["求解困难", "易陷入局部最优", "理论分析复杂"],
                complexity="高",
                implementation_difficulty="高",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "数值型"},
                key_parameters=["初始点", "学习率", "收敛准则", "正则化参数"],
                validation_methods=["多起点优化", "梯度检验", "海森矩阵验证"],
                common_pitfalls=["初始点选择不当", "约束条件非凸", "数值不稳定"]
            ),
            "time_series_arima": ModelKnowledge(
                name="时间序列ARIMA",
                category="预测",
                description="自回归整合移动平均模型,适用于序列相关的时间序列数据",
                applicable_problems=["销售预测", "股票预测", "气象预测", "需求预测"],
                advantages=["理论完善", "计算效率高", "可处理自相关数据"],
                disadvantages=["数据要求严格", "参数选择复杂", "不适合非平稳强趋势"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "大", "data_quality": "高", "data_type": "时间序列"},
                key_parameters=["p参数", "d参数", "q参数", "季节性参数"],
                validation_methods=["AIC/BIC准则", "自相关函数分析", "残差检验"],
                common_pitfalls=["参数过多导致过拟合", "数据处理不当", "季节性识别错误"]
            ),
            "regression_linear": ModelKnowledge(
                name="线性回归",
                category="预测",
                description="建立因变量与自变量间的线性关系模型",
                applicable_problems=["价格预测", "销量预测", "风险评估", "关系分析"],
                advantages=["简单易懂", "计算快速", "结果可解释"],
                disadvantages=["假设限制多", "无法处理非线性", "对异常值敏感"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "中等", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["正则化参数lambda", "学习率", "特征缩放参数"],
                validation_methods=["R²检验", "残差分析", "多重共线性检验"],
                common_pitfalls=["特征选择不当", "共线性问题", "假设验证不充分"]
            ),
            "random_forest": ModelKnowledge(
                name="随机森林",
                category="预测/分类",
                description="集成多个决策树进行预测或分类的机器学习算法",
                applicable_problems=["特征重要性分析", "非线性预测", "分类问题", "风险评估"],
                advantages=["处理非线性能力强", "特征重要性清晰", "鲁棒性好", "易并行化"],
                disadvantages=["可解释性差", "计算复杂度高", "过拟合风险"],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={"sample_size": "大", "data_quality": "中等", "data_type": "混合型"},
                key_parameters=["树个数n_estimators", "最大深度max_depth", "最少样本数min_samples"],
                validation_methods=["交叉验证", "特征重要性分析", "OOB误差估计"],
                common_pitfalls=["参数调优不足", "数据不平衡", "特征工程不够"]
            ),
            "neural_network_mlp": ModelKnowledge(
                name="多层感知机(MLP)",
                category="预测/分类",
                description="包含多个隐层的人工神经网络,可拟合复杂非线性函数",
                applicable_problems=["复杂非线性预测", "图像识别", "模式分类", "函数逼近"],
                advantages=["表达能力强", "可学习复杂模式", "广泛适用"],
                disadvantages=["需要大量数据", "训练复杂", "可解释性差", "易过拟合"],
                complexity="高",
                implementation_difficulty="高",
                data_requirements={"sample_size": "很大", "data_quality": "高", "data_type": "数值型"},
                key_parameters=["隐层规模", "激活函数", "学习率", "正则化系数"],
                validation_methods=["交叉验证", "学习曲线分析", "梯度检验"],
                common_pitfalls=["数据不足", "过拟合严重", "参数初始化不当", "学习率设置不当"]
            ),
            "svm": ModelKnowledge(
                name="支持向量机(SVM)",
                category="分类",
                description="通过找最优超平面进行分类的机器学习算法",
                applicable_problems=["二分类问题", "多分类问题", "异常检测", "回归"],
                advantages=["理论基础扎实", "泛化能力强", "高维数据处理好"],
                disadvantages=["参数敏感", "计算复杂度高", "大数据集不适用"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "数值型"},
                key_parameters=["核函数参数C", "核函数选择", "gamma参数"],
                validation_methods=["交叉验证", "网格搜索", "核函数验证"],
                common_pitfalls=["核函数选择不当", "参数C和gamma调优不足", "特征缩放缺失"]
            ),
            "kmeans_clustering": ModelKnowledge(
                name="K-means聚类",
                category="聚类",
                description="基于质心的划分聚类算法,将数据分为K个簇",
                applicable_problems=["客户分群", "图像分割", "数据分类", "异常检测"],
                advantages=["简单高效", "可扩展性好", "易理解和实现"],
                disadvantages=["需预知K值", "易陷入局部最优", "对初值敏感"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "大", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["聚类数K", "初始化方法", "距离度量"],
                validation_methods=["肘部法则", "轮廓系数", "CH指数"],
                common_pitfalls=["K值选择困难", "初始化不当", "距离度量不合适"]
            ),
            "dbscan_clustering": ModelKnowledge(
                name="DBSCAN聚类",
                category="聚类",
                description="基于密度的聚类算法,可发现任意形状的簇",
                applicable_problems=["异常检测", "地理位置聚类", "自适应聚类", "小样本聚类"],
                advantages=["无需预知聚类数", "可发现任意形状簇", "鲁棒性好"],
                disadvantages=["参数敏感", "高维数据困难", "计算复杂度高"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "大", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["邻域半径eps", "最少邻域点数min_samples"],
                validation_methods=["轮廓系数", "DB指数", "可视化检验"],
                common_pitfalls=["参数选择困难", "高维数据失效", "密度差异大"]
            ),
            "ahp_evaluation": ModelKnowledge(
                name="层次分析法(AHP)",
                category="评价",
                description="将复杂的决策问题分解为多个层次,通过比较矩阵进行权重计算",
                applicable_problems=["多准则决策", "综合评价", "权重确定", "方案选择"],
                advantages=["逻辑清晰", "易于理解", "考虑多个准则"],
                disadvantages=["主观性强", "比较矩阵构造复杂", "一致性要求高"],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={"sample_size": "小", "data_quality": "专家评分", "data_type": "评分型"},
                key_parameters=["比较矩阵", "一致性比率", "权重向量"],
                validation_methods=["一致性检验", "敏感性分析", "权重合理性检验"],
                common_pitfalls=["比较矩阵不一致", "专家选择不当", "层次划分不合理"]
            ),
            "topsis_evaluation": ModelKnowledge(
                name="TOPSIS逼近理想解排序法",
                category="评价",
                description="通过计算各方案到理想解和负理想解的距离进行排序",
                applicable_problems=["多准则评价", "方案排序", "综合评价", "供应商选择"],
                advantages=["客观定量", "考虑正负理想解", "逻辑清晰"],
                disadvantages=["对指标归一化敏感", "未考虑指标相关性"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["权重向量", "归一化方法", "距离度量"],
                validation_methods=["权重敏感性分析", "排序稳定性检验", "与其他评价方法对比"],
                common_pitfalls=["权重确定不合理", "归一化方法选择不当", "指标相关性忽略"]
            ),
            "entropy_weight": ModelKnowledge(
                name="熵权法",
                category="评价",
                description="基于信息熵理论客观确定指标权重的方法",
                applicable_problems=["客观赋权", "综合评价", "指标筛选", "权重确定"],
                advantages=["客观赋权", "无需专家参与", "计算简单"],
                disadvantages=["忽略主观重要性", "对异常值敏感", "仅反映数据离散度"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "中等", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["信息熵", "权重系数", "归一化参数"],
                validation_methods=["权重合理性检验", "与主观权重对比", "敏感性分析"],
                common_pitfalls=["数据标准化遗漏", "零值处理不当", "权重解释不足"]
            ),
            "fuzzy_evaluation": ModelKnowledge(
                name="模糊综合评价",
                category="评价",
                description="利用模糊数学处理评价中的不确定性和模糊性",
                applicable_problems=["不确定评价", "多因素评价", "风险评估", "质量评价"],
                advantages=["处理模糊性", "适用于定性与定量混合", "灵活性强"],
                disadvantages=["隶属度函数主观", "计算复杂", "结果难以对比"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "小", "data_quality": "专家评分", "data_type": "混合型"},
                key_parameters=["隶属度函数", "评价矩阵", "权重向量", "合成算子"],
                validation_methods=["隶属度函数验证", "不同合成算子对比", "敏感性分析"],
                common_pitfalls=["隶属度函数选择不当", "因素层次划分不合理", "信息丢失"]
            ),
            "pca_analysis": ModelKnowledge(
                name="主成分分析(PCA)",
                category="降维/评价",
                description="通过正交变换将相关变量转化为少数不相关的主成分",
                applicable_problems=["数据降维", "特征提取", "多指标综合评价", "数据可视化"],
                advantages=["自动降维", "消除多重共线性", "客观性强"],
                disadvantages=["可解释性差", "信息损失", "对标准化敏感"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "中等", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["主成分个数", "累计贡献率阈值", "标准化方法"],
                validation_methods=["碎石图", "累计方差贡献率", "载荷矩阵分析"],
                common_pitfalls=["未标准化直接做PCA", "主成分个数选择不当", "过度解读主成分含义"]
            ),
            "dea_analysis": ModelKnowledge(
                name="数据包络分析(DEA)",
                category="评价",
                description="基于线性规划评价多输入多输出决策单元相对效率的方法",
                applicable_problems=["效率评价", "绩效评估", "资源配置", "技术效率分析"],
                advantages=["无需指定函数形式", "多投入多产出", "非参数方法"],
                disadvantages=["对异常值敏感", "仅评价相对效率", "维度灾难"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "数值型"},
                key_parameters=["投入指标", "产出指标", "规模报酬假设", "方向距离函数"],
                validation_methods=["超效率分析", "Malmquist指数", "敏感性分析"],
                common_pitfalls=["指标选择不当", "DMU数量不足", "规模报酬假设错误"]
            ),
            "nsga2_optimization": ModelKnowledge(
                name="NSGA-II多目标优化",
                category="优化",
                description="基于非支配排序的多目标遗传算法，求解Pareto最优解集",
                applicable_problems=["多目标优化", "工程设计", "资源调度", "选址规划"],
                advantages=["处理多目标", "获得Pareto前沿", "全局搜索能力强"],
                disadvantages=["计算量大", "参数调优复杂", "收敛性依赖问题"],
                complexity="高",
                implementation_difficulty="中",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["种群大小", "交叉概率", "变异概率", "迭代次数"],
                validation_methods=["Pareto前沿可视化", "超体积指标", "收敛性分析"],
                common_pitfalls=["种群大小不足", "编码方案不合理", "约束处理不当"]
            ),
            "simulated_annealing": ModelKnowledge(
                name="模拟退火算法",
                category="优化",
                description="模拟金属退火过程的随机搜索算法，可跳出局部最优",
                applicable_problems=["组合优化", "TSP问题", "调度问题", "参数优化"],
                advantages=["可跳出局部最优", "实现简单", "适用范围广"],
                disadvantages=["收敛慢", "参数敏感", "结果不稳定"],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["初始温度", "降温系数", "终止温度", "迭代次数"],
                validation_methods=["多次运行统计", "收敛曲线分析", "与精确解对比"],
                common_pitfalls=["初始温度过低", "降温过快", "邻域结构设计不当"]
            ),
            "particle_swarm": ModelKnowledge(
                name="粒子群优化(PSO)",
                category="优化",
                description="模拟鸟群觅食行为的群体智能优化算法",
                applicable_problems=["连续优化", "参数优化", "函数优化", "神经网络训练"],
                advantages=["实现简单", "收敛快", "参数少", "全局搜索能力"],
                disadvantages=["易早熟收敛", "维度灾难", "精度有限"],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["粒子数", "惯性权重", "学习因子c1和c2", "最大速度"],
                validation_methods=["收敛曲线", "多次运行统计", "与其他算法对比"],
                common_pitfalls=["参数设置不当", "早熟收敛", "边界处理缺失"]
            ),
            "tsp_vrp": ModelKnowledge(
                name="TSP/VRP路径优化",
                category="图论/优化",
                description="旅行商问题和车辆路径问题，求最短路径或最优路线",
                applicable_problems=["物流配送", "路径规划", "巡检路线", "快递调度"],
                advantages=["实际应用广", "模型直观", "多种求解方法"],
                disadvantages=["NP难问题", "规模受限", "约束复杂"],
                complexity="高",
                implementation_difficulty="中",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "距离矩阵"},
                key_parameters=["城市/节点数", "车辆容量", "时间窗", "距离矩阵"],
                validation_methods=["与已知最优解对比", "多算法对比", "可视化路径"],
                common_pitfalls=["问题规模估计不足", "约束遗漏", "距离计算错误"]
            ),
            "prophet_forecast": ModelKnowledge(
                name="Prophet预测模型",
                category="预测",
                description="Facebook开源的时间序列预测模型，自动处理趋势、季节性和节假日",
                applicable_problems=["业务预测", "流量预测", "销售预测", "容量规划"],
                advantages=["自动处理季节性", "对缺失值鲁棒", "可添加节假日效应", "易用"],
                disadvantages=["不适合高频数据", "对突变不敏感", "需要较长历史"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "大", "data_quality": "中等", "data_type": "时间序列"},
                key_parameters=["changepoint_prior_scale", "seasonality_prior_scale", "holidays"],
                validation_methods=["时间序列交叉验证", "MAE/RMSE评估", "残差分析"],
                common_pitfalls=["训练数据过短", "忽略外部变量", "过度拟合节假日效应"]
            ),
            "xgboost_model": ModelKnowledge(
                name="XGBoost/LightGBM",
                category="预测/分类",
                description="基于梯度提升的集成学习算法，竞赛中表现优异",
                applicable_problems=["回归预测", "分类问题", "排序问题", "特征重要性"],
                advantages=["精度高", "处理缺失值", "特征重要性", "正则化防过拟合"],
                disadvantages=["可解释性较差", "调参复杂", "对类别特征处理有限"],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={"sample_size": "大", "data_quality": "中等", "data_type": "混合型"},
                key_parameters=["learning_rate", "max_depth", "n_estimators", "subsample"],
                validation_methods=["交叉验证", "学习曲线", "特征重要性分析"],
                common_pitfalls=["过拟合", "学习率与树数量不匹配", "类别不平衡未处理"]
            ),
            "sir_seir_model": ModelKnowledge(
                name="SIR/SEIR传染病模型",
                category="仿真/微分方程",
                description="用微分方程描述传染病传播动力学的经典模型",
                applicable_problems=["传染病预测", "疫情分析", "防控策略评估", "流行病学"],
                advantages=["理论基础扎实", "参数可解释", "可分析均衡点"],
                disadvantages=["假设简化", "参数估计困难", "空间异质性忽略"],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "时间序列"},
                key_parameters=["传染率β", "恢复率γ", "潜伏期1/σ", "初始条件"],
                validation_methods=["参数敏感性分析", "与实际数据拟合", "再生数R0分析"],
                common_pitfalls=["参数估计偏差", "忽略人口流动", "假设均匀混合"]
            ),
            "grey_relational": ModelKnowledge(
                name="灰色关联分析",
                category="评价/分析",
                description="通过灰色关联度衡量因素间关联程度的分析方法",
                applicable_problems=["因素分析", "系统评价", "影响因素排序", "小样本分析"],
                advantages=["小样本适用", "计算简单", "不要求特定分布"],
                disadvantages=["分辨系数主观", "对参考序列敏感", "理论基础薄弱"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["分辨系数ρ", "参考序列", "数据标准化方法"],
                validation_methods=["分辨系数敏感性分析", "与其他方法对比", "排序稳定性"],
                common_pitfalls=["分辨系数选择不当", "数据未标准化", "参考序列选择不合理"]
            ),
            "hypothesis_testing": ModelKnowledge(
                name="假设检验",
                category="统计",
                description="基于样本数据对总体参数或分布进行统计推断的方法",
                applicable_problems=["显著性检验", "A/B测试", "质量控制", "方差分析"],
                advantages=["理论严密", "结论可靠", "广泛适用"],
                disadvantages=["样本量依赖", "假设条件严格", "p值误用风险"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"sample_size": "中等", "data_quality": "高", "data_type": "数值型"},
                key_parameters=["显著性水平α", "检验统计量", "自由度", "效应量"],
                validation_methods=["功效分析", "效应量计算", "置信区间"],
                common_pitfalls=["p值与实际意义混淆", "多重比较校正缺失", "正态性假设未验证"]
            ),
            "bayesian_inference": ModelKnowledge(
                name="贝叶斯推断",
                category="统计",
                description="基于贝叶斯定理结合先验知识和样本信息进行概率推断",
                applicable_problems=["参数估计", "模型选择", "不确定性量化", "小样本推断"],
                advantages=["融合先验知识", "处理不确定性", "小样本可用", "提供完整后验分布"],
                disadvantages=["先验选择主观", "计算复杂", "MCMC收敛慢"],
                complexity="高",
                implementation_difficulty="高",
                data_requirements={"sample_size": "小", "data_quality": "中等", "data_type": "数值型"},
                key_parameters=["先验分布", "似然函数", "MCMC采样参数", "收敛诊断"],
                validation_methods=["后验预测检验", "交叉验证", "DIC/WAIC模型比较"],
                common_pitfalls=["先验过于主观", "MCMC未收敛", "后验诊断不充分"]
            ),
            "grey_prediction": ModelKnowledge(
                name="灰色预测GM(1,1)",
                category="预测",
                description="基于灰色系统理论的小样本预测方法，适用于数据量少且序列具有指数增长趋势的场景",
                applicable_problems=["小样本预测", "趋势预测", "灰色系统", "短期预测", "能源预测", "产量预测"],
                advantages=["所需数据量极少(4个即可)", "计算简单", "短期预测精度高"],
                disadvantages=["仅适用于指数增长趋势", "长期预测误差大", "对波动数据效果差"],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={"minimum_samples": "4-10个数据点", "data_type": "等间隔时间序列"},
                key_parameters=["发展系数a", "灰色作用量b"],
                validation_methods=["后验差检验", "关联度检验", "残差检验"],
                common_pitfalls=["数据量不足4个", "数据非等间隔", "数据波动过大", "忽略后验差检验"],
                implementation_steps=[
                    "数据预处理和累加生成(AGO)",
                    "构建灰色微分方程",
                    "最小二乘法求解参数a和b",
                    "建立时间响应预测模型",
                    "累减还原得到预测值",
                    "残差检验和后验差检验",
                ],
                related_models=["灰色关联分析", "时间序列ARIMA", "指数平滑"],
            ),
            "lstm_network": ModelKnowledge(
                name="LSTM长短期记忆网络",
                category="预测",
                description="一种特殊的循环神经网络(RNN)，通过门控机制有效捕获长期时序依赖关系，是深度学习时序预测的主流方法",
                applicable_problems=[
                    "时序预测", "长期依赖建模", "股价预测", "气象预测",
                    "自然语言处理", "流量预测", "负荷预测", "深度学习预测",
                ],
                advantages=[
                    "捕获长期依赖关系", "自动特征提取", "处理变长序列",
                    "非线性拟合能力强", "支持多变量输入",
                ],
                disadvantages=[
                    "需要大量训练数据", "训练时间长", "超参数多且调优复杂",
                    "可解释性差", "容易过拟合",
                ],
                complexity="高",
                implementation_difficulty="高",
                data_requirements={
                    "minimum_samples": "1000+数据点",
                    "data_type": "时间序列或序列数据",
                    "data_quality": "高",
                },
                key_parameters=[
                    "隐藏层单元数", "层数", "学习率", "batch_size",
                    "时间窗口大小", "dropout率", "epochs",
                ],
                validation_methods=["时间序列交叉验证", "MAE/RMSE评估", "学习曲线分析", "预测可视化"],
                common_pitfalls=[
                    "训练数据不足导致欠拟合", "时间窗口大小选择不当",
                    "未进行数据归一化", "过拟合未使用dropout",
                    "batch_size与学习率不匹配",
                ],
                implementation_steps=[
                    "数据预处理与归一化",
                    "构造滑动窗口样本(X, y)",
                    "划分训练集/验证集/测试集(按时间顺序)",
                    "设计LSTM网络结构(层数、单元数)",
                    "编译模型(优化器、损失函数)",
                    "训练模型并监控验证损失(Early Stopping)",
                    "反归一化预测结果并评估",
                ],
                related_models=["GRU", "Transformer", "时间序列ARIMA", "多层感知机(MLP)"],
            ),
            "game_theory": ModelKnowledge(
                name="博弈论(Nash均衡)",
                category="优化/决策",
                description="研究多个理性决策主体之间策略互动的数学理论，通过Nash均衡分析各方最优策略选择",
                applicable_problems=[
                    "策略决策", "竞争分析", "定价策略", "资源争夺",
                    "合作与竞争", "拍卖设计", "机制设计", "囚徒困境",
                ],
                advantages=[
                    "刻画多方互动决策", "理论基础深厚", "结论具有战略指导意义",
                    "可分析合作与非合作场景",
                ],
                disadvantages=[
                    "理性人假设过强", "均衡可能不唯一", "信息完全假设不现实",
                    "复杂博弈求解困难",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "无固定要求",
                    "data_type": "策略集合与收益矩阵",
                    "data_quality": "需准确的收益估计",
                },
                key_parameters=["参与者集合", "策略空间", "收益函数(支付矩阵)", "信息结构"],
                validation_methods=["Nash均衡存在性验证", "策略稳定性分析", "敏感性分析", "仿真模拟"],
                common_pitfalls=[
                    "收益矩阵构造不合理", "忽略混合策略均衡",
                    "多重均衡选择困难", "理性假设与实际偏差大",
                ],
                implementation_steps=[
                    "识别博弈参与者和策略空间",
                    "构建收益矩阵(支付矩阵)",
                    "判断博弈类型(合作/非合作、完全/不完全信息)",
                    "求解Nash均衡(纯策略和混合策略)",
                    "分析均衡的稳定性和唯一性",
                    "讨论策略选择的实际含义",
                ],
                related_models=["线性规划", "多目标优化", "马尔可夫决策过程"],
            ),
            "queuing_theory": ModelKnowledge(
                name="排队论(M/M/1等)",
                category="优化/仿真",
                description="研究服务系统中排队等待现象的数学理论，用于分析和优化服务系统的效率和资源配置",
                applicable_problems=[
                    "服务系统优化", "窗口设置", "交通流量", "呼叫中心",
                    "医院排队", "银行排队", "生产线优化", "网络拥塞",
                ],
                advantages=[
                    "理论成熟完善", "有解析解", "直接给出运营指标",
                    "参数含义直观",
                ],
                disadvantages=[
                    "对到达和服务分布假设严格", "复杂系统难以解析求解",
                    "多服务台/多队列分析复杂",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "需统计到达率和服务率",
                    "data_type": "到达时间间隔、服务时间",
                    "data_quality": "需要分布拟合检验",
                },
                key_parameters=["到达率λ", "服务率μ", "服务台数c", "系统容量K", "排队规则"],
                validation_methods=["利用率检验(ρ<1)", "Little公式验证", "仿真对比", "拟合优度检验"],
                common_pitfalls=[
                    "到达过程非泊松但强行假设", "忽略系统容量限制",
                    "服务率估计不准确", "未验证稳态条件(ρ<1)",
                ],
                implementation_steps=[
                    "收集到达间隔和服务时间数据",
                    "拟合到达过程和服务时间分布",
                    "确定排队模型类型(M/M/1, M/M/c, M/G/1等)",
                    "计算系统性能指标(Lq, Wq, Ls, Ws, ρ)",
                    "利用Little公式进行交叉验证",
                    "优化服务台数量或服务策略",
                ],
                related_models=["马尔可夫链", "仿真模拟", "线性规划"],
            ),
            "markov_chain": ModelKnowledge(
                name="马尔可夫链",
                category="随机过程/预测",
                description="具有无记忆性的随机过程模型，当前状态仅依赖于前一状态，广泛用于状态转移分析和长期趋势预测",
                applicable_problems=[
                    "状态转移", "市场份额预测", "品牌转换", "天气预测",
                    "人口迁移", "设备状态监测", "随机过程建模", "长期均衡分析",
                ],
                advantages=[
                    "数学基础严谨", "可计算稳态分布", "模型直观易懂",
                    "可分析长期行为趋势",
                ],
                disadvantages=[
                    "无记忆性假设限制适用范围", "转移概率估计需要大量数据",
                    "状态空间过大时计算困难",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "需足够的状态转移观测",
                    "data_type": "状态转移序列",
                    "data_quality": "需准确的转移频次统计",
                },
                key_parameters=["状态空间", "转移概率矩阵P", "初始状态分布π₀"],
                validation_methods=[
                    "Chapman-Kolmogorov方程验证", "稳态分布收敛检验",
                    "马尔可夫性检验(卡方检验)", "仿真对比",
                ],
                common_pitfalls=[
                    "马尔可夫性假设不成立", "状态空间划分不合理",
                    "转移概率矩阵非随机矩阵", "忽略吸收态的影响",
                ],
                implementation_steps=[
                    "定义状态空间和状态划分",
                    "统计状态转移频次",
                    "估计转移概率矩阵",
                    "验证马尔可夫性(独立性检验)",
                    "计算n步转移概率",
                    "求解稳态分布(若存在)",
                    "分析和解释长期行为",
                ],
                related_models=["排队论", "隐马尔可夫模型(HMM)", "随机游走", "SIR/SEIR传染病模型"],
            ),
            "spline_interpolation": ModelKnowledge(
                name="样条插值",
                category="数据拟合",
                description="使用分段多项式函数对离散数据点进行光滑插值，保证在节点处的连续性和光滑性",
                applicable_problems=[
                    "数据拟合", "曲线平滑", "数据补全", "函数逼近",
                    "地形建模", "图像处理", "信号重建", "缺失值插补",
                ],
                advantages=[
                    "拟合精度高", "曲线光滑无震荡", "局部修改不影响全局",
                    "避免龙格现象",
                ],
                disadvantages=[
                    "外推能力差", "边界条件选择影响结果",
                    "对噪声数据过度拟合", "不适合大间隔外推",
                ],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "≥3个数据点",
                    "data_type": "离散数据点(x, y)",
                    "data_quality": "数据需基本可靠，异常值需提前处理",
                },
                key_parameters=["插值节点", "样条阶数(通常三次)", "边界条件类型", "平滑因子(平滑样条)"],
                validation_methods=["残差分析", "留一交叉验证", "光滑度检查", "与原始数据对比可视化"],
                common_pitfalls=[
                    "将插值误用为外推", "数据含噪声时过拟合",
                    "边界条件选择不当导致端点异常", "节点分布不均匀",
                ],
                implementation_steps=[
                    "整理数据点并按自变量排序",
                    "检查数据质量(去除异常值)",
                    "选择样条类型(线性/三次/B样条)",
                    "确定边界条件(自然/固支/周期)",
                    "求解样条系数",
                    "生成插值曲线并可视化",
                    "评估拟合质量(残差分析)",
                ],
                related_models=["多项式拟合", "线性回归", "核回归", "高斯过程回归"],
            ),
            "vikor_evaluation": ModelKnowledge(
                name="VIKOR多准则决策",
                category="评价",
                description="基于理想解折衷排序的多准则决策方法，寻找最接近理想解的折衷方案，兼顾群体效用最大和个体遗憾最小",
                applicable_problems=[
                    "多准则决策", "方案排序", "折衷方案选择", "供应商选择",
                    "项目评估", "选址决策", "综合评价", "风险评估",
                ],
                advantages=[
                    "兼顾群体效用和个体遗憾", "提供折衷解", "排序稳定性好",
                    "可调节决策机制权重",
                ],
                disadvantages=[
                    "权重确定仍有主观性", "对归一化方式敏感",
                    "决策机制系数v选择缺乏统一标准",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "≥2个备选方案",
                    "data_type": "多指标评价矩阵",
                    "data_quality": "中等",
                },
                key_parameters=["权重向量", "决策机制系数v(通常0.5)", "理想解f*", "负理想解f-"],
                validation_methods=[
                    "可接受优势条件检验", "可接受稳定性条件检验",
                    "权重敏感性分析", "与TOPSIS结果对比",
                ],
                common_pitfalls=[
                    "忽略可接受优势和稳定性条件检验", "v值选取随意",
                    "指标方向(成本/收益)未统一处理", "权重确定不合理",
                ],
                implementation_steps=[
                    "构建多属性决策矩阵",
                    "确定各指标权重(熵权法/AHP等)",
                    "确定正理想解f*和负理想解f-",
                    "计算群体效用值S和个体遗憾值R",
                    "计算综合排序指标Q",
                    "检验可接受优势条件和可接受稳定性条件",
                    "输出折衷排序结果",
                ],
                related_models=["TOPSIS", "AHP", "熵权法", "PROMETHEE"],
            ),
            "logistic_regression": ModelKnowledge(
                name="逻辑回归",
                category="分类",
                description="基于Sigmoid函数的广义线性模型，用于二分类问题，输出概率值并通过阈值判定类别",
                applicable_problems=[
                    "二分类", "风险预测", "信用评分", "疾病诊断",
                    "客户流失预测", "违约概率", "事件发生概率", "因素影响分析",
                ],
                advantages=[
                    "输出概率可解释", "计算效率高", "不易过拟合",
                    "系数可解释为各因素的影响程度", "理论基础扎实",
                ],
                disadvantages=[
                    "仅适用于线性可分问题", "对多重共线性敏感",
                    "处理非线性关系能力有限", "多分类需要扩展",
                ],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "每个类别≥50个样本",
                    "data_type": "数值型/编码后的类别型",
                    "data_quality": "中等",
                },
                key_parameters=["正则化参数C", "正则化类型(L1/L2)", "分类阈值", "最大迭代次数"],
                validation_methods=[
                    "混淆矩阵", "ROC曲线和AUC", "Hosmer-Lemeshow检验",
                    "交叉验证", "系数显著性检验",
                ],
                common_pitfalls=[
                    "特征共线性导致系数不稳定", "类别不平衡未处理",
                    "阈值选择不当", "忽略特征交互项",
                    "将概率结果直接作为分类结果而未设定合理阈值",
                ],
                implementation_steps=[
                    "数据预处理(编码、缺失值、标准化)",
                    "特征选择与多重共线性检验(VIF)",
                    "划分训练集与测试集",
                    "训练逻辑回归模型",
                    "系数分析与显著性检验",
                    "选择最优分类阈值(ROC曲线)",
                    "模型评估(混淆矩阵、AUC等)",
                ],
                related_models=["线性回归", "支持向量机(SVM)", "决策树", "朴素贝叶斯"],
            ),
            "decision_tree": ModelKnowledge(
                name="决策树",
                category="分类/回归",
                description="通过递归划分特征空间构建树形结构进行分类或回归，模型可解释性极强",
                applicable_problems=[
                    "分类问题", "回归问题", "决策规则提取", "风险评估",
                    "客户分群", "故障诊断", "特征重要性分析", "医学诊断",
                ],
                advantages=[
                    "可解释性强(可视化决策规则)", "无需特征缩放",
                    "可处理混合类型数据", "自动进行特征选择",
                ],
                disadvantages=[
                    "容易过拟合", "对数据变化敏感(不稳定)",
                    "难以处理连续型目标(阶梯状预测)", "存在偏向多值属性的问题",
                ],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "≥100个样本",
                    "data_type": "数值型或类别型",
                    "data_quality": "中等",
                },
                key_parameters=[
                    "最大深度max_depth", "最小分裂样本数min_samples_split",
                    "分裂准则(gini/entropy/mse)", "最大叶子节点数",
                ],
                validation_methods=[
                    "交叉验证", "剪枝效果评估", "特征重要性分析",
                    "混淆矩阵", "决策树可视化",
                ],
                common_pitfalls=[
                    "未剪枝导致严重过拟合", "树过深失去可解释性",
                    "类别不平衡导致偏向多数类", "忽略预剪枝/后剪枝",
                ],
                implementation_steps=[
                    "数据预处理(编码类别变量、处理缺失值)",
                    "划分训练集与测试集",
                    "选择分裂准则(Gini/信息增益/MSE)",
                    "训练决策树模型",
                    "可视化决策树结构",
                    "剪枝优化(预剪枝或后剪枝/代价复杂度剪枝)",
                    "模型评估与特征重要性分析",
                ],
                related_models=["随机森林", "XGBoost/LightGBM", "逻辑回归", "规则学习"],
            ),
            "monte_carlo_simulation": ModelKnowledge(
                name="蒙特卡洛模拟",
                category="仿真/优化",
                description="通过大量随机抽样和统计分析来近似求解数学和物理问题的数值方法，适用于不确定性分析和复杂系统仿真",
                applicable_problems=[
                    "风险评估", "随机过程模拟", "数值积分", "不确定性量化",
                    "金融定价", "可靠性分析", "供应链模拟", "排队系统仿真",
                    "决策分析", "项目管理风险",
                ],
                advantages=[
                    "处理高维问题能力强", "适合不确定性建模",
                    "无需解析解即可求解", "可模拟复杂随机系统",
                    "实现相对简单",
                ],
                disadvantages=[
                    "计算量大、耗时长", "收敛速度慢(O(1/√N))",
                    "结果具有随机性", "方差控制困难",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "无固定要求，需定义概率分布",
                    "data_type": "概率分布参数或历史数据",
                    "data_quality": "需准确的分布假设或充分的历史数据",
                },
                key_parameters=["模拟次数(通常≥10000)", "随机种子", "采样方法(简单/分层/重要性采样)", "概率分布类型"],
                validation_methods=["收敛性分析", "方差估计", "置信区间计算", "与解析解对比(简单情形)", "敏感性分析"],
                common_pitfalls=[
                    "模拟次数不足导致结果不稳定", "随机数生成器质量差",
                    "方差过大未采用方差缩减技术", "概率分布假设不合理",
                    "忽略相关性结构",
                ],
                implementation_steps=[
                    "明确问题和目标变量",
                    "确定输入变量的概率分布",
                    "生成随机样本(伪随机数)",
                    "对每个样本执行确定性计算",
                    "收集输出结果并统计分析",
                    "计算均值、方差和置信区间",
                    "进行收敛性检验和敏感性分析",
                ],
                related_models=["贝叶斯推断", "排队论", "马尔可夫链", "模拟退火算法"],
            ),
            "cellular_automata": ModelKnowledge(
                name="元胞自动机",
                category="仿真",
                description="由离散的空间网格、有限状态集和局部演化规则组成的动力学模型，通过简单的局部规则产生复杂的全局涌现行为",
                applicable_problems=[
                    "交通流模拟", "森林火灾蔓延", "城市扩张模拟", "生态系统模拟",
                    "人群疏散", "传染病空间传播", "晶体生长", "沙堆模型",
                ],
                advantages=[
                    "能描述复杂系统的涌现行为", "规则直观易于理解",
                    "可视化效果好", "并行计算效率高",
                    "适合空间动态过程建模",
                ],
                disadvantages=[
                    "演化规则设定依赖经验", "难以严格数学验证",
                    "参数标定困难", "对初始条件和边界条件敏感",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "需定义网格和初始状态",
                    "data_type": "空间网格数据、状态转移规则",
                    "data_quality": "规则需要领域知识支撑",
                },
                key_parameters=["网格大小和维度", "邻域类型(Von Neumann/Moore)", "演化规则集", "边界条件(周期/固定/开放)", "时间步数"],
                validation_methods=["与实际数据对比", "参数敏感性分析", "统计特征分析", "可视化动画检验", "简化情形解析验证"],
                common_pitfalls=[
                    "规则设计过于简单无法反映实际", "网格大小不足产生边界效应",
                    "邻域类型选择不当", "忽略随机性(确定性CA过于理想化)",
                    "演化步数不足未达到稳态",
                ],
                implementation_steps=[
                    "定义网格空间(大小、维度、边界条件)",
                    "确定元胞状态集合",
                    "设计邻域类型和演化规则",
                    "初始化网格状态",
                    "迭代执行演化规则",
                    "可视化演化过程(动画或快照)",
                    "统计分析宏观特征(密度、聚集度等)",
                    "参数敏感性分析和规则验证",
                ],
                related_models=["SIR/SEIR传染病模型", "蒙特卡洛模拟", "Agent-Based Model"],
            ),
            "hierarchical_clustering": ModelKnowledge(
                name="层次聚类",
                category="聚类",
                description="通过逐步合并(凝聚式)或分裂(分裂式)的方式构建聚类层次结构，结果以树状图(dendrogram)形式展现",
                applicable_problems=[
                    "分类层次结构发现", "谱系图生成", "基因表达分析",
                    "文档聚类", "市场细分", "物种分类", "社交网络社区发现",
                ],
                advantages=[
                    "不需要预设聚类数K", "可生成直观的树状图(dendrogram)",
                    "能揭示数据的层次结构", "适合小中型数据集",
                    "可在不同粒度切割获得不同聚类方案",
                ],
                disadvantages=[
                    "计算复杂度高O(n^2)至O(n^3)", "不适合大规模数据集",
                    "合并/分裂操作不可撤销", "对噪声和异常值敏感",
                ],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "≥10个样本",
                    "data_type": "数值型或距离矩阵",
                    "data_quality": "中等，需处理异常值",
                },
                key_parameters=["链接方法(ward/complete/average/single)", "距离度量(欧氏/曼哈顿/余弦)", "切割阈值或聚类数", "标准化方法"],
                validation_methods=["树状图可视化分析", "轮廓系数", "Cophenetic相关系数", "与K-means结果对比", "不同链接方法对比"],
                common_pitfalls=[
                    "链接方法选择不当(single linkage链式效应)", "未对数据标准化",
                    "切割位置选择不合理", "数据量过大导致内存不足",
                    "忽略Cophenetic相关系数验证",
                ],
                implementation_steps=[
                    "数据预处理与标准化",
                    "选择距离度量方式",
                    "选择链接方法(推荐Ward法)",
                    "执行凝聚式层次聚类",
                    "绘制树状图(dendrogram)",
                    "根据树状图或指标确定切割位置",
                    "分析各聚类的特征和含义",
                    "与其他聚类方法对比验证",
                ],
                related_models=["K-means聚类", "DBSCAN聚类", "主成分分析(PCA)", "高斯混合模型"],
            ),
            "exponential_smoothing": ModelKnowledge(
                name="指数平滑",
                category="预测",
                description="通过对历史观测值赋予指数递减权重进行时间序列预测的方法，包括简单指数平滑(SES)、Holt线性趋势法和Holt-Winters季节性方法",
                applicable_problems=[
                    "短期时间序列预测", "需求预测", "销售预测",
                    "库存管理", "趋势和季节性分析", "负荷预测",
                    "生产计划", "财务预测",
                ],
                advantages=[
                    "模型简单直观", "短期预测效果好",
                    "参数少且易于调优", "计算效率高",
                    "可自适应处理趋势和季节性",
                ],
                disadvantages=[
                    "长期预测效果差", "无法处理复杂非线性模式",
                    "对突变和结构变化敏感", "理论基础不如ARIMA完备",
                ],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "≥2个完整季节周期(有季节性时)",
                    "data_type": "等间隔时间序列",
                    "data_quality": "中等",
                },
                key_parameters=["平滑系数alpha(水平)", "平滑系数beta(趋势)", "平滑系数gamma(季节性)", "趋势类型(加法/乘法/阻尼)", "季节周期长度"],
                validation_methods=["时间序列交叉验证", "MAE/RMSE/MAPE评估", "残差分析", "AIC/BIC模型选择", "预测区间检验"],
                common_pitfalls=[
                    "平滑系数选择不当(过大过拟合、过小反应迟缓)",
                    "季节周期识别错误", "未区分加法和乘法季节性",
                    "对非平稳序列直接使用简单指数平滑",
                    "忽略阻尼趋势导致长期预测发散",
                ],
                implementation_steps=[
                    "数据探索与可视化(趋势、季节性识别)",
                    "选择指数平滑类型(SES/Holt/Holt-Winters)",
                    "确定季节性类型(加法/乘法)和周期",
                    "参数初始化和优化(最小化MSE)",
                    "模型拟合与诊断",
                    "生成预测值和预测区间",
                    "与ARIMA等模型对比评估",
                ],
                related_models=["时间序列ARIMA", "Prophet预测模型", "灰色预测GM(1,1)", "LSTM长短期记忆网络"],
            ),
            "multiple_regression": ModelKnowledge(
                name="多元回归分析",
                category="预测/统计",
                description="建立一个因变量与多个自变量之间线性或非线性关系的统计模型，用于多因素因果分析和变量关系量化",
                applicable_problems=[
                    "多因素因果分析", "变量关系量化", "影响因素识别",
                    "经济预测", "社会指标分析", "医学研究",
                    "环境因素分析", "房价预测",
                ],
                advantages=[
                    "可解释性强(系数直接反映影响程度)", "理论基础扎实",
                    "可进行统计推断和假设检验", "可量化各因素的贡献度",
                    "模型诊断方法完善",
                ],
                disadvantages=[
                    "对正态性、同方差性等假设要求严格",
                    "多重共线性影响系数稳定性",
                    "无法捕捉复杂非线性关系", "对异常值敏感",
                ],
                complexity="低",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "样本量≥自变量数的10-20倍",
                    "data_type": "数值型(类别变量需哑变量编码)",
                    "data_quality": "高，需满足回归假设",
                },
                key_parameters=["自变量选择(逐步/全子集/LASSO)", "VIF阈值(通常<10)", "显著性水平alpha", "正则化参数(Ridge/LASSO)"],
                validation_methods=[
                    "R^2和调整R^2", "F检验(整体显著性)", "t检验(各系数显著性)",
                    "残差分析(正态性、同方差性、独立性)", "多重共线性检验(VIF)",
                    "交叉验证",
                ],
                common_pitfalls=[
                    "多重共线性导致系数符号异常", "残差假设未验证",
                    "变量选择不当(遗漏重要变量或引入无关变量)",
                    "混淆相关性与因果性", "样本量不足导致过拟合",
                    "忽略交互效应和非线性项",
                ],
                implementation_steps=[
                    "数据探索与相关性分析",
                    "自变量筛选与多重共线性检验(VIF)",
                    "建立回归模型(OLS/正则化)",
                    "系数显著性检验(t检验、F检验)",
                    "残差诊断(正态性、同方差性、独立性)",
                    "模型优化(变量选择、交互项、变换)",
                    "模型评估与预测",
                ],
                related_models=["线性回归", "逻辑回归", "岭回归(Ridge)", "LASSO回归", "主成分分析(PCA)"],
            ),
            "shortest_path": ModelKnowledge(
                name="Dijkstra/Floyd最短路径",
                category="图论",
                description="经典的图论最短路径算法。Dijkstra求单源最短路径(非负权)，Floyd-Warshall求所有点对间最短路径，广泛用于路径规划和网络优化",
                applicable_problems=[
                    "路径规划", "网络优化", "物流配送", "交通导航",
                    "通信网络", "管道布局", "应急救援路线", "社交网络分析",
                ],
                advantages=[
                    "保证找到最优解", "算法成熟且实现简单",
                    "理论时间复杂度明确", "适用场景广泛",
                ],
                disadvantages=[
                    "Dijkstra不支持负权边", "Floyd时间复杂度O(n^3)不适合大规模图",
                    "仅考虑静态图(动态变化需重新计算)", "大规模网络内存消耗大",
                ],
                complexity="中",
                implementation_difficulty="低",
                data_requirements={
                    "minimum_samples": "需完整的图结构(邻接矩阵或邻接表)",
                    "data_type": "图结构(节点、边、权重)",
                    "data_quality": "权重需准确定义",
                },
                key_parameters=["图的表示方式(邻接矩阵/邻接表)", "边权重定义(距离/时间/费用)", "起点和终点", "算法选择(Dijkstra/Floyd/Bellman-Ford)"],
                validation_methods=["路径可行性检验", "与其他算法结果对比", "路径可视化", "极端情形测试", "实际数据验证"],
                common_pitfalls=[
                    "Dijkstra用于含负权边的图(应使用Bellman-Ford)",
                    "图的构建遗漏边或节点", "权重定义与实际问题不一致",
                    "大规模图未使用优先队列优化Dijkstra",
                    "混淆有向图与无向图",
                ],
                implementation_steps=[
                    "构建图模型(确定节点、边和权重)",
                    "选择合适的算法(单源/多源、有无负权)",
                    "初始化距离数组和前驱节点",
                    "执行最短路径算法",
                    "回溯提取最短路径",
                    "可视化路径结果",
                    "进行敏感性分析(权重变化对路径的影响)",
                ],
                related_models=["TSP/VRP路径优化", "最小生成树(Prim/Kruskal)", "网络流", "整数规划"],
            ),
            "genetic_algorithm": ModelKnowledge(
                name="遗传算法",
                category="优化",
                description="模拟自然选择和遗传机制的全局随机搜索优化算法，通过选择、交叉、变异等遗传操作在解空间中迭代进化寻找最优解",
                applicable_problems=[
                    "组合优化", "NP-hard问题", "多目标优化", "参数优化",
                    "调度问题", "函数优化", "路径规划", "工程设计优化",
                    "特征选择", "神经网络结构搜索",
                ],
                advantages=[
                    "全局搜索能力强", "适用范围广(无需目标函数可微)",
                    "天然支持并行计算", "可处理离散和连续变量",
                    "鲁棒性好、通用性强",
                ],
                disadvantages=[
                    "参数(种群、交叉率、变异率)敏感", "易早熟收敛",
                    "计算量大、收敛速度慢", "最优解不保证",
                    "编码方案设计困难",
                ],
                complexity="中",
                implementation_difficulty="中",
                data_requirements={
                    "minimum_samples": "无固定要求，需定义适应度函数",
                    "data_type": "目标函数和约束条件",
                    "data_quality": "适应度函数需准确反映优化目标",
                },
                key_parameters=["种群大小(通常50-200)", "交叉率(通常0.6-0.9)", "变异率(通常0.01-0.1)", "选择策略(轮盘赌/锦标赛)", "最大迭代代数", "编码方式(二进制/实数/排列)"],
                validation_methods=["收敛曲线分析", "多次独立运行统计", "与精确解或已知最优解对比", "参数敏感性分析", "与其他启发式算法对比"],
                common_pitfalls=[
                    "种群规模过小导致多样性不足", "交叉率和变异率设置不当",
                    "早熟收敛(精英策略过强)", "编码方案不合理产生大量不可行解",
                    "适应度函数设计不当", "终止条件设置不合理",
                ],
                implementation_steps=[
                    "问题分析与编码方案设计",
                    "定义适应度函数(含约束惩罚)",
                    "初始化种群(随机或启发式)",
                    "选择操作(轮盘赌/锦标赛选择)",
                    "交叉操作(单点/双点/均匀交叉)",
                    "变异操作(位翻转/高斯变异)",
                    "精英保留策略",
                    "终止条件判断(代数/收敛/时间)",
                    "结果分析与可视化",
                ],
                related_models=["NSGA-II多目标优化", "粒子群优化(PSO)", "模拟退火算法", "差分进化"],
            ),
        }

    def _initialize_metrics(self) -> Dict[str, EvaluationMetricKnowledge]:
        """初始化评价指标知识库"""
        return {
            "rmse": EvaluationMetricKnowledge(
                name="均方根误差(RMSE)",
                metric_type="回归",
                description="预测值与真实值差的平方和平均后再开方",
                formula="√(Σ(y_pred - y_true)² / n)",
                interpretation="值越小,预测精度越高,与数据单位一致",
                range="0到∞",
                when_to_use=["回归问题", "预测精度评估", "模型对比"],
                advantages=["单位与原数据一致", "对大误差敏感", "易于优化"],
                limitations=["对异常值敏感", "难以在不同数据集间对比"],
                related_metrics=["MAE", "MAPE", "R²"]
            ),
            "mae": EvaluationMetricKnowledge(
                name="平均绝对误差(MAE)",
                metric_type="回归",
                description="预测值与真实值绝对差的平均值",
                formula="Σ|y_pred - y_true| / n",
                interpretation="值越小,预测准确度越高",
                range="0到∞",
                when_to_use=["回归问题", "预测精度评估", "稳健性分析"],
                advantages=["简单直观", "对异常值鲁棒", "易解释"],
                limitations=["不可导", "难以优化", "不区分高估/低估"],
                related_metrics=["RMSE", "MAPE", "R²"]
            ),
            "r_squared": EvaluationMetricKnowledge(
                name="决定系数(R²)",
                metric_type="回归",
                description="模型解释的方差占总方差的比例",
                formula="1 - Σ(y_pred - y_true)² / Σ(y_mean - y_true)²",
                interpretation="值越接近1,模型拟合越好,表示解释力强",
                range="0到1(或负数,表示模型很差)",
                when_to_use=["回归模型评估", "模型对比", "拟合优度判断"],
                advantages=["无量纲", "易于在不同数据集对比", "意义清晰"],
                limitations=["特征增加会提高R²", "不能表示预测精度"],
                related_metrics=["调整R²", "RMSE", "MAE"]
            ),
            "accuracy": EvaluationMetricKnowledge(
                name="准确率(Accuracy)",
                metric_type="分类",
                description="分类正确的样本数占总样本数的比例",
                formula="Σ(y_pred = y_true) / n",
                interpretation="值越接近1,分类准确度越高",
                range="0到1",
                when_to_use=["分类问题", "不均衡数据较少时", "快速评估"],
                advantages=["简单直观", "易于计算", "通俗易懂"],
                limitations=["不平衡数据时误导", "不区分误差类型"],
                related_metrics=["Precision", "Recall", "F1-Score"]
            ),
            "f1_score": EvaluationMetricKnowledge(
                name="F1分数",
                metric_type="分类",
                description="精确率和召回率的调和平均数",
                formula="2 × Precision × Recall / (Precision + Recall)",
                interpretation="值越接近1,模型越好;综合考虑精确率和召回率",
                range="0到1",
                when_to_use=["不平衡分类", "需要权衡精确率和召回率", "多分类问题"],
                advantages=["综合指标", "处理不平衡好", "健壮性好"],
                limitations=["计算较复杂", "难以直观理解"],
                related_metrics=["Precision", "Recall", "AUC-ROC"]
            ),
            "auc_roc": EvaluationMetricKnowledge(
                name="AUC-ROC",
                metric_type="分类",
                description="ROC曲线下的面积,表示模型区分正负样本的能力",
                formula="ROC曲线积分",
                interpretation="值越接近1,模型区分能力越强;0.5表示随机分类",
                range="0到1",
                when_to_use=["二分类问题", "不平衡数据", "模型对比"],
                advantages=["不受类别比例影响", "综合性能评估", "可处理概率输出"],
                limitations=["多分类不适用", "计算复杂"],
                related_metrics=["精确率", "召回率", "F1-Score"]
            ),
            "silhouette_score": EvaluationMetricKnowledge(
                name="轮廓系数(Silhouette Score)",
                metric_type="聚类",
                description="衡量样本与其所在簇的相似度,与其他簇的距离对比",
                formula="(b-a)/max(a,b)",
                interpretation="值越接近1,样本聚类越好;负值表示可能聚类错误",
                range="-1到1",
                when_to_use=["聚类结果评估", "K值确定", "聚类质量评判"],
                advantages=["直观清晰", "无需真实标签", "考虑类间类内距离"],
                limitations=["计算复杂度高", "对初始化敏感"],
                related_metrics=["Davies-Bouldin", "Calinski-Harabasz"]
            ),
            "mape": EvaluationMetricKnowledge(
                name="平均绝对百分比误差(MAPE)",
                metric_type="回归",
                description="预测值与真实值的绝对百分比误差平均值",
                formula="Σ|y_pred - y_true| / |y_true| × 100%",
                interpretation="值越小,预测精度越高,表示平均偏差百分比",
                range="0到∞",
                when_to_use=["回归预测评估", "不同量级数据对比", "百分比误差关注"],
                advantages=["无量纲", "易解释", "适合对比不同量级"],
                limitations=["真实值为零时无意义", "对小值过度敏感"],
                related_metrics=["MAE", "RMSE", "R²"]
            ),
            "optimality_gap": EvaluationMetricKnowledge(
                name="最优性间隙(Optimality Gap)",
                metric_type="优化",
                description="当前解与已知最优解（或下界）之间的差距百分比",
                formula="(当前解 - 最优下界) / |最优下界| × 100%",
                interpretation="值越小,解越接近最优;0%表示已找到最优解",
                range="0到∞",
                when_to_use=["优化问题求解质量", "启发式算法评估", "求解器性能对比"],
                advantages=["直观衡量解的质量", "适合优化问题", "可比较不同算法"],
                limitations=["需要已知最优解或下界", "大规模问题下界难获取"],
                related_metrics=["目标函数值", "约束违反度"]
            ),
            "constraint_satisfaction": EvaluationMetricKnowledge(
                name="约束满足度",
                metric_type="优化",
                description="衡量解满足所有约束条件的程度",
                formula="满足的约束数 / 总约束数 × 100%（或约束违反量之和）",
                interpretation="100%表示所有约束满足;低于100%需要检查不可行约束",
                range="0到100%",
                when_to_use=["约束优化问题", "可行性分析", "松弛策略评估"],
                advantages=["直观评价可行性", "支持软约束评估"],
                limitations=["不区分约束重要性", "仅评价可行性不评价最优性"],
                related_metrics=["最优性间隙", "目标函数值"]
            ),
            "consistency_ratio": EvaluationMetricKnowledge(
                name="一致性比率(CR)",
                metric_type="评价",
                description="AHP中衡量判断矩阵一致性的指标",
                formula="CI / RI, 其中 CI = (λmax - n) / (n - 1)",
                interpretation="CR < 0.1 表示一致性可接受; CR >= 0.1 需要调整判断矩阵",
                range="0到∞",
                when_to_use=["AHP权重检验", "专家评分一致性", "多准则决策"],
                advantages=["标准化指标", "有明确判断标准", "AHP必需步骤"],
                limitations=["仅适用于AHP", "临界值0.1有争议"],
                related_metrics=["权重向量", "特征值"]
            ),
            "kendall_tau": EvaluationMetricKnowledge(
                name="Kendall's tau排序一致性",
                metric_type="评价",
                description="衡量两组排名一致程度的非参数统计量",
                formula="(一致对数 - 不一致对数) / C(n,2)",
                interpretation="值越接近1排序越一致;0表示无关;-1完全相反",
                range="-1到1",
                when_to_use=["评价方法对比", "排序结果验证", "评委一致性检验"],
                advantages=["非参数方法", "鲁棒性好", "适合排序对比"],
                limitations=["仅评价排序不评价数值差异", "对并列排名敏感"],
                related_metrics=["Spearman相关系数", "一致性比率"]
            )
        }

    def _initialize_validation_methods(self) -> Dict[str, ValidationMethodKnowledge]:
        """初始化验证方法知识库"""
        return {
            "k_fold_cv": ValidationMethodKnowledge(
                name="K折交叉验证",
                description="将数据分为K份,轮流使用一份作为验证集,其余作为训练集",
                applicable_scenarios=["有限数据", "模型选择", "超参数调优", "无专门测试集"],
                implementation_steps=[
                    "1. 确定K值(通常5或10)",
                    "2. 随机分割数据为K份",
                    "3. 对每一折执行训练和验证",
                    "4. 计算K个性能指标的平均值和方差"
                ],
                computational_cost="中等(需训练K次模型)",
                robustness="高(充分利用数据)",
                sample_size_requirement="中等(50+样本)",
                common_issues=["K值选择困难", "类别不平衡时分割不均", "计算开销大"]
            ),
            "stratified_kfold": ValidationMethodKnowledge(
                name="分层K折交叉验证",
                description="K折交叉验证的改进,保持各折的类别分布一致",
                applicable_scenarios=["不平衡分类", "小数据集", "需要保持分布的场景"],
                implementation_steps=[
                    "1. 按类别分层数据",
                    "2. 在每个层内进行K折分割",
                    "3. 组合各层的分割结果",
                    "4. 执行交叉验证"
                ],
                computational_cost="中等(需训练K次模型)",
                robustness="很高(保持分布,充分利用数据)",
                sample_size_requirement="中等(50+样本)",
                common_issues=["特征工程复杂", "多分类时层数多"]
            ),
            "time_series_cv": ValidationMethodKnowledge(
                name="时间序列交叉验证",
                description="按时间顺序分割,避免数据泄露,适用于时间序列数据",
                applicable_scenarios=["时间序列预测", "金融数据", "需要避免未来信息泄露"],
                implementation_steps=[
                    "1. 固定训练集大小",
                    "2. 逐步向后滑动验证集",
                    "3. 保持时间顺序",
                    "4. 计算多个周期的性能指标"
                ],
                computational_cost="高(多个时间步)",
                robustness="很高(避免数据泄露)",
                sample_size_requirement="大(足够时间步)",
                common_issues=["趋势和季节性", "需大量历史数据"]
            ),
            "bootstrap_validation": ValidationMethodKnowledge(
                name="自助法(Bootstrap)",
                description="随机有放回地重复抽样,用于估计统计量的分布",
                applicable_scenarios=["小数据集", "置信区间估计", "非参数推断"],
                implementation_steps=[
                    "1. 从原数据随机有放回抽样",
                    "2. 生成B个Bootstrap样本",
                    "3. 对每个样本训练模型",
                    "4. 计算性能指标的分布"
                ],
                computational_cost="高(需训练B次模型)",
                robustness="高(充分利用数据)",
                sample_size_requirement="小(10+样本)",
                common_issues=["计算开销大", "假设独立同分布"]
            )
        }

    def _initialize_best_practices(self) -> Dict[str, List[str]]:
        """初始化最佳实践"""
        return {
            "data_preprocessing": [
                "始终检查缺失值并合理处理(删除、填充或保留)",
                "检测并处理异常值(IQR法、3σ法等)",
                "进行特征缩放(标准化或归一化)",
                "处理类别不平衡(过采样、欠采样、调整权重)",
                "进行特征工程(创建交互项、多项式特征等)",
                "检查特征共线性",
                "确保数据质量和一致性"
            ],
            "model_selection": [
                "从简单模型开始,逐步增加复杂度",
                "基于问题特性和数据特征选择合适的模型",
                "准备多个备选模型进行对比",
                "考虑模型的可解释性",
                "评估模型的计算复杂度和可扩展性",
                "进行充分的理论分析"
            ],
            "validation_strategy": [
                "采用合适的数据分割策略(避免数据泄露)",
                "对分类问题使用分层抽样",
                "对时间序列使用时间顺序分割",
                "使用多个评价指标进行全面评估",
                "进行交叉验证以评估模型稳定性",
                "进行敏感性分析",
                "检验结果的统计显著性"
            ],
            "robustness_testing": [
                "测试模型对参数变化的敏感性",
                "进行数据扰动测试(添加噪声、删除样本等)",
                "测试模型在不同数据分布下的表现",
                "进行异常值处理的影响分析",
                "多起点优化以避免局部最优",
                "进行蒙特卡洛模拟"
            ],
            "reporting_and_interpretation": [
                "清晰呈现方法论和假设",
                "提供充分的可视化支持结果",
                "讨论模型限制和不适用场景",
                "提供改进方向建议",
                "与基线方法对比",
                "讨论结果的实际意义",
                "提供可操作的建议"
            ]
        }

    def _initialize_problem_guidelines(self) -> Dict[str, Dict[str, Any]]:
        """初始化问题类型指南"""
        return {
            "optimization": {
                "description": "寻找在约束条件下使目标函数最优的解",
                "key_models": [
                    "线性规划", "整数规划", "非线性规划", "动态规划",
                    "博弈论(Nash均衡)", "排队论", "模拟退火算法",
                ],
                "validation_focus": ["约束条件验证", "解的可行性", "最优性判定"],
                "common_challenges": ["约束条件复杂", "模型规模大", "求解算法效率"],
                "best_practice": "先用启发式算法获得上界,再用精确算法求解"
            },
            "prediction": {
                "description": "基于历史数据预测未来趋势或值",
                "key_models": [
                    "回归分析", "时间序列ARIMA", "神经网络", "集成方法",
                    "灰色预测GM(1,1)", "LSTM长短期记忆网络", "Prophet预测模型",
                    "样条插值",
                ],
                "validation_focus": ["预测精度", "泛化能力", "鲁棒性"],
                "common_challenges": ["数据不足", "特征工程复杂", "过拟合风险"],
                "best_practice": "进行充分的特征工程,使用多个模型集成"
            },
            "classification": {
                "description": "将样本分配到预定的类别中",
                "key_models": [
                    "逻辑回归", "决策树", "SVM", "随机森林",
                    "XGBoost/LightGBM",
                ],
                "validation_focus": ["分类准确率", "类别平衡", "ROC/AUC"],
                "common_challenges": ["类别不平衡", "高维数据", "可解释性"],
                "best_practice": "处理类别不平衡,使用多个指标评估,提供特征重要性分析"
            },
            "clustering": {
                "description": "将数据分组,同组内相似度高,不同组间差异大",
                "key_models": ["K-means", "DBSCAN", "层次聚类", "高斯混合模型"],
                "validation_focus": ["聚类质量", "簇数确定", "簇的解释性"],
                "common_challenges": ["K值选择", "初始化影响", "高维数据"],
                "best_practice": "多个K值评估,结合多个指标判断,验证簇的意义"
            },
            "evaluation": {
                "description": "对多个方案进行综合评价,选择最优方案",
                "key_models": [
                    "AHP", "TOPSIS", "熵权法", "模糊评价",
                    "VIKOR多准则决策",
                ],
                "validation_focus": ["权重合理性", "评价体系完整性", "一致性"],
                "common_challenges": ["主观性强", "指标体系复杂", "权重确定困难"],
                "best_practice": "邀请专家参与,进行敏感性分析,多种方法对比"
            },
            "stochastic_process": {
                "description": "对随机演化过程进行建模和分析",
                "key_models": [
                    "马尔可夫链", "排队论", "SIR/SEIR传染病模型",
                    "贝叶斯推断",
                ],
                "validation_focus": ["模型假设验证", "参数估计精度", "稳态分析"],
                "common_challenges": ["假设条件验证", "参数估计困难", "状态空间大"],
                "best_practice": "先验证马尔可夫性等基本假设,结合仿真模拟交叉验证"
            }
        }

    def search_model(self, problem_type: str, key_words: List[str] = None) -> List[ModelKnowledge]:
        """根据问题类型和关键词搜索合适的模型"""
        results = []
        problem_lower = problem_type.lower()

        for model_key, model in self.models.items():
            # 检查问题类型是否匹配
            if any(
                keyword in problem_lower or problem_lower in keyword
                for keyword in (p.lower() for p in model.applicable_problems)
            ):
                results.append(model)
            # 检查关键词是否匹配
            elif key_words and any(kw in str(model.__dict__).lower() for kw in key_words):
                results.append(model)

        return results

    def get_validation_method(self, problem_type: str, data_size: str = "中等") -> List[ValidationMethodKnowledge]:
        """根据问题类型和数据规模推荐验证方法"""
        recommendations = []

        if "时间序列" in problem_type or "预测" in problem_type:
            recommendations.append(self.validation_methods["time_series_cv"])
        else:
            if data_size == "小":
                recommendations.append(self.validation_methods["bootstrap_validation"])
            else:
                recommendations.append(self.validation_methods["k_fold_cv"])

            if "分类" in problem_type:
                recommendations.append(self.validation_methods["stratified_kfold"])

        return recommendations

    def get_evaluation_metrics(self, problem_type: str) -> List[EvaluationMetricKnowledge]:
        """根据问题类型推荐评价指标。

        支持的问题类型关键词: 回归、预测、分类、聚类、优化、评价/决策。
        当问题类型包含多个关键词时，会返回所有匹配类型的指标（去重）。
        """
        metrics: List[EvaluationMetricKnowledge] = []
        seen_names: set[str] = set()

        def _add(metric: EvaluationMetricKnowledge) -> None:
            """去重添加指标。"""
            if metric.name not in seen_names:
                seen_names.add(metric.name)
                metrics.append(metric)

        # 回归/预测类指标
        if "回归" in problem_type or "预测" in problem_type:
            for key in ("rmse", "mae", "r_squared", "mape"):
                if key in self.metrics:
                    _add(self.metrics[key])

        # 分类类指标
        if "分类" in problem_type:
            for key in ("accuracy", "f1_score", "auc_roc"):
                if key in self.metrics:
                    _add(self.metrics[key])

        # 聚类类指标
        if "聚类" in problem_type:
            if "silhouette_score" in self.metrics:
                _add(self.metrics["silhouette_score"])

        # 优化类指标
        if "优化" in problem_type:
            for key in ("optimality_gap", "constraint_satisfaction"):
                if key in self.metrics:
                    _add(self.metrics[key])

        # 评价/决策类指标
        if "评价" in problem_type or "决策" in problem_type:
            for key in ("consistency_ratio", "kendall_tau"):
                if key in self.metrics:
                    _add(self.metrics[key])

        return metrics

    def get_knowledge_for_prompt(
        self,
        problem_type: str = "",
        keywords: List[str] | None = None,
        max_chars: int = 2000,
    ) -> str:
        """根据问题类型和关键词生成用于注入 Prompt 的知识文本

        Args:
            problem_type: 问题类型描述（如 "优化"、"预测"）
            keywords: 关键词列表
            max_chars: 最大返回字符数

        Returns:
            格式化的知识库推荐文本，为空则返回空字符串
        """
        sections: List[str] = []

        # 1. 搜索匹配的模型
        matched_models = self.search_model(problem_type, key_words=keywords)
        if matched_models:
            model_lines = []
            for m in matched_models[:5]:  # 最多展示5个模型
                advantages = "、".join(m.advantages[:3])
                pitfalls = "、".join(m.common_pitfalls[:2])
                model_lines.append(
                    f"- **{m.name}**（{m.category}，复杂度: {m.complexity}）: "
                    f"{m.description}。优势: {advantages}。常见陷阱: {pitfalls}"
                )
            sections.append("### 推荐模型\n" + "\n".join(model_lines))

        # 2. 问题类型指南
        for ptype, guidelines in self.problem_type_guidelines.items():
            if ptype in problem_type.lower():
                key_models = "、".join(guidelines.get("key_models", []))
                best_practice = guidelines.get("best_practice", "")
                challenges = "、".join(guidelines.get("common_challenges", []))
                sections.append(
                    f"### 问题类型指南（{ptype}）\n"
                    f"- 关键模型: {key_models}\n"
                    f"- 最佳实践: {best_practice}\n"
                    f"- 常见挑战: {challenges}"
                )
                break

        # 3. 推荐评价指标
        eval_metrics = self.get_evaluation_metrics(problem_type)
        if eval_metrics:
            metric_lines = [
                f"- **{m.name}**: {m.interpretation}"
                for m in eval_metrics[:3]
            ]
            sections.append("### 推荐评价指标\n" + "\n".join(metric_lines))

        # 4. 推荐验证方法
        validation_methods = self.get_validation_method(problem_type)
        if validation_methods:
            val_lines = [
                f"- **{v.name}**: {v.description}"
                for v in validation_methods[:2]
            ]
            sections.append("### 推荐验证方法\n" + "\n".join(val_lines))

        result = "\n\n".join(sections)

        # 截断到最大字符数
        if len(result) > max_chars:
            result = result[:max_chars].rsplit("\n", 1)[0] + "\n..."

        return result

    def get_model_combinations(self, problem_type: str) -> List[Dict[str, Any]]:
        """根据问题类型推荐模型组合策略。

        针对竞赛中常见的问题类型，推荐经过验证的模型组合方案，
        包括组合名称、组成模型、适用场景、组合优势和使用建议。

        Args:
            problem_type: 问题类型描述（如 "评价"、"预测"、"优化"、"分类"、"聚类"）

        Returns:
            匹配的模型组合策略列表，每个元素为包含组合详情的字典
        """
        # 预定义的模型组合策略库
        combination_registry: Dict[str, List[Dict[str, Any]]] = {
            "评价": [
                {
                    "name": "AHP + TOPSIS 综合评价",
                    "models": ["层次分析法(AHP)", "TOPSIS逼近理想解排序法"],
                    "scenario": "主观权重与客观排序相结合的多准则决策",
                    "advantage": "AHP确定权重具有逻辑性，TOPSIS排序客观全面",
                    "usage_notes": "先用AHP构建层次结构并计算权重，再将权重代入TOPSIS进行方案排序",
                },
                {
                    "name": "熵权法 + TOPSIS 客观评价",
                    "models": ["熵权法", "TOPSIS逼近理想解排序法"],
                    "scenario": "无专家参与、需要纯客观评价的场景",
                    "advantage": "完全基于数据的客观赋权与排序，避免主观偏差",
                    "usage_notes": "先用熵权法从数据中提取权重，再代入TOPSIS排序；适合数据充分的场景",
                },
                {
                    "name": "AHP + 模糊综合评价",
                    "models": ["层次分析法(AHP)", "模糊综合评价"],
                    "scenario": "评价指标含定性因素、边界模糊的综合评价问题",
                    "advantage": "AHP处理层次关系，模糊评价处理不确定性和模糊性",
                    "usage_notes": "AHP确定各层权重，模糊评价处理定性指标的隶属度，适合质量评价等场景",
                },
                {
                    "name": "熵权法 + VIKOR 折衷决策",
                    "models": ["熵权法", "VIKOR多准则决策"],
                    "scenario": "需要寻找折衷方案、兼顾群体与个体的多准则决策",
                    "advantage": "客观赋权与折衷排序结合，兼顾群体效用和个体遗憾",
                    "usage_notes": "熵权法确定权重后代入VIKOR，注意检验可接受优势和稳定性条件",
                },
            ],
            "预测": [
                {
                    "name": "ARIMA + Prophet 集成预测",
                    "models": ["时间序列ARIMA", "Prophet预测模型"],
                    "scenario": "中长期时间序列预测，需要综合统计模型和趋势分解",
                    "advantage": "ARIMA捕获自相关性，Prophet处理趋势和季节性，互补性强",
                    "usage_notes": "分别训练两个模型，通过加权平均或Stacking集成预测结果",
                },
                {
                    "name": "LSTM + XGBoost 混合预测",
                    "models": ["LSTM长短期记忆网络", "XGBoost/LightGBM"],
                    "scenario": "数据量充足的复杂时序预测，兼顾深度特征和结构化特征",
                    "advantage": "LSTM提取时序深层特征，XGBoost处理结构化特征，组合提升精度",
                    "usage_notes": "LSTM负责时序特征提取，XGBoost融合外部特征进行最终预测；注意数据对齐",
                },
                {
                    "name": "灰色预测 + 回归修正",
                    "models": ["灰色预测GM(1,1)", "线性回归"],
                    "scenario": "小样本趋势预测，需要修正系统偏差",
                    "advantage": "灰色预测处理小样本，回归模型修正残差，提高预测精度",
                    "usage_notes": "先用GM(1,1)得到初始预测，再用回归模型拟合残差进行修正",
                },
                {
                    "name": "样条插值 + 时间序列",
                    "models": ["样条插值", "时间序列ARIMA"],
                    "scenario": "数据存在缺失或不等间隔的时序预测",
                    "advantage": "样条插值补全数据，时间序列模型进行预测",
                    "usage_notes": "先用样条插值补全缺失数据并平滑，再使用ARIMA等模型建模预测",
                },
            ],
            "优化": [
                {
                    "name": "遗传算法 + 模拟退火 混合优化",
                    "models": ["NSGA-II多目标优化", "模拟退火算法"],
                    "scenario": "复杂组合优化问题，搜索空间大且多峰",
                    "advantage": "遗传算法全局搜索，模拟退火局部精细化，避免早熟收敛",
                    "usage_notes": "遗传算法获得初步优良解集，模拟退火对候选解局部优化",
                },
                {
                    "name": "多目标优化 + TOPSIS 决策",
                    "models": ["NSGA-II多目标优化", "TOPSIS逼近理想解排序法"],
                    "scenario": "多目标优化后需要从Pareto前沿中选择最终方案",
                    "advantage": "NSGA-II获得Pareto最优解集，TOPSIS从中选出综合最优方案",
                    "usage_notes": "先用NSGA-II求解Pareto前沿，再用TOPSIS对前沿上的解进行排序选择",
                },
                {
                    "name": "排队论 + 线性规划 服务优化",
                    "models": ["排队论(M/M/1等)", "线性规划"],
                    "scenario": "服务系统设计与资源配置优化",
                    "advantage": "排队论分析系统性能指标，线性规划优化资源分配",
                    "usage_notes": "先用排队论建立性能约束(等待时间、利用率)，再用线性规划求解最优配置",
                },
            ],
            "分类": [
                {
                    "name": "逻辑回归 + 随机森林 对比",
                    "models": ["逻辑回归", "随机森林"],
                    "scenario": "二分类问题，需要兼顾可解释性和预测精度",
                    "advantage": "逻辑回归提供可解释的因素分析，随机森林保证预测精度",
                    "usage_notes": "逻辑回归用于因素分析和基准，随机森林用于提高精度；对比两者结果增强说服力",
                },
                {
                    "name": "决策树 + XGBoost 渐进方案",
                    "models": ["决策树", "XGBoost/LightGBM"],
                    "scenario": "从简单到复杂的分类建模，论文中体现模型演进",
                    "advantage": "决策树可视化决策规则，XGBoost提供高精度集成结果",
                    "usage_notes": "先展示决策树的可解释规则，再用XGBoost提升精度；对比分析增加论文深度",
                },
            ],
            "聚类": [
                {
                    "name": "PCA降维 + K-means 聚类",
                    "models": ["主成分分析(PCA)", "K-means聚类"],
                    "scenario": "高维数据聚类，需要降维后可视化",
                    "advantage": "PCA消除共线性并降维，K-means在低维空间中高效聚类",
                    "usage_notes": "先用PCA降至2-3维进行可视化和去噪，再用K-means聚类；肘部法确定K值",
                },
            ],
            "随机过程": [
                {
                    "name": "马尔可夫链 + 博弈论 策略演化",
                    "models": ["马尔可夫链", "博弈论(Nash均衡)"],
                    "scenario": "多主体策略随时间演化的动态博弈分析",
                    "advantage": "马尔可夫链刻画状态转移，博弈论分析均衡策略",
                    "usage_notes": "博弈论确定各状态下的策略选择，马尔可夫链模拟策略演化的长期趋势",
                },
            ],
        }

        results: List[Dict[str, Any]] = []
        problem_lower = problem_type.lower()

        for category, combinations in combination_registry.items():
            if category in problem_lower:
                results.extend(combinations)

        # 如果未精确匹配到类别，尝试模糊匹配关键词
        if not results:
            keyword_mapping: Dict[str, str] = {
                "排序": "评价",
                "决策": "评价",
                "权重": "评价",
                "选择": "评价",
                "综合": "评价",
                "趋势": "预测",
                "时序": "预测",
                "时间序列": "预测",
                "销量": "预测",
                "规划": "优化",
                "调度": "优化",
                "分配": "优化",
                "路径": "优化",
                "二分类": "分类",
                "识别": "分类",
                "诊断": "分类",
                "分群": "聚类",
                "分组": "聚类",
                "状态转移": "随机过程",
                "马尔可夫": "随机过程",
            }
            for keyword, mapped_type in keyword_mapping.items():
                if keyword in problem_lower and mapped_type in combination_registry:
                    results.extend(combination_registry[mapped_type])
                    break

        return results

    def get_best_practices(self, problem_type: str) -> Dict[str, List[str]]:
        """获取特定问题类型的最佳实践"""
        practices = {}

        # 通用最佳实践
        for category, items in self.best_practices.items():
            practices[category] = items

        # 问题类型特定的最佳实践
        for ptype, guidelines in self.problem_type_guidelines.items():
            if ptype in problem_type.lower():
                practices[f"{ptype}_specific"] = guidelines.get("best_practice", [])

        return practices


# 全局知识库实例
knowledge_base = MathModelingKnowledgeBase()
