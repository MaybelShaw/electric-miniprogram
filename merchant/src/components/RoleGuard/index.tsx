import React from 'react';
import { Navigate } from 'react-router-dom';
import { getUser } from '@/utils/auth';
import { isStoreBackendUser } from '@/utils/permissions';

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: string[];
}

const RoleGuard: React.FC<RoleGuardProps> = ({ children, allowedRoles }) => {
  const user = getUser();
  const loginPath = allowedRoles.includes('admin') ? "/admin/login" : "/support/login";

  if (!user) {
    return <Navigate to={loginPath} replace />;
  }

  const hasStoreBackendAccess = allowedRoles.includes('admin') && isStoreBackendUser(user);

  if (!allowedRoles.includes(user.role) && !hasStoreBackendAccess) {
    return <Navigate to={loginPath} replace />;
  }

  return <>{children}</>;
};

export default RoleGuard;
