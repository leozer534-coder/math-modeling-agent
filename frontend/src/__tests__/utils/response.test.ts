/**
 * Response 类型工具 单元测试
 *
 * 覆盖场景：
 * - 消息类型判别式联合（discriminated union）正确性
 * - 各消息类型的结构验证
 * - Message 联合类型的类型守卫行为
 * - 代码执行结果类型（OutputItem）的判别
 *
 * 说明：response.ts 主要导出 TypeScript 类型定义，
 * 运行时测试聚焦于类型守卫函数和对象结构的实际匹配行为。
 */

import { AgentType } from "@/utils/enum";
import type {
	BaseMessage,
	CoderMessage,
	CoordinatorMessage,
	ErrorExecution,
	ExecutionFormat,
	InterpreterMessage,
	Message,
	ModelerMessage,
	OutputItem,
	ProgressMessage,
	ResultExecution,
	ReviewerMessage,
	ScholarMessage,
	StdErrExecution,
	StdOutExecution,
	SystemMessage,
	SystemMessageType,
	TaskStatusMessage,
	ToolMessage,
	UserMessage,
	WriterMessage,
} from "@/utils/response";
import { describe, expect, it } from "vitest";

// ============================================================
// 辅助函数：根据 msg_type 筛选消息（模拟业务中常见的类型守卫模式）
// ============================================================

/** 判断是否为 agent 消息 */
function isAgentMessage(
	msg: Message,
): msg is
	| CoderMessage
	| WriterMessage
	| ModelerMessage
	| CoordinatorMessage
	| ReviewerMessage {
	return msg.msg_type === "agent";
}

/** 判断是否为 tool 消息 */
function isToolMessage(msg: Message): msg is ToolMessage {
	return msg.msg_type === "tool";
}

/** 判断是否为进度消息 */
function isProgressMessage(msg: Message): msg is ProgressMessage {
	return msg.msg_type === "progress";
}

/** 判断是否为任务状态消息 */
function isTaskStatusMessage(msg: Message): msg is TaskStatusMessage {
	return msg.msg_type === "task_status";
}

// ============================================================
// 消息类型判别式联合测试
// ============================================================
describe("Message 判别式联合", () => {
	describe("msg_type 判别", () => {
		it("应正确识别 system 消息", () => {
			const msg: SystemMessage = {
				id: "sys-1",
				msg_type: "system",
				type: "info",
				content: "任务已启动",
			};

			expect(msg.msg_type).toBe("system");
			expect(msg.type).toBe("info");
		});

		it("应正确识别 user 消息", () => {
			const msg: UserMessage = {
				id: "user-1",
				msg_type: "user",
				content: "请帮我建模",
			};

			expect(msg.msg_type).toBe("user");
		});

		it("应正确识别 agent 消息及其 agent_type", () => {
			const coderMsg: CoderMessage = {
				id: "coder-1",
				msg_type: "agent",
				agent_type: AgentType.CODER,
				content: "代码已生成",
			};

			expect(coderMsg.msg_type).toBe("agent");
			expect(coderMsg.agent_type).toBe(AgentType.CODER);
		});

		it("应正确识别 tool 消息", () => {
			const toolMsg: InterpreterMessage = {
				id: "tool-1",
				msg_type: "tool",
				tool_name: "execute_code",
				input: { code: 'print("hello")' },
				output: null,
			};

			expect(toolMsg.msg_type).toBe("tool");
			expect(toolMsg.tool_name).toBe("execute_code");
		});

		it("应正确识别 progress 消息", () => {
			const progressMsg: ProgressMessage = {
				id: "progress-1",
				msg_type: "progress",
				percent: 45,
				phase: "建模阶段",
				message: "正在构建数学模型...",
				elapsed_time: 120,
			};

			expect(progressMsg.msg_type).toBe("progress");
			expect(progressMsg.percent).toBe(45);
		});

		it("应正确识别 task_status 消息", () => {
			const statusMsg: TaskStatusMessage = {
				id: "status-1",
				msg_type: "task_status",
				status: "running",
				phase: "modeling",
			};

			expect(statusMsg.msg_type).toBe("task_status");
			expect(statusMsg.status).toBe("running");
		});
	});
});

