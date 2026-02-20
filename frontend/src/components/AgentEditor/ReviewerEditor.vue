<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTaskStore } from '@/stores/task'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { renderMarkdown } from '@/utils/markdown'

const taskStore = useTaskStore()

// 评审消息
const reviewerMsgs = computed(() => taskStore.reviewerMessages)

// 分析消息
const analyzerMsgs = computed(() => taskStore.analyzerMessages)

// 验证消息
const validatorMsgs = computed(() => taskStore.validatorMessages)

// 优化消息
const optimizerMsgs = computed(() => taskStore.optimizerMessages)

// 合并所有分析评审相关消息，按时间排序
const allMessages = computed(() => {
  const msgs = [
    ...reviewerMsgs.value.map(m => ({ ...m, _category: '评审' as const })),
    ...analyzerMsgs.value.map(m => ({ ...m, _category: '分析' as const })),
    ...validatorMsgs.value.map(m => ({ ...m, _category: '验证' as const })),
    ...optimizerMsgs.value.map(m => ({ ...m, _category: '优化' as const })),
  ]
  return msgs
})

// 分类统计
const stats = computed(() => ({
  reviewer: reviewerMsgs.value.length,
  analyzer: analyzerMsgs.value.length,
  validator: validatorMsgs.value.length,
  optimizer: optimizerMsgs.value.length,
  total: allMessages.value.length,
}))

