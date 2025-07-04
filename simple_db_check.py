#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
import pymysql

load_dotenv('.env')

print("当前数据库连接配置:")
print(f"DB_HOST: {os.environ.get('DB_HOST', '未设置')}")
print(f"DB_NAME: {os.environ.get('DB_NAME', '未设置')}")
print(f"DB_USER: {os.environ.get('DB_USER', '未设置')}")
print()

try:
    connection = pymysql.connect(
        host=os.environ.get('DB_HOST'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'),
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE(), @@hostname")
        result = cursor.fetchone()
        print(f"✅ 连接成功！")
        print(f"数据库名: {result[0]}")
        print(f"主机名: {result[1]}")
        
        cursor.execute("SELECT COUNT(*) FROM merchants")
        count = cursor.fetchone()[0]
        print(f"merchants表记录数: {count}")
        
        if count > 0:
            cursor.execute("SELECT merchant_code, merchant_name LIMIT 3")
            merchants = cursor.fetchall()
            print("前3条商家数据:")
            for m in merchants:
                print(f"  - {m[0]}: {m[1]}")
    
    connection.close()
    
except Exception as e:
    print(f"❌ 连接失败: {e}") 