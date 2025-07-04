#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase 到腾讯云 PostgreSQL 数据迁移工具
使用前请确保已配置好环境变量
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client
from datetime import datetime
import uuid

class DatabaseMigrator:
    def __init__(self):
        # Supabase配置
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        # 腾讯云PostgreSQL配置
        self.tencent_host = os.environ.get("DB_HOST")
        self.tencent_port = os.environ.get("DB_PORT", "5432")
        self.tencent_db = os.environ.get("DB_NAME")
        self.tencent_user = os.environ.get("DB_USER")
        self.tencent_password = os.environ.get("DB_PASSWORD")
        
        # 验证配置
        self.validate_config()
        
        # 初始化连接
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
    def validate_config(self):
        """验证环境变量配置"""
        required_vars = [
            "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
            "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"缺少环境变量: {', '.join(missing_vars)}")
        
        print("✅ 环境变量配置验证通过")
    
    def get_tencent_connection(self):
        """获取腾讯云数据库连接"""
        return psycopg2.connect(
            host=self.tencent_host,
            port=self.tencent_port,
            database=self.tencent_db,
            user=self.tencent_user,
            password=self.tencent_password,
            cursor_factory=RealDictCursor
        )
    
    def migrate_profiles(self):
        """迁移用户档案表"""
        print("开始迁移 profiles 表...")
        
        try:
            # 从Supabase获取数据
            response = self.supabase.from_('profiles').select("*").execute()
            data = response.data
            
            if not data:
                print("profiles 表无数据，跳过迁移")
                return
            
            # 连接腾讯云数据库
            with self.get_tencent_connection() as conn:
                cursor = conn.cursor()
                
                # 清空目标表（可选）
                cursor.execute("DELETE FROM profiles WHERE username != 'admin'")
                
                # 插入数据
                for record in data:
                    cursor.execute("""
                        INSERT INTO profiles (id, username, created_at, role, notes, permissions)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username) DO UPDATE SET
                            role = EXCLUDED.role,
                            notes = EXCLUDED.notes,
                            permissions = EXCLUDED.permissions
                    """, (
                        record['id'],
                        record['username'],
                        record['created_at'],
                        record.get('role', 'normal'),
                        record.get('notes', ''),
                        json.dumps(record.get('permissions', []))
                    ))
                
                conn.commit()
                print(f"✅ profiles 表迁移完成，共 {len(data)} 条记录")
                
        except Exception as e:
            print(f"❌ profiles 表迁移失败: {e}")
    
    def migrate_merchants(self):
        """迁移商家表"""
        print("开始迁移 merchants 表...")
        
        try:
            # 从Supabase获取数据
            response = self.supabase.from_('merchants').select("*").execute()
            data = response.data
            
            if not data:
                print("merchants 表无数据，跳过迁移")
                return
            
            # 连接腾讯云数据库
            with self.get_tencent_connection() as conn:
                cursor = conn.cursor()
                
                # 清空目标表（保留示例数据）
                cursor.execute("DELETE FROM merchants WHERE merchant_code NOT LIKE 'M%'")
                
                # 插入数据
                for record in data:
                    cursor.execute("""
                        INSERT INTO merchants (id, merchant_code, merchant_name, created_at, merchant_id_code)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (merchant_code) DO UPDATE SET
                            merchant_name = EXCLUDED.merchant_name,
                            merchant_id_code = EXCLUDED.merchant_id_code
                    """, (
                        record['id'],
                        record['merchant_code'],
                        record['merchant_name'],
                        record['created_at'],
                        record.get('merchant_id_code', '')
                    ))
                
                conn.commit()
                print(f"✅ merchants 表迁移完成，共 {len(data)} 条记录")
                
        except Exception as e:
            print(f"❌ merchants 表迁移失败: {e}")
    
    def migrate_shipping_costs(self):
        """迁移运费成本表（重要业务数据）"""
        print("开始迁移 shipping_costs 表...")
        
        try:
            # 从Supabase获取数据
            response = self.supabase.from_('shipping_costs').select("*").execute()
            data = response.data
            
            if not data:
                print("shipping_costs 表无数据，跳过迁移")
                return
            
            # 连接腾讯云数据库
            with self.get_tencent_connection() as conn:
                cursor = conn.cursor()
                
                # 清空目标表
                cursor.execute("TRUNCATE TABLE shipping_costs")
                
                # 插入数据
                for record in data:
                    cursor.execute("""
                        INSERT INTO shipping_costs (
                            id, created_at, date, freight_unit_price, 
                            total_settle_weight, actual_weight_with_box, 
                            tracking_number, shipment_id, merchants, 
                            order_number, settlement_status, box_count
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        record['id'],
                        record['created_at'],
                        record.get('date'),
                        record.get('freight_unit_price'),
                        record.get('total_settle_weight'),
                        record.get('actual_weight_with_box'),
                        record.get('tracking_number'),
                        record.get('shipment_id'),
                        json.dumps(record.get('merchants', [])),
                        record.get('order_number'),
                        record.get('settlement_status', 'pending'),
                        record.get('box_count', 0)
                    ))
                
                conn.commit()
                print(f"✅ shipping_costs 表迁移完成，共 {len(data)} 条记录")
                
        except Exception as e:
            print(f"❌ shipping_costs 表迁移失败: {e}")
    
    def migrate_temu_workflow(self):
        """迁移Temu工作流表"""
        print("开始迁移 temu_workflow 表...")
        
        try:
            # 从Supabase获取数据
            response = self.supabase.from_('temu_workflow').select("*").execute()
            data = response.data
            
            if not data:
                print("temu_workflow 表无数据，跳过迁移")
                return
            
            # 连接腾讯云数据库
            with self.get_tencent_connection() as conn:
                cursor = conn.cursor()
                
                # 清空目标表
                cursor.execute("TRUNCATE TABLE temu_workflow CASCADE")
                
                # 插入数据
                for record in data:
                    cursor.execute("""
                        INSERT INTO temu_workflow (
                            id, cn_send_date, main_tracking_id, box_code, 
                            box_count, inner_count, status, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        record['id'],
                        record.get('cn_send_date'),
                        record.get('main_tracking_id'),
                        record.get('box_code'),
                        record.get('box_count', 0),
                        record.get('inner_count', 0),
                        record.get('status', 'pending'),
                        record.get('created_at', datetime.now())
                    ))
                
                conn.commit()
                print(f"✅ temu_workflow 表迁移完成，共 {len(data)} 条记录")
                
        except Exception as e:
            print(f"❌ temu_workflow 表迁移失败: {e}")
    
    def migrate_temu_details_and_ids(self):
        """迁移Temu相关详情表"""
        print("开始迁移 temu_shipment_details 和 temu_shipment_ids 表...")
        
        try:
            # 迁移 temu_shipment_details
            response = self.supabase.from_('temu_shipment_details').select("*").execute()
            details_data = response.data
            
            # 迁移 temu_shipment_ids
            response = self.supabase.from_('temu_shipment_ids').select("*").execute()
            ids_data = response.data
            
            with self.get_tencent_connection() as conn:
                cursor = conn.cursor()
                
                # 清空目标表
                cursor.execute("DELETE FROM temu_shipment_details")
                cursor.execute("DELETE FROM temu_shipment_ids")
                
                # 插入详情数据
                if details_data:
                    for record in details_data:
                        cursor.execute("""
                            INSERT INTO temu_shipment_details (
                                id, workflow_id, merchant, quantity, 
                                scan_channel, notes, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            record['id'],
                            record['workflow_id'],
                            record['merchant'],
                            record['quantity'],
                            record.get('scan_channel'),
                            record.get('notes'),
                            record.get('created_at', datetime.now())
                        ))
                
                # 插入ID数据
                if ids_data:
                    for record in ids_data:
                        cursor.execute("""
                            INSERT INTO temu_shipment_ids (
                                id, workflow_id, shipment_id_value, created_at
                            ) VALUES (%s, %s, %s, %s)
                        """, (
                            record['id'],
                            record['workflow_id'],
                            record['shipment_id_value'],
                            record.get('created_at', datetime.now())
                        ))
                
                conn.commit()
                print(f"✅ temu详情表迁移完成，详情: {len(details_data or [])} 条，ID: {len(ids_data or [])} 条")
                
        except Exception as e:
            print(f"❌ temu详情表迁移失败: {e}")
    
    def verify_migration(self):
        """验证迁移结果"""
        print("\n开始验证迁移结果...")
        
        tables = ['profiles', 'merchants', 'shipping_costs', 'temu_workflow', 
                  'temu_shipment_details', 'temu_shipment_ids']
        
        try:
            with self.get_tencent_connection() as conn:
                cursor = conn.cursor()
                
                print("表名\t\t\t记录数")
                print("-" * 40)
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"{table:<20}\t{count}")
                
                print("-" * 40)
                print("✅ 迁移验证完成")
                
        except Exception as e:
            print(f"❌ 验证失败: {e}")
    
    def run_migration(self):
        """执行完整迁移流程"""
        print("🚀 开始数据库迁移...")
        print("=" * 50)
        
        try:
            # 按依赖关系顺序迁移
            self.migrate_profiles()
            self.migrate_merchants()
            self.migrate_shipping_costs()
            self.migrate_temu_workflow()
            self.migrate_temu_details_and_ids()
            
            # 验证迁移结果
            self.verify_migration()
            
            print("\n" + "=" * 50)
            print("🎉 数据库迁移完成！")
            print("\n下一步：")
            print("1. 更新应用的 .env 文件，配置腾讯云数据库连接")
            print("2. 修改应用代码，使用新的数据库连接")
            print("3. 测试所有功能是否正常")
            
        except Exception as e:
            print(f"\n❌ 迁移过程中出现错误: {e}")
            print("请检查配置和网络连接")

def main():
    """主函数"""
    print("Supabase 到腾讯云 PostgreSQL 数据迁移工具")
    print("=" * 50)
    
    # 检查环境变量
    required_vars = [
        "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
        "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"
    ]
    
    print("检查环境变量...")
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # 隐藏敏感信息
            if 'KEY' in var or 'PASSWORD' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: 未设置")
            return
    
    print("\n开始迁移...")
    migrator = DatabaseMigrator()
    migrator.run_migration()

if __name__ == "__main__":
    main() 