# 海尔商品开发查询接口文档

## 版本历史

| 版本 | 内容 | 日期 | Author |
|------|------|------|--------|
| V1.0.0 | 可采商品、价格查询方案 | 2025-06-27 | 孙亚志 |
| v1.0.1 | 库存查询方案 | 2025-06-27 | 王斌 |
| v1.0.2 | 新增余额查询接口 | 2025-07-03 | 魏本栋 |
| v1.0.3 | 可采商品，价格查询出入参修改 | 2025-07-08 | 孙亚志 |
| v1.0.4 | 付款方余额查询接口修改请求方式改成 post，入参增加客户密码字段 | 2025-07-11 | 魏本栋 |
| v1.0.5 | 外网访问方式 | 2025-07-11 | 房鑫 |
| v1.0.6 | RX库存三方直连库存查询接口修改商品编码描述 | 2025-07-15 | 房鑫 |
| v1.0.7 | 一期订单创建等接口增加 | 2025-07-15 | 付永彬 |

## 1. 缩略语、范围

### 1.1 缩略语
| 名词 | 说明 |
|------|------|
|      |      |

### 1.2 范围
本接口规范定义了巨商汇订单中心与各业务方进行交易的接口、交易处理流程和安全机制，作为各个业务方作为业务接口对接的接口设计、开发的参考。

## 2. 接口定义

### 外网访问方式

#### OAuth认证信息
```
OAuth client_id: 7RKuo0yBew5yRAq9oSwZw8PseXkNHpLb 
OAuth client_secret: y8Dt0YYDoQSY3DphKa79XkfpWoDqPnGp
```

#### 获取外网 Token
```bash
curl --location --request POST 'https://openplat.haier.net/gateway-test/oauth2/token' \
--header 'Content-Type: application/json' \
--data-raw '{
  "client_id": "${client_id}",
  "client_secret": "${client_secret}",
  "grant_type": "client_credentials"
}'
```

#### 调用外网 API
```bash
curl --location --request GET 'https://openplat.haier.net/op/gateway-test/v3' \
--header 'Authorization: eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJianFpU1NuVjBvIiwiZXh0ZW5kIjp7fSwiZXhwIjoxNjgwOTI1NTAwfQ.NRaztddzuRtcTHJDIx8GMT6q9zwY3EjtVJtIxSzn4VTfewy2dY0v_dY5efSTJ0SmCOIUkwghtQQ1yX1yKpisKg'
```

### 2.1 可采商品接口

#### 访问地址
| 环境 | 访问域名 |
|------|----------|
| 测试地址 | 外网：https://openplat-test.haier.net/yilihuo/jsh-service-goods-mall-search/api/product-info/procurable-products-out/check-procurable-products OAuth2.0认证地址：https://openplat-test.haier.net/oauth2/auth |
| 预生产地址 | 外网：https://openplat-bj-aliyun-stage.haier.net/yilihuo/jsh-service-goods-mall-search/api/product-info/procurable-products-out/check-procurable-products OAuth2.0认证地址：https://openplat-bj-aliyun-stage.haier.net/oauth2/auth |
| 生产地址 | 外网：https://openplat-bj-aliyun.haier.net/yilihuo/jsh-service-goods-mall-search/api/product-info/procurable-products-out/check-procurable-products OAuth2.0认证地址：https://openplat-bj-aliyun.haier.net/oauth2/auth |

#### 接口概述
| 接口功能概述 | 批量查询可采商品 |
|--------------|-----------------|
| 请求方式 | post |
| Content-type | application/json |

#### 请求报文
| 序号 | 参数名称 | 中文名称 | 类型 | 必填 | 默认值 | 备注 | 示例 |
|------|----------|----------|------|------|--------|------|------|
| 1 | customerCode | 售达方编码 | String | 是 | 无 | 单个客户编码入参 | 客户在海尔建户的售达方编码，如 8800633175 |
| 2 | sendToCode | 送达方编码 | String | 否 | 无 | 单个送达方编码入参 | 客户在海尔建的送达方编码，如8800633175；如果供货方为海尔智家1001，则此字段必填； |
| 3 | productCodes | 产品编码 List | List<String> | 是 | 无 | 一次最多20个产品编码 | 产品编码为海尔内部产品编码,如 GA0SZC00U |
| 4 | supplierCode | 供货方编码 | String | 是 | 无 | 不能为空 | 海尔智家默认1001；服务商传服务商8码 |
| 5 | searchType | 查询类型 | String | 是 | PTJSH | 不能为空 | PTJSH约定为只能查询供货方为海尔智家的商品范围，不含样机/工程对应的型号（这些型号不校验投放） |
| 6 | passWord | 约定密码 | String | 是 |  |  | 每个账号对应一个密码 |

