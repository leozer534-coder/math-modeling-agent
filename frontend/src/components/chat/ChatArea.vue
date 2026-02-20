<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useTaskStore } from "@/stores/task";
import type { Message } from "@/utils/response";
import { MessageSquare, Send } from "lucide-vue-next";
import { computed, nextTick, ref, watch } from "vue";
import Bubble from "./Bubble.vue";
import SystemMessage from "./SystemMessage.vue";

const props = defineProps<{ messages: Message[] }>();
const taskStore = useTaskStore();

// 进度增强信息
const iterationInfo = computed(() => {
	const p = taskStore.latestProgress;
	if (p && (p.iteration ?? 0) > 0 && (p.max_iterations ?? 0) > 0) {
		return `反馈迭代 ${p.iteration}/${p.max_iterations}`;
	}
	return "";
});

const qualityInfo = computed(() => {
	const p = taskStore.latestProgress;
	if (p && (p.quality_score ?? 0) > 0) {
		return `质量评分: ${p.quality_score}/100`;
	}
	return "";
});

const subPhaseInfo = computed(() => taskStore.latestProgress?.sub_phase || "");

const inputValue = ref("");
const inputRef = ref<HTMLInputElement | null>(null);
const scrollRef = ref<HTMLDivElement | null>(null);

/** 用户是否手动滚动到上方（距底部超过 100px 则认为不在底部） */
const isUserScrolledUp = ref(false);

/** 检测用户是否在底部附近 */
const handleScroll = () => {
	if (!scrollRef.value) return;
	const { scrollTop, scrollHeight, clientHeight } = scrollRef.value;
	// 距底部 100px 以内认为在底部
	isUserScrolledUp.value = scrollHeight - scrollTop - clientHeight > 100;
};

// 自动滚动到底部
const scrollToBottom = () => {
	nextTick(() => {
		if (scrollRef.value) {
			scrollRef.value.scrollTo({
				top: scrollRef.value.scrollHeight,
				behavior: "smooth",
			});
		}
	});
};

// 监听消息变化，仅当用户在底部附近时自动滚动
watch(
	() => props.messages.length,
	() => {
		if (!isUserScrolledUp.value) {
			scrollToBottom();
		}
	},
);

const sendMessage = () => {
	const content = inputValue.value.trim();
	if (!content) return;

	// 通过 WebSocket 发送用户消息（store 方法会同时添加本地回显）
	taskStore.sendUserMessage(content);

	// 清空输入框并聚焦
	inputValue.value = "";
	inputRef.value?.focus();
};
</script>

<template>
  <div class="chat-area">
    <div ref="scrollRef" class="messages-container" @scroll="handleScroll">
      <TransitionGroup name="message">
        <template v-for="message in props.messages" :key="message.id">
          <div class="message-wrapper">
            <!-- 用户消息 -->
            <Bubble v-if="message.msg_type === 'user'" type="user" :content="message.content || ''" />
            <!-- agent 消息 -->
            <Bubble v-else-if="message.msg_type === 'agent'" type="agent" :agentType="message.agent_type"
              :content="message.content || ''" />
            <!-- 系统消息 -->
            <SystemMessage v-else-if="message.msg_type === 'system'" :content="message.content || ''"
              :type="message.type" />
          </div>
        </template>
      </TransitionGroup>
      <!-- 进度信息条 -->
      <div v-if="iterationInfo || qualityInfo || subPhaseInfo"
        class="sticky top-0 z-10 flex items-center gap-3 px-3 py-1.5 mb-2 rounded-lg bg-muted/80 backdrop-blur-sm border border-border text-xs text-muted-foreground">
        <span v-if="subPhaseInfo" class="font-medium text-foreground">{{ subPhaseInfo }}</span>
        <span v-if="iterationInfo">{{ iterationInfo }}</span>
        <span v-if="qualityInfo">{{ qualityInfo }}</span>
      </div>
      <!-- 空状态引导 -->
      <div v-if="props.messages.length === 0" class="flex items-center justify-center h-full">
        <div class="text-center space-y-3">
          <div class="w-16 h-16 rounded-full gradient-bg mx-auto flex items-center justify-center">
            <MessageSquare class="w-8 h-8 text-white" />
          </div>
          <p class="text-lg font-medium text-foreground">对话区域</p>
          <p class="text-sm text-muted-foreground">Agent 的消息将在此显示</p>
        </div>
      </div>
    </div>
    <form class="input-form" @submit.prevent="sendMessage">
      <Input ref="inputRef" v-model="inputValue" type="text" placeholder="请输入消息..." class="flex-1" autocomplete="off" />
      <Button type="submit" :disabled="!inputValue.trim()" class="send-button">
        <Send />
      </Button>
    </form>
  </div>
</template>

<style scoped>
.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.75rem;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.message-wrapper {
  margin-bottom: 0.75rem;
}

/* 消息过渡动画 */
.message-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.message-leave-active {
  transition: all 0.2s ease-out;
}

.message-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.message-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* 输入表单 */
.input-form {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 1rem;
  max-width: 42rem;
  margin: 0 auto;
  width: 100%;
}

.send-button {
  flex-shrink: 0;
}

/* 自定义滚动条样式 */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: hsl(var(--primary));
  border-radius: 9999px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--primary));
  opacity: 0.8;
}
</style>
