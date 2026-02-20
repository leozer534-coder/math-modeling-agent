// 路由配置与认证守卫
import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import { getPersistedToken } from "@/utils/auth";

// 需要认证的路由路径白名单（不在此列表中的路由均需要认证）
const PUBLIC_ROUTES = new Set(["/", "/login", "/oauth/callback"]);

const routes: RouteRecordRaw[] = [
	{
		path: "/",
		name: "Home",
		component: () => import("@/pages/index.vue"),
	},
	{
		path: "/login",
		name: "Login",
		component: () => import("@/pages/login/index.vue"),
	},
	{
		path: "/oauth/callback",
		name: "GoogleCallback",
		component: () => import("@/pages/auth/GoogleCallback.vue"),
	},
	{
		path: "/chat",
		name: "Chat",
		meta: { requiresAuth: true },
		component: () => import("@/pages/chat/index.vue"),
	},
	{
		path: "/task/:task_id",
		name: "Task",
		meta: { requiresAuth: true },
		component: () => import("@/pages/task/index.vue"),
		props: true,
	},
	{
		// 404 通配符路由：匹配所有未定义的路径
		path: "/:pathMatch(.*)*",
		name: "NotFound",
		component: () => import("@/pages/404.vue"),
	},
];

// 创建路由
const router = createRouter({
	history: createWebHistory(),
	routes,
});

// 路由守卫：检查认证状态
router.beforeEach((to, _from, next) => {
	// 公开路由无需认证，直接放行
	if (PUBLIC_ROUTES.has(to.path)) {
		next();
		return;
	}

	// 需要认证的路由检查 Token
	const token = getPersistedToken();
	if (!token && to.meta.requiresAuth) {
		// 未登录，重定向到登录页，并携带原目标路径以便登录后跳回
		next({
			path: "/login",
			query: { redirect: to.fullPath },
		});
		return;
	}

	// Token 存在或路由不要求认证，放行
	next();
});

export default router;
