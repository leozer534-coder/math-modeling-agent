<h1 align="center">🤖 MathModelAgent 📐</h1>
<p align="center">
    <img src="./docs/icon.png" height="250px">
</p>
<h4 align="center">
    专为数学建模设计的 AI Agent 系统<br>
    自动完成数学建模、代码求解、论文撰写全流程
</h4>

<h5 align="center">简体中文 | <a href="README_EN.md">English</a></h5>

<p align="center">
    <a href="https://github.com/leozer534-coder/math-modeling-agent/stargazers"><img src="https://img.shields.io/github/stars/leozer534-coder/math-modeling-agent" alt="GitHub stars"></a>
    <a href="https://github.com/leozer534-coder/math-modeling-agent/network/members"><img src="https://img.shields.io/github/forks/leozer534-coder/math-modeling-agent" alt="GitHub forks"></a>
    <a href="https://github.com/leozer534-coder/math-modeling-agent/issues"><img src="https://img.shields.io/github/issues/leozer534-coder/math-modeling-agent" alt="GitHub issues"></a>
    <a href="https://github.com/leozer534-coder/math-modeling-agent/blob/main/LICENSE"><img src="https://img.shields.io/github/license/leozer534-coder/math-modeling-agent" alt="License"></a>
    <a href="https://pd.qq.com/s/7rfbai3au"><img src="https://img.shields.io/badge/QQ 频道-MathModelAgent-blue" alt="QQ Channel"></a>
</p>

## 🌟 愿景

**将 3 天的比赛时间缩短为 1 小时** <br> 
**AI 辅助完成获奖级别的数学建模论文**

> ⚡ **5 分钟快速开始** → [查看快速入门指南](docs/md/quickstart.md)

<p align="center">
    <img src="./docs/index.png" alt="主界面" width="800">
    <br><em>图 1: MathModelAgent 主界面 - 智能对话式建模</em>
</p>

<p align="center">
    <img src="./docs/chat.png" alt="对话界面" width="800">
    <br><em>图 2: 自然语言交互，AI 自动理解问题</em>
</p>

<p align="center">
    <img src="./docs/coder.png" alt="代码执行" width="800">
    <br><em>图 3: 自动编写并执行 Python 代码求解</em>
</p>

<p align="center">
    <img src="./docs/writer.png" alt="论文生成" width="800">
    <br><em>图 4: 自动生成完整建模论文</em>
</p>

---

## ✨ 功能特性

### 🤖 多 Agent 协作系统

MathModelAgent 采用多 Agent 协作架构，模拟专业建模团队：

| Agent | 角色 | 职责 |
|-------|------|------|
| 🎯 **协调者** | 团队 Leader | 任务分解、调度、结果整合 |
| 📐 **建模者** | 数学专家 | 问题分析、模型建立、公式推导 |
| 💻 **代码者** | 编程专家 | 代码实现、调试、可视化 |
| ✍️ **写作者** | 论文专家 | 论文撰写、格式排版、参考文献 |

### 🔧 核心技术

