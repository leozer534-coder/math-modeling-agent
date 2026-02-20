<script setup lang="ts">
import { validateApiKey } from "@/apis/apiKeyApi";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
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

// 重置表单（必须在 watch 之前定义，因为 watch 使用了 immediate: true）
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
	} catch (error) {
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
    <DialogContent class="max-w-md">
      <DialogHeader>
        <DialogTitle>{{ dialogTitle }}</DialogTitle>
      </DialogHeader>

      <div class="space-y-4 py-4">
        <!-- 模板选择 -->
        <div class="space-y-2" v-if="!isEditMode">
          <Label class="text-sm font-medium">{{ t('providerEdit.presetTemplate') }}</Label>
          <Select :model-value="selectedTemplate" @update:model-value="onTemplateChange">
            <SelectTrigger class="h-9">
              <SelectValue :placeholder="t('providerEdit.templatePlaceholder')" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>{{ t('providerEdit.commonProviders') }}</SelectLabel>
                <SelectItem v-for="(_, name) in templates" :key="name" :value="name">
                  {{ name }}
                </SelectItem>
                <SelectItem :value="customTemplateKey">
                  {{ customTemplateKey }}
                </SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>

        <!-- 供应商名称 -->
        <div class="space-y-2">
          <Label for="provider-name" class="text-sm font-medium">{{ t('providerEdit.providerName') }}</Label>
          <Input
            id="provider-name"
            v-model="form.name"
            :placeholder="t('providerEdit.providerNamePlaceholder')"
            class="h-9"
          />
        </div>

        <!-- API Key -->
        <div class="space-y-2">
          <Label for="api-key" class="text-sm font-medium">{{ t('providerEdit.apiKeyLabel') }}</Label>
          <div class="relative">
            <Input
              id="api-key"
              v-model="form.apiKey"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="t('providerEdit.apiKeyPlaceholder')"
              class="h-9 pr-10"
            />
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              @click="showPassword = !showPassword"
            >
              <svg v-if="showPassword" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Base URL -->
        <div class="space-y-2">
          <Label for="base-url" class="text-sm font-medium">{{ t('providerEdit.baseUrlLabel') }}</Label>
          <Input
            id="base-url"
            v-model="form.baseUrl"
            placeholder="https://api.example.com"
            class="h-9"
          />
        </div>

        <!-- Model ID -->
        <div class="space-y-2">
          <Label for="model-id" class="text-sm font-medium">{{ t('providerEdit.modelIdLabel') }}</Label>
          <Input
            id="model-id"
            v-model="form.modelId"
            :placeholder="t('providerEdit.modelIdPlaceholder')"
            class="h-9"
          />
        </div>

        <!-- API 协议 -->
        <div class="space-y-2">
          <Label class="text-sm font-medium">{{ t('providerEdit.apiProtocol') }}</Label>
          <Select v-model="form.apiFormat">
            <SelectTrigger class="h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="format in apiFormats" :key="format.value" :value="format.value">
                {{ format.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p class="text-xs text-muted-foreground">
            {{ t('providerEdit.endpoint') }}: {{ apiFormats.find(f => f.value === form.apiFormat)?.endpoint }}
          </p>
        </div>

        <!-- 测试结果 -->
        <div v-if="testResult" :class="[
          'text-sm px-3 py-2 rounded border',
          testResult.valid ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
        ]">
          {{ testResult.message }}
        </div>
      </div>

      <DialogFooter class="flex gap-2">
        <Button variant="outline" @click="testConnection" :disabled="testing || !form.apiKey || !form.modelId">
          <span v-if="testing" class="flex items-center gap-1">
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            {{ t('providerEdit.testing') }}
          </span>
          <span v-else>{{ t('providerEdit.testConnection') }}</span>
        </Button>
        <Button variant="outline" @click="handleClose">{{ t('common.cancel') }}</Button>
        <Button @click="handleSave" :disabled="!isFormValid">{{ t('common.save') }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
