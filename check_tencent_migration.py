#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云数据库迁移检查工具
用于验证数据库连接和表结构
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_tencent_connection():
    """检查腾讯云数据库连接"""
    print("=" * 50)
    print("检查腾讯云PostgreSQL数据库连接...")
    
    # 获取环境变量
    host = os.environ.get('DB_HOST')
    port = os.environ.get('DB_PORT', '5432')
    database = os.environ.get('DB_NAME')
    user = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASSWORD')
    
    if not all([host, database, user, password]):
        print("❌ 缺少数据库连接配置")
        print("请确保设置了以下环境变量：")
        print("- DB_HOST")
        print("- DB_NAME")
        print("- DB_USER")
        print("- DB_PASSWORD")
        return False
    
    try:
        # 尝试连接
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        
        print(f"✅ 数据库连接成功")
        print(f"   服务器: {host}:{port}")
        print(f"   数据库: {database}")
        print(f"   版本: {version}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_table_structure():
    """检查表结构是否正确创建"""
    print("\n" + "=" * 50)
    print("检查数据库表结构...")
    
    expected_tables = [
        'profiles', 'merchants', 'shipping_costs', 
        'temu_workflow', 'temu_shipment_details', 'temu_shipment_ids'
    ]
    
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print("数据库表检查结果：")
        print("-" * 30)
        
        all_tables_exist = True
        for table in expected_tables:
            if table in existing_tables:
                # 检查表的记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ {table:<20} ({count} 条记录)")
            else:
                print(f"❌ {table:<20} (不存在)")
                all_tables_exist = False
        
        # 显示额外的表
        extra_tables = set(existing_tables) - set(expected_tables)
        if extra_tables:
            print("\n其他表：")
            for table in extra_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table:<20} ({count} 条记录)")
        
        conn.close()
        return all_tables_exist
        
    except Exception as e:
        print(f"❌ 表结构检查失败: {e}")
        return False

def check_indexes():
    """检查索引是否创建"""
    print("\n" + "=" * 50)
    print("检查数据库索引...")
    
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # 查询索引
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        
        indexes = cursor.fetchall()
        
        print("数据库索引：")
        print("-" * 30)
        
        current_table = None
        for index in indexes:
            if index['tablename'] != current_table:
                current_table = index['tablename']
                print(f"\n{current_table}:")
            
            index_name = index['indexname']
            if not index_name.endswith('_pkey'):  # 跳过主键索引
                print(f"  ✅ {index_name}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 索引检查失败: {e}")
        return False

def test_basic_operations():
    """测试基本数据库操作"""
    print("\n" + "=" * 50)
    print("测试基本数据库操作...")
    
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # 测试插入
        test_merchant_code = 'TEST001'
        cursor.execute("""
            INSERT INTO merchants (merchant_code, merchant_name, merchant_id_code)
            VALUES (%s, %s, %s)
            ON CONFLICT (merchant_code) DO UPDATE SET
                merchant_name = EXCLUDED.merchant_name
            RETURNING id
        """, (test_merchant_code, '测试商家', 'TEST_SHOP'))
        
        merchant_id = cursor.fetchone()['id']
        print("✅ 插入操作测试通过")
        
        # 测试查询
        cursor.execute("""
            SELECT merchant_code, merchant_name 
            FROM merchants 
            WHERE merchant_code = %s
        """, (test_merchant_code,))
        
        result = cursor.fetchone()
        if result:
            print("✅ 查询操作测试通过")
        
        # 测试更新
        cursor.execute("""
            UPDATE merchants 
            SET merchant_name = %s 
            WHERE merchant_code = %s
        """, ('测试商家(已更新)', test_merchant_code))
        
        if cursor.rowcount > 0:
            print("✅ 更新操作测试通过")
        
        # 清理测试数据
        cursor.execute("DELETE FROM merchants WHERE merchant_code = %s", (test_merchant_code,))
        print("✅ 删除操作测试通过")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 基本操作测试失败: {e}")
        return False

def generate_migration_report():
    """生成迁移报告"""
    print("\n" + "=" * 50)
    print("生成迁移状态报告...")
    
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # 统计各表数据量
        tables_info = []
        tables = ['profiles', 'merchants', 'shipping_costs', 'temu_workflow', 
                  'temu_shipment_details', 'temu_shipment_ids']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                
                # 获取最新记录时间
                if table in ['profiles', 'merchants', 'shipping_costs', 'temu_workflow']:
                    cursor.execute(f"SELECT MAX(created_at) as latest FROM {table}")
                    latest = cursor.fetchone()['latest']
                    latest_str = latest.strftime('%Y-%m-%d %H:%M:%S') if latest else '无'
                else:
                    latest_str = '无'
                
                tables_info.append({
                    'table': table,
                    'count': count,
                    'latest': latest_str
                })
            except:
                tables_info.append({
                    'table': table,
                    'count': 0,
                    'latest': '表不存在'
                })
        
        print("\n数据库迁移状态报告")
        print("=" * 60)
        print(f"{'表名':<20} {'记录数':<10} {'最新记录时间':<20}")
        print("-" * 60)
        
        total_records = 0
        for info in tables_info:
            print(f"{info['table']:<20} {info['count']:<10} {info['latest']:<20}")
            total_records += info['count']
        
        print("-" * 60)
        print(f"{'总计':<20} {total_records:<10}")
        
        conn.close()
        
        # 生成建议
        print("\n迁移建议：")
        if total_records == 0:
            print("⚠️  数据库为空，建议：")
            print("   1. 如果是新部署，可以直接使用")
            print("   2. 如果需要迁移数据，请运行迁移脚本")
        else:
            print("✅ 数据库包含数据，建议：")
            print("   1. 验证数据完整性")
            print("   2. 测试应用功能")
            print("   3. 备份重要数据")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        return False

def main():
    """主函数"""
    print("腾讯云PostgreSQL数据库迁移检查工具")
    print("=" * 50)
    
    # 检查环境变量
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 缺少必要的环境变量：")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n请确保设置了所有必要的环境变量")
        return
    
    # 执行检查
    checks = [
        ("数据库连接", check_tencent_connection),
        ("表结构", check_table_structure),
        ("索引", check_indexes),
        ("基本操作", test_basic_operations),
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    # 生成报告
    generate_migration_report()
    
    # 总结
    print("\n" + "=" * 50)
    print("检查结果总结：")
    passed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项检查通过")
    
    if passed == len(results):
        print("🎉 所有检查通过！数据库迁移准备就绪。")
    else:
        print("⚠️  部分检查失败，请根据上述提示进行修复。")

if __name__ == "__main__":
    main()