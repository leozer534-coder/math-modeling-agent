/**
 * WebSocket 工具类 单元测试
 *
 * 覆盖场景：
 * - TaskWebSocket 实例化与参数传递
 * - connect() 连接建立流程
 * - 认证流程（first-message auth）
 * - 消息收发（认证前缓存、认证后转发）
 * - 心跳机制（ping/pong）
 * - 断连重连策略（两阶段：指数退避 + 固定间隔）
 * - 重连次数耗尽回调
 * - manualReconnect 手动重连
 * - close 主动关闭
 * - 消息回补（replay）
 * - send 在未连接时的行为
 */

import { TaskWebSocket } from "@/utils/websocket";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// ============================================================
// Mock WebSocket 全局对象
// ============================================================

/** 模拟的 WebSocket 实例，用于捕获事件处理器和验证调用 */
class MockWebSocket {
	static readonly CONNECTING = 0;
	static readonly OPEN = 1;
	static readonly CLOSING = 2;
	static readonly CLOSED = 3;

	url: string;
	readyState: number = MockWebSocket.OPEN;

	onopen: ((event: Event) => void) | null = null;
	onmessage: ((event: MessageEvent) => void) | null = null;
	onclose: ((event: CloseEvent) => void) | null = null;
	onerror: ((event: Event) => void) | null = null;

	send = vi.fn();
	close = vi.fn().mockImplementation(() => {
		this.readyState = MockWebSocket.CLOSED;
	});

	constructor(url: string) {
		this.url = url;
		// 保存最近创建的实例，供测试访问
		mockWebSocketInstances.push(this);
	}

	/** 模拟触发 onopen 事件 */
	simulateOpen() {
		this.readyState = MockWebSocket.OPEN;
		this.onopen?.(new Event("open"));
	}

	/** 模拟收到服务端消息 */
	simulateMessage(data: Record<string, unknown>) {
		this.onmessage?.(
			new MessageEvent("message", { data: JSON.stringify(data) }),
		);
	}

	/** 模拟连接关闭 */
	simulateClose(code = 1006, reason = "") {
		this.readyState = MockWebSocket.CLOSED;
		this.onclose?.({ code, reason, wasClean: code === 1000 } as CloseEvent);
	}

	/** 模拟连接错误 */
	simulateError() {
		this.onerror?.(new Event("error"));
	}
}

// 存储所有创建的 MockWebSocket 实例
let mockWebSocketInstances: MockWebSocket[] = [];

// 获取最新创建的 MockWebSocket 实例
function getLatestWs(): MockWebSocket {
	return mockWebSocketInstances[mockWebSocketInstances.length - 1];
}

// 替换全局 WebSocket
vi.stubGlobal("WebSocket", MockWebSocket);

