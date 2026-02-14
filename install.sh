#!/bin/bash

echo "=========================================="
echo "  Hummingbot Lite - 安装脚本"
echo "=========================================="
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ 错误：未找到 Python"
    exit 1
fi
echo "✓ Python 已安装"
echo ""

# 安装依赖
echo "安装 Python 依赖..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 错误：依赖安装失败"
    exit 1
fi
echo "✓ 依赖安装成功"
echo ""

# 检查配置文件
echo "检查配置文件..."
if [ ! -f "config.yaml" ]; then
    echo "⚠️  配置文件不存在，从模板创建..."
    cp config.example.yaml config.yaml
    echo "✓ 配置文件已创建：config.yaml"
    echo ""
    echo "⚠️  重要提示："
    echo "1. 打开 config.yaml 文件"
    echo "2. 填写您的 OKX API 密钥"
    echo "3. 根据需要调整策略参数"
    echo ""
else
    echo "✓ 配置文件已存在"
fi

echo ""
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 编辑 config.yaml 填写 OKX API 密钥"
echo "2. 运行: python src/main.py"
echo "3. 访问 http://localhost:5000 查看控制面板"
echo ""
