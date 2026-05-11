import type { CurrentStoreContext } from '@/services/types';

export const STORE_OPERATION_ROUTE_KEYS = new Set([
  '/admin/sales-stats',
  '/admin/account-statements',
  '/admin/account-transactions',
  '/admin/home-banners',
  '/admin/special-zones',
  '/admin/brands',
  '/admin/categories',
  '/admin/products',
  '/admin/product-skus',
  '/admin/inventory-logs',
  '/admin/orders',
  '/admin/invoices',
  '/admin/discounts',
]);

export const STORE_DEFAULT_ROUTE = '/admin/sales-stats';
export const PLATFORM_DEFAULT_ROUTE = '/admin/users';

export const isPlatformUserFromContext = (context: CurrentStoreContext | null | undefined): boolean => {
  return Boolean(context?.is_platform_admin);
};

export const canAccessAdminRoute = (
  pathname: string,
  context: CurrentStoreContext | null | undefined,
): boolean => {
  if (!context || context.is_platform_admin) return true;
  return STORE_OPERATION_ROUTE_KEYS.has(pathname);
};

export const isPlatformUserFromStoredUser = (user: any): boolean => {
  if (!user) return false;
  if (user.is_superuser) return true;
  return Array.isArray(user.store_roles) && user.store_roles.some((role: any) => role?.role === 'platform_admin');
};

export const isStoreBackendUser = (user: any): boolean => {
  return Array.isArray(user?.store_roles) && user.store_roles.some((role: any) => role?.status === 'active');
};
