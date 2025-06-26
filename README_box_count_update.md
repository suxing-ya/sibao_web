# 箱数功能更新说明

## 📦 功能概述

在发货费用分摊表（`Expense Allocation Function.html`）中新增了"箱数"字段，用于记录每批货物的包装箱数量。

## 🎯 更新内容

### 前端修改
1. **新增输入字段**：在页面第三列摘要区域添加了"箱数"输入框
2. **数据保存**：箱数数据会自动保存到数据库
3. **数据加载**：从数据库加载数据时会自动填充箱数字段
4. **表单重置**：清空表单时会同时清空箱数字段

### 数据库修改
需要在 `shipping_costs` 表中添加 `box_count` 字段：

```sql
ALTER TABLE shipping_costs 
ADD COLUMN IF NOT EXISTS box_count INTEGER DEFAULT 0;
```

## 🛠️ 部署步骤

### 1. 数据库更新
在 Supabase SQL 编辑器中执行 `add_box_count_field.sql` 文件中的 SQL 语句：

1. 登录 Supabase 控制台
2. 进入 SQL Editor
3. 复制并执行以下 SQL：

```sql
-- 添加 box_count 字段
ALTER TABLE shipping_costs 
ADD COLUMN IF NOT EXISTS box_count INTEGER DEFAULT 0;

-- 添加注释说明
COMMENT ON COLUMN shipping_costs.box_count IS '箱数：该批货物的包装箱数量';
```

### 2. 验证更新
执行以下查询验证字段是否成功添加：

```sql
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'shipping_costs' 
AND column_name = 'box_count';
```

## 📋 使用说明

### 输入箱数
1. 在发货费用分摊页面的右侧摘要区域
2. 找到"箱数"输入框
3. 输入该批货物的包装箱数量（整数）
4. 点击"保存数据"按钮保存

### 数据字段
- **字段名**：`box_count`
- **数据类型**：INTEGER
- **默认值**：0
- **是否必填**：否
- **说明**：记录该批货物使用的包装箱数量

## 🔄 兼容性

- **向后兼容**：现有数据不受影响，新字段默认值为 0
- **前端兼容**：现有功能正常工作，新增字段不影响原有操作
- **数据完整性**：保存和加载数据时会正确处理箱数字段

## 📊 显示位置

箱数字段位于页面右侧摘要区域：
- 今日运费
- 纸箱重量
- **箱数** ← 新增
- 商户数量

## ⚠️ 注意事项

1. 执行数据库更新前请备份数据
2. 确保有足够的数据库权限执行 ALTER TABLE 操作
3. 箱数字段为可选字段，不填写不影响其他功能
4. 数据类型为整数，不支持小数输入 