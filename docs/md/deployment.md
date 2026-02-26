# 📦 详细部署教程

本文档详细介绍 MathModelAgent 的各种部署方式，包括 Docker 部署、本地部署和生产环境部署。

---

## 目录

- [Docker 部署（推荐）](#docker-部署推荐)
- [本地部署（开发）](#本地部署开发)
- [生产环境部署](#生产环境部署)
- [网络环境极差时的配置](#网络环境极差时的配置)
- [故障排查](#故障排查)

---

## Docker 部署（推荐）⭐

### 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 步骤 1：安装 Docker

**Ubuntu/Debian:**
```bash
# 卸载旧版本
sudo apt-get remove docker docker-engine docker.io containerd runc

# 安装
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

**macOS:**
```bash
# 使用 Homebrew
brew install --cask docker

# 或者下载 Docker Desktop
# https://www.docker.com/products/docker-desktop/
```

**Windows:**
下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 步骤 2：克隆项目

```bash
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent
```

### 步骤 3：配置环境变量

```bash
# 复制后端环境配置
cp backend/.env.example backend/.env.dev

# 编辑配置文件
nano backend/.env.dev
# 或者使用你喜欢的编辑器
```

**必须配置的变量：**
```env
# API Key（至少配置一个）
COORDINATOR_API_KEY=sk-your-api-key
COORDINATOR_MODEL=deepseek/deepseek-chat
COORDINATOR_BASE_URL=https://api.deepseek.com

# Redis 配置（Docker 环境使用这个）
REDIS_URL=redis://redis:6379/0

# 安全配置（生产环境必须设置）
API_KEY_MASTER_SECRET=your-32-char-random-secret-here
```

生成随机密钥：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 步骤 4：启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 步骤 5：验证部署

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查前端
curl http://localhost:5173
```

访问：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 步骤 6：管理容器

```bash
# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs redis

# 重新构建
docker-compose build --no-cache

# 完全清理
docker-compose down -v
```

---

## 本地部署（开发）

### 系统要求

- Python 3.10 - 3.12
- Node.js 18+
- Redis 6.0+
- Git

### 步骤 1：安装依赖

**安装 Python:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.10 python3.10-venv python3-pip

# macOS
brew install python@3.10

# Windows
# 下载 https://www.python.org/downloads/
```

**安装 Node.js:**
```bash
# 使用 nvm（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 或者直接下载
# https://nodejs.org/
```

**安装 Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS
brew install redis
brew services start redis

# Windows
# 下载 https://github.com/microsoftarchive/redis/releases
# 或使用 WSL
```

### 步骤 2：克隆项目

```bash
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent
```

### 步骤 3：配置后端

```bash
cd backend

# 复制环境配置
cp .env.example .env.dev

# 编辑配置
nano .env.dev
```

**关键配置项：**
```env
ENV=dev

# LLM 配置
COORDINATOR_API_KEY=sk-your-key
COORDINATOR_MODEL=deepseek/deepseek-chat
COORDINATOR_BASE_URL=https://api.deepseek.com

# Redis 配置（本地环境）
REDIS_URL=redis://localhost:6379/0

# 开发模式
DEBUG=true
LOG_LEVEL=DEBUG
```

### 步骤 4：安装 Python 依赖

**方法一：使用 uv（推荐，更快）**
```bash
# 安装 uv
pip install uv

# 同步依赖
uv sync

# 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate
# Windows:
venv\Scripts\activate
```

**方法二：使用 pip**
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
# 或者使用 pyproject.toml
pip install -e .
```

### 步骤 5：安装 Jupyter（代码执行器）

```bash
# 在虚拟环境中
pip install jupyter ipykernel
```

### 步骤 6：启动后端

```bash
# macOS/Linux:
ENV=DEV uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120 --reload

# Windows:
set ENV=DEV
uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120
```

验证后端启动：
```bash
curl http://localhost:8000/health
```

### 步骤 7：启动前端

```bash
cd frontend

# 安装 pnpm
npm install -g pnpm

# 安装依赖
pnpm install

# 启动开发服务器
pnpm run dev
```

访问 http://localhost:5173

---

## 生产环境部署

### 安全配置

**1. 设置强密钥**
```bash
# 生成随机密钥
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

在 `.env.prod` 中设置：
```env
API_KEY_MASTER_SECRET=your-generated-secret-here
DEBUG=false
LOG_LEVEL=INFO
```

**2. 配置 CORS**
```env
CORS_ALLOW_ORIGINS=https://your-domain.com
```

**3. 使用 HTTPS**

配置反向代理（Nginx 示例）：
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker 生产部署

```bash
# 使用生产配置构建
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 或者设置环境变量
ENV=PROD docker-compose up -d
```

### 监控和日志

```bash
# 查看实时日志
docker-compose logs -f backend

# 资源监控
docker stats

# 健康检查
watch -n 5 'docker-compose ps'
```

---

## 网络环境极差时的配置

### 问题场景

- 无法访问 Docker Hub
- 无法访问 PyPI
- 无法访问 npm
- API 访问受限

### 解决方案

**1. 使用国内镜像源**

**Docker 镜像加速:**
```bash
# 配置 /etc/docker/daemon.json (Linux)
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

**Python pip 镜像:**
```bash
# 使用清华镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者配置 pip.conf
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
```

**Node.js npm 镜像:**
```bash
# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com

# 或者在 .npmrc 中添加
registry=https://registry.npmmirror.com
```

**2. 离线安装依赖**

在有网络的环境中下载依赖：
```bash
# 下载 Python 依赖
pip download -r requirements.txt -d ./packages

# 下载 Node.js 依赖
npm pack package.json
```

传输到目标机器后安装：
```bash
# 安装 Python 包
pip install --no-index --find-links=./packages -r requirements.txt

# 安装 Node.js 包
npm install ./package-name-version.tgz
```

**3. 使用代理**

```bash
# 临时设置代理
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port

# 或者在 .env 中设置
HTTP_PROXY=http://proxy-server:port
HTTPS_PROXY=http://proxy-server:port
```

**4. 使用自动部署脚本（社区贡献）**

参考：[mmaAutoSetupRun](https://github.com/Fitia-UCAS/mmaAutoSetupRun)

---

## 故障排查

### 常见问题

**1. Docker 容器无法启动**

```bash
# 查看详细日志
docker-compose logs backend

# 常见问题：
# - 端口被占用：修改 docker-compose.yml 中的端口映射
# - 内存不足：增加 Docker 资源限制
# - 配置文件错误：检查 .env.dev
```

**2. Redis 连接失败**

```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 测试 Redis 连接
docker-compose exec redis redis-cli ping
# 应该返回 PONG

# 本地部署检查
redis-cli ping
```

**3. 后端启动失败**

```bash
# 检查 Python 版本
python --version
# 应该是 3.10 - 3.12

# 检查依赖是否完整
pip list

# 查看错误日志
tail -f backend/logs/app.log
```

**4. 前端无法连接后端**

检查前端配置：
```bash
# frontend/.env.development
VITE_API_URL=http://localhost:8000
```

**5. API Key 验证失败**

```bash
# 检查 .env.dev 配置
cat backend/.env.dev | grep API_KEY

# 测试 API 连接
curl -X POST http://localhost:8000/api/test \
  -H "Authorization: Bearer your-api-key"
```

### 获取帮助

- 📖 查看 [FAQ](./faq.md)
- 💬 加入 QQ 群：699970403
- 🐛 提交 [GitHub Issue](https://github.com/leozer534-coder/math-modeling-agent/issues)
- 📧 联系作者

---

## 性能优化建议

**1. 增加内存**
- 建议至少 8GB RAM
- Docker 容器限制：`docker-compose.yml` 中设置 `mem_limit`

**2. 使用 SSD**
- 代码执行和文件读写会更快

**3. 本地缓存**
- 配置 LLM API 缓存减少重复请求
- 使用 Redis 持久化

**4. 并发配置**
```env
# 增加 Redis 连接数
REDIS_MAX_CONNECTIONS=50

# 调整 uvicorn worker 数
UVICORN_WORKERS=4
```

---

**部署完成后，查看 [快速开始指南](./quickstart.md) 开始使用！**
