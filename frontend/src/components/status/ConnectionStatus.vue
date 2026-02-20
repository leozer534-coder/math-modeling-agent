<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Loader2, Wifi, WifiOff } from "lucide-vue-next";
import { computed } from "vue";

export type ConnectionState = "connected" | "disconnected" | "reconnecting";

const props = defineProps<{
	status: ConnectionState;
	reconnectAttempt?: number;
	maxReconnectAttempts?: number;
}>();

const emit = defineEmits<(e: "reconnect") => void>();

// 状态配置
const statusConfig = computed(() => {
	switch (props.status) {
		case "connected":
			return {
				icon: Wifi,
				text: "已连接",
				bgColor: "bg-green-100 dark:bg-green-900/30",
				textColor: "text-green-700 dark:text-green-300",
				borderColor: "border-green-200 dark:border-green-800",
				iconColor: "text-green-500",
				show: false, // 连接正常时不显示
			};
		case "reconnecting":
			return {
				icon: Loader2,
				text: `正在重连${props.reconnectAttempt ? ` (${props.reconnectAttempt}/${props.maxReconnectAttempts || 10})` : ""}...`,
				bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
				textColor: "text-yellow-700 dark:text-yellow-300",
				borderColor: "border-yellow-200 dark:border-yellow-800",
				iconColor: "text-yellow-500",
				show: true,
				animate: true,
			};
		case "disconnected":
			return {
				icon: WifiOff,
				text: "连接已断开",
				bgColor: "bg-red-100 dark:bg-red-900/30",
				textColor: "text-red-700 dark:text-red-300",
				borderColor: "border-red-200 dark:border-red-800",
				iconColor: "text-red-500",
				show: true,
				showReconnect: true,
			};
		default:
			return {
				icon: WifiOff,
				text: "未知状态",
				bgColor: "bg-gray-100 dark:bg-gray-800",
				textColor: "text-gray-700 dark:text-gray-300",
				borderColor: "border-gray-200 dark:border-gray-700",
				iconColor: "text-gray-500",
				show: true,
			};
	}
});

const handleReconnect = () => {
	emit("reconnect");
};
</script>

<template>
  <Transition name="slide-down">
    <div
      v-if="statusConfig.show"
      :class="[
        'connection-status fixed top-0 left-0 right-0 z-50 px-4 py-2 border-b shadow-sm',
        statusConfig.bgColor,
        statusConfig.borderColor
      ]"
    >
      <div class="max-w-4xl mx-auto flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <component
            :is="statusConfig.icon"
            :class="[
              'w-5 h-5',
              statusConfig.iconColor,
              statusConfig.animate ? 'animate-spin' : ''
            ]"
          />
          <span :class="['text-sm font-medium', statusConfig.textColor]">
            {{ statusConfig.text }}
          </span>
        </div>

        <Button
          v-if="statusConfig.showReconnect"
          @click="handleReconnect"
          variant="outline"
          size="sm"
          class="h-7 text-xs"
        >
          重新连接
        </Button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.connection-status {
  animation: slideDown 0.3s ease-out;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-100%);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
