<script setup lang="ts">
import type { ProviderConfig } from "@/stores/apiKeys";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2 } from "lucide-vue-next";

const { t } = useI18n();

const props = defineProps<{
	provider: ProviderConfig;
}>();

const emit = defineEmits<{
	(e: "edit", provider: ProviderConfig): void;
	(e: "delete", providerId: string): void;
}>();

/** API Key 脱敏显示 */
const maskedApiKey = computed(() => {
	const key = props.provider.apiKey;
	if (!key) return "••••••••";
	if (key.length <= 8) return "••••••••";
	return `${key.slice(0, 4)}····${key.slice(-4)}`;
});

/** 状态色点颜色 + 动画 */
const statusColor = computed(() => {
	switch (props.provider.status) {
		case "valid":
			return "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]";
		case "invalid":
			return "bg-red-400 shadow-[0_0_6px_rgba(248,113,113,0.4)]";
		default:
			return "bg-zinc-300 dark:bg-zinc-600";
	}
});

/** 状态提示文本 */
const statusText = computed(() => {
	switch (props.provider.status) {
		case "valid":
			return t("provider.statusValid");
		case "invalid":
			return t("provider.statusInvalid");
		default:
			return t("provider.statusUntested");
	}
});

/** 供应商首字母头像背景色 */
const avatarColor = computed(() => {
	const colors = [
		"bg-blue-500/10 text-blue-600 dark:text-blue-400",
		"bg-purple-500/10 text-purple-600 dark:text-purple-400",
		"bg-amber-500/10 text-amber-600 dark:text-amber-400",
		"bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
		"bg-pink-500/10 text-pink-600 dark:text-pink-400",
		"bg-cyan-500/10 text-cyan-600 dark:text-cyan-400",
	];
	const hash = props.provider.name.charCodeAt(0) || 0;
	return colors[hash % colors.length];
});

const avatarLetter = computed(() => {
	return (props.provider.name || "?").charAt(0).toUpperCase();
});
</script>

<template>
  <div
    class="group relative rounded-xl border border-border/50 bg-card/50 p-4 hover:bg-accent/30 hover:border-border transition-all duration-200 cursor-default"
  >
    <div class="flex items-center gap-3.5">
      <!-- 供应商头像 -->
      <div
        :class="['flex items-center justify-center w-10 h-10 rounded-xl text-sm font-semibold shrink-0', avatarColor]"
      >
        {{ avatarLetter }}
      </div>

      <!-- 供应商信息 -->
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <span class="text-[14px] font-medium truncate">{{ provider.name }}</span>
          <!-- 状态圆点 -->
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <span
                  :class="['inline-block w-[7px] h-[7px] rounded-full shrink-0 transition-all', statusColor]"
                />
              </TooltipTrigger>
              <TooltipContent side="top" :side-offset="4">
                <p class="text-xs">{{ statusText }}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <div class="flex items-center gap-1.5 mt-0.5">
          <span class="text-xs text-muted-foreground/70 truncate">{{ provider.modelId }}</span>
          <span class="text-muted-foreground/30">·</span>
          <span class="text-xs text-muted-foreground/50 font-mono tracking-tight">{{ maskedApiKey }}</span>
        </div>
      </div>

      <!-- 操作按钮（hover 显示） -->
      <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                class="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
                @click="emit('edit', provider)"
              >
                <Pencil class="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top" :side-offset="4">
              <p class="text-xs">{{ t('provider.editTooltip') }}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                class="h-8 w-8 rounded-lg text-muted-foreground hover:text-red-500 dark:hover:text-red-400"
                @click="emit('delete', provider.id)"
              >
                <Trash2 class="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top" :side-offset="4">
              <p class="text-xs">{{ t('provider.deleteTooltip') }}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  </div>
</template>
