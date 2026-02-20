<script setup lang="ts">
import { saveApiConfig } from "@/apis/apiKeyApi";
import { submitModelingTask } from "@/apis/submitModelingApi";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectGroup,
	SelectItem,
	SelectLabel,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/toast";
import { useApiKeyStore } from "@/stores/apiKeys";
import { useTaskStore } from "@/stores/task";
import {
	ArrowRight,
	Check,
	CloudUpload,
	FileUp,
	Loader2,
	Paperclip,
	Settings2,
	Sparkles,
} from "lucide-vue-next";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import type FileConfirmDialog from "./FileConfirmDialog.vue";

const { t } = useI18n();
const taskStore = useTaskStore();
const { toast } = useToast();
const apiKeyStore = useApiKeyStore();
const currentStep = ref(1);
const fileConfirmDialog = ref<InstanceType<typeof FileConfirmDialog> | null>(
	null,
);
const fileUploaded = ref(true);

// 拖拽状态
const isDragging = ref(false);
const isSubmitting = ref(false);

// 表单数据
const uploadedFiles = ref<File[]>([]);
const question = ref("");
const selectedOptions = ref({
	template: "国赛",
	language: "中文",
	format: "Markdown",
	workflowMode: "智能模式",
});

// 参数配置面板
const showSettings = ref(false);

const selectConfig = computed(() => [
	{
		field: "template",
		label: t("chatHome.templateLabel"),
		placeholder: t("chatHome.templatePlaceholder"),
		options: [
			{ value: "国赛", label: t("chatHome.templateNational") },
			{ value: "美赛", label: t("chatHome.templateMCM") },
		],
	},
	{
		field: "language",
		label: t("chatHome.languageLabel"),
		placeholder: t("chatHome.languagePlaceholder"),
		options: [
			{ value: "中文", label: t("chatHome.languageChinese") },
			{ value: "英文", label: t("chatHome.languageEnglish") },
		],
	},
	{
		field: "format",
		label: t("chatHome.formatLabel"),
		placeholder: t("chatHome.formatPlaceholder"),
		options: [
			{ value: "Markdown", label: "Markdown" },
			{ value: "LaTeX", label: "LaTeX", hint: t("chatHome.formatLatexHint") },
		],
	},
	{
		field: "workflowMode",
		label: t("chatHome.workflowLabel"),
		placeholder: t("chatHome.workflowPlaceholder"),
		options: [
			{ value: "智能模式", label: t("chatHome.workflowSmart"), hint: t("chatHome.workflowSmartHint") },
			{ value: "标准", label: t("chatHome.workflowStandard"), hint: t("chatHome.workflowStandardHint") },
			{ value: "获奖", label: t("chatHome.workflowEnhanced"), hint: t("chatHome.workflowEnhancedHint") },
		],
	},
]);

// 添加状态控制
const showUploadSuccess = ref(false);
const taskId = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

const nextStep = () => {
	if (currentStep.value < 2) currentStep.value++;
};

const prevStep = () => {
	if (currentStep.value > 1) currentStep.value--;
};

// 文件上传处理
const handleFileUpload = (event: Event) => {
	const input = event.target as HTMLInputElement;
	if (input.files && input.files.length > 0) {
		uploadedFiles.value = Array.from(input.files);
		fileUploaded.value = true;
		showUploadSuccess.value = true;
		toast({
			title: t("chatHome.fileAdded"),
			description: t("chatHome.fileAddedDesc", { count: uploadedFiles.value.length }),
		});
		setTimeout(() => {
			showUploadSuccess.value = false;
		}, 1000);
	}
};

// 拖拽上传处理
const handleDrop = (event: DragEvent) => {
	isDragging.value = false;
	const files = event.dataTransfer?.files;
	if (files && files.length > 0) {
		uploadedFiles.value = Array.from(files);
		fileUploaded.value = true;
		showUploadSuccess.value = true;
		toast({
			title: t("chatHome.fileAdded"),
			description: t("chatHome.fileAddedDesc", { count: uploadedFiles.value.length }),
		});
		setTimeout(() => {
			showUploadSuccess.value = false;
		}, 1000);
	}
};

const router = useRouter();

const canSubmit = computed(() => {
	return question.value.trim().length > 0 && !isSubmitting.value;
});

