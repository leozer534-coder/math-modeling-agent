<script setup lang="ts">
import { Coins, TrendingUp, Zap } from "lucide-vue-next";
import { computed, onUnmounted, ref, watch } from "vue";

interface Props {
	inputTokens?: number;
	outputTokens?: number;
	costUsd?: number;
	maxCostUsd?: number;
	isRunning?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
	inputTokens: 0,
	outputTokens: 0,
	costUsd: 0,
	maxCostUsd: 10,
	isRunning: false,
});

// 总 Token 数
const totalTokens = computed(() => props.inputTokens + props.outputTokens);

// 成本百分比
const costPercent = computed(() => {
	if (props.maxCostUsd <= 0) return 0;
	return Math.min(100, (props.costUsd / props.maxCostUsd) * 100);
});

// 成本状态
const costStatus = computed(() => {
	if (costPercent.value >= 80) return "danger";
	if (costPercent.value >= 50) return "warning";
	return "normal";
});

// 格式化数字
const formatNumber = (num: number): string => {
	if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
	if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
	return num.toString();
};

// 格式化成本
const formatCost = (usd: number): string => {
	return `$${usd.toFixed(4)}`;
};

// 人民币成本
const costCny = computed(() => {
	return (props.costUsd * 7.2).toFixed(2);
});

// 动画效果
const isAnimating = ref(false);
let animationTimer: ReturnType<typeof setInterval> | null = null;

watch(() => props.isRunning, (running) => {
	if (animationTimer) {
		clearInterval(animationTimer);
		animationTimer = null;
	}
	if (running) {
		animationTimer = setInterval(() => {
			isAnimating.value = !isAnimating.value;
		}, 1000);
	}
}, { immediate: true });

onUnmounted(() => {
	if (animationTimer) {
		clearInterval(animationTimer);
	}
});
</script>

<template>
  <div class="token-usage">
    <!-- 标题 -->
    <div class="usage-header">
      <div class="header-title">
        <Coins class="header-icon" />
        <span>Token 消耗</span>
      </div>
      <span v-if="isRunning" class="live-badge">
        <span class="live-dot"></span>
        实时
      </span>
    </div>

    <!-- Token 统计 -->
    <div class="token-stats">
      <div class="stat-item">
        <div class="stat-label">
          <Zap class="stat-icon input" />
          输入
        </div>
        <div class="stat-value">{{ formatNumber(inputTokens) }}</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-label">
          <Zap class="stat-icon output" />
          输出
        </div>
        <div class="stat-value">{{ formatNumber(outputTokens) }}</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-label">
          <TrendingUp class="stat-icon total" />
          总计
        </div>
        <div class="stat-value total">{{ formatNumber(totalTokens) }}</div>
      </div>
    </div>

    <!-- 成本显示 -->
    <div class="cost-section">
      <div class="cost-header">
        <span class="cost-label">成本</span>
        <span :class="['cost-value', `cost-${costStatus}`]">
          {{ formatCost(costUsd) }}
          <span class="cost-cny">(¥{{ costCny }})</span>
        </span>
      </div>
      
      <!-- 成本进度条 -->
      <div class="cost-track">
        <div 
          :class="['cost-bar', `bar-${costStatus}`]"
          :style="{ width: `${costPercent}%` }"
        ></div>
      </div>
      
      <div class="cost-footer">
        <span class="cost-used">已用 {{ costPercent.toFixed(1) }}%</span>
        <span class="cost-limit">上限 {{ formatCost(maxCostUsd) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.token-usage {
  padding: 1rem;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.dark .token-usage {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-color: #334155;
}

/* 头部 */
.usage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #1e293b;
}

.dark .header-title {
  color: #f1f5f9;
}

.header-icon {
  width: 18px;
  height: 18px;
  color: #f59e0b;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #22c55e;
  font-weight: 500;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: #22c55e;
  border-radius: 50%;
  animation: pulse-live 1.5s ease-in-out infinite;
}

@keyframes pulse-live {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

/* Token 统计 */
.token-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  background: #f1f5f9;
  border-radius: 12px;
  margin-bottom: 0.75rem;
}

.dark .token-stats {
  background: #334155;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  flex: 1;
}

.stat-label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #64748b;
}

.dark .stat-label {
  color: #94a3b8;
}

.stat-icon {
  width: 14px;
  height: 14px;
}

.stat-icon.input { color: #3b82f6; }
.stat-icon.output { color: #8b5cf6; }
.stat-icon.total { color: #10b981; }

.stat-value {
  font-weight: 700;
  font-size: 1rem;
  color: #1e293b;
}

.dark .stat-value {
  color: #f1f5f9;
}

.stat-value.total {
  color: #10b981;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: #e2e8f0;
}

.dark .stat-divider {
  background: #475569;
}

/* 成本部分 */
.cost-section {
  padding-top: 0.5rem;
}

.cost-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.cost-label {
  font-size: 0.875rem;
  color: #64748b;
}

.dark .cost-label {
  color: #94a3b8;
}

.cost-value {
  font-weight: 700;
  font-size: 1.125rem;
}

.cost-normal { color: #10b981; }
.cost-warning { color: #f59e0b; }
.cost-danger { color: #ef4444; }

.cost-cny {
  font-size: 0.75rem;
  font-weight: 400;
  color: #94a3b8;
}

/* 成本进度条 */
.cost-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 0.375rem;
}

.dark .cost-track {
  background: #334155;
}

.cost-bar {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.bar-normal {
  background: linear-gradient(90deg, #22c55e 0%, #10b981 100%);
}

.bar-warning {
  background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
}

.bar-danger {
  background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
}

.cost-footer {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94a3b8;
}
</style>
