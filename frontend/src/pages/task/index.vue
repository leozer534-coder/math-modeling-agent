<script setup lang="ts">
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import CoderEditor from '@/components/AgentEditor/CoderEditor.vue'
import WriterEditor from '@/components/AgentEditor/WriterEditor.vue'
import ModelerEditor from '@/components/AgentEditor/ModelerEditor.vue'
import ReviewerEditor from '@/components/AgentEditor/ReviewerEditor.vue'
import ChatArea from '@/components/chat/ChatArea.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'
import { useTaskStore } from '@/stores/task'
import { getWriterSeque } from '@/apis/commonApi';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast/use-toast'
import FilesSheet from '@/pages/task/components/FileSheet.vue'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Play, 
  RotateCcw, 
  StopCircle, 
  Download, 
  FileText, 
  Code2, 
  Brain, 
  Search,
  LayoutList
} from 'lucide-vue-next'

const { toast } = useToast()

const props = defineProps<{ task_id: string }>()
const taskStore = useTaskStore()
const writerSequence = ref<string[]>([]);
const startTime = ref<number>(Date.now())
const currentTime = ref<number>(Date.now())
let timer: ReturnType<typeof setInterval> | null = null

const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / 1000)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60
  if (hours > 0) return `${hours}h ${minutes}m ${remainingSeconds}s`
  if (minutes > 0) return `${minutes}m ${remainingSeconds}s`
  return `${remainingSeconds}s`
}

const runningDuration = ref<string>('0s')
const updateDuration = () => {
  currentTime.value = Date.now()
  runningDuration.value = formatDuration(currentTime.value - startTime.value)
}

const allAgentMessages = computed(() =>
  taskStore.messages.filter(
    (msg) => msg.msg_type === 'agent' && msg.content != null && msg.content !== ''
  )
)

if (import.meta.env.DEV) {
  console.log('Task ID:', props.task_id)
}

onMounted(async () => {
  const hasHistory = await taskStore.loadHistoryMessages(props.task_id)
  if (hasHistory) {
    taskStore.taskId = props.task_id
  } else {
    taskStore.connectWebSocket(props.task_id)
  }

  try {
    const res = await getWriterSeque();
    writerSequence.value = Array.isArray(res.data) ? res.data : [];
  } catch (error) {
    if (import.meta.env.DEV) console.error('获取论文结构失败:', error)
  }

  timer = setInterval(updateDuration, 1000)
  updateDuration()
})

const handleStopTask = async () => {
  toast({ title: '正在终止任务...', description: '发送取消指令' })
  await taskStore.cancelCurrentTask()
  toast({ title: '任务已终止', description: '任务执行已停止' })
}

