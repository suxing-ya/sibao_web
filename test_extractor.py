#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from temu_extractor import TemuExtractor

def main():
    url = "https://www.temu.com/us-zh-Hans/50pcs-19mm-%E5%A4%8D%E5%8F%A4%E7%8F%A0%E5%85%89%E5%9C%86%E5%9C%88%E5%9C%86%E7%8E%AF%E7%99%BE%E6%90%AD%E4%BA%9A%E5%85%8B%E5%8A%9Bdiy%E6%89%8B%E5%B7%A5%E9%A5%B0%E5%93%81%E8%80%B3%E7%8E%AF%E9%85%8D%E4%BB%B6%E6%9D%90%E6%96%99-g-601101076255740.html"
    
    print("开始测试Temu产品提取器...")
    print(f"测试URL: {url}")
    print("-" * 80)
    
    extractor = TemuExtractor()
    result = extractor.extract_product_info(url)
    
    print("\n提取结果:")
    print("-" * 80)
    print(result)

if __name__ == "__main__":
    main() 