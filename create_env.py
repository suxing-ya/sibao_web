#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建.env配置文件
"""

env_content = """DB_TYPE=mysql
DB_HOST=43.160.251.20
DB_PORT=3306
DB_NAME=sibao
DB_USER=sibao
DB_PASSWORD=53NArDapXDK7FNCJ
DB_CHARSET=utf8mb4
FLASK_SECRET_KEY=sibao-web-secret-key-2024
"""

# 创建.env文件
with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)

print("✅ .env文件创建成功！")

# 验证文件内容
with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()
    print("\n文件内容:")
    print(content) 