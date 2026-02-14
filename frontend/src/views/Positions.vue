<template>
  <div class="positions-page">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>当前仓位</span>
          <el-button type="primary" :icon="Refresh" @click="refreshPositions">
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="accountStore.positions" stripe v-loading="accountStore.loading">
        <el-table-column prop="symbol" label="交易对" width="150" />
        <el-table-column label="方向" width="80">
          <template #default="{ row }">
            <el-tag :type="row.side === 'long' ? 'success' : 'danger'" size="small">
              {{ row.side === 'long' ? '多头' : '空头' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="仓位大小" width="120">
          <template #default="{ row }">
            {{ row.size.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="entry_price" label="开仓均价" width="120">
          <template #default="{ row }">
            ${{ row.entry_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="mark_price" label="标记价格" width="120">
          <template #default="{ row }">
            ${{ row.mark_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="未实现盈亏" width="140">
          <template #default="{ row }">
            <span :class="{ positive: row.unrealized_pnl >= 0, negative: row.unrealized_pnl < 0 }">
              {{ row.unrealized_pnl >= 0 ? '+' : '' }}${{ row.unrealized_pnl.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="已实现盈亏" width="140">
          <template #default="{ row }">
            <span :class="{ positive: row.realized_pnl >= 0, negative: row.realized_pnl < 0 }">
              {{ row.realized_pnl >= 0 ? '+' : '' }}${{ row.realized_pnl.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="leverage" label="杠杆" width="80" />
        <el-table-column label="保证金率" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="row.margin_ratio * 100"
              :color="getMarginRatioColor(row.margin_ratio)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="liquidation_price" label="强平价格" width="120">
          <template #default="{ row }">
            {{ row.liquidation_price ? `$${row.liquidation_price.toFixed(2)}` : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 仓位汇总 -->
    <el-row :gutter="24" class="summary-section">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-content">
            <div class="summary-label">未实现盈亏</div>
            <div class="summary-value" :class="{ positive: totalUnrealizedPnL >= 0, negative: totalUnrealizedPnL < 0 }">
              {{ totalUnrealizedPnL >= 0 ? '+' : '' }}${{ totalUnrealizedPnL.toFixed(2) }}
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-content">
            <div class="summary-label">已实现盈亏</div>
            <div class="summary-value" :class="{ positive: totalRealizedPnL >= 0, negative: totalRealizedPnL < 0 }">
              {{ totalRealizedPnL >= 0 ? '+' : '' }}${{ totalRealizedPnL.toFixed(2) }}
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-content">
            <div class="summary-label">多头仓位</div>
            <div class="summary-value long">{{ longPositionsCount }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-content">
            <div class="summary-label">空头仓位</div>
            <div class="summary-value short">{{ shortPositionsCount }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAccountStore } from '@/stores/account'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const accountStore = useAccountStore()

// 总未实现盈亏
const totalUnrealizedPnL = computed(() => {
  return accountStore.positions.reduce((sum, p) => sum + p.unrealized_pnl, 0)
})

// 总已实现盈亏
const totalRealizedPnL = computed(() => {
  return accountStore.positions.reduce((sum, p) => sum + p.realized_pnl, 0)
})

// 多头仓位数量
const longPositionsCount = computed(() => {
  return accountStore.positions.filter(p => p.side === 'long').length
})

// 空头仓位数量
const shortPositionsCount = computed(() => {
  return accountStore.positions.filter(p => p.side === 'short').length
})

// 获取保证金率颜色
function getMarginRatioColor(ratio: number) {
  if (ratio > 0.7) return '#f56c6c'
  if (ratio > 0.5) return '#e6a23c'
  return '#67c23a'
}

// 刷新仓位
async function refreshPositions() {
  try {
    await accountStore.fetchPositions()
    ElMessage.success('仓位已刷新')
  } catch (err) {
    ElMessage.error('刷新仓位失败')
  }
}

onMounted(async () => {
  await accountStore.fetchPositions()
})
</script>

<style scoped>
.positions-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-section {
  margin-bottom: 0;
}

.summary-card {
  height: 100px;
}

.summary-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.summary-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 8px;
}

.summary-value {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.summary-value.positive {
  color: #10b981;
}

.summary-value.negative {
  color: #ef4444;
}

.summary-value.long {
  color: #10b981;
}

.summary-value.short {
  color: #ef4444;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}
</style>