// ============================================================
// 类型守卫函数测试
// ============================================================
describe("类型守卫函数", () => {
	const allMessages: Message[] = [
		{ id: "1", msg_type: "user", content: "用户输入" } as UserMessage,
		{
			id: "2",
			msg_type: "system",
			type: "info",
			content: "系统消息",
		} as SystemMessage,
		{
			id: "3",
			msg_type: "agent",
			agent_type: AgentType.CODER,
			content: "代码",
		} as CoderMessage,
		{
			id: "4",
			msg_type: "agent",
			agent_type: AgentType.WRITER,
			content: "论文",
		} as WriterMessage,
		{
			id: "5",
			msg_type: "agent",
			agent_type: AgentType.MODELER,
			content: "模型",
		} as ModelerMessage,
		{
			id: "6",
			msg_type: "agent",
			agent_type: AgentType.COORDINATOR,
			content: "调度",
		} as CoordinatorMessage,
		{
			id: "7",
			msg_type: "agent",
			agent_type: AgentType.REVIEWER,
			content: "审核",
		} as ReviewerMessage,
		{
			id: "8",
			msg_type: "tool",
			tool_name: "execute_code",
			input: { code: "" },
			output: null,
		} as InterpreterMessage,
		{
			id: "9",
			msg_type: "progress",
			percent: 50,
			phase: "test",
			message: "msg",
			elapsed_time: 10,
		} as ProgressMessage,
		{
			id: "10",
			msg_type: "task_status",
			status: "completed",
			phase: "done",
		} as TaskStatusMessage,
	];

	it("isAgentMessage 应正确筛选出 5 条 agent 消息", () => {
		const agents = allMessages.filter(isAgentMessage);
		expect(agents).toHaveLength(5);
		for (const msg of agents) {
			expect(msg.msg_type).toBe("agent");
		}
	});

	it("isToolMessage 应正确筛选出 tool 消息", () => {
		const tools = allMessages.filter(isToolMessage);
		expect(tools).toHaveLength(1);
		expect(tools[0].msg_type).toBe("tool");
	});

	it("isProgressMessage 应正确筛选出 progress 消息", () => {
		const progress = allMessages.filter(isProgressMessage);
		expect(progress).toHaveLength(1);
		expect(progress[0].percent).toBe(50);
	});

	it("isTaskStatusMessage 应正确筛选出 task_status 消息", () => {
		const status = allMessages.filter(isTaskStatusMessage);
		expect(status).toHaveLength(1);
		expect(status[0].status).toBe("completed");
	});
});

// ============================================================
// Agent 消息类型细分
// ============================================================
describe("Agent 消息类型细分", () => {
	it("CoderMessage 应具有 CODER agent_type", () => {
		const msg: CoderMessage = {
			id: "c1",
			msg_type: "agent",
			agent_type: AgentType.CODER,
			content: "代码片段",
		};
		expect(msg.agent_type).toBe("CoderAgent");
	});

	it("WriterMessage 应支持 sub_title 可选字段", () => {
		const msg: WriterMessage = {
			id: "w1",
			msg_type: "agent",
			agent_type: AgentType.WRITER,
			content: "论文段落",
			sub_title: "第二章 模型建立",
		};
		expect(msg.sub_title).toBe("第二章 模型建立");
	});

	it("WriterMessage 不带 sub_title 也应合法", () => {
		const msg: WriterMessage = {
			id: "w2",
			msg_type: "agent",
			agent_type: AgentType.WRITER,
			content: "论文段落",
		};
		expect(msg.sub_title).toBeUndefined();
	});

	it("ReviewerMessage 应支持 review_score 和 dimension_scores", () => {
		const msg: ReviewerMessage = {
			id: "r1",
			msg_type: "agent",
			agent_type: AgentType.REVIEWER,
			content: "审核报告",
			review_score: 85,
			dimension_scores: {
				模型合理性: 90,
				代码质量: 80,
				论文结构: 85,
			},
		};
		expect(msg.review_score).toBe(85);
		expect(msg.dimension_scores?.代码质量).toBe(80);
	});
});

