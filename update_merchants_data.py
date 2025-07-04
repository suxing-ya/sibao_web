#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import pymysql

load_dotenv('.env')

# 网页显示的商家数据
merchants_data = [
    ('0001', 'SB', '思宝'),
    ('0002', 'zjs', '朱教授'),
    ('0003', 'j', '进'),
    ('0004', 'r', '然'),
    ('0005', 'cxz', '相册纸'),
    ('0006', 'DIYmj', 'DIY毛巾'),
    ('0007', 'y', '光'),
    ('0008', 'sct', '素材甜'),
    ('0009', 'kn', '康娜'),
    ('0010', 'CJ', '茳茳'),
    ('0012', 'cff', '陈芬芬'),
    ('0013', 'JANE', 'JANE')
]

try:
    connection = pymysql.connect(
        host=os.environ.get('DB_HOST'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'),
        charset='utf8mb4',
        use_unicode=True,
        init_command="SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    
    with connection.cursor() as cursor:
        print("🗑️  清空现有merchants数据...")
        cursor.execute("DELETE FROM merchants")
        
        print("📥 插入新的商家数据...")
        for merchant_id_code, merchant_code, merchant_name in merchants_data:
            cursor.execute("""
                INSERT INTO merchants (merchant_id_code, merchant_code, merchant_name, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (merchant_id_code, merchant_code, merchant_name))
            print(f"  ✅ 已添加: {merchant_id_code} - {merchant_code} ({merchant_name})")
        
        connection.commit()
        print(f"\n🎉 成功更新 {len(merchants_data)} 条商家数据！")
        
        # 验证数据
        cursor.execute("SELECT merchant_id_code, merchant_code, merchant_name FROM merchants ORDER BY merchant_id_code")
        result = cursor.fetchall()
        print("\n📋 验证更新后的数据:")
        for row in result:
            print(f"  {row[0]} - {row[1]} ({row[2]})")
    
    connection.close()
    
except Exception as e:
    print(f"❌ 错误: {e}") 