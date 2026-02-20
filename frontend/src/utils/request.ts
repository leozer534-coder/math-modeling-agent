// src/utils/request.ts
import axios from "axios";
import { getPersistedToken, clearPersistedAuth } from "@/utils/auth";
import router from "@/router";

// 创建 axios 实例
const service = axios.create({
	baseURL: import.meta.env.VITE_API_BASE_URL, // 从环境变量获取基础 URL
	timeout: 30000, // 请求超时时间（建模相关接口需要较长时间）
});

// 请求拦截器：自动注入 Auth Token
service.interceptors.request.use(
	(config) => {
		// 从持久化存储中获取 Token，避免与 Pinia Store 产生循环依赖
		const token = getPersistedToken();
		if (token) {
			config.headers["Authorization"] = `Bearer ${token}`;
		}
		return config;
	},
	(error) => {
		// 请求构造阶段的错误（如网络不可用），仅在开发环境打印
		if (import.meta.env.DEV) {
			console.error("请求拦截器错误:", error);
		}
		return Promise.reject(error);
	},
);

// 响应拦截器：统一处理错误状态码
service.interceptors.response.use(
	(response) => {
		return response;
	},
	(error) => {
		const status = error.response?.status;

		switch (status) {
			case 401:
				// Token 过期或无效，清除本地认证数据并跳转到登录页
				clearPersistedAuth();
				// 避免重复跳转：仅当前页不是登录页时才跳转
				if (router.currentRoute.value.path !== "/login") {
					router.push({
						path: "/login",
						query: { redirect: router.currentRoute.value.fullPath },
					});
				}
				break;

			case 429:
				// 请求限流：服务端返回 429 Too Many Requests
				if (import.meta.env.DEV) {
					console.warn("请求被限流 (429)，请稍后重试");
				}
				break;

			case 500:
			case 502:
			case 503:
			case 504:
				// 服务端错误
				if (import.meta.env.DEV) {
					console.error(`服务端错误 (${status})，请稍后重试`);
				}
				break;
		}

		return Promise.reject(error);
	},
);

export default service;