// ============================================================
// 工具消息类型
// ============================================================
describe("工具消息类型", () => {
	it("InterpreterMessage 应具有 execute_code tool_name", () => {
		const msg: InterpreterMessage = {
			id: "i1",
			msg_type: "tool",
			tool_name: "execute_code",
			input: { code: "import numpy as np\nprint(np.pi)" },
			output: [{ res_type: "stdout", msg: "3.141592653589793" }],
		};
		expect(msg.tool_name).toBe("execute_code");
		expect(msg.input?.code).toContain("numpy");
		expect(msg.output).toHaveLength(1);
	});

	it("ScholarMessage 应具有 search_scholar tool_name", () => {
		const msg: ScholarMessage = {
			id: "s1",
			msg_type: "tool",
			tool_name: "search_scholar",
			input: {},
			output: ["Paper 1", "Paper 2"],
		};
		expect(msg.tool_name).toBe("search_scholar");
		expect(msg.output).toHaveLength(2);
	});

	it("InterpreterMessage 的 input 和 output 可以为 null", () => {
		const msg: InterpreterMessage = {
			id: "i2",
			msg_type: "tool",
			tool_name: "execute_code",
			input: null,
			output: null,
		};
		expect(msg.input).toBeNull();
		expect(msg.output).toBeNull();
	});
});

// ============================================================
// 代码执行结果类型（OutputItem）
// ============================================================
describe("OutputItem 类型判别", () => {
	it("stdout 类型结果应具有 res_type: stdout", () => {
		const item: StdOutExecution = {
			res_type: "stdout",
			msg: "输出内容",
		};
		expect(item.res_type).toBe("stdout");
	});

	it("stderr 类型结果应具有 res_type: stderr", () => {
		const item: StdErrExecution = {
			res_type: "stderr",
			msg: "警告信息",
		};
		expect(item.res_type).toBe("stderr");
	});

	it("result 类型应包含 format 字段", () => {
		const item: ResultExecution = {
			res_type: "result",
			format: "png",
			msg: "base64...",
		};
		expect(item.res_type).toBe("result");
		expect(item.format).toBe("png");
	});

	it("error 类型应包含 name, value, traceback", () => {
		const item: ErrorExecution = {
			res_type: "error",
			name: "ValueError",
			value: "invalid literal",
			traceback: "Traceback (most recent call last):\n  ...",
		};
		expect(item.res_type).toBe("error");
		expect(item.name).toBe("ValueError");
		expect(item.traceback).toContain("Traceback");
	});

	it("OutputItem 联合类型应可通过 res_type 判别", () => {
		const items: OutputItem[] = [
			{ res_type: "stdout", msg: "输出" },
			{ res_type: "stderr", msg: "错误" },
			{ res_type: "result", format: "text", msg: "结果" },
			{ res_type: "error", name: "Error", value: "msg", traceback: "" },
		];

		const stdout = items.filter((i) => i.res_type === "stdout");
		const stderr = items.filter((i) => i.res_type === "stderr");
		const result = items.filter((i) => i.res_type === "result");
		const error = items.filter((i) => i.res_type === "error");

		expect(stdout).toHaveLength(1);
		expect(stderr).toHaveLength(1);
		expect(result).toHaveLength(1);
		expect(error).toHaveLength(1);
	});
});

