#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入测试用户数据到MySQL数据库的脚本
"""

import os
import sys
from datetime import datetime
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env')

def create_test_user():
    """创建测试用户数据"""
    try:
        # 数据库连接配置
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # 检查是否已存在测试用户
            cursor.execute("SELECT id FROM users WHERE email = %s", ('test@example.com',))
            if cursor.fetchone():
                print("测试用户已存在，跳过创建")
                return
            
            # 插入测试用户数据
            # 注意：这里密码使用明文存储，实际生产环境应该使用哈希
            test_users = [
                {
                    'email': 'admin@sibao.com',
                    'password': 'admin123',
                    'full_name': '系统管理员',
                    'role': 'admin',
                    'is_active': True
                },
                {
                    'email': 'test@example.com', 
                    'password': 'test123',
                    'full_name': '测试用户',
                    'role': 'user',
                    'is_active': True
                }
            ]
            
            for user in test_users:
                cursor.execute("""
                    INSERT INTO users (email, password, full_name, role, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user['email'],
                    user['password'],
                    user['full_name'],
                    user['role'],
                    user['is_active'],
                    datetime.now(),
                    datetime.now()
                ))
                
                print(f"已创建用户: {user['email']} / {user['password']} ({user['role']})")
            
            connection.commit()
            print("\n测试用户创建成功！")
            print("=" * 50)
            print("登录账号信息：")
            print("管理员账号:")
            print("  邮箱: admin@sibao.com")
            print("  密码: admin123")
            print()
            print("普通用户账号:")
            print("  邮箱: test@example.com") 
            print("  密码: test123")
            print("=" * 50)
            
    except Exception as e:
        print(f"创建测试用户失败: {str(e)}")
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    create_test_user() 