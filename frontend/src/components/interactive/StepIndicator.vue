<template>
  <div class="step-indicator mb-6">
    <div class="flex items-center justify-between">
      <div
        v-for="(step, index) in steps"
        :key="index"
        :class="[
          'step-item',
          { active: currentStep === index },
          { completed: currentStep > index },
          { pending: currentStep < index }
        ]"
      >
        <div class="step-circle">
          <CheckCircle v-if="currentStep > index" class="w-5 h-5" />
          <span v-else>{{ index + 1 }}</span>
        </div>
        <span class="step-title">{{ step.title }}</span>
        <div v-if="index < steps.length - 1" class="step-line"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CheckCircle } from "lucide-vue-next";

import type { Component } from "vue";

defineProps<{
	steps: Array<{ title: string; icon: Component }>;
	currentStep: number;
}>();
</script>

<style scoped>
.step-indicator {
  position: relative;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
}

.step-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 8px;
  transition: all 0.3s ease;
}

.step-item.active .step-circle {
  background: #3b82f6;
  color: white;
}

.step-item.completed .step-circle {
  background: #10b981;
  color: white;
}

.step-title {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  text-align: center;
  margin-bottom: 16px;
}

.step-item.active .step-title {
  color: #1f2937;
}

.step-item.completed .step-title {
  color: #059669;
}

.step-line {
  position: absolute;
  top: 20px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: #e5e7eb;
  z-index: -1;
}

.step-item.completed .step-line {
  background: #10b981;
}
</style>
