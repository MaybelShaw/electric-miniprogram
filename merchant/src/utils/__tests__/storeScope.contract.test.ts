import { withSelectedStoreId } from '../storeScope';

export function storeScopePayloadContract() {
  const filled = withSelectedStoreId({ name: '瓷砖' }, 12);
  const explicit = withSelectedStoreId({ name: '瓷砖', store_id: 8 }, 12);
  const withoutStore = withSelectedStoreId({ name: '瓷砖' }, null);

  const filledStoreId: number = filled.store_id;
  const explicitStoreId: number = explicit.store_id;

  return {
    filledStoreId,
    explicitStoreId,
    withoutStore,
  };
}
