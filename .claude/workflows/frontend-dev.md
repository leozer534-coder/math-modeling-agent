---
name: frontend-dev
description: 前端开发快速启动 — 包含完整的组件开发和验证流程
---

# 前端开发工作流

## 环境准备
1. 确认依赖已安装: `cd frontend && pnpm install`
2. 启动开发服务器: `cd frontend && pnpm run dev`
3. 浏览器打开: http://localhost:5173

## 开发流程

### 1. 需求理解
- 阅读相关组件和页面代码
- 确认 API 接口格式（与后端对齐）
- 如涉及新的状态管理，先设计 Store 结构

### 2. 编写组件
- 使用 Composition API + `<script setup lang="ts">`
- 样式使用 TailwindCSS 工具类
- UI 组件基于 Reka UI
- 支持暗色模式 (`dark:` 变体)
- 中文注释

### 3. 代码检查
```bash
cd frontend && pnpm exec biome check src/
```

### 4. 构建验证
```bash
cd frontend && pnpm run build
```

## 关键目录
| 目录 | 说明 |
|------|------|
| `src/components/` | 通用组件 |
| `src/pages/chat/` | 聊天/建模页面 |
| `src/pages/task/` | 任务管理页面 |
| `src/stores/` | Pinia 状态管理 |
| `src/apis/` | API 接口封装 |
| `src/utils/` | 工具函数 |
| `src/router/` | 路由配置 |

## 新组件开发步骤
1. 在 `src/components/` 创建 PascalCase.vue 文件
2. 定义 Props 类型 (TypeScript interface)
3. 定义 Emits 类型
4. 编写模板和逻辑
5. 在目标页面中引入和使用
6. 运行 Biome 检查
7. 浏览器验证交互效果

## 新页面开发步骤
1. 在 `src/pages/` 下创建目录和 `index.vue`
2. 在 `src/router/index.ts` 注册路由
3. 如需新的 API，在 `src/apis/` 创建封装
4. 如需新的状态，在 `src/stores/` 创建 Store
5. 运行 Biome 检查
6. 构建验证
