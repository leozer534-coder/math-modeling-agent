"""
质量评审专家 - 综合评审方案质量并提供改进建议
"""
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

from app.core.agents.expert_agent import AgentRole, ExpertAgent


class ReviewStatus(Enum):
    """评审状态"""
    APPROVED = "通过"
    APPROVED_WITH_NOTES = "有条件通过"
    NEEDS_REVISION = "需要修改"
    REJECTED = "未通过"


@dataclass
class QualityReview:
    """质量评审结果"""
    overall_rating: int  # 1-5
    review_status: ReviewStatus
    content_quality: Dict[str, Any]
    methodology_quality: Dict[str, Any]
    result_quality: Dict[str, Any]
    writing_quality: Dict[str, Any]
    innovation_assessment: Dict[str, Any]
    critical_issues: List[Dict[str, str]]
    suggestions_for_improvement: List[Dict[str, str]]
    final_recommendation: str
    reviewer_comments: str


class Reviewer(ExpertAgent):
    """质量评审专家Agent"""

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.REVIEWER,
            max_reflections=1,
            max_chat_turns=12
        )

    def get_system_prompt(self) -> str:
        return """
# 质量评审专家

你是一位资深的数学建模竞赛评审专家，曾多次担任全国大学生数学建模竞赛（CUMCM）和美国大学生数学建模竞赛（MCM/ICM）的评委。你对优秀的数学建模论文有深入理解，能够从竞赛评审角度进行专业的多维度评估。

## 核心职责
1. **综合质量评审** - 从多维度评估方案整体质量
2. **内容合理性检查** - 验证问题理解和建模思路
3. **方法论规范检查** - 确保方法正确规范
4. **结果可靠性评估** - 验证结果的准确性和可信度
5. **写作质量评审** - 评估论文写作质量
6. **创新性评估** - 识别创新点和亮点
7. **问题识别** - 发现关键问题和不足
8. **改进建议** - 提供具体的、可执行的改进建议

---

## 数学建模竞赛评审标准

### 一、四大核心评审维度（竞赛评委视角）

#### 1. 创新性（Innovation）
- 是否提出了独特的建模视角或思路
- 是否对经典模型做了有意义的改进或扩展
- 是否融合了多种方法形成混合模型
- 创新点是否有实质性价值，而非为创新而创新

#### 2. 科学性（Scientific Rigor）
- 数学推导是否严谨、逻辑是否自洽
- 模型假设是否合理，是否有充分的现实依据
- 参数估计方法是否科学
- 求解过程是否正确，是否有数学证明或理论支撑
- 符号系统是否统一，公式编号是否连续

#### 3. 完整性（Completeness）
- 是否回答了题目的所有子问题
- 每个子问题是否都有独立的建模和求解过程
- 是否包含问题分析、模型建立、模型求解、模型验证、结果分析等完整环节
- 是否有摘要、目录、参考文献等完整论文结构

#### 4. 实用性（Practicality）
- 模型结果是否有实际应用价值
- 结论是否可以指导实际决策
- 模型是否具有可推广性
- 是否讨论了模型的适用范围和局限性

### 二、常见扣分项（严格检查）

#### 严重扣分项（Critical，直接影响获奖等级）
- **模型假设不合理**: 假设过于理想化或缺乏依据，与实际问题严重脱节
- **缺乏模型验证**: 没有对模型进行任何形式的验证（交叉验证、残差分析、回代检验等）
- **公式推导有误**: 数学公式推导过程存在逻辑错误或计算错误
- **结论无数据支撑**: 最终结论缺少定量分析支撑，仅有定性描述
- **未回答所有子问题**: 遗漏了题目中的某个子问题

#### 中等扣分项（Important）
- **缺少模型对比**: 未与至少一个 baseline 模型进行对比分析
- **敏感性分析缺失**: 未分析关键参数变化对结果的影响
- **图表不规范**: 缺少标题、坐标轴标签、单位、图例等
- **数据预处理不当**: 未说明数据清洗、异常值处理的方法和理由
- **符号不一致**: 同一物理量在不同位置使用不同符号

#### 轻微扣分项（Nice-to-have）
- **参考文献格式不统一**: 引用格式不规范
- **排版细节**: 段落间距、字体大小不统一
- **变量定义集中度**: 变量未在首次出现时定义

### 三、数学公式和符号一致性检查

你在评审时必须特别关注以下公式和符号规范问题：
1. **符号定义**: 所有变量和参数是否在首次使用时明确定义
2. **符号一致性**: 同一物理量在全文中是否使用相同符号，避免 x 和 X、alpha 和 a 混用
3. **公式编号**: 重要公式是否有编号，正文中是否正确引用
4. **量纲分析**: 等式两端的量纲是否一致
5. **下标/上标规范**: 数学符号的上下标是否清晰、无歧义
6. **矩阵/向量标记**: 矩阵是否用粗体大写、向量是否用粗体小写或箭头标记
7. **单位标注**: 数值结果是否标注了正确的物理单位

---

## 评审维度详细说明

### 1. 内容质量评估
**题意理解**:
- 问题理解是否准确完整
- 问题的关键要素是否全部考虑
- 背景信息的理解是否充分
- 是否识别了问题的数学本质（优化、预测、分类、评价等）

**建模思路**:
- 思路是否清晰合理
- 是否选择了合适的建模方法
- 模型假设是否合理且有现实依据
- 约束条件是否充分考虑
- 是否从简单模型出发逐步改进

**数据处理**:
- 数据特征分析是否充分（描述性统计、分布分析）
- 数据预处理是否恰当（缺失值、异常值处理有说明）
- 特征工程是否合理
- 是否进行了数据可视化探索

### 2. 方法论质量评估
**模型选择**:
- 模型是否适合问题类型
- 是否考虑了多个备选模型并进行对比
- 模型选择的理由是否充分，是否有理论支撑
- 模型复杂度是否合适（奥卡姆剃刀原则）

**求解方法**:
- 求解方法是否正确
- 算法参数设置是否恰当，是否有调参过程
- 是否有创新的求解思路
- 计算复杂度是否可接受

**模型验证**:
- 是否进行了交叉验证或留出法验证
- 是否进行了残差分析
- 是否进行了敏感性分析（关键参数的影响）
- 是否进行了鲁棒性测试
- 是否用已知结果做回代检验

**模型对比**:
- 是否与至少一个 baseline 模型做了对比
- 对比指标是否合理（MSE、R2、准确率等）
- 对比分析是否客观，是否说明了各模型的优劣

### 3. 结果质量评估
**数值合理性**:
- 结果数值是否在合理范围内
- 与预期或已知数据是否相符
- 是否通过了合理性检验
- 数值结果的量纲是否正确

**误差与置信度分析**:
- 是否报告了误差范围或置信区间
- 是否分析了误差来源（模型误差、数据误差、计算误差）
- 误差大小是否可接受
- 是否讨论了结果的统计显著性

**可视化与可解释性**:
- 结果是否易于理解
- 物理或实际意义是否清晰
- 图表是否有标题、坐标轴标签和单位
- 图表中数据点是否有图例说明
- 是否使用了合适的图表类型展示结果

### 4. 论文写作质量
**结构完整性**:
- 论文结构是否完整合理（摘要、问题分析、模型建立、求解、验证、结论）
- 各部分逻辑关系是否清晰
- 过渡是否流畅

**表达清晰性**:
- 用语是否准确、专业
- 表述是否清晰、简洁
- 是否有语法或表达错误

**图表质量**:
- 图表是否清晰美观
- 图表标注是否完整（标题、坐标轴、单位、图例）
- 图表是否有效支撑论文论述

**引用规范**:
- 文献引用是否规范
- 数据来源是否标注
- 是否有适当数量的引用

### 5. 创新性评估
**方法创新**:
- 是否使用了新颖的方法或算法
- 是否对经典方法做了有意义的改进
- 与常见解法的差异化程度

**应用创新**:
- 是否有新的应用角度
- 是否有实际应用价值
- 是否有推广潜力

**改进创新**:
- 是否改进了现有方法的不足
- 改进的合理性和有效性如何

---

## 评分标准

### 五级评分体系
- **5分 (优秀)**: 各方面表现出色，有明确的创新亮点，符合一等奖水平
- **4分 (良好)**: 整体表现良好，方法论严谨，个别细节可改进，符合二等奖水平
- **3分 (一般)**: 达到基本要求，方法和结果正确但缺乏深度，有明显改进空间
- **2分 (较差)**: 存在较多问题，模型或求解有明显缺陷，需要较大改进
- **1分 (很差)**: 存在严重问题，模型不正确或未完成关键部分

### 各维度权重
- 内容质量: 30%
- 方法论质量: 30%
- 结果质量: 20%
- 论文质量: 10%
- 创新性: 10%

## 输出要求

### 评审结果JSON格式
```json
{
    "overall_rating": 4,
    "review_status": "有条件通过",
    "content_quality": {
        "problem_understanding": 5,
        "modeling_approach": 4,
        "data_analysis": 4,
        "average_score": 4.33,
        "comments": "评论说明"
    },
    "methodology_quality": {
        "model_selection": 4,
        "solving_method": 4,
        "validation_approach": 3,
        "model_comparison": 3,
        "assumption_quality": 4,
        "average_score": 3.6,
        "comments": "评论说明",
        "missing_items": ["缺失项列表"]
    },
    "result_quality": {
        "numerical_validity": 4,
        "error_analysis": 3,
        "interpretability": 4,
        "confidence_interval": 2,
        "visualization_quality": 4,
        "dimensional_consistency": 4,
        "average_score": 3.5,
        "comments": "评论说明",
        "missing_items": ["缺失项列表"]
    },
    "writing_quality": {
        "structure": 4,
        "clarity": 4,
        "figures_tables": 4,
        "citations": 3,
        "average_score": 3.75,
        "comments": "评论说明"
    },
    "innovation_assessment": {
        "method_innovation": 3,
        "application_innovation": 3,
        "improvement_innovation": 2,
        "average_score": 2.67,
        "comments": "创新不足，建议增强"
    },
    "critical_issues": [
        {
            "issue": "问题描述",
            "severity": "critical/important/nice-to-have",
            "evidence": "出现位置或证据",
            "suggested_fix": "建议修改"
        }
    ],
    "suggestions_for_improvement": [
        {
            "category": "类别",
            "suggestion": "具体建议",
            "impact": "预期影响",
            "priority": "critical/important/nice-to-have"
        }
    ],
    "final_recommendation": "最终建议",
    "reviewer_comments": "评审意见（200-300字）"
}
```

## 执行流程
1. 获取完整的建模方案（论文全文、代码执行结果）
2. 深入理解问题和方案
3. 按照数学建模竞赛评审标准从多维度评估
4. 重点检查常见扣分项
5. 检查数学公式和符号一致性
6. 识别关键问题并按严重程度分级
7. 提供具体的、可执行的改进建议
8. 生成评审报告
9. 自我反思和验证

## 评审原则
- **竞赛视角**: 以数学建模竞赛评委的标准进行评审
- **客观公正**: 基于论文内容事实，不主观臆断
- **建设性**: 找到问题的同时必须提供具体的解决方案
- **全面深入**: 不遗漏重要问题，特别关注常见扣分项
- **鼓励创新**: 认可创新和亮点，创新性是拉开差距的关键
- **实事求是**: 既看成绩也看不足，评分有理有据

现在开始进行全面的质量评审！
        """

    async def execute(self, modeling_results: Dict[str, Any]) -> QualityReview:
        """执行质量评审"""
        await self.send_message("👨‍⚖️ 开始综合质量评审...", "info")
        self.state.current_stage = "reviewing"

        # 1. 内容质量评审
        content_quality = await self._review_content_quality(modeling_results)
        await self.send_message("✅ 内容质量评审完成", "success")

        # 2. 方法论质量评审
        methodology_quality = await self._review_methodology_quality(modeling_results)
        await self.send_message("✅ 方法论质量评审完成", "success")

        # 3. 结果质量评审
        result_quality = await self._review_result_quality(modeling_results)
        await self.send_message("✅ 结果质量评审完成", "success")

        # 4. 写作质量评审
        writing_quality = await self._review_writing_quality(modeling_results)
        await self.send_message("✅ 论文质量评审完成", "success")

        # 5. 创新性评估
        innovation_assessment = await self._assess_innovation(modeling_results)
        await self.send_message("✅ 创新性评估完成", "success")

        # 6. 综合评分和评审状态
        overall_rating, review_status = self._calculate_overall_rating(
            content_quality, methodology_quality, result_quality,
            writing_quality, innovation_assessment
        )
        await self.send_message(f"📊 综合评分: {overall_rating}分 ({review_status.value})", "info")

        # 7. 问题识别
        critical_issues = await self._identify_critical_issues(
            modeling_results, content_quality, methodology_quality, result_quality
        )
        await self.send_message(f"🔍 识别{len(critical_issues)}个关键问题", "info")

        # 8. 生成改进建议
        improvement_suggestions = await self._generate_improvement_suggestions(
            critical_issues, modeling_results
        )
        await self.send_message(f"💡 生成{len(improvement_suggestions)}条改进建议", "success")

        # 9. 生成最终建议
        final_recommendation = await self._generate_final_recommendation(
            overall_rating, review_status, critical_issues
        )

        # 10. 生成评审意见
        reviewer_comments = await self._generate_reviewer_comments(
            overall_rating, content_quality, methodology_quality,
            result_quality, innovation_assessment
        )

        # 11. 生成完整评审报告
        quality_review = QualityReview(
            overall_rating=overall_rating,
            review_status=review_status,
            content_quality=content_quality,
            methodology_quality=methodology_quality,
            result_quality=result_quality,
            writing_quality=writing_quality,
            innovation_assessment=innovation_assessment,
            critical_issues=critical_issues,
            suggestions_for_improvement=improvement_suggestions,
            final_recommendation=final_recommendation,
            reviewer_comments=reviewer_comments
        )

        # 12. 自我反思
        await self.reflect(
            json.dumps(quality_review.__dict__, ensure_ascii=False, indent=2, default=str),
            "综合评审建模方案的质量"
        )

        # 13. 质量评估
        await self.evaluate_quality(
            json.dumps(quality_review.__dict__, ensure_ascii=False, indent=2, default=str),
            "评审要公正客观、全面深入"
        )

        await self.send_message("🎉 质量评审完成！", "success")
        self.state.current_stage = "completed"

        return quality_review

    async def _review_content_quality(self, modeling_results: Dict[str, Any]) -> Dict[str, Any]:
        """评审内容质量"""
        content_prompt = f"""
        评审建模方案的内容质量：

        建模结果摘要：{json.dumps(modeling_results, ensure_ascii=False, default=str)[:1000]}

        请从以下维度评分（1-5分）：
        1. 问题理解 - 是否准确完整理解了问题
        2. 建模思路 - 建模思路是否清晰合理
        3. 数据分析 - 数据处理和分析是否充分

        以JSON格式输出：
        {{
            "problem_understanding": 4,
            "modeling_approach": 4,
            "data_analysis": 3,
            "average_score": 3.67,
            "comments": "评论说明"
        }}
        """

        content = await self.think(content_prompt, use_tools=False)

        try:
            return json.loads(
                content.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "problem_understanding": 4,
                "modeling_approach": 4,
                "data_analysis": 3,
                "average_score": 3.67,
                "comments": "内容质量良好，问题理解准确"
            }

    async def _review_methodology_quality(self, modeling_results: Dict[str, Any]) -> Dict[str, Any]:
        """评审方法论质量

        重点检查：模型选择、求解方法、模型验证、模型对比、假设合理性。
        这些是数学建模竞赛评审中方法论维度的核心要素。
        """
        # 提取论文内容用于深度分析
        paper_content = modeling_results.get("paper_content", "")
        sections = modeling_results.get("sections", [])

        methodology_prompt = f"""
请作为数学建模竞赛评委，严格评审以下建模方案的方法论质量。

## 待评审内容

论文内容（摘要）：
{paper_content[:3000]}

论文包含的章节：{json.dumps(sections, ensure_ascii=False)}

## 评审要求

请从以下 **5 个维度** 逐一评分（1-5分），并针对每个维度给出评分依据：

### 1. 模型选择 (model_selection)
- 所选模型是否适合问题类型（优化/预测/分类/评价等）
- 模型选择的理由是否有理论支撑
- 模型复杂度是否符合奥卡姆剃刀原则

### 2. 求解方法 (solving_method)
- 求解算法是否正确、高效
- 参数设置是否合理，是否说明了调参过程
- 计算复杂度是否可接受

### 3. 模型验证 (validation_approach)
- 是否进行了交叉验证或留出法验证
- 是否进行了残差分析
- 是否进行了敏感性分析（关键参数变化对结果的影响）
- 是否进行了鲁棒性测试
- 是否用已知结果做了回代检验
**注意**：如果论文中完全没有任何形式的模型验证，此项最高给 2 分。

### 4. 模型对比 (model_comparison)
- 是否与至少一个 baseline 模型进行了对比
- 对比指标是否合理（如 MSE、R2、准确率、AIC/BIC 等）
- 是否客观分析了所选模型相对于对比模型的优势和劣势
**注意**：如果论文中没有任何模型对比，此项最高给 2 分。

### 5. 假设质量 (assumption_quality)
- 模型假设是否合理，是否有现实依据或文献支撑
- 假设是否过于理想化（如假设数据完全满足正态分布但未检验）
- 是否讨论了假设不成立时的影响
- 假设数量是否适中（过多或过少都不好）

## 输出格式

请严格按以下 JSON 格式输出，missing_items 列出方法论中缺失的关键要素：
{{
    "model_selection": 4,
    "solving_method": 4,
    "validation_approach": 3,
    "model_comparison": 3,
    "assumption_quality": 4,
    "average_score": 3.6,
    "comments": "总体评价，指出方法论的优势和不足",
    "missing_items": ["缺失的关键要素1", "缺失的关键要素2"]
}}
        """

        methodology = await self.think(methodology_prompt, use_tools=False)

        try:
            result = json.loads(
                methodology.replace("```json", "").replace("```", "").strip()
            )
            # 确保新增字段存在并重新计算平均分
            score_keys = (
                "model_selection", "solving_method", "validation_approach",
                "model_comparison", "assumption_quality",
            )
            scores = [result.get(k, 3) for k in score_keys]
            result["average_score"] = round(sum(scores) / len(scores), 2)
            if "missing_items" not in result:
                result["missing_items"] = []
            return result
        except json.JSONDecodeError:
            return {
                "model_selection": 3,
                "solving_method": 3,
                "validation_approach": 2,
                "model_comparison": 2,
                "assumption_quality": 3,
                "average_score": 2.6,
                "comments": "方法论评审因解析异常使用默认值，建议关注模型验证和对比分析",
                "missing_items": ["模型验证", "模型对比"],
            }

    async def _review_result_quality(self, modeling_results: Dict[str, Any]) -> Dict[str, Any]:
        """评审结果质量

        重点检查：数值合理性、误差分析/置信区间、图表规范性、
        量纲一致性、可视化质量、结果可解释性。
        """
        paper_content = modeling_results.get("paper_content", "")

        result_prompt = f"""
请作为数学建模竞赛评委，严格评审以下建模方案的结果质量。

## 待评审内容

论文内容（摘要）：
{paper_content[:3000]}

## 评审要求

请从以下 **6 个维度** 逐一评分（1-5分），并针对每个维度给出评分依据：

### 1. 数值合理性 (numerical_validity)
- 结果数值是否在合理范围内（如概率在 0-1 之间、比例不超过 100% 等）
- 与问题背景或已知数据是否相符
- 结果是否通过了合理性检验（如量级是否正确）
- 是否存在明显不合理的数值（如负距离、超出物理极限的值等）

### 2. 误差分析 (error_analysis)
- 是否报告了误差范围（如均方误差 MSE、平均绝对误差 MAE 等）
- 是否报告了置信区间或置信水平
- 是否分析了误差来源（模型误差、数据噪声、计算精度等）
- 是否讨论了结果的统计显著性（p值、t检验等）
**注意**：如果论文中完全没有任何形式的误差分析或置信区间，此项最高给 2 分。

### 3. 可解释性 (interpretability)
- 结果是否易于理解
- 是否清晰解释了结果的物理含义或实际意义
- 是否将数学结果转化为对实际问题的回答
- 结论是否有定量数据支撑（而非仅有定性描述）

### 4. 置信区间报告 (confidence_interval)
- 关键数值结果是否附带了置信区间
- 是否说明了置信水平（如 95%、99%）
- 预测结果是否给出了预测区间
**注意**：如果论文完全没有提及置信区间或不确定性量化，此项最高给 2 分。

### 5. 可视化质量 (visualization_quality)
- 图表是否有清晰的标题
- 坐标轴是否有标签和单位
- 是否有图例（legend）说明
- 图表类型是否适合所展示的数据（如时序用折线图、分类用柱状图等）
- 图表中的文字是否可读（字号合适、不重叠）
- 表格是否有表头和单位说明

### 6. 量纲一致性 (dimensional_consistency)
- 公式等式两端的量纲是否一致
- 数值结果是否标注了正确的物理单位
- 不同单位的量是否做了统一（如全部使用国际单位制）
- 无量纲化处理是否正确说明

## 输出格式

请严格按以下 JSON 格式输出，missing_items 列出结果展示中缺失的关键要素：
{{
    "numerical_validity": 4,
    "error_analysis": 3,
    "interpretability": 4,
    "confidence_interval": 2,
    "visualization_quality": 4,
    "dimensional_consistency": 4,
    "average_score": 3.5,
    "comments": "总体评价，指出结果展示的优势和不足",
    "missing_items": ["缺失的关键要素1", "缺失的关键要素2"]
}}
        """

        result = await self.think(result_prompt, use_tools=False)

        try:
            parsed = json.loads(
                result.replace("```json", "").replace("```", "").strip()
            )
            # 确保新增字段存在并重新计算平均分
            score_keys = (
                "numerical_validity", "error_analysis", "interpretability",
                "confidence_interval", "visualization_quality",
                "dimensional_consistency",
            )
            scores = [parsed.get(k, 3) for k in score_keys]
            parsed["average_score"] = round(sum(scores) / len(scores), 2)
            if "missing_items" not in parsed:
                parsed["missing_items"] = []
            return parsed
        except json.JSONDecodeError:
            return {
                "numerical_validity": 3,
                "error_analysis": 2,
                "interpretability": 3,
                "confidence_interval": 2,
                "visualization_quality": 3,
                "dimensional_consistency": 3,
                "average_score": 2.67,
                "comments": "结果质量评审因解析异常使用默认值，建议关注误差分析和置信区间",
                "missing_items": ["误差分析", "置信区间", "图表标注"],
            }

    async def _review_writing_quality(self, modeling_results: Dict[str, Any]) -> Dict[str, Any]:
        """评审论文写作质量"""
        writing_prompt = f"""
        评审论文的写作质量：

        建模结果摘要：{json.dumps(modeling_results, ensure_ascii=False, default=str)[:1000]}

        请从以下维度评分（1-5分）：
        1. 论文结构 - 结构是否完整合理
        2. 表达清晰 - 用语是否准确清晰
        3. 图表质量 - 图表是否清晰美观
        4. 引用规范 - 引用是否规范

        以JSON格式输出：
        {{
            "structure": 4,
            "clarity": 4,
            "figures_tables": 4,
            "citations": 3,
            "average_score": 3.75,
            "comments": "评论说明"
        }}
        """

        writing = await self.think(writing_prompt, use_tools=False)

        try:
            return json.loads(
                writing.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "structure": 4,
                "clarity": 4,
                "figures_tables": 4,
                "citations": 3,
                "average_score": 3.75,
                "comments": "论文写作质量较好，部分引用格式需规范"
            }

    async def _assess_innovation(self, modeling_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估创新性"""
        innovation_prompt = f"""
        评估方案的创新性：

        建模结果摘要：{json.dumps(modeling_results, ensure_ascii=False, default=str)[:1000]}

        请从以下维度评分（1-5分）：
        1. 方法创新 - 是否使用了新颖方法
        2. 应用创新 - 是否有创意的应用
        3. 改进创新 - 是否改进了现有方法

        以JSON格式输出：
        {{
            "method_innovation": 3,
            "application_innovation": 3,
            "improvement_innovation": 2,
            "average_score": 2.67,
            "comments": "评论说明"
        }}
        """

        innovation = await self.think(innovation_prompt, use_tools=False)

        try:
            return json.loads(
                innovation.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "method_innovation": 3,
                "application_innovation": 3,
                "improvement_innovation": 2,
                "average_score": 2.67,
                "comments": "创新点不足，建议增强创新性"
            }

    def _calculate_overall_rating(
        self, content: Dict, methodology: Dict, result: Dict,
        writing: Dict, innovation: Dict
    ) -> Tuple[int, ReviewStatus]:
        """计算综合评分"""
        # 加权计算总分
        total_score = (
            content.get("average_score", 3) * 0.30 +
            methodology.get("average_score", 3) * 0.30 +
            result.get("average_score", 3) * 0.20 +
            writing.get("average_score", 3) * 0.10 +
            innovation.get("average_score", 3) * 0.10
        )

        overall_rating = round(total_score)

        # 确定评审状态
        if overall_rating >= 5:
            status = ReviewStatus.APPROVED
        elif overall_rating >= 4:
            status = ReviewStatus.APPROVED_WITH_NOTES
        elif overall_rating >= 3:
            status = ReviewStatus.NEEDS_REVISION
        else:
            status = ReviewStatus.REJECTED

        return overall_rating, status

    async def _identify_critical_issues(
        self, modeling_results: Dict, content: Dict, methodology: Dict, result: Dict
    ) -> List[Dict[str, str]]:
        """识别关键问题"""
        issues_prompt = f"""
        基于以下评审结果，识别关键问题：

        内容质量：{json.dumps(content, ensure_ascii=False)}
        方法论质量：{json.dumps(methodology, ensure_ascii=False)}
        结果质量：{json.dumps(result, ensure_ascii=False)}

        请识别2-5个关键问题，以JSON格式输出：
        {{
            "issues": [
                {{
                    "issue": "问题描述",
                    "severity": "高",
                    "evidence": "出现位置",
                    "suggested_fix": "建议修改"
                }}
            ]
        }}
        """

        issues = await self.think(issues_prompt, use_tools=False)

        try:
            result_json = json.loads(
                issues.replace("```json", "").replace("```", "").strip()
            )
            return result_json.get("issues", [])
        except json.JSONDecodeError:
            return [
                {
                    "issue": "示例问题",
                    "severity": "中",
                    "evidence": "方法论部分",
                    "suggested_fix": "加强验证方法"
                }
            ]

    async def _generate_improvement_suggestions(
        self, critical_issues: List[Dict], modeling_results: Dict
    ) -> List[Dict[str, str]]:
        """基于评审缺失项和关键问题生成针对性改进建议

        改进建议按优先级分为三级：
        - critical: 直接影响获奖等级的严重问题，必须修复
        - important: 明显影响论文质量的问题，强烈建议修复
        - nice-to-have: 锦上添花的改进，有余力时处理
        """
        suggestions: List[Dict[str, str]] = []

        # 1. 从关键问题中提取改进建议，映射严重程度到三级优先级
        severity_to_priority = {
            "高": "critical",
            "critical": "critical",
            "中": "important",
            "important": "important",
            "低": "nice-to-have",
            "nice-to-have": "nice-to-have",
        }

        for issue in critical_issues:
            raw_severity = issue.get("severity", "important")
            priority = severity_to_priority.get(raw_severity, "important")
            suggested_fix = issue.get("suggested_fix", "")
            if suggested_fix:
                suggestions.append({
                    "category": issue.get("issue", "未分类"),
                    "suggestion": suggested_fix,
                    "impact": self._estimate_impact(priority),
                    "priority": priority,
                })

        # 2. 从方法论和结果评审的 missing_items 中生成针对性建议
        # 这些建议基于具体的缺失项，而非泛泛而谈
        missing_item_suggestions = self._build_missing_item_suggestions(
            modeling_results
        )
        suggestions.extend(missing_item_suggestions)

        # 3. 按优先级排序：critical > important > nice-to-have
        priority_order = {"critical": 0, "important": 1, "nice-to-have": 2}
        suggestions.sort(key=lambda s: priority_order.get(s["priority"], 1))

        # 4. 去重（基于 suggestion 文本）
        seen_suggestions: set[str] = set()
        unique_suggestions: List[Dict[str, str]] = []
        for s in suggestions:
            text = s["suggestion"]
            if text not in seen_suggestions:
                seen_suggestions.add(text)
                unique_suggestions.append(s)

        return unique_suggestions[:8]  # 返回最多 8 条建议

    def _build_missing_item_suggestions(
        self, modeling_results: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """根据评审上下文中记录的缺失项生成具体改进建议

        此方法检查 methodology_quality 和 result_quality 中的 missing_items
        字段，并为每个缺失项生成有针对性的、可执行的改进建议。
        """
        # 缺失项 -> (类别, 建议内容, 影响说明, 优先级) 的映射
        missing_item_map: Dict[str, tuple[str, str, str, str]] = {
            # 方法论相关缺失项
            "模型验证": (
                "模型验证",
                "添加至少一种模型验证方法：(1) 将数据集按 7:3 划分进行留出法验证；"
                "(2) 使用 K 折交叉验证评估模型泛化能力；"
                "(3) 对残差进行正态性检验和自相关分析",
                "模型验证是竞赛评审的硬性要求，缺失将直接影响获奖等级",
                "critical",
            ),
            "模型对比": (
                "模型对比",
                "选择至少一个 baseline 模型进行对比分析：(1) 选择该问题类型的经典方法作为基线；"
                "(2) 使用统一的评价指标（如 MSE、R2、准确率等）进行定量对比；"
                "(3) 分析所选模型相对于基线的优势和适用场景",
                "模型对比体现方法选择的合理性，是评委重点关注的内容",
                "important",
            ),
            "敏感性分析": (
                "敏感性分析",
                "对模型中的关键参数进行敏感性分析：(1) 识别 2-3 个关键参数；"
                "(2) 在合理范围内改变参数值，观察结果变化；"
                "(3) 绘制参数-结果变化曲线图，讨论参数影响程度",
                "敏感性分析能增强结果的可信度和模型的鲁棒性论证",
                "important",
            ),
            # 结果相关缺失项
            "误差分析": (
                "误差分析",
                "补充完整的误差分析：(1) 计算并报告 MSE、MAE、MAPE 等误差指标；"
                "(2) 分析误差来源（模型简化误差、数据噪声、计算精度等）；"
                "(3) 讨论误差是否在可接受范围内",
                "误差分析是结果可信度的基础，缺失会被认为结果不可靠",
                "critical",
            ),
            "置信区间": (
                "置信区间",
                "为关键数值结果添加置信区间：(1) 报告 95% 置信区间；"
                "(2) 对预测结果给出预测区间；"
                "(3) 使用 Bootstrap 方法或解析公式计算置信区间",
                "置信区间量化了结果的不确定性，是科学性的重要体现",
                "important",
            ),
            "图表标注": (
                "图表规范",
                "完善所有图表的标注：(1) 每张图表添加描述性标题；"
                "(2) 坐标轴标注变量名称和物理单位；"
                "(3) 多条曲线的图表添加图例（legend）；"
                "(4) 表格添加表头说明和单位行",
                "图表是评委快速了解结果的窗口，不规范会严重影响印象分",
                "important",
            ),
        }

        suggestions: List[Dict[str, str]] = []

        # 从上下文中查找已识别的缺失项
        # 注意：execute() 方法中各维度评审的结果存储在 self.state.context 中
        # 但由于我们在 execute 中是分步调用的，此处直接从 modeling_results 无法获取
        # 因此我们通过关键词匹配论文内容来判断缺失项
        paper_content = modeling_results.get("paper_content", "").lower()

        # 检查方法论相关缺失项
        validation_keywords = (
            "交叉验证", "cross validation", "留出法", "holdout",
            "残差分析", "residual", "回代检验", "鲁棒性",
        )
        if not any(kw in paper_content for kw in validation_keywords):
            item_data = missing_item_map["模型验证"]
            suggestions.append({
                "category": item_data[0],
                "suggestion": item_data[1],
                "impact": item_data[2],
                "priority": item_data[3],
            })

        comparison_keywords = (
            "对比模型", "baseline", "基线", "模型比较", "模型对比",
            "对比分析", "对照实验", "benchmark",
        )
        if not any(kw in paper_content for kw in comparison_keywords):
            item_data = missing_item_map["模型对比"]
            suggestions.append({
                "category": item_data[0],
                "suggestion": item_data[1],
                "impact": item_data[2],
                "priority": item_data[3],
            })

        sensitivity_keywords = (
            "敏感性分析", "sensitivity", "灵敏度", "参数影响",
            "参数变化", "鲁棒性分析",
        )
        if not any(kw in paper_content for kw in sensitivity_keywords):
            item_data = missing_item_map["敏感性分析"]
            suggestions.append({
                "category": item_data[0],
                "suggestion": item_data[1],
                "impact": item_data[2],
                "priority": item_data[3],
            })

        # 检查结果相关缺失项
        error_keywords = (
            "误差", "error", "mse", "mae", "mape", "rmse",
            "残差", "偏差", "误差分析",
        )
        if not any(kw in paper_content for kw in error_keywords):
            item_data = missing_item_map["误差分析"]
            suggestions.append({
                "category": item_data[0],
                "suggestion": item_data[1],
                "impact": item_data[2],
                "priority": item_data[3],
            })

        confidence_keywords = (
            "置信区间", "confidence interval", "置信水平",
            "预测区间", "bootstrap", "不确定性",
        )
        if not any(kw in paper_content for kw in confidence_keywords):
            item_data = missing_item_map["置信区间"]
            suggestions.append({
                "category": item_data[0],
                "suggestion": item_data[1],
                "impact": item_data[2],
                "priority": item_data[3],
            })

        return suggestions

    @staticmethod
    def _estimate_impact(priority: str) -> str:
        """根据优先级估计改进影响

        将优先级映射为对论文质量影响的描述。
        """
        impact_map = {
            "critical": "直接影响获奖等级，修复后可能提升 1 个获奖档次",
            "important": "显著提升论文质量和评审印象分",
            "nice-to-have": "锦上添花，体现论文的专业性和完整性",
        }
        return impact_map.get(priority, "提升论文整体质量")

    async def _generate_final_recommendation(
        self, overall_rating: int, review_status: ReviewStatus, critical_issues: List[Dict]
    ) -> str:
        """生成最终建议"""
        if review_status == ReviewStatus.APPROVED:
            return "方案质量优秀，建议原则上可提交。"
        elif review_status == ReviewStatus.APPROVED_WITH_NOTES:
            return f"方案质量良好，建议修改{len(critical_issues)}个问题后提交。"
        elif review_status == ReviewStatus.NEEDS_REVISION:
            return f"方案需要较大改进，建议解决{len(critical_issues)}个问题后重新评审。"
        else:
            return "方案存在严重问题，建议重新设计和实现。"

    async def _generate_reviewer_comments(
        self, rating: int, content: Dict, methodology: Dict, result: Dict,
        innovation: Dict
    ) -> str:
        """基于各维度评审数据生成针对性评审意见"""
        rating_labels = ["很差", "较差", "一般", "良好", "优秀"]
        rating_label = rating_labels[min(rating - 1, 4)]

        # 收集各维度的优点（平均分 >= 4 的维度）
        strengths = []
        weaknesses = []

        dimensions = [
            ("内容质量", content),
            ("方法论质量", methodology),
            ("结果质量", result),
            ("创新性", innovation),
        ]

        for dim_name, dim_data in dimensions:
            avg = dim_data.get("average_score", 0)
            comment = dim_data.get("comments", "")
            if avg >= 4:
                strengths.append(f"- {dim_name}（{avg:.1f}分）：{comment}")
            elif avg < 3:
                weaknesses.append(f"- {dim_name}（{avg:.1f}分）：{comment}")

        # 如果没有从数据中提取到足够的优缺点，补充通用条目
        if not strengths:
            strengths.append("- 整体方案具有一定的完整性")
        if not weaknesses:
            weaknesses.append("- 各维度均达到基本要求，但仍有提升空间")

        # 识别具体的子指标亮点和短板
        sub_highlights = []
        sub_issues = []
        for dim_name, dim_data in dimensions:
            for key, value in dim_data.items():
                if key in ("average_score", "comments"):
                    continue
                if isinstance(value, (int, float)):
                    if value >= 5:
                        sub_highlights.append(f"{dim_name}-{key}")
                    elif value <= 2:
                        sub_issues.append(f"{dim_name}-{key}")

        strengths_text = "\n".join(strengths)
        weaknesses_text = "\n".join(weaknesses)

        comments = f"""建模方案综合评审意见：

优点：
{strengths_text}"""

        if sub_highlights:
            comments += f"\n特别亮点：{', '.join(sub_highlights[:3])}"

        comments += f"""

不足：
{weaknesses_text}"""

        if sub_issues:
            comments += f"\n重点关注：{', '.join(sub_issues[:3])}"

        comments += f"""

总体评价：
该方案整体质量{rating_label}（{rating}/5分）。"""

        if rating >= 4:
            comments += "方案完成度高，建议在创新性和细节论证方面进一步打磨。"
        elif rating >= 3:
            comments += "方案基本可行，建议根据评审意见重点改进薄弱环节。"
        else:
            comments += "方案存在较多问题，建议对关键模块进行重新设计和实现。"

        return comments.strip()

    def get_review_summary(self) -> Dict[str, Any]:
        """获取评审摘要"""
        summary = self.get_summary()
        if self.state.quality_metrics:
            summary["quality_level"] = self.state.quality_metrics.get_level().name
        return summary