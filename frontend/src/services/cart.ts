import { http } from '../utils/request'
import { Cart } from '../types'

export const cartService = {
  // 获取购物车
  async getCart(): Promise<Cart> {
    return http.get<Cart>('/cart/my_cart/')
  },
  
  // 添加商品到购物车
  async addItem(product_id: number, quantity = 1): Promise<Cart> {
    const data = {
      product_id: product_id,
      quantity: quantity
    }
    return http.post<Cart>('/cart/add_item/', data)
  },
  
  // 更新商品数量
  async updateItem(product_id: number, quantity: number): Promise<Cart> {
    if (!product_id) {
      throw new Error('product_id is required')
    }
    
    const data = {
      product_id: product_id,
      quantity: quantity
    }
    return http.post<Cart>('/cart/update_item/', data)
  },
  
  // 移除商品
  async removeItem(product_id: number): Promise<Cart> {
    const data = {
      product_id: product_id
    }
    return http.post<Cart>('/cart/remove_item/', data)
  },
  
  // 清空购物车
  async clearCart(): Promise<Cart> {
    return http.post<Cart>('/cart/clear/')
  }
}
