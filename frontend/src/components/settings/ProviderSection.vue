<script setup lang="ts">
import type { AgentAssignment, ProviderConfig } from "@/stores/apiKeys";
import { useApiKeyStore } from "@/stores/apiKeys";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Plus, Server } from "lucide-vue-next";
import ProviderCard from "./ProviderCard.vue";

const { t } = useI18n();
const store = useApiKeyStore();

defineProps<{
	providers: ProviderConfig[];
	agentAssignment: AgentAssignment;
}>();

const emit = defineEmits<{
	(e: "add"): void;
	(e: "edit", provider: ProviderConfig): void;
	(e: "delete", providerId: string): void;
}>();

// 删除确认对话框状态
const deleteConfirmOpen = ref(false);
const pendingDeleteId = ref("");

const affectedAgents = computed(() => {
	if (!pendingDeleteId.value) return [];
	return store.getAgentsUsingProvider(pendingDeleteId.value);
});

/** Agent key 的显示名 */
function getAgentLabel(key: string): string {
	const map: Record<string, string> = {
		coordinator: t("agent.coordinator"),
		modeler: t("agent.modeler"),
		coder: t("agent.coder"),
		writer: t("agent.writer"),
	};
	return map[key] ?? key;
}

function requestDelete(providerId: string) {
	const agents = store.getAgentsUsingProvider(providerId);
	if (agents.length > 0) {
		pendingDeleteId.value = providerId;
		deleteConfirmOpen.value = true;
	} else {
		emit("delete", providerId);
	}
}

function confirmDelete() {
	emit("delete", pendingDeleteId.value);
	deleteConfirmOpen.value = false;
	pendingDeleteId.value = "";
}
</script>

<template>
  <section>
    <!-- 区块标题 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-[15px] font-semibold tracking-tight">{{ t('provider.config') }}</h3>
        <p class="text-xs text-muted-foreground/70 mt-0.5">API · LLM · {{ t('provider.headerStatus') }}</p>
      </div>
      <Button
        variant="outline"
        size="sm"
        class="h-8 px-3.5 text-xs rounded-lg gap-1.5 border-dashed hover:border-solid transition-all"
        @click="emit('add')"
      >
        <Plus class="h-3.5 w-3.5" />
        {{ t('provider.addProvider') }}
      </Button>
    </div>

    <!-- 供应商列表 -->
    <div v-if="providers.length > 0" class="space-y-2.5">
      <ProviderCard
        v-for="provider in providers"
        :key="provider.id"
        :provider="provider"
        @edit="emit('edit', $event)"
        @delete="requestDelete"
      />
    </div>

    <!-- 空状态 -->
    <div
      v-else
      class="flex flex-col items-center justify-center py-12 rounded-2xl border border-dashed border-border/60 bg-muted/20"
    >
      <div class="flex items-center justify-center w-12 h-12 rounded-2xl bg-muted/60 mb-4">
        <Server class="h-5 w-5 text-muted-foreground/50" />
      </div>
      <p class="text-sm font-medium text-muted-foreground/80 mb-1">{{ t('provider.noProviders') }}</p>
      <p class="text-xs text-muted-foreground/50 mb-4">{{ t('apiDialog.description') }}</p>
      <Button
        variant="outline"
        size="sm"
        class="h-8 px-4 text-xs rounded-lg gap-1.5"
        @click="emit('add')"
      >
        <Plus class="h-3.5 w-3.5" />
        {{ t('provider.addFirst') }}
      </Button>
    </div>
  </section>

  <!-- 删除确认对话框 -->
  <Dialog :open="deleteConfirmOpen" @update:open="deleteConfirmOpen = $event">
    <DialogContent class="max-w-sm rounded-2xl">
      <DialogHeader>
        <DialogTitle class="text-base">{{ t('common.confirm') }}</DialogTitle>
        <DialogDescription class="text-[13px] leading-relaxed">
          {{ t('settings.deleteProviderWarning') }}
          <span class="font-medium text-foreground">
            {{ affectedAgents.map(getAgentLabel).join('、') }}
          </span>
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="flex gap-2 pt-2">
        <Button variant="outline" size="sm" class="rounded-lg" @click="deleteConfirmOpen = false">
          {{ t('common.cancel') }}
        </Button>
        <Button variant="destructive" size="sm" class="rounded-lg" @click="confirmDelete">
          {{ t('common.delete') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
