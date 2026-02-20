/**
 * HIL (Human-in-the-Loop) Store 单元测试
 *
 * 覆盖场景：
 * - 事件队列管理（添加、弹出、清空）
 * - showNextEvent 逻辑（自动展示下一个待处理事件）
 * - 事件响应提交（approve / reject / modify / skip）
 * - 事件历史记录
 * - 事件类型标签与图标
 */

import { useHILStore } from "@/stores/hil";
import type { HILEvent, HILResponse } from "@/stores/hil";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ============================================================
// Mock task store，避免 HIL 提交响应时真正发送 WebSocket 消息
// 使用模块级共享 mock 函数，确保 HIL store 内部调用和测试中引用的是同一实例
// ============================================================
const mockSendWsMessage = vi.fn();
vi.mock("@/stores/task", () => ({
	useTaskStore: vi.fn(() => ({
		sendWsMessage: mockSendWsMessage,
	})),
}));

/**
 * 创建测试用的 HIL 事件
 */
function createMockEvent(overrides: Partial<HILEvent> = {}): HILEvent {
	return {
		event_id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		event_type: "plan_review",
		title: "方案审核",
		description: "请审核以下建模方案",
		phase: "modeling",
		options: [
			{
				id: "opt-1",
				label: "通过",
				description: "方案合理",
				is_default: true,
				metadata: {},
			},
			{
				id: "opt-2",
				label: "修改",
				description: "需要调整",
				is_default: false,
				metadata: {},
			},
		],
		current_value: null,
		metadata: {},
		timeout_seconds: 300,
		allow_custom_input: false,
		created_at: new Date().toISOString(),
		...overrides,
	};
}

