<script setup lang="ts">
interface Step {
	label: string;
}

const props = withDefaults(
	defineProps<{
		currentStep: number;
		steps?: Step[];
	}>(),
	{
		currentStep: 1,
		steps: () => [{ label: "上传数据" }, { label: "输入题目" }],
	},
);
</script>

<template>
  <div class="flex items-center justify-center gap-0 mb-6">
    <template v-for="(step, index) in props.steps" :key="index">
      <!-- 连接线 (除了第一个步骤前) -->
      <div
        v-if="index > 0"
        :class="[
          'w-12 h-0.5 mx-2 transition-colors',
          props.currentStep > index ? 'gradient-bg' : 'bg-border'
        ]"
      />
      <!-- 步骤圆点 + 标签 -->
      <div class="flex items-center gap-2">
        <div
          :class="[
            'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
            props.currentStep >= index + 1
              ? 'gradient-bg text-white'
              : 'bg-muted text-muted-foreground'
          ]"
        >
          {{ index + 1 }}
        </div>
        <span
          :class="[
            'text-sm transition-colors',
            props.currentStep >= index + 1
              ? 'text-foreground font-medium'
              : 'text-muted-foreground'
          ]"
        >
          {{ step.label }}
        </span>
      </div>
    </template>
  </div>
</template>
