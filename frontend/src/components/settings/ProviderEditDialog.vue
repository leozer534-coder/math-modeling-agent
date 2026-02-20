<script setup lang="ts">
import { validateApiKey } from "@/apis/apiKeyApi";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectGroup,
	SelectItem,
	SelectLabel,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import type { ProviderConfig } from "@/stores/apiKeys";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
	CheckCircle,
	XCircle,
	Eye,
	EyeOff,
	Loader2,
	Zap,
} from "lucide-vue-next";

const { t } = useI18n();

const props = defineProps<{
	open: boolean;
	provider?: ProviderConfig | null;
}>();

const emit = defineEmits<{
	(e: "update:open", value: boolean): void;
	(e: "save", provider: ProviderConfig): void;
}>();

// 预设模板
const templates = {
	DeepSeek: {
		baseUrl: "https://api.deepseek.com",
		modelId: "deepseek-chat",
		apiFormat: "openai" as const,
	},
	SiliconFlow: {
		baseUrl: "https://api.siliconflow.cn",
		modelId: "deepseek-ai/DeepSeek-V3",
		apiFormat: "openai" as const,
	},
	OpenAI: {
		baseUrl: "https://api.openai.com",
		modelId: "gpt-4o",
		apiFormat: "openai" as const,
	},
	Anthropic: {
		baseUrl: "https://api.anthropic.com",
		modelId: "claude-sonnet-4-20250514",
		apiFormat: "anthropic" as const,
	},
	"Google Gemini": {
		baseUrl: "https://generativelanguage.googleapis.com",
		modelId: "gemini-2.0-flash",
		apiFormat: "gemini" as const,
	},
	Groq: {
		baseUrl: "https://api.groq.com/openai",
		modelId: "llama-3.3-70b-versatile",
		apiFormat: "openai" as const,
	},
	Moonshot: {
		baseUrl: "https://api.moonshot.cn",
		modelId: "moonshot-v1-128k",
		apiFormat: "openai" as const,
	},
	"Zhipu AI": {
		baseUrl: "https://open.bigmodel.cn/api/paas",
		modelId: "glm-4-plus",
		apiFormat: "openai" as const,
	},
	"Alibaba Qwen": {
		baseUrl: "https://dashscope.aliyuncs.com/compatible-mode",
		modelId: "qwen-max",
		apiFormat: "openai" as const,
	},
	"302.AI": {
		baseUrl: "https://api.302.ai",
		modelId: "deepseek-chat",
		apiFormat: "openai" as const,
	},
	OpenRouter: {
		baseUrl: "https://openrouter.ai/api",
		modelId: "anthropic/claude-sonnet-4",
		apiFormat: "openai" as const,
	},
};

// 自定义模板 key 使用计算属性以支持国际化
const customTemplateKey = computed(() => t("providerEdit.custom"));

const apiFormats = computed(() => [
	{
		value: "openai",
		label: t("providerEdit.openaiProtocol"),
		endpoint: "/v1/chat/completions",
	},
	{
		value: "anthropic",
		label: t("providerEdit.anthropicProtocol"),
		endpoint: "/v1/messages",
	},
	{
		value: "gemini",
		label: t("providerEdit.geminiProtocol"),
		endpoint: "/v1beta/models/...",
	},
]);

// 表单数据
const form = ref<ProviderConfig>({
	id: "",
	name: "",
	apiKey: "",
	baseUrl: "",
	modelId: "",
	apiFormat: "openai",
	status: "untested",
});

const selectedTemplate = ref("");
const showPassword = ref(false);
const testing = ref(false);
const testResult = ref<{ valid: boolean; message: string } | null>(null);

// 是否编辑模式
const isEditMode = computed(() => !!props.provider?.id);
const dialogTitle = computed(() =>
	isEditMode.value ? t("providerEdit.editTitle") : t("providerEdit.addTitle"),
);

// 重置表单
const resetForm = () => {
	form.value = {
		id: "",
		name: "",
		apiKey: "",
		baseUrl: "",
		modelId: "",
		apiFormat: "openai",
		status: "untested",
	};
	selectedTemplate.value = "";
	testResult.value = null;
};

