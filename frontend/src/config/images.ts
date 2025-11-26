/**
 * 图片资源配置
 * 使用网络占位图，方便快速开发
 * 生产环境请替换为实际图片
 */

const PLACEHOLDER_BASE = 'https://via.placeholder.com'

export const IMAGES = {
  // TabBar 图标 (已在 app.config.ts 中临时移除)
  tabHome: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Home`,
  tabHomeActive: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Home`,
  tabCategory: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Category`,
  tabCategoryActive: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Category`,
  tabCart: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Cart`,
  tabCartActive: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Cart`,
  tabProfile: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Profile`,
  tabProfileActive: `${PLACEHOLDER_BASE}/81x81/1989FA/FFFFFF?text=Profile`,
  
  // 功能图标
  search: `${PLACEHOLDER_BASE}/32x32/F7F8FA/969799?text=🔍`,
  arrowRight: `${PLACEHOLDER_BASE}/24x24/F7F8FA/969799?text=>`,
  favorite: `${PLACEHOLDER_BASE}/48x48/F7F8FA/969799?text=♡`,
  favoriteActive: `${PLACEHOLDER_BASE}/48x48/FF6034/FFFFFF?text=♥`,
  cart: `${PLACEHOLDER_BASE}/48x48/F7F8FA/969799?text=🛒`,
  address: `${PLACEHOLDER_BASE}/48x48/F7F8FA/969799?text=📍`,
  defaultAvatar: `${PLACEHOLDER_BASE}/120x120/F7F8FA/969799?text=👤`,
  
  // 空状态图标
  emptyCart: `${PLACEHOLDER_BASE}/300x300/F7F8FA/969799?text=Empty+Cart`,
  emptyOrder: `${PLACEHOLDER_BASE}/300x300/F7F8FA/969799?text=No+Orders`,
  emptyFavorite: `${PLACEHOLDER_BASE}/300x300/F7F8FA/969799?text=No+Favorites`,
  emptySearch: `${PLACEHOLDER_BASE}/300x300/F7F8FA/969799?text=No+Results`,
  
  // 订单状态图标
  orderPending: `${PLACEHOLDER_BASE}/80x80/FFA726/FFFFFF?text=Pending`,
  orderPaid: `${PLACEHOLDER_BASE}/80x80/66BB6A/FFFFFF?text=Paid`,
  orderShipped: `${PLACEHOLDER_BASE}/80x80/42A5F5/FFFFFF?text=Shipped`,
  orderCompleted: `${PLACEHOLDER_BASE}/80x80/26A69A/FFFFFF?text=Done`,
  
  // 轮播图
  banner1: `${PLACEHOLDER_BASE}/750x360/1989FA/FFFFFF?text=Banner+1`,
  banner2: `${PLACEHOLDER_BASE}/750x360/FF6034/FFFFFF?text=Banner+2`,
  banner3: `${PLACEHOLDER_BASE}/750x360/66BB6A/FFFFFF?text=Banner+3`,
  
  // 分类图标生成函数
  getCategoryIcon: (name: string) => 
    `${PLACEHOLDER_BASE}/96x96/F7F8FA/969799?text=${encodeURIComponent(name)}`,
}

// 商品占位图
export const getProductPlaceholder = (width = 300, height = 300) => 
  `${PLACEHOLDER_BASE}/${width}x${height}/F7F8FA/969799?text=Product`

// 品牌 Logo 占位图
export const getBrandPlaceholder = (name: string) => 
  `${PLACEHOLDER_BASE}/160x80/F7F8FA/969799?text=${encodeURIComponent(name)}`
