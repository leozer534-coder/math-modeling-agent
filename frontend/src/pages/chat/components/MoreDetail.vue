<script setup lang="ts">
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { useI18n } from "vue-i18n";
import { FolderOpen, FileCode, FileText, Settings } from "lucide-vue-next";

const { t } = useI18n();

const modelValue = defineModel({
	type: Boolean,
	default: false,
});
</script>

<template>
  <Dialog :open="modelValue" @update:open="modelValue = false">
    <DialogContent class="max-w-[420px] rounded-2xl border-border/40 bg-background/95 backdrop-blur-xl p-0 gap-0">
      <DialogHeader class="px-7 pt-7 pb-1">
        <DialogTitle class="text-lg font-semibold tracking-tight">
          {{ t('about.title') }}
        </DialogTitle>
        <DialogDescription class="text-[13px] text-muted-foreground/70">
          {{ t('about.version') }}
        </DialogDescription>
      </DialogHeader>

      <div class="px-7 py-5 space-y-4">
        <!-- 输出目录 -->
        <div class="space-y-2.5">
          <h3 class="text-[13px] font-medium text-foreground">{{ t('about.outputDir') }}</h3>
          <div class="space-y-1.5">
            <div class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-muted/30 border border-border/30">
              <FolderOpen class="w-4 h-4 text-muted-foreground/50 shrink-0" />
              <div class="min-w-0">
                <p class="text-[12px] font-mono text-foreground/80 truncate">backend/project/work_dir/xxx/*</p>
              </div>
            </div>
            <div class="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-muted/20">
              <FileCode class="w-3.5 h-3.5 text-muted-foreground/40 shrink-0 mt-0.5" />
              <p class="text-[12px] text-muted-foreground/60">
                <span class="font-mono text-foreground/60">notebook.ipynb</span> — {{ t('about.notebookDesc') }}
              </p>
            </div>
            <div class="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-muted/20">
              <FileText class="w-3.5 h-3.5 text-muted-foreground/40 shrink-0 mt-0.5" />
              <p class="text-[12px] text-muted-foreground/60">
                <span class="font-mono text-foreground/60">res.md</span> — {{ t('about.paperDesc') }}
              </p>
            </div>
          </div>
        </div>

        <!-- 自定义配置 -->
        <div class="space-y-2.5">
          <h3 class="text-[13px] font-medium text-foreground">{{ t('about.customConfig') }}</h3>
          <div class="space-y-1.5">
            <div class="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-muted/20">
              <Settings class="w-3.5 h-3.5 text-muted-foreground/40 shrink-0 mt-0.5" />
              <p class="text-[12px] text-muted-foreground/60">
                <span class="text-foreground/60">{{ t('about.template') }}:</span>
                <span class="font-mono ml-1">backend/app/config/md_template.toml</span>
              </p>
            </div>
            <div class="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-muted/20">
              <Settings class="w-3.5 h-3.5 text-muted-foreground/40 shrink-0 mt-0.5" />
              <p class="text-[12px] text-muted-foreground/60">
                <span class="text-foreground/60">{{ t('about.prompts') }}:</span>
                <span class="font-mono ml-1">backend/app/config/prompts.toml</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
