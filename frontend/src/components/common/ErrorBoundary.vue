<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-vue-next";
import { onErrorCaptured, provide, ref } from "vue";

const props = defineProps<{
	fallbackMessage?: string;
}>();

const emit = defineEmits<(e: "error", error: Error) => void>();

// 错误状态
const hasError = ref(false);
const errorMessage = ref("");
const errorStack = ref("");

// 捕获子组件错误
onErrorCaptured((error: Error, _instance, info) => {
	console.error("ErrorBoundary 捕获到错误:", error);
	console.error("组件信息:", info);

	hasError.value = true;
	errorMessage.value = error.message || "未知错误";
	errorStack.value = error.stack || "";

	emit("error", error);

	// 返回 false 阻止错误继续传播
	return false;
});

// 重试方法
const retry = () => {
	hasError.value = false;
	errorMessage.value = "";
	errorStack.value = "";
};

// 刷新页面
const refreshPage = () => {
	window.location.reload();
};

// 提供给子组件的方法
provide("errorBoundary", {
	reportError: (error: Error) => {
		hasError.value = true;
		errorMessage.value = error.message;
		errorStack.value = error.stack || "";
		emit("error", error);
	},
	clearError: retry,
});
</script>

<template>
  <div class="error-boundary">
    <!-- 错误状态 -->
    <div v-if="hasError" class="error-fallback p-6 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
      <div class="flex items-start space-x-4">
        <div class="flex-shrink-0">
          <AlertTriangle class="w-8 h-8 text-red-500" />
        </div>
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
            {{ props.fallbackMessage || '出现了一些问题' }}
          </h3>
          <p class="text-sm text-red-600 dark:text-red-300 mb-4">
            {{ errorMessage }}
          </p>
          <details v-if="errorStack" class="mb-4">
            <summary class="text-sm text-red-500 cursor-pointer hover:underline">
              查看详细信息
            </summary>
            <pre class="mt-2 p-3 bg-red-100 dark:bg-red-900/40 rounded text-xs overflow-x-auto text-red-700 dark:text-red-300">{{ errorStack }}</pre>
          </details>
          <div class="flex space-x-3">
            <Button @click="retry" variant="outline" size="sm" class="text-red-600 border-red-300 hover:bg-red-100">
              <RefreshCw class="w-4 h-4 mr-2" />
              重试
            </Button>
            <Button @click="refreshPage" variant="ghost" size="sm" class="text-red-600">
              刷新页面
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 正常内容 -->
    <slot v-else />
  </div>
</template>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-fallback {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
