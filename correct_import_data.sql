-- 运费数据导入SQL（使用正确的字段名）
-- 注意：这里使用的是实际表结构中的字段名

INSERT INTO shipping_costs (
    date, 
    tracking_number, 
    order_number, 
    actual_weight_with_box, 
    freight_unit_price, 
    merchants, 
    settlement_status, 
    created_at
) VALUES
('2025-06-20', 'SF1234567890', 'FORM001', 2.5, 15.80, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantA', 'weight', 2.5)), 'shipped', NOW()),
('2025-06-20', 'YTO9876543210', 'FORM002', 1.8, 12.50, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantB', 'weight', 1.8)), 'shipped', NOW()),
('2025-06-21', 'ZTO1111222233', 'FORM003', 3.2, 18.90, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantC', 'weight', 3.2)), 'delivering', NOW()),
('2025-06-21', 'STO4444555566', 'FORM004', 0.9, 8.50, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantA', 'weight', 0.9)), 'shipped', NOW()),
('2025-06-22', 'EMS7777888899', 'FORM005', 4.1, 25.60, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantD', 'weight', 4.1)), 'delivered', NOW()),
('2025-06-22', 'JD0000111122', 'FORM006', 2.3, 16.20, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantB', 'weight', 2.3)), 'delivering', NOW()),
('2025-06-23', 'SF3333444455', 'FORM007', 1.5, 11.80, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantE', 'weight', 1.5)), 'shipped', NOW()),
('2025-06-23', 'YTO6666777788', 'FORM008', 3.8, 22.40, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantC', 'weight', 3.8)), 'delivering', NOW()),
('2025-06-24', 'ZTO9999000011', 'FORM009', 2.7, 17.30, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantA', 'weight', 2.7)), 'delivered', NOW()),
('2025-06-24', 'STO2222333344', 'FORM010', 1.2, 9.90, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantF', 'weight', 1.2)), 'shipped', NOW()),
('2025-06-25', 'EMS5555666677', 'FORM011', 4.5, 28.70, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantD', 'weight', 4.5)), 'delivering', NOW()),
('2025-06-25', 'JD8888999900', 'FORM012', 3.0, 19.50, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantB', 'weight', 3.0)), 'shipped', NOW()),
('2025-06-26', 'SF1111000099', 'FORM013', 2.1, 14.60, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantG', 'weight', 2.1)), 'delivered', NOW()),
('2025-06-26', 'YTO4444333322', 'FORM014', 1.6, 12.20, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantE', 'weight', 1.6)), 'delivering', NOW()),
('2025-06-26', 'ZTO7777666655', 'FORM015', 3.4, 20.80, JSON_ARRAY(JSON_OBJECT('merchant_name', 'MerchantC', 'weight', 3.4)), 'shipped', NOW());

-- 检查导入结果
SELECT COUNT(*) as '导入记录数' FROM shipping_costs;
SELECT date, tracking_number, order_number, actual_weight_with_box, freight_unit_price 
FROM shipping_costs 
ORDER BY date DESC 
LIMIT 5; 