// ============================================================
// 进度消息详细字段
// ============================================================
describe("ProgressMessage 详细字段", () => {
	it("必填字段应全部存在", () => {
		const msg: ProgressMessage = {
			id: "p1",
			msg_type: "progress",
			percent: 75,
			phase: "代码执行",
			message: "正在执行第 3 个代码块...",
			elapsed_time: 240,
		};

		expect(msg.percent).toBe(75);
		expect(msg.phase).toBe("代码执行");
		expect(msg.message).toContain("代码块");
		expect(msg.elapsed_time).toBe(240);
	});

	it("可选字段应支持不传", () => {
		const msg: ProgressMessage = {
			id: "p2",
			msg_type: "progress",
			percent: 50,
			phase: "建模",
			message: "进行中",
			elapsed_time: 100,
		};

		expect(msg.sub_phase).toBeUndefined();
		expect(msg.iteration).toBeUndefined();
		expect(msg.max_iterations).toBeUndefined();
		expect(msg.quality_score).toBeUndefined();
	});

	it("可选字段应支持传值", () => {
		const msg: ProgressMessage = {
			id: "p3",
			msg_type: "progress",
			percent: 60,
			phase: "代码调试",
			message: "第 2 轮迭代",
			elapsed_time: 180,
			sub_phase: "错误修复",
			iteration: 2,
			max_iterations: 5,
			quality_score: 72,
		};

		expect(msg.sub_phase).toBe("错误修复");
		expect(msg.iteration).toBe(2);
		expect(msg.max_iterations).toBe(5);
		expect(msg.quality_score).toBe(72);
	});
});

// ============================================================
// TaskStatusMessage 状态枚举
// ============================================================
describe("TaskStatusMessage 状态值", () => {
	const validStatuses = [
		"pending",
		"running",
		"completed",
		"failed",
		"cancelled",
	] as const;

	for (const status of validStatuses) {
		it(`应支持状态值: ${status}`, () => {
			const msg: TaskStatusMessage = {
				id: `ts-${status}`,
				msg_type: "task_status",
				status,
				phase: "test",
			};
			expect(msg.status).toBe(status);
		});
	}

	it("error 字段应为可选", () => {
		const msgWithoutError: TaskStatusMessage = {
			id: "ts-ok",
			msg_type: "task_status",
			status: "completed",
			phase: "done",
		};
		expect(msgWithoutError.error).toBeUndefined();

		const msgWithError: TaskStatusMessage = {
			id: "ts-err",
			msg_type: "task_status",
			status: "failed",
			phase: "coding",
			error: "代码执行超时",
		};
		expect(msgWithError.error).toBe("代码执行超时");
	});
});

// ============================================================
// SystemMessageType 枚举值
// ============================================================
describe("SystemMessageType 枚举值", () => {
	const validTypes: SystemMessageType[] = [
		"info",
		"warning",
		"success",
		"error",
	];

	for (const type of validTypes) {
		it(`应支持系统消息类型: ${type}`, () => {
			const msg: SystemMessage = {
				id: `sys-${type}`,
				msg_type: "system",
				type,
				content: `${type} 消息`,
			};
			expect(msg.type).toBe(type);
		});
	}
});

// ============================================================
// BaseMessage 公共字段
// ============================================================
describe("BaseMessage 公共字段", () => {
	it("seq 字段应为可选", () => {
		const msgWithSeq: UserMessage = {
			id: "u1",
			msg_type: "user",
			content: "消息",
			seq: 42,
		};
		expect(msgWithSeq.seq).toBe(42);

		const msgWithoutSeq: UserMessage = {
			id: "u2",
			msg_type: "user",
			content: "消息",
		};
		expect(msgWithoutSeq.seq).toBeUndefined();
	});

	it("is_replay 字段应为可选", () => {
		const replayMsg: UserMessage = {
			id: "u3",
			msg_type: "user",
			content: "回放消息",
			is_replay: true,
			seq: 10,
		};
		expect(replayMsg.is_replay).toBe(true);
	});

	it("content 字段应支持 null", () => {
		const msg: SystemMessage = {
			id: "sys-null",
			msg_type: "system",
			type: "info",
			content: null,
		};
		expect(msg.content).toBeNull();
	});
});

// ============================================================
// ExecutionFormat 枚举值
// ============================================================
describe("ExecutionFormat 枚举值", () => {
	const validFormats: ExecutionFormat[] = [
		"text",
		"html",
		"markdown",
		"png",
		"jpeg",
		"svg",
		"pdf",
		"latex",
		"json",
		"javascript",
	];

	for (const format of validFormats) {
		it(`应支持执行结果格式: ${format}`, () => {
			const item: ResultExecution = {
				res_type: "result",
				format,
				msg: `${format} 内容`,
			};
			expect(item.format).toBe(format);
		});
	}
});
