const SELECTED_STORE_KEY = 'selected_store_id';

export const getSelectedStoreId = (): number | null => {
  const value = localStorage.getItem(SELECTED_STORE_KEY);
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const setSelectedStoreId = (storeId: number | null): void => {
  if (!storeId) {
    localStorage.removeItem(SELECTED_STORE_KEY);
    return;
  }
  localStorage.setItem(SELECTED_STORE_KEY, String(storeId));
};