- **自动建模**: 🔍 智能分析问题，选择合适的数学模型
- **代码执行**: 💻 
  - 本地 Jupyter：代码保存为 notebook 方便再编辑
  - 云端执行：支持 [E2B](https://e2b.dev/) 和 [Daytona](https://app.daytona.io/) 沙箱环境
- **论文生成**: 📝 自动生成符合比赛规范的完整论文
- **多模型支持**: 🔄 每个 Agent 可配置不同的 LLM（DeepSeek、GPT-4、Claude 等）
- **全模型兼容**: 🤖 支持 [LiteLLM](https://docs.litellm.ai/docs/providers) 的所有模型
- **低成本**: 💰 Agentless 工作流，不依赖昂贵的 Agent 框架
- **自定义模板**: 🧩 可为每个子任务单独设置 prompt 模板

### 📊 支持的模型类型

- **优化类**: 线性规划、整数规划、非线性规划、动态规划、多目标优化
- **预测类**: 时间序列、回归分析、机器学习预测
- **评价类**: AHP、模糊综合评价、TOPSIS、熵权法
- **分类聚类**: KNN、决策树、随机森林、SVM、K-means
- **微分方程**: ODE、PDE、差分方程
- **图论**: 最短路径、最小生成树、网络流

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐 ⭐）

```bash
# 1. 克隆项目
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent

# 2. 启动服务
docker-compose up

# 3. 访问界面
# 前端：http://localhost:5173
# 后端：http://localhost:8000

# 4. 配置 API Key（侧边栏 → 头像 → API Key）
```

### 方式二：本地部署

```bash
# 1. 克隆项目
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent

# 2. 启动 Redis
redis-server

# 3. 启动后端
cd backend
pip install uv
uv sync
source .venv/bin/activate  # Windows: venv\Scripts\activate
ENV=DEV uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动前端
cd frontend
pnpm i
pnpm run dev
```

> 📖 **详细教程**: [部署文档](docs/md/deployment.md) | [快速开始](docs/md/quickstart.md)

---

## 📚 文档导航

| 文档 | 描述 | 预计时间 |
|------|------|----------|
| [🚀 快速开始](docs/md/quickstart.md) | 5 分钟上手指南 | 5 分钟 |
| [📦 部署教程](docs/md/deployment.md) | Docker/本地/生产部署 | 15 分钟 |
| [📚 使用教程](docs/md/tutorial.md) | 完整功能说明 | 30 分钟 |
| [📊 示例案例](docs/md/examples.md) | 12+ 真实案例 | 20 分钟 |
| [❓ FAQ](docs/md/faq.md) | 常见问题解答 | 10 分钟 |

---

## 🎬 视频 Demo

<video src="https://github.com/user-attachments/assets/954cb607-8e7e-45c6-8b15-f85e204a0c5d"></video>

> **演示**: 使用 MathModelAgent 解决线性规划问题，自动生成完整论文

📺 **更多视频教程**: [B 站](https://www.bilibili.com/)（待添加）| [YouTube](https://www.youtube.com/)（待添加）

---

## 🗺️ 后期计划

### ✅ 已完成

- [x] WebUI 和 CLI
- [x] Docker 部署
- [x] 云端代码执行器（E2B、Daytona）
- [x] 文献引用
- [x] 测试案例
- [x] 完善的教程、文档

### 🚧 开发中

- [ ] Web 服务（云端部署）
- [ ] 英文支持（美赛）
- [ ] LaTeX 模板集成
- [ ] 视觉模型接入
- [ ] Human-in-the-loop (HIL)

### 📋 计划中

- [ ] 多语言支持（R、Matlab）
- [ ] 更多绘图（napkin、draw.io、mermaid.js）
- [ ] Benchmark 测试
- [ ] Web Search Tool
- [ ] RAG 知识库
- [ ] A2A Hand Off

---

## 📖 使用教程

### 三种部署方式

选择最适合你的方案：

1. **[Docker 部署](docs/md/deployment.md#docker-部署推荐)** - 最简单，推荐新手
2. **[本地部署](docs/md/deployment.md#本地部署开发)** - 适合开发者
3. **[自动脚本](https://github.com/Fitia-UCAS/mmaAutoSetupRun)** - 社区贡献

### 快速示例

**问题**: 农场种植优化

```
问题：某农场有 50 亩土地，可种植玉米和小麦。
玉米每亩产量 800kg，成本 500 元，售价 2 元/kg；
小麦每亩产量 600kg，成本 400 元，售价 2.5 元/kg。
如何分配种植面积使利润最大？
```

**输出**:
- ✅ 数学模型（线性规划）
- ✅ Python 代码求解
- ✅ 完整论文（含摘要、关键词、参考文献）

📊 **更多案例**: [查看示例文档](docs/md/examples.md)

---

## 🤝 贡献和开发

### 开发资源

- [DeepWiki](https://deepwiki.com/leozer534-coder/math-modeling-agent) - AI 代码导航
- [Zread](https://zread.ai/leozer534-coder/math-modeling-agent) - 代码阅读

### 贡献指南

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

### 提交案例

如果你有好的案例，欢迎提交到示例仓库：
[MathModelAgent-Example](https://github.com/leozer534-coder/math-modeling-agent-Example)

### 开发提示

Clone 项目后，安装 **Todo Tree** 插件查看代码中的 TODO 注释。

`.cursor/*` 目录包含项目架构、规则和 MCP 配置，方便开发使用。

---

## 📄 版权 License

- ✅ **个人免费使用**
- ❌ **请勿商业用途**
- 💼 商业用途请联系作者

[查看详细 License](docs/md/License.md)

---

## 🙏 参考项目

感谢以下优秀项目：

- [OpenCodeInterpreter](https://github.com/OpenCodeInterpreter/OpenCodeInterpreter)
- [TaskWeaver](https://github.com/microsoft/TaskWeaver)
- [Code-Interpreter](https://github.com/MrGreyfun/Local-Code-Interpreter)
- [Latex](https://github.com/Veni222987/MathModelingLatexTemplate)
- [Agent Laboratory](https://github.com/SamuelSchmidgall/AgentLaboratory)
- [ai-manus](https://github.com/Simpleyyt/ai-manus)

---

## 💖 赞助支持

[☕️ 给作者买一杯咖啡](docs/md/sponser.md)

### 企业赞助

<div align="center">
    <a href="https://share.302.ai/UoTruU" target="_blank">
        <img src="./docs/302ai.jpg" alt="302.AI" width="400">
    </a>
</div>

[302.AI](https://share.302.ai/UoTruU) 是一个按用量付费的企业级 AI 资源平台，提供最新的 AI 模型和 API

### 贡献者

[danmo-tyc](https://github.com/danmo-tyc)

---

## 👥 社区交流

有问题？加入我们的社区！

- **腾讯频道**: [MathModelAgent](https://pd.qq.com/s/7rfbai3au)
- **QQ 群 1**: 699970403
- **QQ 群 2**: 779159301
- **Discord**: [加入服务器](https://discord.gg/3Jmpqg5J)

<div align="center">
    <img src="./docs/qq.jpg" alt="QQ 群" height="400">
    <br><em>扫码加入 QQ 交流群</em>
</div>

---

## ⚠️ 免责声明

> 本项目处于**实验探索阶段**，存在改进空间。AI 生成内容仅供参考，目前直接参加国赛获奖仍有难度。作者会持续优化更新，欢迎贡献。

---

<p align="center">
    <strong>🌟 如果这个项目对你有帮助，请给一个 Star！</strong>
</p>

<p align="center">
    Made with ❤️ by MathModelAgent Team
</p>
