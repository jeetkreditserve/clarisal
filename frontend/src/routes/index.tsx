import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { CTLayout } from '@/components/layouts/CTLayout'
import { OrgLayout } from '@/components/layouts/OrgLayout'
import { EmployeeLayout } from '@/components/layouts/EmployeeLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { ControlTowerLoginPage } from '@/pages/auth/ControlTowerLoginPage'
import { InviteAcceptPage } from '@/pages/auth/InviteAcceptPage'
import { RequestPasswordResetPage } from '@/pages/auth/RequestPasswordResetPage'
import { ControlTowerRequestPasswordResetPage } from '@/pages/auth/ControlTowerRequestPasswordResetPage'
import { ResetPasswordPage } from '@/pages/auth/ResetPasswordPage'
import { CTDashboardPage } from '@/pages/ct/DashboardPage'
import { OrganisationsPage } from '@/pages/ct/OrganisationsPage'
import { NewOrganisationPage } from '@/pages/ct/NewOrganisationPage'
import { OrganisationDetailPage } from '@/pages/ct/OrganisationDetailPage'
import { OrgDashboardPage } from '@/pages/org/DashboardPage'
import { OrgProfilePage } from '@/pages/org/ProfilePage'
import { LocationsPage } from '@/pages/org/LocationsPage'
import { DepartmentsPage } from '@/pages/org/DepartmentsPage'
import { EmployeesPage } from '@/pages/org/EmployeesPage'
import { EmployeeDetailPage } from '@/pages/org/EmployeeDetailPage'
import { EmployeeDashboardPage } from '@/pages/employee/DashboardPage'
import { OnboardingPage } from '@/pages/employee/OnboardingPage'
import { ProfilePage } from '@/pages/employee/ProfilePage'
import { EducationPage } from '@/pages/employee/EducationPage'
import { DocumentsPage } from '@/pages/employee/DocumentsPage'
import { LeavePage } from '@/pages/employee/LeavePage'
import { OnDutyPage } from '@/pages/employee/OnDutyPage'
import { ApprovalsPage } from '@/pages/employee/ApprovalsPage'
import { HolidaysPage } from '@/pages/org/HolidaysPage'
import { LeaveCyclesPage } from '@/pages/org/LeaveCyclesPage'
import { LeavePlansPage } from '@/pages/org/LeavePlansPage'
import { OnDutyPoliciesPage } from '@/pages/org/OnDutyPoliciesPage'
import { ApprovalWorkflowsPage } from '@/pages/org/ApprovalWorkflowsPage'
import { NoticesPage } from '@/pages/org/NoticesPage'

export const router = createBrowserRouter([
  // Public auth routes
  {
    path: '/auth/login',
    element: <LoginPage />,
  },
  {
    path: '/ct/login',
    element: <ControlTowerLoginPage />,
  },
  {
    path: '/auth/invite/:token',
    element: <InviteAcceptPage />,
  },
  {
    path: '/auth/reset-password',
    element: <RequestPasswordResetPage />,
  },
  {
    path: '/ct/reset-password',
    element: <ControlTowerRequestPasswordResetPage />,
  },
  {
    path: '/auth/reset-password/:token',
    element: <ResetPasswordPage />,
  },
  {
    path: '/ct/reset-password/:token',
    element: <ResetPasswordPage />,
  },

  // Control Tower routes
  {
    element: <ProtectedRoute requiredAccess="CONTROL_TOWER" />,
    children: [
      {
        element: <CTLayout />,
        children: [
          { path: '/ct/dashboard', element: <CTDashboardPage /> },
          { path: '/ct/organisations', element: <OrganisationsPage /> },
          { path: '/ct/organisations/new', element: <NewOrganisationPage /> },
          { path: '/ct/organisations/:id', element: <OrganisationDetailPage /> },
        ],
      },
    ],
  },

  // Organisation Admin routes
  {
    element: <ProtectedRoute requiredAccess="ORG_ADMIN" />,
    children: [
      {
        element: <OrgLayout />,
        children: [
          { path: '/org/dashboard', element: <OrgDashboardPage /> },
          { path: '/org/profile', element: <OrgProfilePage /> },
          { path: '/org/locations', element: <LocationsPage /> },
          { path: '/org/departments', element: <DepartmentsPage /> },
          { path: '/org/employees', element: <EmployeesPage /> },
          { path: '/org/employees/:id', element: <EmployeeDetailPage /> },
          { path: '/org/holidays', element: <HolidaysPage /> },
          { path: '/org/leave-cycles', element: <LeaveCyclesPage /> },
          { path: '/org/leave-plans', element: <LeavePlansPage /> },
          { path: '/org/on-duty-policies', element: <OnDutyPoliciesPage /> },
          { path: '/org/approval-workflows', element: <ApprovalWorkflowsPage /> },
          { path: '/org/notices', element: <NoticesPage /> },
        ],
      },
    ],
  },

  // Employee routes
  {
    element: <ProtectedRoute requiredAccess="EMPLOYEE" />,
    children: [
      {
        element: <EmployeeLayout />,
        children: [
          { path: '/me/onboarding', element: <OnboardingPage /> },
          { path: '/me/dashboard', element: <EmployeeDashboardPage /> },
          { path: '/me/profile', element: <ProfilePage /> },
          { path: '/me/education', element: <EducationPage /> },
          { path: '/me/documents', element: <DocumentsPage /> },
          { path: '/me/leave', element: <LeavePage /> },
          { path: '/me/od', element: <OnDutyPage /> },
          { path: '/me/approvals', element: <ApprovalsPage /> },
        ],
      },
    ],
  },

  // Root redirect
  { path: '/', element: <Navigate to="/auth/login" replace /> },
  { path: '*', element: <Navigate to="/auth/login" replace /> },
])
