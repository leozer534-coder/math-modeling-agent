import { ref } from 'vue'

/** 连接状态类型 */
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

/** WebSocket 服务端推送消息结构 */
export interface WsServerMessage {
  msg_type: string
  content?: string | null
  [key: string]: unknown
}

/** WebSocket 客户端发送消息结构 */
export interface WsClientMessage {
  type?: string
  msg_type?: string
  [key: string]: unknown
}

/** WebSocket 客户端配置选项 */
export interface WebSocketClientOptions {
  /** 是否自动重连，默认 true */
  autoReconnect?: boolean
  /** 心跳间隔（毫秒），默认 30000 */
  heartbeatInterval?: number
  /** Pong 超时时间（毫秒），默认 10000 */
  pongTimeout?: number
  /** 最大重连次数，默认 30 */
  maxReconnectAttempts?: number
}

/**
 * WebSocket 客户端
 *
 * 功能：
 * - 指数退避重连（前10次 1s->30s，后20次固定 30s，最多30次）
 * - 心跳保活（30s ping，10s pong 超时检测）
 * - 消息缓冲队列（连接未建立时缓存消息，连接后自动发送）
 * - 连接状态暴露（reactive）
 * - JSON.parse 防护
 */
export class WebSocketClient {
  private socket: WebSocket | null = null
  /** 消息缓冲队列：连接未就绪时暂存待发消息 */
  private messageQueue: string[] = []
  /** 消息缓冲队列最大长度，超出时丢弃最旧的消息 */
  private readonly MAX_QUEUE_SIZE = 50
  /** 当前重连尝试次数 */
  private reconnectAttempts = 0
  /** 最大重连次数 */
  private maxReconnectAttempts: number
  /** 心跳定时器 */
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  /** Pong 超时定时器 */
  private pongTimeout: ReturnType<typeof setTimeout> | null = null
  /** 重连定时器 */
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  /** 是否为用户主动关闭 */
  private manualClose = false
  /** 心跳间隔（毫秒） */
  private heartbeatInterval: number
  /** Pong 超时时间（毫秒） */
  private pongTimeoutMs: number
  /** 是否自动重连 */
  private autoReconnect: boolean

  /** 当前连接状态（响应式） */
  public state = ref<ConnectionState>('disconnected')

  constructor(
    private url: string,
    private onMessage: (data: WsServerMessage) => void,
    options?: WebSocketClientOptions
  ) {
    this.autoReconnect = options?.autoReconnect ?? true
    this.heartbeatInterval = options?.heartbeatInterval ?? 30000
    this.pongTimeoutMs = options?.pongTimeout ?? 10000
    this.maxReconnectAttempts = options?.maxReconnectAttempts ?? 30
  }

  /** 建立 WebSocket 连接 */
  connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.manualClose = false
    this.state.value = this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting'

    try {
      this.socket = new WebSocket(this.url)
    } catch (error) {
      if (import.meta.env.DEV) {
        console.warn('[WebSocket] 创建连接失败:', error)
      }
      this.scheduleReconnect()
      return
    }

    this.socket.onopen = () => {
      if (import.meta.env.DEV) {
        console.info('[WebSocket] 连接已建立')
      }
      this.state.value = 'connected'
      this.reconnectAttempts = 0
      this.startHeartbeat()
      this.flushMessageQueue()
    }

    this.socket.onmessage = (event: MessageEvent) => {
      const rawData = event.data as string

      // 处理 pong 响应
      if (rawData === 'pong' || rawData === '"pong"') {
        this.clearPongTimeout()
        return
      }

      // JSON 解析防护
      let parsed: WsServerMessage
      try {
        parsed = JSON.parse(rawData) as WsServerMessage
      } catch {
        if (import.meta.env.DEV) {
          console.warn('[WebSocket] 消息解析失败，非法 JSON:', rawData)
        }
        return
      }

      // 处理服务端 pong 消息（JSON 格式）
      if (parsed.msg_type === 'pong' || (parsed as Record<string, unknown>).type === 'pong') {
        this.clearPongTimeout()
        return
      }

      this.onMessage(parsed)
    }

