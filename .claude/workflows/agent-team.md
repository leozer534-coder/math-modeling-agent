---
name: agent-team
description: 启动多智能体并行工作 — 商业级团队协作流程
---

# Agent Team 工作流 (商业级)

创建一个高效的 Agent Team 来并行处理开发任务。

## 第一步：需求分析与任务拆解

1. **理解需求全貌**: 明确用户要解决什么问题
2. **识别模块边界**: 哪些是纯前端、纯后端、跨层、测试
3. **依赖关系分析**: 哪些任务有先后依赖，哪些可并行
4. **风险评估**: 哪些任务涉及核心逻辑变更，需要架构审查

## 第二步：角色选择矩阵

| 任务类型 | 分配角色 | 说明 |
|---------|---------|------|
| Agent 核心逻辑 | `backend-dev` | 智能体、流程编排、工作流 |
| API 接口开发 | `backend-dev` | 路由、Schema、服务层 |
| Vue 组件/页面 | `frontend-dev` | UI、交互、状态管理 |
| WebSocket/联调 | `fullstack-dev` | 前后端通信、数据契约同步 |
| 单元/集成测试 | `test-engineer` | 测试用例、覆盖率 |
| 架构决策/审查 | `architect` | 设计方案评审、代码审查 |
| 部署/安全 | `devops` | Docker、沙箱、安全加固 |

## 第三步：创建团队

```
1. 使用 TeamCreate 创建团队
2. 使用 TaskCreate 创建所有任务 (标明依赖关系)
3. 使用 Task 工具 spawn Teammates (根据任务选择 subagent_type)
4. 使用 TaskUpdate 分配任务给对应 Teammate
```

## 第四步：团队协作规则

### 文件锁定原则 (防冲突)
- **严禁**: 两个 Teammate 同时修改同一文件
- **前端文件**: 仅 `frontend-dev` 或 `fullstack-dev` 可修改
- **后端文件**: 仅 `backend-dev` 或 `fullstack-dev` 可修改
- **测试文件**: 仅 `test-engineer` 可修改
- **部署文件**: 仅 `devops` 可修改

### 通信协议
- 接口变更 → 发消息通知相关 Teammate
- 发现 bug → 创建新 Task 并 @负责人
- 完成任务 → 报告变更摘要

### 质量门禁
- 后端代码: 必须通过 `ruff check` 和 `ruff format`
- 前端代码: 必须通过 `biome check`
- 测试: 新功能必须有对应测试用例
- 关键变更: 必须经过 `architect` 审查

## 第五步：监控与收尾

1. 定期检查 TaskList，确认进度
2. 处理 blocked 任务，解除依赖
3. 所有任务完成后，运行全量测试验证
4. 清理团队资源

## 常用团队模板

### 模板 A: 新功能开发 (4人)
```
Teammate 1: backend-dev  → 实现后端 API 和逻辑
Teammate 2: frontend-dev → 实现前端页面和组件
Teammate 3: test-engineer → 编写测试用例
依赖: Teammate 3 等待 Teammate 1 完成后开始
```

### 模板 B: Bug 修复 (3人)
```
Teammate 1: fullstack-dev → 定位和修复 bug
Teammate 2: test-engineer → 编写回归测试
Teammate 3: architect → 审查修复方案
```

### 模板 C: 系统优化 (3人)
```
Teammate 1: architect → 分析瓶颈，制定方案
Teammate 2: backend-dev → 执行后端优化
Teammate 3: devops → 优化部署和配置
```

### 模板 D: 全栈功能 (5人)
```
Teammate 1: architect → 评审技术方案
Teammate 2: backend-dev → 后端实现
Teammate 3: frontend-dev → 前端实现
Teammate 4: fullstack-dev → 前后端联调
Teammate 5: test-engineer → 测试验证
依赖链: 1→2,3→4→5
```
