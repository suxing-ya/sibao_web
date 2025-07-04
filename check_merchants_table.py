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
        print("📋 腾讯云数据库merchants表当前结构:")
        cursor.execute("DESCRIBE merchants")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        print(f"\n📊 merchants表数据:")
        cursor.execute("SELECT * FROM merchants")
        data = cursor.fetchall()
        for i, row in enumerate(data, 1):
            print(f"  {i}. {row}")
            
        print(f"\n🎯 网页需要的字段:")
        print("  - merchant_id_code (商家编号)")
        print("  - merchant_code (商家代号)")  
        print("  - merchant_name (商家名称)")
    
    connection.close()
    
except Exception as e:
    print(f"❌ 错误: {e}") 