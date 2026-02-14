<template>
  <div class="dashboard">
    <!-- 概览卡片 -->
    <el-row :gutter="24" class="overview-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon equity">
              <el-icon><Wallet /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">总权益</div>
              <div class="stat-value">${{ accountStore.totalEquity.toFixed(2) }}</div>
              <div class="stat-change" :class="{ positive: accountStore.todayPnL >= 0, negative: accountStore.todayPnL < 0 }">
                <el-icon><component :is="accountStore.todayPnL >= 0 ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
                {{ accountStore.todayPnL >= 0 ? '+' : '' }}{{ accountStore.todayPnL.toFixed(2) }} 今日
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon pnl">
              <el-icon><Money /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">累计 PnL</div>
              <div class="stat-value" :class="{ positive: accountStore.totalPnL >= 0, negative: accountStore.totalPnL < 0 }">
                {{ accountStore.totalPnL >= 0 ? '+' : '' }}${{ accountStore.totalPnL.toFixed(2) }}
              </div>
              <div class="stat-change">
                实盘盈亏
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon strategies">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">运行策略</div>
              <div class="stat-value">{{ strategyStore.runningCount }} / {{ strategyStore.strategies.length }}</div>
              <div class="stat-change">
                活跃 / 总数
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon positions">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">持仓数量</div>
              <div class="stat-value">{{ activePositionsCount }}</div>
              <div class="stat-change">
                {{ longPositions }} 多 / {{ shortPositions }} 空
              </div>
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
              <span>PnL 曲线</span>
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

      <!-- 资产分布 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>资产分布</span>
            </div>
          </template>
          <div ref="balanceChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 策略列表和最新订单 -->
    <el-row :gutter="24" class="bottom-section">
      <!-- 策略列表 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>运行中的策略</span>
              <el-button type="primary" size="small" @click="$router.push('/strategies')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="strategyStore.runningStrategies" stripe>
            <el-table-column prop="instance_name" label="名称" width="150" />
            <el-table-column prop="strategy_name" label="策略类型" width="120" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="盈亏" width="100">
              <template #default="{ row }">
                <span :class="{ positive: (row.stats?.realized_pnl || 0) >= 0, negative: (row.stats?.realized_pnl || 0) < 0 }">
                  {{ (row.stats?.realized_pnl || 0) >= 0 ? '+' : '' }}{{ (row.stats?.realized_pnl || 0).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button-group size="small">
                  <el-button type="primary" @click="$router.push(`/strategies/${row.instance_id}`)">
                    详情
                  </el-button>
                  <el-button type="danger" @click="handleStopStrategy(row.instance_id)">
                    停止
                  </el-button>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 最新成交 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最新成交</span>
              <el-button type="primary" size="small" @click="$router.push('/orders')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentTrades" stripe max-height="300">
            <el-table-column prop="symbol" label="交易对" width="100" />
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <el-tag :type="row.side === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.side === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="100" />
            <el-table-column prop="amount" label="数量" width="100" />
            <el-table-column prop="timestamp" label="时间" width="100">
              <template #default="{ row }">
                {{ formatTime(row.timestamp) }}
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
import { useStrategyStore } from '@/stores/strategy'
import { useAccountStore } from '@/stores/account'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { Wallet, Money, DataAnalysis, Document, ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const strategyStore = useStrategyStore()
const accountStore = useAccountStore()

const pnlTimeRange = ref('24h')
const pnlChartRef = ref<HTMLElement>()
const balanceChartRef = ref<HTMLElement>()
let pnlChart: ECharts | null = null
let balanceChart: ECharts | null = null
let refreshTimer: number | null = null

// 活跃持仓数量
const activePositionsCount = computed(() => {
  return accountStore.positions.filter(p => Math.abs(p.size) > 0).length
})

const longPositions = computed(() => {
  return accountStore.positions.filter(p => p.size > 0).length
})

const shortPositions = computed(() => {
  return accountStore.positions.filter(p => p.size < 0).length
})

// 最新成交（取前10条）
const recentTrades = computed(() => {
  return accountStore.trades.slice(0, 10)
})

// 获取状态类型
function getStatusType(status: string) {
  const types: Record<string, any> = {
    running: 'success',
    stopped: 'info',
    paused: 'warning',
    error: 'danger',
  }
  return types[status] || 'info'
}

// 获取状态文本
function getStatusText(status: string) {
  const texts: Record<string, string> = {
    running: '运行中',
    stopped: '已停止',
    paused: '暂停',
    error: '错误',
  }
  return texts[status] || status
}

// 格式化时间
function formatTime(timestamp: number) {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 停止策略
async function handleStopStrategy(instanceId: string) {
  try {
    await ElMessageBox.confirm('确定要停止此策略吗？', '确认', {
      type: 'warning',
    })
    await strategyStore.stopStrategy(instanceId)
    ElMessage.success('策略已停止')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('停止策略失败')
    }
  }
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
  } catch (err) {
    console.error('获取 PnL 历史失败:', err)
  }
}

// 更新 PnL 图表
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
          return value.split(' ')[1]
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

  // 资产分布饼图
  if (balanceChartRef.value) {
    balanceChart = echarts.init(balanceChartRef.value)
    updateBalanceChart()
  }
}

// 更新资产分布图表
function updateBalanceChart() {
  if (!balanceChart || !accountStore.balance) return

  const data = Object.entries(accountStore.balance)
    .filter(([_, b]) => b.total > 0)
    .map(([currency, b]) => ({
      name: currency.toUpperCase(),
      value: b.total,
    }))

  balanceChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: ${c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
    },
    series: [
      {
        name: '资产分布',
        type: 'pie',
        radius: '50%',
        data: data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  })
}

// 窗口大小改变时重新渲染图表
function handleResize() {
  pnlChart?.resize()
  balanceChart?.resize()
}

onMounted(async () => {
  await Promise.all([
    strategyStore.fetchStrategies(),
    accountStore.init(),
  ])
  await accountStore.fetchTradeHistory({ limit: 10 })

  initCharts()
  fetchPnLHistory()

  window.addEventListener('resize', handleResize)

  // 定时刷新数据
  refreshTimer = window.setInterval(async () => {
    await Promise.all([
      strategyStore.fetchStrategies(),
      accountStore.fetchAccount(),
      accountStore.fetchTradeHistory({ limit: 10 }),
    ])
    fetchPnLHistory()
    updateBalanceChart()
  }, 10000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  pnlChart?.dispose()
  balanceChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.overview-cards {
  margin-bottom: 0;
}

.stat-card {
  height: 140px;
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

.stat-icon.pnl {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.strategies {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.positions {
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
  margin-bottom: 4px;
}

.stat-value.positive {
  color: #10b981;
}

.stat-value.negative {
  color: #ef4444;
}

.stat-change {
  font-size: 12px;
  color: #9ca3af;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-change.positive {
  color: #10b981;
}

.stat-change.negative {
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

.bottom-section {
  margin-bottom: 0;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}
</style>
