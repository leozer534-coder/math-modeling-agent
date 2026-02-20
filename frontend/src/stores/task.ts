import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WebSocketClient } from '@/utils/websocket'
import type { WsClientMessage, WsServerMessage } from '@/utils/websocket'
import type { Message, CoderMessage, WriterMessage, UserMessage, ModelerMessage, CoordinatorMessage, InterpreterMessage, ProgressMessage, ReviewerMessage, AnalyzerMessage, ValidatorMessage, OptimizerMessage, StreamMessage } from '@/utils/response'
import { AgentType } from '@/utils/enum'
import { cancelTask as apiCancelTask } from '@/apis/interactiveModelingApi'
import { getTaskMessages } from '@/apis/taskApi'

const MAX_MESSAGES = 500

/**
 * 校验 WebSocket 收到的数据是否为合法的 Message 结构。
 * 仅做最小化 "形状" 检查，避免将非法数据推入消息列表。
 */
function isValidWsMessage(data: unknown): data is Message {
  if (typeof data !== 'object' || data === null) return false
  const obj = data as Record<string, unknown>
  return typeof obj.msg_type === 'string'
}

export const useTaskStore = defineStore('task', () => {
  const messages = ref<Message[]>([])
  let ws: WebSocketClient | null = null

  // 交互状态
  const taskId = ref<string>('')
  const isWaitingForInput = ref(false)
  const canRollback = ref(false)
  const isTaskRunning = ref(false)
  const currentStage = ref('')

  // 流式消息缓存: message_id -> 累积内容
  const streamBuffers = ref<Record<string, string>>({})

  // 连接 WebSocket
  function connectWebSocket(taskId_: string) {
    taskId.value = taskId_
    isTaskRunning.value = true
    const baseUrl = import.meta.env.VITE_WS_URL
    const wsUrl = `${baseUrl}/task/${taskId_}`

    ws = new WebSocketClient(wsUrl, (data: WsServerMessage) => {
      if (import.meta.env.DEV) {
        console.info('[TaskStore] 收到消息:', data)
      }
      if (!isValidWsMessage(data)) {
        if (import.meta.env.DEV) {
          console.warn('[TaskStore] 收到未知格式的 WebSocket 消息:', data)
        }
        return
      }

      // 处理流式消息
      if (data.msg_type === 'stream') {
        const streamData = data as StreamMessage
        const mid = streamData.message_id
        if (streamData.done) {
          // 流式结束，从缓存移除
          delete streamBuffers.value[mid]
        } else {
          // 追加 delta
          if (mid in streamBuffers.value) {
            streamBuffers.value[mid] += streamData.delta
          } else {
            streamBuffers.value[mid] = streamData.delta
          }
          // 查找已有消息并更新，或创建新消息
          const existing = messages.value.find(
            (m) => m.id === mid
          )
          if (existing) {
            existing.content = streamBuffers.value[mid]
          } else {
            messages.value.push({
              id: mid,
              msg_type: 'agent',
              content: streamBuffers.value[mid],
              agent_type: streamData.agent_type as AgentType,
            } as Message)
          }
        }
        return
      }

      // 处理系统消息中的交互状态
      if (data.msg_type === 'system') {
        const content = (data as any).content || ''
        if (content.includes('等待您的确认')) {
          isWaitingForInput.value = true
        } else if (content.includes('任务完成') || content.includes('执行失败') || content.includes('取消')) {
          isWaitingForInput.value = false
          isTaskRunning.value = false
        }
      }

      messages.value.push(data)
      // 消息数量保护，防止长时间运行任务导致内存无限增长
      if (messages.value.length > MAX_MESSAGES) {
        const excess = messages.value.length - MAX_MESSAGES
        messages.value.splice(1, excess)
      }
    })
    ws.connect()
  }

  // 关闭 WebSocket
  function closeWebSocket() {
    ws?.close()
  }

  // 通过 WebSocket 发送消息到后端
  function sendWsMessage(data: WsClientMessage) {
    if (ws) {
      ws.send(data)
    } else if (import.meta.env.DEV) {
      console.warn('[TaskStore] WebSocket 未连接，无法发送消息')
    }
  }

  // 获取 WebSocket 连接状态（响应式）
  function getConnectionState() {
    return ws?.state
  }

  function addUserMessage(content: string) {
    messages.value.push({
      id: Date.now().toString(),
      msg_type: 'user',
      content: content,
    } as UserMessage)
  }

  // 加载历史消息
  async function loadHistoryMessages(taskId_: string) {
    try {
      const { data } = await getTaskMessages(taskId_)
      if (Array.isArray(data) && data.length > 0) {
        messages.value = data as Message[]
        if (import.meta.env.DEV) {
          console.info('[TaskStore] 已加载历史消息:', data.length, '条')
        }
        return true
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.warn('[TaskStore] 加载历史消息失败:', error)
      }
    }
    return false
  }

  // 下载消息
  function downloadMessages() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(messages.value, null, 2))
    const downloadAnchorNode = document.createElement('a')
    downloadAnchorNode.setAttribute("href", dataStr)
    downloadAnchorNode.setAttribute("download", "message.json")
    document.body.appendChild(downloadAnchorNode)
    downloadAnchorNode.click()
    downloadAnchorNode.remove()
  }

  // 进度消息相关计算属性
  const latestProgress = computed(() => {
    const progressMsgs = messages.value.filter(
      (m): m is ProgressMessage => m.msg_type === 'progress'
    )
    if (progressMsgs.length === 0) return null
    return progressMsgs[progressMsgs.length - 1]
  })

  const progressPercent = computed(() => latestProgress.value?.percent ?? 0)
  const progressPhase = computed(() => latestProgress.value?.phase ?? '')
  const progressMessage = computed(() => latestProgress.value?.message ?? '')

  // 计算属性（排除 progress 消息，进度信息不应出现在聊天区域）
  const chatMessages = computed(() =>
    messages.value.filter(
      (msg) => {
        if (msg.msg_type === 'progress') {
          return false
        }
        if (msg.msg_type === 'agent' && msg.content != null && msg.content !== '') {
          return true
        }
        if (msg.msg_type === 'user') {
          return true
        }
        if (msg.msg_type === 'system') {
          return true
        }
        return false
      }
    )
  )

  const coordinatorMessages = computed(() =>
    messages.value.filter(
      (msg): msg is CoordinatorMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.COORDINATOR &&
        msg.content != null
    )
  )

  const modelerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is ModelerMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.MODELER &&
        msg.content != null
    )
  )

  const coderMessages = computed(() =>
    messages.value.filter(
      (msg): msg is CoderMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.CODER &&
        msg.content != null
    )
  )

  const writerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is WriterMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.WRITER &&
        msg.content != null
    )
  )

  // 评审消息
  const reviewerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is ReviewerMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.REVIEWER &&
        msg.content != null
    )
  )

  // 分析消息（问题分析、数据理解、结果解释等）
  const analyzerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is AnalyzerMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.ANALYZER &&
        msg.content != null
    )
  )

  // 验证消息
  const validatorMessages = computed(() =>
    messages.value.filter(
      (msg): msg is ValidatorMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.VALIDATOR &&
        msg.content != null
    )
  )

  // 优化消息
  const optimizerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is OptimizerMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.OPTIMIZER &&
        msg.content != null
    )
  )

  // 添加代码执行工具消息的计算属性
  const interpreterMessage = computed(() =>
    messages.value.filter(
      (msg): msg is InterpreterMessage =>
        msg.msg_type === 'tool' &&
        'tool_name' in msg &&
        msg.tool_name === 'execute_code'
    )
  )

  const files = computed(() => {
    // 反向遍历消息找到最新的文件列表
    for (let i = coderMessages.value.length - 1; i >= 0; i--) {
      const msg = coderMessages.value[i]
      if ('files' in msg && msg.files && Array.isArray(msg.files) && msg.files.length > 0) {
        if (import.meta.env.DEV) {
          console.log('找到文件列表:', msg.files)
        }
        return msg.files
      }
    }
    // 如果没有找到文件列表，返回空数组
    return []
  })

  // 初始化连接
  // 如果需要自动连接，可以在这里添加代码
  // 例如：connectWebSocket('default')

  // 取消任务
  async function cancelCurrentTask() {
    if (!taskId.value) return
    try {
      // 通过 WebSocket 发送取消（最快路径）
      sendWsMessage({ type: 'cancel' } as WsClientMessage)
      // 也通过 REST API 取消（备用路径）
      await apiCancelTask(taskId.value)
      isTaskRunning.value = false
      isWaitingForInput.value = false
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('取消任务失败:', error)
      }
    }
  }

  // 发送用户操作（确认/回退/修改等）
  function sendAction(action: string, feedback?: Record<string, unknown>, message?: string) {
    sendWsMessage({
      type: 'user_action',
      action,
      feedback: feedback || {},
      message: message || '',
    } as WsClientMessage)
    if (action === 'confirm' || action === 'skip') {
      isWaitingForInput.value = false
    }
  }

  // 发送用户文本消息
  function sendUserMessage(content: string) {
    if (!content.trim()) return
    sendWsMessage({
      type: 'user_message',
      content,
    } as WsClientMessage)
    addUserMessage(content)
  }

  return {
    messages,
    chatMessages,
    coordinatorMessages,
    modelerMessages,
    coderMessages,
    writerMessages,
    reviewerMessages,
    analyzerMessages,
    validatorMessages,
    optimizerMessages,
    interpreterMessage,
    files,
    latestProgress,
    progressPercent,
    progressPhase,
    progressMessage,
    // 交互状态
    taskId,
    isWaitingForInput,
    canRollback,
    isTaskRunning,
    currentStage,
    streamBuffers,
    // 方法
    connectWebSocket,
    closeWebSocket,
    sendWsMessage,
    getConnectionState,
    downloadMessages,
    addUserMessage,
    loadHistoryMessages,
    cancelCurrentTask,
    sendAction,
    sendUserMessage,
  }
}) 