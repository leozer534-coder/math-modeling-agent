# Git 工作流规则 (MathModelAgent 项目)

## 提交消息格式

使用约定式提交（Conventional Commits）：

```
<type>(<scope>): <description>

[optional body]
```

### 类型
| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(agent): 添加 ReviewerAgent 审核能力` |
| `fix` | Bug 修复 | `fix(coder): 修复死循环检测误判` |
| `refactor` | 重构 | `refactor(workflow): 统一三套工作流为 Pipeline 模式` |
| `docs` | 文档 | `docs: 更新 API 端点文档` |
| `test` | 测试 | `test(flows): 添加拓扑排序边界条件测试` |
| `chore` | 杂项 | `chore: 更新依赖版本` |
| `perf` | 性能 | `perf(redis): 优化消息序列化性能` |
| `ci` | CI/CD | `ci: 添加覆盖率门禁` |
| `security` | 安全 | `security: 修复 WebSocket 认证绕过` |

### Scope（可选）
`agent`, `workflow`, `router`, `frontend`, `docker`, `config`, `test`, `security`

## 功能开发流程

### 1. 规划阶段
- 使用 `architect` Agent 评审技术方案
- 识别影响范围、依赖关系和风险点
- 拆分为可独立交付的子任务

### 2. 开发阶段
- 遵循项目代码规范（Python: Ruff, TypeScript: Biome）
- 每个功能点完成后立即运行相关测试
- 代码变更 < 500 行为一个 PR 的合理范围

### 3. 审查阶段
- 后端核心逻辑变更需 `architect` 审查
- 安全相关变更需额外安全审查
- 接口变更需前后端双方确认

### 4. 提交阶段
- 提交前运行: `ruff check` + `biome check` + `pytest`
- 遵循安全检查清单
- 详细的提交消息，描述 why 而非 what

## PR 工作流

1. 分析完整提交历史（`git log`）
2. 使用 `git diff main...HEAD` 审查全部变更
3. 撰写全面的 PR 摘要（Summary + Test Plan）
4. 新分支推送使用 `-u` 标志

## 禁止操作

- ❌ `git push --force` 到 main 分支
- ❌ `git reset --hard` 不带明确确认
- ❌ 提交包含密钥/Token 的文件
- ❌ 提交 `.env.dev` 或 `*.db` 文件
- ❌ 单个 PR 超过 1000 行变更（应拆分）
