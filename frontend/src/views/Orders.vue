<template>
  <div class="orders-page">
    <el-row :gutter="24">
      <!-- 左侧：活跃订单 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>活跃订单</span>
              <el-button type="primary" :icon="Refresh" @click="refreshOrders">
                刷新
              </el-button>
            </div>
          </template>

          <el-table :data="activeOrders" stripe v-loading="loading">
            <el-table-column prop="order_id" label="订单ID" width="120" />
            <el-table-column prop="symbol" label="交易对" width="100" />
            <el-table-column label="方向" width="70">
              <template #default="{ row }">
                <el-tag :type="row.side === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.side === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                {{ row.type }}
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="100">
              <template #default="{ row }">
                ${{ row.price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="数量" width="100">
              <template #default="{ row }">
                {{ row.amount.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column label="已成交" width="100">
              <template #default="{ row }">
                <el-progress
                  :percentage="(row.filled / row.amount) * 100"
                  :stroke-width="8"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="handleCancelOrder(row.order_id)">
                  取消
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：订单簿 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>订单簿 - {{ selectedSymbol }}</span>
              <el-select v-model="selectedSymbol" size="small" style="width: 150px" @change="fetchOrderBook">
                <el-option label="BTC-USDT" value="BTC-USDT" />
                <el-option label="ETH-USDT" value="ETH-USDT" />
                <el-option label="SOL-USDT" value="SOL-USDT" />
              </el-select>
            </div>
          </template>

          <div class="orderbook-container">
            <div class="orderbook-header">
              <span class="col-price">价格</span>
              <span class="col-amount">数量</span>
              <span class="col-total">累计</span>
            </div>

            <!-- 卖单 -->
            <div class="orderbook-asks">
              <div
                v-for="(ask, index) in orderBookAsks"
                :key="index"
                class="orderbook-row ask"
                :style="{ background: `linear-gradient(to right, rgba(239, 68, 68, ${getDepthRatio(index, 'ask')}), transparent)` }"
              >
                <span class="col-price">{{ ask[0].toFixed(2) }}</span>
                <span class="col-amount">{{ ask[1].toFixed(4) }}</span>
                <span class="col-total">{{ (ask[0] * ask[1]).toFixed(2) }}</span>
              </div>
            </div>

            <!-- 中间价格 -->
            <div class="orderbook-mid">
              <span class="mid-price">{{ currentPrice.toFixed(2) }}</span>
              <span class="mid-label">最新价</span>
            </div>

            <!-- 买单 -->
            <div class="orderbook-bids">
              <div
                v-for="(bid, index) in orderBookBids"
                :key="index"
                class="orderbook-row bid"
                :style="{ background: `linear-gradient(to right, rgba(16, 185, 129, ${getDepthRatio(index, 'bid')}), transparent)` }"
              >
                <span class="col-price">{{ bid[0].toFixed(2) }}</span>
                <span class="col-amount">{{ bid[1].toFixed(4) }}</span>
                <span class="col-total">{{ (bid[0] * bid[1]).toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 成交历史 -->
    <el-row :gutter="24" class="history-section">
      <el-col :xs="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>成交历史</span>
              <el-button type="primary" :icon="Refresh" @click="refreshTrades">
                刷新
              </el-button>
            </div>
          </template>

          <el-table :data="trades" stripe v-loading="loading">
            <el-table-column prop="trade_id" label="成交ID" width="150" />
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column label="方向" width="80">
              <template #default="{ row }">
                <el-tag :type="row.side === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.side === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="120">
              <template #default="{ row }">
                ${{ row.price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="数量" width="120">
              <template #default="{ row }">
                {{ row.amount.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column prop="fee" label="手续费" width="120">
              <template #default="{ row }">
                {{ row.fee.toFixed(4) }} {{ row.fee_currency }}
              </template>
            </el-table-column>
            <el-table-column prop="timestamp" label="时间" width="180">
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
import { useAccountStore } from '@/stores/account'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as api from '@/api/client'
import type { Order, Trade, OrderBook } from '@/types/account'

const accountStore = useAccountStore()

const loading = ref(false)
const activeOrders = ref<Order[]>([])
const trades = ref<Trade[]>([])
const orderBook = ref<OrderBook | null>(null)
const selectedSymbol = ref('BTC-USDT')
let refreshTimer: number | null = null

// 当前价格（取最佳买卖价的中间值）
const currentPrice = computed(() => {
  if (!orderBook.value) return 0
  const bestBid = orderBook.value.bids[0]?.[0] || 0
  const bestAsk = orderBook.value.asks[0]?.[0] || 0
  return (bestBid + bestAsk) / 2
})

// 买单（按价格降序）
const orderBookBids = computed(() => {
  if (!orderBook.value) return []
  return [...orderBook.value.bids].sort((a, b) => b[0] - a[0]).slice(0, 10)
})

// 卖单（按价格升序）
const orderBookAsks = computed(() => {
  if (!orderBook.value) return []
  return [...orderBook.value.asks].sort((a, b) => a[0] - b[0]).slice(0, 10)
})

// 获取深度比例（用于背景色）
function getDepthRatio(index: number, side: 'bid' | 'ask') {
  const data = side === 'bid' ? orderBookBids.value : orderBookAsks.value
  const maxAmount = Math.max(...data.map(d => d[1]))
  if (maxAmount === 0) return 0
  return data[index][1] / maxAmount * 0.8
}

// 格式化时间
function formatTime(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

// 刷新订单
async function refreshOrders() {
  loading.value = true
  try {
    activeOrders.value = await api.getActiveOrders()
  } catch (err) {
    ElMessage.error('刷新订单失败')
  } finally {
    loading.value = false
  }
}

// 刷新成交记录
async function refreshTrades() {
  loading.value = true
  try {
    trades.value = await api.getTradeHistory({ limit: 20 })
  } catch (err) {
    ElMessage.error('刷新成交记录失败')
  } finally {
    loading.value = false
  }
}

// 获取订单簿
async function fetchOrderBook() {
  try {
    orderBook.value = await api.getOrderBook(selectedSymbol.value, 20)
  } catch (err) {
    console.error('获取订单簿失败:', err)
  }
}

// 取消订单
async function handleCancelOrder(orderId: string) {
  try {
    // TODO: 实现取消订单 API
    ElMessage.success('订单已取消')
    await refreshOrders()
  } catch (err) {
    ElMessage.error('取消订单失败')
  }
}

onMounted(async () => {
  await Promise.all([
    refreshOrders(),
    refreshTrades(),
    fetchOrderBook(),
  ])

  // 定时刷新数据
  refreshTimer = window.setInterval(async () => {
    await Promise.all([
      refreshOrders(),
      fetchOrderBook(),
    ])
  }, 2000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.orders-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-section {
  margin-bottom: 0;
}

.orderbook-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.orderbook-header {
  display: flex;
  padding: 8px 12px;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #666;
}

.col-price {
  flex: 1;
  text-align: left;
}

.col-amount {
  flex: 1;
  text-align: center;
}

.col-total {
  flex: 1;
  text-align: right;
}

.orderbook-row {
  display: flex;
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 2px;
  position: relative;
}

.orderbook-row.ask .col-price {
  color: #ef4444;
}

.orderbook-row.bid .col-price {
  color: #10b981;
}

.orderbook-mid {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-size: 18px;
  font-weight: 600;
}

.mid-price {
  color: #1890ff;
}

.mid-label {
  font-size: 12px;
  color: #999;
  font-weight: normal;
}

.orderbook-bids,
.orderbook-asks {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
