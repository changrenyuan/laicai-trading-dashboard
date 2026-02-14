<template>
  <div class="pnl-page">
    <!-- 概览卡片 -->
    <el-row :gutter="24" class="overview-section">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon equity">
              <el-icon><Wallet /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">总权益</div>
              <div class="stat-value">${{ accountStore.totalEquity.toFixed(2) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon total-pnl">
              <el-icon><Money /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">累计盈亏</div>
              <div class="stat-value" :class="{ positive: accountStore.totalPnL >= 0, negative: accountStore.totalPnL < 0 }">
                {{ accountStore.totalPnL >= 0 ? '+' : '' }}${{ accountStore.totalPnL.toFixed(2) }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon today-pnl">
              <el-icon><Calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">今日盈亏</div>
              <div class="stat-value" :class="{ positive: accountStore.todayPnL >= 0, negative: accountStore.todayPnL < 0 }">
                {{ accountStore.todayPnL >= 0 ? '+' : '' }}${{ accountStore.todayPnL.toFixed(2) }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon trades">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">成交笔数</div>
              <div class="stat-value">{{ accountStore.trades.length }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="24" class="chart-section">
      <!-- PnL 曲线 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>权益曲线</span>
              <el-radio-group v-model="pnlTimeRange" size="small" @change="fetchPnLHistory">
                <el-radio-button label="1h">1小时</el-radio-button>
                <el-radio-button label="24h">24小时</el-radio-button>
                <el-radio-button label="7d">7天</el-radio-button>
                <el-radio-button label="30d">30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="pnlChartRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 每日盈亏柱状图 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>每日盈亏</span>
            </div>
          </template>
          <div ref="dailyChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 交易对盈亏 -->
    <el-row :gutter="24" class="symbol-section">
      <el-col :xs="24">
        <el-card shadow="hover">
          <template #header>
            <span>各交易对盈亏</span>
          </template>
          <el-table :data="symbolPnLData" stripe>
            <el-table-column prop="symbol" label="交易对" width="150" />
            <el-table-column prop="trades" label="成交数" width="100" />
            <el-table-column label="已实现盈亏" width="150">
              <template #default="{ row }">
                <span :class="{ positive: row.realized_pnl >= 0, negative: row.realized_pnl < 0 }">
                  {{ row.realized_pnl >= 0 ? '+' : '' }}${{ row.realized_pnl.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="未实现盈亏" width="150">
              <template #default="{ row }">
                <span :class="{ positive: row.unrealized_pnl >= 0, negative: row.unrealized_pnl < 0 }">
                  {{ row.unrealized_pnl >= 0 ? '+' : '' }}${{ row.unrealized_pnl.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="总盈亏" width="150">
              <template #default="{ row }">
                <span :class="{ positive: (row.realized_pnl + row.unrealized_pnl) >= 0, negative: (row.realized_pnl + row.unrealized_pnl) < 0 }">
                  {{ (row.realized_pnl + row.unrealized_pnl) >= 0 ? '+' : '' }}${{ (row.realized_pnl + row.unrealized_pnl).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="贡献度">
              <template #default="{ row }">
                <el-progress
                  :percentage="getContributionRatio(row)"
                  :color="getContributionColor(row)"
                  :stroke-width="12"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAccountStore } from '@/stores/account'
import { useStrategyStore } from '@/stores/strategy'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { Wallet, Money, Calendar, DataAnalysis } from '@element-plus/icons-vue'

const accountStore = useAccountStore()
const strategyStore = useStrategyStore()

const pnlTimeRange = ref('24h')
const pnlChartRef = ref<HTMLElement>()
const dailyChartRef = ref<HTMLElement>()
let pnlChart: ECharts | null = null
let dailyChart: ECharts | null = null
let refreshTimer: number | null = null

// 交易对盈亏数据（模拟）
const symbolPnLData = computed(() => {
  const positions = accountStore.positions
  const trades = accountStore.trades

  const symbolMap = new Map<string, {
    symbol: string
    trades: number
    realized_pnl: number
    unrealized_pnl: number
  }>()

  // 从仓位中获取未实现盈亏
  positions.forEach(p => {
    if (!symbolMap.has(p.symbol)) {
      symbolMap.set(p.symbol, {
        symbol: p.symbol,
        trades: 0,
        realized_pnl: 0,
        unrealized_pnl: 0,
      })
    }
    const data = symbolMap.get(p.symbol)!
    data.unrealized_pnl += p.unrealized_pnl
    data.realized_pnl += p.realized_pnl
  })

  // 从成交记录中统计交易数
  trades.forEach(t => {
    if (!symbolMap.has(t.symbol)) {
      symbolMap.set(t.symbol, {
        symbol: t.symbol,
        trades: 0,
        realized_pnl: 0,
        unrealized_pnl: 0,
      })
    }
    symbolMap.get(t.symbol)!.trades++
  })

  return Array.from(symbolMap.values())
})

// 获取贡献度比例
function getContributionRatio(row: any): number {
  const total = Math.abs(accountStore.totalPnL)
  if (total === 0) return 0
  return Math.abs(row.realized_pnl + row.unrealized_pnl) / total * 100
}

// 获取贡献度颜色
function getContributionColor(row: any): string {
  const pnl = row.realized_pnl + row.unrealized_pnl
  return pnl >= 0 ? '#10b981' : '#ef4444'
}

// 获取 PnL 历史
async function fetchPnLHistory() {
  try {
    const endTime = Math.floor(Date.now() / 1000)
    const timeRanges: Record<string, number> = {
      '1h': 3600,
      '24h': 86400,
      '7d': 604800,
      '30d': 2592000,
    }
    const startTime = endTime - timeRanges[pnlTimeRange.value]
    const data = await accountStore.fetchPnLHistory({ start_time: startTime, end_time: endTime })
    updatePnLChart(data)
    updateDailyChart(data)
  } catch (err) {
    console.error('获取 PnL 历史失败:', err)
  }
}

// 更新 PnL 曲线
function updatePnLChart(data: any[]) {
  if (!pnlChart || !data || data.length === 0) return

  const timestamps = data.map(d => new Date(d.timestamp * 1000).toLocaleString('zh-CN'))
  const equityData = data.map(d => d.equity)

  pnlChart.setOption({
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLabel: {
        formatter: (value: string) => {
          const parts = value.split(' ')
          if (pnlTimeRange.value === '1h') {
            return parts[1] // 只显示时间
          }
          return parts[0].substring(5) // 只显示月-日
        },
      },
    },
    yAxis: {
      type: 'value',
      name: '权益 (USDT)',
    },
    series: [
      {
        name: '权益',
        type: 'line',
        data: equityData,
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
            { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
          ]),
        },
        itemStyle: {
          color: '#1890ff',
        },
      },
    ],
  })
}

// 更新每日盈亏柱状图
function updateDailyChart(data: any[]) {
  if (!dailyChart || !data || data.length === 0) return

  // 按日期聚合数据
  const dailyMap = new Map<string, number>()
  data.forEach((d, index) => {
    const date = new Date(d.timestamp * 1000).toLocaleDateString('zh-CN')
    if (!dailyMap.has(date)) {
      dailyMap.set(date, d.equity)
    } else {
      dailyMap.set(date, d.equity)
    }
  })

  const dates = Array.from(dailyMap.keys())
  const pnlValues = dates.map(date => {
    const equities = data
      .filter(d => new Date(d.timestamp * 1000).toLocaleDateString('zh-CN') === date)
      .map(d => d.equity)
    const first = equities[0] || 0
    const last = equities[equities.length - 1] || 0
    return last - first
  })

  dailyChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        formatter: (value: string) => value.substring(5),
      },
    },
    yAxis: {
      type: 'value',
      name: '盈亏 (USDT)',
    },
    series: [
      {
        name: '盈亏',
        type: 'bar',
        data: pnlValues,
        itemStyle: {
          color: (params: any) => {
            return params.value >= 0 ? '#10b981' : '#ef4444'
          },
        },
      },
    ],
  })
}

// 初始化图表
function initCharts() {
  // PnL 曲线
  if (pnlChartRef.value) {
    pnlChart = echarts.init(pnlChartRef.value)
    pnlChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          return `${params[0].name}<br/>权益: $${params[0].value.toFixed(2)}`
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: [],
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        name: '权益 (USDT)',
      },
      series: [
        {
          name: '权益',
          type: 'line',
          data: [],
          smooth: true,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
            ]),
          },
          itemStyle: {
            color: '#1890ff',
          },
        },
      ],
    })
  }

  // 每日盈亏柱状图
  if (dailyChartRef.value) {
    dailyChart = echarts.init(dailyChartRef.value)
    dailyChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          return `${params[0].name}<br/>盈亏: $${params[0].value.toFixed(2)}`
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: [],
      },
      yAxis: {
        type: 'value',
        name: '盈亏 (USDT)',
      },
      series: [
        {
          name: '盈亏',
          type: 'bar',
          data: [],
        },
      ],
    })
  }
}

// 窗口大小改变时重新渲染图表
function handleResize() {
  pnlChart?.resize()
  dailyChart?.resize()
}

onMounted(async () => {
  await Promise.all([
    strategyStore.fetchStrategies(),
    accountStore.init(),
    accountStore.fetchTradeHistory({ limit: 100 }),
  ])

  initCharts()
  fetchPnLHistory()

  window.addEventListener('resize', handleResize)

  // 定时刷新数据
  refreshTimer = window.setInterval(async () => {
    await accountStore.fetchAccount()
    fetchPnLHistory()
  }, 10000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  pnlChart?.dispose()
  dailyChart?.dispose()
})
</script>

<style scoped>
.pnl-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.overview-section {
  margin-bottom: 0;
}

.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
}

.stat-icon.equity {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.total-pnl {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.today-pnl {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.trades {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.stat-value.positive {
  color: #10b981;
}

.stat-value.negative {
  color: #ef4444;
}

.chart-section {
  margin-bottom: 0;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.symbol-section {
  margin-bottom: 0;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}
</style>
