/**
 * 策略类型定义
 */

export type StrategyStatus = 'running' | 'stopped' | 'paused' | 'error'

export interface StrategyInstance {
  instance_id: string
  instance_name: string
  strategy_name: string
  status: StrategyStatus
  config: Record<string, any>
  created_at: number
  started_at?: number
  stopped_at?: number
  error_message?: string
  // 策略运行时统计
  stats?: {
    total_orders: number
    total_trades: number
    realized_pnl: number
    unrealized_pnl: number
  }
}

export interface StrategyConfig {
  // 基础配置
  symbol: string
  exchange: string
  // 交易参数
  order_amount: number
  order_price: number
  // 策略参数
  spread?: number
  min_spread?: number
  max_spread?: number
  inventory_target_base_amount?: number
  inventory_target_base_pct?: number
  // 风控参数
  order_refresh_time?: number
  order_refresh_tolerance_pct?: number
  filled_order_delay?: number
  // 其他参数
  [key: string]: any
}
