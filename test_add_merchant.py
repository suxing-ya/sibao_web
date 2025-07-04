#!/usr/bin/env python3
import requests
import json

# 测试新增商家API
def test_add_merchant():
    url = "http://127.0.0.1:5000/api/merchants"
    
    # 测试数据 - 王丹丹
    merchant_data = {
        "merchant_id_code": "0014",
        "merchant_code": "wdd", 
        "merchant_name": "王丹丹"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("🧪 测试新增商家API...")
        print(f"📤 发送数据: {merchant_data}")
        
        response = requests.post(url, json=merchant_data, headers=headers)
        
        print(f"📥 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 新增商家成功！")
                return True
            else:
                print(f"❌ 新增失败: {result.get('message')}")
                return False
        else:
            print(f"❌ API调用失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False

if __name__ == "__main__":
    test_add_merchant() 