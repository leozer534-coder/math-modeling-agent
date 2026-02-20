import request from "@/utils/request";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export interface UserInfo {
	id: string;
	email: string;
	nickname: string | null;
	avatar_url: string | null;
	credits: number;
	vip_level: number;
}

export interface AuthResponse {
	access_token: string;
	token_type: string;
	user: UserInfo;
}

export const useUserStore = defineStore(
	"user",
	() => {
		// token 由 Pinia persist 插件自动持久化，无需手动操作 localStorage
		const token = ref<string | null>(null);
		const user = ref<UserInfo | null>(null);
		const loading = ref(false);
		const error = ref<string | null>(null);

		const isLoggedIn = computed(() => !!token.value && !!user.value);
		const credits = computed(() => user.value?.credits ?? 0);

		function setToken(newToken: string | null) {
			token.value = newToken;
		}

		function setUser(newUser: UserInfo | null) {
			user.value = newUser;
		}

		/**
		 * 处理 Google OAuth 回调
		 * 直接使用后端重定向传来的 JWT token
		 */
		async function handleGoogleCallback(jwtToken: string): Promise<boolean> {
			loading.value = true;
			error.value = null;

			try {
				// 保存 token
				setToken(jwtToken);

				// 用 token 获取用户信息
				const response = await request.get<UserInfo>("/auth/me");
				setUser(response.data);
				return true;
			} catch (err: unknown) {
				const axiosError = err as { response?: { data?: { detail?: string } } };
				error.value = axiosError.response?.data?.detail || "登录失败";
				setToken(null);
				setUser(null);
				return false;
			} finally {
				loading.value = false;
			}
		}

		async function fetchUserInfo(): Promise<boolean> {
			if (!token.value) return false;

			loading.value = true;
			try {
				const response = await request.get<UserInfo>("/auth/me");
				setUser(response.data);
				return true;
			} catch {
				logout();
				return false;
			} finally {
				loading.value = false;
			}
		}

		async function refreshCredits(): Promise<void> {
			if (!token.value) return;

			try {
				const response = await request.get<{ credits: number }>(
					"/auth/credits",
				);
				if (user.value) {
					user.value.credits = response.data.credits;
				}
			} catch {
				// ignore
			}
		}

		function logout() {
			setToken(null);
			setUser(null);
			error.value = null;
		}

		async function initialize(): Promise<void> {
			if (token.value && !user.value) {
				await fetchUserInfo();
			}
		}

		return {
			token,
			user,
			loading,
			error,
			isLoggedIn,
			credits,

			handleGoogleCallback,
			logout,
			fetchUserInfo,
			refreshCredits,
			initialize,
		};
	},
	{
		persist: {
			pick: ["token"],
		},
	},
);
