"""
Windows 环境测试脚本
用于验证 Windows 环境配置是否正确
"""
import sys
import os
import platform
from pathlib import Path

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}\n")

def test_python():
    """测试 Python 环境"""
    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    print(f"Python 编译器: {sys.version_info.compiler}")
    print(f"Python 平台: {sys.platform}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")

    # 检查 Python 版本
    if sys.version_info < (3, 10):
        print("⚠️  警告: Python 版本过低，建议使用 3.10+")
        return False
    else:
        print("✅ Python 版本符合要求")
        return True

def test_modules():
    """测试必需模块"""
    modules = [
        'asyncio',
        'logging',
        'json',
        'pathlib',
        'datetime',
        'typing'
    ]

    print("测试 Python 标准库模块:")
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            return False

    return True

def test_third_party():
    """测试第三方模块"""
    modules = {
        'fastapi': 'Web 框架',
        'uvicorn': 'ASGI 服务器',
        'websockets': 'WebSocket 支持',
        'ccxt': '交易所库',
        'aiohttp': '异步 HTTP 客户端',
        'dotenv': '环境变量管理',
        'pyyaml': 'YAML 解析'
    }

    print("测试第三方模块:")
    all_installed = True
    for module, description in modules.items():
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', '未知')
            print(f"  ✅ {module} ({version}) - {description}")
        except ImportError:
            print(f"  ❌ {module} - {description} (未安装)")
            all_installed = False

    return all_installed

def test_project_structure():
    """测试项目结构"""
    required_dirs = [
        'src',
        'src/core',
        'src/strategies',
        'src/connectors',
        'src/ui',
        'logs'
    ]

    required_files = [
        'requirements.txt',
        'src/main_multi_strategy_demo.py',
        '.env.example'
    ]

    print("测试项目目录结构:")
    all_exist = True

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ (不存在)")
            all_exist = False

    print("\n测试必需文件:")
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (不存在)")
            all_exist = False

    return all_exist

def test_env_config():
    """测试环境配置"""
    print("测试环境配置:")

    # 检查 .env 文件
    env_file = Path('.env')
    if env_file.exists():
        print("  ✅ .env 文件存在")

        # 读取 .env 内容
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        required_keys = [
            'OKX_API_KEY',
            'OKX_API_SECRET',
            'OKX_API_PASSPHRASE'
        ]

        for key in required_keys:
            if f'{key}=' in content:
                value = content.split(f'{key}=')[1].split('\n')[0]
                if 'your_' in value.lower() or 'demo_' in value.lower():
                    print(f"  ⚠️  {key}: {value} (使用演示值)")
                else:
                    print(f"  ✅ {key}: *** (已配置)")
            else:
                print(f"  ❌ {key}: 未设置")
    else:
        print("  ❌ .env 文件不存在")
        return False

    return True

def test_network():
    """测试网络连接"""
    print("测试网络连接:")
    import socket

    try:
        # 测试本地端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        port = sock.getsockname()[1]
        sock.close()
        print(f"  ✅ 本地网络正常 (端口 {port})")

        # 测试端口 5000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()

        if result == 0:
            print("  ⚠️  端口 5000 已被占用")
            return False
        else:
            print("  ✅ 端口 5000 可用")
            return True

    except Exception as e:
        print(f"  ❌ 网络测试失败: {e}")
        return False

def test_files():
    """测试文件读写权限"""
    print("测试文件读写权限:")

    try:
        # 测试写入
        test_file = Path('test_permission.tmp')
        test_file.write_text('test', encoding='utf-8')
        print("  ✅ 文件写入权限正常")

        # 测试读取
        content = test_file.read_text(encoding='utf-8')
        print("  ✅ 文件读取权限正常")

        # 测试删除
        test_file.unlink()
        print("  ✅ 文件删除权限正常")

        return True

    except Exception as e:
        print(f"  ❌ 文件权限测试失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "="*50)
    print("  Hummingbot Lite - Windows 环境测试")
    print("="*50)

    results = {}

    # 运行所有测试
    print_section("1. Python 环境")
    results['python'] = test_python()

    print_section("2. 标准库模块")
    results['standard_lib'] = test_modules()

    print_section("3. 第三方模块")
    results['third_party'] = test_third_party()

    print_section("4. 项目结构")
    results['project_structure'] = test_project_structure()

    print_section("5. 环境配置")
    results['env_config'] = test_env_config()

    print_section("6. 网络连接")
    results['network'] = test_network()

    print_section("7. 文件权限")
    results['files'] = test_files()

    # 总结
    print_section("测试总结")
    all_passed = True
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print("  🎉 所有测试通过！环境配置正常")
        print("  您可以运行 start.bat 启动程序")
    else:
        print("  ⚠️  部分测试失败，请查看上方详细信息")
        print("  建议运行 fix.bat 修复问题")
    print("="*50 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
