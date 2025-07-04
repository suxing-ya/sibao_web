#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宝塔部署检查脚本
用于检查项目部署环境是否正确配置
"""

import os
import sys
import subprocess

def check_python_version():
    """检查Python版本"""
    print("=" * 50)
    print("检查Python版本...")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python版本符合要求")
        return True
    else:
        print("❌ Python版本过低，需要Python 3.8或更高版本")
        return False

def check_environment_file():
    """检查环境变量文件"""
    print("=" * 50)
    print("检查环境变量文件...")
    
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ 找到环境变量文件: {env_file}")
        
        # 检查必要的环境变量
        required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "FLASK_SECRET_KEY"]
        missing_vars = []
        
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for var in required_vars:
                if var not in content or f"{var}=" not in content:
                    missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
            return False
        else:
            print("✅ 环境变量配置完整")
            return True
    else:
        print(f"❌ 未找到环境变量文件: {env_file}")
        print("请复制 env_example.txt 为 .env 并填入正确的配置")
        return False

def check_required_packages():
    """检查必要的Python包"""
    print("=" * 50)
    print("检查必要的Python包...")
    
    required_packages = [
        "flask", "werkzeug", "supabase", "python-dotenv", "flask-cors", "gunicorn"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n缺少的包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("✅ 所有必要的包都已安装")
        return True

def check_project_structure():
    """检查项目结构"""
    print("=" * 50)
    print("检查项目结构...")
    
    required_files = [
        "app.py", "wsgi.py", "requirements.txt", "templates"
    ]
    
    missing_files = []
    for item in required_files:
        if os.path.exists(item):
            print(f"✅ {item}")
        else:
            print(f"❌ {item} - 缺失")
            missing_files.append(item)
    
    if missing_files:
        print(f"\n缺少的文件/目录: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 项目结构完整")
        return True

def test_flask_import():
    """测试Flask应用导入"""
    print("=" * 50)
    print("测试Flask应用导入...")
    
    try:
        from app import app
        print("✅ Flask应用导入成功")
        return True
    except Exception as e:
        print(f"❌ Flask应用导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_config_suggestions():
    """生成配置建议"""
    print("=" * 50)
    print("宝塔面板配置建议:")
    print("""
推荐配置参数:
- Python版本: 3.9
- 启动文件: wsgi.py
- 启动方式: gunicorn
- 端口: 5000
- 进程数: 4
- 启动参数: --bind 0.0.0.0:5000 --workers 4 --timeout 120 --worker-class gthread --threads 2

如果遇到问题，请检查:
1. 确保所有文件已上传到服务器
2. 确保 .env 文件配置正确
3. 确保Python版本为3.8或更高
4. 确保所有依赖包已安装
5. 查看宝塔面板的错误日志
    """)

def main():
    """主函数"""
    print("宝塔Python项目部署检查工具")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_project_structure(),
        check_environment_file(),
        check_required_packages(),
        test_flask_import()
    ]
    
    print("=" * 50)
    print("检查结果汇总:")
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ 所有检查通过 ({passed}/{total})")
        print("项目可以部署到宝塔面板！")
    else:
        print(f"❌ 部分检查失败 ({passed}/{total})")
        print("请根据上述提示修复问题后重新检查")
    
    generate_config_suggestions()

if __name__ == "__main__":
    main() 