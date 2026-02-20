/**
 * User Store 单元测试
 *
 * 覆盖场景：
 * - Token 设置与清除
 * - 用户信息管理
 * - 认证状态计算（isLoggedIn）
 * - 积分查询
 * - 登出逻辑
 * - 初始化逻辑
 */

import { useUserStore } from "@/stores/user";
import type { UserInfo } from "@/stores/user";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ============================================================
// Mock axios request 模块，避免真实 HTTP 请求
// ============================================================
vi.mock("@/utils/request", () => ({
	default: {
		get: vi.fn(),
		post: vi.fn(),
	},
}));

// 测试用的用户数据
const mockUser: UserInfo = {
	id: "user-001",
	email: "test@example.com",
	nickname: "测试用户",
	credits: 100,
	vip_level: 1,
};

describe("useUserStore", () => {
	let store: ReturnType<typeof useUserStore>;

	beforeEach(() => {
		setActivePinia(createPinia());
		store = useUserStore();
	});

	// ========================================================
	// 初始状态
	// ========================================================
	describe("初始状态", () => {
		it("token 应为 null", () => {
			expect(store.token).toBeNull();
		});

		it("user 应为 null", () => {
			expect(store.user).toBeNull();
		});

		it("loading 应为 false", () => {
			expect(store.loading).toBe(false);
		});

		it("error 应为 null", () => {
			expect(store.error).toBeNull();
		});

		it("isLoggedIn 应为 false", () => {
			expect(store.isLoggedIn).toBe(false);
		});

		it("credits 应为 0", () => {
			expect(store.credits).toBe(0);
		});
	});

	// ========================================================
	// Token 设置与清除
	// ========================================================
	describe("Token 管理", () => {
		it("setToken 应正确设置 token", () => {
			store.token = "test-jwt-token-abc123";
			expect(store.token).toBe("test-jwt-token-abc123");
		});

		it("setToken(null) 应清除 token", () => {
			store.token = "some-token";
			store.token = null;
			expect(store.token).toBeNull();
		});

		it("清除 token 后 isLoggedIn 应为 false", () => {
			// 先模拟登录状态
			store.token = "valid-token";
			store.user = mockUser;
			expect(store.isLoggedIn).toBe(true);

			// 清除 token
			store.token = null;
			expect(store.isLoggedIn).toBe(false);
		});
	});

	// ========================================================
	// 用户信息管理
	// ========================================================
	describe("用户信息管理", () => {
		it("应正确设置用户信息", () => {
			store.user = mockUser;
			expect(store.user).toEqual(mockUser);
			expect(store.user?.email).toBe("test@example.com");
			expect(store.user?.nickname).toBe("测试用户");
		});

		it("应正确读取积分", () => {
			store.user = mockUser;
			expect(store.credits).toBe(100);
		});

		it("user 为 null 时 credits 应返回 0", () => {
			store.user = null;
			expect(store.credits).toBe(0);
		});
	});

	// ========================================================
	// 认证状态（isLoggedIn 计算属性）
	// ========================================================
	describe("认证状态", () => {
		it("token 和 user 都存在时 isLoggedIn 为 true", () => {
			store.token = "valid-token";
			store.user = mockUser;
			expect(store.isLoggedIn).toBe(true);
		});

		it("只有 token 没有 user 时 isLoggedIn 为 false", () => {
			store.token = "valid-token";
			store.user = null;
			expect(store.isLoggedIn).toBe(false);
		});

		it("只有 user 没有 token 时 isLoggedIn 为 false", () => {
			store.token = null;
			store.user = mockUser;
			expect(store.isLoggedIn).toBe(false);
		});

		it("token 和 user 都为 null 时 isLoggedIn 为 false", () => {
			expect(store.isLoggedIn).toBe(false);
		});

		it("空字符串 token 应视为未登录", () => {
			store.token = "";
			store.user = mockUser;
			expect(store.isLoggedIn).toBe(false);
		});
	});

	// ========================================================
	// 登出逻辑
	// ========================================================
	describe("登出", () => {
		it("logout 应清除 token、user 和 error", () => {
			// 模拟已登录状态
			store.token = "valid-token";
			store.user = mockUser;
			store.error = "某个错误";

			store.logout();

			expect(store.token).toBeNull();
			expect(store.user).toBeNull();
			expect(store.error).toBeNull();
			expect(store.isLoggedIn).toBe(false);
		});
	});

	// ========================================================
	// 登录请求
	// ========================================================
	describe("登录请求", () => {
		it("登录成功应设置 token 和 user", async () => {
			const request = await import("@/utils/request");
			const mockPost = vi.mocked(request.default.post);
			mockPost.mockResolvedValueOnce({
				data: {
					access_token: "new-jwt-token",
					token_type: "bearer",
					user: mockUser,
				},
			});

			const result = await store.login({
				email: "test@example.com",
				password: "password123",
			});

			expect(result).toBe(true);
			expect(store.token).toBe("new-jwt-token");
			expect(store.user).toEqual(mockUser);
			expect(store.loading).toBe(false);
			expect(store.error).toBeNull();
		});

		it("登录失败应设置 error", async () => {
			const request = await import("@/utils/request");
			const mockPost = vi.mocked(request.default.post);
			mockPost.mockRejectedValueOnce({
				response: {
					data: {
						detail: "邮箱或密码错误",
					},
				},
			});

			const result = await store.login({
				email: "wrong@example.com",
				password: "wrong",
			});

			expect(result).toBe(false);
			expect(store.token).toBeNull();
			expect(store.error).toBe("邮箱或密码错误");
			expect(store.loading).toBe(false);
		});

		it("登录失败且无详情应显示默认错误信息", async () => {
			const request = await import("@/utils/request");
			const mockPost = vi.mocked(request.default.post);
			mockPost.mockRejectedValueOnce(new Error("网络错误"));

			const result = await store.login({
				email: "test@example.com",
				password: "password",
			});

			expect(result).toBe(false);
			expect(store.error).toBe("登录失败");
		});
	});

	// ========================================================
	// 注册请求
	// ========================================================
	describe("注册请求", () => {
		it("注册成功应设置 token 和 user", async () => {
			const request = await import("@/utils/request");
			const mockPost = vi.mocked(request.default.post);
			mockPost.mockResolvedValueOnce({
				data: {
					access_token: "register-token",
					token_type: "bearer",
					user: mockUser,
				},
			});

			const result = await store.register({
				email: "new@example.com",
				password: "newpass123",
				nickname: "新用户",
			});

			expect(result).toBe(true);
			expect(store.token).toBe("register-token");
			expect(store.user).toEqual(mockUser);
		});

		it("注册失败应设置 error", async () => {
			const request = await import("@/utils/request");
			const mockPost = vi.mocked(request.default.post);
			mockPost.mockRejectedValueOnce({
				response: {
					data: {
						detail: "邮箱已被注册",
					},
				},
			});

			const result = await store.register({
				email: "existing@example.com",
				password: "pass",
			});

			expect(result).toBe(false);
			expect(store.error).toBe("邮箱已被注册");
		});
	});

	// ========================================================
	// 初始化逻辑
	// ========================================================
	describe("初始化", () => {
		it("有 token 但无 user 时应尝试获取用户信息", async () => {
			const request = await import("@/utils/request");
			const mockGet = vi.mocked(request.default.get);
			mockGet.mockResolvedValueOnce({
				data: mockUser,
			});

			store.token = "existing-token";
			await store.initialize();

			expect(store.user).toEqual(mockUser);
		});

		it("无 token 时不应发起请求", async () => {
			const request = await import("@/utils/request");
			const mockGet = vi.mocked(request.default.get);

			await store.initialize();

			expect(mockGet).not.toHaveBeenCalled();
		});

		it("token 和 user 都存在时不应重复请求", async () => {
			const request = await import("@/utils/request");
			const mockGet = vi.mocked(request.default.get);

			store.token = "existing-token";
			store.user = mockUser;

			await store.initialize();

			expect(mockGet).not.toHaveBeenCalled();
		});
	});
});
