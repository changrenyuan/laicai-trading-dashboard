# 交易所连接管理 - 实现说明

## 问题诊断

从日志看：

```
2026-02-18 09:33:57,384 - src.ui.web_server - DEBUG - Received message from client:
{"cmd":"create_connection","exchange":"okx","api_key":"1","api_secret":"1","testnet":false}
2026-02-18 09:33:57,385 - src.core.ws_command_handler - INFO - Processing WebSocket command: create_connection
2026-02-18 09:33:57,385 - src.ui.web_server - DEBUG - Command response sent: True
```

命令被接收并处理了，但：
- ❌ 没有实际建立连接
- ❌ 没有错误日志
- ❌ 没有后续处理日志

**原因**：`_create_connection` 方法是 **TODO 占位符**，只返回了假的响应。

---

## 实现内容

### ✅ 已完成

1. **添加连接管理器**
   ```python
   self.connections: Dict[str, Dict] = {}
   ```
   - 存储所有已创建的连接
   - 支持多交易所连接

2. **实现 `_create_connection`**
   - 创建真实的 OKX 连接器
   - 初始化 HTTP 客户端
   - 测试连接（获取服务器时间）
   - 发布连接事件
   - 存储连接信息

3. **实现 `_delete_connection`**
   - 检查连接是否存在
   - 关闭连接器
   - 发布删除事件
   - 从管理器中移除

4. **实现 `_test_connection`**
   - 检查连接是否存在
   - 测试连接健康状态
   - 返回服务器时间
   - 发布测试事件

5. **实现 `_get_connections`**
   - 获取所有连接列表
   - 返回连接摘要信息
   - 用于前端显示

---

## 支持的交易所

### ✅ OKX

**配置参数**：
```json
{
  "cmd": "create_connection",
  "exchange": "okx",
  "api_key": "your-api-key",
  "api_secret": "your-api-secret",
  "passphrase": "your-passphrase",
  "testnet": false
}
```

**特性**：
- ✅ 实时连接测试
- ✅ 支持沙盒环境
- ✅ 支持代理配置
- ✅ 自动时间同步

---

## API 接口

### 1. 创建连接

**命令**：`create_connection`

**参数**：
- `exchange` (必填): 交易所名称（目前只支持 "okx"）
- `api_key` (必填): API Key
- `api_secret` (必填): API Secret
- `passphrase` (可选): OKX Passphrase
- `testnet` (可选): 是否使用测试网，默认 false

**请求示例**：
```json
{
  "cmd": "create_connection",
  "exchange": "okx",
  "api_key": "your-api-key",
  "api_secret": "your-api-secret",
  "passphrase": "your-passphrase",
  "testnet": false
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "Connection to okx created successfully",
  "connection_id": "okx-1778912345678",
  "exchange": "okx"
}
```

---

### 2. 删除连接

**命令**：`delete_connection`

**参数**：
- `id` (必填): 连接 ID

**请求示例**：
```json
{
  "cmd": "delete_connection",
  "id": "okx-1778912345678"
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "Connection okx-1778912345678 deleted"
}
```

---

### 3. 测试连接

**命令**：`test_connection`

**参数**：
- `id` (必填): 连接 ID

**请求示例**：
```json
{
  "cmd": "test_connection",
  "id": "okx-1778912345678"
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "Connection okx-1778912345678 is healthy",
  "server_time": "2026-02-18T09:33:57.123456Z"
}
```

---

### 4. 获取连接列表

**命令**：`get_connections`

**参数**：无

**请求示例**：
```json
{
  "cmd": "get_connections"
}
```

**响应示例**：
```json
{
  "success": true,
  "connections": [
    {
      "id": "okx-1778912345678",
      "exchange": "okx",
      "config": {
        "api_key": "abc12345...",
        "testnet": false
      },
      "created_at": "2026-02-18T09:33:57.123456"
    }
  ],
  "count": 1
}
```

---

## 事件推送

### 连接创建事件

```json
{
  "type": "connection",
  "event": "created",
  "connection_id": "okx-1778912345678",
  "exchange": "okx",
  "status": "connected"
}
```

### 连接删除事件

```json
{
  "type": "connection",
  "event": "deleted",
  "connection_id": "okx-1778912345678",
  "exchange": "okx"
}
```

### 连接测试事件

```json
{
  "type": "connection",
  "event": "tested",
  "connection_id": "okx-1778912345678",
  "status": "healthy"
}
```

