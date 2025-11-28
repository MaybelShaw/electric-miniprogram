export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/category/index',
    'pages/cart/index',
    'pages/profile/index',
    'pages/product-detail/index',
    'pages/order-list/index',
    'pages/order-confirm/index',
    'pages/order-detail/index',
    'pages/address-list/index',
    'pages/address-edit/index',
    'pages/profile-edit/index',
    'pages/search/index',
    'pages/brand/index',
    'pages/company-certification/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '家电商城',
    navigationBarTextStyle: 'black',
    backgroundColor: '#F7F8FA'
  },
  tabBar: {
    color: '#969799',
    selectedColor: '#1989FA',
    backgroundColor: '#fff',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/home/index',
        text: '首页'
      },
      {
        pagePath: 'pages/category/index',
        text: '分类'
      },
      {
        pagePath: 'pages/cart/index',
        text: '购物车'
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的'
      }
    ]
  }
})