onBeforeUnmount(() => {
  taskStore.closeWebSocket()
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset class="bg-background overflow-hidden">
      <!-- 顶部 Header / 工具栏 -->
      <header class="flex h-14 shrink-0 items-center gap-2 border-b border-border/40 bg-background/60 backdrop-blur-md px-4 absolute top-0 left-0 right-0 z-10 transition-all">
        <SidebarTrigger class="-ml-1 text-muted-foreground hover:text-foreground" />
        
        <div class="h-4 w-[1px] bg-border mx-2"></div>

        <div class="flex items-center gap-2 text-sm text-foreground/80 font-medium">
          <span class="opacity-50">Task</span>
          <span>/</span>
          <span class="truncate max-w-[200px]">{{ props.task_id.slice(0, 8) }}...</span>
        </div>

        <div class="ml-auto flex items-center gap-3">
             <div class="text-xs font-mono text-muted-foreground bg-secondary/50 px-2 py-1 rounded-md">
                {{ runningDuration }}
             </div>

             <div class="h-4 w-[1px] bg-border mx-1"></div>

             <!-- 交互控制按钮组 -->
             <div class="flex items-center gap-2">
                <Button
                  v-if="taskStore.isWaitingForInput"
                  @click="taskStore.sendAction('confirm')"
                  size="sm"
                  class="h-8 gap-1.5 rounded-full bg-green-500 hover:bg-green-600 text-white shadow-sm"
                >
                  <Play class="w-3.5 h-3.5" />
                  Continue
                </Button>
                <Button
                  v-if="taskStore.isWaitingForInput"
                  @click="taskStore.sendAction('rollback')"
                  variant="outline"
                  size="sm"
                  class="h-8 gap-1.5 rounded-full border-border/60 hover:bg-secondary/80"
                >
                  <RotateCcw class="w-3.5 h-3.5" />
                  Rollback
                </Button>
                <Button
                  v-if="taskStore.isTaskRunning"
                  @click="handleStopTask"
                  variant="destructive"
                  size="sm"
                  class="h-8 gap-1.5 rounded-full shadow-sm opacity-90 hover:opacity-100"
                >
                  <StopCircle class="w-3.5 h-3.5" />
                  Stop
                </Button>

                <Button @click="taskStore.downloadMessages" variant="ghost" size="icon" class="h-8 w-8 rounded-full hover:bg-secondary">
                  <Download class="w-4 h-4 text-muted-foreground" />
                </Button>

                <FilesSheet />
             </div>
        </div>
      </header>

      <!-- 主要内容区域 (由 Header 撑开顶部 padding) -->
      <div class="flex-1 h-full pt-14 p-2 sm:p-4 bg-secondary/30">
        <ResizablePanelGroup direction="horizontal" class="h-full rounded-xl border border-border/40 shadow-sm bg-background overflow-hidden">
          
          <!-- 左侧：聊天区域 -->
          <ResizablePanel :default-size="40" :min-size="30" class="h-full bg-background/50 backdrop-blur-sm">
            <ChatArea :messages="taskStore.chatMessages" />
          </ResizablePanel>

          <ResizableHandle class="bg-border/20 w-[1px] hover:w-[2px] transition-all hover:bg-primary/50" />

          <!-- 右侧：工作区 -->
          <ResizablePanel :default-size="60" :min-size="30" class="h-full min-w-0 bg-background/50">
             <Tabs default-value="modeler" class="w-full h-full flex flex-col">
                <div class="border-b border-border/40 px-3 py-2 bg-secondary/10">
                   <TabsList class="h-9 w-full justify-start gap-1 bg-muted/40 p-1 rounded-lg">
                      <TabsTrigger value="modeler" class="rounded-md px-3 text-xs data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all flex gap-1.5">
                        <Brain class="w-3.5 h-3.5" /> 建模
                      </TabsTrigger>
                      <TabsTrigger value="coder" class="rounded-md px-3 text-xs data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all flex gap-1.5">
                        <Code2 class="w-3.5 h-3.5" /> 代码
                      </TabsTrigger>
                      <TabsTrigger value="writer" class="rounded-md px-3 text-xs data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all flex gap-1.5">
                        <FileText class="w-3.5 h-3.5" /> 论文
                      </TabsTrigger>
                      <TabsTrigger value="reviewer" class="rounded-md px-3 text-xs data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all flex gap-1.5">
                        <Search class="w-3.5 h-3.5" /> 评审
                      </TabsTrigger>
                      <TabsTrigger value="logs" class="rounded-md px-3 text-xs data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all flex gap-1.5">
                        <LayoutList class="w-3.5 h-3.5" /> 日志
                      </TabsTrigger>
                   </TabsList>
                </div>

                <div class="flex-1 overflow-hidden relative">
                    <TabsContent value="modeler" class="absolute inset-0 m-0 p-0 border-none outline-none data-[state=active]:flex flex-col">
                      <ModelerEditor />
                    </TabsContent>
        
                    <TabsContent value="coder" class="absolute inset-0 m-0 p-0 border-none outline-none data-[state=active]:flex flex-col">
                      <CoderEditor />
                    </TabsContent>
        
                    <TabsContent value="writer" class="absolute inset-0 m-0 p-0 border-none outline-none data-[state=active]:flex flex-col">
                      <WriterEditor :messages="taskStore.writerMessages" :writerSequence="writerSequence" />
                    </TabsContent>
        
                    <TabsContent value="reviewer" class="absolute inset-0 m-0 p-0 border-none outline-none data-[state=active]:flex flex-col">
                      <ReviewerEditor />
                    </TabsContent>
        
                    <TabsContent value="logs" class="absolute inset-0 m-0 p-0 border-none outline-none data-[state=active]:flex flex-col">
                       <div class="h-full flex flex-col">
                           <div class="px-4 py-3 border-b flex justify-between items-center bg-white/50">
                             <h2 class="text-sm font-semibold text-foreground/80">System Logs</h2>
                             <span class="text-[10px] bg-secondary px-2 py-0.5 rounded-full text-muted-foreground">{{ allAgentMessages.length }} entries</span>
                           </div>
                           <ScrollArea class="flex-1 p-4 bg-secondary/5">
                             <div class="space-y-3 max-w-4xl mx-auto">
                                <div v-if="allAgentMessages.length === 0" class="text-center py-20 text-muted-foreground">
                                   No logs available
                                </div>
                                <div
                                  v-for="(msg, index) in allAgentMessages"
                                  :key="index"
                                  class="p-4 rounded-xl bg-card border border-border/50 shadow-sm text-sm hover:shadow-md transition-shadow"
                                >
                                   <div class="flex items-center gap-2 mb-2">
                                     <span class="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-md bg-primary/10 text-primary">
                                       {{ 'agent_type' in msg ? msg.agent_type : 'System' }}
                                     </span>
                                     <span class="text-[10px] text-muted-foreground ml-auto">{{ new Date().toLocaleTimeString() }}</span>
                                   </div>
                                   <div class="text-foreground/90 whitespace-pre-wrap font-mono text-[13px] leading-relaxed">
                                     {{ msg.content }}
                                   </div>
                                </div>
                             </div>
                           </ScrollArea>
                       </div>
                    </TabsContent>
                </div>
             </Tabs>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>

<style scoped>
/* 确保 TabsContent 占满 */
:deep(.tabs-content) {
  height: 100%;
}
</style>
