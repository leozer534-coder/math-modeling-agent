<script setup lang="ts">
import { saveApiConfig } from "@/apis/apiKeyApi";
import { exampleAPI } from "@/apis/commonApi";
import { submitModelingTask } from "@/apis/submitModelingApi";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
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
import { useToast } from "@/components/ui/toast";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { useApiKeyStore } from "@/stores/apiKeys";
import { useTaskStore } from "@/stores/task";
import {
	ArrowRight,
	Brain,
	Code,
	File as FileIcon,
	FileSpreadsheet,
	FileText,
	FileUp,
	PenTool,
	Send,
	Settings2,
	Sigma,
	Sparkles,
	X,
	Zap,
} from "lucide-vue-next";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

const { t } = useI18n();
const taskStore = useTaskStore();
const { toast } = useToast();
const apiKeyStore = useApiKeyStore();
const router = useRouter();

// 表单数据
const uploadedFiles = ref<File[]>([]);
const question = ref("");
const isDragging = ref(false);
const isSubmitting = ref(false);
const showOptions = ref(false);
const showFileConfirm = ref(false);
let fileConfirmResolve: ((value: boolean) => void) | null = null;

const selectedOptions = ref({
	template: "国赛",
	language: "中文",
	format: "Markdown",
	workflowMode: "智能模式",
});

// 参数配置使用计算属性，确保语言切换时实时更新
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
			{
				value: "智能模式",
				label: t("chatHome.workflowSmart"),
				hint: t("chatHome.workflowSmartHint"),
			},
			{
				value: "标准",
				label: t("chatHome.workflowStandard"),
				hint: t("chatHome.workflowStandardHint"),
			},
			{
				value: "增强",
				label: t("chatHome.workflowEnhanced"),
				hint: t("chatHome.workflowEnhancedHint"),
			},
			{
				value: "获奖",
				label: t("chatHome.workflowAward"),
				hint: t("chatHome.workflowAwardHint"),
			},
		],
	},
]);

// 样例数据使用计算属性，确保语言切换时实时更新
const examples = computed(() => [
	{
		id: 1,
		title: t("chatHome.example1Title"),
		source: t("chatHome.example1Source"),
		tags: [t("chatHome.example1Tag1"), t("chatHome.example1Tag2")],
		icon: Brain,
	},
	{
		id: 2,
		title: t("chatHome.example2Title"),
		source: t("chatHome.example2Source"),
		tags: [t("chatHome.example2Tag1"), t("chatHome.example2Tag2")],
		icon: Sparkles,
	},
	{
		id: 3,
		title: t("chatHome.example3Title"),
		source: t("chatHome.example3Source"),
		tags: [t("chatHome.example3Tag1"), t("chatHome.example3Tag2")],
		icon: Code,
	},
]);

// 文件图标映射
const getFileIcon = (filename: string) => {
	const ext = filename.split(".").pop()?.toLowerCase();
	if (ext === "csv" || ext === "xlsx" || ext === "xls") return FileSpreadsheet;
	if (ext === "txt" || ext === "md") return FileText;
	return FileIcon;
};

