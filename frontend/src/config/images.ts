export const IMAGES = {
  // TabBar 图标 (已在 app.config.ts 中临时移除)
  tabHome: '',
  tabHomeActive: '',
  tabCategory: '',
  tabCategoryActive: '',
  tabCart: '',
  tabCartActive: '',
  tabProfile: '',
  tabProfileActive: '',

  // 功能图标
  search: '',
  arrowRight: '',
  favorite: '',
  favoriteActive: '',
  cart: '',
  address: '',
  defaultAvatar: '',

  // 空状态图标
  emptyCart: '',
  emptyOrder: '',
  emptyFavorite: '',
  emptySearch: '',

  // 订单状态图标
  orderPending: '',
  orderPaid: '',
  orderShipped: '',
  orderCompleted: '',

  // 轮播图
  banner1: '',
  banner2: '',
  banner3: '',

  // 分类图标生成函数
  getCategoryIcon: (_name: string) => '',
}

// 商品占位图
export const getProductPlaceholder = (_width = 300, _height = 300) => ''

// 品牌 Logo 占位图
export const getBrandPlaceholder = (_name: string) => ''
