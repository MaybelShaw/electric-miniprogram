/**
 * 生成占位图片脚本
 * 使用 Node.js 运行: node scripts/generate-placeholder-images.js
 */

const fs = require('fs');
const path = require('path');

// 确保 assets 目录存在
const assetsDir = path.join(__dirname, '../src/assets');
const categoryDir = path.join(assetsDir, 'category');

if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true });
}

if (!fs.existsSync(categoryDir)) {
  fs.mkdirSync(categoryDir, { recursive: true });
}

// 生成简单的 SVG 占位图
function generateSVG(width, height, text, bgColor = '#CCCCCC', textColor = '#666666') {
  return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="${width}" height="${height}" fill="${bgColor}"/>
  <text x="50%" y="50%" font-family="Arial" font-size="14" fill="${textColor}" text-anchor="middle" dominant-baseline="middle">${text}</text>
</svg>`;
}

// 将 SVG 转换为 base64 并保存为文件
function saveSVGAsFile(filename, svg) {
  const base64 = Buffer.from(svg).toString('base64');
  const dataUrl = `data:image/svg+xml;base64,${base64}`;
  
  // 创建一个简单的 1x1 透明 PNG (最小的有效 PNG)
  // 这里我们使用 SVG 的 base64，实际使用时微信小程序会处理
  const content = `<!-- SVG Placeholder: ${filename} -->\n${svg}`;
  
  fs.writeFileSync(filename, content);
  console.log(`✓ Created: ${path.basename(filename)}`);
}

// 生成所有需要的占位图
const images = [
  // TabBar 图标
  { name: 'tab-home.png', width: 81, height: 81, text: '首页', color: '#1989FA' },
  { name: 'tab-home-active.png', width: 81, height: 81, text: '首页', color: '#1989FA' },
  { name: 'tab-category.png', width: 81, height: 81, text: '分类', color: '#1989FA' },
  { name: 'tab-category-active.png', width: 81, height: 81, text: '分类', color: '#1989FA' },
  { name: 'tab-cart.png', width: 81, height: 81, text: '购物车', color: '#1989FA' },
  { name: 'tab-cart-active.png', width: 81, height: 81, text: '购物车', color: '#1989FA' },
  { name: 'tab-profile.png', width: 81, height: 81, text: '我的', color: '#1989FA' },
  { name: 'tab-profile-active.png', width: 81, height: 81, text: '我的', color: '#1989FA' },
  
  // 功能图标
  { name: 'search.png', width: 32, height: 32, text: '🔍', color: '#F7F8FA' },
  { name: 'arrow-right.png', width: 24, height: 24, text: '>', color: '#F7F8FA' },
  { name: 'favorite.png', width: 48, height: 48, text: '♡', color: '#F7F8FA' },
  { name: 'favorite-active.png', width: 48, height: 48, text: '♥', color: '#FF6034' },
  { name: 'cart.png', width: 48, height: 48, text: '🛒', color: '#F7F8FA' },
  { name: 'address.png', width: 48, height: 48, text: '📍', color: '#F7F8FA' },
  { name: 'default-avatar.png', width: 120, height: 120, text: '👤', color: '#F7F8FA' },
  
  // 空状态图标
  { name: 'empty-cart.png', width: 300, height: 300, text: '购物车空空如也', color: '#F7F8FA' },
  { name: 'empty-order.png', width: 300, height: 300, text: '暂无订单', color: '#F7F8FA' },
  { name: 'empty-favorite.png', width: 300, height: 300, text: '暂无收藏', color: '#F7F8FA' },
  { name: 'empty-search.png', width: 300, height: 300, text: '无搜索结果', color: '#F7F8FA' },
  
  // 订单状态图标
  { name: 'order-pending.png', width: 80, height: 80, text: '待付', color: '#FFA726' },
  { name: 'order-paid.png', width: 80, height: 80, text: '已付', color: '#66BB6A' },
  { name: 'order-shipped.png', width: 80, height: 80, text: '已发', color: '#42A5F5' },
  { name: 'order-completed.png', width: 80, height: 80, text: '完成', color: '#26A69A' },
  
  // 轮播图
  { name: 'banner1.jpg', width: 750, height: 360, text: 'Banner 1', color: '#1989FA' },
  { name: 'banner2.jpg', width: 750, height: 360, text: 'Banner 2', color: '#FF6034' },
  { name: 'banner3.jpg', width: 750, height: 360, text: 'Banner 3', color: '#66BB6A' },
];

// 分类图标
const categories = ['空调', '冰箱', '洗衣机', '电视', '热水器', '油烟机', '燃气灶', '微波炉'];

console.log('Generating placeholder images...\n');

// 生成主要图片
images.forEach(img => {
  const filepath = path.join(assetsDir, img.name);
  const svg = generateSVG(img.width, img.height, img.text, img.color);
  saveSVGAsFile(filepath, svg);
});

// 生成分类图标
categories.forEach(cat => {
  const filepath = path.join(categoryDir, `${cat}.png`);
  const svg = generateSVG(96, 96, cat, '#F7F8FA');
  saveSVGAsFile(filepath, svg);
});

console.log('\n✅ All placeholder images generated!');
console.log('\n⚠️  Note: These are SVG placeholders. For production, please replace with actual PNG/JPG images.');
console.log('📖 See src/assets/README.md for more information.\n');
