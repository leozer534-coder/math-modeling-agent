/// <reference types="vite/client" />

/**
 * Vite 环境变量类型声明
 * 对应 .env / .env.development 中定义的 VITE_ 前缀变量
 */
interface ImportMetaEnv {
	/** 后端 API 基础地址，留空则使用 Vite proxy */
	readonly VITE_API_BASE_URL: string;
	/** WebSocket 连接地址 */
	readonly VITE_WS_URL: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
