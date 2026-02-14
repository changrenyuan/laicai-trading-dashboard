<template>
  <div class="strategies-page">
    <el-row :gutter="24">
      <!-- 左侧：策略列表 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>策略实例</span>
              <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
                新建策略
              </el-button>
            </div>
          </template>

          <el-table :data="strategyStore.strategies" stripe v-loading="strategyStore.loading">
            <el-table-column prop="instance_name" label="名称" width="150" />
            <el-table-column prop="strategy_name" label="策略类型" width="150" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="配置" min-width="200">
              <template #default="{ row }">
                <div class="config-preview">
                  <span>交易对: {{ row.config?.symbol || '-' }}</span>
                  <span>交易所: {{ row.config?.exchange || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="盈亏" width="100">
              <template #default="{ row }">
                <span :class="{ positive: (row.stats?.realized_pnl || 0) >= 0, negative: (row.stats?.realized_pnl || 0) < 0 }">
                  {{ (row.stats?.realized_pnl || 0) >= 0 ? '+' : '' }}{{ (row.stats?.realized_pnl || 0).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button-group size="small">
                  <el-button type="primary" @click="handleViewDetail(row)">
                    详情
                  </el-button>
                  <el-button
                    v-if="row.status === 'stopped'"
                    type="success"
                    :icon="VideoPlay"
                    @click="handleStart(row.instance_id)"
                  >
                    启动
                  </el-button>
                  <el-button
                    v-if="row.status === 'running'"
                    type="warning"
                    :icon="VideoPause"
                    @click="handleStop(row.instance_id)"
                  >
                    停止
                  </el-button>
                  <el-button type="danger" :icon="Delete" @click="handleDelete(row.instance_id)">
                    删除
                  </el-button>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：策略统计 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <span>策略统计</span>
          </template>
          <div class="strategy-stats">
            <div class="stat-item">
              <div class="stat-label">运行中</div>
              <div class="stat-value running">{{ strategyStore.runningCount }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">已停止</div>
              <div class="stat-value stopped">{{ strategyStore.stoppedCount }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">总订单数</div>
              <div class="stat-value">{{ totalOrders }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">总成交数</div>
              <div class="stat-value">{{ totalTrades }}</div>
            </div>
          </div>
        </el-card>

        <el-card shadow="hover" class="mt-24">
          <template #header>
            <span>盈亏排行</span>
          </template>
          <el-table :data="topStrategies" stripe>
            <el-table-column prop="instance_name" label="策略" />
            <el-table-column label="盈亏" width="100">
              <template #default="{ row }">
                <span :class="{ positive: (row.stats?.realized_pnl || 0) >= 0, negative: (row.stats?.realized_pnl || 0) < 0 }">
                  {{ (row.stats?.realized_pnl || 0) >= 0 ? '+' : '' }}{{ (row.stats?.realized_pnl || 0).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 创建策略对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建策略实例"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="120px">
        <el-form-item label="策略类型" prop="strategy_name">
          <el-select v-model="createForm.strategy_name" placeholder="选择策略类型" style="width: 100%">
            <el-option
              v-for="strategy in availableStrategies"
              :key="strategy.name"
              :label="strategy.name"
              :value="strategy.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="实例名称" prop="instance_name">
          <el-input
            v-model="createForm.instance_name"
            placeholder="输入实例名称"
          />
        </el-form-item>

        <div v-if="createForm.strategy_name">
          <el-divider content-position="left">基础配置</el-divider>
          <el-form-item label="交易对" prop="symbol">
            <el-input v-model="createForm.config.symbol" placeholder="如: BTC-USDT" />
          </el-form-item>

          <el-form-item label="交易所" prop="exchange">
            <el-select v-model="createForm.config.exchange" placeholder="选择交易所" style="width: 100%">
              <el-option label="OKX" value="okx" />
              <el-option label="Binance" value="binance" />
              <el-option label="Bybit" value="bybit" />
            </el-select>
          </el-form-item>

          <el-form-item label="下单数量" prop="order_amount">
            <el-input-number
              v-model="createForm.config.order_amount"
              :min="0.0001"
              :precision="4"
              :step="0.0001"
              style="width: 100%"
            />
          </el-form-item>

          <el-divider content-position="left">策略参数</el-divider>

          <el-form-item label="价差" prop="spread">
            <el-input-number
              v-model="createForm.config.spread"
              :min="0"
              :precision="4"
              :step="0.0001"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item label="库存目标" prop="inventory_target_base_pct">
            <el-slider
              v-model="createForm.config.inventory_target_base_pct"
              :min="0"
              :max="100"
              :step="1"
            />
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateStrategy" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 策略详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="`策略详情 - ${selectedStrategy?.instance_name}`"
      width="800px"
    >
      <el-descriptions :column="2" border v-if="selectedStrategy">
        <el-descriptions-item label="实例ID">{{ selectedStrategy.instance_id }}</el-descriptions-item>
        <el-descriptions-item label="策略类型">{{ selectedStrategy.strategy_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(selectedStrategy.status)">
            {{ getStatusText(selectedStrategy.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(selectedStrategy.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="总订单数">{{ selectedStrategy.stats?.total_orders || 0 }}</el-descriptions-item>
        <el-descriptions-item label="总成交数">{{ selectedStrategy.stats?.total_trades || 0 }}</el-descriptions-item>
        <el-descriptions-item label="已实现盈亏" :span="2">
          <span :class="{ positive: (selectedStrategy.stats?.realized_pnl || 0) >= 0, negative: (selectedStrategy.stats?.realized_pnl || 0) < 0 }">
            {{ (selectedStrategy.stats?.realized_pnl || 0) >= 0 ? '+' : '' }}{{ (selectedStrategy.stats?.realized_pnl || 0).toFixed(2) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">配置详情</el-divider>
      <el-descriptions :column="2" border>
        <el-descriptions-item
          v-for="(value, key) in selectedStrategy.config"
          :key="key"
          :label="key"
          :span="1"
        >
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useStrategyStore } from '@/stores/strategy'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, VideoPlay, VideoPause, Delete } from '@element-plus/icons-vue'
import * as api from '@/api/client'
import type { StrategyInstance } from '@/types/strategy'

const strategyStore = useStrategyStore()

const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const selectedStrategy = ref<StrategyInstance | null>(null)
const createFormRef = ref<FormInstance>()
const creating = ref(false)

const createForm = ref({
  strategy_name: '',
  instance_name: '',
  config: {
    symbol: '',
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
  { name: 'CrossExchangeMarketMakingStrategy', description: '跨交易所套利' },
])

const createRules: FormRules = {
  strategy_name: [{ required: true, message: '请选择策略类型', trigger: 'change' }],
  instance_name: [{ required: true, message: '请输入实例名称', trigger: 'blur' }],
  symbol: [{ required: true, message: '请输入交易对', trigger: 'blur' }],
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
}

// 总订单数
const totalOrders = computed(() => {
  return strategyStore.strategies.reduce((sum, s) => sum + (s.stats?.total_orders || 0), 0)
})

// 总成交数
const totalTrades = computed(() => {
  return strategyStore.strategies.reduce((sum, s) => sum + (s.stats?.total_trades || 0), 0)
})

// 盈亏排行
const topStrategies = computed(() => {
  return [...strategyStore.strategies]
    .sort((a, b) => (b.stats?.realized_pnl || 0) - (a.stats?.realized_pnl || 0))
    .slice(0, 5)
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
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

// 查看详情
function handleViewDetail(strategy: StrategyInstance) {
  selectedStrategy.value = strategy
  showDetailDialog.value = true
}

// 启动策略
async function handleStart(instanceId: string) {
  try {
    await ElMessageBox.confirm('确定要启动此策略吗？', '确认', { type: 'info' })
    await strategyStore.startStrategy(instanceId)
    ElMessage.success('策略已启动')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('启动策略失败')
    }
  }
}

// 停止策略
async function handleStop(instanceId: string) {
  try {
    await ElMessageBox.confirm('确定要停止此策略吗？', '确认', { type: 'warning' })
    await strategyStore.stopStrategy(instanceId)
    ElMessage.success('策略已停止')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('停止策略失败')
    }
  }
}

// 删除策略
async function handleDelete(instanceId: string) {
  try {
    await ElMessageBox.confirm('确定要删除此策略吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonClass: 'el-button--danger',
    })
    await strategyStore.deleteStrategy(instanceId)
    ElMessage.success('策略已删除')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除策略失败')
    }
  }
}

// 创建策略
async function handleCreateStrategy() {
  if (!createFormRef.value) return

  try {
    await createFormRef.value.validate()
    creating.value = true

    await strategyStore.createStrategy({
      strategy_name: createForm.value.strategy_name,
      instance_name: createForm.value.instance_name,
      config: createForm.value.config,
    })

    ElMessage.success('策略创建成功')
    showCreateDialog.value = false

    // 重置表单
    createForm.value = {
      strategy_name: '',
      instance_name: '',
      config: {
        symbol: '',
        exchange: 'okx',
        order_amount: 0.001,
        spread: 0.001,
        inventory_target_base_pct: 50,
      },
    }
  } catch (err) {
    console.error('创建策略失败:', err)
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await strategyStore.fetchStrategies()
  // 获取可用策略列表
  try {
    availableStrategies.value = await api.getStrategies()
  } catch (err) {
    console.error('获取策略列表失败:', err)
  }
})
</script>

<style scoped>
.strategies-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mt-24 {
  margin-top: 24px;
}

.strategy-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-item {
  padding: 16px;
  background-color: #f9fafb;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.stat-value.running {
  color: #10b981;
}

.stat-value.stopped {
  color: #6b7280;
}

.config-preview {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}

:deep(.el-descriptions__label) {
  font-weight: 500;
}
</style>
