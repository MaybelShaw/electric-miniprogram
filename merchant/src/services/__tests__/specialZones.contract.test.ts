import {
  bindSpecialZoneProduct,
  deleteSpecialZone,
  getSpecialZoneProducts,
  getSpecialZones,
  removeSpecialZoneProduct,
  updateSpecialZoneProduct,
} from '../api';
import type { SpecialZone, SpecialZoneProduct } from '../types';

export async function specialZoneApiContract() {
  const zone: SpecialZone = {
    id: 1,
    store: 1,
    title: '618大促',
    slug: '618-sale',
    kind: 'activity',
    subtitle: '',
    cover_image: '',
    is_active: true,
    show_on_home: true,
    home_order: 1,
    start_at: null,
    end_at: null,
    created_at: '',
    updated_at: '',
  };
  const binding: SpecialZoneProduct = {
    id: 1,
    zone: zone.id,
    product: {
      id: 2,
      name: '床垫',
      price: 100,
      stock: 10,
      is_active: true,
      source: 'local',
    },
    product_id: 2,
    is_active: true,
    order: 1,
    created_at: '',
  };

  await getSpecialZones({ store: zone.store });
  await getSpecialZoneProducts(zone.id);
  await bindSpecialZoneProduct(zone.id, {
    product_id: binding.product_id,
    order: binding.order,
    is_active: binding.is_active,
  });
  await updateSpecialZoneProduct(zone.id, binding.product_id, {
    order: binding.order + 1,
    is_active: false,
  });
  await removeSpecialZoneProduct(zone.id, binding.product_id);
  await deleteSpecialZone(zone.id);
}
