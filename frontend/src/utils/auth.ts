// Pinia persist 插件使用 store id 作为 localStorage key
// user store 的 token 字段以 JSON 格式存储在 "user" key 下
const PERSIST_STORE_KEY = "user";

/**
 * 从 Pinia persist 存储中读取 token
 *
 * 独立于 store 实例，直接解析 localStorage 中的持久化数据，
 * 避免在 router guard / WebSocket 等模块中引入 store 导致循环依赖。
 */
export function getPersistedToken(): string | null {
	try {
		const raw = localStorage.getItem(PERSIST_STORE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		return parsed.token ?? null;
	} catch {
		return null;
	}
}

/**
 * 清除持久化存储中的认证数据
 *
 * 用于 token 过期或认证失败时的清理操作。
 */
export function clearPersistedAuth(): void {
	localStorage.removeItem(PERSIST_STORE_KEY);
}
