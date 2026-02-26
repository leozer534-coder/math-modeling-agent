# 🚀 快速开始指南（5 分钟上手）

本指南将帮助你在 5 分钟内快速启动 MathModelAgent 并运行第一个示例。

## 前置要求

- **Docker** 和 **Docker Compose**（推荐）或
- **Python 3.10+**、**Node.js 18+**、**Redis**

## 方案一：Docker 快速启动（推荐 ⭐）

### 步骤 1：克隆项目

```bash
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent
```

### 步骤 2：启动服务

```bash
docker-compose up
```

等待所有服务启动完成（约 1-2 分钟）。

### 步骤 3：访问界面

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000

### 步骤 4：配置 API Key

1. 点击左侧边栏的头像图标
2. 输入你的 API Key（支持 DeepSeek、OpenAI 等）
3. 点击保存

### 步骤 5：运行第一个示例

1. 在聊天界面输入数学建模问题，例如：
   ```
   问题：某农场有 50 亩土地，可种植玉米和小麦。
   玉米每亩产量 800kg，成本 500 元，售价 2 元/kg；
   小麦每亩产量 600kg，成本 400 元，售价 2.5 元/kg。
   如何分配种植面积使利润最大？
   ```
2. 点击发送，等待 AI 自动分析、建模、求解并生成论文

✅ **完成！** 你现在已经成功运行了 MathModelAgent！

---

## 方案二：本地部署（开发者）

### 步骤 1：克隆项目

```bash
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent
```

### 步骤 2：启动 Redis

**macOS:**
```bash
brew install redis
redis-server
```

**Linux:**
```bash
sudo apt-get install redis-server
redis-server
```

**Windows:**
下载并运行 [Redis for Windows](https://github.com/microsoftarchive/redis/releases)

### 步骤 3：配置后端

```bash
cd backend

# 复制环境配置
cp .env.example .env.dev

# 编辑 .env.dev，设置你的 API Key
# 至少设置 COORDINATOR_API_KEY
```

### 步骤 4：安装后端依赖

```bash
# 推荐使用 uv（更快）
pip install uv
uv sync

# 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 步骤 5：启动后端

```bash
# macOS/Linux:
ENV=DEV uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120 --reload

# Windows:
set ENV=DEV
uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120
```

### 步骤 6：启动前端

```bash
cd frontend

# 安装 pnpm（如未安装）
npm install -g pnpm

# 安装依赖
pnpm i

# 启动开发服务器
pnpm run dev
```

### 步骤 7：访问并配置

打开 http://localhost:5173，按上述步骤配置 API Key

---

## 常见问题

### Q: 启动后无法访问前端？

**A:** 检查后端和 Redis 是否正常运行：
```bash
# 查看 Docker 容器状态
docker-compose ps

# 查看后端日志
docker-compose logs backend
```

### Q: API Key 应该设置哪个模型？

**A:** 推荐使用 **DeepSeek**，性价比高。也可以使用 OpenAI、Claude 等。在 `.env.dev` 中配置：
```env
COORDINATOR_API_KEY=sk-your-key
COORDINATOR_MODEL=deepseek/deepseek-chat
COORDINATOR_BASE_URL=https://api.deepseek.com
```

### Q: 代码执行失败？

**A:** 检查是否正确安装 Jupyter：
```bash
# 在后端虚拟环境中
pip install jupyter
```

### Q: 如何查看生成的论文？

**A:** 生成的文件保存在 `backend/project/work_dir/xxx/` 目录：
- `notebook.ipynb` - 代码执行记录
- `res.md` - 最终论文（Markdown 格式）

---

## 下一步

- 📖 查看 [详细部署教程](./deployment.md) 了解更多部署选项
- 📚 查看 [示例案例](./examples.md) 学习更多使用场景
- ❓ 查看 [FAQ](./faq.md) 解决常见问题
- 🎥 查看 [视频教程](https://www.bilibili.com/)（待添加）

---

**遇到问题？** 加入我们的社区：
- QQ 群：699970403
- [Discord](https://discord.gg/3Jmpqg5J)
- [GitHub Issues](https://github.com/leozer534-coder/math-modeling-agent/issues)
