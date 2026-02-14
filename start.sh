#!/bin/bash

echo "🚀 启动 Hummingbot Lite..."
echo ""

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "❌ 错误：配置文件不存在"
    echo "请先运行 ./install.sh 或复制 config.example.yaml 为 config.yaml"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python -c "import ccxt" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 错误：依赖未安装"
    echo "请先运行: ./install.sh"
    exit 1
fi
echo "✓ 依赖已安装"
echo ""

# 启动程序
echo "启动程序..."
echo "访问 http://localhost:5000 查看控制面板"
echo "按 Ctrl+C 停止程序"
echo ""
python src/main.py
