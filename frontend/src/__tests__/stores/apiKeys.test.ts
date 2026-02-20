/**
 * ApiKeys Store 单元测试
 *
 * 覆盖场景：
 * - 初始状态验证
 * - 供应商 CRUD（增删改查）
 * - 供应商状态更新
 * - Agent 分配管理
 * - 计算属性（各 Agent 的 ModelConfig 映射）
 * - isEmpty 计算属性
 * - OpenAlex Email 管理
 * - getAllAgentConfigs 聚合查询
 * - resetAll 重置
 * - 删除供应商时自动清除关联的 Agent 分配
 */

import { useApiKeyStore } from "@/stores/apiKeys";
import type { AgentAssignment, ProviderConfig } from "@/stores/apiKeys";
import { AgentType } from "@/utils/enum";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

/**
 * 创建测试用的供应商配置
 */
function createMockProvider(
	overrides: Partial<ProviderConfig> = {},
): ProviderConfig {
	return {
		id: `provider-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
		name: "DeepSeek",
		apiKey: "sk-test-key-xxx",
		baseUrl: "https://api.deepseek.com",
		modelId: "deepseek-chat",
		apiFormat: "openai",
		status: "untested",
		...overrides,
	};
}

describe("useApiKeyStore", () => {
	let store: ReturnType<typeof useApiKeyStore>;

	beforeEach(() => {
		setActivePinia(createPinia());
		store = useApiKeyStore();
	});

	// ========================================================
	// 初始状态
	// ========================================================
	describe("初始状态", () => {
		it("供应商列表应为空", () => {
			expect(store.providers).toEqual([]);
		});

		it("Agent 分配应全部为空字符串", () => {
			expect(store.agentAssignment).toEqual({
				coordinator: "",
				modeler: "",
				coder: "",
				writer: "",
			});
		});

		it("openalexEmail 应为空字符串", () => {
			expect(store.openalexEmail).toBe("");
		});

		it("isEmpty 应为 true", () => {
			expect(store.isEmpty).toBe(true);
		});
	});

	// ========================================================
	// 供应商 CRUD
	// ========================================================
	describe("供应商管理", () => {
		it("addProvider 应正确添加供应商", () => {
			const provider = createMockProvider({ id: "p1", name: "OpenAI" });
			store.addProvider(provider);

			expect(store.providers).toHaveLength(1);
			expect(store.providers[0].id).toBe("p1");
			expect(store.providers[0].name).toBe("OpenAI");
			expect(store.isEmpty).toBe(false);
		});

		it("addProvider 应支持添加多个供应商", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			store.addProvider(createMockProvider({ id: "p2" }));
			store.addProvider(createMockProvider({ id: "p3" }));

			expect(store.providers).toHaveLength(3);
		});

		it("updateProvider 应正确更新已有供应商", () => {
			const provider = createMockProvider({ id: "p1", name: "旧名称" });
			store.addProvider(provider);

			store.updateProvider({ ...provider, name: "新名称", modelId: "gpt-4o" });

			expect(store.providers[0].name).toBe("新名称");
			expect(store.providers[0].modelId).toBe("gpt-4o");
		});

		it("updateProvider 对不存在的 ID 应无副作用", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			const originalLength = store.providers.length;

			store.updateProvider(createMockProvider({ id: "non-existent" }));

			expect(store.providers).toHaveLength(originalLength);
		});

		it("deleteProvider 应正确删除供应商", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			store.addProvider(createMockProvider({ id: "p2" }));

			store.deleteProvider("p1");

			expect(store.providers).toHaveLength(1);
			expect(store.providers[0].id).toBe("p2");
		});

		it("deleteProvider 对不存在的 ID 应无副作用", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			store.deleteProvider("non-existent");
			expect(store.providers).toHaveLength(1);
		});

		it("删除供应商后 isEmpty 应正确更新", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			expect(store.isEmpty).toBe(false);

			store.deleteProvider("p1");
			expect(store.isEmpty).toBe(true);
		});
	});

	// ========================================================
	// 供应商状态更新
	// ========================================================
	describe("供应商状态更新", () => {
		it("updateProviderStatus 应正确更新状态为 valid", () => {
			store.addProvider(createMockProvider({ id: "p1", status: "untested" }));
			store.updateProviderStatus("p1", "valid");
			expect(store.providers[0].status).toBe("valid");
		});

		it("updateProviderStatus 应正确更新状态为 invalid", () => {
			store.addProvider(createMockProvider({ id: "p1", status: "valid" }));
			store.updateProviderStatus("p1", "invalid");
			expect(store.providers[0].status).toBe("invalid");
		});

		it("updateProviderStatus 对不存在的 ID 应无副作用", () => {
			store.addProvider(createMockProvider({ id: "p1", status: "untested" }));
			store.updateProviderStatus("non-existent", "valid");
			expect(store.providers[0].status).toBe("untested");
		});
	});

	// ========================================================
	// Agent 分配管理
	// ========================================================
	describe("Agent 分配管理", () => {
		it("setAgentAssignment 应正确设置部分分配", () => {
			store.setAgentAssignment({ coordinator: "p1", coder: "p2" });

			expect(store.agentAssignment.coordinator).toBe("p1");
			expect(store.agentAssignment.coder).toBe("p2");
			// 未设置的保持原值
			expect(store.agentAssignment.modeler).toBe("");
			expect(store.agentAssignment.writer).toBe("");
		});

		it("setAgentAssignment 应支持覆盖已有分配", () => {
			store.setAgentAssignment({ coordinator: "p1" });
			store.setAgentAssignment({ coordinator: "p2" });

			expect(store.agentAssignment.coordinator).toBe("p2");
		});

		it("setAgentAssignment 应支持一次性设置全部", () => {
			const assignment: AgentAssignment = {
				coordinator: "p1",
				modeler: "p2",
				coder: "p3",
				writer: "p4",
			};
			store.setAgentAssignment(assignment);

			expect(store.agentAssignment).toEqual(assignment);
		});

		it("删除供应商时应自动清除关联的 Agent 分配", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			store.setAgentAssignment({
				coordinator: "p1",
				modeler: "p1",
				coder: "p1",
				writer: "p1",
			});

			store.deleteProvider("p1");

			expect(store.agentAssignment.coordinator).toBe("");
			expect(store.agentAssignment.modeler).toBe("");
			expect(store.agentAssignment.coder).toBe("");
			expect(store.agentAssignment.writer).toBe("");
		});

		it("删除供应商时不应影响其他供应商的分配", () => {
			store.addProvider(createMockProvider({ id: "p1" }));
			store.addProvider(createMockProvider({ id: "p2" }));
			store.setAgentAssignment({
				coordinator: "p1",
				modeler: "p2",
				coder: "p1",
				writer: "p2",
			});

			store.deleteProvider("p1");

			expect(store.agentAssignment.coordinator).toBe("");
			expect(store.agentAssignment.modeler).toBe("p2");
			expect(store.agentAssignment.coder).toBe("");
			expect(store.agentAssignment.writer).toBe("p2");
		});
	});

	// ========================================================
	// 计算属性（Agent ModelConfig 映射）
	// ========================================================
	describe("Agent ModelConfig 计算属性", () => {
		const testProvider: ProviderConfig = {
			id: "provider-deepseek",
			name: "DeepSeek",
			apiKey: "sk-deepseek-key",
			baseUrl: "https://api.deepseek.com",
			modelId: "deepseek-chat",
			apiFormat: "openai",
			status: "valid",
		};

		beforeEach(() => {
			store.addProvider(testProvider);
		});

		it("coordinatorConfig 应正确映射供应商配置", () => {
			store.setAgentAssignment({ coordinator: "provider-deepseek" });

			expect(store.coordinatorConfig).toEqual({
				apiKey: "sk-deepseek-key",
				baseUrl: "https://api.deepseek.com",
				modelId: "deepseek-chat",
				provider: "DeepSeek",
			});
		});

		it("modelerConfig 应正确映射供应商配置", () => {
			store.setAgentAssignment({ modeler: "provider-deepseek" });

			expect(store.modelerConfig).toEqual({
				apiKey: "sk-deepseek-key",
				baseUrl: "https://api.deepseek.com",
				modelId: "deepseek-chat",
				provider: "DeepSeek",
			});
		});

		it("coderConfig 应正确映射供应商配置", () => {
			store.setAgentAssignment({ coder: "provider-deepseek" });

			expect(store.coderConfig).toEqual({
				apiKey: "sk-deepseek-key",
				baseUrl: "https://api.deepseek.com",
				modelId: "deepseek-chat",
				provider: "DeepSeek",
			});
		});

		it("writerConfig 应正确映射供应商配置", () => {
			store.setAgentAssignment({ writer: "provider-deepseek" });

			expect(store.writerConfig).toEqual({
				apiKey: "sk-deepseek-key",
				baseUrl: "https://api.deepseek.com",
				modelId: "deepseek-chat",
				provider: "DeepSeek",
			});
		});

		it("未分配供应商时 config 应返回空值对象", () => {
			// 不设置 agentAssignment，所有 config 应为空
			expect(store.coordinatorConfig).toEqual({
				apiKey: "",
				baseUrl: "",
				modelId: "",
				provider: "",
			});
		});

		it("分配的供应商 ID 不存在时 config 应返回空值对象", () => {
			store.setAgentAssignment({ coordinator: "non-existent-id" });

			expect(store.coordinatorConfig).toEqual({
				apiKey: "",
				baseUrl: "",
				modelId: "",
				provider: "",
			});
		});

		it("供应商更新后 config 计算属性应自动更新", () => {
			store.setAgentAssignment({ coordinator: "provider-deepseek" });
			expect(store.coordinatorConfig.modelId).toBe("deepseek-chat");

			store.updateProvider({
				...testProvider,
				modelId: "deepseek-coder",
			});

			expect(store.coordinatorConfig.modelId).toBe("deepseek-coder");
		});
	});

	// ========================================================
	// getAllAgentConfigs
	// ========================================================
	describe("getAllAgentConfigs", () => {
		it("应返回所有 Agent 的配置映射", () => {
			const provider = createMockProvider({ id: "p1", name: "TestProvider" });
			store.addProvider(provider);
			store.setAgentAssignment({
				coordinator: "p1",
				modeler: "p1",
				coder: "p1",
				writer: "p1",
			});

			const configs = store.getAllAgentConfigs();

			expect(configs[AgentType.COORDINATOR].provider).toBe("TestProvider");
			expect(configs[AgentType.MODELER].provider).toBe("TestProvider");
			expect(configs[AgentType.CODER].provider).toBe("TestProvider");
			expect(configs[AgentType.WRITER].provider).toBe("TestProvider");
		});

		it("未分配时应返回空值配置", () => {
			const configs = store.getAllAgentConfigs();

			expect(configs[AgentType.COORDINATOR].apiKey).toBe("");
			expect(configs[AgentType.MODELER].apiKey).toBe("");
			expect(configs[AgentType.CODER].apiKey).toBe("");
			expect(configs[AgentType.WRITER].apiKey).toBe("");
		});
	});

	// ========================================================
	// OpenAlex Email
	// ========================================================
	describe("OpenAlex Email", () => {
		it("setOpenalexEmail 应正确设置邮箱", () => {
			store.setOpenalexEmail("researcher@university.edu");
			expect(store.openalexEmail).toBe("researcher@university.edu");
		});

		it("setOpenalexEmail 应支持清空", () => {
			store.setOpenalexEmail("test@test.com");
			store.setOpenalexEmail("");
			expect(store.openalexEmail).toBe("");
		});
	});

	// ========================================================
	// resetAll
	// ========================================================
	describe("resetAll", () => {
		it("应清除所有供应商、分配和邮箱", () => {
			// 先填充一些数据
			store.addProvider(createMockProvider({ id: "p1" }));
			store.addProvider(createMockProvider({ id: "p2" }));
			store.setAgentAssignment({
				coordinator: "p1",
				modeler: "p2",
				coder: "p1",
				writer: "p2",
			});
			store.setOpenalexEmail("test@test.com");

			store.resetAll();

			expect(store.providers).toEqual([]);
			expect(store.agentAssignment).toEqual({
				coordinator: "",
				modeler: "",
				coder: "",
				writer: "",
			});
			expect(store.openalexEmail).toBe("");
			expect(store.isEmpty).toBe(true);
		});
	});
});
