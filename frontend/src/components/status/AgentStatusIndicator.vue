<script setup lang="ts">
import { Brain, Code2, Pen } from "lucide-vue-next";

interface AgentStatus {
	name: string;
	status: "idle" | "running" | "done" | "error";
}

const props = withDefaults(
	defineProps<{
		agents?: AgentStatus[];
	}>(),
	{
		agents: () => [
			{ name: "Modeler", status: "idle" },
			{ name: "Coder", status: "idle" },
			{ name: "Writer", status: "idle" },
		],
	},
);

const getIcon = (name: string) => {
	switch (name) {
		case "Modeler":
			return Brain;
		case "Coder":
			return Code2;
		case "Writer":
			return Pen;
		default:
			return Brain;
	}
};

const getColorClass = (name: string) => {
	switch (name) {
		case "Modeler":
			return "text-agent-modeler";
		case "Coder":
			return "text-agent-coder";
		case "Writer":
			return "text-agent-writer";
		default:
			return "text-primary";
	}
};

const getDotColorClass = (name: string) => {
	switch (name) {
		case "Modeler":
			return "bg-agent-modeler";
		case "Coder":
			return "bg-agent-coder";
		case "Writer":
			return "bg-agent-writer";
		default:
			return "bg-primary";
	}
};

const getStatusLabel = (status: string) => {
	switch (status) {
		case "idle":
			return "等待中";
		case "running":
			return "运行中";
		case "done":
			return "已完成";
		case "error":
			return "错误";
		default:
			return "未知";
	}
};
</script>

<template>
  <div class="flex items-center gap-4">
    <div
      v-for="agent in props.agents"
      :key="agent.name"
      class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card border border-border"
    >
      <component :is="getIcon(agent.name)" class="w-4 h-4" :class="getColorClass(agent.name)" />
      <span class="text-xs font-medium text-foreground">{{ agent.name }}</span>
      <div class="flex items-center gap-1">
        <div
          class="w-2 h-2 rounded-full"
          :class="[
            getDotColorClass(agent.name),
            agent.status === 'running' ? 'animate-pulse' : '',
            agent.status === 'error' ? 'bg-destructive' : '',
            agent.status === 'idle' ? 'opacity-40' : ''
          ]"
        />
        <span class="text-xs text-muted-foreground">{{ getStatusLabel(agent.status) }}</span>
      </div>
    </div>
  </div>
</template>
