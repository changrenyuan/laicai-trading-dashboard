# Hummingbot Web UI - 真实交易所配置指南

## 1. 配置交易所 API 密钥

### 1.1 获取 OKX API 密钥

1. 登录 [OKX 官网](https://www.okx.com)
2. 进入 **账户管理** → **API 管理**
3. 点击 **创建 API Key**
4. 配置 API 权限：
   - ✅ 读取权限：账户信息、交易信息
   - ✅ 交易权限：下单、撤单（如果需要自动交易）
   - ✅ 提现权限：根据需要开启（通常不需要）

### 1.2 修改配置文件

打开项目根目录的 `config.json` 文件，填入你的 API 密钥：

```json
{
  "exchange": {
    "name": "okx",
    "sandbox": false,
    "registration_sub_domain": "www"
  },
  "api_credentials": {
    "api_key": "你的 API Key",
    "secret_key": "你的 Secret Key",
    "passphrase": "你的 Passphrase"
  },
  "proxy": {
    "enabled": false,
    "type": "http",
    "host": "127.0.0.1",
    "port": 7890
  },
  "risk_management": {
    "max_daily_loss": 0.05,
    "max_position_size": 0.1,
    "max_order_size": 0.01
  }
}
```

**重要提示**：
- 不要泄露你的 API 密钥
- 建议先使用 **沙盒环境** 测试（设置 `"sandbox": true`）
- 建议只开启读取权限，手动交易

### 1.3 配置说明

#### 交易所配置

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `name` | 交易所名称 | `okx` |
| `sandbox` | 是否使用沙盒环境 | `true`（沙盒）, `false`（实盘） |
| `registration_sub_domain` | 子域名 | `www`, `app`, `my` |

#### API 凭证

| 参数 | 说明 | 获取位置 |
|------|------|----------|
| `api_key` | API Key | OKX API 管理 |
| `secret_key` | Secret Key | OKX API 管理 |
| `passphrase` | Passphrase | 创建 API 时设置的密码 |

#### 代理配置

| 参数 | 说明 | 示例 |
|------|------|------|
| `enabled` | 是否启用代理 | `true`, `false` |
| `type` | 代理类型 | `http`, `socks5` |
| `host` | 代理地址 | `127.0.0.1` |
| `port` | 代理端口 | `7890`（HTTP）, `7891`（SOCKS5） |

**Clash 代理示例**：
- HTTP 代理：`127.0.0.1:7890`
- SOCKS5 代理：`127.0.0.1:7891`

#### 风控配置

| 参数 | 说明 | 示例 |
|------|------|------|
| `max_daily_loss` | 最大每日亏损比例 | `0.05`（5%） |
| `max_position_size` | 最大仓位大小 | `0.1`（10%） |
| `max_order_size` | 最大订单大小 | `0.01`（1%） |

## 2. 启动服务

### 2.1 启动后端

```bash
python start_backend.py
```

如果配置正确，你会看到：

```
✅ 成功连接到 OKX 交易所
💰 账户余额: {...}
🚀 服务器启动成功!
📍 API 地址: http://localhost:5000
```

如果配置错误，你会看到：

```
❌ 错误: 请在 config.json 中配置真实的 OKX API 密钥
```

### 2.2 启动前端

```bash
cd frontend
pnpm dev
```

### 2.3 访问应用

- 前端界面：http://localhost:5173
- 后端 API：http://localhost:5000
- API 文档：http://localhost:5000/docs

## 3. 验证连接

### 3.1 检查账户余额

访问 http://localhost:5173，查看：
- 账户余额是否显示真实数据
- 权益是否正确计算

### 3.2 检查市场数据

查看：
- 订单簿数据是否实时更新
- Ticker 数据是否正确

### 3.3 测试 API

使用以下命令测试：

```bash
# 获取账户余额
curl http://localhost:5000/api/balance

# 获取账户权益
curl http://localhost:5000/api/equity

# 获取订单簿
curl http://localhost:5000/api/orderbook/BTC-USDT
```

## 4. 常见问题

### Q1: 连接失败，提示认证错误

**原因**：API 密钥配置错误

**解决**：
1. 检查 `api_key`, `secret_key`, `passphrase` 是否正确
2. 确认 API 权限是否开启
3. 尝试重新生成 API Key

### Q2: 无法获取余额

**原因**：网络问题或 IP 白名单限制

**解决**：
1. 检查网络连接
2. 在 OKX API 管理中添加 IP 白名单
3. 如果使用代理，检查代理配置是否正确

### Q3: 请求超时

**原因**：网络延迟或代理问题

**解决**：
1. 启用代理（Clash）
2. 检查代理端口是否正确
3. 增加超时时间（修改 `aiohttp.ClientTimeout`）

### Q4: 沙盒环境如何测试？

**配置沙盒环境**：
```json
{
  "exchange": {
    "sandbox": true
  }
}
```

沙盒环境说明：
- 使用模拟资金
- 不影响真实账户
- 适合测试和调试

## 5. 安全建议

1. **不要泄露 API 密钥**
   - 不要将 `config.json` 提交到 Git
   - 将 `config.json` 添加到 `.gitignore`

2. **使用最小权限原则**
   - 只开启必要的权限
   - 定期更换 API 密钥

3. **IP 白名单**
   - 在 OKX API 管理中设置 IP 白名单
   - 限制 API 访问来源

4. **沙盒测试**
   - 先在沙盒环境测试
   - 确认无误后再切换到实盘

5. **风险控制**
   - 设置合理的止损
   - 控制仓位大小
   - 监控每日盈亏

## 6. 后续步骤

配置完成后，你可以：

1. **查看实时数据**：余额、仓位、订单
2. **管理策略**：创建、启动、停止策略
3. **监控交易**：实时查看订单和成交记录
4. **分析盈亏**：查看 PnL 历史和统计

祝交易顺利！🚀
