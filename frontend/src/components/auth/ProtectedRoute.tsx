import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { useAuth } from '@/hooks/useAuth'
import { getDefaultRoute } from '@/lib/rbac'

interface ProtectedRouteProps {
  requiredAccess?: 'CONTROL_TOWER' | 'ORG_ADMIN' | 'EMPLOYEE'
}

export function ProtectedRoute({ requiredAccess }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingScreen />
  }

  if (!user) {
    const loginPath = requiredAccess === 'CONTROL_TOWER' ? '/ct/login' : '/auth/login'
    return <Navigate to={loginPath} state={{ from: location }} replace />
  }

  if (requiredAccess === 'CONTROL_TOWER' && !user.has_control_tower_access) {
    return <Navigate to={getDefaultRoute(user)} replace />
  }

  if (requiredAccess === 'ORG_ADMIN' && !user.has_org_admin_access) {
    return <Navigate to={getDefaultRoute(user)} replace />
  }

  if (requiredAccess === 'EMPLOYEE' && !user.has_employee_access) {
    return <Navigate to={getDefaultRoute(user)} replace />
  }

  if (
    requiredAccess === 'EMPLOYEE' &&
    location.pathname !== '/me/onboarding' &&
    user.active_employee_status === 'INVITED'
  ) {
    return <Navigate to="/me/onboarding" replace />
  }

  if (
    requiredAccess === 'EMPLOYEE' &&
    location.pathname !== '/me/onboarding' &&
    user.active_employee_onboarding_status &&
    user.active_employee_onboarding_status !== 'COMPLETE'
  ) {
    return <Navigate to="/me/onboarding" replace />
  }

  return <Outlet />
}
