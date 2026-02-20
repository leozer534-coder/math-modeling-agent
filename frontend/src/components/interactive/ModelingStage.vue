<template>
  <div class="stage-content">
    <div class="flex items-center mb-4">
      <Cpu class="w-6 h-6 text-green-500 mr-2" />
      <h3 class="text-xl font-semibold">建模执行</h3>
    </div>

    <!-- 进度展示 -->
    <div v-if="progress" class="space-y-4">
      <div class="bg-gray-50 p-4 rounded-lg">
        <div class="flex justify-between items-center mb-2">
          <span class="font-medium">执行进度</span>
          <span class="text-sm text-gray-600">{{ progress.progress }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="bg-green-500 h-2 rounded-full transition-all duration-300"
            :style="{ width: progress.progress + '%' }"
          ></div>
        </div>
      </div>

      <!-- 当前执行步骤 -->
      <div v-if="progress.currentStep" class="border-l-4 border-green-500 pl-4">
        <div class="flex items-center">
          <Loader2 class="w-5 h-5 animate-spin mr-2" />
          <span class="font-medium">正在执行：{{ progress.currentStep }}</span>
        </div>
      </div>

      <!-- 已完成的结果 -->
      <div v-if="progress.completedSteps.length > 0" class="space-y-2">
        <h4 class="font-medium">已完成步骤：</h4>
        <div
          v-for="step in progress.completedSteps"
          :key="step.name"
          class="bg-green-50 p-3 rounded-lg"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <CheckCircle class="w-4 h-4 text-green-500 mr-2" />
              <span class="font-medium">{{ step.name }}</span>
            </div>
            <div class="flex items-center space-x-2">
              <Button variant="outline" size="sm" @click="$emit('viewResult', step)">
                <Eye class="w-3 h-3 mr-1" />
                查看结果
              </Button>
              <Button variant="outline" size="sm" @click="$emit('retryStep', step)">
                <RefreshCw class="w-3 h-3 mr-1" />
                重试
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 控制按钮 -->
    <div class="flex justify-between pt-4">
      <div class="space-x-2">
        <Button variant="outline" @click="$emit('pause')" v-if="!isPaused">
          <Pause class="w-4 h-4 mr-2" />
          暂停
        </Button>
        <Button variant="outline" @click="$emit('resume')" v-else>
          <Play class="w-4 h-4 mr-2" />
          继续
        </Button>
      </div>
      <Button variant="outline" @click="$emit('rollback')">
        <SkipBack class="w-4 h-4 mr-2" />
        回退上一步
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
	CheckCircle,
	Cpu,
	Eye,
	Loader2,
	Pause,
	Play,
	RefreshCw,
	SkipBack,
} from "lucide-vue-next";

interface CompletedStep {
	name: string;
	result?: unknown;
}

interface ModelingProgress {
	progress: number;
	currentStep?: string;
	completedSteps: CompletedStep[];
}

defineProps<{
	progress: ModelingProgress | null;
	isPaused: boolean;
}>();

defineEmits(["pause", "resume", "rollback", "viewResult", "retryStep"]);
</script>

<style scoped>
.stage-content {
  min-height: 400px;
}
</style>
