# 🇺🇸 美赛（MCM/ICM）英文支持完全指南

本指南详细介绍如何使用 MathModelAgent 参加美国大学生数学建模竞赛（MCM/ICM），包括英文界面、英文论文输出和 LaTeX 排版。

---

## 📋 目录

- [概述](#概述)
- [英文 UI 界面](#英文-ui-界面)
- [美赛模板选择](#美赛模板选择)
- [英文论文输出](#英文论文输出)
- [LaTeX 支持](#latex-支持)
- [最佳实践](#最佳实践)
- [示例工作流](#示例工作流)

---

## 🌟 概述

MathModelAgent 为 MCM/ICM 竞赛提供全面的英文支持：

- ✅ **双语界面**: 中英文一键切换
- ✅ **英文 Prompt**: 优化的英文论文生成提示词
- ✅ **美赛模板**: 专为美式竞赛设计的格式模板
- ✅ **LaTeX 输出**: 专业的 LaTeX 排版（mcmthesis 模板）
- ✅ **Markdown 输出**: 简洁的英文 Markdown 论文

---

## 🖥️ 英文 UI 界面

### 切换语言

**在网页界面中：**

1. 在顶部导航栏找到语言选择器
2. 点击语言图标（🇨🇳/🇺🇸）
3. 选择 "English" 或 "简体中文"

**快捷键：**
- 按 `Ctrl+L` 切换语言（如已实现）

**持久化设置：**
- 语言偏好保存在浏览器 localStorage
- 下次访问自动使用首选语言

### 已翻译的界面组件

所有主要 UI 组件都已翻译：

- ✅ 导航和菜单
- ✅ 首页内容
- ✅ 聊天界面
- ✅ 设置和配置
- ✅ 错误消息和通知
- ✅ Agent 描述
- ✅ 工作流程说明

---

## 📝 美赛模板选择

### 模板类型

MathModelAgent 提供两种美赛模板格式：

| 模板 | 格式 | 适用场景 |
|------|------|----------|
| **MCM Markdown** | `.md` | 快速起草，易于编辑 |
| **MCM LaTeX** | `.tex` | 专业排版，最终提交 |

### 如何选择

**在聊天界面中：**

1. 点击"任务参数设置"（设置图标）
2. 在"模板"下拉菜单中选择：
   - **国赛** → 中国大学生数学建模竞赛
   - **美赛** → 美国大学生数学建模竞赛（MCM/ICM）
3. 在"格式"下拉菜单中选择：
   - **Markdown** → 易于编辑
   - **LaTeX** → 专业排版（美赛推荐）
4. 在"语言"下拉菜单中选择：
   - **英文** → 英文输出
   - **中文** → 中文输出

### 流程模式推荐

对于 MCM/ICM 竞赛：

| 模式 | Token 用量 | 质量 | 推荐用于 |
|------|-----------|------|----------|
| **智能模式** | 基准 | 好 | 简单问题 |
| **标准模式** | +20% | 更好 | 大多数问题 |
| **增强模式** | +50% | 最佳 | 复杂问题 |
| **获奖级模式** | +80% | 优秀 | 最终提交 |

**推荐：** MCM/ICM 使用 **增强模式** 或 **获奖级模式**。

---

## 📄 英文论文输出

### 论文结构（美赛格式）

英文论文遵循标准美赛结构：

```
1. Summary Sheet（标题 + 摘要 + 关键词）
2. Introduction（引言）
   - Problem Background（问题背景）
   - Restatement of the Problem（问题重述）
   - Our Approach（我们的方法）
3. Problem Analysis（问题分析）
4. Assumptions and Justifications（假设与理由）
5. Notations and Data Preprocessing（符号说明与数据预处理）
6. Model Development and Solution（模型建立与求解）
   - Problem 1, 2, 3...（每个问题单独一节）
7. Sensitivity Analysis and Model Validation（灵敏度分析与模型验证）
8. Strengths and Weaknesses（优缺点评价）
9. Conclusions（结论）
10. Letter to Decision Maker（给决策者的信/Memo）
11. References（参考文献）
```

### 英文 Prompt 模板

系统为每个部分使用专门的英文 prompt：

**Summary Sheet：**
- Title：10-15 个单词，描述性强
- Abstract：1-2 页，结构化段落
- Keywords：5-6 个关键词，空格分隔

**Introduction：**
- Background 引用 3-5 篇文献
- Problem restatement 用自己的话重述
- Approach overview 方法概述

**Problem Analysis：**
- Mathematical nature identification 数学类型识别
- Data characteristics 数据特征
- Modeling strategy 建模策略（baseline + improved + innovative）

**Model Development：**
- Rigorous mathematical formulation 严格的数学表述
- Algorithm design 算法设计
- Results with specific numerical values 具体数值结果
- Model comparison tables 模型对比表格

**Sensitivity Analysis：**
- Parameter variation（±10%, ±20%, ±50%）参数变化
- Impact on results 对结果的影响
- Robustness conclusions 鲁棒性结论

### 质量期望

英文输出质量与中文相当：

- ✅ 同等水平的数学严谨性
- ✅ 正确的学术写作风格
- ✅ 准确的术语使用
- ✅ 专业的格式排版
- ✅ 完整的引用和参考文献

---

## 🎓 LaTeX 支持

### 为什么美赛推荐使用 LaTeX？

LaTeX 是 **强烈推荐** 的美赛排版工具，因为：

1. **专业排版**: 漂亮的数学公式
2. **标准格式**: 符合竞赛要求
3. **易于编辑**: 内容与格式分离
4. **参考文献管理**: 自动生成参考文献
5. **版本控制**: 基于文本，支持 git

### LaTeX 模板特性

MCM LaTeX 模板包括：

- **mcmthesis** 类兼容性
- 正确的章节结构
- 数学公式环境
- 表格和图片环境
- 引用支持（`\upcite{N}`）
- 专业格式

### LaTeX 输出示例

```latex
\title{An Optimized Multi-Objective Agricultural Planning Model Using Harris Hawks Algorithm}

\begin{abstract}
This paper addresses the agricultural planning optimization problem...

For Problem 1, we formulate a multi-objective optimization model...

\textbf{Keywords:} HHO, MOHHO, Genetic Algorithm, Monte Carlo Simulation, Multi-Objective Optimization
\end{abstract}

\section{Introduction}
\subsection{Problem Background}
The problem of resource allocation has been extensively studied in operations research\upcite{1}...
```

### 编译 LaTeX

**选项 1：在线编译器（推荐）**

1. Overleaf: https://www.overleaf.com/
2. 复制生成的 `.tex` 文件
3. 上传到 Overleaf
4. 使用 XeLaTeX 或 PDFLaTeX 编译

**选项 2：本地编译**

```bash
# 安装 TeX Live（Linux/macOS）或 MiKTeX（Windows）
# 然后编译：
xelatex paper.tex
bibtex paper.aux
xelatex paper.tex
xelatex paper.tex
```

**选项 3：VS Code + LaTeX Workshop**

1. 安装 "LaTeX Workshop" 扩展
2. 打开 `.tex` 文件
3. 按 `Ctrl+Alt+B` 编译

---

## ✨ 最佳实践

### 1. 问题描述

**好的描述：**
```
问题：某农场有 50 亩土地，可种植玉米和小麦。
玉米每亩产量 800kg，成本 500 元，售价 2 元/kg；
小麦每亩产量 600kg，成本 400 元，售价 2.5 元/kg。
如何分配种植面积使利润最大？

请建立线性规划模型并求解。
```

**不好的描述：**
```
帮我做个优化题
```

### 2. 语言设置

对于 MCM/ICM：
- **模板**: 美赛（MCM/ICM）
- **语言**: 英文
- **格式**: LaTeX（推荐）或 Markdown
- **流程**: 增强模式或获奖级模式

### 3. 迭代优化

如果第一次输出不理想：

1. 在问题描述中提供更多背景信息
2. 明确指出需要改进的地方
3. 提供示例或参考格式
4. 调整模型参数

**示例：**
```
上一个回答中，模型建立得很好，但是：
1. 请增加敏感性分析
2. 补充更多的图表可视化
3. 参考文献格式改为 APA 格式
```

### 4. 结果验证

始终验证 AI 生成的内容：

- ✅ 检查模型假设的合理性
- ✅ 验证代码逻辑和计算
- ✅ 检查论文完整性（摘要、关键词、参考文献）
- ✅ 验证数值结果

### 5. API 模型选择

对于英文输出，推荐模型：

| Agent | 推荐模型 | 原因 |
|-------|---------|------|
| 协调者 | Claude 3.5 Sonnet | 推理能力强 |
| 建模者 | DeepSeek Chat | 数学能力强 |
| 代码者 | GPT-4o | 代码能力最佳 |
| 写作者 | DeepSeek Chat | 性价比高 |

---

## 📊 示例工作流

### 逐步解决 MCM 问题

**问题：** 2024 MCM Problem A - Resource Allocation

**步骤 1：准备问题陈述**
```
从 MCM ICM 官网复制完整的问题陈述。
包含所有数据文件和补充材料。
```

**步骤 2：配置设置**
```
模板：美赛（MCM/ICM）
语言：英文
格式：LaTeX
流程：获奖级模式
```

**步骤 3：提交问题**
```
在聊天界面中粘贴完整的问题陈述。
上传任何数据文件（CSV、Excel 等）。
点击"开始分析"。
```

**步骤 4：监控进度**
```
系统将自动：
1. 分析问题（协调者）
2. 建立数学模型（建模者）
3. 编写和执行代码（代码者）
4. 生成论文（写作者）
```

**步骤 5：审查和完善**
```
审查生成的论文：
- 检查数学公式
- 验证数值结果
- 确保所有问题都得到解决
- 根据需要请求修改
```

**步骤 6：导出和提交**
```
下载 LaTeX 源代码。
使用 Overleaf 或本地 TeX 编译为 PDF。
添加队伍编号和最终格式。
提交到 MCM/ICM 门户。
```

---

## 🔧 技术细节

### 后端配置

**模板文件：**
- `backend/app/config/mcm_template.toml` - 英文 Markdown 模板
- `backend/app/config/mcm_latex_template.toml` - 英文 LaTeX 模板
- `backend/app/config/md_template.toml` - 中文模板

**语言选择：**
```python
# 后端根据以下参数确定模板：
comp_template: CompTemplate.CHINA | CompTemplate.AMERICAN
format_output: FormatOutPut.Markdown | FormatOutPut.LaTeX
language: "zh-CN" | "en-US"
```

### 前端 i18n

**语言文件：**
- `frontend/src/locales/zh-CN.ts` - 中文翻译
- `frontend/src/locales/en-US.ts` - 英文翻译
- `frontend/src/locales/index.ts` - i18n 配置

**切换语言：**
```typescript
import { setLocale } from '@/locales';
setLocale('en-US'); // 或 'zh-CN'
```

---

## 📚 其他资源

### 官方 MCM/ICM 资源

- [COMAP MCM/ICM 官网](https://www.comap.com/undergraduate/contests/mcm)
- [MCM/ICM 问题档案](https://www.comap.com/undergraduate/contests/mcm-icm-problems)
- [MCM/ICM 竞赛规则](https://www.comap.com/undergraduate/contests/mcm-icm-rules)

### LaTeX 资源

- [Overleaf MCM 模板](https://www.overleaf.com/latex/templates/mcm-icm-template)
- [LaTeX 数学符号](https://oeis.org/wiki/List_of_LaTeX_mathematical_symbols)
- [LaTeX 表格生成器](https://www.tablesgenerator.com/)

### MathModelAgent 资源

- [快速开始指南](./quickstart_en.md)
- [部署教程](./deployment.md)
- [示例案例](./examples.md)
- [FAQ](./faq.md)

---

## ❓ 故障排查

### Q: 英文输出质量差

**A:** 
1. 使用更强的模型（Claude 3.5、GPT-4o）
2. 提供更详细的问题描述
3. 在 prompt 中明确"用学术英语写作"
4. 将流程模式增加到增强或获奖级

### Q: LaTeX 编译失败

**A:**
1. 检查是否缺少宏包（添加到导言区）
2. 验证图片文件路径
3. 使用 Overleaf 更容易调试
4. 检查需要转义的特殊字符

### Q: 参考文献不显示

**A:**
1. 确保参考文献环境正确
2. LaTeX 编译后运行 BibTeX
3. 检查引用键与参考文献列表匹配
4. 美赛模板使用 `\upcite{N}` 格式

### Q: 语言无法切换

**A:**
1. 清除浏览器缓存和 localStorage
2. 刷新页面
3. 检查浏览器控制台错误
4. 验证语言文件已加载

---

## 🎯 成功检查清单

提交 MCM/ICM 论文前：

- [ ] 所有问题都已解决
- [ ] Summary sheet 完整（标题、摘要、关键词）
- [ ] 数学公式正确
- [ ] 代码结果已验证
- [ ] 包含敏感性分析
- [ ] 优缺点评价诚实
- [ ] 参考文献格式正确
- [ ] 已添加队伍编号
- [ ] PDF 编译无错误
- [ ] 符合页数限制（最多 25 页）

---

**祝你在 MCM/ICM 竞赛中取得好成绩！** 🏆

需要帮助？加入我们的社区：
- Discord: https://discord.gg/3Jmpqg5J
- GitHub Issues: https://github.com/leozer534-coder/math-modeling-agent/issues
- QQ 群：699970403
