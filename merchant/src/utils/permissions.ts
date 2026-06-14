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
  '/admin/search-logs': 'catalog.manage',
  '/admin/inventory-logs': 'catalog.manage',
  '/admin/feedback-tickets': 'dashboard.view',
  '/admin/orders': 'orders.view',
  '/admin/invoices': 'invoices.manage',
  '/admin/store-members': 'store_members.manage',
};

export const STORE_OPERATION_ROUTE_KEYS = new Set(Object.keys(ROUTE_PERMISSION_MAP));

export const STORE_DEFAULT_ROUTE = '/admin/sales-stats';
export const PLATFORM_DEFAULT_ROUTE = '/admin/users';

export const isPlatformUserFromContext = (context: CurrentStoreContext | null | undefined): boolean => {
  return Boolean(context?.is_platform_admin);
};

export const canAccessAdminRoute = (
  pathname: string,
  context: CurrentStoreContext | null | undefined,
): boolean => {
  if (!context) return false;
  if (context.is_platform_admin) return true;
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
    role?.role === 'platform_admin' && role?.status === 'active',
  );
};

export const isStoreBackendUser = (user: any): boolean => {
  return Array.isArray(user?.store_roles) && user.store_roles.some((role: any) => role?.status === 'active');
};

export const hasStoredPermission = (user: any, permission: string): boolean => {
  if (isPlatformUserFromStoredUser(user)) return true;
  return Array.isArray(user?.store_roles) && user.store_roles.some((role: any) =>
    role?.status === 'active' && Array.isArray(role?.permissions) && role.permissions.includes(permission),
  );
};