// 监听 provider 变化，填充表单
watch(
	() => props.provider,
	(newProvider) => {
		if (newProvider) {
			form.value = { ...newProvider };
			selectedTemplate.value = "";
		} else {
			resetForm();
		}
	},
	{ immediate: true },
);

// 监听弹窗关闭
watch(
	() => props.open,
	(open) => {
		if (!open) {
			testResult.value = null;
			showPassword.value = false;
		}
	},
);

// 选择模板时自动填充
const onTemplateChange = (templateName: any) => {
	if (typeof templateName !== "string") return;
	selectedTemplate.value = templateName;

	// 检查是否是自定义模板
	if (templateName === customTemplateKey.value) {
		form.value.name = "";
		form.value.baseUrl = "";
		form.value.modelId = "";
		form.value.apiFormat = "openai";
		testResult.value = null;
		return;
	}

	const template = templates[templateName as keyof typeof templates];
	if (template) {
		form.value.name = templateName;
		form.value.baseUrl = template.baseUrl;
		form.value.modelId = template.modelId;
		form.value.apiFormat = template.apiFormat;
		testResult.value = null;
	}
};

// 测试连接
const testConnection = async () => {
	testing.value = true;
	testResult.value = null;

	try {
		const result = await validateApiKey({
			api_key: form.value.apiKey,
			base_url: form.value.baseUrl || "https://api.openai.com/v1",
			model_id: form.value.modelId,
			api_format: form.value.apiFormat,
		});
		testResult.value = {
			valid: result.data.valid,
			message: result.data.message,
		};
		form.value.status = result.data.valid ? "valid" : "invalid";
	} catch {
		testResult.value = {
			valid: false,
			message: t("providerEdit.connectionFailed"),
		};
		form.value.status = "invalid";
	} finally {
		testing.value = false;
	}
};

// 表单验证
const isFormValid = computed(() => {
	return (
		form.value.name &&
		form.value.apiKey &&
		form.value.baseUrl &&
		form.value.modelId
	);
});

// 保存
const handleSave = () => {
	if (!isFormValid.value) return;

	// 生成 ID
	if (!form.value.id) {
		form.value.id = `provider_${Date.now()}`;
	}

	emit("save", { ...form.value });
	emit("update:open", false);
};

// 关闭
const handleClose = () => {
	emit("update:open", false);
};
</script>

