#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试环境变量加载
"""

import os
from dotenv import load_dotenv

print("测试环境变量加载...")

# 加载.env文件
load_dotenv()

print(f"DB_HOST: {os.environ.get('DB_HOST')}")
print(f"DB_USER: {os.environ.get('DB_USER')}")
print(f"DB_PASSWORD: {os.environ.get('DB_PASSWORD')}")
print(f"DB_NAME: {os.environ.get('DB_NAME')}")
print(f"FLASK_SECRET_KEY: {os.environ.get('FLASK_SECRET_KEY')}")

# 检查.env文件是否存在
if os.path.exists('.env'):
    print("\n.env文件存在")
    with open('.env', 'r', encoding='utf-8') as f:
        print("文件内容:")
        print(f.read())
else:
    print("\n.env文件不存在") 