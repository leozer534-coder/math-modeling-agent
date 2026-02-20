# TypeScript/Vue 开发规则 (MathModelAgent 项目适配)

> 融合 everything-claude-code 精华 + 项目特定约束

## 编码风格

### 强制标准
- **Linter**: Biome（项目默认配置）
- **组件**: Composition API + `<script setup lang="ts">`
- **命名**: 组件 PascalCase, 文件 PascalCase.vue, 工具函数 camelCase
- **注释语言**: 中文
- 生产代码中**禁止** `console.log`，使用结构化日志或条件编译

### 不可变性优先
```typescript
// ✅ 正确: 展开运算符创建新对象
function updateTask(task: Task, status: TaskStatus): Task {
  return { ...task, status, updatedAt: Date.now() }
}

// ✅ 正确: 使用 readonly 标记不可变
interface AgentConfig {
  readonly model: string
  readonly temperature: number
}

// ❌ 错误: 直接修改
function updateTask(task: Task, status: TaskStatus): Task {
  task.status = status  // MUTATION!
  return task
}
```

### 代码质量检查清单
- [ ] 无 `any` 类型逃逸（使用 `unknown` + 类型守卫替代）
- [ ] 无 `console.log`（使用条件编译 `if (import.meta.env.DEV)`）
- [ ] 所有 Props 和 Emits 有完整 TypeScript 类型定义
- [ ] 环境变量在 `env.d.ts` 中声明
- [ ] 函数体 < 50 行，文件 < 800 行

## 类型安全

### 消除 any 类型
```typescript
// ✅ 正确: 精确类型
interface HILEvent {
  event_type: HILEventType
  metadata: Record<string, string | number | boolean>
  current_value: string | number | null
}

// ❌ 错误: any 逃逸
interface HILEvent {
  metadata: Record<string, any>  // 禁止！
  current_value: any             // 禁止！
}
```

### 环境变量类型声明
```typescript
// frontend/src/env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_TITLE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

### 判别式联合（已有，保持一致）
```typescript
// ✅ 正确: 使用 msg_type 作为 discriminator
type WsMessage =
  | { msg_type: 'agent'; agent_type: AgentType; content: string }
  | { msg_type: 'code_result'; execution: ExecutionResult }
  | { msg_type: 'hil'; event: HILEvent }
  | { msg_type: 'progress'; progress: ProgressData }
```

## 输入验证

### 使用 Zod 进行运行时验证（推荐引入）
```typescript
import { z } from 'zod'

// API 响应验证
const ModelingResponseSchema = z.object({
  code: z.number(),
  data: z.object({
    task_id: z.string(),
    status: z.enum(['pending', 'running', 'completed', 'failed']),
  }),
  message: z.string(),
})

// 使用时验证后端响应，防止类型不一致
const validated = ModelingResponseSchema.parse(response.data)
```

## 错误处理

### 统一错误处理（全局 + 局部）
```typescript
// ✅ 正确: 统一的 API 错误处理
import { toast } from '@/components/ui/toast'

function handleApiError(error: AxiosError<ApiResponse>) {
  const response = error.response?.data
  const status = error.response?.status

  switch (status) {
    case 401:
      toast.error('登录已过期，请重新登录')
      router.push('/login')
      break
    case 429:
      toast.warning('请求过于频繁，请稍后重试')
      break
    case 500:
    case 502:
    case 503:
      toast.error('服务暂时不可用，请稍后重试')
      break
    default:
      toast.error(response?.message || '操作失败，请重试')
  }
}

// ❌ 错误: 只 console.error
catch (error) {
  console.error('请求失败:', error)  // 用户看不到！
}
```

### async/await 错误处理
```typescript
// ✅ 正确: try-catch + 用户反馈
async function submitTask(request: ModelingRequest) {
  loading.value = true
  try {
    const result = await submitModelingApi.submit(request)
    toast.success('任务已提交')
    return result
  } catch (error) {
    handleApiError(error as AxiosError)
    throw error  // 保持异常链
  } finally {
    loading.value = false
  }
}
```

## 组件设计

### 组件目录规范（商业化标准）
```
frontend/src/components/
├── auth/              # 认证相关
│   ├── LoginForm.vue
│   └── ...
├── chat/              # 聊天相关
│   ├── ChatArea.vue
│   ├── Bubble.vue
│   └── ...
├── task/              # 任务相关
│   ├── NotebookArea.vue
│   ├── NotebookCell.vue
│   └── Files.vue
├── hil/               # 人机交互
│   └── HILDialog.vue
├── layout/            # 布局
│   ├── AppSidebar.vue
│   └── NavUser.vue
├── status/            # 状态指示
│   ├── ServiceStatus.vue
│   ├── ConnectionStatus.vue
│   └── TaskProgress.vue
└── ui/                # 基础 UI 组件 (Reka UI)
```

### 性能要求（商业化标准）
- **首屏加载**: < 2s (Lighthouse Performance > 90)
- **交互响应**: < 100ms
- **代码分割**: 路由级懒加载
- **Bundle 监控**: 持续关注构建产物大小

## 状态管理

### Pinia Store 规范
```typescript
// ✅ 正确: 组合式 Store + 精确持久化
export const useApiKeyStore = defineStore('apiKeys', () => {
  const providers = ref<Provider[]>([])

  // 清理死代码: 不保留空函数体的兼容方法
  // ❌ 删除: function setModelerConfig(_config: ModelConfig) { }

  return { providers }
}, {
  persist: {
    pick: ['providers']  // 只持久化必要状态
  }
})
```

### 敏感数据处理
```typescript
// ❌ 错误: API Key 存储在 localStorage
persist: { pick: ['providers'] }  // providers 含 apiKey 字段

// ✅ 正确: API Key 由后端托管，前端仅持有 config_id
persist: { pick: ['configId', 'agentAssignment'] }
```

## WebSocket 规范

### Token 传递安全
```typescript
// ❌ 错误: Token 通过 URL 传递
const wsUrl = `${baseUrl}/task/${taskId}?token=${token}`

// ✅ 正确: 握手后首条消息认证
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'auth', token }))
}
```

### 断连恢复
- 两阶段重连：前 10 次指数退避 (1s→30s)，后 20 次固定 30s
- 心跳：30s ping，10s pong 超时
- **重连后消息回补**: 记录最后收到的消息 ID，重连后请求缺失消息

## 安全规范

### 密钥管理
```typescript
// ❌ 永远不要
const apiKey = "sk-proj-xxxxx"

// ✅ 环境变量
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
if (!apiBaseUrl) {
  throw new Error('VITE_API_BASE_URL 未配置')
}
```

### XSS 防护（已有，保持）
- Markdown 渲染使用 `sanitizeHtml` 过滤危险标签
- 图片 src/alt 属性转义
- `data:image/` 前缀白名单

## 测试规范（待引入）

### 框架: Vitest + Playwright
```bash
# 组件单元测试
cd frontend && pnpm run test:unit

# E2E 测试
cd frontend && pnpm run test:e2e
```

### 优先测试目标
1. 4 个 Pinia Store（task, apiKeys, user, hil）
2. WebSocket 工具类（连接、重连、心跳）
3. Markdown 渲染（含 XSS 防护验证）
4. 关键用户流程 E2E（登录 → 提交任务 → 查看结果）

## 工具链

```bash
# 代码检查
cd frontend && pnpm exec biome check src/

# 构建验证
cd frontend && pnpm run build

# 类型检查
cd frontend && pnpm exec vue-tsc --noEmit
```
