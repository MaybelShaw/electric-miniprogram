import React from 'react';
import { Navigate } from 'react-router-dom';
import { getUser } from '@/utils/auth';

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: string[];
}

const RoleGuard: React.FC<RoleGuardProps> = ({ children, allowedRoles }) => {
  const user = getUser();

  if (!user) {
    return <Navigate to={allowedRoles.includes('support') ? "/support/login" : "/admin/login"} replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={allowedRoles.includes('support') ? "/support/login" : "/admin/login"} replace />;
  }

  return <>{children}</>;
};

export default RoleGuard;
