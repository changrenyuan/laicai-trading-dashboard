/**
 * 账户状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Account, Position, Trade, Balance } from '@/types/account'
import * as api from '@/api/client'

export const useAccountStore = defineStore('account', () => {
  // 状态
  const account = ref<Account | null>(null)
  const positions = ref<Position[]>([])
  const trades = ref<Trade[]>([])
  const balance = ref<Balance | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const totalEquity = computed(() => account.value?.equity ?? 0)
  const totalBalance = computed(() => {
    if (!balance.value) return 0
    return Object.values(balance.value).reduce((sum: number, b: any) => sum + (b?.total ?? 0), 0)
  })
  const totalPnL = computed(() => account.value?.pnl ?? 0)
  const todayPnL = computed(() => account.value?.today_pnl ?? 0)

  // 操作
  async function fetchAccount() {
    loading.value = true
    error.value = null
    console.log('[Account Store] 开始获取账户权益...')
    try {
      console.log('[Account Store] 调用 API: getEquity()')
      account.value = await api.getEquity()
      console.log('[Account Store] 账户权益获取成功:', account.value)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取账户信息失败'
      console.error('[Account Store] 获取账户权益失败:', err)
      console.error('[Account Store] 错误详情:', JSON.stringify(err, null, 2))
    } finally {
      loading.value = false
    }
  }

  async function fetchPositions() {
    console.log('[Account Store] 开始获取仓位...')
    try {
      console.log('[Account Store] 调用 API: getPositions()')
      positions.value = await api.getPositions()
      console.log('[Account Store] 仓位获取成功，数量:', positions.value.length)
    } catch (err) {
      console.error('[Account Store] 获取仓位失败:', err)
      console.error('[Account Store] 错误详情:', JSON.stringify(err, null, 2))
      throw err
    }
  }

  async function fetchBalance() {
    console.log('[Account Store] 开始获取余额...')
    try {
      console.log('[Account Store] 调用 API: getBalance()')
      balance.value = await api.getBalance()
      console.log('[Account Store] 余额获取成功:', balance.value)
    } catch (err) {
      console.error('[Account Store] 获取余额失败:', err)
      console.error('[Account Store] 错误详情:', JSON.stringify(err, null, 2))
      throw err
    }
  }

  async function fetchTradeHistory(params?: { limit?: number; symbol?: string }) {
    try {
      trades.value = await api.getTradeHistory(params)
    } catch (err) {
      console.error('获取成交历史失败:', err)
      throw err
    }
  }

  async function fetchPnLHistory(params?: { start_time?: number; end_time?: number }) {
    try {
      return await api.getPnLHistory(params)
    } catch (err) {
      console.error('获取 PnL 历史失败:', err)
      throw err
    }
  }

  function getPositionBySymbol(symbol: string): Position | undefined {
    return positions.value.find(p => p.symbol === symbol)
  }

  // 初始化
  async function init() {
    console.log('[Account Store] ========== 初始化账户信息 ==========')
    console.log('[Account Store] 并行获取账户权益、仓位和余额...')
    try {
      await Promise.all([
        fetchAccount(),
        fetchPositions(),
        fetchBalance(),
      ])
      console.log('[Account Store] ========== 初始化完成 ==========')
      console.log('[Account Store] 当前账户权益:', totalEquity.value)
      console.log('[Account Store] 当前总余额:', totalBalance.value)
      console.log('[Account Store] 今日 PnL:', todayPnL.value)
    } catch (err) {
      console.error('[Account Store] 初始化过程中发生错误:', err)
    }
  }

  return {
    // 状态
    account,
    positions,
    trades,
    balance,
    loading,
    error,
    // 计算属性
    totalEquity,
    totalBalance,
    totalPnL,
    todayPnL,
    // 操作
    fetchAccount,
    fetchPositions,
    fetchBalance,
    fetchTradeHistory,
    fetchPnLHistory,
    getPositionBySymbol,
    init,
  }
})
