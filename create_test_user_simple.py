#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版本的测试用户创建脚本
请直接在代码中修改数据库连接配置
"""

import pymysql
from datetime import datetime
import uuid

# 请修改这里的数据库连接配置为你的腾讯云MySQL信息
DB_CONFIG = {
    'host': '你的腾讯云MySQL地址',  # 例如：cdb-xxxxxxxxx.cd.tencentcdb.com
    'port': 3306,
    'user': '你的数据库用户名',      # 例如：root
    'password': '你的数据库密码',    # 你的MySQL密码
    'database': 'sibao',          # 数据库名称（根据截图修改）
    'charset': 'utf8mb4'
}

def create_test_user():
    """创建测试用户数据"""
    try:
        # 连接数据库
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ 成功连接到数据库！")
        
        with connection.cursor() as cursor:
            # 检查现有用户
            cursor.execute("SELECT username, role FROM profiles")
            existing_users = cursor.fetchall()
            print(f"📊 现有用户 ({len(existing_users)}个):")
            for user in existing_users:
                print(f"   - {user[0]} ({user[1]})")
            print()
            
            # 检查是否已存在测试管理员
            cursor.execute("SELECT id FROM profiles WHERE username = %s", ('admin@sibao.com',))
            if cursor.fetchone():
                print("✅ 管理员账号已存在，跳过创建")
            else:
                # 插入新的管理员用户
                admin_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO profiles (id, username, password, created_at, role, notes, permissions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    admin_id,
                    'admin@sibao.com',
                    'admin123',
                    datetime.now(),
                    'admin',
                    '测试管理员账户',
                    '["*"]'  # JSON格式的权限
                ))
                print("✅ 已创建测试管理员账号")
            
            # 检查测试用户
            cursor.execute("SELECT id FROM profiles WHERE username = %s", ('test@example.com',))
            if cursor.fetchone():
                print("✅ 测试用户已存在，跳过创建")
            else:
                # 插入测试用户
                user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO profiles (id, username, password, created_at, role, notes, permissions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    'test@example.com',
                    'test123',
                    datetime.now(),
                    'user',
                    '测试普通用户',
                    '["read"]'  # JSON格式的权限
                ))
                print("✅ 已创建测试用户")
            
            connection.commit()
            print("\n" + "="*60)
            print("🎉 测试用户创建成功！")
            print("登录账号信息：")
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
            print("="*60)
            
    except pymysql.Error as e:
        print(f"❌ 数据库错误: {e}")
        print("\n请检查以下问题：")
        print("1. 数据库连接配置是否正确")
        print("2. 数据库服务是否正常运行")
        print("3. 数据库中是否已创建了 profiles 表")
        print("4. 网络连接是否正常")
        
    except Exception as e:
        print(f"❌ 创建测试用户失败: {e}")
        
    finally:
        if 'connection' in locals():
            connection.close()
            print("🔒 数据库连接已关闭")

if __name__ == '__main__':
    print("🚀 开始创建测试用户...")
    print("📋 基于你的数据库结构：")
    print("   - 数据库名: sibao")
    print("   - 表名: profiles")
    print("   - 用户名字段: username")
    print()
    print("请确保：")
    print("1. 已修改了脚本中的数据库连接配置")
    print("2. 网络连接正常")
    print("3. 数据库用户有插入权限")
    print()
    
    create_test_user()