import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { UserRole } from '@/types/auth'
import { useAuth } from '@/hooks/useAuth'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Wrong role — send to their correct dashboard
    const roleRoutes: Record<UserRole, string> = {
      CONTROL_TOWER: '/ct/dashboard',
      ORG_ADMIN: '/org/dashboard',
      EMPLOYEE: '/me/dashboard',
    }
    return <Navigate to={roleRoutes[user.role]} replace />
  }

  return <Outlet />
}
