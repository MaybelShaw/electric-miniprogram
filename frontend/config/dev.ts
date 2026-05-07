import type { UserConfigExport } from "@tarojs/cli"

export default {
  defineConstants: {
    'process.env.TARO_APP_API_BASE_URL': JSON.stringify(process.env.TARO_APP_API_BASE_URL || 'http://127.0.0.1:8000/api'),
    'process.env.TARO_APP_ALLOW_REMOTE_MEDIA': JSON.stringify(process.env.TARO_APP_ALLOW_REMOTE_MEDIA || 'false'),
    'process.env.TARO_APP_WECHAT_CONFIRM_RECEIPT_APPID': JSON.stringify(process.env.TARO_APP_WECHAT_CONFIRM_RECEIPT_APPID || '')
  },
  mini: {},
  h5: {}
} satisfies UserConfigExport<'vite'>