#### Curl示例
```bash
curl --location --request POST 'https://openplat-test.haier.net/yilihuo/jsh-service-goods-mall-search/api/product-info/procurable-products-out/check-procurable-products' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "customerCode": "8800633175",
  "sendToCode": "8800633175",
  "productCodes": ["GA0SZC00U"],
  "supplierCode": "1001",
  "searchType": "PTJSH",
  "passWord": "your_password"
}'
```

#### 返回参数
List<ProductOutInfoDto>返回产品信息集合

| 序号 | 参数名称 | 中文名称 | 类型 | 备注 |
|------|----------|----------|------|------|
| 1 | productCode | 产品编码 | String | 1.产品编码为海尔内部产品编码,如 GA0SZC00U 2.如果未指定产品编码，则返回所有可采明细型号列表 |
| 2 | productModel | 型号 | String | 产品编码为海尔内部产品型号,如 EC6001-HT3 |
| 3 | productGroupNamd | 产品组 | String | 海尔产品组名字，如电热水器 |
| 4 | productBrandName | 品牌 | String | 海尔品牌名字，如海尔 |
| 5 | productImageUrl | 主图 | String | 产品主图 url地址 |
| 6 | productLageUrls | 拉页 | List<String> | 产品拉页 url地址 list |
| 7 | isSales | 是否可采 | String | 是否可采（1可采，0不可采） |
| 8 | noSalesReason | 提示信息 | String | 如果指定查询的产品编码不可查，则返回相应提示信息，比如产品未投放对应提示语 |

### 2.2 可采商品价格接口

#### 访问地址
| 环境 | 访问域名 |
|------|----------|
| 测试地址 | 外网：https://openplat-test.haier.net/yilihuo/jsh-service-goods-price/api/goods-price/price-daily-sales/price-query/pt-out-list-price OAuth2.0认证地址：https://openplat-test.haier.net/oauth2/auth |
| 预生产地址 | 外网：https://openplat-bj-aliyun-stage.haier.net/yilihuo/jsh-service-goods-price/api/goods-price/price-daily-sales/price-query/pt-out-list-price OAuth2.0认证地址：https://openplat-bj-aliyun-stage.haier.net/oauth2/auth |
| 生产地址 | 外网：https://openplat-bj-aliyun-stage.haier.net/yilihuo/jsh-service-goods-price/api/goods-price/price-daily-sales/price-query/pt-out-list-price OAuth2.0认证地址：https://openplat-bj-aliyun.haier.net/oauth2/auth |

#### 接口概述
| 接口功能概述 | 查询商品价格 |
|--------------|--------------|
| 请求方式 | post |
| Content-type | application/json |

#### 请求报文
| 序号 | 参数名称 | 中文名称 | 类型 | 必填 | 默认值 | 备注 | 示例 |
|------|----------|----------|------|------|--------|------|------|
| 1 | customerCode | 售达方编码 | String | 是 | 无 | 单个客户编码入参 | 客户在海尔建户的售达方编码，如 8800633175 |
| 2 | sendToCode | 送达方编码 | String | 是 | 无 | 单个送达方编码入参 | 客户在海尔建的送达方编码，如8800633175 |
| 3 | productCodes | 产品编码 | List<String> | 是 | 无 | 一次最多20个产品编码 | 产品编码为海尔内部产品编码,如 GA0SZC00U，或者产品编码列表 |
| 4 | priceType | 价格业务类型 | String | 是 | PT | 默认值 | 该价格场景对应的大B价格业务类型为 PT，该场景不支持溢价/特价/工程/样机/活动，且不受活动影响 |
| 5 | passWord | 约定密码 | String | 是 |  |  | 每个账号对应一个密码 |

#### Curl示例
```bash
curl --location --request POST 'https://openplat-test.haier.net/yilihuo/jsh-service-goods-price/api/goods-price/price-daily-sales/price-query/pt-out-list-price' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "customerCode": "8800633175",
  "sendToCode": "8800633175",
  "productCodes": ["GA0SZC00U"],
  "priceType": "PT",
  "passWord": "your_password"
}'
```

#### 返回参数
List<PriceSupplyVo>产品价格信息集合

| 序号 | 参数名称 | 中文名称 | 类型 | 备注 |
|------|----------|----------|------|------|
| 1 | productCode | 产品编码 | String | 1.产品编码为海尔内部产品编码,如 GA0SZC00U 2.查询价格前需先完成可采产品校验，如果未通过，则返回提示信息 1。 |
| 2 | supplyPrice | 普通供价 | BigDecimal | 如果查不到供价，则返回提示"价格未生效" |
| 3 | invoicePrice | 开票价 | BigDecimal | 开票价=普投供价*(1-直扣)-台返 |
| 4 | stockRebatePolicy | 直扣 | BigDecimal | 如果查询不到直扣，则显示0 |
| 5 | rebateMoney | 台返 | BigDecimal | 如果查询不到台返，则显示0 |
| 6 | stockRebatePolicy | 返利类型 | String | 执行供价返利类型 COM/FHQ/BF/DTDBF |
| 7 | reason | 提示信息 | String | 1.如果指定查询的产品编码不可查，则返回提示"商品暂不可采" 2.如果普通供价缺失，则返回提示"价格未生效" |
| 8 | isSales | 是否可采 | String | 是否可采（1可采，0不可采） |

