#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import pymysql

load_dotenv('.env')

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
        print("📋 腾讯云数据库profiles表结构:")
        cursor.execute("DESCRIBE profiles")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        print(f"\n📊 profiles表数据:")
        cursor.execute("SELECT id, username, role, created_at FROM profiles")
        data = cursor.fetchall()
        for i, row in enumerate(data, 1):
            print(f"  {i}. ID:{row[0]} 用户名:{row[1]} 角色:{row[2]} 创建时间:{row[3]}")
            
        print(f"\n🎯 子账号功能说明:")
        print("  - 新增子账号会在 profiles 表中添加新记录")
        print("  - 字段包括: username, password, role, permissions等")
    
    connection.close()
    
except Exception as e:
    print(f"❌ 错误: {e}") 