import type { CurrentStoreContext } from '@/services/types';

export const ROUTE_PERMISSION_MAP: Record<string, string> = {
  '/admin/sales-stats': 'dashboard.view',
  '/admin/account-statements': 'finance.view',
  '/admin/account-transactions': 'finance.view',
  '/admin/home-banners': 'store_content.manage',
  '/admin/special-zones': 'store_content.manage',
  '/admin/brands': 'catalog.manage',
  '/admin/categories': 'catalog.manage',
  '/admin/products': 'catalog.manage',
  '/admin/product-skus': 'catalog.manage',
  '/admin/customer-groups': 'customer_groups.manage',
  '/admin/inventory-logs': 'catalog.manage',
  '/admin/support-chats': 'dashboard.view',
  '/admin/support-templates': 'dashboard.view',
  '/admin/feedback-tickets': 'dashboard.view',
  '/admin/orders': 'orders.view',
  '/admin/invoices': 'invoices.manage',
  '/admin/store-members': 'store_members.manage',
};

export const STORE_DEFAULT_ROUTE = '/admin/sales-stats';
export const PLATFORM_DEFAULT_ROUTE = '/admin/users';

export const PARTNER_DISPLAY_ONLY_ROUTE = '/admin/products';

export const PARTNER_DISPLAY_ONLY_BLOCKED_ROUTES = new Set([
  '/admin/sales-stats',
  '/admin/credit-accounts',
  '/admin/account-statements',
  '/admin/account-transactions',
  '/admin/inventory-logs',
  '/admin/orders',
  '/admin/invoices',
  '/admin/discounts',
  '/admin/profit-sharing',
]);

export const getStoreDefaultRoute = (storeType?: string): string => (
  storeType === 'partner' ? PARTNER_DISPLAY_ONLY_ROUTE : STORE_DEFAULT_ROUTE
);

export const canAccessAdminRoute = (
  pathname: string,
  context: CurrentStoreContext | null | undefined,
): boolean => {
  if (!context) return false;
  if (context.is_platform_admin) return true;
  if (context.default_store?.store_type === 'partner' && PARTNER_DISPLAY_ONLY_BLOCKED_ROUTES.has(pathname)) {
    return false;
  }
  const requiredPermission = ROUTE_PERMISSION_MAP[pathname];
  if (!requiredPermission) return false;
  return context.memberships.some((membership) =>
    membership.status === 'active' && Array.isArray(membership.permissions) && membership.permissions.includes(requiredPermission),
  );
};

export const isPlatformUserFromStoredUser = (user: any): boolean => {
  if (!user) return false;
  if (user.is_superuser) return true;
  return Array.isArray(user.store_roles) && user.store_roles.some((role: any) =>
    role?.status === 'active' && (role?.role === 'platform_admin' || (role?.role === 'store_admin' && role?.store_is_main)),
  );
};

export const isStoreBackendUser = (user: any): boolean => {
  return Array.isArray(user?.store_roles) && user.store_roles.some((role: any) => role?.status === 'active');
};
