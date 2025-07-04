-- 腾讯云PostgreSQL数据库表结构创建脚本
-- 执行前请确保已连接到正确的数据库

-- 启用UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. 用户档案表
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    role TEXT DEFAULT 'normal',
    notes TEXT,
    permissions JSONB DEFAULT '[]'::jsonb
);

-- 2. 商家管理表
CREATE TABLE merchants (
    id BIGSERIAL PRIMARY KEY,
    merchant_code TEXT NOT NULL UNIQUE,
    merchant_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    merchant_id_code TEXT
);

-- 3. 运费成本表（主要业务数据）
CREATE TABLE shipping_costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date DATE,
    freight_unit_price NUMERIC(10,2),
    total_settle_weight NUMERIC(10,3),
    actual_weight_with_box NUMERIC(10,3),
    tracking_number TEXT,
    shipment_id TEXT,
    merchants JSONB,
    order_number TEXT,
    settlement_status TEXT DEFAULT 'pending',
    box_count INTEGER DEFAULT 0
);

-- 4. Temu工作流表
CREATE TABLE temu_workflow (
    id BIGSERIAL PRIMARY KEY,
    cn_send_date DATE,
    main_tracking_id TEXT,
    box_code TEXT,
    box_count INTEGER DEFAULT 0,
    inner_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Temu货件详情表
CREATE TABLE temu_shipment_details (
    id BIGSERIAL PRIMARY KEY,
    workflow_id BIGINT REFERENCES temu_workflow(id) ON DELETE CASCADE,
    merchant TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    scan_channel TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Temu货件ID表
CREATE TABLE temu_shipment_ids (
    id BIGSERIAL PRIMARY KEY,
    workflow_id BIGINT REFERENCES temu_workflow(id) ON DELETE CASCADE,
    shipment_id_value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引以提高查询性能
CREATE INDEX idx_profiles_username ON profiles(username);
CREATE INDEX idx_profiles_role ON profiles(role);

CREATE INDEX idx_merchants_code ON merchants(merchant_code);
CREATE INDEX idx_merchants_name ON merchants(merchant_name);

CREATE INDEX idx_shipping_costs_date ON shipping_costs(date);
CREATE INDEX idx_shipping_costs_tracking ON shipping_costs(tracking_number);
CREATE INDEX idx_shipping_costs_order ON shipping_costs(order_number);
CREATE INDEX idx_shipping_costs_status ON shipping_costs(settlement_status);

CREATE INDEX idx_temu_workflow_date ON temu_workflow(cn_send_date);
CREATE INDEX idx_temu_workflow_tracking ON temu_workflow(main_tracking_id);
CREATE INDEX idx_temu_workflow_status ON temu_workflow(status);

CREATE INDEX idx_temu_details_workflow ON temu_shipment_details(workflow_id);
CREATE INDEX idx_temu_details_merchant ON temu_shipment_details(merchant);

CREATE INDEX idx_temu_ids_workflow ON temu_shipment_ids(workflow_id);

-- 添加表注释
COMMENT ON TABLE profiles IS '用户档案表，存储用户基本信息和权限';
COMMENT ON TABLE merchants IS '商家管理表，存储商家基本信息';
COMMENT ON TABLE shipping_costs IS '运费成本表，存储运费分摊相关数据';
COMMENT ON TABLE temu_workflow IS 'Temu工作流表，存储货物流转工作流信息';
COMMENT ON TABLE temu_shipment_details IS 'Temu货件详情表，存储每个工作流的商家详情';
COMMENT ON TABLE temu_shipment_ids IS 'Temu货件ID表，存储工作流关联的货件ID';

-- 添加列注释
COMMENT ON COLUMN profiles.permissions IS '用户权限JSON数组';
COMMENT ON COLUMN shipping_costs.merchants IS '商家详情JSON数组，包含名称、件数、重量等';
COMMENT ON COLUMN shipping_costs.box_count IS '箱数：该批货物的包装箱数量';
COMMENT ON COLUMN temu_workflow.inner_count IS '内装总件数';

-- 创建初始管理员用户（可选）
INSERT INTO profiles (username, role, created_at, notes, permissions) 
VALUES (
    'admin', 
    'admin', 
    NOW(), 
    '系统管理员账户', 
    '["all"]'::jsonb
) ON CONFLICT (username) DO NOTHING;

-- 创建一些示例商家数据（可选）
INSERT INTO merchants (merchant_code, merchant_name, merchant_id_code) VALUES
('M001', '示例商家1', 'SHOP001'),
('M002', '示例商家2', 'SHOP002'),
('M003', '示例商家3', 'SHOP003')
ON CONFLICT (merchant_code) DO NOTHING;

-- 显示创建结果
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN ('profiles', 'merchants', 'shipping_costs', 'temu_workflow', 'temu_shipment_details', 'temu_shipment_ids')
ORDER BY tablename; 