<template>
  <Dialog :open="props.open" @update:open="emit('update:open', $event)">
    <DialogContent class="max-w-[460px] rounded-2xl border-border/40 bg-background/95 backdrop-blur-xl p-0 gap-0">
      <!-- 头部 -->
      <DialogHeader class="px-7 pt-7 pb-1">
        <DialogTitle class="text-lg font-semibold tracking-tight">
          {{ dialogTitle }}
        </DialogTitle>
        <DialogDescription class="text-[13px] text-muted-foreground/70">
          {{ t('providerEdit.dialogDesc') }}
        </DialogDescription>
      </DialogHeader>

      <!-- 表单主体 -->
      <div class="px-7 py-5 space-y-4.5">
        <!-- 模板选择 -->
        <div class="space-y-2" v-if="!isEditMode">
          <Label class="text-[13px] font-medium">{{ t('providerEdit.presetTemplate') }}</Label>
          <Select :model-value="selectedTemplate" @update:model-value="onTemplateChange">
            <SelectTrigger class="h-9 rounded-lg border-border/50 text-[13px]">
              <SelectValue :placeholder="t('providerEdit.templatePlaceholder')" />
            </SelectTrigger>
            <SelectContent class="rounded-xl">
              <SelectGroup>
                <SelectLabel class="text-xs text-muted-foreground/60">{{ t('providerEdit.commonProviders') }}</SelectLabel>
                <SelectItem
                  v-for="(_, name) in templates"
                  :key="name"
                  :value="name"
                  class="rounded-lg text-[13px]"
                >
                  {{ name }}
                </SelectItem>
                <SelectItem :value="customTemplateKey" class="rounded-lg text-[13px]">
                  {{ customTemplateKey }}
                </SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>

        <!-- 供应商名称 -->
        <div class="space-y-2">
          <Label for="provider-name" class="text-[13px] font-medium">{{ t('providerEdit.providerName') }}</Label>
          <Input
            id="provider-name"
            v-model="form.name"
            :placeholder="t('providerEdit.providerNamePlaceholder')"
            class="h-9 rounded-lg text-[13px] border-border/50"
          />
        </div>

        <!-- API Key -->
        <div class="space-y-2">
          <Label for="api-key" class="text-[13px] font-medium">{{ t('providerEdit.apiKeyLabel') }}</Label>
          <div class="relative">
            <Input
              id="api-key"
              v-model="form.apiKey"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="t('providerEdit.apiKeyPlaceholder')"
              class="h-9 pr-10 rounded-lg text-[13px] border-border/50 font-mono"
            />
            <button
              type="button"
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground transition-colors"
              @click="showPassword = !showPassword"
            >
              <EyeOff v-if="showPassword" class="h-3.5 w-3.5" />
              <Eye v-else class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <!-- Base URL -->
        <div class="space-y-2">
          <Label for="base-url" class="text-[13px] font-medium">{{ t('providerEdit.baseUrlLabel') }}</Label>
          <Input
            id="base-url"
            v-model="form.baseUrl"
            placeholder="https://api.example.com"
            class="h-9 rounded-lg text-[13px] border-border/50 font-mono"
          />
        </div>

        <!-- Model ID -->
        <div class="space-y-2">
          <Label for="model-id" class="text-[13px] font-medium">{{ t('providerEdit.modelIdLabel') }}</Label>
          <Input
            id="model-id"
            v-model="form.modelId"
            :placeholder="t('providerEdit.modelIdPlaceholder')"
            class="h-9 rounded-lg text-[13px] border-border/50"
          />
        </div>

        <!-- API 协议 -->
        <div class="space-y-2">
          <Label class="text-[13px] font-medium">{{ t('providerEdit.apiProtocol') }}</Label>
          <Select v-model="form.apiFormat">
            <SelectTrigger class="h-9 rounded-lg border-border/50 text-[13px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent class="rounded-xl">
              <SelectItem
                v-for="format in apiFormats"
                :key="format.value"
                :value="format.value"
                class="rounded-lg text-[13px]"
              >
                {{ format.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p class="text-[11px] text-muted-foreground/50 font-mono">
            {{ t('providerEdit.endpoint') }}: {{ apiFormats.find(f => f.value === form.apiFormat)?.endpoint }}
          </p>
        </div>

        <!-- 测试结果 -->
        <div
          v-if="testResult"
          :class="[
            'flex items-center gap-2 text-[12px] px-3.5 py-2.5 rounded-lg',
            testResult.valid
              ? 'bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
              : 'bg-red-500/5 text-red-600 dark:text-red-400 border border-red-500/20',
          ]"
        >
          <CheckCircle v-if="testResult.valid" class="h-3.5 w-3.5 shrink-0" />
          <XCircle v-else class="h-3.5 w-3.5 shrink-0" />
          <span>{{ testResult.message }}</span>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <DialogFooter class="px-7 py-4 border-t border-border/30 bg-muted/20 rounded-b-2xl">
        <div class="flex items-center justify-between w-full">
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3.5 text-xs rounded-lg gap-1.5"
            :disabled="testing || !form.apiKey || !form.modelId"
            @click="testConnection"
          >
            <Loader2 v-if="testing" class="h-3.5 w-3.5 animate-spin" />
            <Zap v-else class="h-3.5 w-3.5" />
            {{ testing ? t('providerEdit.testing') : t('providerEdit.testConnection') }}
          </Button>
          <div class="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              class="h-8 px-4 text-xs rounded-lg"
              @click="handleClose"
            >
              {{ t('common.cancel') }}
            </Button>
            <Button
              size="sm"
              class="h-8 px-4 text-xs rounded-lg shadow-sm"
              :disabled="!isFormValid"
              @click="handleSave"
            >
              {{ t('common.save') }}
            </Button>
          </div>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
