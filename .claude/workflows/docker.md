---
name: docker
description: Docker 部署、沙箱构建和安全配置
---

# Docker 工作流

## 服务管理

| 命令 | 说明 |
|------|------|
| `docker-compose up -d` | 后台启动所有服务 |
| `docker-compose logs -f` | 查看实时日志 |
| `docker-compose logs -f backend` | 仅查看后端日志 |
| `docker-compose down` | 停止所有服务 |
| `docker-compose build --no-cache` | 重建所有镜像 |
| `docker-compose restart backend` | 重启后端服务 |

## 服务组成

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 应用 |
| frontend | 5173 | Vue 开发服务器 |
| redis | 6379 | Redis 缓存 |

## 沙箱镜像构建

```bash
# 构建沙箱镜像
docker build -f backend/Dockerfile.sandbox -t mathmodel-sandbox .

# 验证沙箱安全
docker run --rm mathmodel-sandbox whoami  # 应输出非 root 用户
```

### 沙箱安全配置
- 内存限制: 512MB
- CPU 配额: 50%
- 执行超时: 300 秒
- 网络隔离: 默认无网络
- 只读文件系统 + tmpfs
- 非 root 用户运行
- 禁止提权

## 镜像管理

```bash
# 查看项目相关镜像
docker images | findstr mathmodel

# 清理悬挂镜像
docker image prune -f

# 清理所有未使用资源
docker system prune -f
```

## 环境变量

- 开发环境: `backend/.env.dev`
- 示例文件: `backend/.env.example`
- Docker 环境: 通过 `docker-compose.yml` 的 `env_file` 注入

## 健康检查

```bash
# 检查后端服务
curl http://localhost:8000/health

# 检查 Redis
docker-compose exec redis redis-cli ping
```
