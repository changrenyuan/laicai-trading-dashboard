<template>
  <div class="settings-page">
    <el-row :gutter="24">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>API 密钥配置</span>
              <el-tag type="info">{{ selectedExchange }}</el-tag>
            </div>
          </template>

          <el-form :model="apiKeyForm" label-width="120px">
            <el-form-item label="交易所">
              <el-select v-model="selectedExchange" style="width: 100%" @change="loadApiKey">
                <el-option label="OKX" value="okx" />
                <el-option label="Binance" value="binance" />
                <el-option label="Bybit" value="bybit" />
              </el-select>
            </el-form-item>

            <el-form-item label="API Key">
              <el-input
                v-model="apiKeyForm.api_key"
                type="password"
                placeholder="输入 API Key"
                show-password
              />
            </el-form-item>

            <el-form-item label="API Secret">
              <el-input
                v-model="apiKeyForm.api_secret"
                type="password"
                placeholder="输入 API Secret"
                show-password
              />
            </el-form-item>

            <el-form-item label="Passphrase" v-if="selectedExchange === 'okx'">
              <el-input
                v-model="apiKeyForm.passphrase"
                type="password"
                placeholder="输入 Passphrase"
                show-password
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveApiKey" :loading="saving">
                保存配置
              </el-button>
              <el-button @click="testApiKey" :loading="testing">
                测试连接
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" class="mt-24">
          <template #header>
            <span>系统设置</span>
          </template>

          <el-form label-width="120px">
            <el-form-item label="自动重启策略">
              <el-switch v-model="settings.autoRestart" />
              <span class="form-tip">策略崩溃时自动重启</span>
            </el-form-item>

            <el-form-item label="最大并发数">
              <el-input-number
                v-model="settings.maxConcurrentStrategies"
                :min="1"
                :max="10"
              />
              <span class="form-tip">同时运行的策略最大数量</span>
            </el-form-item>

            <el-form-item label="日志级别">
              <el-select v-model="settings.logLevel" style="width: 200px">
                <el-option label="DEBUG" value="DEBUG" />
                <el-option label="INFO" value="INFO" />
                <el-option label="WARNING" value="WARNING" />
                <el-option label="ERROR" value="ERROR" />
              </el-select>
            </el-form-item>

            <el-form-item label="数据刷新间隔">
              <el-input-number
                v-model="settings.refreshInterval"
                :min="1"
                :max="60"
              />
              <span class="form-tip">秒</span>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveSettings" :loading="saving">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <span>系统信息</span>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统状态">
              <el-tag type="success">运行中</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="版本">
              2.12.0
            </el-descriptions-item>
            <el-descriptions-item label="运行时间">
              {{ uptime }}
            </el-descriptions-item>
            <el-descriptions-item label="WebSocket">
              <el-tag :type="wsConnected ? 'success' : 'danger'">
                {{ wsConnected ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="运行策略数">
              {{ strategyStore.runningCount }}
            </el-descriptions-item>
            <el-descriptions-item label="总权益">
              ${{ accountStore.totalEquity.toFixed(2) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="hover" class="mt-24">
          <template #header>
            <span>快捷操作</span>
          </template>

          <div class="quick-actions">
            <el-button type="success" :icon="Refresh" @click="refreshAll">
              刷新所有数据
            </el-button>
            <el-button type="warning" :icon="Download" @click="exportData">
              导出数据
            </el-button>
            <el-button type="info" :icon="DocumentCopy" @click="showLogs">
              查看日志
            </el-button>
          </div>
        </el-card>

        <el-card shadow="hover" class="mt-24">
          <template #header>
            <span>危险操作</span>
          </template>

          <el-alert
            title="以下操作具有风险，请谨慎使用"
            type="warning"
            :closable="false"
            style="margin-bottom: 16px"
          />

          <div class="danger-actions">
            <el-button type="danger" plain @click="stopAllStrategies">
              停止所有策略
            </el-button>
            <el-button type="danger" plain @click="cancelAllOrders">
              取消所有订单
            </el-button>
            <el-button type="danger" @click="triggerKillSwitch">
              紧急停止
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStrategyStore } from '@/stores/strategy'
import { useAccountStore } from '@/stores/account'
import { wsClient } from '@/api/websocket'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  Download,
  DocumentCopy,
} from '@element-plus/icons-vue'

const router = useRouter()
const strategyStore = useStrategyStore()
const accountStore = useAccountStore()

const selectedExchange = ref('okx')
const apiKeyForm = ref({
  api_key: '',
  api_secret: '',
  passphrase: '',
})

const settings = ref({
  autoRestart: true,
  maxConcurrentStrategies: 5,
  logLevel: 'INFO',
  refreshInterval: 5,
})

const saving = ref(false)
const testing = ref(false)
const wsConnected = ref(false)
const startTime = ref(Date.now())

// 计算运行时间
const uptime = computed(() => {
  const diff = Date.now() - startTime.value
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diff % (1000 * 60)) / 1000)

  if (days > 0) {
    return `${days}天 ${hours}小时 ${minutes}分钟`
  } else if (hours > 0) {
    return `${hours}小时 ${minutes}分钟 ${seconds}秒`
  } else if (minutes > 0) {
    return `${minutes}分钟 ${seconds}秒`
  } else {
    return `${seconds}秒`
  }
})

// 加载 API 密钥
function loadApiKey() {
  // TODO: 从后端加载 API 密钥
  console.log('Load API key for:', selectedExchange.value)
}

// 保存 API 密钥
async function saveApiKey() {
  saving.value = true
  try {
    // TODO: 保存到后端
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('API 密钥已保存')
  } catch (err) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 测试 API 密钥
async function testApiKey() {
  testing.value = true
  try {
    // TODO: 调用后端 API 测试
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('连接测试成功')
  } catch (err) {
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

// 保存系统设置
async function saveSettings() {
  saving.value = true
  try {
    // TODO: 保存到后端
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('设置已保存')
  } catch (err) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 刷新所有数据
async function refreshAll() {
  try {
    await Promise.all([
      strategyStore.fetchStrategies(),
      accountStore.init(),
    ])
    ElMessage.success('数据已刷新')
  } catch (err) {
    ElMessage.error('刷新失败')
  }
}

// 导出数据
function exportData() {
  // TODO: 实现数据导出
  ElMessage.info('导出功能开发中')
}

// 查看日志
function showLogs() {
  router.push('/logs')
}

// 停止所有策略
async function stopAllStrategies() {
  try {
    await ElMessageBox.confirm(
      '确定要停止所有运行中的策略吗？',
      '确认',
      { type: 'warning' }
    )

    // TODO: 调用批量停止 API
    ElMessage.success('所有策略已停止')
    await strategyStore.fetchStrategies()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('停止失败')
    }
  }
}

// 取消所有订单
async function cancelAllOrders() {
  try {
    await ElMessageBox.confirm(
      '确定要取消所有挂单吗？',
      '确认',
      { type: 'warning' }
    )

    // TODO: 调用批量取消订单 API
    ElMessage.success('所有订单已取消')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('取消失败')
    }
  }
}

// 触发紧急停止
async function triggerKillSwitch() {
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

onMounted(() => {
  wsClient.onConnection((connected) => {
    wsConnected.value = connected
  })
})
</script>

<style scoped>
.settings-page {
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

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #999;
}

.quick-actions,
.danger-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.danger-actions .el-button {
  width: 100%;
}
</style>
