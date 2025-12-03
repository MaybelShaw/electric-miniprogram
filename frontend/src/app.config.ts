export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/category/index',
    // Product list page
    'pages/product-list/index',
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
    'pages/company-certification/index',
    'pages/credit-account/index',
    'pages/account-statements/index',
    'pages/statement-detail/index',
    'pages/account-transactions/index',
    'pages/debt-reconciliation/index',
    'pages/invoice-request/index',
    'pages/request-return/index',
    'pages/return-tracking/index',
    // Support pages
    'pages/support-chat/index',
    'pages/support-chat/select-order/index',
    'pages/support-chat/select-product/index'
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
        text: '首页',
        iconPath: 'assets/tabbar/home.png',
        selectedIconPath: 'assets/tabbar/home-active.png'
      },
      {
        pagePath: 'pages/category/index',
        text: '分类',
        iconPath: 'assets/tabbar/category.png',
        selectedIconPath: 'assets/tabbar/category-active.png'
      },
      {
        pagePath: 'pages/cart/index',
        text: '购物车',
        iconPath: 'assets/tabbar/cart.png',
        selectedIconPath: 'assets/tabbar/cart-active.png'
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/tabbar/profile.png',
        selectedIconPath: 'assets/tabbar/profile-active.png'
      }
    ]
  }
})