const handleSubmit = async () => {
	try {
		if (apiKeyStore.isEmpty) {
			toast({
				title: t("chatHome.configureApiKey"),
				description: t("chatHome.configureApiKeyDesc"),
				variant: "destructive",
			});
			return;
		}

		isSubmitting.value = true;

		// 保存 API Key
		await saveApiConfig(apiKeyStore.getSavePayload());

		if (uploadedFiles.value.length === 0) {
			if (!fileConfirmDialog.value) return;

			const shouldContinue = await fileConfirmDialog.value.openConfirmDialog();

			if (!shouldContinue) {
				isSubmitting.value = false;
				return;
			}
		}

		// 映射前端中文选项到后端枚举值
		const templateMap: Record<string, string> = {
			"国赛": "CHINA",
			"美赛": "AMERICAN",
		};
		const workflowMap: Record<string, string> = {
			"智能模式": "auto",
			"标准": "standard",
			"增强": "enhanced",
			"获奖": "award",
		};

		const response = await submitModelingTask(
			{
				ques_all: question.value,
				comp_template: templateMap[selectedOptions.value.template] || "CHINA",
				format_output: selectedOptions.value.format,
				workflow_mode: workflowMap[selectedOptions.value.workflowMode] || "auto",
			},
			uploadedFiles.value,
		);

		taskId.value = response?.data?.task_id ?? null;
		taskStore.addUserMessage(question.value);

		router.push(`/task/${taskId.value}`);
		toast({
			title: t("chatHome.taskSubmitted"),
			description: t("chatHome.taskId", { id: taskId.value }),
		});
	} catch (error) {
		if (import.meta.env.DEV) {
			console.error("任务提交失败:", error);
		}
		toast({
			title: t("chatHome.taskSubmitFailed"),
			description: t("chatHome.taskSubmitFailedDesc"),
			variant: "destructive",
		});
	} finally {
		isSubmitting.value = false;
	}
};
</script>

