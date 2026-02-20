<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { useHILStore } from "@/stores/hil";
import { computed, ref, watch } from "vue";

const hilStore = useHILStore();

const selectedOptionId = ref<string | null>(null);
const customValue = ref("");
const userComment = ref("");
const showCustomInput = ref(false);
const remainingTime = ref(0);
let countdownTimer: number | null = null;

const currentEvent = computed(() => hilStore.currentEvent);
const isOpen = computed(() => hilStore.isDialogOpen);

watch(
	() => hilStore.currentEvent,
	(event) => {
		if (event) {
			selectedOptionId.value =
				event.options.find((o) => o.is_default)?.id || null;
			customValue.value = "";
			userComment.value = "";
			showCustomInput.value = false;
			startCountdown(event.timeout_seconds);
		} else {
			stopCountdown();
		}
	},
);

function startCountdown(seconds: number) {
	stopCountdown();
	remainingTime.value = seconds;
	countdownTimer = window.setInterval(() => {
		remainingTime.value--;
		if (remainingTime.value <= 0) {
			handleTimeout();
		}
	}, 1000);
}

function stopCountdown() {
	if (countdownTimer) {
		clearInterval(countdownTimer);
		countdownTimer = null;
	}
}

function handleTimeout() {
	stopCountdown();
	hilStore.approveWithDefault();
}

function handleApprove() {
	if (selectedOptionId.value) {
		hilStore.selectOption(selectedOptionId.value, userComment.value);
	} else {
		hilStore.approveWithDefault();
	}
}

function handleReject() {
	hilStore.rejectEvent(userComment.value);
}

function handleModify() {
	if (customValue.value) {
		hilStore.modifyValue(customValue.value, userComment.value);
	}
}

function handleSkip() {
	hilStore.skipEvent(userComment.value);
}

function formatTime(seconds: number): string {
	const mins = Math.floor(seconds / 60);
	const secs = seconds % 60;
	return `${mins}:${secs.toString().padStart(2, "0")}`;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen && currentEvent"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      >
        <div
          class="bg-card rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden"
        >
          <div class="gradient-bg px-6 py-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="text-2xl">{{ hilStore.getEventTypeIcon(currentEvent.event_type) }}</span>
                <div>
                  <h3 class="text-white font-semibold text-lg">{{ currentEvent.title }}</h3>
                  <p class="text-white/80 text-sm">{{ hilStore.getEventTypeLabel(currentEvent.event_type) }}</p>
                </div>
              </div>
              <div class="text-white text-sm bg-white/20 px-3 py-1 rounded-full">
                {{ formatTime(remainingTime) }}
              </div>
            </div>
          </div>

          <div class="p-6 space-y-4">
            <p class="text-foreground">{{ currentEvent.description }}</p>

            <div v-if="currentEvent.options.length > 0" class="space-y-2">
              <p class="text-sm font-medium text-muted-foreground">选择一个选项：</p>
              <div class="space-y-2">
                <label
                  v-for="option in currentEvent.options"
                  :key="option.id"
                  class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
                  :class="[
                    selectedOptionId === option.id
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-border/80'
                  ]"
                >
                  <input
                    type="radio"
                    :value="option.id"
                    v-model="selectedOptionId"
                    class="mt-1"
                  />
                  <div class="flex-1">
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-foreground">{{ option.label }}</span>
                      <span
                        v-if="option.is_default"
                        class="text-xs bg-success/10 text-success px-2 py-0.5 rounded"
                      >
                        推荐
                      </span>
                    </div>
                    <p v-if="option.description" class="text-sm text-muted-foreground mt-0.5">
                      {{ option.description }}
                    </p>
                  </div>
                </label>
              </div>
            </div>

            <div v-if="currentEvent.allow_custom_input" class="space-y-2">
              <button
                @click="showCustomInput = !showCustomInput"
                class="text-sm text-primary hover:text-primary/80 flex items-center gap-1"
              >
                <span>{{ showCustomInput ? '收起' : '自定义输入' }}</span>
              </button>

              <Transition name="slide">
                <textarea
                  v-if="showCustomInput"
                  v-model="customValue"
                  class="w-full p-3 rounded-lg border border-border bg-background text-foreground resize-none"
                  rows="3"
                  placeholder="输入自定义内容..."
                />
              </Transition>
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-muted-foreground">备注（可选）</label>
              <input
                v-model="userComment"
                type="text"
                class="w-full p-2 rounded-lg border border-border bg-background text-foreground"
                placeholder="添加备注..."
              />
            </div>
          </div>

          <div class="px-6 py-4 bg-muted flex gap-3 justify-end">
            <Button variant="outline" @click="handleSkip">
              跳过
            </Button>
            <Button variant="outline" @click="handleReject">
              拒绝
            </Button>
            <Button
              v-if="showCustomInput && customValue"
              @click="handleModify"
              class="bg-accent hover:bg-accent/90 text-accent-foreground"
            >
              使用自定义值
            </Button>
            <Button @click="handleApprove" class="bg-primary hover:bg-primary/90">
              确认
            </Button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
