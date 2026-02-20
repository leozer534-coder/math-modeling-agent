<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
	Brain,
	Code2,
	FileText,
	Loader2,
	Sigma,
	Sparkles,
} from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";

const { t } = useI18n();
const route = useRoute();

const isLoading = ref(false);
const errorMessage = ref<string | null>(null);

// 检查 URL 中是否有错误 (Google OAuth 回调错误)
onMounted(() => {
	const error = route.query.error as string;
	if (error) {
		const errorMap: Record<string, string> = {
			token_exchange_failed: t("login.errorTokenExchange"),
			userinfo_failed: t("login.errorUserInfo"),
			account_disabled: t("login.errorAccountDisabled"),
			server_error: t("login.errorServer"),
			missing_code: t("login.errorMissingCode"),
		};
		errorMessage.value = errorMap[error] || t("login.errorUnknown");
	}
});

const apiBaseUrl = computed(() => {
	// 开发环境下使用 Vite 代理 (空字符串)，生产环境使用完整 URL
	return import.meta.env.VITE_API_BASE_URL || "";
});

function handleGoogleLogin() {
	isLoading.value = true;
	errorMessage.value = null;
	// 直接跳转到后端的 Google OAuth 授权入口
	window.location.href = `${apiBaseUrl.value}/auth/google/login`;
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <Card class="overflow-hidden rounded-2xl border-border/40 shadow-xl shadow-black/[0.03] dark:shadow-black/[0.15]">
      <CardContent class="grid p-0 md:grid-cols-2">
        <!-- 左侧：登录表单 -->
        <div class="flex flex-col items-center justify-center p-8 md:p-10">
          <div class="flex flex-col gap-7 w-full max-w-sm">
            <!-- 标题区域 -->
            <div class="flex flex-col items-start gap-1.5">
              <h1 class="text-2xl font-bold tracking-tight">
                {{ t('login.welcomeBack') }}
              </h1>
              <p class="text-[14px] text-muted-foreground/70 leading-relaxed">
                {{ t('login.loginDesc') }}
              </p>
            </div>

            <!-- 错误提示 -->
            <div
              v-if="errorMessage"
              class="flex items-center gap-2.5 px-4 py-3 text-[13px] text-red-600 dark:text-red-400 bg-red-500/5 border border-red-500/15 rounded-xl"
            >
              <div class="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
              {{ errorMessage }}
            </div>

            <!-- Google 登录按钮 -->
            <div class="grid gap-4">
              <Button
                class="w-full h-12 rounded-xl text-[14px] font-medium shadow-sm transition-all duration-200 hover:shadow-md bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-border/50 hover:bg-zinc-50 dark:hover:bg-zinc-700"
                :disabled="isLoading"
                @click="handleGoogleLogin"
              >
                <Loader2 v-if="isLoading" class="h-5 w-5 animate-spin mr-3" />
                <template v-else>
                  <!-- Google Logo SVG -->
                  <svg class="w-5 h-5 mr-3" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                </template>
                <span>{{ t('login.googleButton') }}</span>
              </Button>
            </div>

            <!-- 提示文字 -->
            <div class="text-center text-[13px] text-muted-foreground/50">
              {{ t('login.googleHint') }}
            </div>
          </div>
        </div>

        <!-- 右侧：品牌展示面板 -->
        <div class="relative hidden md:block overflow-hidden bg-zinc-950 dark:bg-zinc-900">
          <!-- 背景渐变 -->
          <div class="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/10 to-transparent" />
          <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent" />

          <!-- 网格纹理 -->
          <div
            class="absolute inset-0 opacity-[0.03]"
            style="background-image: url(&quot;data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E&quot;)"
          />

          <!-- 内容 -->
          <div class="relative z-10 flex flex-col items-center justify-center h-full p-10">
            <!-- 品牌 Logo -->
            <div class="mb-8">
              <div class="w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-sm flex items-center justify-center ring-1 ring-white/[0.08] shadow-2xl">
                <Sigma class="w-8 h-8 text-white" />
              </div>
            </div>

            <!-- 标语 -->
            <div class="text-center mb-10 max-w-[280px]">
              <h2 class="text-[22px] font-bold tracking-tight text-white mb-2">
                MathModelAgent
              </h2>
              <p class="text-[14px] text-white/50 leading-relaxed">
                {{ t('login.slogan') }}
              </p>
            </div>

            <!-- 特性卡片 -->
            <div class="grid gap-2.5 w-full max-w-[280px]">
              <div class="flex items-center gap-3.5 p-3.5 rounded-xl bg-white/[0.04] backdrop-blur-sm ring-1 ring-white/[0.06] transition-all duration-200 hover:bg-white/[0.07]">
                <div class="w-9 h-9 rounded-lg bg-blue-500/15 flex items-center justify-center shrink-0">
                  <Brain class="w-4 h-4 text-blue-400" />
                </div>
                <div class="min-w-0">
                  <p class="text-[13px] font-medium text-white/90">{{ t('login.featureMultiAgent') }}</p>
                  <p class="text-[11px] text-white/35 leading-tight">{{ t('login.featureMultiAgentDesc') }}</p>
                </div>
              </div>

              <div class="flex items-center gap-3.5 p-3.5 rounded-xl bg-white/[0.04] backdrop-blur-sm ring-1 ring-white/[0.06] transition-all duration-200 hover:bg-white/[0.07]">
                <div class="w-9 h-9 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0">
                  <Code2 class="w-4 h-4 text-emerald-400" />
                </div>
                <div class="min-w-0">
                  <p class="text-[13px] font-medium text-white/90">{{ t('login.featureCodeSandbox') }}</p>
                  <p class="text-[11px] text-white/35 leading-tight">{{ t('login.featureCodeSandboxDesc') }}</p>
                </div>
              </div>

              <div class="flex items-center gap-3.5 p-3.5 rounded-xl bg-white/[0.04] backdrop-blur-sm ring-1 ring-white/[0.06] transition-all duration-200 hover:bg-white/[0.07]">
                <div class="w-9 h-9 rounded-lg bg-amber-500/15 flex items-center justify-center shrink-0">
                  <FileText class="w-4 h-4 text-amber-400" />
                </div>
                <div class="min-w-0">
                  <p class="text-[13px] font-medium text-white/90">{{ t('login.featurePaperGen') }}</p>
                  <p class="text-[11px] text-white/35 leading-tight">{{ t('login.featurePaperGenDesc') }}</p>
                </div>
              </div>
            </div>

            <!-- 底部装饰 -->
            <div class="mt-auto pt-8">
              <div class="flex items-center gap-1.5 text-[11px] text-white/20">
                <Sparkles class="w-3 h-3" />
                <span>Powered by Multi-Agent AI</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 底部条款 -->
    <div class="text-center text-[12px] text-muted-foreground/40 leading-relaxed">
      {{ t('login.termsText') }}
      <a href="#" class="text-muted-foreground/60 hover:text-foreground/70 underline underline-offset-4 transition-colors duration-150">
        {{ t('login.termsOfService') }}
      </a>
      {{ t('login.and') }}
      <a href="#" class="text-muted-foreground/60 hover:text-foreground/70 underline underline-offset-4 transition-colors duration-150">
        {{ t('login.privacyPolicy') }}
      </a>
    </div>
  </div>
</template>