<template>
  <div class="w-full max-w-2xl mx-auto relative">
    <!-- 统一的卡片容器 -->
    <div class="rounded-2xl border border-white/20 bg-background/60 backdrop-blur-xl shadow-2xl overflow-hidden transition-all duration-500 hover:shadow-primary/5">

      <!-- Step 1: 文件上传 -->
      <div v-if="currentStep === 1" class="p-2">
        <div
          :class="[
            'relative rounded-xl border-2 border-dashed transition-all duration-300 cursor-pointer group',
            isDragging
              ? 'border-primary bg-primary/5 scale-[0.99]'
              : 'border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/30'
          ]"
          @click="() => fileInput?.click()"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <input
            type="file"
            ref="fileInput"
            class="hidden"
            @change="handleFileUpload"
            accept=".txt,.csv,.xlsx"
            multiple
          >

          <div class="flex flex-col items-center justify-center py-14 px-6">
            <!-- 上传图标 -->
            <div :class="[
              'w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-all duration-300 shadow-sm',
              isDragging
                ? 'bg-primary text-white scale-110 rotate-3'
                : uploadedFiles.length > 0
                  ? 'bg-emerald-500 text-white shadow-emerald-500/20'
                  : 'bg-white shadow-sm text-muted-foreground group-hover:scale-105 group-hover:text-primary'
            ]">
              <Check v-if="uploadedFiles.length > 0" class="w-7 h-7" />
              <CloudUpload v-else-if="isDragging" class="w-7 h-7" />
              <FileUp v-else class="w-7 h-7" />
            </div>

            <!-- 文字提示 -->
            <template v-if="uploadedFiles.length > 0">
              <p class="text-[15px] font-semibold text-foreground mb-2">
                {{ t('chatHome.fileAdded') }}
              </p>
              <div class="flex flex-wrap justify-center gap-2 mt-1">
                <span
                  v-for="(file, index) in uploadedFiles"
                  :key="index"
                  class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-border/50 shadow-sm text-[12px] text-foreground/80"
                >
                  <Paperclip class="w-3 h-3 text-muted-foreground" />
                  {{ file.name }}
                </span>
              </div>
            </template>
            <template v-else>
              <p class="text-[15px] font-medium text-foreground mb-1 group-hover:text-primary transition-colors">
                {{ isDragging ? t('chatHome.dropFiles') : t('chatHome.dropFiles') }}
              </p>
              <p class="text-[13px] text-muted-foreground/60">
                {{ t('chatHome.dropFilesHint') }}
              </p>
            </template>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="flex items-center justify-end px-2 py-2">
          <Button
            size="sm"
            class="h-9 px-5 rounded-full text-[13px] font-medium gap-1.5 shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all"
            :disabled="!fileUploaded"
            @click="nextStep"
          >
            <span>{{ t('chatHome.continueSubmit') }}</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      <!-- Step 2: 题目输入 -->
      <div v-if="currentStep === 2" class="p-2">
        <!-- 文本输入区域 -->
        <div class="relative bg-white/40 dark:bg-black/20 rounded-xl">
          <Textarea
            v-model="question"
            :placeholder="t('chatHome.textareaPlaceholder')"
            class="min-h-[180px] resize-none border-0 bg-transparent text-[15px] leading-relaxed placeholder:text-muted-foreground/40 focus-visible:ring-0 px-5 pt-5 pb-16"
            @keydown.ctrl.enter="canSubmit && handleSubmit()"
          />

          <!-- 底部工具栏（内嵌在输入区域底部） -->
          <div class="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 py-3 border-t border-black/5 dark:border-white/5">
            <div class="flex items-center gap-1.5">
              <!-- 上传文件按钮 -->
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="sm"
                      class="h-8 w-8 p-0 rounded-full text-muted-foreground/60 hover:text-foreground hover:bg-black/5 transition-all"
                      @click="prevStep"
                    >
                      <Paperclip class="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="top" class="text-[12px]">
                    {{ t('chatHome.uploadTooltip') }}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <!-- 参数设置按钮 -->
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="sm"
                      :class="[
                        'h-8 w-8 p-0 rounded-full transition-all',
                        showSettings ? 'text-primary bg-primary/10' : 'text-muted-foreground/60 hover:text-foreground hover:bg-black/5'
                      ]"
                      @click="showSettings = !showSettings"
                    >
                      <Settings2 class="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="top" class="text-[12px]">
                    {{ t('chatHome.settingsTooltip') }}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <!-- 已上传文件指示 -->
              <div
                v-if="uploadedFiles.length > 0"
                class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-border/50 shadow-sm text-[11px] text-muted-foreground ml-1"
              >
                <Paperclip class="w-3 h-3" />
                <span>{{ uploadedFiles.length }}</span>
              </div>
            </div>

            <!-- 提交按钮 -->
            <Button
              size="sm"
              class="h-9 px-5 rounded-full text-[13px] font-medium gap-1.5 shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all hover:scale-105 active:scale-95"
              :disabled="!canSubmit"
              @click="handleSubmit"
            >
              <Loader2 v-if="isSubmitting" class="w-3.5 h-3.5 animate-spin" />
              <Sparkles v-else class="w-3.5 h-3.5" />
              {{ isSubmitting ? t('chatHome.submitting') : t('chatHome.startAnalysis') }}
            </Button>
          </div>
        </div>

        <!-- 参数设置面板（可折叠） -->
        <Transition
          enter-active-class="transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1)"
          enter-from-class="opacity-0 -translate-y-2 max-h-0"
          enter-to-class="opacity-100 translate-y-0 max-h-40"
          leave-active-class="transition-all duration-200 cubic-bezier(0.16, 1, 0.3, 1)"
          leave-from-class="opacity-100 translate-y-0 max-h-40"
          leave-to-class="opacity-0 -translate-y-2 max-h-0"
        >
          <div v-if="showSettings" class="mt-2 px-1 pb-1 overflow-hidden">
             <div class="bg-muted/30 rounded-xl p-3 border border-border/40">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div v-for="item in selectConfig" :key="item.field">
                    <Select
                      v-model="selectedOptions[item.field as keyof typeof selectedOptions]"
                      :default-value="item.options[0].value"
                    >
                      <SelectTrigger class="h-8 rounded-lg border-transparent bg-white shadow-sm text-[12px] hover:border-primary/20 focus:ring-0 transition-all">
                        <SelectValue :placeholder="item.placeholder" />
                      </SelectTrigger>
                      <SelectContent class="rounded-xl border border-black/5 shadow-xl">
                        <SelectGroup>
                          <SelectLabel class="text-[10px] uppercase tracking-wider text-muted-foreground/50 px-2 py-1.5">{{ item.label }}</SelectLabel>
                          <SelectItem
                            v-for="option in item.options"
                            :key="option.value"
                            :value="option.value"
                            class="rounded-lg text-[12px] cursor-pointer"
                          >
                            <span>{{ option.label }}</span>
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
             </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- 步骤指示器（卡片下方） -->
    <div class="flex items-center justify-center gap-2.5 mt-6">
      <button
        :class="[
          'h-1.5 rounded-full transition-all duration-300',
          currentStep === 1 ? 'w-6 bg-primary shadow-sm' : 'w-1.5 bg-muted-foreground/20 hover:bg-muted-foreground/40'
        ]"
        @click="currentStep = 1"
      />
      <button
        :class="[
          'h-1.5 rounded-full transition-all duration-300',
          currentStep === 2 ? 'w-6 bg-primary shadow-sm' : 'w-1.5 bg-muted-foreground/20 hover:bg-muted-foreground/40'
        ]"
        @click="currentStep = 2"
      />
    </div>
  </div>
  <FileConfirmDialog ref="fileConfirmDialog" />
</template>
