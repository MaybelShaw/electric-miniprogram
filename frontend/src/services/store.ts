import { http } from '../utils/request'
import { PaginatedResponse, PublicStoreDetail, Store } from '../types'

export const storeService = {
  async getPartnerStores(params?: { platform?: number | string; page?: number; page_size?: number }): Promise<PaginatedResponse<Store>> {
    return http.get<PaginatedResponse<Store>>('/stores/public/partners/', params, false)
  },

  async getStoreDetail(id: number | string, params?: { category_id?: number }): Promise<PublicStoreDetail> {
    return http.get<PublicStoreDetail>(`/stores/public/${id}/detail/`, params, false)
  },
}
