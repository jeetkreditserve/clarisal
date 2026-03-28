import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { CTLayout } from '@/components/layouts/CTLayout'
import { OrgLayout } from '@/components/layouts/OrgLayout'
import { EmployeeLayout } from '@/components/layouts/EmployeeLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { InviteAcceptPage } from '@/pages/auth/InviteAcceptPage'
import { RequestPasswordResetPage } from '@/pages/auth/RequestPasswordResetPage'
import { CTDashboardPage } from '@/pages/ct/DashboardPage'
import { OrgDashboardPage } from '@/pages/org/DashboardPage'
import { EmployeeDashboardPage } from '@/pages/employee/DashboardPage'

export const router = createBrowserRouter([
  // Public auth routes
  {
    path: '/auth/login',
    element: <LoginPage />,
  },
  {
    path: '/auth/invite/:token',
    element: <InviteAcceptPage />,
  },
  {
    path: '/auth/reset-password',
    element: <RequestPasswordResetPage />,
  },

  // Control Tower routes
  {
    element: <ProtectedRoute allowedRoles={['CONTROL_TOWER']} />,
    children: [
      {
        element: <CTLayout />,
        children: [
          { path: '/ct/dashboard', element: <CTDashboardPage /> },
          // Phase 2: CT organisation routes will be added here
        ],
      },
    ],
  },

  // Organisation Admin routes
  {
    element: <ProtectedRoute allowedRoles={['ORG_ADMIN']} />,
    children: [
      {
        element: <OrgLayout />,
        children: [
          { path: '/org/dashboard', element: <OrgDashboardPage /> },
          // Phase 3: Locations, departments, employees routes will be added here
        ],
      },
    ],
  },

  // Employee routes
  {
    element: <ProtectedRoute allowedRoles={['EMPLOYEE']} />,
    children: [
      {
        element: <EmployeeLayout />,
        children: [
          { path: '/me/dashboard', element: <EmployeeDashboardPage /> },
          // Phase 4: Profile, education, documents routes will be added here
        ],
      },
    ],
  },

  // Root redirect
  { path: '/', element: <Navigate to="/auth/login" replace /> },
  { path: '*', element: <Navigate to="/auth/login" replace /> },
])
