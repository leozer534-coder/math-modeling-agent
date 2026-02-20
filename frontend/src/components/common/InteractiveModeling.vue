<template>
  <div class="interactive-modeling-container">
    <!-- 步骤指示器 -->
    <StepIndicator :steps="modelingSteps" :currentStep="currentStep" />

    <!-- 主内容区域 -->
    <div class="main-content bg-white rounded-lg shadow-sm p-6 mb-6">
      <!-- 问题分析阶段 -->
      <AnalysisStage
        v-if="currentStep === 0"
        :analysisResult="analysisResult"
        :isAnalyzing="isAnalyzing"
        @confirm="confirmAnalysis"
        @cancel="cancelTask"
        @retry="requestAnalysis"
      />

      <!-- 建模执行阶段 -->
      <ModelingStage
        v-else-if="currentStep === 1"
        :progress="modelingProgress"
        :isPaused="isPaused"
        @pause="pauseExecution"
        @resume="resumeExecution"
        @rollback="rollbackStep"
        @viewResult="viewStepResult"
        @retryStep="retryStep"
      />

      <!-- 结果展示阶段 -->
      <ResultsStage
        v-else-if="currentStep === 2"
        :results="finalResults"
        @viewNotebook="viewNotebook"
        @viewReport="viewReport"
        @download="downloadResults"
        @newModeling="startNewModeling"
      />
    </div>

    <!-- 实时消息区域 -->
    <MessagePanel :messages="messages" @clear="clearMessages" />
  </div>
</template>

<script setup lang="ts">
import { interactiveModelingApi } from "@/apis/interactiveModelingApi";
import { toast } from "@/components/ui/toast";
import { TaskWebSocket } from "@/utils/websocket";
import { CheckCircle, Cpu, Search } from "lucide-vue-next";
import { onUnmounted, ref } from "vue";

import AnalysisStage from "./interactive/AnalysisStage.vue";
import MessagePanel from "./interactive/MessagePanel.vue";
import ModelingStage from "./interactive/ModelingStage.vue";
import ResultsStage from "./interactive/ResultsStage.vue";
// Import sub-components
import StepIndicator from "./interactive/StepIndicator.vue";

// 类型定义
interface MessageItem {
	timestamp: string;
	content: string;
	type: string;
}

interface AnalysisResultType {
	problem_summary: string;
	key_questions: string[];
	suggested_approaches: Array<{
		name: string;
		description: string;
		pros: string[];
		cons: string[];
		complexity: string;
		suitable_for: string;
	}>;
}

interface ModelingProgressType {
	currentStep: string;
	progress: number;
	completedSteps: Array<{ name: string; result: unknown }>;
}

interface StartModelingResponse {
	task_id: string;
	[key: string]: unknown;
}

// 状态定义
const currentStep = ref(0);
const isAnalyzing = ref(false);
const isPaused = ref(false);
const taskId = ref<string | null>(null);
const websocket = ref<TaskWebSocket | null>(null);

const modelingSteps = [
	{ title: "问题分析", icon: Search },
	{ title: "建模执行", icon: Cpu },
	{ title: "结果展示", icon: CheckCircle },
];

const analysisResult = ref<AnalysisResultType | null>(null);
const modelingProgress = ref<ModelingProgressType | null>(null);
const finalResults = ref<unknown>(null);
const messages = ref<MessageItem[]>([]);

// WebSocket 连接管理
const connectWebSocket = (id: string) => {
	const baseUrl = import.meta.env.VITE_WS_URL;
	// 从 localStorage 获取 JWT Token 并附加到 WebSocket URL
	const token = localStorage.getItem("auth_token");
	const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
	const wsUrl = `${baseUrl}/task/${id}${tokenParam}`;

	const ws = new TaskWebSocket(
		wsUrl,
		(data) =>
			handleWebSocketMessage(data as unknown as Record<string, unknown>),
	);
	ws.connect();
	websocket.value = ws;
};

const handleWebSocketMessage = (data: Record<string, unknown>) => {
	// 添加到消息列表
	messages.value.push({
		timestamp: new Date().toISOString(),
		content: (data.content || data.message || "") as string,
		type: (data.type || "info") as string,
	});

	// 处理不同类型的消息
	switch (data.type) {
		case "analysis_complete":
			analysisResult.value = data.data as AnalysisResultType;
			isAnalyzing.value = false;
			break;

		case "analysis_start":
			isAnalyzing.value = true;
			currentStep.value = 0;
			break;

		case "stage_start":
			currentStep.value =
				data.stage === "analysis" ? 0 : data.stage === "modeling" ? 1 : 2;
			break;

		case "coding_step":
			modelingProgress.value = {
				currentStep: data.step as string,
				progress: calculateProgress(data.step as string),
				completedSteps: [],
			};
			break;

		case "coding_result":
			if (modelingProgress.value) {
				modelingProgress.value.completedSteps.push({
					name: data.step as string,
					result: data.result,
				});
			}
			break;

		case "plan_confirmed":
			currentStep.value = 1;
			break;

		case "success":
			currentStep.value = 2;
			finalResults.value = data;
			break;
	}
};

