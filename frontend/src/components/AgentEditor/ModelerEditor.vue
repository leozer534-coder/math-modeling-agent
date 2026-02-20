<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTaskStore } from '@/stores/task'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { renderMarkdown } from '@/utils/markdown'

const taskStore = useTaskStore()

// 获取最新的CoordinatorMessage
const latestCoordinatorMessage = computed(() => {
  const messages = taskStore.coordinatorMessages
  return messages.length > 0 ? messages[messages.length - 1] : null
})

// 解析CoordinatorMessage的JSON内容
const coordinatorData = computed(() => {
  if (!latestCoordinatorMessage.value?.content) return null

  try {
    const content = latestCoordinatorMessage.value.content
    // 移除可能的```json标记
    const cleanContent = content.replace(/```json\n?/, '').replace(/```$/, '').trim()
    return JSON.parse(cleanContent)
  } catch (error) {
    console.error('解析CoordinatorMessage失败:', error)
    return null
  }
})

// 获取最新的ModelerMessage
const latestModelerMessage = computed(() => {
  const messages = taskStore.modelerMessages
  return messages.length > 0 ? messages[messages.length - 1] : null
})

// 解析ModelerMessage的JSON内容
const modelerData = computed(() => {
  if (!latestModelerMessage.value?.content) return null

  try {
    const content = latestModelerMessage.value.content
    // 移除可能的```json标记
    const cleanContent = content.replace(/```json\n?/, '').replace(/```$/, '').trim()
    return JSON.parse(cleanContent)
  } catch (error) {
    console.error('解析ModelerMessage失败:', error)
    return null
  }
})

// 生成问题列表
const questionsList = computed(() => {
  if (!coordinatorData.value) return []

  const questions = []
  for (let i = 1; i <= coordinatorData.value.ques_count; i++) {
    const quesKey = `ques${i}`
    if (coordinatorData.value[quesKey]) {
      questions.push({
        number: i,
        content: coordinatorData.value[quesKey]
      })
    }
  }
  return questions
})

// ---- Markdown 渲染 ----
const renderedTitle = ref('')
const renderedBackground = ref('')
const renderedQuestions = ref<Record<number, string>>({})
const renderedEda = ref('')
const renderedSolutions = ref<Record<number, string>>({})
const renderedSensitivity = ref('')

// 渲染 coordinator 数据
watch(coordinatorData, async (data) => {
  if (!data) {
    renderedTitle.value = ''
    renderedBackground.value = ''
    renderedQuestions.value = {}
    return
  }
  if (data.title) renderedTitle.value = await renderMarkdown(data.title)
  if (data.background) renderedBackground.value = await renderMarkdown(data.background)

  const qMap: Record<number, string> = {}
  for (const q of questionsList.value) {
    qMap[q.number] = await renderMarkdown(q.content)
  }
  renderedQuestions.value = qMap
}, { immediate: true })

// 渲染 modeler 数据
watch([modelerData, questionsList], async ([mData, qList]) => {
  if (!mData) {
    renderedEda.value = ''
    renderedSolutions.value = {}
    renderedSensitivity.value = ''
    return
  }
  if (mData.eda) renderedEda.value = await renderMarkdown(mData.eda)
  if (mData.sensitivity_analysis) renderedSensitivity.value = await renderMarkdown(mData.sensitivity_analysis)

  const sMap: Record<number, string> = {}
  for (const q of qList) {
    const key = `ques${q.number}`
    if (mData[key]) {
      sMap[q.number] = await renderMarkdown(mData[key])
    }
  }
  renderedSolutions.value = sMap
}, { immediate: true })
</script>