### 2.3 RX库存三方直连库存查询接口

#### 接口概述
| 接口功能概述 | RX库存三方直连库存查询接口 |
|--------------|--------------------------|
| 请求方式 | post |
| Content-type | application/json |

#### 请求地址
| 环境 | 地址 |
|------|------|
| 测试 | OAuth2.0认证地址：https://openplat-test.haier.net/oauth2/auth 调用地址：https://openplat-test.haier.net/yilihuo/jsh-service-stock-mall/api/page/stock/get-available-stock-open |
| 预生产 | OAuth2.0认证地址：https://openplat-bj-aliyun-stage.haier.net/oauth2/auth 调用地址：https://openplat-bj-aliyun-stage.haier.net/yilihuo/jsh-service-stock-mall/api/page/stock/get-available-stock-open |
| 生产 | OAuth2.0认证地址：https://openplat-bj-aliyun.haier.net/oauth2/auth 调用地址：https://openplat-bj-aliyun.haier.net/yilihuo/jsh-service-stock-mall/api/page/stock/get-available-stock-open |

#### 请求报文
| 序号 | 参数名称 | 中文名称 | 类型 | 必填 | 默认值 | 备注 | 示例 |
|------|----------|----------|------|------|--------|------|------|
| 1 | salesCode | 售达方编码 | String | 是 | 无 | 单个客户编码入参 | 客户在海尔建户的售达方编码，如8800633175 |
| 2 | senderCode | 送达方编码 | String | 是 | 无 | 单个送达方编码入参 | 客户在海尔建的送达方编码，如8800633175 |
| 3 | productCode | 商品编码 | String | 是 | 无 | 商品编码 | 产品编码为海尔内部产品编码,如GA0SZC00U，或者产品编码列表 |
| 4 | countyCode | 区域编码 | String | 是 | 无 | 三级地址国标码 | 6位国标码 |
| 5 | source | 供货方标识 | String | 是 | JSH-B | 默认传：JSH-B |  |
| 6 | sellerPassword | 客户密码 | String | 是 | 无 |  |  |

#### Curl示例
```bash
curl --location --request POST 'https://openplat-test.haier.net/yilihuo/jsh-service-stock-mall/api/page/stock/get-available-stock-open' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "salesCode": "8800633175",
  "senderCode": "8800633175",
  "productCode": "GA0SZC00U",
  "countyCode": "110101",
  "source": "JSH-B",
  "sellerPassword": "your_password"
}'
```

#### 返回参数
| 序号 | 参数名称 | 中文名称 | 类型 | 备注 |
|------|----------|----------|------|------|
| 1 | secCode | 库位编码 | string | 库位编码 |
| 2 | timelinessData | 时效信息 | Object | 时效信息 |
| 3 | stock | 库存数量 | string | 库存数量 |
| 4 | warehouseGrade | 0:本级仓/1:上级仓 | string | 0:本级仓/1:上级仓 |

**timelinessData时效信息：**
| 序号 | 参数名称 | 中文名称 | 类型 | 备注 |
|------|----------|----------|------|------|
| 1 | cutTime | 截单时间 | string |  |
| 2 | achieveUserOrderCut | 预计送达用户时间 | date |  |
| 3 | hour | 配送用户时效 | string |  |
| 4 | isTranfer | 是否转运：0否 1是 | string |  |

### 2.4 物流信息查询

#### 接口概述
| 接口功能概述 | 零售查询物流信息 |
|--------------|-----------------|
| 接口调用地址 | /api/page/stock/logistics/sass/get-thirdparty-logistics-info-by-order-code-auth |
| 请求方式 | post |
| Content-type | application/json |

#### 请求地址
| 环境 | 地址 |
|------|------|
| 测试 | OAuth2.0认证地址：https://openplat-test.haier.net/oauth2/auth 调用地址：https://openplat-test.haier.net/yilihuo/ylh-cloud-service-stock/api/page/stock/logistics/sass/get-thirdparty-logistics-info-by-order-code-auth |
| 预生产 | OAuth2.0认证地址：https://openplat-bj-aliyun-stage.haier.net/oauth2/auth 调用地址：https://openplat-bj-aliyun-stage.haier.net/yilihuo/ylh-cloud-service-stock/api/page/stock/logistics/sass/get-thirdparty-logistics-info-by-order-code-auth |
| 生产 | OAuth2.0认证地址：https://openplat-bj-aliyun.haier.net/oauth2/auth 调用地址：https://openplat-bj-aliyun.haier.net/yilihuo/ylh-cloud-service-stock/api/page/stock/logistics/sass/get-thirdparty-logistics-info-by-order-code-auth |

