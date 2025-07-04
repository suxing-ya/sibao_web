-- 腾讯云MySQL数据库表结构创建脚本
-- 执行前请确保已连接到正确的数据库

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. 用户档案表
CREATE TABLE IF NOT EXISTS `profiles` (
    `id` varchar(36) NOT NULL DEFAULT (UUID()),
    `username` varchar(100) NOT NULL,
    `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
    `role` varchar(20) DEFAULT 'normal',
    `notes` text,
    `permissions` json DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 商家管理表
CREATE TABLE IF NOT EXISTS `merchants` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `merchant_code` varchar(50) NOT NULL,
    `merchant_name` varchar(100) NOT NULL,
    `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
    `merchant_id_code` varchar(20) DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_merchant_code` (`merchant_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 运费成本表（主要业务数据）
CREATE TABLE IF NOT EXISTS `shipping_costs` (
    `id` varchar(36) NOT NULL DEFAULT (UUID()),
    `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
    `date` date DEFAULT NULL,
    `freight_unit_price` decimal(10,2) DEFAULT NULL,
    `total_settle_weight` decimal(10,3) DEFAULT NULL,
    `actual_weight_with_box` decimal(10,3) DEFAULT NULL,
    `tracking_number` varchar(100) DEFAULT NULL,
    `shipment_id` varchar(100) DEFAULT NULL,
    `merchants` json DEFAULT NULL,
    `order_number` varchar(50) DEFAULT NULL,
    `settlement_status` varchar(20) DEFAULT 'pending',
    `box_count` int DEFAULT 0,
    PRIMARY KEY (`id`),
    KEY `idx_date` (`date`),
    KEY `idx_tracking_number` (`tracking_number`),
    KEY `idx_order_number` (`order_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Temu工作流表
CREATE TABLE IF NOT EXISTS `temu_workflow` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `cn_send_date` date DEFAULT NULL,
    `main_tracking_id` varchar(100) DEFAULT NULL,
    `box_code` varchar(100) DEFAULT NULL,
    `box_count` int DEFAULT 0,
    `inner_count` int DEFAULT 0,
    `status` varchar(20) DEFAULT 'pending',
    `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
    `us_receive_date` date DEFAULT NULL,
    `us_box_count` int DEFAULT 0,
    `us_actual_count` int DEFAULT 0,
    `detail_table` json DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_main_tracking_id` (`main_tracking_id`),
    KEY `idx_cn_send_date` (`cn_send_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Temu货件详情表
CREATE TABLE IF NOT EXISTS `temu_shipment_details` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `workflow_id` bigint NOT NULL,
    `merchant` varchar(100) NOT NULL,
    `quantity` int NOT NULL DEFAULT 0,
    `scan_channel` varchar(100) DEFAULT NULL,
    `notes` text DEFAULT NULL,
    `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_workflow_id` (`workflow_id`),
    FOREIGN KEY (`workflow_id`) REFERENCES `temu_workflow`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Temu货件ID表
CREATE TABLE IF NOT EXISTS `temu_shipment_ids` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `workflow_id` bigint NOT NULL,
    `shipment_id` varchar(100) NOT NULL,
    `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_workflow_id` (`workflow_id`),
    KEY `idx_shipment_id` (`shipment_id`),
    FOREIGN KEY (`workflow_id`) REFERENCES `temu_workflow`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入初始管理员用户
INSERT IGNORE INTO `profiles` (`username`, `role`, `notes`, `permissions`) 
VALUES ('admin', 'admin', '系统管理员账户', JSON_ARRAY('all'));

-- 插入一些示例商家数据
INSERT IGNORE INTO `merchants` (`merchant_code`, `merchant_name`, `merchant_id_code`) VALUES
('M001', '示例商家1', '0001'),
('M002', '示例商家2', '0002'),
('M003', '示例商家3', '0003');

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示创建的表
SHOW TABLES; 