import { getSelectedStoreId } from './store';

type StoreScopedPayload = Record<string, any>;

export function withSelectedStoreId<T extends StoreScopedPayload>(
  data: T,
  fallbackStoreId: number,
): T & { store_id: number };
export function withSelectedStoreId<T extends StoreScopedPayload>(
  data: T,
  fallbackStoreId?: number | null,
): T;
export function withSelectedStoreId<T extends StoreScopedPayload>(
  data: T,
  fallbackStoreId: number | null = getSelectedStoreId(),
): T | (T & { store_id: number }) {
  if (data.store_id || data.store || !fallbackStoreId) {
    return data;
  }

  return {
    ...data,
    store_id: fallbackStoreId,
  };
}
