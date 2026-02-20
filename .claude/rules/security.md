# 安全规则 (MathModelAgent 项目适配)

> 数学建模智能体商业化安全基线

## 强制安全检查清单（每次提交前）

- [ ] 无硬编码密钥/Token/API Key
- [ ] 所有用户输入经过验证（Pydantic/Zod）
- [ ] 参数化查询（如涉及数据库操作）
- [ ] XSS 防护（前端 sanitizeHtml, 后端 HTML 转义）
- [ ] CSRF 防护（Cookie SameSite + Token）
- [ ] 认证/授权已验证（包括 WebSocket 连接）
- [ ] 速率限制已配置（生产环境强制启用）
- [ ] 错误消息不暴露内部实现细节或堆栈信息

## 密钥管理

### Python 后端
```python
# ✅ 启动时强制验证
from app.config.setting import settings

if settings.ENV == "production" and not settings.API_KEY_MASTER_SECRET:
    raise ValueError("生产环境必须配置 API_KEY_MASTER_SECRET")
```

### TypeScript 前端
```typescript
// ✅ 构建时验证
const requiredEnvVars = ['VITE_API_BASE_URL', 'VITE_WS_URL'] as const
for (const key of requiredEnvVars) {
  if (!import.meta.env[key]) {
    throw new Error(`环境变量 ${key} 未配置`)
  }
}
```

### 禁止事项
- ❌ 在源码中硬编码任何密钥
- ❌ 将 `.env.dev` 提交到 Git（已在 .gitignore）
- ❌ 在日志中输出完整 API Key（使用 DataMasker 脱敏）
- ❌ 在 URL query parameter 中传递 JWT Token
- ❌ 将 API Key 以明文存储在 localStorage

## 代码执行安全

### 沙箱配置（商业化基线）
```yaml
sandbox:
  network_mode: "none"          # 完全网络隔离
  read_only_root: true          # 只读根文件系统
  drop_capabilities: ["ALL"]    # 移除所有 Linux capabilities
  no_new_privileges: true       # 禁止权限提升
  user: "nobody"                # 非 root 运行
  memory_limit: "2g"            # 内存上限
  cpu_quota: 50000              # CPU 50%
  timeout: 300                  # 5 分钟超时
```

### 代码注入防护
- 用户代码执行前必须经过 `CodeSanitizer` 审查
- Notebook 执行使用临时文件传递，不使用字符串拼接
- 沙箱临时目录不以 `rw` 模式挂载到宿主机

## WebSocket 安全

### 认证流程
```
客户端                              服务端
  │                                   │
  ├── WebSocket 握手 ──────────────►  │ 建立连接
  │                                   │
  ├── { type: "auth", token } ────►  │ 验证 JWT
  │                                   │
  │◄──── { type: "auth_ok" } ───────┤ 认证成功
  │                                   │
  ├── 业务消息 ──────────────────►   │ 正常处理
```

## 安全响应协议（发现安全问题时）

1. **立即停止** — 不继续编写有安全隐患的代码
2. **评估影响** — 确定漏洞的影响范围和严重程度
3. **先修关键** — CRITICAL > HIGH > MEDIUM 优先级处理
4. **轮换密钥** — 如有密钥可能泄露，立即轮换
5. **全局排查** — 在整个代码库中搜索类似问题模式