#### 请求报文
| 序号 | 参数名称 | 中文名称 | 类型 | 必填 | 默认值 | 备注 | 示例 |
|------|----------|----------|------|------|--------|------|------|
| 1 | orderCode | 订单编码 | String | 是 | 无 |  | SO.20190106.000003 |
| 2 | deliveryRecordCode | 发货单号 | String | 否 | 无 |  | SO.20190106.000003.F1 |
| 3 | memberId | 会员id | Integer | 否 | 无 |  | 零售的客户id |
| 4 | sellerCode | 客户8码 | String | 是 | 无 |  | 零售客户8码 |
| 5 | sellerPassword | 客户密码 | String | 是 | 无 |  |  |

#### Curl示例
```bash
curl --location --request POST 'https://openplat-test.haier.net/yilihuo/ylh-cloud-service-stock/api/page/stock/logistics/sass/get-thirdparty-logistics-info-by-order-code-auth' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "orderCode": "SO.20190106.000003",
  "deliveryRecordCode": "SO.20190106.000003.F1",
  "memberId": 12345,
  "sellerCode": "8800633175",
  "sellerPassword": "your_password"
}'
```

#### 返回参数
| 序号 | 参数名称 | 中文名称 | 类型 | 备注 |
|------|----------|----------|------|------|
| 1 | getAllLogisticsInfoByOrderCode | 统仓云仓物流信息 | List<Object> | 统仓云仓物流信息 |
| 2 | getStockDeliveryLogisticsRecord | 智汇宝物流信息 | List<Object> | 智汇宝物流信息 |
| 3 | getStockDeliveryLogisticsRecordThirdparty | 智汇宝第三方快递信息 | List<Object> | 智汇宝第三方快递信息 |

### 2.5 付款方余额查询接口

#### 接口概述
| 接口功能概述 | B端付款方余额查询 |
|--------------|------------------|
| 请求方式 | post |
| Content-type | application/json |

#### 请求地址
- 测试: https://openplat-test.haier.net/yilihuo/jsh-service-finance-mall/api/page/account/account-balance-manager/get-payer-account-balance-by-customer-code
- 预生产: https://openplat-bj-aliyun-stage.haier.net/yilihuo/jsh-service-finance-mall/api/page/account/account-balance-manager/get-payer-account-balance-by-customer-code
- 生产: https://openplat-bj-aliyun.haier.net/yilihuo/jsh-service-finance-mall/api/page/account/account-balance-manager/get-payer-account-balance-by-customer-code

#### Body参数
| 序号 | 参数名称 | 中文名称 | 类型 | 必填 | 默认值 | 备注 | 示例 |
|------|----------|----------|------|------|--------|------|------|
| 1 | customerCode | 售达方编码 | String | 是 | 无 | 单个客户编码入参 | 客户在海尔建户的售达方编码，如 8800633175 |
| 2 | customerPassword | 客户密码 | String | 是 |  |  |  |

#### Curl示例
```bash
curl --location --request POST 'https://openplat-test.haier.net/yilihuo/jsh-service-finance-mall/api/page/account/account-balance-manager/get-payer-account-balance-by-customer-code' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "customerCode": "8800633175",
  "customerPassword": "your_password"
}'
```

#### 返回参数
| 序号 | 参数名称 | 中文名称 | 类型 | 备注 |
|------|----------|----------|------|------|
| 1 | saleGroupCode | 销售组织编码 | String | 销售组织编码 |
| 2 | saleGroupName | 销售组织名称 | String | 销售组织名称 |
| 3 | payerAccountCode | 付款方编码 | String | 付款方编码 |
| 4 | payerAccountName | 付款方名称 | String | 付款方名称 |
| 5 | payerAccountBalance | 付款方余额 | BigDecimal | 付款方余额 |

## 3. 鉴权

### 获取token接口
| 接口功能概述 | 获取token |
|--------------|-----------|
| 接口调用地址 | 开发环境: http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token 预生产环境：http://pre.yilihuo.com/ylh-cloud-mgt-auth-pre/oauth/token 生产环境：http://www.yilihuo.com/ylh-cloud-mgt-auth/oauth/token |
| 请求方式 | post |
| Content-type | application/json |

#### Headers
| 参数名称 | 参数值 | 是否必须 | 示例 | 备注 |
|----------|--------|----------|------|------|
| Content-Type | application/x-www-form-urlencoded | 是 |  |  |
| system-name | ylh-open-api | 是 |  |  |
| Authorization |  | 是 | 例如 Basic b3Blbl9hcGlfZXJwOjEyMzQ1Njc4 |  |

#### Body
| 参数名称 | 参数类型 | 是否必须 | 示例 | 备注 |
|----------|----------|----------|------|------|
| grant_type | T文本 | 是 | password | 固定值 password |
| username | T文本 | 是 | erp | 技术对接申请，见备注 |
| password | T文本 | 是 | 123qwe | 技术对接申请，见备注 |

