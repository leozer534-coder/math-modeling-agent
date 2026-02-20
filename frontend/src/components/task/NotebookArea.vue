<script setup lang="ts">
import NotebookCell from "@/components/task/NotebookCell.vue";
import { useTaskStore } from "@/stores/task";
import type { CodeCell, NoteCell, ResultCell } from "@/utils/interface";
import { FileCode2 } from "lucide-vue-next";
import { computed } from "vue";

// 使用任务存储
const taskStore = useTaskStore();

// 将代码消息转换为Notebook单元格
const cells = computed<NoteCell[]>(() => {
	const notebookCells: NoteCell[] = [];

	// 获取代码执行工具消息，按顺序处理
	for (const toolMsg of taskStore.interpreterMessage) {
		// 处理代码输入消息
		if (toolMsg.input?.code) {
			const codeCell: CodeCell = {
				type: "code",
				content: toolMsg.input.code,
			};
			notebookCells.push(codeCell);
		}

		// 处理执行结果消息
		if (toolMsg.output && toolMsg.output.length > 0) {
			const resultCell: ResultCell = {
				type: "result",
				code_results: toolMsg.output,
			};
			notebookCells.push(resultCell);
		}
	}

	return notebookCells;
});
</script>

<template>
  <div class="notebook-area flex-1 px-1 pt-1 pb-4 h-full overflow-y-auto">
    <!-- 遍历所有单元格 -->
    <div v-for="(cell, index) in cells" :key="index" :class="[
      'transform transition-all duration-200 hover:shadow-lg',
      cell.type === 'code' ? 'pt-2' : 'pt-0'
    ]">
      <NotebookCell :cell="cell" />
    </div>

    <!-- 无内容时的提示 -->
    <div v-if="cells.length === 0" class="flex items-center justify-center h-full">
      <div class="text-muted-foreground text-center p-8">
        <div class="text-4xl mb-2 flex justify-center">
          <FileCode2 class="w-10 h-10" />
        </div>
        <div class="text-lg font-medium">暂无代码执行结果</div>
        <div class="text-sm">执行代码后将在此显示结果</div>
      </div>
    </div>
    <!-- 添加底部空间 -->
    <div class="h-4"></div>
  </div>
</template>

<style scoped>
/* 自定义滚动条 - 限定在组件范围内 */
.notebook-area::-webkit-scrollbar {
  width: 0.375rem;
  height: 0.375rem;
}

.notebook-area::-webkit-scrollbar-track {
  background-color: hsl(var(--muted));
  border-radius: 9999px;
}

.notebook-area::-webkit-scrollbar-thumb {
  background-color: hsl(var(--muted-foreground) / 0.4);
  border-radius: 9999px;
}

.notebook-area::-webkit-scrollbar-thumb:hover {
  background-color: hsl(var(--muted-foreground) / 0.6);
  transition-property: background-color;
  transition-duration: 200ms;
}

/* 代码高亮样式 */
:deep(.hljs) {
  background-color: hsl(var(--notebook-code-bg));
  padding: 1rem;
  border-radius: 0.5rem;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

/* 数学公式样式 */
:deep(.katex-display) {
  margin-top: 1rem;
  margin-bottom: 1rem;
  overflow-x: auto;
}

:deep(.katex) {
  font-size: 1rem;
}
</style>
