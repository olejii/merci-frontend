import { Navigate, Outlet } from 'react-router-dom';

import { useAuthStore } from 'src/stores';
import type { UserRole } from 'src/types';

interface ProtectedRouteProps {
  allowedRoles: UserRole[];
}

function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={user.role === 'admin' ? '/admin' : '/waiter'} replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
