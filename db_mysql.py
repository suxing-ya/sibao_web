#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL数据库连接和操作工具类
"""

import os
import json
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from datetime import datetime
import uuid

class MySQLDatabase:
    def __init__(self):
        """初始化MySQL数据库连接配置"""
        # 使用环境变量配置，兼容之前的工作配置
        self.config = {
            'host': os.environ.get('MYSQL_HOST', os.environ.get('DB_HOST', '43.160.251.20')),
            'port': int(os.environ.get('MYSQL_PORT', os.environ.get('DB_PORT', 3306))),
            'user': os.environ.get('MYSQL_USER', os.environ.get('DB_USER', 'sibao')),
            'password': os.environ.get('MYSQL_PASSWORD', os.environ.get('DB_PASSWORD', 'xxxxxx')),
            'database': os.environ.get('MYSQL_DATABASE', os.environ.get('DB_NAME', 'sibao')),
            'charset': os.environ.get('DB_CHARSET', 'utf8mb4'),
            'autocommit': True,
            'cursorclass': DictCursor
        }
        
        print(f"MySQL配置: host={self.config['host']}, user={self.config['user']}, database={self.config['database']}")
        
        # 验证配置
        # self.validate_config()  # 先注释掉验证，避免环境变量问题
    
    def validate_config(self):
        """验证数据库配置"""
        # 检查配置是否完整
        required_keys = ['host', 'user', 'password', 'database']
        for key in required_keys:
            if not self.config.get(key):
                raise ValueError(f"缺少数据库配置: {key}")
        
        print("数据库配置验证通过")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        connection = None
        try:
            connection = pymysql.connect(**self.config)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, sql, params=None, fetch_one=False, fetch_all=True):
        """执行查询"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    
                    if fetch_one:
                        return cursor.fetchone()
                    elif fetch_all:
                        return cursor.fetchall()
                    else:
                        return cursor.rowcount
        except Exception as e:
            print(f"数据库查询失败: {e}")
            raise e
    
    def execute_insert(self, sql, params=None):
        """执行插入操作"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"数据库插入失败: {e}")
            raise e
    
    def execute_update(self, sql, params=None):
        """执行更新操作"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"数据库更新失败: {e}")
            raise e
    
    def execute_delete(self, sql, params=None):
        """执行删除操作"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"数据库删除失败: {e}")
            raise e
    
    # 业务相关查询方法
    
    def get_merchants(self, search_term=None):
        """获取商家列表"""
        sql = """
        SELECT id, merchant_code, merchant_name, merchant_id_code, created_at 
        FROM merchants 
        """
        params = []
        
        if search_term:
            sql += """
            WHERE merchant_code LIKE %s 
               OR merchant_name LIKE %s 
               OR merchant_id_code LIKE %s
            """
            like_term = f"%{search_term}%"
            params.extend([like_term, like_term, like_term])
        
        sql += " ORDER BY merchant_id_code ASC"
        
        return self.execute_query(sql, params)
    
    def get_shipping_costs(self, filters=None):
        """获取运费成本数据"""
        sql = """
        SELECT id, date, tracking_number, order_number, freight_unit_price,
               total_settle_weight, actual_weight_with_box, settlement_status,
               merchants, created_at
        FROM shipping_costs
        """
        params = []
        where_conditions = []
        
        if filters:
            if filters.get('start_date'):
                where_conditions.append("date >= %s")
                params.append(filters['start_date'])
            
            if filters.get('end_date'):  
                where_conditions.append("date <= %s")
                params.append(filters['end_date'])
            
            if filters.get('tracking_numbers'):
                placeholders = ','.join(['%s'] * len(filters['tracking_numbers']))
                where_conditions.append(f"tracking_number IN ({placeholders})")
                params.extend(filters['tracking_numbers'])
            
            if filters.get('merchant_name'):
                where_conditions.append("JSON_SEARCH(merchants, 'one', %s) IS NOT NULL")
                params.append(f"%{filters['merchant_name']}%")
        
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
        
        sql += " ORDER BY date DESC"
        
        return self.execute_query(sql, params)
    
    def save_shipping_cost(self, data):
        """保存运费成本数据"""
        # 检查是否已存在（根据order_number）
        existing = self.execute_query(
            "SELECT id FROM shipping_costs WHERE order_number = %s",
            [data.get('order_number')],
            fetch_one=True
        )
        
        if existing:
            # 更新现有记录
            sql = """
            UPDATE shipping_costs SET
                date = %s, freight_unit_price = %s, total_settle_weight = %s,
                actual_weight_with_box = %s, tracking_number = %s, shipment_id = %s,
                merchants = %s
            WHERE order_number = %s
            """
            params = [
                data.get('date'),
                data.get('freight_unit_price'),
                data.get('total_settle_weight'),
                data.get('actual_weight_with_box'),
                data.get('tracking_number'),
                data.get('shipment_id'),
                json.dumps(data.get('merchants', [])),
                data.get('order_number')
            ]
            return self.execute_update(sql, params)
        else:
            # 插入新记录
            sql = """
            INSERT INTO shipping_costs (
                id, date, freight_unit_price, total_settle_weight,
                actual_weight_with_box, tracking_number, shipment_id,
                merchants, order_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = [
                str(uuid.uuid4()),
                data.get('date'),
                data.get('freight_unit_price'),
                data.get('total_settle_weight'),
                data.get('actual_weight_with_box'),
                data.get('tracking_number'),
                data.get('shipment_id'),
                json.dumps(data.get('merchants', [])),
                data.get('order_number')
            ]
            return self.execute_insert(sql, params)
    
    def update_settlement_status(self, cost_id, status):
        """更新结算状态"""
        sql = "UPDATE shipping_costs SET settlement_status = %s WHERE id = %s"
        return self.execute_update(sql, [status, cost_id])
    
    def get_temu_workflow(self, filters=None):
        """获取Temu工作流数据"""
        sql = """
        SELECT id, cn_send_date, main_tracking_id, box_code, box_count,
               inner_count, status, us_receive_date, us_box_count,
               us_actual_count, detail_table, created_at
        FROM temu_workflow
        """
        params = []
        where_conditions = []
        
        if filters:
            if filters.get('date_range'):
                if filters['date_range'] == 7:
                    where_conditions.append("cn_send_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
                elif filters['date_range'] == 10:
                    where_conditions.append("cn_send_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)")
            
            if filters.get('main_tracking_id'):
                where_conditions.append("main_tracking_id LIKE %s")
                params.append(f"%{filters['main_tracking_id']}%")
            
            if filters.get('status'):
                where_conditions.append("status = %s")
                params.append(filters['status'])
        
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
        
        sql += " ORDER BY cn_send_date DESC"
        
        return self.execute_query(sql, params)

    # ==========================================
    # 发货费用分摊表相关操作函数（新增）
    # ==========================================
    
    def save_shipping_allocation(self, data):
        """
        保存发货费用分摊数据到新的表结构
        Args:
            data: 包含主表和明细表数据的字典
        Returns:
            main_id: 主表记录ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查是否已存在相同order_number的记录
                    cursor.execute(
                        "SELECT id FROM shipping_allocation_main WHERE order_number = %s",
                        [data.get('order_number')]
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新现有记录
                        main_id = existing['id']
                        self._update_shipping_allocation_main(cursor, main_id, data)
                        # 删除旧的明细记录
                        cursor.execute("DELETE FROM shipping_allocation_details WHERE main_id = %s", [main_id])
                    else:
                        # 插入新记录
                        main_id = self._insert_shipping_allocation_main(cursor, data)
                    
                    # 插入明细记录
                    self._insert_shipping_allocation_details(cursor, main_id, data.get('merchants', []))
                    
                    # 记录操作历史
                    self._insert_allocation_history(cursor, main_id, 'CREATE' if not existing else 'UPDATE', data)
                    
                    conn.commit()
                    return main_id
                    
        except Exception as e:
            print(f"保存发货费用分摊数据失败: {e}")
            raise e
    
    def _insert_shipping_allocation_main(self, cursor, data):
        """插入主表记录"""
        sql = """
        INSERT INTO shipping_allocation_main (
            date, order_number, tracking_number, shipment_id,
            freight_unit_price, box_count, total_settle_weight, actual_weight_with_box,
            total_actual_weight, total_box_weight, total_throw_weight,
            total_amount, merchant_count, created_by
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        # 计算汇总数据
        merchants = data.get('merchants', [])
        total_actual_weight = sum(float(m.get('weight', 0)) for m in merchants)
        total_amount = sum(float(m.get('amount', 0)) for m in merchants)
        merchant_count = len(merchants)
        
        # 计算纸箱和抛出重量
        actual_weight_with_box = float(data.get('actual_weight_with_box', 0))
        total_settle_weight = float(data.get('total_settle_weight', 0))
        total_box_weight = actual_weight_with_box - total_actual_weight
        total_throw_weight = total_settle_weight - actual_weight_with_box
        
        params = [
            data.get('date'),
            data.get('order_number'),
            data.get('tracking_number'),
            data.get('shipment_id'),
            float(data.get('freight_unit_price', 0)),
            int(data.get('box_count', 0)),
            float(data.get('total_settle_weight', 0)),
            actual_weight_with_box,
            total_actual_weight,
            max(0, total_box_weight),
            max(0, total_throw_weight),
            total_amount,
            merchant_count,
            'system'  # 可以后续改为当前用户
        ]
        
        cursor.execute(sql, params)
        return cursor.lastrowid
    
    def _update_shipping_allocation_main(self, cursor, main_id, data):
        """更新主表记录"""
        sql = """
        UPDATE shipping_allocation_main SET
            date = %s, tracking_number = %s, shipment_id = %s,
            freight_unit_price = %s, box_count = %s, total_settle_weight = %s,
            actual_weight_with_box = %s, total_actual_weight = %s,
            total_box_weight = %s, total_throw_weight = %s,
            total_amount = %s, merchant_count = %s, updated_by = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        
        # 计算汇总数据
        merchants = data.get('merchants', [])
        total_actual_weight = sum(float(m.get('weight', 0)) for m in merchants)
        total_amount = sum(float(m.get('amount', 0)) for m in merchants)
        merchant_count = len(merchants)
        
        # 计算纸箱和抛出重量
        actual_weight_with_box = float(data.get('actual_weight_with_box', 0))
        total_settle_weight = float(data.get('total_settle_weight', 0))
        total_box_weight = actual_weight_with_box - total_actual_weight
        total_throw_weight = total_settle_weight - actual_weight_with_box
        
        params = [
            data.get('date'),
            data.get('tracking_number'),
            data.get('shipment_id'),
            float(data.get('freight_unit_price', 0)),
            int(data.get('box_count', 0)),
            float(data.get('total_settle_weight', 0)),
            actual_weight_with_box,
            total_actual_weight,
            max(0, total_box_weight),
            max(0, total_throw_weight),
            total_amount,
            merchant_count,
            'system',  # 可以后续改为当前用户
            main_id
        ]
        
        cursor.execute(sql, params)
    
    def _insert_shipping_allocation_details(self, cursor, main_id, merchants):
        """
        插入明细记录，支持物流状态和实收件数
        """
        if not merchants:
            return
        
        sql = """
        INSERT INTO shipping_allocation_details (
            main_id, sequence_number, merchant_name, pieces, actual_weight,
            weight_ratio, box_weight, throw_weight, settle_weight, amount,
            logistics_status, actual_received_count
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        for i, merchant in enumerate(merchants, 1):
            params = [
                main_id,
                i,  # 序号
                merchant.get('merchant_name', ''),
                int(merchant.get('pieces', 0)),
                float(merchant.get('weight', 0)),
                float(merchant.get('weight_ratio', 0)),
                float(merchant.get('box_weight', 0)),
                float(merchant.get('throw_weight', 0)),
                float(merchant.get('settle_weight', 0)),
                float(merchant.get('amount', 0)),
                merchant.get('logistics_status', '途中'),
                int(merchant.get('actual_received_count', 0))
            ]
            cursor.execute(sql, params)
    
    def _insert_allocation_history(self, cursor, main_id, operation_type, data):
        """插入历史记录"""
        sql = """
        INSERT INTO shipping_allocation_history (
            main_id, operation_type, new_data, operator, ip_address
        ) VALUES (
            %s, %s, %s, %s, %s
        )
        """
        
        params = [
            main_id,
            operation_type,
            json.dumps(data, ensure_ascii=False),
            'system',  # 可以后续改为当前用户
            '127.0.0.1'  # 可以后续获取真实IP
        ]
        
        cursor.execute(sql, params)
    
    def get_shipping_allocations(self, filters=None):
        """
        获取发货费用分摊数据，明细表增加物流状态和实收件数
        """
        try:
            # 主表查询
            main_sql = """
            SELECT 
                id, date, order_number, tracking_number, shipment_id,
                freight_unit_price, box_count, total_settle_weight, actual_weight_with_box,
                total_actual_weight, total_box_weight, total_throw_weight,
                total_amount, merchant_count, status, created_at, updated_at
            FROM shipping_allocation_main
            """
            params = []
            where_conditions = ["status = 1"]
            if filters:
                if filters.get('start_date'):
                    where_conditions.append("date >= %s")
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    where_conditions.append("date <= %s")
                    params.append(filters['end_date'])
                if filters.get('order_numbers'):
                    order_list = filters['order_numbers'] if isinstance(filters['order_numbers'], list) else [filters['order_numbers']]
                    placeholders = ','.join(['%s'] * len(order_list))
                    where_conditions.append(f"order_number IN ({placeholders})")
                    params.extend(order_list)
                if filters.get('order_number_prefix'):
                    where_conditions.append("order_number LIKE %s")
                    params.append(f"{filters['order_number_prefix']}%")
                if filters.get('tracking_number'):
                    where_conditions.append("tracking_number = %s")
                    params.append(filters['tracking_number'])
            if where_conditions:
                main_sql += " WHERE " + " AND ".join(where_conditions)
            main_sql += " ORDER BY date DESC, created_at DESC"
            main_records = self.execute_query(main_sql, params)
            if not main_records:
                return []
            main_ids = [record['id'] for record in main_records]
            detail_sql = """
            SELECT 
                main_id, sequence_number, merchant_name, pieces, actual_weight,
                weight_ratio, box_weight, throw_weight, settle_weight, amount,
                logistics_status, actual_received_count
            FROM shipping_allocation_details
            WHERE main_id IN ({}) AND status = 1
            ORDER BY main_id, sequence_number
            """.format(','.join(['%s'] * len(main_ids)))
            detail_records = self.execute_query(detail_sql, main_ids)
            detail_dict = {}
            for detail in detail_records:
                main_id = detail['main_id']
                if main_id not in detail_dict:
                    detail_dict[main_id] = []
                detail_dict[main_id].append(detail)
            result = []
            for main_record in main_records:
                main_record['merchants'] = detail_dict.get(main_record['id'], [])
                result.append(main_record)
            return result
        except Exception as e:
            print(f"获取发货费用分摊数据失败: {e}")
            raise e
    
    def get_shipping_allocation_by_order_number(self, order_number):
        """根据订单号获取单条分摊记录"""
        filters = {'order_numbers': [order_number]}
        results = self.get_shipping_allocations(filters)
        return results[0] if results else None
    
    def delete_shipping_allocation(self, main_id):
        """
        删除发货费用分摊记录（软删除）
        Args:
            main_id: 主表记录ID
        Returns:
            影响的行数
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 软删除主表记录
                    cursor.execute(
                        "UPDATE shipping_allocation_main SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        [main_id]
                    )
                    main_affected = cursor.rowcount
                    
                    # 软删除明细记录
                    cursor.execute(
                        "UPDATE shipping_allocation_details SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE main_id = %s",
                        [main_id]
                    )
                    
                    # 记录删除历史
                    self._insert_allocation_history(cursor, main_id, 'DELETE', {'deleted_at': datetime.now().isoformat()})
                    
                    conn.commit()
                    return main_affected
                    
        except Exception as e:
            print(f"删除发货费用分摊记录失败: {e}")
            raise e
    
    def get_merchant_allocation_summary(self, merchant_name=None, start_date=None, end_date=None):
        """
        获取商户费用分摊汇总统计
        Args:
            merchant_name: 商户名称
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            商户费用汇总数据
        """
        sql = """
        SELECT 
            sad.merchant_name,
            COUNT(DISTINCT sam.id) as allocation_count,
            SUM(sad.pieces) as total_pieces,
            SUM(sad.actual_weight) as total_actual_weight,
            SUM(sad.settle_weight) as total_settle_weight,
            SUM(sad.amount) as total_amount,
            AVG(sad.amount) as avg_amount,
            MIN(sam.date) as first_date,
            MAX(sam.date) as last_date
        FROM shipping_allocation_details sad
        JOIN shipping_allocation_main sam ON sad.main_id = sam.id
        WHERE sam.status = 1 AND sad.status = 1
        """
        
        params = []
        if merchant_name:
            sql += " AND sad.merchant_name = %s"
            params.append(merchant_name)
        
        if start_date:
            sql += " AND sam.date >= %s"
            params.append(start_date)
        
        if end_date:
            sql += " AND sam.date <= %s"
            params.append(end_date)
        
        sql += " GROUP BY sad.merchant_name ORDER BY total_amount DESC"
        
        return self.execute_query(sql, params)
    
    def get_allocation_statistics(self, start_date=None, end_date=None):
        """
        获取发货费用分摊统计数据
        Args:
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            统计数据
        """
        sql = """
        SELECT 
            COUNT(*) as total_records,
            SUM(total_actual_weight) as total_weight,
            SUM(total_amount) as total_amount,
            AVG(total_amount) as avg_amount,
            SUM(merchant_count) as total_merchants,
            AVG(merchant_count) as avg_merchants_per_day
        FROM shipping_allocation_main
        WHERE status = 1
        """
        
        params = []
        if start_date:
            sql += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            sql += " AND date <= %s"
            params.append(end_date)
        
        result = self.execute_query(sql, params, fetch_one=True)
        return result if result else {}

    def update_shipping_allocation_main(self, order_number, date, freight_unit_price=0, total_settle_weight=0, 
                                       actual_weight_with_box=0, tracking_number='', shipment_id='', box_count=0):
        """
        更新发货费用分摊主表记录
        
        参数:
            order_number: 订单号
            date: 日期
            freight_unit_price: 运费单价
            total_settle_weight: 总结算重量
            actual_weight_with_box: 实际重量(含箱)
            tracking_number: 快递单号
            shipment_id: 货件ID
            box_count: 箱数
        
        返回:
            int: 更新的记录的id，如果未找到记录则返回None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 首先获取要更新的记录的id
                    select_sql = "SELECT id FROM shipping_allocation_main WHERE order_number = %s"
                    cursor.execute(select_sql, (order_number,))
                    result = cursor.fetchone()
                    
                    if not result:
                        return None  # 未找到记录
                    
                    main_id = result[0]
                    
                    # 更新主表记录
                    update_sql = """
                    UPDATE shipping_allocation_main 
                    SET date = %s, freight_unit_price = %s, total_settle_weight = %s, 
                        actual_weight_with_box = %s, tracking_number = %s, shipment_id = %s, 
                        box_count = %s, updated_at = NOW()
                    WHERE order_number = %s
                    """
                    
                    cursor.execute(update_sql, (
                        date, freight_unit_price, total_settle_weight,
                        actual_weight_with_box, tracking_number, shipment_id,
                        box_count, order_number
                    ))
                    
                    conn.commit()
                    print(f"✅ 成功更新分摊主表记录，order_number: {order_number}, main_id: {main_id}")
                    return main_id
            
        except Exception as e:
            print(f"❌ 更新分摊主表记录失败: {e}")
            raise e

    def delete_shipping_allocation_details_by_main_id(self, main_id):
        """根据主表ID删除所有明细记录"""
        sql = "DELETE FROM shipping_allocation_details WHERE main_id = %s"
        return self.execute_delete(sql, [main_id])

    def insert_shipping_allocation_detail(self, main_id, merchant_name, pieces=0, 
                                        actual_weight=0, weight_ratio=0, box_weight=0, 
                                        throw_weight=0, settle_weight=0, amount=0,
                                        logistics_status='途中', actual_received_count=0):
        """
        插入单个明细记录，支持物流状态和实收件数
        """
        # 获取当前最大序号
        max_seq_sql = "SELECT COALESCE(MAX(sequence_number), 0) FROM shipping_allocation_details WHERE main_id = %s"
        max_seq_result = self.execute_query(max_seq_sql, [main_id], fetch_one=True)
        sequence_number = (max_seq_result['COALESCE(MAX(sequence_number), 0)'] if max_seq_result else 0) + 1
        
        sql = """
        INSERT INTO shipping_allocation_details (
            main_id, sequence_number, merchant_name, pieces, actual_weight,
            weight_ratio, box_weight, throw_weight, settle_weight, amount,
            logistics_status, actual_received_count
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        params = [
            main_id, sequence_number, merchant_name, int(pieces),
            float(actual_weight), float(weight_ratio), float(box_weight),
            float(throw_weight), float(settle_weight), float(amount),
            logistics_status, int(actual_received_count)
        ]
        
        return self.execute_insert(sql, params)

    def insert_shipping_allocation_history(self, main_id, operation_type, operation_data):
        """插入操作历史记录"""
        sql = """
        INSERT INTO shipping_allocation_history (
            main_id, operation_type, new_data, operator, ip_address
        ) VALUES (
            %s, %s, %s, %s, %s
        )
        """
        
        params = [
            main_id, operation_type, operation_data,
            'system', '127.0.0.1'  # 可以后续获取真实用户和IP
        ]
        
        return self.execute_insert(sql, params)

# 创建全局数据库实例
db = MySQLDatabase() 