---

## 日志输出

### 成功创建连接

```
[INFO] Creating connection to okx (testnet=False)
[INFO] OKX connector initialized successfully
[INFO] OKX server time: 2026-02-18T09:33:57.123456Z
[INFO] Connection created: okx-1778912345678
```

### 连接失败

```
[ERROR] Failed to initialize OKX connector: Invalid API credentials
[ERROR] Error creating connection: Invalid credentials
```

### 测试连接

```
[INFO] Testing connection: okx-1778912345678
[INFO] Connection test successful: okx-1778912345678, server time: 2026-02-18T09:33:57.123456Z
```

---

## 前端使用示例

### 1. 创建连接

```typescript
// 发送创建连接命令
const response = await ws.send(JSON.stringify({
  cmd: "create_connection",
  exchange: "okx",
  api_key: "your-api-key",
  api_secret: "your-api-secret",
  passphrase: "your-passphrase",
  testnet: false
}));

// 接收响应
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.success) {
    console.log("Connection created:", data.connection_id);
    // 保存 connection_id
  }
};
```

### 2. 监听连接事件

```typescript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "connection" && data.event === "created") {
    console.log("Connection created event:", data.connection_id);
    // 更新 UI
  }
};
```

### 3. 获取连接列表

```typescript
ws.send(JSON.stringify({
  cmd: "get_connections"
}));

// 响应
{
  "success": true,
  "connections": [...],
  "count": 1
}
```

---

## 注意事项

### 1. API 密钥安全

- API 密钥在日志中只显示前 8 位
- 前端不应存储完整的 API 密钥
- 使用 HTTPS 传输

### 2. 连接生命周期

- 连接创建后会自动测试
- 连接测试失败不会自动删除
- 需要手动删除失败的连接

### 3. 多连接支持

- 支持创建多个连接
- 每个连接有唯一的 ID
- 可以同时连接多个交易所

### 4. 错误处理

- 所有命令都有错误响应
- 错误信息会记录到日志
- 前端需要检查 `success` 字段

---

## 故障排查

### 问题：连接创建失败

**检查**：
1. API 密钥是否正确
2. 网络连接是否正常
3. 交易所 API 是否可用
4. 查看后端错误日志

### 问题：连接测试失败

**检查**：
1. API 密钥权限是否足够
2. IP 白名单是否配置
3. 网络代理是否正确

### 问题：连接丢失

**检查**：
1. 网络连接是否稳定
2. 心跳是否正常
3. 交易所是否维护

---

## 后续计划

### 短期
- [ ] 支持更多交易所（Binance, Huobi）
- [ ] 添加连接自动重连
- [ ] 连接健康监控

### 中期
- [ ] 连接池管理
- [ ] 连接权限控制
- [ ] 连接使用统计

### 长期
- [ ] 多账户管理
- [ ] 账户权限系统
- [ ] 审计日志

---

## 文件修改

### 修改的文件

1. `src/core/ws_command_handler.py`
   - 添加 `connections` 字典
   - 实现 `_create_connection`
   - 实现 `_delete_connection`
   - 实现 `_test_connection`
   - 实现 `_get_connections`

### 依赖的文件

1. `src/connectors/okx_lite/connector.py` - OKX 连接器
2. `src/core/event_bus.py` - 事件总线

---

## 测试

### 测试用例

```python
# 测试创建连接
cmd = {
  "cmd": "create_connection",
  "exchange": "okx",
  "api_key": "test-key",
  "api_secret": "test-secret",
  "testnet": True
}
response = await handler.handle_command(cmd)
assert response["success"] == True

# 测试获取连接
cmd = {"cmd": "get_connections"}
response = await handler.handle_command(cmd)
assert response["count"] == 1

# 测试删除连接
cmd = {"id": response["connections"][0]["id"]}
response = await handler.handle_command(cmd)
assert response["success"] == True
```

---

## 总结

### ✅ 已实现

- 真实的 OKX 连接创建
- 连接生命周期管理
- 连接健康测试
- 连接事件推送
- 详细的日志输出

### 🎯 使用方式

1. 前端发送 `create_connection` 命令
2. 后端创建连接并测试
3. 发布连接创建事件
4. 前端监听事件并更新 UI
5. 可以获取连接列表、测试连接、删除连接

### 📝 注意

- 使用真实的 API 密钥
- 测试网络连接
- 查看日志排查问题
- 妥善保管 API 密钥
