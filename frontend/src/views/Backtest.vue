<template>
  <div class="backtest-page">
    <el-row :gutter="24">
      <!-- 左侧：回测配置 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <span>回测配置</span>
          </template>

          <el-form :model="backtestForm" label-width="120px">
            <el-form-item label="策略类型">
              <el-select v-model="backtestForm.strategy" placeholder="选择策略" style="width: 100%">
                <el-option
                  v-for="strategy in availableStrategies"
                  :key="strategy.name"
                  :label="strategy.name"
                  :value="strategy.name"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="开始时间">
              <el-date-picker
                v-model="backtestForm.start_time"
                type="datetime"
                placeholder="选择开始时间"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="结束时间">
              <el-date-picker
                v-model="backtestForm.end_time"
                type="datetime"
                placeholder="选择结束时间"
                style="width: 100%"
              />
            </el-form-item>

            <el-divider content-position="left">策略参数</el-divider>

            <el-form-item label="交易对">
              <el-input v-model="backtestForm.config.symbol" placeholder="如: BTC-USDT" />
            </el-form-item>

            <el-form-item label="交易所">
              <el-select v-model="backtestForm.config.exchange" placeholder="选择交易所" style="width: 100%">
                <el-option label="OKX" value="okx" />
                <el-option label="Binance" value="binance" />
              </el-select>
            </el-form-item>

            <el-form-item label="下单数量">
              <el-input-number
                v-model="backtestForm.config.order_amount"
                :min="0.0001"
                :precision="4"
                :step="0.0001"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="价差">
              <el-input-number
                v-model="backtestForm.config.spread"
                :min="0"
                :precision="4"
                :step="0.0001"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="库存目标">
              <el-slider
                v-model="backtestForm.config.inventory_target_base_pct"
                :min="0"
                :max="100"
                :step="1"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :icon="VideoPlay"
                @click="runBacktest"
                :loading="running"
                style="width: 100%"
              >
                运行回测
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：回测结果 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover" v-if="!backtestResult">
          <div class="placeholder">
            <el-icon><DataAnalysis /></el-icon>
            <p>配置参数并运行回测后，结果将显示在这里</p>
          </div>
        </el-card>

        <div v-if="backtestResult" class="result-section">
          <!-- 概览卡片 -->
          <el-row :gutter="16" class="overview-cards">
            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" class="stat-card">
                <div class="stat-value" :class="{ positive: backtestResult.total_pnl >= 0, negative: backtestResult.total_pnl < 0 }">
                  {{ backtestResult.total_pnl >= 0 ? '+' : '' }}{{ backtestResult.total_pnl.toFixed(2) }}
                </div>
                <div class="stat-label">总盈亏</div>
              </el-card>
            </el-col>

            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" class="stat-card">
                <div class="stat-value">
                  {{ backtestResult.total_trades }}
                </div>
                <div class="stat-label">成交笔数</div>
              </el-card>
            </el-col>

            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" class="stat-card">
                <div class="stat-value">
                  {{ backtestResult.win_rate.toFixed(2) }}%
                </div>
                <div class="stat-label">胜率</div>
              </el-card>
            </el-col>

            <el-col :xs="12" :sm="6">
              <el-card shadow="hover" class="stat-card">
                <div class="stat-value">
                  {{ backtestResult.sharpe_ratio.toFixed(2) }}
                </div>
                <div class="stat-label">夏普比率</div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 回测曲线 -->
          <el-card shadow="hover" class="mt-16">
            <template #header>
              <span>权益曲线</span>
            </template>
            <div ref="backtestChartRef" class="chart-container"></div>
          </el-card>

          <!-- 详细统计 -->
          <el-card shadow="hover" class="mt-16">
            <template #header>
              <span>详细统计</span>
            </template>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="总收益">
                <span :class="{ positive: backtestResult.total_return >= 0, negative: backtestResult.total_return < 0 }">
                  {{ backtestResult.total_return >= 0 ? '+' : '' }}{{ backtestResult.total_return.toFixed(2) }}%
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="最大回撤">
                {{ backtestResult.max_drawdown.toFixed(2) }}%
              </el-descriptions-item>
              <el-descriptions-item label="盈亏比">
                {{ backtestResult.profit_factor.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="平均盈利">
                {{ backtestResult.avg_win.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="平均亏损">
                {{ backtestResult.avg_loss.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="期望收益">
                {{ backtestResult.expected_return.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="年化收益">
                {{ backtestResult.annualized_return.toFixed(2) }}%
              </el-descriptions-item>
              <el-descriptions-item label="波动率">
                {{ backtestResult.volatility.toFixed(2) }}%
              </el-descriptions-item>
              <el-descriptions-item label="总手续费">
                {{ backtestResult.total_fees.toFixed(2) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, DataAnalysis } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import * as api from '@/api/client'

const backtestForm = ref({
  strategy: '',
  start_time: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
  end_time: new Date(),
  config: {
    symbol: 'BTC-USDT',
    exchange: 'okx',
    order_amount: 0.001,
    spread: 0.001,
    inventory_target_base_pct: 50,
  },
})

const availableStrategies = ref([
  { name: 'MarketMakingStrategy', description: '做市策略' },
  { name: 'PureMarketMakingStrategy', description: '纯做市策略' },
  { name: 'AvellanedaMarketMakingStrategy', description: 'Avellaneda 做市策略' },
])

const running = ref(false)
const backtestResult = ref<any>(null)
const backtestChartRef = ref<HTMLElement>()
let backtestChart: ECharts | null = null

// 运行回测
async function runBacktest() {
  if (!backtestForm.value.strategy) {
    ElMessage.warning('请选择策略类型')
    return
  }

  running.value = true
  try {
    const result = await api.runBacktest({
      strategy: backtestForm.value.strategy,
      config: backtestForm.value.config,
      start_time: Math.floor(backtestForm.value.start_time.getTime() / 1000),
      end_time: Math.floor(backtestForm.value.end_time.getTime() / 1000),
    })

    backtestResult.value = result
    updateBacktestChart()
    ElMessage.success('回测完成')
  } catch (err) {
    console.error('回测失败:', err)
    ElMessage.error('回测失败')
  } finally {
    running.value = false
  }
}

// 更新回测图表
function updateBacktestChart() {
  if (!backtestChart || !backtestResult.value) return

  const data = backtestResult.value.equity_curve || []
  const timestamps = data.map((d: any) => new Date(d.timestamp * 1000).toLocaleString('zh-CN'))
  const equityValues = data.map((d: any) => d.equity)

  backtestChart.setOption({
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
      data: timestamps,
      axisLabel: {
        formatter: (value: string) => {
          return value.split(' ')[0].substring(5)
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
        data: equityValues,
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.05)' },
          ]),
        },
        itemStyle: {
          color: '#10b981',
        },
      },
    ],
  })
}

// 初始化图表
function initChart() {
  if (backtestChartRef.value) {
    backtestChart = echarts.init(backtestChartRef.value)
    backtestChart.setOption({
      tooltip: {
        trigger: 'axis',
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
              { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.05)' },
            ]),
          },
          itemStyle: {
            color: '#10b981',
          },
        },
      ],
    })
  }
}

// 窗口大小改变时重新渲染图表
function handleResize() {
  backtestChart?.resize()
}

onMounted(async () => {
  initChart()
  window.addEventListener('resize', handleResize)

  try {
    availableStrategies.value = await api.getStrategies()
  } catch (err) {
    console.error('获取策略列表失败:', err)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  backtestChart?.dispose()
})
</script>

<style scoped>
.backtest-page {
  padding: 0;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #999;
}

.placeholder .el-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.placeholder p {
  font-size: 16px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-cards {
  margin-bottom: 0;
}

.stat-card {
  text-align: center;
  padding: 16px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 8px;
}

.stat-value.positive {
  color: #10b981;
}

.stat-value.negative {
  color: #ef4444;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.mt-16 {
  margin-top: 16px;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}
</style>
