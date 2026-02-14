/**
 * API 客户端
 * 封装所有与后端 API 的通信
 */
import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    console.error('API 请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API 响应错误:', error)
    const message = error.response?.data?.error || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// ==================== 策略相关 API ====================

/**
 * 获取所有可用策略
 */
export const getStrategies = async () => {
  return await apiClient.get('/api/strategies')
}

/**
 * 获取所有策略实例
 */
export const getStrategyInstances = async () => {
  return await apiClient.get('/api/strategy-instances')
}

/**
 * 获取指定策略实例详情
 */
export const getStrategyInstance = async (instanceId: string) => {
  return await apiClient.get(`/api/strategy-instances/${instanceId}`)
}

/**
 * 创建策略实例
 */
export const createStrategyInstance = async (data: {
  strategy_name: string
  config?: Record<string, any>
  instance_name?: string
}) => {
  return await apiClient.post('/api/strategy-instances', data)
}

/**
 * 启动策略实例
 */
export const startStrategyInstance = async (instanceId: string) => {
  return await apiClient.post(`/api/strategy-instances/${instanceId}/start`)
}

/**
 * 停止策略实例
 */
export const stopStrategyInstance = async (instanceId: string) => {
  return await apiClient.post(`/api/strategy-instances/${instanceId}/stop`)
}

/**
 * 删除策略实例
 */
export const deleteStrategyInstance = async (instanceId: string) => {
  return await apiClient.delete(`/api/strategy-instances/${instanceId}`)
}

/**
 * 更新策略实例配置
 */
export const updateStrategyConfig = async (instanceId: string, config: Record<string, any>) => {
  return await apiClient.put(`/api/strategy-instances/${instanceId}/config`, { config })
}

// ==================== 仓位相关 API ====================

/**
 * 获取所有仓位
 */
export const getPositions = async () => {
  return await apiClient.get('/api/positions')
}

/**
 * 获取指定交易对的仓位
 */
export const getPosition = async (symbol: string) => {
  return await apiClient.get(`/api/positions/${symbol}`)
}

// ==================== 账户相关 API ====================

/**
 * 获取账户余额
 */
export const getBalance = async () => {
  return await apiClient.get('/api/balance')
}

/**
 * 获取账户净值
 */
export const getEquity = async () => {
  return await apiClient.get('/api/equity')
}

/**
 * 获取 PnL 历史
 */
export const getPnLHistory = async (params?: { start_time?: number; end_time?: number }) => {
  return await apiClient.get('/api/pnl/history', { params })
}

// ==================== 订单相关 API ====================

/**
 * 获取活跃订单
 */
export const getActiveOrders = async () => {
  return await apiClient.get('/api/orders/active')
}

/**
 * 获取成交历史
 */
export const getTradeHistory = async (params?: { limit?: number; symbol?: string }) => {
  return await apiClient.get('/api/trades/history', { params })
}

/**
 * 获取订单簿
 */
export const getOrderBook = async (symbol: string, limit?: number) => {
  return await apiClient.get(`/api/orderbook/${symbol}`, { params: { limit } })
}

// ==================== 市场数据 API ====================

/**
 * 获取 Ticker
 */
export const getTicker = async (symbol: string) => {
  return await apiClient.get(`/api/ticker/${symbol}`)
}

/**
 * 获取 K 线数据
 */
export const getKlines = async (params: {
  symbol: string
  interval: string
  limit?: number
}) => {
  return await apiClient.get('/api/klines', { params })
}

// ==================== 系统相关 API ====================

/**
 * 获取系统状态
 */
export const getSystemStatus = async () => {
  return await apiClient.get('/api/status')
}

/**
 * 触发 Kill Switch（紧急停止）
 */
export const triggerKillSwitch = async () => {
  return await apiClient.post('/api/kill-switch')
}

/**
 * 获取实时统计数据
 */
export const getRealtimeStats = async () => {
  return await apiClient.get('/api/stats/realtime')
}

// ==================== 回测相关 API ====================

/**
 * 运行回测
 */
export const runBacktest = async (data: {
  strategy: string
  config: Record<string, any>
  start_time: number
  end_time: number
}) => {
  return await apiClient.post('/api/backtest/run', data)
}

/**
 * 获取回测结果
 */
export const getBacktestResult = async (backtestId: string) => {
  return await apiClient.get(`/api/backtest/${backtestId}`)
}

export default apiClient
