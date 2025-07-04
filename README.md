# Temu商品信息提取器

这是一个用于提取Temu商品信息的Python工具。它使用Selenium WebDriver来模拟真实浏览器访问，能够提取商品的标题、价格、评分、评价数、销量等信息。

## 功能特点

- 支持单个和批量提取商品信息
- 自动处理动态加载内容
- 支持代理服务器
- 内置重试机制
- 支持导出为JSON和CSV格式
- 详细的日志记录
- 反爬虫措施

## 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd <repository-name>
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 确保已安装Chrome浏览器

## 使用方法

### 单个商品提取

```python
from temu_selenium_extractor import extract_temu_products

url = "https://www.temu.com/your-product-url"
result = extract_temu_products(url)

if result['success']:
    product = result['data'][0]
    print(f"商品标题: {product['title']}")
    print(f"当前价格: {product['price']}")
    print(f"原价: {product.get('original_price', 'N/A')}")
    print(f"评分: {product.get('rating', 'N/A')}")
    print(f"评价数: {product.get('review_count', 'N/A')}")
    print(f"销量: {product.get('sales_count', 'N/A')}")
```

### 批量提取

```python
urls = [
    "https://www.temu.com/product-url-1",
    "https://www.temu.com/product-url-2",
    "https://www.temu.com/product-url-3"
]

# 导出为JSON
result = extract_temu_products(
    urls,
    output_file="products.json"
)

# 导出为CSV
result = extract_temu_products(
    urls,
    output_file="products.csv"
)
```

### 使用代理

```python
result = extract_temu_products(
    url,
    proxy="http://your-proxy-server:port"
)
```

### 完整参数说明

```python
extract_temu_products(
    urls,                    # 单个URL字符串或URL列表
    include_images=True,     # 是否包含商品图片
    include_reviews=True,    # 是否包含评价信息
    output_file=None,        # 输出文件路径(.json或.csv)
    proxy=None,             # 代理服务器地址
    max_retries=3           # 最大重试次数
)
```

## 提取的数据字段

- `title`: 商品标题
- `price`: 当前价格
- `original_price`: 原价
- `rating`: 评分
- `review_count`: 评价数量
- `sales_count`: 销量
- `image_url`: 商品图片URL
- `sku`: 商品SKU
- `specifications`: 商品规格
- `product_url`: 商品页面URL

## 注意事项

1. 确保网络连接稳定
2. 如果遇到频繁的验证码或IP限制，建议：
   - 使用代理服务器
   - 增加请求间隔
   - 减少批量请求的数量
3. 某些字段可能因页面结构变化而无法提取
4. 建议在使用代理时先测试代理的可用性

## 许可证

MIT License 