<template>
  <div class="h-full flex flex-col p-4">
    <!-- 上半部分：CoordinatorMessage 结构化信息 -->
    <div class="h-1/2 mb-4 bg-white rounded-lg border shadow-sm">
      <div class="border-b px-4 py-3">
        <h2 class="text-lg font-semibold text-gray-900">题目信息</h2>
      </div>
      <div class="h-full pb-14">
        <ScrollArea class="h-full">
          <div class="p-4 space-y-4">
            <div v-if="coordinatorData">
              <!-- 题目标题 -->
              <div class="space-y-2">
                <h3 class="text-base font-medium text-gray-700">题目标题</h3>
                <div class="text-lg font-semibold text-gray-900 prose prose-slate max-w-none" v-html="renderedTitle">
                </div>
              </div>

              <Separator />

              <!-- 题目背景 -->
              <div class="space-y-2">
                <h3 class="text-base font-medium text-gray-700">题目背景</h3>
                <div class="prose prose-slate max-w-none text-sm text-gray-800 leading-relaxed"
                  v-html="renderedBackground">
                </div>
              </div>

              <Separator />

              <!-- 问题数量和问题列表 -->
              <div class="space-y-2">
                <div class="flex items-center gap-2">
                  <h3 class="text-base font-medium text-gray-700">问题列表</h3>
                  <span class="px-2 py-1 text-xs bg-gray-100 rounded">{{ coordinatorData.ques_count }} 个问题</span>
                </div>

                <div class="space-y-3">
                  <div v-for="question in questionsList" :key="question.number"
                    class="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50 rounded-r">
                    <div class="text-sm font-medium text-blue-700 mb-1">
                      问题 {{ question.number }}
                    </div>
                    <div class="prose prose-slate max-w-none text-sm text-gray-800 leading-relaxed"
                      v-html="renderedQuestions[question.number] || ''">
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="flex items-center justify-center h-32 text-gray-500">
              暂无题目信息
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>

    <!-- 下半部分：ModelerMessage 建模手册 -->
    <div class="h-1/2 bg-white rounded-lg border shadow-sm">
      <div class="border-b px-4 py-3">
        <h2 class="text-lg font-semibold text-gray-900">建模手册</h2>
      </div>
      <div class="h-full pb-14">
        <ScrollArea class="h-full">
          <div class="p-4">
            <div v-if="modelerData" class="space-y-4">
              <!-- EDA部分 -->
              <div v-if="modelerData.eda" class="space-y-2">
                <h3 class="text-base font-medium text-gray-700 flex items-center gap-2">
                  <span class="px-2 py-1 text-xs bg-gray-200 border rounded">EDA</span>
                  探索性数据分析
                </h3>
                <div
                  class="prose prose-slate max-w-none text-sm text-gray-800 leading-relaxed bg-gray-50 p-3 rounded"
                  v-html="renderedEda">
                </div>
              </div>

              <!-- 问题解决方案 -->
              <div v-for="question in questionsList" :key="`solution-${question.number}`" class="space-y-2">
                <div v-if="modelerData[`ques${question.number}`]">
                  <h3 class="text-base font-medium text-gray-700 flex items-center gap-2">
                    <span class="px-2 py-1 text-xs bg-gray-200 border rounded">问题{{ question.number }}</span>
                    解决方案
                  </h3>
                  <div
                    class="prose prose-slate max-w-none text-sm text-gray-800 leading-relaxed bg-green-50 p-3 rounded border-l-4 border-green-500"
                    v-html="renderedSolutions[question.number] || ''">
                  </div>
                </div>
              </div>

              <!-- 敏感性分析 -->
              <div v-if="modelerData.sensitivity_analysis" class="space-y-2">
                <h3 class="text-base font-medium text-gray-700 flex items-center gap-2">
                  <span class="px-2 py-1 text-xs bg-gray-200 border rounded">敏感性分析</span>
                </h3>
                <div
                  class="prose prose-slate max-w-none text-sm text-gray-800 leading-relaxed bg-orange-50 p-3 rounded border-l-4 border-orange-500"
                  v-html="renderedSensitivity">
                </div>
              </div>
            </div>

            <div v-else class="flex items-center justify-center h-32 text-gray-500">
              暂无建模手册信息
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