// 文件大小格式化
const formatFileSize = (bytes: number) => {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// 是否可以提交
const canSubmit = computed(() => question.value.trim().length > 0);

// 文件上传 ref
const fileInput = ref<HTMLInputElement | null>(null);

// 处理文件上传
const handleFileUpload = (event: Event) => {
	const input = event.target as HTMLInputElement;
	if (input.files && input.files.length > 0) {
		const newFiles = Array.from(input.files);
		uploadedFiles.value = [...uploadedFiles.value, ...newFiles];
		toast({
			title: t("chatHome.fileAdded"),
			description: t("chatHome.fileAddedDesc", { count: newFiles.length }),
		});
	}
	// 重置 input 以便重复选择相同文件
	if (input) input.value = "";
};

// 拖拽上传
const handleDrop = (event: DragEvent) => {
	isDragging.value = false;
	const files = event.dataTransfer?.files;
	if (files && files.length > 0) {
		const newFiles = Array.from(files);
		uploadedFiles.value = [...uploadedFiles.value, ...newFiles];
		toast({
			title: t("chatHome.fileAdded"),
			description: t("chatHome.fileAddedDesc", { count: newFiles.length }),
		});
	}
};

// 移除文件
const removeFile = (index: number) => {
	uploadedFiles.value.splice(index, 1);
};

// 打开文件确认弹窗
const openFileConfirm = (): Promise<boolean> => {
	showFileConfirm.value = true;
	return new Promise((resolve) => {
		fileConfirmResolve = resolve;
	});
};

const confirmContinueWithoutFile = () => {
	showFileConfirm.value = false;
	fileConfirmResolve?.(true);
};

const cancelContinueWithoutFile = () => {
	showFileConfirm.value = false;
	fileConfirmResolve?.(false);
};

// 选择样例
const selectExample = async (example: { id: number; source: string }) => {
	try {
		const res = await exampleAPI(example.id.toString(), example.source);
		const task_id = res?.data?.task_id;
		router.push(`/task/${task_id}`);
	} catch (error) {
		toast({
			title: t("chatHome.loadExampleFailed"),
			description: t("chatHome.loadExampleFailedDesc"),
			variant: "destructive",
		});
	}
};

// 提交任务
const handleSubmit = async () => {
	if (!canSubmit.value || isSubmitting.value) return;

	try {
		if (apiKeyStore.isEmpty) {
			toast({
				title: t("chatHome.configureApiKey"),
				description: t("chatHome.configureApiKeyDesc"),
				variant: "destructive",
			});
			return;
		}

		// 保存 API Key
		await saveApiConfig(apiKeyStore.getSavePayload());

		// 未上传文件时确认
		if (uploadedFiles.value.length === 0) {
			const shouldContinue = await openFileConfirm();
			if (!shouldContinue) {
				fileInput.value?.click();
				return;
			}
		}

		isSubmitting.value = true;

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

		const taskId = response?.data?.task_id ?? null;

		if (!taskId) {
			toast({
				title: t("chatHome.taskSubmitFailed"),
				description: t("chatHome.taskSubmitFailedDesc"),
				variant: "destructive",
			});
			return;
		}

		taskStore.addUserMessage(question.value);

		toast({
			title: t("chatHome.taskSubmitted"),
			description: t("chatHome.taskId", { id: taskId }),
		});

		router.push(`/task/${taskId}`);
	} catch (error) {
		if (import.meta.env.DEV) {
			console.error("Task submission failed:", error);
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

// Ctrl+Enter 提交
const handleKeydown = (event: KeyboardEvent) => {
	if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
		event.preventDefault();
		handleSubmit();
	}
};
</script>

<template>
  <div
    class="flex-1 flex flex-col items-center overflow-y-auto"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
  >
    <!-- 拖拽遮罩 -->
    <Transition name="fade">
      <div
        v-if="isDragging"
        class="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center"
      >
        <div class="border-2 border-dashed border-primary rounded-2xl p-16 text-center">
          <FileUp class="w-12 h-12 text-primary mx-auto mb-4" />
          <p class="text-lg font-medium">{{ t('chatHome.dropFiles') }}</p>
          <p class="text-sm text-muted-foreground mt-1">{{ t('chatHome.dropFilesHint') }}</p>
        </div>
      </div>
    </Transition>

    <!-- 主体内容 -->
    <div class="w-full max-w-3xl mx-auto px-4 pt-16 pb-8 flex flex-col flex-1">

      <!-- Logo + 欢迎语 -->
      <div class="text-center mb-12">
        <div class="w-16 h-16 rounded-2xl gradient-bg mx-auto flex items-center justify-center mb-5 shadow-lg shadow-primary/20">
          <Sigma class="w-8 h-8 text-white" />
        </div>
        <h1 class="text-2xl font-semibold mb-2">{{ t('chatHome.welcomeTitle') }}</h1>
        <p class="text-muted-foreground">
          {{ t('chatHome.welcomeDesc') }}
        </p>
      </div>

      <!-- 智能体能力卡片 -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-10">
        <div class="flex flex-col items-center gap-2 p-4 rounded-xl border border-border/60 bg-card hover:shadow-md hover:border-border transition-all">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center agent-avatar-coordinator">
            <Zap class="w-4.5 h-4.5" />
          </div>
          <span class="text-xs font-medium">{{ t('chatHome.agentCoordinator') }}</span>
        </div>
        <div class="flex flex-col items-center gap-2 p-4 rounded-xl border border-border/60 bg-card hover:shadow-md hover:border-border transition-all">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center agent-avatar-modeler">
            <Brain class="w-4.5 h-4.5" />
          </div>
          <span class="text-xs font-medium">{{ t('chatHome.agentModeler') }}</span>
        </div>
        <div class="flex flex-col items-center gap-2 p-4 rounded-xl border border-border/60 bg-card hover:shadow-md hover:border-border transition-all">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center agent-avatar-coder">
            <Code class="w-4.5 h-4.5" />
          </div>
          <span class="text-xs font-medium">{{ t('chatHome.agentCoder') }}</span>
        </div>
        <div class="flex flex-col items-center gap-2 p-4 rounded-xl border border-border/60 bg-card hover:shadow-md hover:border-border transition-all">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center agent-avatar-writer">
            <PenTool class="w-4.5 h-4.5" />
          </div>
          <span class="text-xs font-medium">{{ t('chatHome.agentWriter') }}</span>
        </div>
      </div>

      <!-- 样例卡片 -->
      <div class="mb-8">
        <h3 class="text-sm font-medium text-muted-foreground mb-3">{{ t('chatHome.examplesTitle') }}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            v-for="example in examples"
            :key="example.id"
            class="group text-left p-4 rounded-xl border border-border/60 bg-card hover:shadow-md hover:border-primary/30 transition-all"
            @click="selectExample(example)"
          >
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/15 transition-colors">
                <component :is="example.icon" class="w-4 h-4 text-primary" />
              </div>
              <div class="min-w-0 flex-1">
                <h4 class="text-sm font-medium leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                  {{ example.title }}
                </h4>
                <p class="text-xs text-muted-foreground mt-1">{{ example.source }}</p>
              </div>
            </div>
            <div class="flex items-center justify-between mt-3">
              <div class="flex gap-1.5">
                <span
                  v-for="tag in example.tags"
                  :key="tag"
                  class="px-2 py-0.5 bg-muted text-muted-foreground rounded-full text-[10px]"
                >
                  {{ tag }}
                </span>
              </div>
              <ArrowRight class="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </button>
        </div>
      </div>

      <!-- 弹性占位 -->
      <div class="flex-1 min-h-4" />

      <!-- 输入区域 -->
      <div class="sticky bottom-0 pb-4 bg-gradient-to-t from-background via-background to-transparent pt-8">
        <!-- 已上传文件列表 -->
        <div v-if="uploadedFiles.length > 0" class="mb-3">
          <div class="flex flex-wrap gap-2">
            <div
              v-for="(file, index) in uploadedFiles"
              :key="index"
              class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/80 border border-border/60 text-sm group"
            >
              <component :is="getFileIcon(file.name)" class="w-4 h-4 text-muted-foreground" />
              <span class="max-w-[160px] truncate">{{ file.name }}</span>
              <span class="text-xs text-muted-foreground">{{ formatFileSize(file.size) }}</span>
              <button
                class="ml-0.5 p-0.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                @click="removeFile(index)"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="relative rounded-2xl border border-border/80 bg-card shadow-lg focus-within:border-primary/40 focus-within:shadow-xl focus-within:shadow-primary/5 transition-all">
          <Textarea
            v-model="question"
            :placeholder="t('chatHome.textareaPlaceholder')"
            class="min-h-[100px] max-h-[280px] resize-none border-0 bg-transparent px-4 pt-4 pb-14 focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
            @keydown="handleKeydown"
          />

          <!-- 底部操作栏 -->
          <div class="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 py-2.5">
            <div class="flex items-center gap-1">
              <!-- 上传按钮 -->
              <input
                type="file"
                ref="fileInput"
                class="hidden"
                @change="handleFileUpload"
                accept=".txt,.csv,.xlsx,.xls,.pdf,.doc,.docx,.zip"
                multiple
              />
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-lg"
                      @click="fileInput?.click()"
                    >
                      <FileUp class="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{{ t('chatHome.uploadTooltip') }}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <!-- 设置按钮 -->
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-lg"
                      :class="showOptions ? 'bg-muted' : ''"
                      @click="showOptions = !showOptions"
                    >
                      <Settings2 class="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{{ t('chatHome.settingsTooltip') }}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <!-- 参数选择器（展开时显示） -->
              <Transition name="slide-fade">
                <div v-if="showOptions" class="flex items-center gap-2 ml-1">
                  <div v-for="item in selectConfig" :key="item.field">
                    <Select
                      v-model="selectedOptions[item.field as keyof typeof selectedOptions]"
                      :default-value="item.options[0].value"
                    >
                      <SelectTrigger class="h-7 text-xs min-w-[80px] border-border/60">
                        <SelectValue :placeholder="item.placeholder" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectLabel>{{ item.label }}</SelectLabel>
                          <SelectItem
                            v-for="option in item.options"
                            :key="option.value"
                            :value="option.value"
                          >
                            <span>{{ option.label }}</span>
                            <span v-if="option.hint" class="text-xs text-muted-foreground ml-1">
                              ({{ option.hint }})
                            </span>
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </Transition>
            </div>

            <!-- 提交按钮 -->
            <Button
              size="sm"
              class="h-8 px-4 rounded-lg gradient-bg border-0 text-white hover:opacity-90 disabled:opacity-40"
              :disabled="!canSubmit || isSubmitting"
              @click="handleSubmit"
            >
              <svg v-if="isSubmitting" class="animate-spin w-4 h-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <Send v-else class="w-4 h-4 mr-1" />
              <span>{{ isSubmitting ? t('chatHome.submitting') : t('chatHome.startAnalysis') }}</span>
            </Button>
          </div>
        </div>

        <!-- 底部提示 -->
        <p class="text-center text-xs text-muted-foreground mt-3">
          {{ t('chatHome.bottomHint') }}
        </p>
      </div>
    </div>

    <!-- 文件确认弹窗 -->
    <Dialog v-model:open="showFileConfirm">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ t('chatHome.confirmContinue') }}</DialogTitle>
        </DialogHeader>
        <p class="text-sm text-muted-foreground py-2">
          {{ t('chatHome.noFileWarning') }}
        </p>
        <DialogFooter class="flex gap-2">
          <Button variant="outline" size="sm" @click="cancelContinueWithoutFile">
            {{ t('chatHome.goUpload') }}
          </Button>
          <Button size="sm" @click="confirmContinueWithoutFile">
            {{ t('chatHome.continueSubmit') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-fade-enter-active {
  transition: all 0.2s ease;
}
.slide-fade-leave-active {
  transition: all 0.15s ease;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(-8px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>
