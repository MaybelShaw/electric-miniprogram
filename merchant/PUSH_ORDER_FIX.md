# 推送海尔订单功能修复

## 问题
推送海尔订单时出现错误：
```
cannot import name 'YLHApi' from 'integrations.ylhapi'
Internal Server Error: /api/orders/2/push_to_haier/
```

## 原因
1. **导入错误**：代码中导入的类名 `YLHApi` 不存在，实际类名是 `YLHSystemAPI`
2. **配置缺失**：`.env` 文件中缺少易理货API配置
3. **Settings未加载**：`settings/base.py` 中没有加载易理货配置

## 修复内容

### 1. 修复导入错误
**文件**: `backend/orders/views.py`

修改前：
```python
from integrations.ylhapi import YLHApi
ylh_api = YLHApi(config)
```

修改后：
```python
from integrations.ylhapi import YLHSystemAPI
ylh_api = YLHSystemAPI(config)
```

### 2. 添加配置到 .env
**文件**: `backend/.env`

添加了以下配置：
```bash
# 海尔API配置
HAIER_CLIENT_ID=7RKuo0yBew5yRAq9oSwZw8PseXkNHpLb
HAIER_CLIENT_SECRET=y8Dt0YYDoQSY3DphKa79XkfpWoDqPnGp
HAIER_TOKEN_URL=https://openplat-test.haier.net/oauth2/auth
HAIER_BASE_URL=https://openplat-test.haier.net
HAIER_CUSTOMER_CODE=8800633175
HAIER_SEND_TO_CODE=8800633175
HAIER_SUPPLIER_CODE=1001
HAIER_PASSWORD=your-haier-password
HAIER_SELLER_PASSWORD=your-seller-password

# 易理货系统API配置
YLH_AUTH_URL=http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token
YLH_BASE_URL=http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev
YLH_USERNAME=erp
YLH_PASSWORD=123qwe
YLH_CLIENT_ID=open_api_erp
YLH_CLIENT_SECRET=12345678
```

### 3. 在 Settings 中加载配置
**文件**: `backend/backend/settings/base.py`

添加了配置加载代码：
```python
# Haier API Configuration
HAIER_CLIENT_ID = EnvironmentConfig.get_env('HAIER_CLIENT_ID', '')
HAIER_CLIENT_SECRET = EnvironmentConfig.get_env('HAIER_CLIENT_SECRET', '')
# ... 其他配置

# YLH System API Configuration
YLH_AUTH_URL = EnvironmentConfig.get_env('YLH_AUTH_URL', '...')
YLH_BASE_URL = EnvironmentConfig.get_env('YLH_BASE_URL', '...')
# ... 其他配置
```

### 4. 更新配置结构
**文件**: `backend/orders/views.py`

修改配置初始化以匹配 `YLHSystemAPI` 的要求：
```python
config = {
    'auth_url': settings.YLH_AUTH_URL,
    'base_url': settings.YLH_BASE_URL,
    'username': settings.YLH_USERNAME,
    'password': settings.YLH_PASSWORD,
    'client_id': getattr(settings, 'YLH_CLIENT_ID', 'open_api_erp'),
    'client_secret': getattr(settings, 'YLH_CLIENT_SECRET', '12345678'),
}
```

## 验证

已通过测试验证：
- ✅ 配置正确加载
- ✅ 类导入成功
- ✅ API初始化成功
- ✅ 认证成功

## 使用方法

1. **确保后端运行**
   ```bash
   cd backend
   python manage.py runserver
   ```

2. **在merchant-admin推送订单**
   - 打开订单列表
   - 找到已支付的海尔订单（显示"海尔订单: 是, 未推送"）
   - 点击"推送海尔"按钮
   - 填写订单来源系统和店铺名称
   - 确认推送

3. **查看推送结果**
   - 推送成功后，状态变为"已推送"
   - 可以点击"查询物流"按钮查看物流信息

## 注意事项

1. **测试环境**：当前配置使用的是测试环境的API地址
2. **生产环境**：部署到生产环境时，需要更新为正式的API地址和凭证
3. **认证信息**：确保 `.env` 文件中的用户名和密码正确
4. **网络访问**：确保服务器可以访问易理货API的URL

## 相关文档

- [海尔订单推送指南](./HAIER_ORDER_PUSH_GUIDE.md)
- [海尔功能快速参考](./HAIER_FEATURES.md)
- [海尔订单问题排查](./HAIER_ORDER_TROUBLESHOOTING.md)
