#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态文件测试脚本
用于验证Flask静态文件配置是否正确
"""

import os
from flask import Flask, url_for

def test_static_files():
    """测试静态文件配置"""
    print("=" * 50)
    print("静态文件配置测试")
    print("=" * 50)
    
    # 检查静态文件目录结构
    static_dir = "static"
    images_dir = os.path.join(static_dir, "images")
    css_dir = os.path.join(static_dir, "css")
    js_dir = os.path.join(static_dir, "js")
    
    print("1. 检查目录结构:")
    directories = [static_dir, images_dir, css_dir, js_dir]
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"✅ {directory}/ - 存在")
        else:
            print(f"❌ {directory}/ - 不存在")
    
    print("\n2. 检查背景图片:")
    background_image = os.path.join(images_dir, "back.jpeg")
    if os.path.exists(background_image):
        file_size = os.path.getsize(background_image)
        print(f"✅ back.jpeg - 存在 ({file_size} bytes)")
    else:
        print("❌ back.jpeg - 不存在")
        print("   请将你的背景图片重命名为 'back.jpeg' 并放置在 static/images/ 目录下")
    
    print("\n3. 测试Flask URL生成:")
    try:
        # 创建临时Flask应用来测试URL生成
        app = Flask(__name__)
        with app.app_context():
            static_url = url_for('static', filename='images/back.jpeg')
            print(f"✅ 静态文件URL: {static_url}")
    except Exception as e:
        print(f"❌ URL生成失败: {e}")
    
    print("\n4. 推荐的图片格式和大小:")
    print("   - 格式: JPEG, PNG, WebP")
    print("   - 推荐尺寸: 1920x1080 或更高")
    print("   - 文件大小: 建议小于2MB")
    
    print("\n5. 如何添加背景图片:")
    print("   1. 准备一张背景图片")
    print("   2. 重命名为 'back.jpeg'")
    print("   3. 放置在 static/images/ 目录下")
    print("   4. 重启Flask应用")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_static_files() 