#### Curl示例
```bash
curl --location --request POST 'http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'system-name: ylh-open-api' \
--header 'Authorization: Basic b3Blbl9hcGlfZXJwOjEyMzQ1Njc4' \
--data-urlencode 'grant_type=password' \
--data-urlencode 'username=erp' \
--data-urlencode 'password=123qwe'
```

### 3.1 订单创建

#### 接口概述
| 接口功能概述 | 接收水联网订单 |
|--------------|--------------|
| 接口调用地址 | 开发环境:http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev/api/page/hmm/retailorder/receive-hmm-retail-order 预生产环境：http://pre.yilihuo.com/ylh-cloud-service-jst-order-pre/api/page/hmm/retailorder/receive-hmm-retail-order 生产环境：http://www.yilihuo.com/ylh-cloud-service-jst-order/api/page/hmm/retailorder/receive-hmm-retail-order |
| 请求方式 | post |
| Content-type | application/json |

#### Body参数
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| sourceSystem | string | 必须 |  | 订单来源，跟3、订单同步到水联网接口-订单来源保持一致 |  |
| shopName | string | 必须 |  | 店铺名称，例如"XX旗舰店" |  |
| sellerCode | string | 必须 |  | 客户八码，测试环境使用"8800539012" |  |
| consigneeName | string | 必须 |  | 姓名，例如"李四" |  |
| consigneeMobile | string | 必须 |  | 手机号，例如"13900139000" |  |
| onlineNo | string | 必须 |  | 平台订单号，例如"HMM202300001" |  |
| soId | string | 必须 |  | 子订单号，需要唯一，例如"SUB202300001"，会校验子单号是否重复推送 |  |
| remark | string | 非必须 |  | 备注，例如"周末配送" |  |
| totalQty | integer | 必须 |  | 订单总数量，例如1 |  |
| totalAmt | number | 必须 |  | 订单总金额，例如1999.98 |  |
| createTime | integer | 必须 |  | 订单创建时间戳，毫秒时间戳，例如 1748931496 |  |
| province | string | 必须 |  | 省，例如"江苏省" |  |
| city | string | 必须 |  | 市，例如"南京市" |  |
| area | string | 必须 |  | 区，例如"鼓楼区" |  |
| town | string | 非必须 |  | 县，例如"中央门街道" |  |
| detailAddress | string | 必须 |  | 详细地址，例如"中山北路100号" |  |
| distributionTime | number | 非必须 |  | Date类型，配送时间，（时间戳） |  |
| installTime | number | 非必须 |  | Date类型，安装时间，（时间戳） |  |
| governmentOrder | boolean | 非必须 |  | 是否国补订单，例如 true |  |
| deliveryInstall | string | 必须 |  | 是否送装一体，例如 true，如果配送时间安装时间传值并且值相同，就传 true.如果配送时间安装时间都不传值，或者传的值不一样就传 false |  |
| itemList | object[] | 必须 |  | 订单明细集合 | item类型: object |
| productCode | string | 必须 |  | 商品编码，例如"BS01U000N" |  |
| itemQty | integer | 必须 |  | 商品数量，例如1，一单一台 |  |
| retailPrice | number | 必须 |  | 零售价，例如1299.99 |  |
| discountAmount | number | 必须 |  | 单件商品折扣金额（如果没有就传0），例如100.00 |  |
| actualPrice | number | 必须 |  | 实际成交价，例如1199.99 |  |
| isGift | boolean | 非必须 |  | 是否赠品，例如 false |  |

#### Curl示例
```bash
curl --location --request POST 'http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev/api/page/hmm/retailorder/receive-hmm-retail-order' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "sourceSystem": "system_name",
  "shopName": "XX旗舰店",
  "sellerCode": "8800539012",
  "consigneeName": "李四",
  "consigneeMobile": "13900139000",
  "onlineNo": "HMM202300001",
  "soId": "SUB202300001",
  "remark": "周末配送",
  "totalQty": 1,
  "totalAmt": 1999.98,
  "createTime": 1748931496,
  "province": "江苏省",
  "city": "南京市",
  "area": "鼓楼区",
  "town": "中央门街道",
  "detailAddress": "中山北路100号",
  "deliveryInstall": "true",
  "itemList": [
    {
      "productCode": "BS01U000N",
      "itemQty": 1,
      "retailPrice": 1299.99,
      "discountAmount": 100.00,
      "actualPrice": 1199.99,
      "isGift": false
    }
  ]
}'
```

### 3.2 订单取消

#### 接口概述
| 接口功能概述 | 取消订单 |
|--------------|---------|
| 接口调用地址 | 开发环境：http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev/api/page/hmm/retailorder/cancel-hmm-retail-order 预生产环境：http://pre.yilihuo.com/ylh-cloud-service-jst-order-pre/api/page/hmm/retailorder/cancel-hmm-retail-order 生产环境：http://www.yilihuo.com/ylh-cloud-service-jst-order/api/page/hmm/retailorder/cancel-hmm-retail-order |
| 请求方式 | post |
| Content-type | application/json |