const calculateProgress = (step: string): number => {
	// 根据步骤计算进度百分比
	const steps = ["数据预处理", "模型建立", "模型求解", "结果分析"];
	const currentIndex = steps.indexOf(step);
	return Math.max(10, Math.min(90, (currentIndex + 1) * 25));
};

// API 调用方法
const startModeling = async (requestData: FormData) => {
	try {
		const response = (await interactiveModelingApi.startModeling(
			requestData,
		)) as unknown as StartModelingResponse;
		taskId.value = response.task_id;
		connectWebSocket(taskId.value);

		toast({
			title: "建模任务已启动",
			description: `任务ID: ${response.task_id}`,
		});
	} catch (err) {
		const error = err as Error;
		console.error("启动建模任务失败:", error);
		toast({
			title: "启动失败",
			description: error.message,
			variant: "destructive",
		});
	}
};

const confirmAnalysis = async ({
	selectedApproach,
	userAnswers,
}: { selectedApproach: string; userAnswers: Record<string, unknown> }) => {
	try {
		await interactiveModelingApi.sendUserAction({
			task_id: taskId.value,
			action: "confirm",
			feedback: {
				selected_approach: selectedApproach,
				user_answers: userAnswers,
			},
		});
	} catch (error) {
		console.error("发送确认失败:", error);
	}
};

const requestAnalysis = async () => {
	analysisResult.value = null;
	isAnalyzing.value = true;

	// 请求重新分析
	setTimeout(() => {
		isAnalyzing.value = false;
		// 模拟分析结果
		analysisResult.value = {
			problem_summary: "重新分析的问题摘要",
			key_questions: ["重新分析的问题1"],
			suggested_approaches: [
				{
					name: "新的方法",
					description: "重新分析的建模方法",
					pros: ["新优点1"],
					cons: ["新缺点1"],
					complexity: "中",
					suitable_for: "新适用场景",
				},
			],
		};
	}, 2000);
};

const cancelTask = async () => {
	if (taskId.value) {
		try {
			await interactiveModelingApi.cancelTask(taskId.value);
			toast({
				title: "任务已取消",
				description: "建模任务已被取消",
			});
		} catch (error) {
			console.error("取消任务失败:", error);
		}
	}
};

const pauseExecution = async () => {
	if (taskId.value) {
		try {
			await interactiveModelingApi.pauseTask(taskId.value);
			isPaused.value = true;
		} catch (error) {
			console.error("暂停任务失败:", error);
		}
	}
};

const resumeExecution = async () => {
	if (taskId.value) {
		try {
			await interactiveModelingApi.resumeTask(taskId.value);
			isPaused.value = false;
		} catch (error) {
			console.error("恢复任务失败:", error);
		}
	}
};

const rollbackStep = async () => {
	try {
		await interactiveModelingApi.sendUserAction({
			task_id: taskId.value,
			action: "rollback",
		});
	} catch (error) {
		console.error("回退失败:", error);
	}
};

const viewStepResult = (step: { name: string; result?: unknown }) => {
	// 查看步骤详细结果
	console.log("查看步骤结果:", step);
};

const retryStep = async (step: { name: string; result?: unknown }) => {
	try {
		await interactiveModelingApi.sendUserAction({
			task_id: taskId.value,
			action: "retry",
			feedback: { step: step.name },
		});
	} catch (error) {
		console.error("重试失败:", error);
	}
};

const viewNotebook = () => {
	// 查看Jupyter Notebook
	window.open(`/static/${taskId.value}/notebook.ipynb`, "_blank");
};

const viewReport = () => {
	// 查看报告
	window.open(`/static/${taskId.value}/report.md`, "_blank");
};

const downloadResults = () => {
	// 下载结果
	window.open(`/api/interactive/download-results/${taskId.value}`, "_blank");
};

const startNewModeling = () => {
	// 重新开始
	location.reload();
};

const clearMessages = () => {
	messages.value = [];
};

// 清理
onUnmounted(() => {
	if (websocket.value) {
		websocket.value.close();
	}
});

// 暴露给父组件
defineExpose({
	startModeling,
});
</script>

<style scoped>
.interactive-modeling-container {
  max-width: 1000px;
  margin: 0 auto;
}
</style>