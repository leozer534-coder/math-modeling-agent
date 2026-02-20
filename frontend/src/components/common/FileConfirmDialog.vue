<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { AlertTriangle } from "lucide-vue-next";
import { ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

// 控制弹窗显示
const showConfirmDialog = ref(false);
let resolvePromise: (value: boolean) => void;

// 打开确认弹窗（返回Promise）
const openConfirmDialog = () => {
	showConfirmDialog.value = true;
	return new Promise((resolve) => {
		resolvePromise = resolve;
	});
};

// 处理确认操作
const handleConfirm = () => {
	showConfirmDialog.value = false;
	resolvePromise(true);
};

// 处理取消操作
const handleCancel = () => {
	showConfirmDialog.value = false;
	resolvePromise(false);
};

// 暴露方法给父组件
defineExpose({ openConfirmDialog });
</script>

<template>
  <Dialog v-model:open="showConfirmDialog">
    <DialogContent class="max-w-[400px] rounded-2xl border-border/40 bg-background/95 backdrop-blur-xl p-0 gap-0">
      <DialogHeader class="px-7 pt-7 pb-1">
        <div class="flex items-center gap-2.5 mb-1">
          <div class="w-9 h-9 rounded-xl bg-amber-500/10 flex items-center justify-center shrink-0">
            <AlertTriangle class="w-4.5 h-4.5 text-amber-500" />
          </div>
          <DialogTitle class="text-[16px] font-semibold tracking-tight">
            {{ t('chatHome.confirmContinue') }}
          </DialogTitle>
        </div>
        <DialogDescription class="text-[13px] text-muted-foreground/70 leading-relaxed pl-[46px]">
          {{ t('chatHome.noFileWarning') }}
        </DialogDescription>
      </DialogHeader>

      <DialogFooter class="px-7 py-4 mt-2 border-t border-border/30 bg-muted/20 rounded-b-2xl">
        <div class="flex items-center justify-end w-full gap-2">
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-4 text-[13px] rounded-lg"
            @click="handleCancel"
          >
            {{ t('chatHome.goUpload') }}
          </Button>
          <Button
            size="sm"
            class="h-8 px-4 text-[13px] rounded-lg shadow-sm"
            @click="handleConfirm"
          >
            {{ t('chatHome.continueSubmit') }}
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