// 分类颜色
const categoryColors: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  '评审': { bg: 'bg-purple-50', border: 'border-purple-500', text: 'text-purple-700', badge: 'bg-purple-100 text-purple-700' },
  '分析': { bg: 'bg-blue-50', border: 'border-blue-500', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-700' },
  '验证': { bg: 'bg-green-50', border: 'border-green-500', text: 'text-green-700', badge: 'bg-green-100 text-green-700' },
  '优化': { bg: 'bg-orange-50', border: 'border-orange-500', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-700' },
}

// 渲染后的内容（缓存，避免重复渲染）
const renderedContents = ref<Record<string, string>>({})

// 监听消息变化，异步渲染 Markdown
watch(allMessages, async (msgs) => {
  const newRendered: Record<string, string> = {}
  for (const msg of msgs) {
    if (msg.content && msg.id) {
      // 已渲染过的跳过
      if (renderedContents.value[msg.id]) {
        newRendered[msg.id] = renderedContents.value[msg.id]
      } else {
        newRendered[msg.id] = await renderMarkdown(msg.content)
      }
    }
  }
  renderedContents.value = newRendered
}, { immediate: true })

// 获取某条消息的渲染 HTML
function getRenderedContent(msgId: string): string {
  return renderedContents.value[msgId] || ''
}
</script>

<template>
  <div class="h-full flex flex-col p-4">
    <!-- 统计概览 -->
    <div class="mb-4 bg-white rounded-lg border shadow-sm">
      <div class="border-b px-4 py-3 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">分析评审概览</h2>
        <span class="px-2 py-1 text-xs bg-gray-100 rounded">共 {{ stats.total }} 条消息</span>
      </div>
      <div class="p-4 grid grid-cols-4 gap-3">
        <div class="text-center p-3 rounded-lg bg-purple-50 border border-purple-200">
          <div class="text-2xl font-bold text-purple-700">{{ stats.reviewer }}</div>
          <div class="text-xs text-purple-600 mt-1">评审</div>
        </div>
        <div class="text-center p-3 rounded-lg bg-blue-50 border border-blue-200">
          <div class="text-2xl font-bold text-blue-700">{{ stats.analyzer }}</div>
          <div class="text-xs text-blue-600 mt-1">分析</div>
        </div>
        <div class="text-center p-3 rounded-lg bg-green-50 border border-green-200">
          <div class="text-2xl font-bold text-green-700">{{ stats.validator }}</div>
          <div class="text-xs text-green-600 mt-1">验证</div>
        </div>
        <div class="text-center p-3 rounded-lg bg-orange-50 border border-orange-200">
          <div class="text-2xl font-bold text-orange-700">{{ stats.optimizer }}</div>
          <div class="text-xs text-orange-600 mt-1">优化</div>
        </div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="flex-1 bg-white rounded-lg border shadow-sm overflow-hidden">
      <div class="border-b px-4 py-3">
        <h2 class="text-lg font-semibold text-gray-900">消息流</h2>
      </div>
      <div class="h-full pb-14">
        <ScrollArea class="h-full">
          <div class="p-4 space-y-3">
            <div v-if="allMessages.length > 0">
              <div
                v-for="(msg, index) in allMessages"
                :key="index"
                :class="[
                  'border-l-4 pl-4 py-3 rounded-r mb-3',
                  categoryColors[msg._category]?.bg || 'bg-gray-50',
                ]"
                :style="{ borderLeftColor: msg._category === '评审' ? '#a855f7' : msg._category === '分析' ? '#3b82f6' : msg._category === '验证' ? '#22c55e' : '#f97316' }"
              >
                <div class="flex items-center gap-2 mb-2">
                  <span
                    :class="[
                      'px-2 py-0.5 text-xs rounded-full font-medium',
                      categoryColors[msg._category]?.badge || 'bg-gray-100 text-gray-700'
                    ]"
                  >
                    {{ msg._category }}
                  </span>
                  <span class="text-xs text-gray-400">{{ msg.agent_type }}</span>
                </div>
                <div class="prose prose-slate max-w-none text-sm text-gray-800 leading-relaxed"
                  v-html="getRenderedContent(msg.id)">
                </div>

                <!-- 评审专属：显示评分 -->
                <div v-if="msg._category === '评审' && 'review_score' in msg && msg.review_score" class="mt-2">
                  <Separator class="my-2" />
                  <div class="flex items-center gap-4 text-xs text-gray-600">
                    <span>综合评分: <strong class="text-purple-700">{{ msg.review_score }}</strong></span>
                    <div v-if="'dimension_scores' in msg && msg.dimension_scores" class="flex gap-2">
                      <span v-for="(score, dim) in msg.dimension_scores" :key="dim">
                        {{ dim }}: {{ score }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="flex items-center justify-center h-32 text-gray-500">
              暂无分析评审消息，等待 Agent 运行...
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import 'katex/dist/katex.min.css';

:deep(.prose h1) { @apply text-2xl font-bold mb-4 text-gray-900; }
:deep(.prose h2) { @apply text-xl font-semibold mt-3 mb-3 text-gray-800; }
:deep(.prose h3) { @apply text-lg font-semibold mt-2 mb-2 text-gray-800; }
:deep(.prose p) { @apply mb-3 leading-relaxed; }
:deep(.prose ul) { @apply list-disc ml-6 mb-3 space-y-1; }
:deep(.prose ol) { @apply list-decimal ml-6 mb-3 space-y-1; }
:deep(.prose blockquote) { @apply border-l-4 border-gray-300 pl-4 italic my-3 text-gray-600; }
:deep(.prose a) { @apply text-blue-600 hover:text-blue-800 underline; }
:deep(.prose hr) { @apply my-6 border-gray-200; }
:deep(.prose table) { @apply w-full border-collapse my-4 !border-2 !border-gray-400; }
:deep(.prose th) { @apply !bg-gray-200 p-2 text-left !font-bold !text-gray-900 !border !border-gray-400; }
:deep(.prose td) { @apply p-2 !text-gray-900 !border !border-gray-400; }
:deep(.prose tr:nth-child(even)) { @apply !bg-gray-50; }
:deep(.prose code) { @apply bg-gray-100 px-1 py-0.5 rounded text-sm font-mono; }
:deep(.prose pre) { @apply bg-gray-100 p-3 rounded-lg overflow-x-auto my-3; }
:deep(.prose pre code) { @apply bg-transparent p-0; }
:deep(.prose .math-block) { @apply my-3 overflow-x-auto; text-align: center; }
:deep(.prose .katex-display) { @apply my-3 overflow-x-auto; }
:deep(.prose .katex) { font-size: 1.1em; }
:deep(.prose strong) { @apply font-bold text-gray-900; }
</style>
