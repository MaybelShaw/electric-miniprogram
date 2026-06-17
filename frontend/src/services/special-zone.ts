import { http } from '../utils/request'
import { HomeStoreCard, ProductListResponse, SpecialZone } from '../types'

export const specialZoneService = {
  async getZones(storeId?: number | string, kind?: string): Promise<SpecialZone[]> {
    const params = { ...(storeId ? { store: storeId } : {}), ...(kind ? { kind } : {}) }
    const response = await http.get<{ count: number; results: SpecialZone[] }>(
      '/catalog/special-zones/',
      params,
      false
    )
    return response.results || []
  },

  async getZone(id: number): Promise<SpecialZone> {
    return http.get<SpecialZone>(`/catalog/special-zones/${id}/`, undefined, false)
  },

  async getZoneProducts(
    zoneId: number,
    params?: { page?: number; page_size?: number; store?: number | string }
  ): Promise<ProductListResponse> {
    return http.get<ProductListResponse>(
      '/catalog/products/',
      { ...(params || {}), special_zone: zoneId },
      false
    )
  },

  async getHomeStoreCards(params?: { store?: number | string }): Promise<HomeStoreCard[]> {
    const response = await http.get<{ count: number; results: HomeStoreCard[] }>(
      '/catalog/home-store-cards/',
      params,
      false
    )
    return response.results || []
  },
}
