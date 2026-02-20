<script setup lang="ts">
import { ChevronDown } from "lucide-vue-next";
import { onMounted, onUnmounted, ref } from "vue";

const props = defineProps<{
	scrollContainer?: HTMLElement | null;
	threshold?: number;
}>();

const emit = defineEmits<(e: "click") => void>();

const isVisible = ref(false);

const checkScroll = () => {
	const container = props.scrollContainer;
	if (!container) return;

	const { scrollTop, scrollHeight, clientHeight } = container;
	const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
	isVisible.value = distanceFromBottom > (props.threshold || 200);
};

const handleClick = () => {
	emit("click");
};

let observer: MutationObserver | null = null;

onMounted(() => {
	const container = props.scrollContainer;
	if (container) {
		container.addEventListener("scroll", checkScroll);
		// 监听内容变化
		observer = new MutationObserver(checkScroll);
		observer.observe(container, { childList: true, subtree: true });
	}
});

onUnmounted(() => {
	const container = props.scrollContainer;
	if (container) {
		container.removeEventListener("scroll", checkScroll);
	}
	if (observer) {
		observer.disconnect();
	}
});
</script>

<template>
  <Transition name="fade-up">
    <button
      v-if="isVisible"
      @click="handleClick"
      class="fixed bottom-24 right-6 z-40 w-10 h-10 rounded-full gradient-bg text-white shadow-lg flex items-center justify-center hover:opacity-90 transition-opacity"
      aria-label="滚动到底部"
    >
      <ChevronDown class="w-5 h-5" />
    </button>
  </Transition>
</template>

<style scoped>
.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.3s ease;
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
