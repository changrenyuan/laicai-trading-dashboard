# Hummingbot Lite - Windows 快速开始

## 🚀 最快速的启动方式（三步走）

### 第一步：安装
双击运行 `install.bat`
- 自动安装 Python 虚拟环境
- 自动安装所有依赖包

### 第二步：配置
编辑 `.env` 文件
```env
OKX_API_KEY=你的API密钥
OKX_API_SECRET=你的API密钥
OKX_API_PASSPHRASE=你的密码短语
OKX_SANDBOX=true  # 首次使用建议设为 true
```

### 第三步：启动
双击运行 `start.bat`
- 自动启动程序
- 自动打开浏览器访问 http://localhost:5000

## 📋 批处理脚本说明

| 脚本 | 功能 | 何时使用 |
|------|------|----------|
| `install.bat` | 安装程序 | 首次运行或重新安装 |
| `start.bat` | 启动程序 | 日常运行 |
| `stop.bat` | 停止程序 | 需要停止服务时 |
| `check_status.bat` | 检查状态 | 遇到问题时诊断 |

## 🔧 常见问题快速修复

### 问题1：双击脚本闪退
**解决**：右键脚本 -> 以管理员身份运行

### 问题2：提示 Python 未安装
**解决**：
1. 下载 Python：https://www.python.org/downloads/
2. 安装时**务必勾选** "Add Python to PATH"

### 问题3：端口 5000 被占用
**解决**：编辑 `.env` 文件，将 `PORT=5000` 改为 `PORT=5001`

### 问题4：依赖安装失败
**解决**：
```cmd
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 📱 访问 Web UI

启动成功后，在浏览器打开：
```
http://localhost:5000
```

## ⚠️ 重要提示

1. **首次使用**：建议设置 `OKX_SANDBOX=true` 使用模拟环境测试
2. **API 密钥**：从 OKX 官网获取，**不要**提现权限
3. **防火墙**：确保 Python 允许访问网络
4. **杀毒软件**：将项目目录添加到白名单

## 📚 更多信息

详细安装和配置指南请查看：[WINDOWS_INSTALL.md](WINDOWS_INSTALL.md)

## 🆘 需要帮助？

1. 运行 `check_status.bat` 检查系统状态
2. 查看 `logs/app.log` 了解详细错误信息
3. 确保所有依赖已正确安装

---

**祝你交易顺利！** 📈
