<script setup lang="ts">
import { cn } from "@/lib/utils";
import { AgentType } from "@/utils/enum";
import { renderMarkdown } from "@/utils/markdown";
import { ClipboardCheck, Code2, Pen, User } from "lucide-vue-next";
import type { HTMLAttributes } from "vue";
import { ref, watch } from "vue";

interface BubbleProps {
	type: "agent" | "user";
	agentType?: AgentType;
	class?: HTMLAttributes["class"];
	content: string;
}

const props = withDefaults(defineProps<BubbleProps>(), {
	type: "user",
});

// 使用安全的 Markdown 渲染（带 XSS 防护）
const renderedContent = ref("");

watch(
	() => props.content,
	async (newContent) => {
		renderedContent.value = await renderMarkdown(newContent);
	},
	{ immediate: true },
);
</script>

<template>
  <div :class="[
    'bubble',
    props.type === 'user' ? 'bubble-user' : '',
    props.type === 'agent' && props.agentType === AgentType.CODER ? 'bubble-coder' : '',
    props.type === 'agent' && props.agentType === AgentType.WRITER ? 'bubble-writer' : '',
    props.type === 'agent' && props.agentType === AgentType.REVIEWER ? 'bubble-reviewer' : '',
    props.class
  ]">
    <div class="flex flex-col gap-1 flex-1">
      <!-- 头像：Lucide 图标 + 彩色圆形背景 -->
      <div v-if="props.type === 'user'"
        class="w-8 h-8 rounded-full flex items-center justify-center bg-primary/15 text-primary mb-1">
        <User class="w-4 h-4" />
      </div>
      <div v-else-if="props.type === 'agent' && props.agentType === AgentType.CODER"
        class="w-8 h-8 rounded-full flex items-center justify-center agent-avatar-coder mb-1">
        <Code2 class="w-4 h-4" />
      </div>
      <div v-else-if="props.type === 'agent' && props.agentType === AgentType.WRITER"
        class="w-8 h-8 rounded-full flex items-center justify-center agent-avatar-writer mb-1">
        <Pen class="w-4 h-4" />
      </div>
      <div v-else-if="props.type === 'agent' && props.agentType === AgentType.REVIEWER"
        class="w-8 h-8 rounded-full flex items-center justify-center agent-avatar-reviewer mb-1">
        <ClipboardCheck class="w-4 h-4" />
      </div>
      <!-- 气泡内容在下方 -->
      <div :class="cn(
        'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
        props.type === 'user'
          ? 'bg-primary text-primary-foreground prose-invert'
          : 'bg-muted text-foreground',
        'prose prose-sm prose-slate max-w-none'
      )">
        <div v-html="renderedContent"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.prose) {
  @apply text-inherit;
}

:deep(.prose p) {
  @apply my-1;
}

:deep(.prose p:not(:first-child)) {
  @apply mt-1;
}

:deep(.prose h1),
:deep(.prose h2),
:deep(.prose h3),
:deep(.prose h4) {
  @apply my-1 font-semibold;
}

:deep(.prose h1) {
  @apply text-lg;
}

:deep(.prose h2) {
  @apply text-base;
}

:deep(.prose h3),
:deep(.prose h4) {
  @apply text-sm;
}

:deep(.prose ul),
:deep(.prose ol) {
  @apply my-1 pl-4;
}

:deep(.prose ul) {
  @apply list-disc;
}

:deep(.prose ol) {
  @apply list-decimal;
}

:deep(.prose li) {
  @apply my-0.5;
}

:deep(.prose code) {
  @apply px-1 py-0.5 rounded bg-black/10 dark:bg-white/10;
}

:deep(.prose pre) {
  @apply p-2 my-1 rounded bg-black/10 dark:bg-white/10 overflow-x-auto;
  max-width: 100%;
  width: 100%;
}

:deep(.prose pre code) {
  @apply bg-transparent p-0;
  @apply overflow-y-auto;
  max-width: 100%;
  white-space: pre-wrap;
  word-break: break-word;
}

:deep(.prose blockquote) {
  @apply my-1 pl-3 border-l-2 border-current opacity-80 italic;
}

:deep(.prose a) {
  @apply underline underline-offset-2 opacity-80 hover:opacity-100;
}

:deep(.prose img) {
  @apply my-1 rounded-lg;
}

:deep(.prose table) {
  @apply my-1 w-full;
}

:deep(.prose thead) {
  @apply border-b border-current opacity-20;
}

:deep(.prose th) {
  @apply p-2 text-left font-semibold;
}

:deep(.prose td) {
  @apply p-2 border-t border-current opacity-10;
}

:deep(.prose-invert) {
  @apply text-primary-foreground;
}

/* 确保透明度样式不会被继承 */
:deep(.prose thead *),
:deep(.prose td *) {
  @apply opacity-100;
}

.bubble {
  display: flex;
  flex: 1 1 0%;
}

.bubble-user {
  justify-content: flex-end;
}

.bubble-coder,
.bubble-writer,
.bubble-reviewer {
  justify-content: flex-start;
}

/* 用户气泡颜色 */
.bubble-user :deep(.prose) {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  box-shadow: 0 2px 8px hsl(var(--primary) / 0.08);
  border: 1px solid hsl(var(--primary));
}

/* CoderAgent 气泡颜色 */
.bubble-coder :deep(.prose) {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
  box-shadow: 0 2px 8px hsl(var(--agent-coder) / 0.08);
}

/* WriterAgent 气泡颜色 */
.bubble-writer :deep(.prose) {
  background: hsl(var(--agent-writer-bg));
  color: hsl(var(--foreground));
  box-shadow: 0 2px 8px hsl(var(--agent-writer) / 0.08);
}

/* ReviewerAgent 气泡颜色 */
.bubble-reviewer :deep(.prose) {
  background: hsl(var(--agent-reviewer-bg));
  color: hsl(var(--foreground));
  box-shadow: 0 2px 8px hsl(var(--agent-reviewer) / 0.08);
}
</style>
