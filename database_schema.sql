-- ========================================
-- 发货费用分摊表数据库架构
-- ========================================

-- 主表：保存发货费用分摊的基础信息和汇总数据
CREATE TABLE IF NOT EXISTS `shipping_allocation_main` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `date` date NOT NULL COMMENT '发货日期',
  `order_number` varchar(50) NOT NULL COMMENT '表单编号',
  `tracking_number` varchar(100) DEFAULT NULL COMMENT '快递单号',
  `shipment_id` varchar(100) DEFAULT NULL COMMENT '货件ID',
  
  -- 费用相关字段
  `freight_unit_price` decimal(10,4) DEFAULT 0.0000 COMMENT '运费单价(元/kg)',
  `box_count` int(11) DEFAULT 0 COMMENT '箱数',
  `total_settle_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '总结算重量(kg)',
  `actual_weight_with_box` decimal(10,4) DEFAULT 0.0000 COMMENT '实重+纸箱重量(kg)',
  
  -- 汇总数据字段
  `total_actual_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '货物实重总和(kg)',
  `total_box_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '纸箱重量总和(kg)',
  `total_throw_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '抛出重量总和(kg)',
  `total_amount` decimal(12,2) DEFAULT 0.00 COMMENT '今日运费总额(元)',
  `merchant_count` int(11) DEFAULT 0 COMMENT '商户数量',
  
  -- 系统字段
  `status` tinyint(4) DEFAULT 1 COMMENT '状态：1=有效，0=无效',
  `remark` text DEFAULT NULL COMMENT '备注',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `updated_by` varchar(50) DEFAULT NULL COMMENT '更新人',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_number` (`order_number`),
  KEY `idx_date` (`date`),
  KEY `idx_tracking_number` (`tracking_number`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='发货费用分摊主表';

-- 明细表：保存每个商户的详细分摊数据
CREATE TABLE IF NOT EXISTS `shipping_allocation_details` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `main_id` bigint(20) NOT NULL COMMENT '关联主表ID',
  `sequence_number` int(11) NOT NULL COMMENT '序号',
  `merchant_name` varchar(100) NOT NULL COMMENT '商户名称',
  
  -- 重量和数量字段
  `pieces` int(11) DEFAULT 0 COMMENT '件数',
  `actual_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '货物实重(kg)',
  `weight_ratio` decimal(8,4) DEFAULT 0.0000 COMMENT '重量比例(%)',
  `box_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '占纸箱重量(kg)',
  `throw_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '占抛出重量(kg)',
  `settle_weight` decimal(10,4) DEFAULT 0.0000 COMMENT '结算重量(kg)',
  `amount` decimal(12,2) DEFAULT 0.00 COMMENT '分摊金额(元)',
  
  -- 扩展字段
  `merchant_id` bigint(20) DEFAULT NULL COMMENT '商户ID（关联商户表）',
  `product_category` varchar(100) DEFAULT NULL COMMENT '商品类别',
  `volume_weight` decimal(10,4) DEFAULT NULL COMMENT '体积重量(kg)',
  `special_handling` varchar(200) DEFAULT NULL COMMENT '特殊处理说明',
  
  -- 系统字段
  `status` tinyint(4) DEFAULT 1 COMMENT '状态：1=有效，0=无效',
  `remark` text DEFAULT NULL COMMENT '备注',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_main_id` (`main_id`),
  KEY `idx_merchant_name` (`merchant_name`),
  KEY `idx_sequence` (`main_id`, `sequence_number`),
  CONSTRAINT `fk_details_main` FOREIGN KEY (`main_id`) REFERENCES `shipping_allocation_main` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='发货费用分摊明细表';

-- 费用计算历史表：保存历史计算记录，便于审计和追溯
CREATE TABLE IF NOT EXISTS `shipping_allocation_history` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `main_id` bigint(20) NOT NULL COMMENT '关联主表ID',
  `operation_type` varchar(20) NOT NULL COMMENT '操作类型：CREATE/UPDATE/DELETE/CALCULATE',
  `old_data` json DEFAULT NULL COMMENT '变更前数据(JSON格式)',
  `new_data` json DEFAULT NULL COMMENT '变更后数据(JSON格式)',
  `change_summary` text DEFAULT NULL COMMENT '变更摘要',
  `operator` varchar(50) DEFAULT NULL COMMENT '操作人',
  `operation_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `ip_address` varchar(45) DEFAULT NULL COMMENT '操作IP地址',
  
  PRIMARY KEY (`id`),
  KEY `idx_main_id` (`main_id`),
  KEY `idx_operation_time` (`operation_time`),
  KEY `idx_operation_type` (`operation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='发货费用分摊历史记录表';

-- 费用统计视图：便于快速查询统计数据
CREATE OR REPLACE VIEW `v_shipping_allocation_stats` AS
SELECT 
    sam.date,
    sam.order_number,
    sam.tracking_number,
    sam.total_actual_weight,
    sam.total_amount,
    sam.merchant_count,
    COUNT(sad.id) as detail_count,
    AVG(sad.amount) as avg_amount_per_merchant,
    MAX(sad.amount) as max_amount,
    MIN(sad.amount) as min_amount,
    GROUP_CONCAT(DISTINCT sad.merchant_name ORDER BY sad.sequence_number) as merchant_list
FROM shipping_allocation_main sam
LEFT JOIN shipping_allocation_details sad ON sam.id = sad.main_id
WHERE sam.status = 1 AND sad.status = 1
GROUP BY sam.id, sam.date, sam.order_number, sam.tracking_number, 
         sam.total_actual_weight, sam.total_amount, sam.merchant_count;

-- 商户费用汇总视图：按商户统计费用信息
CREATE OR REPLACE VIEW `v_merchant_shipping_summary` AS
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
GROUP BY sad.merchant_name;

-- 创建索引优化查询性能
CREATE INDEX `idx_date_merchant` ON `shipping_allocation_details` (`main_id`, `merchant_name`);
CREATE INDEX `idx_amount_range` ON `shipping_allocation_details` (`amount`);
CREATE INDEX `idx_weight_range` ON `shipping_allocation_details` (`actual_weight`);

-- 插入示例数据（可选）
INSERT INTO `shipping_allocation_main` (
    `date`, `order_number`, `tracking_number`, `shipment_id`,
    `freight_unit_price`, `box_count`, `total_settle_weight`, `actual_weight_with_box`,
    `total_actual_weight`, `total_box_weight`, `total_throw_weight`, 
    `total_amount`, `merchant_count`, `created_by`
) VALUES (
    '2025-01-15', 'SA20250115001', 'SF1234567890', 'SP2025011501',
    60.00, 5, 38.000, 35.000,
    30.000, 5.000, 3.000,
    2280.00, 3, 'system'
);

-- 获取刚插入的主表ID
SET @main_id = LAST_INSERT_ID();

-- 插入对应的明细数据
INSERT INTO `shipping_allocation_details` (
    `main_id`, `sequence_number`, `merchant_name`, `pieces`, `actual_weight`,
    `weight_ratio`, `box_weight`, `throw_weight`, `settle_weight`, `amount`
) VALUES 
(@main_id, 1, '陈芬芬', 10, 10.000, 33.33, 1.667, 1.000, 12.667, 760.00),
(@main_id, 2, '汪汪', 15, 10.000, 33.33, 1.667, 1.000, 12.667, 760.00),
(@main_id, 3, '王丹丹', 12, 10.000, 33.33, 1.666, 1.000, 12.666, 760.00);

-- 创建触发器：自动更新主表汇总数据
DELIMITER //

CREATE TRIGGER `tr_update_main_totals_after_detail_insert`
AFTER INSERT ON `shipping_allocation_details`
FOR EACH ROW
BEGIN
    UPDATE `shipping_allocation_main` 
    SET 
        `total_actual_weight` = (
            SELECT COALESCE(SUM(actual_weight), 0) 
            FROM `shipping_allocation_details` 
            WHERE main_id = NEW.main_id AND status = 1
        ),
        `total_amount` = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM `shipping_allocation_details` 
            WHERE main_id = NEW.main_id AND status = 1
        ),
        `merchant_count` = (
            SELECT COUNT(*) 
            FROM `shipping_allocation_details` 
            WHERE main_id = NEW.main_id AND status = 1
        ),
        `updated_at` = CURRENT_TIMESTAMP
    WHERE id = NEW.main_id;
END//

CREATE TRIGGER `tr_update_main_totals_after_detail_update`
AFTER UPDATE ON `shipping_allocation_details`
FOR EACH ROW
BEGIN
    UPDATE `shipping_allocation_main` 
    SET 
        `total_actual_weight` = (
            SELECT COALESCE(SUM(actual_weight), 0) 
            FROM `shipping_allocation_details` 
            WHERE main_id = NEW.main_id AND status = 1
        ),
        `total_amount` = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM `shipping_allocation_details` 
            WHERE main_id = NEW.main_id AND status = 1
        ),
        `merchant_count` = (
            SELECT COUNT(*) 
            FROM `shipping_allocation_details` 
            WHERE main_id = NEW.main_id AND status = 1
        ),
        `updated_at` = CURRENT_TIMESTAMP
    WHERE id = NEW.main_id;
END//

CREATE TRIGGER `tr_update_main_totals_after_detail_delete`
AFTER DELETE ON `shipping_allocation_details`
FOR EACH ROW
BEGIN
    UPDATE `shipping_allocation_main` 
    SET 
        `total_actual_weight` = (
            SELECT COALESCE(SUM(actual_weight), 0) 
            FROM `shipping_allocation_details` 
            WHERE main_id = OLD.main_id AND status = 1
        ),
        `total_amount` = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM `shipping_allocation_details` 
            WHERE main_id = OLD.main_id AND status = 1
        ),
        `merchant_count` = (
            SELECT COUNT(*) 
            FROM `shipping_allocation_details` 
            WHERE main_id = OLD.main_id AND status = 1
        ),
        `updated_at` = CURRENT_TIMESTAMP
    WHERE id = OLD.main_id;
END//

DELIMITER ;

-- 查询示例
-- 1. 查询某日期范围的费用分摊汇总
/*
SELECT 
    date,
    order_number,
    tracking_number,
    total_actual_weight,
    total_amount,
    merchant_count
FROM shipping_allocation_main 
WHERE date BETWEEN '2025-01-01' AND '2025-01-31'
ORDER BY date DESC;
*/

-- 2. 查询某个订单的详细分摊情况
/*
SELECT 
    sam.order_number,
    sam.date,
    sam.total_amount,
    sad.sequence_number,
    sad.merchant_name,
    sad.pieces,
    sad.actual_weight,
    sad.settle_weight,
    sad.amount
FROM shipping_allocation_main sam
JOIN shipping_allocation_details sad ON sam.id = sad.main_id
WHERE sam.order_number = 'SA20250115001'
ORDER BY sad.sequence_number;
*/

-- 3. 查询商户费用统计
/*
SELECT * FROM v_merchant_shipping_summary 
WHERE merchant_name = '陈芬芬'
ORDER BY total_amount DESC;
*/ 