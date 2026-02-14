/**
 * WebSocket 客户端
 * 用于实时接收日志和订单数据
 */

export type LogMessage = {
  timestamp: number
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  logger: string
  message: string
}

export type OrderUpdate = {
  order_id: string
  symbol: string
  side: 'buy' | 'sell'
  price: number
  amount: number
  filled: number
  status: string
  timestamp: number
}

export type WSMessage = {
  type: 'log' | 'order' | 'trade' | 'ticker' | 'position'
  data: LogMessage | OrderUpdate | any
}

type WSMessageHandler = (message: WSMessage) => void
type WSConnectionHandler = (connected: boolean) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private messageHandlers: Set<WSMessageHandler> = new Set()
  private connectionHandlers: Set<WSConnectionHandler> = new Set()

  constructor(url: string) {
    this.url = url
  }

  /**
   * 连接 WebSocket
   */
  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      console.log('WebSocket 已连接或正在连接中')
      return
    }

    console.log('正在连接 WebSocket:', this.url)
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('WebSocket 连接成功')
      this.reconnectAttempts = 0
      this.notifyConnectionHandlers(true)
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        this.notifyMessageHandlers(message)
      } catch (error) {
        console.error('解析 WebSocket 消息失败:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket 错误:', error)
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket 连接关闭:', event.code, event.reason)
      this.notifyConnectionHandlers(false)

      // 自动重连
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
        console.log(`将在 ${delay / 1000} 秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        this.reconnectTimer = window.setTimeout(() => {
          this.connect()
        }, delay)
      } else {
        console.error('达到最大重连次数，停止重连')
      }
    }
  }

  /**
   * 断开 WebSocket 连接
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 发送消息
   */
  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket 未连接，无法发送消息')
    }
  }

  /**
   * 订阅消息
   */
  onMessage(handler: WSMessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => {
      this.messageHandlers.delete(handler)
    }
  }

  /**
   * 订阅连接状态变化
   */
  onConnection(handler: WSConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    // 立即通知当前状态
    handler(this.isConnected())
    return () => {
      this.connectionHandlers.delete(handler)
    }
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  private notifyMessageHandlers(message: WSMessage): void {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message)
      } catch (error) {
        console.error('消息处理错误:', error)
      }
    })
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected)
      } catch (error) {
        console.error('连接状态处理错误:', error)
      }
    })
  }
}

// 创建 WebSocket 客户端实例
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:5000/ws/logs'
export const wsClient = new WebSocketClient(WS_URL)

export default WebSocketClient
