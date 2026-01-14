import { http } from '../utils/request'
import { SpecialZone } from '../types'

export const specialZoneService = {
  async getSpecialZones(params?: { type?: 'gift' | 'designer' }): Promise<SpecialZone[]> {
    const response = await http.get<{ count: number; results: SpecialZone[] }>('/catalog/special-zones/', params, false)
    return response.results || []
  },
}
