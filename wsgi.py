#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI入口文件
用于宝塔面板Python项目部署
"""

import sys
import os
import traceback

# 添加项目路径到Python路径
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

print(f"项目路径: {project_path}")
print(f"Python路径: {sys.path}")

try:
    # 检查环境变量文件
    env_file = os.path.join(project_path, '.env')
    if os.path.exists(env_file):
        print(f"找到环境变量文件: {env_file}")
    else:
        print(f"警告: 未找到环境变量文件 {env_file}")
    
    # 导入Flask应用
    from app import app
    print("成功导入Flask应用")
    
    # WSGI应用对象
    application = app
    
except Exception as e:
    print(f"导入Flask应用时出错: {e}")
    traceback.print_exc()
    # 创建一个简单的WSGI应用来显示错误
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        error_msg = f"应用启动失败: {str(e)}\n\n{traceback.format_exc()}"
        return [error_msg.encode('utf-8')]

if __name__ == "__main__":
    try:
        application.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"应用运行时出错: {e}")
        traceback.print_exc() 