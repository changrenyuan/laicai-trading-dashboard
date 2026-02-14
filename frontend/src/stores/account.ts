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
    try {
      account.value = await api.getEquity()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取账户信息失败'
      console.error('获取账户信息失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchPositions() {
    try {
      positions.value = await api.getPositions()
    } catch (err) {
      console.error('获取仓位失败:', err)
      throw err
    }
  }

  async function fetchBalance() {
    try {
      balance.value = await api.getBalance()
    } catch (err) {
      console.error('获取余额失败:', err)
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
    await Promise.all([
      fetchAccount(),
      fetchPositions(),
      fetchBalance(),
    ])
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
