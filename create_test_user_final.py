#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终版本的测试用户创建脚本
自动匹配你的数据库结构：sibao.profiles表
"""

import pymysql
from datetime import datetime
import uuid
import os

# 数据库配置（直接配置，无需环境变量）
DB_CONFIG = {
    'host': '你的腾讯云MySQL地址',  # 例如：cdb-xxxxxxxxx.cd.tencentcdb.com
    'port': 3306,
    'user': '你的数据库用户名',      # 例如：root
    'password': '你的数据库密码',    # 你的MySQL密码
    'database': 'sibao',          # 你的数据库名称
    'charset': 'utf8mb4'
}

def create_test_users():
    """创建测试用户数据"""
    try:
        # 连接数据库
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ 成功连接到数据库 sibao！")
        
        with connection.cursor() as cursor:
            # 显示现有用户
            cursor.execute("SELECT username, role, created_at FROM profiles ORDER BY created_at")
            existing_users = cursor.fetchall()
            print(f"\n📊 现有用户 ({len(existing_users)}个):")
            for i, user in enumerate(existing_users, 1):
                print(f"   {i}. {user[0]} ({user[1]}) - 创建于 {user[2]}")
            print()
            
            # 创建测试管理员账号
            test_admin_username = 'admin@sibao.com'
            cursor.execute("SELECT id FROM profiles WHERE username = %s", (test_admin_username,))
            if cursor.fetchone():
                print("✅ 测试管理员账号已存在，跳过创建")
            else:
                admin_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO profiles (id, username, password, created_at, role, notes, permissions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    admin_id,
                    test_admin_username,
                    'admin123',
                    datetime.now(),
                    'admin',
                    '测试管理员账户',
                    '["*"]'
                ))
                print("✅ 已创建测试管理员账号")
            
            # 创建测试用户账号
            test_user_username = 'test@example.com'
            cursor.execute("SELECT id FROM profiles WHERE username = %s", (test_user_username,))
            if cursor.fetchone():
                print("✅ 测试用户已存在，跳过创建")
            else:
                user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO profiles (id, username, password, created_at, role, notes, permissions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    test_user_username,
                    'test123',
                    datetime.now(),
                    'user',
                    '测试普通用户',
                    '["read"]'
                ))
                print("✅ 已创建测试用户")
            
            connection.commit()
            print("\n" + "="*70)
            print("🎉 测试用户创建完成！")
            print()
            print("📋 所有可用的登录账号：")
            print()
            print("🔑 现有管理员账号:")
            print("   用户名: 229876360@qq.com")
            print("   密码: 123456789")
            print()
            print("🆕 新增管理员账号:")
            print("   用户名: admin@sibao.com")
            print("   密码: admin123")
            print()
            print("👤 测试用户账号:")
            print("   用户名: test@example.com")
            print("   密码: test123")
            print()
            print("🌐 登录地址:")
            print("   管理员登录: http://localhost:5000/admin/login")
            print("   用户登录: http://localhost:5000/login")
            print("="*70)
            
    except pymysql.Error as e:
        print(f"❌ 数据库错误: {e}")
        print("\n💡 请检查以下问题：")
        print("1. 数据库连接配置是否正确")
        print("2. 数据库服务是否正常运行")
        print("3. 数据库中是否已创建了 profiles 表")
        print("4. 网络连接是否正常")
        print("5. 数据库用户是否有插入权限")
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        
    finally:
        if 'connection' in locals():
            connection.close()
            print("🔒 数据库连接已关闭")

def test_connection():
    """测试数据库连接"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ 数据库连接测试成功！")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"📊 当前数据库: {db_name}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 数据库表: {[table[0] for table in tables]}")
            
        connection.close()
        return True
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

if __name__ == '__main__':
    print("🚀 开始创建测试用户...")
    print("📋 目标数据库结构：")
    print("   - 数据库名: sibao")
    print("   - 表名: profiles")
    print("   - 用户名字段: username")
    print()
    
    # 提醒用户修改配置
    if 'localhost' in DB_CONFIG['host'] or '你的' in DB_CONFIG['host']:
        print("⚠️  请先修改脚本中的数据库配置信息！")
        print("   修改 DB_CONFIG 中的以下字段：")
        print(f"   - host: {DB_CONFIG['host']}")
        print(f"   - user: {DB_CONFIG['user']}")
        print(f"   - password: {DB_CONFIG['password']}")
        print()
        exit(1)
    
    # 测试连接
    if test_connection():
        print()
        create_test_users()
    else:
        print("请检查数据库配置后重试！") 