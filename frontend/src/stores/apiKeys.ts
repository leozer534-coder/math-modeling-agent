import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { AgentType } from "@/utils/enum";
import type { ModelConfig } from "@/utils/interface";

/** 供应商配置 */
export interface ProviderConfig {
	id: string;
	name: string;
	apiKey: string;
	baseUrl: string;
	modelId: string;
	apiFormat: "openai" | "anthropic" | "gemini";
	status: "untested" | "valid" | "invalid";
}

/** Agent → Provider 分配映射 */
export interface AgentAssignment {
	coordinator: string; // provider id
	modeler: string;
	coder: string;
	writer: string;
}

type AgentKey = keyof AgentAssignment;

const AGENT_KEYS: readonly AgentKey[] = [
	"coordinator",
	"modeler",
	"coder",
	"writer",
] as const;

/** 旧版 per-agent 配置的 localStorage key（用于迁移检测） */
const LEGACY_STORAGE_KEY = "apiKeys";

export const useApiKeyStore = defineStore(
	"apiKeys",
	() => {
		// ─── 核心状态 ───
		const providers = ref<ProviderConfig[]>([]);
		const agentAssignment = ref<AgentAssignment>({
			coordinator: "",
			modeler: "",
			coder: "",
			writer: "",
		});
		const openalexEmail = ref<string>("");

		// ─── 计算属性 ───
		const isEmpty = computed(() => providers.value.length === 0);

		const hasValidProvider = computed(() =>
			providers.value.some((p) => p.apiKey),
		);

		// ─── Provider CRUD ───

		/** 添加供应商 */
		function addProvider(provider: ProviderConfig): void {
			providers.value.push({ ...provider });
			// 智能默认：如果是第一个供应商，自动分配给所有 Agent
			if (providers.value.length === 1) {
				for (const key of AGENT_KEYS) {
					agentAssignment.value[key] = provider.id;
				}
			}
		}

		/** 更新供应商 */
		function updateProvider(provider: ProviderConfig): void {
			const index = providers.value.findIndex((p) => p.id === provider.id);
			if (index !== -1) {
				providers.value[index] = { ...provider };
			}
		}

		/** 删除供应商 */
		function removeProvider(providerId: string): void {
			providers.value = providers.value.filter((p) => p.id !== providerId);
			// 清理关联的 Agent 分配
			for (const key of AGENT_KEYS) {
				if (agentAssignment.value[key] === providerId) {
					agentAssignment.value[key] = "";
				}
			}
		}

		/** 分配 Agent 到指定供应商 */
		function assignAgent(agentKey: AgentKey, providerId: string): void {
			agentAssignment.value[agentKey] = providerId;
		}

		/** 获取指定 Agent 关联的供应商配置 */
		function getProviderForAgent(
			agentKey: AgentKey,
		): ProviderConfig | undefined {
			const providerId = agentAssignment.value[agentKey];
			return providers.value.find((p) => p.id === providerId);
		}

		/** 获取供应商被哪些 Agent 使用 */
		function getAgentsUsingProvider(providerId: string): AgentKey[] {
			return AGENT_KEYS.filter(
				(key) => agentAssignment.value[key] === providerId,
			);
		}

		// ─── 兼容旧后端接口 ───

		/** 将新数据模型转为旧 SaveApiConfigRequest 格式 */
		function getAllAgentConfigs(): Record<string, ModelConfig> {
			const result: Record<string, ModelConfig> = {};
			const agentTypeMap: Record<AgentKey, string> = {
				coordinator: AgentType.COORDINATOR,
				modeler: AgentType.MODELER,
				coder: AgentType.CODER,
				writer: AgentType.WRITER,
			};

			for (const key of AGENT_KEYS) {
				const provider = getProviderForAgent(key);
				result[agentTypeMap[key]] = {
					apiKey: provider?.apiKey ?? "",
					baseUrl: provider?.baseUrl ?? "",
					modelId: provider?.modelId
						? `${provider.apiFormat === "openai" ? "openai" : provider.apiFormat}/${provider.modelId}`
						: "",
					provider: provider?.name ?? "",
				};
			}
			return result;
		}

		/** 获取适用于后端 save-api-config 接口的负载 */
		function getSavePayload() {
			const buildConfig = (key: AgentKey) => {
				const provider = getProviderForAgent(key);
				return {
					apiKey: provider?.apiKey ?? "",
					baseUrl: provider?.baseUrl ?? "",
					modelId: provider?.modelId
						? `${provider.apiFormat === "openai" ? "openai" : provider.apiFormat}/${provider.modelId}`
						: "",
					provider: provider?.name ?? "",
				};
			};
			return {
				coordinator: buildConfig("coordinator"),
				modeler: buildConfig("modeler"),
				coder: buildConfig("coder"),
				writer: buildConfig("writer"),
				openalex_email: openalexEmail.value,
			};
		}

		// ─── 迁移 ───

		/** 从旧版 per-agent 格式迁移到新的 provider 池 + 分配模式 */
		function migrateFromLegacy(): void {
			// 如果已有新格式数据，跳过迁移
			if (providers.value.length > 0) return;

			try {
				const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
				if (!raw) return;

				const parsed = JSON.parse(raw);
				// 检测是否是旧格式（包含 coordinatorConfig 等字段）
				if (!parsed.coordinatorConfig) return;

				const legacyConfigs: Record<AgentKey, ModelConfig> = {
					coordinator: parsed.coordinatorConfig ?? {
						apiKey: "",
						baseUrl: "",
						modelId: "",
						provider: "",
					},
					modeler: parsed.modelerConfig ?? {
						apiKey: "",
						baseUrl: "",
						modelId: "",
						provider: "",
					},
					coder: parsed.coderConfig ?? {
						apiKey: "",
						baseUrl: "",
						modelId: "",
						provider: "",
					},
					writer: parsed.writerConfig ?? {
						apiKey: "",
						baseUrl: "",
						modelId: "",
						provider: "",
					},
				};

				// 按 provider+baseUrl+modelId 去重合并
				const seen = new Map<string, ProviderConfig>();
				const agentMap: AgentAssignment = {
					coordinator: "",
					modeler: "",
					coder: "",
					writer: "",
				};

				for (const key of AGENT_KEYS) {
					const cfg = legacyConfigs[key];
					if (!cfg.provider && !cfg.baseUrl) continue;

					const dedupeKey = `${cfg.provider}|${cfg.baseUrl}|${cfg.modelId}`;
					if (!seen.has(dedupeKey)) {
						const newProvider: ProviderConfig = {
							id: `provider_migrated_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
							name: cfg.provider || "未命名供应商",
							apiKey: "", // 安全：旧版也不持久化 apiKey
							baseUrl: cfg.baseUrl,
							modelId: cfg.modelId,
							apiFormat: "openai",
							status: "untested",
						};
						seen.set(dedupeKey, newProvider);
					}
					const matched = seen.get(dedupeKey);
					if (matched) {
						agentMap[key] = matched.id;
					}
				}

				if (seen.size > 0) {
					providers.value = Array.from(seen.values());
					agentAssignment.value = agentMap;
					openalexEmail.value = parsed.openalexEmail ?? "";
				}
			} catch {
				// 迁移失败不阻塞应用启动
			}
		}

		// ─── 其他 ───

		function setOpenalexEmail(email: string): void {
			openalexEmail.value = email;
		}

		function resetAll(): void {
			providers.value = [];
			agentAssignment.value = {
				coordinator: "",
				modeler: "",
				coder: "",
				writer: "",
			};
			openalexEmail.value = "";
		}

		return {
			// 状态
			providers,
			agentAssignment,
			openalexEmail,
			isEmpty,
			hasValidProvider,

			// Provider CRUD
			addProvider,
			updateProvider,
			removeProvider,

			// Agent 分配
			assignAgent,
			getProviderForAgent,
			getAgentsUsingProvider,

			// 兼容
			getAllAgentConfigs,
			getSavePayload,

			// 迁移
			migrateFromLegacy,

			// 其他
			setOpenalexEmail,
			resetAll,
		};
	},
	{
		// 安全考虑: 仅持久化非敏感字段
		// apiKey 不持久化，页面刷新后需重新输入或由后端托管
		persist: {
			pick: [
				"providers",
				"agentAssignment",
				"openalexEmail",
			],
			serializer: {
				serialize: (state) => {
					// 持久化时排除 apiKey
					const clone = JSON.parse(JSON.stringify(state));
					if (clone.providers) {
						for (const p of clone.providers) {
							delete p.apiKey;
						}
					}
					return JSON.stringify(clone);
				},
				deserialize: (raw) => {
					const state = JSON.parse(raw);
					// 反序列化时补充 apiKey 默认值
					if (state.providers) {
						for (const p of state.providers) {
							if (!p.apiKey) p.apiKey = "";
						}
					}
					return state;
				},
			},
		},
	},
);
