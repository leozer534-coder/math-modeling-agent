<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useApiKeyStore } from "@/stores/apiKeys";
import type { ProviderConfig } from "@/stores/apiKeys";
import { saveApiConfig } from "@/apis/apiKeyApi";
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import ProviderSection from "./ProviderSection.vue";
import AgentAssignmentSection from "./AgentAssignmentSection.vue";
import OtherSettingsSection from "./OtherSettingsSection.vue";
import ProviderEditDialog from "./ProviderEditDialog.vue";
import { RotateCcw } from "lucide-vue-next";

const { t } = useI18n();
const store = useApiKeyStore();

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{
	(e: "update:open", value: boolean): void;
}>();

// ProviderEditDialog 状态
const isEditDialogOpen = ref(false);
const editingProvider = ref<ProviderConfig | null>(null);
const saving = ref(false);

// 打开时执行迁移检查
watch(
	() => props.open,
	(open) => {
		if (open) {
			store.migrateFromLegacy();
		}
	},
);

// ─── 供应商操作 ───

function handleAddProvider() {
	editingProvider.value = null;
	isEditDialogOpen.value = true;
}

function handleEditProvider(provider: ProviderConfig) {
	editingProvider.value = provider;
	isEditDialogOpen.value = true;
}

function handleDeleteProvider(providerId: string) {
	store.removeProvider(providerId);
}

function handleSaveProvider(provider: ProviderConfig) {
	if (provider.id && store.providers.find((p) => p.id === provider.id)) {
		store.updateProvider(provider);
	} else {
		store.addProvider(provider);
	}
}

// ─── 保存与关闭 ───

async function handleSave() {
	saving.value = true;
	try {
		const payload = store.getSavePayload();
		await saveApiConfig(payload);
	} catch {
		// 后端保存失败不阻塞前端持久化
	} finally {
		saving.value = false;
		emit("update:open", false);
	}
}

function handleReset() {
	store.resetAll();
}

function handleCancel() {
	emit("update:open", false);
}
</script>

<template>
  <Sheet :open="props.open" @update:open="emit('update:open', $event)">
    <SheetContent
      side="right"
      class="w-[520px] sm:max-w-[520px] flex flex-col p-0 border-l border-border/40 bg-background/95 backdrop-blur-xl"
    >
      <!-- 头部 -->
      <SheetHeader class="px-8 pt-8 pb-1">
        <SheetTitle class="text-xl font-semibold tracking-tight">
          {{ t('apiDialog.title') }}
        </SheetTitle>
        <SheetDescription class="text-[13px] text-muted-foreground/80 leading-relaxed">
          {{ t('apiDialog.description') }}
        </SheetDescription>
      </SheetHeader>

      <!-- 主体 -->
      <ScrollArea class="flex-1">
        <div class="px-8 py-6 space-y-8">
          <!-- 供应商管理 -->
          <ProviderSection
            :providers="store.providers"
            :agent-assignment="store.agentAssignment"
            @add="handleAddProvider"
            @edit="handleEditProvider"
            @delete="handleDeleteProvider"
          />

          <!-- Agent 分配 -->
          <AgentAssignmentSection
            :providers="store.providers"
            :assignment="store.agentAssignment"
            @assign="(agentKey: any, providerId: any) => store.assignAgent(agentKey, providerId)"
          />

          <!-- 其他设置 -->
          <OtherSettingsSection
            :email="store.openalexEmail"
            @update:email="store.setOpenalexEmail($event)"
          />
        </div>
      </ScrollArea>

      <!-- 底部操作栏 -->
      <div class="px-8 py-5 border-t border-border/40 bg-muted/30">
        <div class="flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            class="text-muted-foreground hover:text-foreground h-9 px-3 text-[13px] gap-1.5"
            @click="handleReset"
          >
            <RotateCcw class="h-3.5 w-3.5" />
            {{ t('common.reset') }}
          </Button>
          <div class="flex gap-2.5">
            <Button
              variant="outline"
              size="sm"
              class="h-9 px-5 text-[13px] rounded-lg"
              @click="handleCancel"
            >
              {{ t('common.cancel') }}
            </Button>
            <Button
              size="sm"
              class="h-9 px-5 text-[13px] rounded-lg shadow-sm"
              @click="handleSave"
              :disabled="saving"
            >
              {{ saving ? t('apiDialog.saving') : t('apiDialog.saveConfig') }}
            </Button>
          </div>
        </div>
      </div>
    </SheetContent>
  </Sheet>

  <!-- 供应商编辑对话框 -->
  <ProviderEditDialog
    :open="isEditDialogOpen"
    :provider="editingProvider"
    @update:open="isEditDialogOpen = $event"
    @save="handleSaveProvider"
  />
</template>
