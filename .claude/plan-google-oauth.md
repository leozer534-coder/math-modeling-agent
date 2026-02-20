# Google OAuth 登录改造计划

## 目标
将现有的邮箱+密码认证替换为 Google OAuth 2.0 登录（使用 Authorization Code Flow）。

## 架构设计

```
前端 LoginForm.vue
    → 点击 "Sign in with Google" 按钮
    → 重定向到 Google 授权页面
    → Google 回调到前端 /auth/callback?code=xxx
    → 前端将 code 发送到后端 POST /auth/google/callback
    → 后端用 code 换取 Google access_token + id_token
    → 后端解析用户信息(email, name, avatar)
    → 后端查找/创建用户 → 签发本系统 JWT
    → 前端存储 JWT → 跳转到 /chat
```

## 变更文件清单

### 后端（5 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/routers/auth_router.py` | **重写** | 删除 register/login 端点，新增 `/auth/google/login` 和 `/auth/google/callback` |
| `backend/app/utils/auth.py` | **修改** | 删除 bcrypt 密码相关函数，保留 JWT 签发/验证逻辑 |
| `backend/app/services/user_service.py` | **修改** | 新增 `get_or_create_by_google()` 方法，`create_user` 不再需要 `password_hash` |
| `backend/app/models/user.py` | **修改** | `password_hash` 改为可选，新增 `google_id`、`auth_provider` 字段 |
| `backend/app/config/setting.py` | **修改** | 新增 `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_REDIRECT_URI` 配置 |

### 前端（4 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/auth/LoginForm.vue` | **重写** | 移除邮箱密码表单，改为 Google 登录按钮 |
| `frontend/src/stores/user.ts` | **修改** | 删除 `login()`/`register()`，新增 `loginWithGoogle(code)` |
| `frontend/src/router/index.ts` | **修改** | 新增 `/auth/callback` 路由处理 Google 回调 |
| `frontend/src/pages/auth/callback.vue` | **新增** | Google OAuth 回调页面（接收 code 并交给后端） |

### 配置（3 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/vite.config.ts` | **修改** | proxy 无需改动（已有 `/auth` 代理） |
| `backend/.env.dev` | **修改** | 新增 Google OAuth 环境变量 |
| `backend/.env.example` | **修改** | 新增 Google OAuth 示例配置 |

## 详细实施步骤

### 步骤 1: 后端 — 数据模型改造 (`models/user.py`)

```python
# User 表新增字段
google_id = Column(String(255), unique=True, nullable=True, index=True)
auth_provider = Column(String(20), default="google")  # google | local
# password_hash 改为 nullable=True
password_hash = Column(String(255), nullable=True)
```

### 步骤 2: 后端 — 配置新增 (`config/setting.py`)

```python
# Google OAuth 配置
GOOGLE_CLIENT_ID: str = ""
GOOGLE_CLIENT_SECRET: str = ""
GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/callback"
```

### 步骤 3: 后端 — auth 工具简化 (`utils/auth.py`)

- 删除 `verify_password()`, `get_password_hash()`, `pwd_context`
- 删除 `passlib` 依赖
- 保留 JWT 签发/解码/鉴权逻辑不变

### 步骤 4: 后端 — 用户服务层 (`services/user_service.py`)

新增方法：
```python
async def get_or_create_by_google(
    self, google_id: str, email: str,
    nickname: str | None, avatar_url: str | None
) -> tuple[User, bool]:
    """根据 google_id 查找或创建用户，返回 (user, is_new)"""
```

### 步骤 5: 后端 — 认证路由重写 (`routers/auth_router.py`)

新增两个端点：
- `GET /auth/google/login` → 返回 Google 授权 URL
- `POST /auth/google/callback` → 接收 code，换取 token，返回本系统 JWT

删除：
- `POST /auth/register`
- `POST /auth/login`

保留：
- `GET /auth/me`
- `GET /auth/credits`
- `POST /auth/refresh`

### 步骤 6: 后端 — 安装依赖

```bash
cd backend && uv add httpx  # 用于后端调用 Google API
```

（`httpx` 用于向 Google token endpoint 和 userinfo endpoint 发请求）

### 步骤 7: 前端 — 新增 OAuth 回调页面 (`pages/auth/callback.vue`)

```vue
<!-- 从 URL 提取 code，POST 到后端，存储 JWT，跳转 /chat -->
```

### 步骤 8: 前端 — 路由新增 (`router/index.ts`)

```typescript
{
  path: "/auth/callback",
  name: "AuthCallback",
  component: () => import("@/pages/auth/callback.vue"),
}
// PUBLIC_ROUTES 新增 "/auth/callback"
```

### 步骤 9: 前端 — Store 改造 (`stores/user.ts`)

```typescript
// 删除 login(), register(), LoginRequest, RegisterRequest
// 新增
async function loginWithGoogle(code: string): Promise<boolean> {
  const response = await request.post<AuthResponse>(
    "/auth/google/callback", { code }
  );
  setToken(response.data.access_token);
  setUser(response.data.user);
  return true;
}
```

### 步骤 10: 前端 — 登录页改造 (`LoginForm.vue`)

- 移除邮箱/密码/注册表单
- 替换为 "Sign in with Google" 按钮
- 点击后跳转到后端返回的 Google 授权 URL
- 保留右侧品牌面板不变

## 依赖变更

### 后端
- **新增**: `httpx`（异步 HTTP 客户端，调用 Google API）
- **删除**: `passlib`, `bcrypt`（不再需要密码哈希）

### 前端
- 无新增依赖

## 环境变量（用户需配置）

```env
# backend/.env.dev
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/callback
```

## Google Cloud Console 配置指引

用户需要：
1. 前往 https://console.cloud.google.com/
2. 创建或选择项目
3. 启用 "Google Identity" API
4. 创建 OAuth 2.0 客户端 → Web 应用
5. 设置"已获授权的重定向 URI"为 `http://localhost:5173/auth/callback`
6. 复制 Client ID 和 Client Secret 填入 `.env.dev`

## 团队分工

- **backend-dev**: 步骤 1-6（模型、配置、服务、路由、依赖）
- **frontend-dev**: 步骤 7-10（回调页、路由、Store、登录页）
- 两者可并行开发，接口契约已在计划中定义

## 接口契约

### GET /auth/google/login
**Response:**
```json
{ "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&scope=openid email profile&response_type=code" }
```

### POST /auth/google/callback
**Request:**
```json
{ "code": "4/0AX4XfWg..." }
```
**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@gmail.com",
    "nickname": "John",
    "avatar_url": "https://lh3.googleusercontent.com/...",
    "credits": 50,
    "vip_level": 0
  }
}
```
