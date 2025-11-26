import { http } from '../utils/request'
import { Address } from '../types'

export const addressService = {
  // 获取地址列表
  async getAddresses(): Promise<Address[]> {
    return http.get<Address[]>('/addresses/')
  },
  
  // 创建地址
  async createAddress(data: Omit<Address, 'id'>): Promise<Address> {
    return http.post<Address>('/addresses/', data)
  },
  
  // 更新地址
  async updateAddress(id: number, data: Partial<Address>): Promise<Address> {
    return http.patch<Address>(`/addresses/${id}/`, data)
  },
  
  // 删除地址
  async deleteAddress(id: number): Promise<void> {
    return http.delete(`/addresses/${id}/`)
  },
  
  // 设为默认地址
  async setDefaultAddress(id: number): Promise<{ status: string }> {
    return http.post<{ status: string }>(`/addresses/${id}/set_default/`)
  },
  
  // 地址智能解析
  async parseAddress(address: string): Promise<{
    success: boolean
    message: string
    data: {
      province: string | null
      city: string | null
      district: string | null
      detail: string | null
    }
  }> {
    return http.post('/addresses/parse/', { address })
  }
}
