<script setup lang="ts">
import { useTaskStore } from "@/stores/task";
import { computed } from "vue";

const taskStore = useTaskStore();

// 阶段名称映射
const phaseNames: Record<string, string> = {
	init: "初始化",
	coordinate: "问题分析",
	model: "建模设计",
	setup: "环境准备",
	solve: "代码执行",
	write: "论文撰写",
	finalize: "完成处理",
	completed: "已完成",
	failed: "失败",
};

// 阶段图标映射
const phaseIcons: Record<string, string> = {
	init: "🚀",
	coordinate: "🎯",
	model: "📐",
	setup: "⚙️",
	solve: "💻",
	write: "✍️",
	finalize: "📦",
	completed: "✅",
	failed: "❌",
};

// 当前阶段名称
const currentPhaseName = computed(() => {
	const phase = taskStore.progressPhase;
	return phaseNames[phase] || phase || "准备中";
});

// 当前阶段图标
const currentPhaseIcon = computed(() => {
	const phase = taskStore.progressPhase;
	return phaseIcons[phase] || "📋";
});

// 状态文本
const statusText = computed(() => {
	const phase = taskStore.progressPhase;
	if (phase === "failed") return "执行失败";
	if (phase === "completed") return "执行完成";
	if (taskStore.isTaskRunning) return "正在执行";
	return "等待开始";
});

// 状态样式类
const statusClass = computed(() => {
	const phase = taskStore.progressPhase;
	if (phase === "failed") return "status-failed";
	if (phase === "completed") return "status-completed";
	if (taskStore.isTaskRunning) return "status-running";
	return "status-pending";
});

// 进度条样式类
const progressBarClass = computed(() => {
	const phase = taskStore.progressPhase;
	if (phase === "failed") return "progress-failed";
	if (phase === "completed") return "progress-completed";
	return "progress-running";
});

// 阶段顺序
const stageOrder = ["coordinate", "model", "solve", "write"];
const stageNames = ["问题分析", "建模设计", "代码执行", "论文撰写"];

// 获取阶段状态
const getStageStatus = (
	index: number,
): "completed" | "current" | "pending" => {
	const currentPhase = taskStore.progressPhase;
	const currentIndex = stageOrder.indexOf(currentPhase);

	if (index < currentIndex) return "completed";
	if (index === currentIndex) return "current";
	return "pending";
};

// 预估剩余时间
const estimatedTime = computed(() => {
	if (!taskStore.isTaskRunning) return null;
	const progress = taskStore.progressPercent;
	if (progress <= 0) return null;
	return null; // 简化：由于 store 没有 elapsed_time，暂不计算
});

// 是否完成或运行中
const isCompleted = computed(
	() => taskStore.progressPhase === "completed",
);
</script>

<template>
	<div class="task-progress">
		<!-- 标题和状态 -->
		<div class="progress-header">
			<div class="phase-info">
				<span class="phase-icon">{{ currentPhaseIcon }}</span>
				<span class="phase-name">{{ currentPhaseName }}</span>
			</div>
			<span :class="['status-badge', statusClass]">
				{{ statusText }}
			</span>
		</div>

		<!-- 进度条 -->
		<div class="progress-track">
			<div
				:class="['progress-bar', progressBarClass]"
				:style="{ width: `${taskStore.progressPercent}%` }"
			>
				<!-- 流光效果 -->
				<div v-if="taskStore.isTaskRunning" class="shimmer"></div>
			</div>
		</div>

		<!-- 进度信息 -->
		<div class="progress-info">
			<span class="progress-message">{{
				taskStore.progressMessage || "准备中..."
			}}</span>
			<div class="progress-stats">
				<span class="progress-percent"
					>{{ taskStore.progressPercent }}%</span
				>
				<span v-if="estimatedTime" class="estimated-time">
					({{ estimatedTime }})
				</span>
			</div>
		</div>

		<!-- 阶段指示器 -->
		<div
			v-if="taskStore.isTaskRunning || isCompleted"
			class="stage-indicator"
		>
			<div
				v-for="(name, index) in stageNames"
				:key="index"
				class="stage-item"
			>
				<div :class="['stage-dot', `stage-${getStageStatus(index)}`]">
					<span
						v-if="getStageStatus(index) === 'completed'"
						class="check-icon"
						>✓</span
					>
				</div>
				<span class="stage-name">{{ name }}</span>
				<!-- 连接线 -->
				<div
					v-if="index < stageNames.length - 1"
					:class="[
						'stage-line',
						getStageStatus(index) === 'completed'
							? 'line-completed'
							: '',
					]"
				></div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.task-progress {
	padding: 1rem;
	background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
	border-radius: 16px;
	box-shadow:
		0 4px 6px -1px rgba(0, 0, 0, 0.1),
		0 2px 4px -1px rgba(0, 0, 0, 0.06);
	border: 1px solid #e2e8f0;
	min-width: 320px;
}