#### Body参数
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| soId | string | 必须 |  | 需要取消的子订单号，对应创建订单的 sold |  |
| cancelTime | string | 必须 |  | 毫秒时间戳，取消/退货时间，1791990000 |  |
| cancelReason | string | 必须 |  | 订单取消原因，例如"客户要求取消" |  |
| sourceSystem | string | 必须 |  | 订单来源系统 |  |

#### Curl示例
```bash
curl --location --request POST 'http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev/api/page/hmm/retailorder/cancel-hmm-retail-order' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "soId": "SUB202300001",
  "cancelTime": "1791990000",
  "cancelReason": "客户要求取消",
  "sourceSystem": "system_name"
}'
```

### 3.3 订单改约

#### 接口概述
| 接口功能概述 | 订单改约 |
|--------------|---------|
| 接口调用地址 | 开发环境:http://dev.ylhtest.com/ylh-cloud-service-order-dev/api/page/retailorder/hmm/update-distribution-time 预生产环境：http://pre.yilihuo.com/ylh-cloud-service-order-pre/api/page/retailorder/hmm/update-distribution-time 生产环境：http://www.yilihuo.com/ylh-cloud-service-order/api/page/retailorder/hmm/update-distribution-time |
| 请求方式 | post |
| Content-type | application/json |

#### Body参数
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| retailOrderNo | string | 非必须 |  | 巨商汇订单号 |  |
| distributionTime | number | 非必须 |  | 配送时间（时间戳）时分秒必须为23:59:59 |  |
| installTime | number | 非必须 |  | 安装时间（时间戳）时分秒必须为23:59:59 |  |

#### Curl示例
```bash
curl --location --request POST 'http://dev.ylhtest.com/ylh-cloud-service-order-dev/api/page/retailorder/hmm/update-distribution-time' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "retailOrderNo": "SO202300001",
  "distributionTime": 1791990000,
  "installTime": 1791990000
}'
```

### 3.4 获取配送安装照片

#### 接口概述
| 接口功能概述 | 获取配送安装照片 |
|--------------|-----------------|
| 接口调用地址 | 开发环境:http://dev.ylhtest.com/ylh-cloud-service-order-dev/api/page/retailorder/search/get-retail-order-delivery-img 预生产环境：http://pre.yilihuo.com/ylh-cloud-service-order-pre/api/page/retailorder/search/get-retail-order-delivery-img 生产环境：http://www.yilihuo.com/ylh-cloud-service-order/api/page/retailorder/search/get-retail-order-delivery-img |
| 请求方式 | post |
| Content-type | application/json |

#### Body参数
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| orderNo | string | 必须 |  | 订单中台订单号，例如"SO.20250430.000001" |  |

#### Curl示例
```bash
curl --location --request POST 'http://dev.ylhtest.com/ylh-cloud-service-order-dev/api/page/retailorder/search/get-retail-order-delivery-img' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '{
  "orderNo": "SO.20250430.000001"
}'
```

### 3.5 通过SO单号查询物流单号、物流公司、SN码

#### 接口概述
| 接口功能概述 | 通过SO单号查询物流单号、物流公司、SN码 |
|--------------|--------------------------------------|
| 接口调用地址 | 开发环境：https://dev.ylhtest.com/ylh-cloud-service-stock-dev/api/composite/stock/logistics/get-store-logistics-by-order-code 预生产环境：https://pre.yilihuo.com/ylh-cloud-service-stock-pre/api/composite/stock/logistics/get-store-logistics-by-order-code 生产环境：https://www.yilihuo.com/ylh-cloud-service-stock/api/composite/stock/logistics/get-store-logistics-by-order-code |
| 请求方式 | post |
| Content-type | application/json |

#### Body参数
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
|  | string[] | 非必须 |  | 请求信息 | item类型: string |
|  |  | 非必须 |  | so单号，例如SO.20250514.014572 | 备注: so单号，例如SO.20250514.014572 |

#### Curl示例
```bash
curl --location --request POST 'https://dev.ylhtest.com/ylh-cloud-service-stock-dev/api/composite/stock/logistics/get-store-logistics-by-order-code' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${token}' \
--data-raw '[
  "SO.20250514.014572"
]'
```

## 4. 回调接口说明

### 简介
回调接口是平台调用客户的接口回传结果，为了统一开发格式及接口安全性，客户需按照回调接口标准来开发接口，双方接口通讯采用签名的方式，平台调用客户接口时增加签名，客户接口收到回调信息需验证签名，以确保调用方的可靠性。

### 接口约定
1. 客户需向平台提供如下信息，双方按照以下约定的方式加签和验证签名：
   - 1.1 测试、正式环境回调地址:对接方提供
   - 1.2 AppKey、secret密钥值：对接方提供
2. 数据统一使用 utf-8编码
3. POST内容，Content-Type: application/x-www-form-urlencoded
4. 签名机制：
   - 第一步，将除 sign除外的所有"参数+参数值"进行字典排序生成字符串
   - 第二步，将 secret加到该字符串的首尾并转小写,进行 MD5加密，加密后再转大写

