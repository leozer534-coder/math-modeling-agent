import { useTaskStore } from "@/stores/task";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export interface HILOption {
	id: string;
	label: string;
	description: string;
	is_default: boolean;
	metadata: Record<string, string | number | boolean>;
}

export interface HILEvent {
	event_id: string;
	event_type: string;
	title: string;
	description: string;
	phase: string;
	options: HILOption[];
	current_value: string | number | boolean | null;
	metadata: Record<string, string | number | boolean>;
	timeout_seconds: number;
	allow_custom_input: boolean;
	created_at: string;
}

export interface HILResponse {
	event_id: string;
	decision:
		| "approve"
		| "reject"
		| "modify"
		| "skip"
		| "retry"
		| "escalate"
		| "timeout";
	selected_option_id?: string;
	custom_value?: string | number | boolean | null;
	user_comment?: string;
}

export const useHILStore = defineStore("hil", () => {
	const pendingEvents = ref<HILEvent[]>([]);
	const currentEvent = ref<HILEvent | null>(null);
	const isDialogOpen = ref(false);
	const eventHistory = ref<{ event: HILEvent; response: HILResponse }[]>([]);

	const hasPendingEvents = computed(() => pendingEvents.value.length > 0);

	function handleHILEvent(event: HILEvent) {
		pendingEvents.value.push(event);

		if (!currentEvent.value) {
			showNextEvent();
		}
	}

	function showNextEvent() {
		if (pendingEvents.value.length > 0) {
			currentEvent.value = pendingEvents.value[0];
			isDialogOpen.value = true;
		} else {
			currentEvent.value = null;
			isDialogOpen.value = false;
		}
	}

	function submitResponse(response: HILResponse) {
		// 通过 WebSocket 将用户决策发送到后端
		const taskStore = useTaskStore();
		taskStore.sendWsMessage({
			type: "hil_response",
			event_id: response.event_id,
			decision: response.decision,
			selected_option_id: response.selected_option_id,
			custom_value: response.custom_value,
			user_comment: response.user_comment,
		});

		// 保留本地状态管理（历史记录）
		if (currentEvent.value) {
			eventHistory.value.push({
				event: currentEvent.value,
				response: response,
			});

			pendingEvents.value = pendingEvents.value.filter(
				(e) => e.event_id !== response.event_id,
			);
		}

		isDialogOpen.value = false;
		currentEvent.value = null;

		setTimeout(() => showNextEvent(), 300);

		return response;
	}

	function approveWithDefault() {
		if (!currentEvent.value) return null;

		const defaultOption = currentEvent.value.options.find((o) => o.is_default);

		return submitResponse({
			event_id: currentEvent.value.event_id,
			decision: "approve",
			selected_option_id: defaultOption?.id,
		});
	}

	function rejectEvent(comment?: string) {
		if (!currentEvent.value) return null;

		return submitResponse({
			event_id: currentEvent.value.event_id,
			decision: "reject",
			user_comment: comment,
		});
	}

	function selectOption(optionId: string, comment?: string) {
		if (!currentEvent.value) return null;

		return submitResponse({
			event_id: currentEvent.value.event_id,
			decision: "approve",
			selected_option_id: optionId,
			user_comment: comment,
		});
	}

	function modifyValue(
		customValue: string | number | boolean | null,
		comment?: string,
	) {
		if (!currentEvent.value) return null;

		return submitResponse({
			event_id: currentEvent.value.event_id,
			decision: "modify",
			custom_value: customValue,
			user_comment: comment,
		});
	}

	function skipEvent(comment?: string) {
		if (!currentEvent.value) return null;

		return submitResponse({
			event_id: currentEvent.value.event_id,
			decision: "skip",
			user_comment: comment,
		});
	}

	function clearAll() {
		pendingEvents.value = [];
		currentEvent.value = null;
		isDialogOpen.value = false;
	}

	function getEventTypeLabel(eventType: string): string {
		const labels: Record<string, string> = {
			model_selection: "模型选择",
			plan_review: "方案审核",
			parameter_adjustment: "参数调整",
			quality_checkpoint: "质量检查",
			error_recovery: "错误恢复",
			agent_handoff: "模型升级",
			result_approval: "结果确认",
			custom: "自定义",
		};
		return labels[eventType] || eventType;
	}

	function getEventTypeIcon(eventType: string): string {
		const icons: Record<string, string> = {
			model_selection: "🔧",
			plan_review: "📋",
			parameter_adjustment: "⚙️",
			quality_checkpoint: "✅",
			error_recovery: "🔄",
			agent_handoff: "🚀",
			result_approval: "📊",
			custom: "💬",
		};
		return icons[eventType] || "❓";
	}

	return {
		pendingEvents,
		currentEvent,
		isDialogOpen,
		eventHistory,
		hasPendingEvents,

		handleHILEvent,
		showNextEvent,
		submitResponse,
		approveWithDefault,
		rejectEvent,
		selectOption,
		modifyValue,
		skipEvent,
		clearAll,
		getEventTypeLabel,
		getEventTypeIcon,
	};
});