.dark .task-progress {
	background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
	border-color: #334155;
}

/* 头部 */
.progress-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 0.75rem;
}

.phase-info {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.phase-icon {
	font-size: 1.5rem;
}

.phase-name {
	font-weight: 600;
	color: #1e293b;
}

.dark .phase-name {
	color: #f1f5f9;
}

/* 状态徽章 */
.status-badge {
	font-size: 0.75rem;
	font-weight: 600;
	padding: 0.25rem 0.75rem;
	border-radius: 9999px;
}

.status-pending {
	background: #f1f5f9;
	color: #64748b;
}

.status-running {
	background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
	color: white;
	animation: pulse-badge 2s ease-in-out infinite;
}

.status-completed {
	background: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
	color: white;
}

.status-failed {
	background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
	color: white;
}

@keyframes pulse-badge {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.8;
	}
}

/* 进度条轨道 */
.progress-track {
	position: relative;
	height: 8px;
	background: #e2e8f0;
	border-radius: 9999px;
	overflow: hidden;
	margin-bottom: 0.5rem;
}

.dark .progress-track {
	background: #334155;
}

/* 进度条 */
.progress-bar {
	height: 100%;
	border-radius: 9999px;
	transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
	position: relative;
	overflow: hidden;
}

.progress-running {
	background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
}

.progress-completed {
	background: linear-gradient(90deg, #22c55e 0%, #10b981 100%);
}

.progress-failed {
	background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
}

/* 流光效果 */
.shimmer {
	position: absolute;
	top: 0;
	left: -100%;
	width: 100%;
	height: 100%;
	background: linear-gradient(
		90deg,
		transparent 0%,
		rgba(255, 255, 255, 0.4) 50%,
		transparent 100%
	);
	animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
	0% {
		left: -100%;
	}
	100% {
		left: 100%;
	}
}

/* 进度信息 */
.progress-info {
	display: flex;
	align-items: center;
	justify-content: space-between;
	font-size: 0.875rem;
	color: #64748b;
}

.dark .progress-info {
	color: #94a3b8;
}

.progress-message {
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.progress-stats {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	flex-shrink: 0;
}

.progress-percent {
	font-weight: 600;
	color: #3b82f6;
}

.estimated-time {
	font-size: 0.75rem;
	color: #94a3b8;
}

/* 阶段指示器 */
.stage-indicator {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-top: 1rem;
	padding-top: 1rem;
	border-top: 1px solid #e2e8f0;
}

.dark .stage-indicator {
	border-color: #334155;
}

.stage-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	position: relative;
	flex: 1;
}

.stage-dot {
	width: 24px;
	height: 24px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.3s ease;
	margin-bottom: 0.25rem;
	font-size: 0.75rem;
}

.stage-completed {
	background: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
	color: white;
}

.stage-current {
	background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
	color: white;
	animation: pulse-dot 1.5s ease-in-out infinite;
	box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.stage-pending {
	background: #e2e8f0;
	color: #94a3b8;
}

.dark .stage-pending {
	background: #475569;
}

@keyframes pulse-dot {
	0%,
	100% {
		transform: scale(1);
	}
	50% {
		transform: scale(1.1);
	}
}

.stage-name {
	font-size: 0.625rem;
	color: #64748b;
	text-align: center;
}

.dark .stage-name {
	color: #94a3b8;
}

.stage-line {
	position: absolute;
	top: 12px;
	left: calc(50% + 14px);
	width: calc(100% - 28px);
	height: 2px;
	background: #e2e8f0;
}

.dark .stage-line {
	background: #475569;
}

.line-completed {
	background: linear-gradient(90deg, #22c55e 0%, #10b981 100%);
}

.check-icon {
	font-weight: bold;
}
</style>
