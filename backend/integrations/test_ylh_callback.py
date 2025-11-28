"""
YLH回调接口测试脚本

使用方法:
    python backend/integrations/test_ylh_callback.py
"""
import requests
import json
import hashlib
from datetime import datetime


def generate_sign(params, secret):
    """生成签名"""
    filtered_params = {
        k: v for k, v in params.items() 
        if v is not None and str(v).strip() != '' and k.lower() != 'sign'
    }
    
    sorted_keys = sorted(filtered_params.keys())
    
    sign_str = secret
    for key in sorted_keys:
        sign_str += f"{key}{filtered_params[key]}"
    sign_str += secret
    
    sign = hashlib.md5(sign_str.lower().encode('utf-8')).hexdigest().upper()
    return sign


def test_callback(base_url, app_key, secret, method, data):
    """测试回调接口"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    params = {
        "AppKey": app_key,
        "TimeStamp": timestamp,
        "Method": method,
        "Data": json.dumps(data, ensure_ascii=False)
    }
    
    # 生成签名
    sign = generate_sign(params, secret)
    params["Sign"] = sign
    
    print(f"\n{'='*60}")
    print(f"测试回调: {method}")
    print(f"{'='*60}")
    print(f"请求URL: {base_url}")
    print(f"AppKey: {app_key}")
    print(f"TimeStamp: {timestamp}")
    print(f"Data: {json.dumps(data, ensure_ascii=False, indent=2)}")
    print(f"Sign: {sign}")
    
    try:
        response = requests.post(
            base_url,
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        
        return response.json()
    except Exception as e:
        print(f"\n请求失败: {str(e)}")
        return None


def main():
    # 配置
    BASE_URL = "http://localhost:8000/api/ylh/callback/"
    APP_KEY = "85f46119-e920-4f01-9624-66326c013217"
    SECRET = "8e17bb88a087400bac9ab67e67b138ef"
    
    print("YLH回调接口测试")
    print(f"目标地址: {BASE_URL}")
    print(f"AppKey: {APP_KEY}")
    
    # 测试1: 确认订单回调
    test_callback(
        BASE_URL,
        APP_KEY,
        SECRET,
        "hmm.scm_heorder.confirm",
        {
            "ExtOrderNo": "SO.20251128.000001",
            "PlatformOrderNo": "PO20251128001",
            "State": 1
        }
    )
    
    # 测试2: 取消订单回调
    test_callback(
        BASE_URL,
        APP_KEY,
        SECRET,
        "hmm.scm_heorder.cancel",
        {
            "ExtOrderNo": "SO.20251128.000002",
            "PlatformOrderNo": "PO20251128002",
            "State": 1
        }
    )
    
    # 测试3: 订单缺货回调
    test_callback(
        BASE_URL,
        APP_KEY,
        SECRET,
        "hmm.scm_heorder.oostock",
        {
            "ExtOrderNo": "SO.20251128.000003",
            "PlatformOrderNo": "PO20251128003",
            "State": 1,
            "FailMsg": "商品暂时缺货"
        }
    )
    
    # 测试4: 失败的订单确认回调
    test_callback(
        BASE_URL,
        APP_KEY,
        SECRET,
        "hmm.scm_heorder.confirm",
        {
            "ExtOrderNo": "",
            "PlatformOrderNo": "PO20251128004",
            "State": 0,
            "FailMsg": "库存不足"
        }
    )
    
    # 测试5: 错误的签名
    print(f"\n{'='*60}")
    print("测试错误签名")
    print(f"{'='*60}")
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    params = {
        "AppKey": APP_KEY,
        "TimeStamp": timestamp,
        "Method": "hmm.scm_heorder.confirm",
        "Data": json.dumps({"PlatformOrderNo": "PO20251128005", "State": 1}),
        "Sign": "WRONG_SIGNATURE_12345"
    }
    
    try:
        response = requests.post(
            BASE_URL,
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容:")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"请求失败: {str(e)}")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
