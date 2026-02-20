---
name: backend-dev
description: 后端开发快速启动 — 包含完整的开发、检查和测试流程
---

# 后端开发工作流

## 环境准备
1. 确认 Python 虚拟环境已激活: `backend/.venv/`
2. 确认依赖已安装: `cd backend && uv sync`
3. 确认 Redis 服务正常运行

## 开发流程

### 1. 需求理解
- 阅读相关代码，理解现有架构
- 确定修改范围和影响面
- 如涉及重大变更，先咨询 `architect` 角色

### 2. 编写代码
- 遵循 `backend-dev` Agent 定义中的开发规范
- 异步优先，类型标注完整
- 中文注释

### 3. 代码检查
```bash
cd backend && uv run ruff check app/ --fix
cd backend && uv run ruff format app/
```

### 4. 运行测试
```bash
cd backend && uv run pytest app/tests/ -v
```

### 5. 验证功能
```bash
cd backend && set ENV=DEV && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 关键目录
| 目录 | 说明 |
|------|------|
| `app/core/agents/` | 智能体模块 (26个) |
| `app/core/workflow/` | 工作流引擎 |
| `app/core/flows.py` | 流程编排核心 |
| `app/core/hil/` | 人机交互 |
| `app/core/a2a/` | Agent-to-Agent 通信 |
| `app/routers/` | API 路由 (8个) |
| `app/services/` | 业务服务 |
| `app/schemas/` | 数据契约 |
| `app/tools/` | 工具模块 |

## 新模块开发步骤
1. 在对应目录创建文件
2. 定义 Pydantic Schema (`schemas/`)
3. 实现业务逻辑
4. 注册到路由/流程中
5. 运行 Ruff 检查
6. 通知 `test-engineer` 编写测试
