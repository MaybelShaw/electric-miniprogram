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
    if (allowedRoles.includes('support') && !allowedRoles.includes('admin')) {
      return <Navigate to="/support/login" replace />;
    }
    return <Navigate to="/admin/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    // Redirect to their default page based on role
    if (user.role === 'support') {
      return <Navigate to="/support" replace />;
    }
    return <Navigate to="/admin" replace />;
  }

  return <>{children}</>;
};

export default RoleGuard;
