-- 为 shipping_costs 表添加 box_count 字段
-- 这个字段用于存储箱数信息

-- 添加 box_count 字段
ALTER TABLE shipping_costs 
ADD COLUMN IF NOT EXISTS box_count INTEGER DEFAULT 0;

-- 添加注释说明
COMMENT ON COLUMN shipping_costs.box_count IS '箱数：该批货物的包装箱数量';

-- 验证字段是否添加成功
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'shipping_costs' 
AND column_name = 'box_count'; 