# 集成API

<cite>
**本文档引用的文件**  
- [haierapi.py](file://backend/integrations/haierapi.py)
- [views.py](file://backend/integrations/views.py)
- [models.py](file://backend/integrations/models.py)
- [serializers.py](file://backend/integrations/serializers.py)
- [urls.py](file://backend/integrations/urls.py)
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py)
- [base.py](file://backend/backend/settings/base.py)
- [env_config.py](file://backend/backend/settings/env_config.py)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概述](#架构概述)
5. [详细组件分析](#详细组件分析)
6. [依赖分析](#依赖分析)
7. [性能考虑](#性能考虑)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)

## 简介
本文档详细介绍了与海尔系统的API集成功能，重点涵盖供应商数据同步、库存查询、配置管理、API调用机制和日志监控等方面。文档旨在为管理员和开发人员提供全面的技术指导，帮助他们理解和维护系统集成。

## 项目结构
项目结构清晰地划分了不同功能模块，其中`backend/integrations/`目录专门负责与外部系统的集成，特别是与海尔系统的对接。

```mermaid
graph TD
backend[backend/]
--> integrations[integrations/]
--> haierapi[haierapi.py]
--> models[models.py]
--> views[views.py]
--> serializers[serializers.py]
--> urls[urls.py]
backend --> catalog[catalog/]
--> management[management/]
--> commands[commands/]
--> sync_haier_products[sync_haier_products.py]
backend --> settings[backend/settings/]
--> base[base.py]
--> env_config[env_config.py]
```

**图示来源**
- [haierapi.py](file://backend/integrations/haierapi.py)
- [models.py](file://backend/integrations/models.py)
- [views.py](file://backend/integrations/views.py)
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py)
- [base.py](file://backend/backend/settings/base.py)

## 核心组件
本节分析与海尔系统集成的核心组件，包括API客户端、配置管理、数据同步和日志记录。

**本节来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L1-L214)
- [models.py](file://backend/integrations/models.py#L1-L150)
- [views.py](file://backend/integrations/views.py#L1-L327)

## 架构概述
系统通过`HaierAPI`客户端类与海尔API进行通信，使用Django REST Framework提供管理接口，并通过管理命令实现数据同步。

```mermaid
graph TD
Client[客户端/管理员]
--> API[REST API]
--> HaierAPIViewSet[HaierAPIViewSet]
--> HaierAPI[HaierAPI]
--> HaierSystem[海尔系统]
Admin[管理员]
--> Config[配置界面]
--> HaierConfigViewSet[HaierConfigViewSet]
--> HaierConfig[HaierConfig]
Cron[定时任务]
--> Command[管理命令]
--> sync_haier_products[sync_haier_products.py]
--> HaierAPI[HaierAPI]
```

**图示来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L10-L214)
- [views.py](file://backend/integrations/views.py#L104-L327)
- [models.py](file://backend/integrations/models.py#L4-L47)
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py#L13-L156)

## 详细组件分析
本节深入分析各个关键组件的实现细节。

### 海尔API客户端分析
`HaierAPI`类是与海尔系统通信的核心客户端，封装了认证、API调用和错误处理逻辑。

#### 类图
```mermaid
classDiagram
class HaierAPI {
+string client_id
+string client_secret
+string token_url
+string base_url
+string customer_code
+string send_to_code
+string supplier_code
+string password
+string seller_password
+string customer_password
+string access_token
+string token_type
+datetime token_expiry
+__init__(config)
+from_settings()
+authenticate() bool
+_ensure_authenticated() bool
+_auth_headers() dict
+get_products(product_codes) list
+get_product_prices(product_codes) list
+check_stock(product_code, county_code) dict
+get_logistics_info(order_code) dict
+get_account_balance() dict
}
```

**图示来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L10-L214)

**本节来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L10-L214)

### 配置管理分析
海尔API配置通过`HaierConfig`模型进行管理，支持在数据库中存储多个配置实例。

#### 类图
```mermaid
classDiagram
class HaierConfig {
+string name
+json config
+bool is_active
+datetime created_at
+datetime updated_at
+__str__()
}
class HaierConfigSerializer {
+validate_config(value)
}
class HaierConfigViewSet {
+get_serializer_class()
+test(request, pk)
}
HaierConfigViewSet --> HaierConfigSerializer : "使用"
HaierConfigSerializer --> HaierConfig : "序列化"
```

**图示来源**
- [models.py](file://backend/integrations/models.py#L4-L47)
- [serializers.py](file://backend/integrations/serializers.py#L8-L31)
- [views.py](file://backend/integrations/views.py#L36-L101)

**本节来源**
- [models.py](file://backend/integrations/models.py#L4-L47)
- [serializers.py](file://backend/integrations/serializers.py#L8-L31)
- [views.py](file://backend/integrations/views.py#L36-L101)

### 数据同步机制分析
供应商数据同步通过异步执行机制实现，支持按需同步特定商品或批量同步。

#### 序列图
```mermaid
sequenceDiagram
participant Admin as "管理员"
participant Command as "sync_haier_products"
participant API as "HaierAPI"
participant DB as "数据库"
Admin->>Command : 执行管理命令
Command->>API : authenticate()
API-->>Command : 认证结果
alt 认证成功
Command->>API : get_products()
API-->>Command : 商品数据
loop 处理每个商品
Command->>DB : sync_from_haier()
DB-->>Command : 同步结果
alt 需要同步价格
Command->>API : get_product_prices()
API-->>Command : 价格数据
end
alt 需要同步库存
Command->>API : check_stock()
API-->>Command : 库存数据
end
end
end
Command->>Admin : 输出同步结果
```

**图示来源**
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py#L13-L156)
- [haierapi.py](file://backend/integrations/haierapi.py#L74-L97)
- [models.py](file://backend/catalog/models.py)

**本节来源**
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py#L13-L156)

### 库存查询接口分析
供应商库存查询接口实现了缓存策略以提高性能和响应速度。

#### 流程图
```mermaid
flowchart TD
Start([开始查询库存]) --> ValidateInput["验证输入参数"]
ValidateInput --> InputValid{"参数有效?"}
InputValid --> |否| ReturnError["返回错误"]
InputValid --> |是| CheckCache["检查本地缓存"]
CheckCache --> CacheHit{"缓存命中?"}
CacheHit --> |是| ReturnCache["返回缓存数据"]
CacheHit --> |否| CallAPI["调用海尔API"]
CallAPI --> APIResult{"API调用成功?"}
APIResult --> |否| HandleError["处理错误"]
APIResult --> |是| UpdateCache["更新本地缓存"]
UpdateCache --> ReturnResult["返回结果"]
HandleError --> ReturnError
ReturnCache --> End([结束])
ReturnResult --> End
ReturnError --> End
```

**图示来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L121-L142)
- [base.py](file://backend/backend/settings/base.py#L213-L221)

**本节来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L121-L142)

### API调用机制分析
API调用实现了重试机制、错误处理和性能优化策略。

#### 序列图
```mermaid
sequenceDiagram
participant Client as "客户端"
participant View as "API视图"
participant API as "HaierAPI"
participant Logger as "日志系统"
Client->>View : 发起API请求
View->>API : _get_haier_api()
alt 配置存在
API->>API : authenticate()
API-->>View : API实例
View->>API : 执行具体操作
API->>API : _ensure_authenticated()
alt 需要重新认证
API->>API : authenticate()
end
API->>API : 发送HTTP请求
API-->>View : 返回结果
View-->>Client : 返回响应
else 配置错误
View-->>Client : 返回配置错误
end
API->>Logger : 记录错误日志
View->>Logger : 记录操作日志
```

**图示来源**
- [views.py](file://backend/integrations/views.py#L122-L327)
- [haierapi.py](file://backend/integrations/haierapi.py#L41-L69)
- [models.py](file://backend/integrations/models.py#L50-L150)

**本节来源**
- [views.py](file://backend/integrations/views.py#L122-L327)
- [haierapi.py](file://backend/integrations/haierapi.py#L41-L69)

## 依赖分析
系统组件之间的依赖关系清晰，遵循了良好的分层架构原则。

```mermaid
graph TD
haierapi[haierapi.py] --> requests[requests]
haierapi --> settings[settings]
views[views.py] --> haierapi[haierapi.py]
views --> models[models.py]
views --> serializers[serializers.py]
serializers[serializers.py] --> models[models.py]
urls[urls.py] --> views[views.py]
sync_haier_products[sync_haier_products.py] --> haierapi[haierapi.py]
sync_haier_products --> models[models.py]
sync_haier_products --> settings[settings]
base[base.py] --> env_config[env_config.py]
haierapi --> base[base.py]
```

**图示来源**
- [haierapi.py](file://backend/integrations/haierapi.py)
- [views.py](file://backend/integrations/views.py)
- [models.py](file://backend/integrations/models.py)
- [serializers.py](file://backend/integrations/serializers.py)
- [urls.py](file://backend/integrations/urls.py)
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py)
- [base.py](file://backend/backend/settings/base.py)

**本节来源**
- [haierapi.py](file://backend/integrations/haierapi.py)
- [views.py](file://backend/integrations/views.py)
- [models.py](file://backend/integrations/models.py)

## 性能考虑
系统在性能方面进行了多项优化，包括缓存策略、连接复用和异步处理。

**本节来源**
- [base.py](file://backend/backend/settings/base.py#L213-L221)
- [haierapi.py](file://backend/integrations/haierapi.py#L48-L61)
- [sync_haier_products.py](file://backend/catalog/management/commands/sync_haier_products.py)

## 故障排除指南
本节提供常见问题的排查方法和建议。

**本节来源**
- [haierapi.py](file://backend/integrations/haierapi.py#L50-L64)
- [views.py](file://backend/integrations/views.py#L94-L101)
- [models.py](file://backend/integrations/models.py#L50-L150)

## 结论
本文档全面介绍了与海尔系统的API集成方案，涵盖了配置管理、数据同步、库存查询、API调用机制和日志监控等关键方面。系统设计合理，具有良好的可维护性和扩展性，能够满足业务需求。