### 4.1 确认订单回调-需要对接方实现

#### Data请求参数
| 参数名 | 是否必须 | 类型 | 描述 |
|--------|----------|------|------|
| ExtOrderNo | 非必须 | string | 海尔订单号，成功时，必须 |
| PlatformOrderNo | 必须 | string | 客户平台订单号 |
| State | 必须 | int | 状态：1、成功；0、失败 |
| FailMsg | 非必须 | string(100) | 失败原因 |

#### 请求参数
**Headers：**
| 参数名称 | 参数值 | 是否必须 | 示例 | 备注 |
|----------|--------|----------|------|------|
| Content-Type | application/x-www-form-urlencoded | 是 | application/x-www-form-urlencoded |  |

**Body:**
| 参数名称 | 参数类型 | 是否必须 | 示例 | 备注 |
|----------|----------|----------|------|------|
| AppKey | T文本 | 是 |  | string类型，应用 ID |
| TimeStamp | T文本 | 是 |  | string类型，时间戳，格式：20201123162059 |
| Sign | T文本 | 是 |  | string类型，签名 |
| Method | T文本 | 是 |  | 固定值"hmm.scm_heorder.confirm" |
| Data | T文本 | 否 |  | 请求参数体，参数内容见Data请求参数 |

#### Curl示例（平台调用客户接口）
```bash
curl --location --request POST 'https://your-callback-url.com/confirm-order' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode 'AppKey=hmma904eb75643b4eaa' \
--data-urlencode 'Data={"ExtOrderNo":"海尔订单号","PlatformOrderNo":"客户平台订单号","State":1}' \
--data-urlencode 'Method=hmm.scm_heorder.confirm' \
--data-urlencode 'Sign=7D4EA63E69B225C20B150D8F65938218' \
--data-urlencode 'TimeStamp=20230912113528'
```

#### 返回数据
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| data | object | 必须 |  | 业务数据 | 备注:业务数据 |
| code | string | 必须 |  | 业务成功或错误编码,success:表示成功 |  |
| description | string | 必须 |  | 业务成功或错误说明 |  |
| timeStamp | string | 必须 |  | 时间戳，格式：20201123162059 |  |
| success | boolean | 必须 |  | 是否成功 |  |

#### 返回结果示例
```json
{
  "success": true,
  "code": "success",
  "description": "成功",
  "timeStamp": "20250625133956",
  "data": {
    "statusCode": "200",
    "message": "成功",
    "platformOrderNo": "PO20240826369763"
  }
}
```

### 4.2 取消订单回调-需要对接方实现

#### Data请求参数
| 参数名 | 是否必须 | 类型 | 描述 |
|--------|----------|------|------|
| ExtOrderNo | 非必须 | string | 海尔订单号，成功时，必须 |
| PlatformOrderNo | 必须 | string | 客户平台订单号 |
| State | 必须 | int | 状态：1、成功；0、失败 |
| FailMsg | 非必须 | string(100) | 失败原因 |

#### Curl示例（平台调用客户接口）
```bash
curl --location --request POST 'https://your-callback-url.com/cancel-order' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode 'AppKey=hmma904eb75643b4eaa' \
--data-urlencode 'Data={"ExtOrderNo":"海尔订单号","PlatformOrderNo":"客户平台订单号","State":1}' \
--data-urlencode 'Method=hmm.scm_heorder.cancel' \
--data-urlencode 'Sign=7D4EA63E69B225C20B150D8F65938218' \
--data-urlencode 'TimeStamp=20230912113528'
```

#### 请求参数
**Headers：**
| 参数名称 | 参数值 | 是否必须 | 示例 | 备注 |
|----------|--------|----------|------|------|
| Content-Type | application/x-www-form-urlencoded | 是 | application/x-www-form-urlencoded |  |

**Body:**
| 参数名称 | 参数类型 | 是否必须 | 示例 | 备注 |
|----------|----------|----------|------|------|
| AppKey | T文本 | 是 |  | string类型，应用 ID |
| TimeStamp | T文本 | 是 |  | string类型，时间戳，格式：20201123162059 |
| Sign | T文本 | 是 |  | string类型，签名 |
| Method | T文本 | 是 |  | 固定值"hmm.scm_heorder.cancel" |
| Data | T文本 | 否 |  | 请求参数体，参数内容见Data请求参数 |

#### 返回数据
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| data | object | 必须 |  | 业务数据 | 备注:业务数据 |
| code | string | 必须 |  | 业务成功或错误编码,success表示成功 |  |
| description | string | 必须 |  | 业务成功或错误说明 |  |
| timeStamp | string | 必须 |  | 时间戳，格式：20201123162059 |  |
| success | boolean | 必须 |  | 是否成功 |  |

