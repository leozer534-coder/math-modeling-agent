<script setup lang="ts">
import { useUserStore } from "@/stores/user";
import { Loader2 } from "lucide-vue-next";
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const error = ref<string | null>(null);

onMounted(async () => {
	const token = route.query.token as string;

	if (!token) {
		error.value = "登录失败：未收到认证信息";
		setTimeout(() => router.push("/login"), 2000);
		return;
	}

	const success = await userStore.handleGoogleCallback(token);

	if (success) {
		// 登录成功，跳转到聊天页
		router.push("/chat");
	} else {
		error.value = userStore.error || "登录失败，请重试";
		setTimeout(() => router.push("/login"), 2000);
	}
});
</script>

<template>
  <div class="flex min-h-svh items-center justify-center bg-background">
    <div class="flex flex-col items-center gap-4">
      <template v-if="!error">
        <Loader2 class="h-8 w-8 animate-spin text-primary" />
        <p class="text-sm text-muted-foreground">正在完成登录...</p>
      </template>
      <template v-else>
        <div class="flex items-center gap-2.5 px-4 py-3 text-[13px] text-red-600 dark:text-red-400 bg-red-500/5 border border-red-500/15 rounded-xl">
          <div class="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
          {{ error }}
        </div>
        <p class="text-xs text-muted-foreground">正在返回登录页...</p>
      </template>
    </div>
  </div>
</template>
