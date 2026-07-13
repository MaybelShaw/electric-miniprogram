import { http } from '../utils/request'
import { PaginatedResponse, PartnerEntryConfig, PublicStoreDetail, Store } from '../types'

export const storeService = {
  async getPartnerStores(params?: { platform?: number | string; page?: number; page_size?: number }): Promise<PaginatedResponse<Store>> {
    return http.get<PaginatedResponse<Store>>('/stores/public/partners/', params, { needAuth: false, showLoading: false })
  },

  async getPartnerEntryConfig(): Promise<PartnerEntryConfig> {
    return http.get<PartnerEntryConfig>('/stores/public/partner-entry-config/', undefined, { needAuth: false, showLoading: false })
  },

  async getStoreDetail(id: number | string, params?: { category_id?: number }): Promise<PublicStoreDetail> {
    return http.get<PublicStoreDetail>(`/stores/public/${id}/detail/`, params, { needAuth: false, showLoading: false })
  },
}