#### 返回结果示例
```json
{
  "success": true,
  "code": "success",
  "description": "成功",
  "timeStamp": "20250625133956",
  "data": {
    "statusCode": "200",
    "message": "成功",
    "platformOrderNo": "PO20240826369763"
  }
}
```

### 4.3 订单缺货回调-需要对接方实现

#### Data请求参数
| 参数名 | 是否必须 | 类型 | 描述 |
|--------|----------|------|------|
| ExtOrderNo | 非必须 | string | 海尔订单号，成功时，必须 |
| PlatformOrderNo | 必须 | string | 客户平台订单号 |
| State | 必须 | int | 状态：1、成功；0、失败 |
| FailMsg | 非必须 | string(100) | 失败原因 |

#### Curl示例（平台调用客户接口）
```bash
curl --location --request POST 'https://your-callback-url.com/oostock-order' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode 'AppKey=hmma904eb75643b4eaa' \
--data-urlencode 'Data={"ExtOrderNo":"海尔订单号","PlatformOrderNo":"客户平台订单号","State":1}' \
--data-urlencode 'Method=hmm.scm_heorder.oostock' \
--data-urlencode 'Sign=7D4EA63E69B225C20B150D8F65938218' \
--data-urlencode 'TimeStamp=20230912113528'
```

#### 请求参数
**Headers：**
| 参数名称 | 参数值 | 是否必须 | 示例 | 备注 |
|----------|--------|----------|------|------|
| Content-Type | application/x-www-form-urlencoded | 是 | application/x-www-form-urlencoded |  |

**Body:**
| 参数名称 | 参数类型 | 是否必须 | 示例 | 备注 |
|----------|----------|----------|------|------|
| AppKey | T文本 | 是 |  | string类型，应用 ID |
| TimeStamp | T文本 | 是 |  | string类型，时间戳，格式：20201123162059 |
| Sign | T文本 | 是 |  | string类型，签名 |
| Method | T文本 | 是 |  | 固定值"hmm.scm_heorder.oostock" |
| Data | T文本 | 否 |  | 请求参数体，参数内容见Data请求参数 |

#### 返回数据
| 名称 | 类型 | 是否必须 | 默认值 | 备注 | 其他信息 |
|------|------|----------|--------|------|----------|
| data | object | 必须 |  | 业务数据 | 备注:业务数据 |
| code | string | 必须 |  | 业务成功或错误编码,200:表示成功 |  |
| description | string | 必须 |  | 业务成功或错误说明 |  |
| timeStamp | string | 必须 |  | 时间戳，格式：20201123162059 |  |
| success | boolean | 必须 |  | 是否成功 |  |

#### 返回结果示例
```json
{
  "success": true,
  "code": "success",
  "description": "成功",
  "timeStamp": "20250625133956",
  "data": {
    "statusCode": "200",
    "message": "成功",
    "platformOrderNo": "PO20240826369763"
  }
}
```

## 5. 通用说明

### 5.1 签名算法示例代码
```java
/**
 * 获取签名
 * @param params 参数
 * @param secret 密钥
 * @return
 */
private String genSign(Map<String, Object> params, String secret) {
    //第一步，将除 sign除外的所有"参数+参数值"进行字典排序生成字符串
    Set<String> keySet = params.keySet();
    String[] keyArray = keySet.toArray(new String[keySet.size()]);
    Arrays.sort(keyArray);
    
    //第二步，将 secret加到该字符串的首尾
    StringBuilder sb = new StringBuilder();
    sb.append(secret);
    for (String k : keyArray) {
        if (StringUtil.isEmpty(params.get(k).toString()) || "Sign".equals(k)) {
            //参数值为空或者为 sign，则不参与签名
            continue;
        }
        if (!params.get(k).toString().trim().isEmpty()) {
            sb.append(k).append(params.get(k));
        }
    }
    sb.append(secret);
    
    //转小写,进行 MD5加密
    return SecureUtil.md5(sb.toString().toLowerCase()).toUpperCase();
}
```

### 5.2 错误码说明
| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| 400 | 参数错误 | 检查请求参数是否完整、格式是否正确 |
| 401 | 未授权 | 检查token是否有效、权限是否足够 |
| 403 | 禁止访问 | 检查接口权限、IP白名单设置 |
| 404 | 接口不存在 | 检查接口地址是否正确 |
| 500 | 服务器内部错误 | 联系技术支持 |
| 503 | 服务不可用 | 服务暂时不可用，请稍后重试 |

### 5.3 注意事项
1. **参数校验**：所有接口调用前请确保参数完整且格式正确
2. **频率限制**：接口调用频率限制为每秒100次，超过限制会被限流
3. **超时设置**：建议设置请求超时时间为30秒
4. **重试机制**：对于网络异常等情况，建议实现重试机制，最多重试3次
5. **日志记录**：建议记录所有接口请求和响应日志，便于问题排查
6. **安全传输**：所有接口调用必须使用HTTPS协议
7. **token管理**：token有效期为1小时，建议提前10分钟刷新token