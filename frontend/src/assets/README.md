# 图片资源说明

本目录用于存放小程序运行所需的本地图片资源。本项目本地和 Docker 开发默认不使用外部占位图服务，也不依赖云端图片地址。

## 必需的图片资源

### 1. TabBar 图标

如需恢复 TabBar 图片图标，请准备以下本地图片，建议尺寸 81x81px：

```text
assets/
|-- tab-home.png
|-- tab-home-active.png
|-- tab-category.png
|-- tab-category-active.png
|-- tab-cart.png
|-- tab-cart-active.png
|-- tab-profile.png
`-- tab-profile-active.png
```

然后在 `src/app.config.ts` 中配置 `iconPath` 和 `selectedIconPath`。

### 2. 功能图标

```text
assets/
|-- search.png
|-- arrow-right.png
|-- favorite.png
|-- favorite-active.png
|-- cart.png
|-- address.png
`-- default-avatar.png
```

### 3. 空状态图标

```text
assets/
|-- empty-cart.png
|-- empty-order.png
|-- empty-favorite.png
`-- empty-search.png
```

### 4. 订单状态图标

```text
assets/
|-- order-pending.png
|-- order-paid.png
|-- order-shipped.png
`-- order-completed.png
```

### 5. 分类图标

根据实际分类准备本地图片，建议尺寸 96x96px：

```text
assets/category/
|-- air-conditioner.png
|-- refrigerator.png
|-- washing-machine.png
|-- tv.png
`-- ...
```

### 6. 轮播图

建议尺寸 750x360px：

```text
assets/
|-- banner1.jpg
|-- banner2.jpg
`-- banner3.jpg
```

## 本地开发占位方案

1. 优先使用页面内的纯样式占位块，例如 `View` + 文案，不发起图片请求。
2. 如必须使用图片，请放入本目录并通过 `/assets/xxx.png` 引用。
3. 不要在运行时代码、配置或会被 Taro 复制到产物中的资源文件里写入外部图片 URL。

## 图片准备建议

1. **格式**：PNG 用于透明背景图标，JPG 用于照片类图片。
2. **大小**：单个图片建议不超过 200KB。
3. **命名**：使用英文和数字，避免中文文件名。
4. **优化**：提交前压缩图片体积。
5. **适配**：关键图标准备 2x 和 3x 版本以适配不同屏幕。
