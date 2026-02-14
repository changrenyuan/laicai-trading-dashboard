/**
 * 策略状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { StrategyInstance, StrategyStatus } from '@/types/strategy'
import * as api from '@/api/client'

export const useStrategyStore = defineStore('strategy', () => {
  // 状态
  const strategies = ref<StrategyInstance[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const runningStrategies = computed(() =>
    strategies.value.filter(s => s.status === 'running')
  )
  const stoppedStrategies = computed(() =>
    strategies.value.filter(s => s.status === 'stopped')
  )
  const runningCount = computed(() => runningStrategies.value.length)
  const stoppedCount = computed(() => stoppedStrategies.value.length)

  // 操作
  async function fetchStrategies() {
    loading.value = true
    error.value = null
    try {
      strategies.value = await api.getStrategyInstances()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取策略列表失败'
      console.error('获取策略列表失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchStrategy(instanceId: string) {
    try {
      const instance = await api.getStrategyInstance(instanceId)
      const index = strategies.value.findIndex(s => s.instance_id === instanceId)
      if (index !== -1) {
        strategies.value[index] = instance
      } else {
        strategies.value.push(instance)
      }
      return instance
    } catch (err) {
      console.error('获取策略详情失败:', err)
      throw err
    }
  }

  async function createStrategy(data: {
    strategy_name: string
    config?: Record<string, any>
    instance_name?: string
  }) {
    try {
      const instance = await api.createStrategyInstance(data)
      strategies.value.push(instance)
      return instance
    } catch (err) {
      console.error('创建策略失败:', err)
      throw err
    }
  }

  async function startStrategy(instanceId: string) {
    try {
      const instance = await api.startStrategyInstance(instanceId)
      updateStrategyStatus(instanceId, 'running')
      return instance
    } catch (err) {
      console.error('启动策略失败:', err)
      throw err
    }
  }

  async function stopStrategy(instanceId: string) {
    try {
      const instance = await api.stopStrategyInstance(instanceId)
      updateStrategyStatus(instanceId, 'stopped')
      return instance
    } catch (err) {
      console.error('停止策略失败:', err)
      throw err
    }
  }

  async function deleteStrategy(instanceId: string) {
    try {
      await api.deleteStrategyInstance(instanceId)
      strategies.value = strategies.value.filter(s => s.instance_id !== instanceId)
    } catch (err) {
      console.error('删除策略失败:', err)
      throw err
    }
  }

  async function updateConfig(instanceId: string, config: Record<string, any>) {
    try {
      await api.updateStrategyConfig(instanceId, config)
      const index = strategies.value.findIndex(s => s.instance_id === instanceId)
      if (index !== -1 && strategies.value[index]) {
        strategies.value[index].config = { ...strategies.value[index].config, ...config }
      }
    } catch (err) {
      console.error('更新配置失败:', err)
      throw err
    }
  }

  function updateStrategyStatus(instanceId: string, status: StrategyStatus) {
    const index = strategies.value.findIndex(s => s.instance_id === instanceId)
    if (index !== -1) {
      strategies.value[index].status = status
    }
  }

  function getStrategyById(instanceId: string): StrategyInstance | undefined {
    return strategies.value.find(s => s.instance_id === instanceId)
  }

  // 初始化
  async function init() {
    await fetchStrategies()
  }

  return {
    // 状态
    strategies,
    loading,
    error,
    // 计算属性
    runningStrategies,
    stoppedStrategies,
    runningCount,
    stoppedCount,
    // 操作
    fetchStrategies,
    fetchStrategy,
    createStrategy,
    startStrategy,
    stopStrategy,
    deleteStrategy,
    updateConfig,
    getStrategyById,
    init,
  }
})
