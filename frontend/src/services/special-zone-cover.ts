import { http } from '../utils/request'
import { SpecialZoneCover } from '../types'

export const specialZoneCoverService = {
  async getCovers(params?: { type?: 'gift' | 'designer' }): Promise<SpecialZoneCover[]> {
    const response = await http.get<{ count: number; results: SpecialZoneCover[] }>(
      '/catalog/special-zone-covers/',
      params,
      false
    )
    return response.results || []
  },
}
