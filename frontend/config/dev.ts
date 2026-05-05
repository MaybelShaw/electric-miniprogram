import type { UserConfigExport } from "@tarojs/cli"

export default {
  defineConstants: {
    'process.env.TARO_APP_API_BASE_URL': JSON.stringify(process.env.TARO_APP_API_BASE_URL || 'http://127.0.0.1:8000/api')
  },
  mini: {},
  h5: {}
} satisfies UserConfigExport<'vite'>
