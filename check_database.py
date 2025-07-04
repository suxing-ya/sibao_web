#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库连接和表结构的脚本
"""

import pymysql

# 请修改这里的数据库连接配置为你的腾讯云MySQL信息
DB_CONFIG = {
    'host': '你的腾讯云MySQL地址',  # 例如：cdb-xxxxxxxxx.cd.tencentcdb.com
    'port': 3306,
    'user': '你的数据库用户名',      # 例如：root
    'password': '你的数据库密码',    # 你的MySQL密码
    'database': 'sibao_web',      # 数据库名称
    'charset': 'utf8mb4'
}

def check_database():
    """检查数据库连接和表结构"""
    try:
        # 连接数据库
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ 成功连接到数据库！")
        
        with connection.cursor() as cursor:
            # 检查数据库名称
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"📊 当前数据库: {db_name}")
            
            # 检查所有表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print(f"📋 数据库中的表 ({len(tables)}个):")
                for table in tables:
                    print(f"   - {table[0]}")
                    
                # 检查users表结构
                if ('users',) in tables:
                    print("\n👤 users表结构:")
                    cursor.execute("DESCRIBE users")
                    columns = cursor.fetchall()
                    for col in columns:
                        print(f"   - {col[0]} ({col[1]})")
                        
                    # 检查users表中的数据
                    cursor.execute("SELECT COUNT(*) FROM users")
                    user_count = cursor.fetchone()[0]
                    print(f"   用户数量: {user_count}")
                    
                    if user_count > 0:
                        cursor.execute("SELECT email, role FROM users")
                        users = cursor.fetchall()
                        print("   现有用户:")
                        for user in users:
                            print(f"     - {user[0]} ({user[1]})")
                else:
                    print("❌ users表不存在！")
                    print("请先执行 create_mysql_tables.sql 创建表结构")
            else:
                print("❌ 数据库中没有任何表！")
                print("请先执行 create_mysql_tables.sql 创建表结构")
            
    except pymysql.Error as e:
        print(f"❌ 数据库错误: {e}")
        print("\n请检查以下问题：")
        print("1. 数据库连接配置是否正确")
        print("2. 数据库服务是否正常运行") 
        print("3. 网络连接是否正常")
        print("4. 数据库用户权限是否足够")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        
    finally:
        if 'connection' in locals():
            connection.close()
            print("\n🔒 数据库连接已关闭")

if __name__ == '__main__':
    print("🔍 开始检查数据库状态...")
    print("=" * 50)
    check_database()
    print("=" * 50) 