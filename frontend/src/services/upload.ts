import Taro from '@tarojs/taro'
import { TokenManager, BASE_URL } from '../utils/request'

export const uploadService = {
  /**
   * 上传图片
   * @param filePath 本地文件路径
   * @returns Promise<string> 返回图片URL
   */
  async uploadImage(filePath: string): Promise<string> {
    const token = TokenManager.getAccessToken()
    
    return new Promise((resolve, reject) => {
      Taro.uploadFile({
        url: `${BASE_URL}/media-images/`,
        filePath: filePath,
        name: 'file',
        header: {
          'Authorization': `Bearer ${token}`
        },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              const data = JSON.parse(res.data)
              resolve(data.url)
            } catch (e) {
              reject(new Error('解析响应失败'))
            }
          } else {
            reject(new Error(`上传失败: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          reject(new Error(err.errMsg || '上传失败'))
        }
      })
    })
  }
}
