# 🇺🇸 MCM/ICM English Support Guide

This guide explains how to use MathModelAgent for the Mathematical Contest in Modeling (MCM/ICM) with full English support.

---

## 📋 Table of Contents

- [Overview](#overview)
- [English UI Interface](#english-ui-interface)
- [MCM Template Selection](#mcm-template-selection)
- [English Paper Output](#english-paper-output)
- [LaTeX Support](#latex-support)
- [Best Practices](#best-practices)
- [Example Workflow](#example-workflow)

---

## 🌟 Overview

MathModelAgent provides comprehensive English support for MCM/ICM competitions:

- ✅ **Bilingual UI**: Switch between Chinese and English instantly
- ✅ **English Prompts**: Optimized prompt templates for English paper generation
- ✅ **MCM Templates**: Dedicated templates for American competition format
- ✅ **LaTeX Output**: Professional LaTeX formatting with mcmthesis template
- ✅ **Markdown Output**: Clean English Markdown papers

---

## 🖥️ English UI Interface

### Switching Language

**In the Web Interface:**

1. Look for the language selector in the top navigation bar
2. Click on the language icon (🇨🇳/🇺🇸)
3. Select "English" or "简体中文"

**Keyboard Shortcut:**
- Press `Ctrl+L` to toggle language (if implemented)

**Persistent Settings:**
- Your language preference is saved in browser localStorage
- Next visit will automatically use your preferred language

### Available English Translations

All major UI components are translated:

- ✅ Navigation and menus
- ✅ Home page content
- ✅ Chat interface
- ✅ Settings and configuration
- ✅ Error messages and notifications
- ✅ Agent descriptions
- ✅ Workflow explanations

---

## 📝 MCM Template Selection

### Template Types

MathModelAgent provides two MCM template formats:

| Template | Format | Use Case |
|----------|--------|----------|
| **MCM Markdown** | `.md` | Quick drafting, easy editing |
| **MCM LaTeX** | `.tex` | Professional typesetting, final submission |

### How to Select

**In the Chat Interface:**

1. Click on "Task Parameter Settings" (设置图标)
2. Under "Template" dropdown, select:
   - **CUMCM** → Chinese competition (国赛)
   - **MCM/ICM** → American competition (美赛)
3. Under "Format" dropdown, select:
   - **Markdown** → Easy editing
   - **LaTeX** → Professional typesetting (recommended for MCM)
4. Under "Language" dropdown, select:
   - **English** → English output
   - **中文** → Chinese output

### Workflow Mode Recommendations

For MCM/ICM competitions:

| Mode | Token Usage | Quality | Recommended For |
|------|-------------|---------|-----------------|
| **Smart** | Baseline | Good | Simple problems |
| **Standard** | +20% | Better | Most problems |
| **Enhanced** | +50% | Best | Complex problems |
| **Award-Winning** | +80% | Excellent | Final submission |

**Recommendation:** Use **Enhanced Mode** or **Award-Winning Mode** for MCM/ICM.

---

## 📄 English Paper Output

### Paper Structure (MCM Format)

The English paper follows standard MCM structure:

```
1. Summary Sheet (Title + Abstract + Keywords)
2. Introduction
   - Problem Background
   - Restatement of the Problem
   - Our Approach
3. Problem Analysis
4. Assumptions and Justifications
5. Notations and Data Preprocessing
6. Model Development and Solution
   - Problem 1, 2, 3... (each with subsections)
7. Sensitivity Analysis and Model Validation
8. Strengths and Weaknesses
9. Conclusions
10. Letter to Decision Maker (Memo)
11. References
```

### English Prompt Templates

The system uses specialized English prompts for each section:

**Summary Sheet:**
- Title: 10-15 words, descriptive
- Abstract: 1-2 pages, structured paragraphs
- Keywords: 5-6 keywords, space-separated

**Introduction:**
- Background with 3-5 references
- Problem restatement in own words
- Approach overview

**Problem Analysis:**
- Mathematical nature identification
- Data characteristics
- Modeling strategy (baseline + improved + innovative)

**Model Development:**
- Rigorous mathematical formulation
- Algorithm design
- Results with specific numerical values
- Model comparison tables

**Sensitivity Analysis:**
- Parameter variation (±10%, ±20%, ±50%)
- Impact on results
- Robustness conclusions

### Quality Expectations

English output quality matches Chinese:

- ✅ Same level of mathematical rigor
- ✅ Proper academic writing style
- ✅ Correct terminology usage
- ✅ Professional formatting
- ✅ Complete citations and references

---

## 🎓 LaTeX Support

### Why Use LaTeX for MCM?

LaTeX is **highly recommended** for MCM/ICM because:

1. **Professional Typesetting**: Beautiful mathematical formulas
2. **Standard Format**: Matches competition requirements
3. **Easy Editing**: Separate content from formatting
4. **Reference Management**: Automatic bibliography
5. **Version Control**: Text-based, git-friendly

### LaTeX Template Features

The MCM LaTeX template includes:

- **mcmthesis** class compatibility
- Proper section structure
- Mathematical equation environments
- Table and figure environments
- Citation support (`\\upcite{N}`)
- Professional formatting

### Example LaTeX Output

```latex
\\title{An Optimized Multi-Objective Agricultural Planning Model Using Harris Hawks Algorithm}

\\begin{abstract}
This paper addresses the agricultural planning optimization problem...

For Problem 1, we formulate a multi-objective optimization model...

\\textbf{Keywords:} HHO, MOHHO, Genetic Algorithm, Monte Carlo Simulation, Multi-Objective Optimization
\\end{abstract}

\\section{Introduction}
\\subsection{Problem Background}
The problem of resource allocation has been extensively studied in operations research\\upcite{1}...
```

### Compiling LaTeX

**Option 1: Online Compiler (Recommended)**

1. Overleaf: https://www.overleaf.com/
2. Copy generated `.tex` file
3. Upload to Overleaf
4. Compile with XeLaTeX or PDFLaTeX

**Option 2: Local Compilation**

```bash
# Install TeX Live (Linux/macOS) or MiKTeX (Windows)
# Then compile:
xelatex paper.tex
bibtex paper.aux
xelatex paper.tex
xelatex paper.tex
```

**Option 3: VS Code + LaTeX Workshop**

1. Install "LaTeX Workshop" extension
2. Open `.tex` file
3. Press `Ctrl+Alt+B` to build

---

## ✨ Best Practices

### 1. Problem Description

**Good:**
```
Problem: A farm has 50 acres of land and can plant corn and wheat.
Corn: 800kg/acre yield, $500 cost, $2/kg selling price
Wheat: 600kg/acre yield, $400 cost, $2.5/kg selling price
How to allocate planting area to maximize profit?

Please establish a linear programming model and solve it.
```

**Bad:**
```
Help me solve an optimization problem
```

### 2. Language Settings

For MCM/ICM:
- **Template**: MCM/ICM
- **Language**: English
- **Format**: LaTeX (recommended) or Markdown
- **Workflow**: Enhanced or Award-Winning

### 3. Iterative Refinement

If the first output needs improvement:

1. Provide more context in the problem description
2. Specify formatting requirements clearly
3. Give examples of desired output format
4. Request specific sections to be revised

**Example:**
```
The model formulation is good, but please:
1. Add more detailed sensitivity analysis
2. Include more visualization charts
3. Change reference format to APA style
```

### 4. Result Verification

Always verify AI-generated content:

- ✅ Check model assumptions for reasonableness
- ✅ Verify code logic and calculations
- ✅ Review paper completeness (abstract, keywords, references)
- ✅ Validate numerical results

### 5. API Model Selection

For English output, recommended models:

| Agent | Recommended Model | Reason |
|-------|------------------|--------|
| Coordinator | Claude 3.5 Sonnet | Strong reasoning |
| Modeler | DeepSeek Chat | Good at math |
| Coder | GPT-4o | Best coding |
| Writer | DeepSeek Chat | Cost-effective |

---

## 📊 Example Workflow

### Step-by-Step MCM Problem

**Problem:** 2024 MCM Problem A - Resource Allocation

**Step 1: Prepare Problem Statement**
```
Copy the complete problem statement from MCM ICM website.
Include all data files and supplementary materials.
```

**Step 2: Configure Settings**
```
Template: MCM/ICM
Language: English
Format: LaTeX
Workflow: Award-Winning Mode
```

**Step 3: Submit Problem**
```
Paste the complete problem statement in the chat interface.
Upload any data files (CSV, Excel, etc.).
Click "Start Analysis".
```

**Step 4: Monitor Progress**
```
The system will automatically:
1. Analyze the problem (Coordinator)
2. Build mathematical models (Modeler)
3. Write and execute code (Coder)
4. Generate the paper (Writer)
```

**Step 5: Review and Refine**
```
Review the generated paper:
- Check mathematical formulations
- Verify numerical results
- Ensure all problems are addressed
- Request revisions if needed
```

**Step 6: Export and Submit**
```
Download the LaTeX source code.
Compile to PDF using Overleaf or local TeX.
Add team number and final formatting.
Submit to MCM/ICM portal.
```

---

## 🔧 Technical Details

### Backend Configuration

**Template Files:**
- `backend/app/config/mcm_template.toml` - English Markdown template
- `backend/app/config/mcm_latex_template.toml` - English LaTeX template
- `backend/app/config/md_template.toml` - Chinese template

**Language Selection:**
```python
# Backend determines template based on:
comp_template: CompTemplate.CHINA | CompTemplate.AMERICAN
format_output: FormatOutPut.Markdown | FormatOutPut.LaTeX
language: "zh-CN" | "en-US"
```

### Frontend i18n

**Language Files:**
- `frontend/src/locales/zh-CN.ts` - Chinese translations
- `frontend/src/locales/en-US.ts` - English translations
- `frontend/src/locales/index.ts` - i18n configuration

**Switching Language:**
```typescript
import { setLocale } from '@/locales';
setLocale('en-US'); // or 'zh-CN'
```

---

## 📚 Additional Resources

### Official MCM/ICM Resources

- [COMAP MCM/ICM Official Website](https://www.comap.com/undergraduate/contests/mcm)
- [MCM/ICM Problem Archives](https://www.comap.com/undergraduate/contests/mcm-icm-problems)
- [MCM/ICM Contest Rules](https://www.comap.com/undergraduate/contests/mcm-icm-rules)

### LaTeX Resources

- [Overleaf MCM Template](https://www.overleaf.com/latex/templates/mcm-icm-template)
- [LaTeX Mathematical Symbols](https://oeis.org/wiki/List_of_LaTeX_mathematical_symbols)
- [LaTeX Tables Generator](https://www.tablesgenerator.com/)

### MathModelAgent Resources

- [Quick Start Guide](./quickstart_en.md)
- [Deployment Guide](./deployment.md)
- [Example Cases](./examples.md)
- [FAQ](./faq.md)

---

## ❓ Troubleshooting

### Q: English output quality is poor

**A:** 
1. Use stronger models (Claude 3.5, GPT-4o)
2. Provide more detailed problem description
3. Specify "Write in academic English" in your prompt
4. Increase workflow mode to Enhanced or Award-Winning

### Q: LaTeX compilation fails

**A:**
1. Check for missing packages (add to preamble)
2. Verify image file paths
3. Use Overleaf for easier debugging
4. Check for special characters that need escaping

### Q: References not showing

**A:**
1. Ensure bibliography environment is correct
2. Run BibTeX after LaTeX compilation
3. Check citation keys match reference list
4. Use `\\upcite{N}` format for MCM template

### Q: Language doesn't switch

**A:**
1. Clear browser cache and localStorage
2. Refresh the page
3. Check browser console for errors
4. Verify language files are loaded

---

## 🎯 Success Checklist

Before submitting your MCM/ICM paper:

- [ ] All problems are addressed
- [ ] Summary sheet is complete (title, abstract, keywords)
- [ ] Mathematical formulas are correct
- [ ] Code results are verified
- [ ] Sensitivity analysis is included
- [ ] Strengths and weaknesses are honest
- [ ] References are properly formatted
- [ ] Team number is added
- [ ] PDF compiles without errors
- [ ] Page limit is respected (25 pages max)

---

**Good luck with your MCM/ICM competition!** 🏆

Need help? Join our community:
- Discord: https://discord.gg/3Jmpqg5J
- GitHub Issues: https://github.com/leozer534-coder/math-modeling-agent/issues