describe("useHILStore", () => {
	let store: ReturnType<typeof useHILStore>;

	beforeEach(() => {
		setActivePinia(createPinia());
		store = useHILStore();
		// 每次测试前清除共享 mock 的调用记录
		mockSendWsMessage.mockClear();
	});

	// ========================================================
	// 初始状态
	// ========================================================
	describe("初始状态", () => {
		it("待处理事件队列应为空", () => {
			expect(store.pendingEvents).toEqual([]);
		});

		it("当前事件应为 null", () => {
			expect(store.currentEvent).toBeNull();
		});

		it("对话框应关闭", () => {
			expect(store.isDialogOpen).toBe(false);
		});

		it("事件历史应为空", () => {
			expect(store.eventHistory).toEqual([]);
		});

		it("hasPendingEvents 应为 false", () => {
			expect(store.hasPendingEvents).toBe(false);
		});
	});

	// ========================================================
	// 事件队列管理
	// ========================================================
	describe("事件队列管理", () => {
		it("handleHILEvent 应将事件添加到队列", () => {
			const event = createMockEvent({ event_id: "evt-1" });
			store.handleHILEvent(event);

			expect(store.pendingEvents).toHaveLength(1);
			expect(store.pendingEvents[0].event_id).toBe("evt-1");
			expect(store.hasPendingEvents).toBe(true);
		});

		it("首个事件应自动成为当前事件并打开对话框", () => {
			const event = createMockEvent({ event_id: "evt-first" });
			store.handleHILEvent(event);

			expect(store.currentEvent).not.toBeNull();
			expect(store.currentEvent?.event_id).toBe("evt-first");
			expect(store.isDialogOpen).toBe(true);
		});

		it("后续事件应排队，不覆盖当前事件", () => {
			const event1 = createMockEvent({
				event_id: "evt-1",
				title: "第一个事件",
			});
			const event2 = createMockEvent({
				event_id: "evt-2",
				title: "第二个事件",
			});

			store.handleHILEvent(event1);
			store.handleHILEvent(event2);

			expect(store.pendingEvents).toHaveLength(2);
			// 当前事件仍是第一个
			expect(store.currentEvent?.event_id).toBe("evt-1");
		});

		it("多个事件入队后 hasPendingEvents 应为 true", () => {
			store.handleHILEvent(createMockEvent({ event_id: "evt-a" }));
			store.handleHILEvent(createMockEvent({ event_id: "evt-b" }));
			store.handleHILEvent(createMockEvent({ event_id: "evt-c" }));

			expect(store.hasPendingEvents).toBe(true);
			expect(store.pendingEvents).toHaveLength(3);
		});
	});

	// ========================================================
	// showNextEvent 逻辑
	// ========================================================
	describe("showNextEvent 逻辑", () => {
		it("队列有事件时应展示第一个", () => {
			const event = createMockEvent({ event_id: "evt-show" });
			store.pendingEvents.push(event);
			store.showNextEvent();

			expect(store.currentEvent?.event_id).toBe("evt-show");
			expect(store.isDialogOpen).toBe(true);
		});

		it("队列为空时应关闭对话框并清空当前事件", () => {
			store.currentEvent = createMockEvent();
			store.isDialogOpen = true;

			store.showNextEvent();

			expect(store.currentEvent).toBeNull();
			expect(store.isDialogOpen).toBe(false);
		});
	});

	// ========================================================
	// 事件响应提交
	// ========================================================
	describe("事件响应提交", () => {
		let testEvent: HILEvent;

		beforeEach(() => {
			testEvent = createMockEvent({ event_id: "evt-submit-test" });
			store.handleHILEvent(testEvent);
		});

		it("submitResponse 应将事件从队列移除", () => {
			const response: HILResponse = {
				event_id: "evt-submit-test",
				decision: "approve",
				selected_option_id: "opt-1",
			};

			store.submitResponse(response);

			expect(
				store.pendingEvents.find((e) => e.event_id === "evt-submit-test"),
			).toBeUndefined();
		});

		it("submitResponse 应将事件记录到历史", () => {
			const response: HILResponse = {
				event_id: "evt-submit-test",
				decision: "approve",
			};

			store.submitResponse(response);

			expect(store.eventHistory).toHaveLength(1);
			expect(store.eventHistory[0].event.event_id).toBe("evt-submit-test");
			expect(store.eventHistory[0].response.decision).toBe("approve");
		});

		it("submitResponse 应关闭对话框", () => {
			store.submitResponse({
				event_id: "evt-submit-test",
				decision: "approve",
			});

			expect(store.isDialogOpen).toBe(false);
			expect(store.currentEvent).toBeNull();
		});

		it("submitResponse 应通过 WebSocket 发送消息", () => {
			store.submitResponse({
				event_id: "evt-submit-test",
				decision: "reject",
				user_comment: "方案需要修改",
			});

			// 使用模块级共享的 mockSendWsMessage 验证调用
			expect(mockSendWsMessage).toHaveBeenCalledWith(
				expect.objectContaining({
					type: "hil_response",
					event_id: "evt-submit-test",
					decision: "reject",
					user_comment: "方案需要修改",
				}),
			);
		});
	});

	// ========================================================
	// 快捷响应方法
	// ========================================================
	describe("快捷响应方法", () => {
		let testEvent: HILEvent;

		beforeEach(() => {
			testEvent = createMockEvent({
				event_id: "evt-shortcut",
				options: [
					{
						id: "default-opt",
						label: "默认选项",
						description: "",
						is_default: true,
						metadata: {},
					},
					{
						id: "other-opt",
						label: "其他选项",
						description: "",
						is_default: false,
						metadata: {},
					},
				],
			});
			store.handleHILEvent(testEvent);
		});

		it("approveWithDefault 应使用默认选项提交审批", () => {
			const result = store.approveWithDefault();

			expect(result).not.toBeNull();
			expect(store.eventHistory).toHaveLength(1);
			expect(store.eventHistory[0].response.decision).toBe("approve");
			expect(store.eventHistory[0].response.selected_option_id).toBe(
				"default-opt",
			);
		});

		it("approveWithDefault 无当前事件时应返回 null", () => {
			store.currentEvent = null;
			const result = store.approveWithDefault();
			expect(result).toBeNull();
		});

		it("rejectEvent 应以 reject 决策提交", () => {
			const result = store.rejectEvent("不符合要求");

			expect(result).not.toBeNull();
			expect(store.eventHistory[0].response.decision).toBe("reject");
			expect(store.eventHistory[0].response.user_comment).toBe("不符合要求");
		});

		it("rejectEvent 无当前事件时应返回 null", () => {
			store.currentEvent = null;
			expect(store.rejectEvent()).toBeNull();
		});

		it("selectOption 应以指定选项提交", () => {
			const result = store.selectOption("other-opt", "选择了其他方案");

			expect(result).not.toBeNull();
			expect(store.eventHistory[0].response.selected_option_id).toBe(
				"other-opt",
			);
			expect(store.eventHistory[0].response.user_comment).toBe(
				"选择了其他方案",
			);
		});

		it("selectOption 无当前事件时应返回 null", () => {
			store.currentEvent = null;
			expect(store.selectOption("opt-1")).toBeNull();
		});

		it("modifyValue 应以 modify 决策和自定义值提交", () => {
			const customValue = { learningRate: 0.001 };
			const result = store.modifyValue(customValue, "调整了学习率");

			expect(result).not.toBeNull();
			expect(store.eventHistory[0].response.decision).toBe("modify");
			expect(store.eventHistory[0].response.custom_value).toEqual(customValue);
		});

		it("modifyValue 无当前事件时应返回 null", () => {
			store.currentEvent = null;
			expect(store.modifyValue("any")).toBeNull();
		});

		it("skipEvent 应以 skip 决策提交", () => {
			const result = store.skipEvent("暂时跳过");

			expect(result).not.toBeNull();
			expect(store.eventHistory[0].response.decision).toBe("skip");
		});

		it("skipEvent 无当前事件时应返回 null", () => {
			store.currentEvent = null;
			expect(store.skipEvent()).toBeNull();
		});
	});

	// ========================================================
	// 清空操作
	// ========================================================
	describe("clearAll", () => {
		it("应清除所有待处理事件、当前事件并关闭对话框", () => {
			store.handleHILEvent(createMockEvent({ event_id: "evt-clear-1" }));
			store.handleHILEvent(createMockEvent({ event_id: "evt-clear-2" }));

			store.clearAll();

			expect(store.pendingEvents).toEqual([]);
			expect(store.currentEvent).toBeNull();
			expect(store.isDialogOpen).toBe(false);
		});
	});

	// ========================================================
	// 事件类型标签与图标
	// ========================================================
	describe("事件类型标签", () => {
		it("应返回已知事件类型的中文标签", () => {
			expect(store.getEventTypeLabel("model_selection")).toBe("模型选择");
			expect(store.getEventTypeLabel("plan_review")).toBe("方案审核");
			expect(store.getEventTypeLabel("parameter_adjustment")).toBe("参数调整");
			expect(store.getEventTypeLabel("quality_checkpoint")).toBe("质量检查");
			expect(store.getEventTypeLabel("error_recovery")).toBe("错误恢复");
			expect(store.getEventTypeLabel("agent_handoff")).toBe("模型升级");
			expect(store.getEventTypeLabel("result_approval")).toBe("结果确认");
			expect(store.getEventTypeLabel("custom")).toBe("自定义");
		});

		it("未知事件类型应返回原始字符串", () => {
			expect(store.getEventTypeLabel("unknown_type")).toBe("unknown_type");
		});
	});

	describe("事件类型图标", () => {
		it("应返回已知事件类型的图标", () => {
			expect(store.getEventTypeIcon("model_selection")).toBeTruthy();
			expect(store.getEventTypeIcon("plan_review")).toBeTruthy();
		});

		it("未知事件类型应返回默认图标", () => {
			const icon = store.getEventTypeIcon("some_random_type");
			expect(icon).toBeTruthy();
		});
	});
});
