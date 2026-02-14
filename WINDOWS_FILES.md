# Windows 文件清单

本文档列出了为 Windows 用户创建的所有文件。

## 📁 批处理脚本 (.bat)

### 核心脚本

| 文件 | 功能 | 优先级 |
|------|------|--------|
| `install.bat` | 一键安装（虚拟环境 + 依赖） | ⭐⭐⭐ |
| `start.bat` | 启动程序 | ⭐⭐⭐ |
| `stop.bat` | 停止程序 | ⭐⭐ |
| `check_status.bat` | 系统状态检查 | ⭐⭐ |
| `fix.bat` | 一键修复常见问题 | ⭐⭐⭐ |
| `service_manager.bat` | Windows 服务管理 | ⭐ |

## 📄 PowerShell 脚本

| 文件 | 功能 |
|------|------|
| `start.ps1` | PowerShell 版本启动脚本 |

## 📝 文档

| 文件 | 内容 |
|------|------|
| `README_WINDOWS.md` | Windows 快速开始指南 |
| `WINDOWS_INSTALL.md` | 完整的 Windows 安装和配置指南 |

## 🔧 配置文件

| 文件 | 功能 |
|------|------|
| `.env.example` | 配置文件模板 |
| `.env` | 实际配置文件（需用户创建） |

## 📋 文件详细说明

### install.bat
- 检查 Python 环境
- 创建虚拟环境
- 安装所有依赖包
- 创建 .env 配置文件
- 提供下一步操作提示

**使用时机**：首次安装或重新安装

### start.bat
- 检查虚拟环境
- 激活虚拟环境
- 检查端口占用
- 启动主程序
- 错误处理和日志提示

**使用时机**：日常运行

### stop.bat
- 查找运行中的 Python 进程
- 优雅关闭进程
- 清理资源

**使用时机**：需要停止程序时

### check_status.bat
- 检查 Python 环境
- 检查虚拟环境
- 检查依赖包
- 检查配置文件
- 检查端口占用
- 检查运行状态
- 检查日志文件
- 测试 API 连接

**使用时机**：遇到问题时诊断

### fix.bat
- 修复虚拟环境
- 修复依赖包
- 修复配置文件
- 修复日志目录
- 修复防火墙规则
- 清理临时文件
- 运行诊断

**使用时机**：遇到问题时自动修复

### service_manager.bat
- 安装 Windows 服务
- 启动/停止服务
- 卸载服务
- 查看服务状态
- 查看服务日志

**使用时机**：需要开机自启或后台运行

## 🎯 推荐使用流程

### 首次使用

```
1. 双击 install.bat
2. 编辑 .env 文件
3. 双击 start.bat
4. 浏览器访问 http://localhost:5000
```

### 日常使用

```
启动：双击 start.bat
停止：双击 stop.bat
检查：双击 check_status.bat
```

### 遇到问题

```
1. 双击 check_status.bat 查看状态
2. 双击 fix.bat 自动修复
3. 查看 logs\app.log 了解详细错误
```

### 后台运行（开机自启）

```
1. 双击 service_manager.bat
2. 选择 "1. 安装服务"
3. 选择 "2. 启动服务"
```

## 📌 注意事项

1. **管理员权限**：某些操作可能需要管理员权限
2. **防火墙**：首次运行可能需要允许 Python 访问网络
3. **杀毒软件**：建议将项目目录添加到白名单
4. **Python 路径**：确保 Python 已添加到系统 PATH

## 🔄 脚本依赖关系

```
install.bat
    ↓ 创建
start.bat ← .env
    ↓ 运行
stop.bat ← start.bat

check_status.bat → fix.bat
service_manager.bat → start.bat
```

## 📞 快速参考

| 问题 | 解决方案 |
|------|----------|
| 程序无法启动 | 运行 `fix.bat` |
| 端口被占用 | 修改 .env 中的 PORT |
| 依赖缺失 | 运行 `install.bat` |
| 需要开机自启 | 运行 `service_manager.bat` |
| 查看系统状态 | 运行 `check_status.bat` |

## 📚 文档索引

- [README.md](README.md) - 项目主文档
- [README_WINDOWS.md](README_WINDOWS.md) - Windows 快速开始
- [WINDOWS_INSTALL.md](WINDOWS_INSTALL.md) - Windows 详细安装指南
- [本文件](WINDOWS_FILES.md) - Windows 文件清单

---

**最后更新**：2024-02-14