    this.socket.onclose = (event: CloseEvent) => {
      if (import.meta.env.DEV) {
        console.info('[WebSocket] 连接已关闭', event.code, event.reason)
      }
      this.stopHeartbeat()
      this.state.value = 'disconnected'

      if (!this.manualClose && this.autoReconnect) {
        this.scheduleReconnect()
      }
    }

    this.socket.onerror = () => {
      if (import.meta.env.DEV) {
        console.warn('[WebSocket] 连接错误')
      }
      // onerror 之后会触发 onclose，重连逻辑由 onclose 处理
    }
  }

  /**
   * 发送消息
   * 如果连接未就绪，消息会被缓存到队列中，连接建立后自动发送
   */
  send(data: WsClientMessage): void {
    const jsonStr = JSON.stringify(data)

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(jsonStr)
    } else {
      // 连接未就绪，加入缓冲队列（带上限保护）
      if (this.messageQueue.length >= this.MAX_QUEUE_SIZE) {
        this.messageQueue.shift()
        if (import.meta.env.DEV) {
          console.warn('[WebSocket] 消息队列已满，丢弃最旧消息')
        }
      }
      this.messageQueue.push(jsonStr)
      if (import.meta.env.DEV) {
        console.info('[WebSocket] 消息已缓存，当前队列长度:', this.messageQueue.length)
      }
    }
  }

  /** 主动关闭连接 */
  close(): void {
    this.manualClose = true
    this.stopHeartbeat()
    this.clearReconnectTimer()
    this.messageQueue = []

    if (this.socket) {
      this.socket.close(1000, '客户端主动关闭')
      this.socket = null
    }

    this.state.value = 'disconnected'
    this.reconnectAttempts = 0
  }

  /** 安排重连 */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (import.meta.env.DEV) {
        console.warn('[WebSocket] 已达到最大重连次数，停止重连')
      }
      this.state.value = 'disconnected'
      return
    }

    this.state.value = 'reconnecting'
    const delay = this.getReconnectDelay()
    this.reconnectAttempts++

    if (import.meta.env.DEV) {
      console.info(`[WebSocket] 第 ${this.reconnectAttempts} 次重连，${delay}ms 后尝试`)
    }

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * 计算重连延迟
   * 前10次：指数退避 1s -> 30s
   * 后20次：固定 30s
   */
  private getReconnectDelay(): number {
    const maxDelay = 30000

    if (this.reconnectAttempts < 10) {
      // 指数退避：1000 * 2^n，上限 30s
      const exponentialDelay = 1000 * Math.pow(2, this.reconnectAttempts)
      return Math.min(exponentialDelay, maxDelay)
    }

    // 超过10次，固定30s
    return maxDelay
  }

  /** 启动心跳 */
  private startHeartbeat(): void {
    this.stopHeartbeat()

    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping' }))

        // 设置 pong 超时检测
        this.pongTimeout = setTimeout(() => {
          if (import.meta.env.DEV) {
            console.warn('[WebSocket] Pong 超时，关闭连接准备重连')
          }
          // 超时未收到 pong，关闭连接触发重连
          this.socket?.close(4000, 'Pong 超时')
        }, this.pongTimeoutMs)
      }
    }, this.heartbeatInterval)
  }

  /** 停止心跳 */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    this.clearPongTimeout()
  }

  /** 清除 Pong 超时定时器 */
  private clearPongTimeout(): void {
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout)
      this.pongTimeout = null
    }
  }

  /** 清除重连定时器 */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /** 刷新消息缓冲队列，将缓存的消息逐条发送 */
  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return

    if (import.meta.env.DEV) {
      console.info('[WebSocket] 发送缓冲队列消息，数量:', this.messageQueue.length)
    }

    while (this.messageQueue.length > 0) {
      const msg = this.messageQueue.shift()
      if (msg && this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(msg)
      }
    }
  }
}

// 保留向后兼容的别名
export { WebSocketClient as TaskWebSocket }
