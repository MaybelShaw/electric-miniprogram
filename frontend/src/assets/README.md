# 图片资源说明

本目录用于存放小程序所需的图片资源。

## 必需的图片资源

### 1. TabBar 图标 (可选，已临时移除)

如需显示 TabBar 图标，请准备以下图片 (建议尺寸 81x81px):

```
assets/
├── tab-home.png              # 首页图标
├── tab-home-active.png       # 首页选中图标
├── tab-category.png          # 分类图标
├── tab-category-active.png   # 分类选中图标
├── tab-cart.png              # 购物车图标
├── tab-cart-active.png       # 购物车选中图标
├── tab-profile.png           # 我的图标
└── tab-profile-active.png    # 我的选中图标
```

然后在 `src/app.config.ts` 中取消注释 iconPath 和 selectedIconPath。

### 2. 功能图标

```
assets/
├── search.png                # 搜索图标 (32x32px)
├── arrow-right.png           # 右箭头 (24x24px)
├── favorite.png              # 收藏图标 (48x48px)
├── favorite-active.png       # 收藏选中图标 (48x48px)
├── cart.png                  # 购物车图标 (48x48px)
├── address.png               # 地址图标 (48x48px)
└── default-avatar.png        # 默认头像 (120x120px)
```

### 3. 空状态图标

```
assets/
├── empty-cart.png            # 购物车为空 (300x300px)
├── empty-order.png           # 订单为空 (300x300px)
├── empty-favorite.png        # 收藏为空 (300x300px)
└── empty-search.png          # 搜索无结果 (300x300px)
```

### 4. 订单状态图标

```
assets/
├── order-pending.png         # 待支付 (80x80px)
├── order-paid.png            # 已支付 (80x80px)
├── order-shipped.png         # 已发货 (80x80px)
└── order-completed.png       # 已完成 (80x80px)
```

### 5. 分类图标

根据实际分类准备，建议尺寸 96x96px:

```
assets/category/
├── 空调.png
├── 冰箱.png
├── 洗衣机.png
├── 电视.png
└── ...
```

### 6. 轮播图

建议尺寸 750x360px:

```
assets/
├── banner1.jpg
├── banner2.jpg
└── banner3.jpg
```

## 临时解决方案

### 方案 1: 使用网络图片

将代码中的本地图片路径替换为网络图片 URL，例如：

```typescript
// 替换前
<Image src='/assets/search.png' />

// 替换后
<Image src='https://via.placeholder.com/32' />
```

### 方案 2: 使用 Base64 图片

创建简单的 Base64 图片数据。

### 方案 3: 使用 iconfont

使用阿里巴巴矢量图标库 (iconfont.cn) 替代图片图标。

### 方案 4: 暂时注释图片

在开发阶段，可以暂时注释掉图片相关代码，先测试功能逻辑。

## 图片准备建议

1. **格式**: PNG (透明背景) 或 JPG (照片)
2. **大小**: 单个图片不超过 200KB
3. **命名**: 使用英文和数字，避免中文
4. **优化**: 使用 TinyPNG 等工具压缩
5. **适配**: 准备 2x 和 3x 图以适配不同屏幕

## 在线图标资源

- [iconfont](https://www.iconfont.cn/) - 阿里巴巴矢量图标库
- [IconPark](https://iconpark.oceanengine.com/) - 字节跳动图标库
- [Flaticon](https://www.flaticon.com/) - 免费图标
- [Unsplash](https://unsplash.com/) - 免费高质量图片

## 快速生成占位图

可以使用以下在线服务生成占位图：

- https://via.placeholder.com/150
- https://dummyimage.com/150x150
- https://picsum.photos/150

示例：
```
https://via.placeholder.com/81x81/1989FA/FFFFFF?text=Home
```
