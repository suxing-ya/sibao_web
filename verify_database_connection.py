#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证当前应用连接的数据库信息
"""

import os
import sys
from dotenv import load_dotenv

# 尝试加载环境变量
load_dotenv('.env')

print("🔍 验证当前数据库连接配置...")
print("=" * 60)

# 检查环境变量
print("📋 环境变量配置:")
mysql_vars = {
    'MYSQL_HOST': os.environ.get('MYSQL_HOST'),
    'MYSQL_PORT': os.environ.get('MYSQL_PORT'),
    'MYSQL_USER': os.environ.get('MYSQL_USER'),
    'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD'),
    'MYSQL_DATABASE': os.environ.get('MYSQL_DATABASE')
}

db_vars = {
    'DB_HOST': os.environ.get('DB_HOST'),
    'DB_PORT': os.environ.get('DB_PORT'),
    'DB_USER': os.environ.get('DB_USER'),
    'DB_PASSWORD': os.environ.get('DB_PASSWORD'),
    'DB_NAME': os.environ.get('DB_NAME')
}

print("MYSQL_* 变量:")
for key, value in mysql_vars.items():
    print(f"  {key}: {value if value else '未设置'}")

print("\nDB_* 变量:")
for key, value in db_vars.items():
    print(f"  {key}: {value if value else '未设置'}")

print("\n" + "=" * 60)

# 尝试连接数据库并获取信息
try:
    from db_mysql import MySQLDatabase
    
    print("🔌 尝试连接数据库...")
    db = MySQLDatabase()
    
    # 获取数据库连接信息
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            # 获取当前数据库信息
            cursor.execute("SELECT CONNECTION_ID(), DATABASE(), USER(), @@hostname, @@version")
            info = cursor.fetchone()
            
            print("✅ 数据库连接成功！")
            print(f"📊 连接ID: {info[0]}")
            print(f"📝 当前数据库: {info[1]}")
            print(f"👤 连接用户: {info[2]}")
            print(f"🖥️  数据库主机: {info[3]}")
            print(f"📦 MySQL版本: {info[4]}")
            
            return  # 成功后直接返回，避免执行except块
            
            # 检查merchants表
            cursor.execute("SHOW TABLES LIKE 'merchants'")
            merchants_table = cursor.fetchone()
            
            if merchants_table:
                print(f"\n📋 merchants表存在")
                cursor.execute("SELECT COUNT(*) FROM merchants")
                count = cursor.fetchone()[0]
                print(f"📈 merchants表记录数: {count}")
                
                if count > 0:
                    print("\n📦 merchants表前5条数据:")
                    cursor.execute("SELECT merchant_code, merchant_name, merchant_id_code FROM merchants LIMIT 5")
                    merchants = cursor.fetchall()
                    for i, merchant in enumerate(merchants, 1):
                        print(f"  {i}. 编号:{merchant[2]} 代码:{merchant[0]} 名称:{merchant[1]}")
            else:
                print("\n❌ merchants表不存在")
                
            # 检查所有表
            cursor.execute("SHOW TABLES")
            all_tables = cursor.fetchall()
            print(f"\n📋 数据库中的所有表 ({len(all_tables)}个):")
            for table in all_tables:
                print(f"  - {table[0]}")

except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
    print("\n可能的原因:")
    print("1. 环境变量未正确配置")
    print("2. 数据库服务未启动")
    print("3. 网络连接问题")
    print("4. 数据库凭据错误")

print("\n" + "=" * 60) 