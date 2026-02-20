<script setup lang="ts">
import type { AgentAssignment, ProviderConfig } from "@/stores/apiKeys";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Brain, Code, FileText, Users } from "lucide-vue-next";
import type { Component } from "vue";

const { t } = useI18n();

const props = defineProps<{
	providers: ProviderConfig[];
	assignment: AgentAssignment;
}>();

const emit = defineEmits<{
	(e: "assign", agentKey: string, providerId: string): void;
}>();

interface AgentInfo {
	key: keyof AgentAssignment;
	label: string;
	description: string;
	icon: Component;
	color: string;
}

const agents = computed<AgentInfo[]>(() => [
	{
		key: "coordinator",
		label: t("agent.coordinator"),
		description: t("agent.coordinatorDesc"),
		icon: Users,
		color: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
	},
	{
		key: "modeler",
		label: t("agent.modeler"),
		description: t("agent.modelerDesc"),
		icon: Brain,
		color: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
	},
	{
		key: "coder",
		label: t("agent.coder"),
		description: t("agent.coderDesc"),
		icon: Code,
		color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
	},
	{
		key: "writer",
		label: t("agent.writer"),
		description: t("agent.writerDesc"),
		icon: FileText,
		color: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
	},
]);

/** 获取供应商状态色点样式 */
function getStatusDot(provider: ProviderConfig): string {
	switch (provider.status) {
		case "valid":
			return "bg-emerald-500";
		case "invalid":
			return "bg-red-400";
		default:
			return "bg-zinc-300 dark:bg-zinc-600";
	}
}

/** 获取当前 Agent 分配的供应商 ID */
function getAssignedId(agentKey: keyof AgentAssignment): string {
	return props.assignment[agentKey] || "";
}

/** 更新分配 */
function handleAssign(agentKey: keyof AgentAssignment, value: string | number | boolean | Record<string, string>) {
	if (typeof value === "string") {
		emit("assign", agentKey, value);
	}
}
</script>

<template>
  <section>
    <div class="mb-4">
      <h3 class="text-[15px] font-semibold tracking-tight">{{ t('agent.assignTitle') }}</h3>
      <p class="text-xs text-muted-foreground/70 mt-0.5">{{ t('agent.assignDesc') }}</p>
    </div>

    <div class="space-y-2">
      <div
        v-for="agent in agents"
        :key="agent.key"
        class="flex items-center gap-3 p-3 rounded-xl border border-border/40 bg-card/30 hover:bg-accent/20 transition-colors duration-150"
      >
        <!-- Agent 图标 -->
        <div
          :class="['flex items-center justify-center w-9 h-9 rounded-lg shrink-0', agent.color]"
        >
          <component :is="agent.icon" class="h-4 w-4" />
        </div>

        <!-- Agent 名称 + 描述 -->
        <div class="min-w-0 flex-1">
          <span class="text-[13px] font-medium">{{ agent.label }}</span>
          <p class="text-[11px] text-muted-foreground/60 leading-tight">{{ agent.description }}</p>
        </div>

        <!-- 供应商下拉 -->
        <Select
          :model-value="getAssignedId(agent.key)"
          @update:model-value="(v: any) => handleAssign(agent.key, v)"
          :disabled="providers.length === 0"
        >
          <SelectTrigger class="h-8 w-[170px] text-xs rounded-lg border-border/50 shrink-0">
            <SelectValue :placeholder="providers.length === 0 ? t('agent.addProviderFirst') : t('agent.selectProvider')" />
          </SelectTrigger>
          <SelectContent class="rounded-xl">
            <SelectItem v-for="p in providers" :key="p.id" :value="p.id" class="rounded-lg">
              <div class="flex items-center gap-2">
                <span :class="['inline-block w-1.5 h-1.5 rounded-full shrink-0', getStatusDot(p)]" />
                <span class="truncate">{{ p.name }}</span>
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  </section>
</template>
