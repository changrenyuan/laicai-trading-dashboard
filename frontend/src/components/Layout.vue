<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon><TrendCharts /></el-icon>
        <span>Hummingbot Dashboard</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1890ff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>

        <el-menu-item index="/strategies">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>策略管理</template>
        </el-menu-item>

        <el-menu-item index="/positions">
          <el-icon><Document /></el-icon>
          <template #title>仓位管理</template>
        </el-menu-item>

        <el-menu-item index="/orders">
          <el-icon><List /></el-icon>
          <template #title>订单管理</template>
        </el-menu-item>

        <el-menu-item index="/pnl">
          <el-icon><DataLine /></el-icon>
          <template #title>PnL 分析</template>
        </el-menu-item>

        <el-menu-item index="/backtest">
          <el-icon><Timer /></el-icon>
          <template #title>回测</template>
        </el-menu-item>

        <el-menu-item index="/logs">
          <el-icon><DocumentCopy /></el-icon>
          <template #title>日志</template>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <h1>{{ currentPageTitle }}</h1>
        </div>
        <div class="header-right">
          <!-- 账户信息 -->
          <div class="account-info" v-if="accountStore.totalEquity > 0">
            <span class="label">总权益:</span>
            <span class="value" :class="{ 'positive': accountStore.totalPnL >= 0, 'negative': accountStore.totalPnL < 0 }">
              ${{ accountStore.totalEquity.toFixed(2) }}
            </span>
            <span class="pnl" :class="{ 'positive': accountStore.todayPnL >= 0, 'negative': accountStore.todayPnL < 0 }">
              ({{ accountStore.todayPnL >= 0 ? '+' : '' }}{{ accountStore.todayPnL.toFixed(2) }} 今日)
            </span>
          </div>

          <!-- 运行中策略数 -->
          <div class="strategy-badge">
            <el-tag :type="strategyStore.runningCount > 0 ? 'success' : 'info'" effect="dark">
              <el-icon><VideoPlay /></el-icon>
              运行中: {{ strategyStore.runningCount }}
            </el-tag>
          </div>

          <!-- Kill Switch -->
          <el-button
            type="danger"
            size="small"
            :icon="SwitchButton"
            @click="handleKillSwitch"
          >
            紧急停止
          </el-button>

          <!-- WebSocket 连接状态 -->
          <div class="ws-status" :class="{ connected: wsConnected }">
            <el-tooltip :content="wsConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'">
              <el-icon><Connection /></el-icon>
            </el-tooltip>
          </div>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useStrategyStore } from '@/stores/strategy'
import { useAccountStore } from '@/stores/account'
import { wsClient, type WSMessage } from '@/api/websocket'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  TrendCharts,
  Odometer,
  DataAnalysis,
  Document,
  List,
  DataLine,
  Timer,
  DocumentCopy,
  Setting,
  SwitchButton,
  VideoPlay,
  Connection,
} from '@element-plus/icons-vue'

const route = useRoute()
const strategyStore = useStrategyStore()
const accountStore = useAccountStore()

const wsConnected = ref(false)

// 页面标题
const currentPageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': '仪表盘',
    '/strategies': '策略管理',
    '/positions': '仓位管理',
    '/orders': '订单管理',
    '/pnl': 'PnL 分析',
    '/backtest': '回测',
    '/logs': '日志',
    '/settings': '设置',
  }
  return titles[route.path] || '仪表盘'
})

const activeMenu = computed(() => route.path)

// Kill Switch
async function handleKillSwitch() {
  try {
    await ElMessageBox.confirm(
      '此操作将立即停止所有策略并取消所有挂单，是否继续？',
      '紧急停止确认',
      {
        confirmButtonText: '确认停止',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger',
      }
    )

    const { triggerKillSwitch } = await import('@/api/client')
    await triggerKillSwitch()
    ElMessage.success('已触发紧急停止')
    await strategyStore.fetchStrategies()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('触发紧急停止失败')
    }
  }
}

// WebSocket 消息处理
function handleWSMessage(message: WSMessage) {
  switch (message.type) {
    case 'order':
      // 订单更新
      break
    case 'trade':
      // 成交更新
      break
    case 'position':
      // 仓位更新
      accountStore.fetchPositions()
      break
  }
}

// ✅ 修复：将 onUnmounted 放在顶层
let refreshInterval: number | null = null

onMounted(async () => {
  // 初始化 stores
  await Promise.all([
    strategyStore.init(),
    accountStore.init(),
  ])

  // 连接 WebSocket
  wsClient.connect()
  wsClient.onConnection((connected) => {
    wsConnected.value = connected
  })
  wsClient.onMessage(handleWSMessage)

  // 定时刷新数据
  refreshInterval = setInterval(() => {
    strategyStore.fetchStrategies()
    accountStore.fetchAccount()
  }, 5000)
})

onUnmounted(() => {
  console.log('[Layout] 组件卸载，清理资源')
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  wsClient.disconnect()
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background-color: #001529;
  overflow-x: hidden;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
  border-bottom: 1px solid #1f2937;
}

.logo .el-icon {
  margin-right: 8px;
  font-size: 24px;
  color: #1890ff;
}

.sidebar-menu {
  border: none;
}

.sidebar-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.account-info .label {
  color: #6b7280;
}

.account-info .value {
  font-weight: 600;
  font-size: 16px;
}

.account-info .value.positive {
  color: #10b981;
}

.account-info .value.negative {
  color: #ef4444;
}

.account-info .pnl {
  font-size: 12px;
}

.account-info .pnl.positive {
  color: #10b981;
}

.account-info .pnl.negative {
  color: #ef4444;
}

.strategy-badge {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ws-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #ef4444;
  color: #fff;
  font-size: 18px;
  transition: all 0.3s;
}

.ws-status.connected {
  background-color: #10b981;
}

.main-content {
  background-color: #f3f4f6;
  overflow-y: auto;
  padding: 24px;
}
</style>
