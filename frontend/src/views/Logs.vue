<template>
  <div class="logs-page">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>实时日志</span>
          <div class="header-actions">
            <el-select v-model="selectedLogLevel" size="small" style="width: 120px">
              <el-option label="全部" value="all" />
              <el-option label="DEBUG" value="DEBUG" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="ERROR" value="ERROR" />
              <el-option label="CRITICAL" value="CRITICAL" />
            </el-select>
            <el-checkbox v-model="autoScroll" label="自动滚动" />
            <el-button type="danger" :icon="Delete" @click="clearLogs">
              清空
            </el-button>
            <el-button type="primary" :icon="Download" @click="exportLogs">
              导出
            </el-button>
          </div>
        </div>
      </template>

      <div ref="logContainerRef" class="log-container">
        <div
          v-for="(log, index) in filteredLogs"
          :key="index"
          :class="['log-entry', `log-${log.level.toLowerCase()}`]"
        >
          <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
          <span class="log-level">{{ log.level }}</span>
          <span class="log-logger">[{{ log.logger }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>

        <div v-if="filteredLogs.length === 0" class="log-empty">
          <el-icon><DocumentRemove /></el-icon>
          <span>暂无日志</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { wsClient, type LogMessage } from '@/api/websocket'
import { ElMessage } from 'element-plus'
import { Delete, Download, DocumentRemove } from '@element-plus/icons-vue'

const logs = ref<LogMessage[]>([])
const selectedLogLevel = ref('all')
const autoScroll = ref(true)
const logContainerRef = ref<HTMLElement>()

// 过滤后的日志
const filteredLogs = computed(() => {
  if (selectedLogLevel.value === 'all') {
    return logs.value
  }
  return logs.value.filter(log => log.level === selectedLogLevel.value)
})

// 格式化时间戳
function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }) + '.' + date.getMilliseconds().toString().padStart(3, '0')
}

// 处理 WebSocket 消息
function handleWSMessage(message: any) {
  if (message.type === 'log') {
    logs.value.push(message.data as LogMessage)

    // 限制日志数量，最多保留 1000 条
    if (logs.value.length > 1000) {
      logs.value = logs.value.slice(-1000)
    }

    // 自动滚动
    if (autoScroll.value) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  }
}

// 滚动到底部
function scrollToBottom() {
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

// 清空日志
function clearLogs() {
  logs.value = []
  ElMessage.success('日志已清空')
}

// 导出日志
function exportLogs() {
  const content = filteredLogs.value
    .map(log => `[${formatTimestamp(log.timestamp)}] [${log.level}] [${log.logger}] ${log.message}`)
    .join('\n')

  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `logs_${new Date().toISOString().split('T')[0]}.txt`
  link.click()
  URL.revokeObjectURL(url)

  ElMessage.success('日志已导出')
}

onMounted(() => {
  // 连接 WebSocket
  wsClient.onMessage(handleWSMessage)

  if (!wsClient.isConnected()) {
    wsClient.connect()
  }
})

onUnmounted(() => {
  // 不需要断开连接，因为全局只有一个 WebSocket 实例
})

// 监听自动滚动变化
watch(autoScroll, () => {
  if (autoScroll.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})
</script>

<style scoped>
.logs-page {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-container {
  height: calc(100vh - 220px);
  overflow-y: auto;
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 12px;
  border-radius: 4px;
}

.log-entry {
  display: flex;
  gap: 8px;
  padding: 2px 0;
  word-break: break-all;
}

.log-timestamp {
  color: #858585;
  min-width: 100px;
}

.log-level {
  font-weight: bold;
  min-width: 70px;
}

.log-entry.log-debug .log-level {
  color: #858585;
}

.log-entry.log-info .log-level {
  color: #4fc3f7;
}

.log-entry.log-warning .log-level {
  color: #ffb74d;
}

.log-entry.log-error .log-level {
  color: #e57373;
}

.log-entry.log-critical .log-level {
  color: #f44336;
  text-shadow: 0 0 4px #f44336;
}

.log-logger {
  color: #ce9178;
  min-width: 150px;
}

.log-message {
  color: #d4d4d4;
  flex: 1;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #858585;
  gap: 12px;
  font-size: 16px;
}

.log-empty .el-icon {
  font-size: 48px;
}

/* 滚动条样式 */
.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background-color: #1e1e1e;
}

.log-container::-webkit-scrollbar-thumb {
  background-color: #424242;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background-color: #616161;
}
</style>
