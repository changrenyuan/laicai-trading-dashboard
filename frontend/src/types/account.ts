/**
 * 账户类型定义
 */

export interface Account {
  account_id: string
  exchange: string
  equity: number
  total_balance: number
  available_balance: number
  pnl: number
  today_pnl: number
  unrealized_pnl: number
  leverage: number
  margin_ratio: number
}

export interface Balance {
  [currency: string]: {
    total: number
    available: number
    frozen: number
  }
}

export interface Position {
  symbol: string
  side: 'long' | 'short'
  size: number
  entry_price: number
  mark_price: number
  liquidation_price?: number
  unrealized_pnl: number
  realized_pnl: number
  leverage: number
  margin: number
  margin_ratio: number
}

export interface Trade {
  trade_id: string
  symbol: string
  side: 'buy' | 'sell'
  price: number
  amount: number
  fee: number
  fee_currency: string
  timestamp: number
  strategy_instance_id?: string
}

export interface Order {
  order_id: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'limit' | 'market' | 'stop'
  price: number
  amount: number
  filled: number
  remaining: number
  status: 'pending' | 'open' | 'filled' | 'canceled' | 'failed'
  timestamp: number
  strategy_instance_id?: string
}

export interface OrderBook {
  symbol: string
  bids: [number, number][] // [price, amount]
  asks: [number, number][] // [price, amount]
  timestamp: number
}

export interface Ticker {
  symbol: string
  last_price: number
  best_bid: number
  best_ask: number
  bid_qty: number
  ask_qty: number
  price_change_24h: number
  price_change_pct_24h: number
  volume_24h: number
  high_24h: number
  low_24h: number
  timestamp: number
}

export interface Kline {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface PnLData {
  timestamp: number
  equity: number
  realized_pnl: number
  unrealized_pnl: number
}
