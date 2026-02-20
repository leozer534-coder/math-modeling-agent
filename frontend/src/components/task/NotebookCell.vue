<script setup lang="ts">
import type { CodeCell, NoteCell, ResultCell } from "@/utils/interface";
import { renderMarkdown, sanitizeHtml } from "@/utils/markdown";
import type { OutputItem } from "@/utils/response";
import { Copy } from "lucide-vue-next";
import { reactive, ref, watch } from "vue";

const props = defineProps<{
	cell: NoteCell;
}>();

// 异步 Markdown 渲染缓存：key = result index，value = 渲染后的 HTML
const markdownCache = reactive<Record<number, string>>({});

const copySuccess = ref(false);

// 复制代码内容到剪贴板
const copyCode = async (content: string) => {
	try {
		await navigator.clipboard.writeText(content);
		copySuccess.value = true;
		setTimeout(() => {
			copySuccess.value = false;
		}, 2000);
	} catch (err) {
		if (import.meta.env.DEV) {
			console.error("复制失败:", err);
		}
	}
};

// 获取结果格式的CSS类
const getResultClass = (result: OutputItem) => {
	switch (result.res_type) {
		case "stdout":
			return "text-muted-foreground";
		case "stderr":
			return "text-warning";
		case "error":
			return "text-destructive";
		default:
			return "text-foreground";
	}
};

// 判断结果是否为图片
const isImageResult = (result: OutputItem) => {
	return (
		result.res_type === "result" &&
		["png", "jpeg", "svg"].includes(result.format as string)
	);
};

// 判断结果是否为LaTeX
const isLatexResult = (result: OutputItem) => {
	return result.res_type === "result" && result.format === "latex";
};

// 判断结果是否为JSON
const isJsonResult = (result: OutputItem) => {
	return result.res_type === "result" && result.format === "json";
};

// 格式化JSON显示
const formatJson = (jsonString: string) => {
	try {
		const parsed = JSON.parse(jsonString);
		return JSON.stringify(parsed, null, 2);
	} catch (e) {
		return jsonString;
	}
};

// 渲染Markdown内容：监听 cell 变化，异步渲染并缓存结果
watch(
	() => props.cell,
	async (cell) => {
		if (cell.type !== "result") return;
		const resultCell = cell as ResultCell;
		for (let i = 0; i < resultCell.code_results.length; i++) {
			const result = resultCell.code_results[i];
			if (
				result.res_type === "result" &&
				result.format === "markdown" &&
				result.msg
			) {
				markdownCache[i] = await renderMarkdown(result.msg);
			}
		}
	},
	{ immediate: true, deep: true },
);

// 类型守卫函数，用于区分单元格类型
const isCodeCell = (cell: NoteCell): cell is CodeCell => {
	return cell.type === "code";
};

const isResultCell = (cell: NoteCell): cell is ResultCell => {
	return cell.type === "result";
};
</script>

<template>
  <div :class="[
    'bg-card rounded-lg shadow-sm overflow-hidden',
    'border border-border hover:border-primary/50',
    cell.type === 'code' ? 'code-cell' : 'result-cell'
  ]">
    <!-- 单元格头部 -->
    <div
      class="px-3 py-1 flex items-center justify-between bg-gradient-to-r from-muted to-card border-b border-border">
      <div class="flex items-center space-x-2">
        <span :class="[
          'px-2 py-1 rounded text-xs font-medium',
          cell.type === 'code' ? 'bg-primary/10 text-primary' : 'bg-success/10 text-success'
        ]">
          {{ cell.type === 'code' ? 'Code' : 'Result' }}
        </span>
      </div>
    </div>

    <!-- 代码内容 -->
    <div class="relative">
      <!-- 代码单元格 -->
      <template v-if="isCodeCell(cell)">
        <div class="p-4 font-mono relative group">
          <!-- 复制按钮 -->
          <button
            class="absolute top-2 right-2 p-1.5 rounded-md bg-muted/80 text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-opacity"
            @click="copyCode(cell.content)"
            :title="copySuccess ? '已复制' : '复制代码'"
          >
            <Copy class="w-4 h-4" />
          </button>
          <pre class="text-sm overflow-x-auto"><code>{{ cell.content }}</code></pre>
        </div>
      </template>

      <!-- 结果单元格 -->
      <template v-else-if="isResultCell(cell)">
        <div class="px-4 py-3 bg-muted">
          <div class="text-xs font-medium text-muted-foreground mb-2">输出:</div>

          <!-- 遍历所有执行结果 -->
          <div v-for="(result, index) in cell.code_results" :key="index" class="mb-2 last:mb-0">
            <!-- 标准输出/错误 -->
            <template v-if="result.res_type === 'stdout' || result.res_type === 'stderr'">
              <div :class="['font-mono whitespace-pre-wrap text-sm', getResultClass(result)]">
                {{ result.msg }}
              </div>
            </template>

            <!-- 执行错误 -->
            <template v-else-if="result.res_type === 'error'">
              <div class="text-sm text-destructive font-mono whitespace-pre-wrap">
                <div class="font-bold">{{ result.name }}: {{ result.value }}</div>
                <div>{{ result.traceback }}</div>
              </div>
            </template>

            <!-- 执行结果 - 图片 (PNG, JPEG, SVG) -->
            <template v-else-if="isImageResult(result)">
              <img :src="`data:image/${result.format};base64,${result.msg}`"
                   class="max-w-full rounded-lg shadow-sm" />
            </template>

            <!-- 执行结果 - HTML -->
            <template v-else-if="result.res_type === 'result' && result.format === 'html'">
              <div class="prose prose-sm max-w-none" v-html="sanitizeHtml(result.msg || '')"></div>
            </template>

            <!-- 执行结果 - Markdown -->
            <template v-else-if="result.res_type === 'result' && result.format === 'markdown'">
              <div class="prose prose-sm max-w-none" v-html="markdownCache[index] || ''"></div>
            </template>

            <!-- 执行结果 - LaTeX（经过 DOMPurify 净化） -->
            <template v-else-if="isLatexResult(result)">
              <div class="katex-display" v-html="sanitizeHtml(result.msg || '')"></div>
            </template>

            <!-- 执行结果 - JSON -->
            <template v-else-if="isJsonResult(result)">
              <pre class="text-sm bg-muted p-2 rounded overflow-x-auto">{{ formatJson(result.msg || '') }}</pre>
            </template>

            <!-- 执行结果 - 默认文本 -->
            <template v-else>
              <div class="text-sm text-muted-foreground font-mono whitespace-pre-wrap">
                {{ result.msg }}
              </div>
            </template>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* 代码样式 */
.code-cell pre {
  background-color: hsl(var(--notebook-code-bg));
  border-radius: 0.375rem;
  padding: 0.5rem;
}

.code-cell code {
  color: hsl(var(--foreground));
}

/* 结果样式 */
.result-cell {
  margin-top: -0.25rem;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}
</style>
