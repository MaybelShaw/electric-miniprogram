import { http } from '../utils/request'
import { LegacySpecialZoneType, SpecialZoneCover } from '../types'

export const specialZoneCoverService = {
  async getCovers(params?: { type?: LegacySpecialZoneType; store?: number | string; store_id?: number | string }): Promise<SpecialZoneCover[]> {
    const response = await http.get<{ count: number; results: SpecialZoneCover[] }>(
      '/catalog/special-zone-covers/',
      params,
      false
    )
    return response.results || []
  },
}