describe("TaskWebSocket", () => {
	let onMessage: ReturnType<typeof vi.fn>;
	let onConnectionStatus: ReturnType<typeof vi.fn>;
	let onReconnectProgress: ReturnType<typeof vi.fn>;
	let onReconnectFailed: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		vi.useFakeTimers();
		mockWebSocketInstances = [];
		onMessage = vi.fn();
		onConnectionStatus = vi.fn();
		onReconnectProgress = vi.fn();
		onReconnectFailed = vi.fn();

		// 模拟 localStorage 中存在 auth_token
		localStorage.setItem("auth_token", "test-jwt-token");
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	/** 创建 TaskWebSocket 实例的辅助函数 */
	function createWs(url = "ws://localhost:8000/task/test-123"): TaskWebSocket {
		return new TaskWebSocket(
			url,
			onMessage,
			onConnectionStatus,
			onReconnectProgress,
			onReconnectFailed,
		);
	}

	// ========================================================
	// 实例化
	// ========================================================
	describe("实例化", () => {
		it("应正确创建实例", () => {
			const ws = createWs();
			expect(ws).toBeInstanceOf(TaskWebSocket);
		});

		it("初始 readyState 应为 CLOSED", () => {
			const ws = createWs();
			expect(ws.getReadyState()).toBe(MockWebSocket.CLOSED);
		});

		it("初始 lastSequenceId 应为 0", () => {
			const ws = createWs();
			expect(ws.getLastSequenceId()).toBe(0);
		});
	});

	// ========================================================
	// connect() 连接建立
	// ========================================================
	describe("connect - 连接建立", () => {
		it("应创建 WebSocket 连接", () => {
			const ws = createWs("ws://localhost:8000/task/abc");
			ws.connect();

			expect(mockWebSocketInstances).toHaveLength(1);
			expect(getLatestWs().url).toBe("ws://localhost:8000/task/abc");
		});

		it("连接打开后应发送认证消息", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();

			// 应调用 send 发送认证消息
			expect(mockWs.send).toHaveBeenCalledWith(
				JSON.stringify({ type: "auth", token: "test-jwt-token" }),
			);
		});

		it("无 auth_token 时应报告 auth_failed", () => {
			localStorage.removeItem("auth_token");

			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();

			expect(onConnectionStatus).toHaveBeenCalledWith("auth_failed");
		});

		it("已连接时再次调用 connect 应无效", () => {
			const ws = createWs();
			ws.connect();

			const firstWs = getLatestWs();
			firstWs.readyState = MockWebSocket.OPEN;

			ws.connect();

			// 不应创建第二个 WebSocket
			expect(mockWebSocketInstances).toHaveLength(1);
		});
	});

	// ========================================================
	// 认证流程
	// ========================================================
	describe("认证流程", () => {
		it("收到 auth_ok 后应通知 connected 状态", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			expect(onConnectionStatus).toHaveBeenCalledWith("connected");
		});

		it("收到 auth_error 后应通知 auth_failed 状态", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_error", message: "Token 过期" });

			expect(onConnectionStatus).toHaveBeenCalledWith("auth_failed");
		});

		it("auth_error 后不应自动重连", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_error", message: "Invalid token" });

			// 模拟连接关闭
			mockWs.simulateClose(1000);

			// 快进定时器，不应有重连
			vi.advanceTimersByTime(60000);
			expect(mockWebSocketInstances).toHaveLength(1);
		});
	});

	// ========================================================
	// 消息收发
	// ========================================================
	describe("消息收发", () => {
		/** 完成认证流程的辅助函数 */
		function connectAndAuth(ws: TaskWebSocket): MockWebSocket {
			ws.connect();
			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });
			return mockWs;
		}

		it("认证后收到的业务消息应转发给 onMessage", () => {
			const ws = createWs();
			const mockWs = connectAndAuth(ws);

			const businessMsg = {
				msg_type: "agent",
				agent_type: "CoderAgent",
				content: "代码生成完成",
			};
			mockWs.simulateMessage(businessMsg);

			expect(onMessage).toHaveBeenCalledWith(businessMsg);
		});

		it("认证前收到的业务消息不应转发", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();

			// 未完成认证就发来业务消息
			mockWs.simulateMessage({ msg_type: "agent", content: "不应收到" });

			expect(onMessage).not.toHaveBeenCalled();
		});

		it("pong 消息不应转发给 onMessage", () => {
			const ws = createWs();
			const mockWs = connectAndAuth(ws);

			mockWs.simulateMessage({ type: "pong" });

			// onMessage 不应被 pong 消息调用
			expect(onMessage).not.toHaveBeenCalled();
		});

		it("send 在认证后应直接发送", () => {
			const ws = createWs();
			const mockWs = connectAndAuth(ws);

			// 清除认证时的 send 调用记录
			mockWs.send.mockClear();

			ws.send({ type: "user_input", content: "你好" });

			expect(mockWs.send).toHaveBeenCalledWith(
				JSON.stringify({ type: "user_input", content: "你好" }),
			);
		});

		it("send 在认证前应缓存消息", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();

			// 清除认证消息的 send 记录
			mockWs.send.mockClear();

			// 认证前发送业务消息
			ws.send({ type: "user_input", content: "缓存消息" });

			// 不应直接发送
			expect(mockWs.send).not.toHaveBeenCalled();

			// 认证完成后应自动发送缓存的消息
			mockWs.simulateMessage({ type: "auth_ok" });

			expect(mockWs.send).toHaveBeenCalledWith(
				JSON.stringify({ type: "user_input", content: "缓存消息" }),
			);
		});

		it("send 在未连接时不应抛出异常", () => {
			const ws = createWs();
			// 未调用 connect，直接 send 不应崩溃
			expect(() => ws.send({ type: "test" })).not.toThrow();
		});

		it("应记录 seq 序列号", () => {
			const ws = createWs();
			const mockWs = connectAndAuth(ws);

			mockWs.simulateMessage({ msg_type: "agent", content: "消息1", seq: 5 });
			expect(ws.getLastSequenceId()).toBe(5);

			mockWs.simulateMessage({ msg_type: "agent", content: "消息2", seq: 10 });
			expect(ws.getLastSequenceId()).toBe(10);
		});

		it("seq 不应回退（只记录更大的值）", () => {
			const ws = createWs();
			const mockWs = connectAndAuth(ws);

			mockWs.simulateMessage({ msg_type: "agent", content: "消息1", seq: 10 });
			mockWs.simulateMessage({ msg_type: "agent", content: "旧消息", seq: 5 });

			expect(ws.getLastSequenceId()).toBe(10);
		});
	});

	// ========================================================
	// 断连重连策略
	// ========================================================
	describe("断连重连策略", () => {
		it("非正常关闭时应触发自动重连", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 模拟异常断连（code !== 1000）
			mockWs.simulateClose(1006);

			expect(onConnectionStatus).toHaveBeenCalledWith("disconnected");
			expect(onConnectionStatus).toHaveBeenCalledWith("reconnecting");
		});

		it("正常关闭（code 1000）且 shouldReconnect 为 false 时不应重连", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 主动关闭会设置 shouldReconnect = false
			ws.close();

			// 清除状态回调记录
			onConnectionStatus.mockClear();

			// 不应有 reconnecting 回调
			vi.advanceTimersByTime(60000);
			expect(onConnectionStatus).not.toHaveBeenCalledWith("reconnecting");
		});

		it("重连应通知进度回调", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			mockWs.simulateClose(1006);

			// 第一次重连
			expect(onReconnectProgress).toHaveBeenCalledWith(1, 30);
		});

		it("前 10 次重连应使用指数退避策略", () => {
			const ws = createWs();
			ws.connect();

			let mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 触发断连
			mockWs.simulateClose(1006);

			// 第 1 次重连延迟 1s
			expect(mockWebSocketInstances).toHaveLength(1);
			vi.advanceTimersByTime(1000);
			expect(mockWebSocketInstances).toHaveLength(2);

			// 模拟第二次连接也断了
			mockWs = getLatestWs();
			mockWs.simulateClose(1006);

			// 第 2 次重连延迟 2s
			vi.advanceTimersByTime(1999);
			expect(mockWebSocketInstances).toHaveLength(2);
			vi.advanceTimersByTime(1);
			expect(mockWebSocketInstances).toHaveLength(3);
		});

		it("超过最大重连次数应通知 reconnect_exhausted", () => {
			const ws = createWs();
			ws.connect();

			// 首次连接后直接断连（不触发 auth，模拟网络不可达）
			const firstWs = getLatestWs();
			firstWs.simulateClose(1006);

			// 模拟 30 次重连全部失败（连接后立即断开，不触发 onopen，
			// 这样 reconnectAttempts 不会被重置）
			for (let i = 0; i < 30; i++) {
				// 快进足够长时间触发下一次重连
				vi.advanceTimersByTime(35000);
				// 新创建的连接也立即失败
				const mockWs = getLatestWs();
				mockWs.simulateClose(1006);
			}

			expect(onConnectionStatus).toHaveBeenCalledWith("reconnect_exhausted");
			expect(onReconnectFailed).toHaveBeenCalled();
		});
	});

	// ========================================================
	// manualReconnect 手动重连
	// ========================================================
	describe("manualReconnect", () => {
		it("手动重连应重置重连计数", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			ws.manualReconnect();

			// 应创建新的 WebSocket 连接
			expect(mockWebSocketInstances.length).toBeGreaterThan(1);
		});
	});

	// ========================================================
	// close 主动关闭
	// ========================================================
	describe("close - 主动关闭", () => {
		it("close 应关闭 WebSocket 连接", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();

			ws.close();

			expect(mockWs.close).toHaveBeenCalledWith(
				1000,
				"Client closed connection",
			);
		});

		it("close 后 getReadyState 应返回 CLOSED", () => {
			const ws = createWs();
			ws.connect();

			ws.close();

			expect(ws.getReadyState()).toBe(MockWebSocket.CLOSED);
		});
	});

	// ========================================================
	// 消息回补（replay）
	// ========================================================
	describe("消息回补", () => {
		it("重连后认证成功且有历史 seq 时应发送 replay 请求", () => {
			const ws = createWs();
			ws.connect();

			let mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 收到几条带 seq 的消息
			mockWs.simulateMessage({ msg_type: "agent", content: "消息1", seq: 5 });
			mockWs.simulateMessage({ msg_type: "agent", content: "消息2", seq: 10 });

			// 断连
			mockWs.simulateClose(1006);

			// 等待重连
			vi.advanceTimersByTime(1000);

			// 新连接的认证
			mockWs = getLatestWs();
			mockWs.simulateOpen();

			// 清除之前的 send 调用
			mockWs.send.mockClear();

			// 认证成功
			mockWs.simulateMessage({ type: "auth_ok" });

			// 应发送 replay 请求
			const sendCalls = mockWs.send.mock.calls.map((call: [string]) =>
				JSON.parse(call[0]),
			);
			const replayCall = sendCalls.find(
				(msg: Record<string, unknown>) => msg.type === "replay",
			);
			expect(replayCall).toBeDefined();
			expect(replayCall.last_sequence_id).toBe(10);
		});

		it("首次连接认证成功时不应发送 replay 请求", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();

			// 清除认证消息的 send 记录
			mockWs.send.mockClear();

			mockWs.simulateMessage({ type: "auth_ok" });

			// 首次连接不应发送 replay
			const sendCalls = mockWs.send.mock.calls.map((call: [string]) =>
				JSON.parse(call[0]),
			);
			const replayCall = sendCalls.find(
				(msg: Record<string, unknown>) => msg.type === "replay",
			);
			expect(replayCall).toBeUndefined();
		});
	});

	// ========================================================
	// 心跳机制
	// ========================================================
	describe("心跳机制", () => {
		it("认证成功后应启动心跳定时器", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 清除之前的 send 调用
			mockWs.send.mockClear();

			// 快进 30s（PING_INTERVAL）
			vi.advanceTimersByTime(30000);

			// 应发送 ping
			const sendCalls = mockWs.send.mock.calls.map((call: [string]) =>
				JSON.parse(call[0]),
			);
			expect(
				sendCalls.some((msg: Record<string, unknown>) => msg.type === "ping"),
			).toBe(true);
		});

		it("收到 pong 后应清除超时定时器（不触发断连）", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 快进触发 ping
			vi.advanceTimersByTime(30000);

			// 模拟收到 pong
			mockWs.simulateMessage({ type: "pong" });

			// 再快进 10s（PONG_TIMEOUT），不应关闭连接
			mockWs.close.mockClear();
			vi.advanceTimersByTime(10000);

			expect(mockWs.close).not.toHaveBeenCalled();
		});

		it("未收到 pong 超时后应关闭连接", () => {
			const ws = createWs();
			ws.connect();

			const mockWs = getLatestWs();
			mockWs.simulateOpen();
			mockWs.simulateMessage({ type: "auth_ok" });

			// 清除之前的 close 调用
			mockWs.close.mockClear();

			// 快进触发 ping
			vi.advanceTimersByTime(30000);

			// 不发送 pong，等待超时
			vi.advanceTimersByTime(10000);

			expect(mockWs.close).toHaveBeenCalled();
		});
	});
});
