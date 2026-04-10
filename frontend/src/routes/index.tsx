import type { ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { CTLayout } from '@/components/layouts/CTLayout'
import { OrgLayout } from '@/components/layouts/OrgLayout'
import { EmployeeLayout } from '@/components/layouts/EmployeeLayout'
import { AppErrorBoundary } from '@/components/ui/AppErrorBoundary'
import { LoginPage } from '@/pages/auth/LoginPage'
import { ControlTowerLoginPage } from '@/pages/auth/ControlTowerLoginPage'
import { InviteAcceptPage } from '@/pages/auth/InviteAcceptPage'
import { RequestPasswordResetPage } from '@/pages/auth/RequestPasswordResetPage'
import { ControlTowerRequestPasswordResetPage } from '@/pages/auth/ControlTowerRequestPasswordResetPage'
import { ResetPasswordPage } from '@/pages/auth/ResetPasswordPage'
import { CTDashboardPage } from '@/pages/ct/DashboardPage'
import { OrganisationsPage } from '@/pages/ct/OrganisationsPage'
import { NewOrganisationPage } from '@/pages/ct/NewOrganisationPage'
import { FirstLicenceBatchPage } from '@/pages/ct/FirstLicenceBatchPage'
import { OrganisationDetailPage } from '@/pages/ct/OrganisationDetailPage'
import { OrgDashboardPage } from '@/pages/org/DashboardPage'
import { OrgSetupPage } from '@/pages/org/SetupPage'
import { OrgProfilePage } from '@/pages/org/ProfilePage'
import { PayrollPage } from '@/pages/org/PayrollPage'
import { PayrollRunDetailPage } from '@/pages/org/PayrollRunDetailPage'
import { JobPostingsPage } from '@/pages/org/JobPostingsPage'
import { ApplicationsPage } from '@/pages/org/ApplicationsPage'
import { CandidateDetailPage } from '@/pages/org/CandidateDetailPage'
import { GoalCyclesPage } from '@/pages/org/GoalCyclesPage'
import { AppraisalCyclesPage } from '@/pages/org/AppraisalCyclesPage'
import { ReportsPage } from '@/pages/org/ReportsPage'
import { OrgAuditPage } from '@/pages/org/AuditPage'
import { LocationsPage } from '@/pages/org/LocationsPage'
import { DepartmentsPage } from '@/pages/org/DepartmentsPage'
import { AttendanceImportsPage } from '@/pages/org/AttendanceImportsPage'
import { BiometricDevicesPage } from '@/pages/org/BiometricDevicesPage'
import { EmployeesPage } from '@/pages/org/EmployeesPage'
import { EmployeeDetailPage } from '@/pages/org/EmployeeDetailPage'
import { EmployeeDashboardPage } from '@/pages/employee/DashboardPage'
import { AttendancePage } from '@/pages/employee/AttendancePage'
import { OnboardingPage } from '@/pages/employee/OnboardingPage'
import { ProfilePage } from '@/pages/employee/ProfilePage'
import { EducationPage } from '@/pages/employee/EducationPage'
import { DocumentsPage } from '@/pages/employee/DocumentsPage'
import { LeavePage } from '@/pages/employee/LeavePage'
import { OnDutyPage } from '@/pages/employee/OnDutyPage'
import { ApprovalsPage } from '@/pages/employee/ApprovalsPage'
import { PayslipsPage } from '@/pages/employee/PayslipsPage'
import { PerformancePage } from '@/pages/employee/PerformancePage'
import { HolidaysPage } from '@/pages/org/HolidaysPage'
import { LeaveCyclesPage } from '@/pages/org/LeaveCyclesPage'
import { LeavePlansPage } from '@/pages/org/LeavePlansPage'
import { LeavePlanBuilderPage } from '@/pages/org/LeavePlanBuilderPage'
import { OnDutyPoliciesPage } from '@/pages/org/OnDutyPoliciesPage'
import { OnDutyPolicyBuilderPage } from '@/pages/org/OnDutyPolicyBuilderPage'
import { ApprovalWorkflowsPage } from '@/pages/org/ApprovalWorkflowsPage'
import { ApprovalWorkflowBuilderPage } from '@/pages/org/ApprovalWorkflowBuilderPage'
import { NoticesPage } from '@/pages/org/NoticesPage'
import { NoticeEditorPage } from '@/pages/org/NoticeEditorPage'
import { PayrollMastersPage } from '@/pages/ct/PayrollMastersPage'
import { CtOrgPayrollPage } from '@/pages/ct/CtOrgPayrollPage'

function withErrorBoundary(element: ReactNode) {
  return <AppErrorBoundary>{element}</AppErrorBoundary>
}

export const router = createBrowserRouter([
  // Public auth routes
  {
    path: '/auth/login',
    element: withErrorBoundary(<LoginPage />),
  },
  {
    path: '/ct/login',
    element: withErrorBoundary(<ControlTowerLoginPage />),
  },
  {
    path: '/auth/invite/:token',
    element: withErrorBoundary(<InviteAcceptPage />),
  },
  {
    path: '/auth/reset-password',
    element: withErrorBoundary(<RequestPasswordResetPage />),
  },
  {
    path: '/ct/reset-password',
    element: withErrorBoundary(<ControlTowerRequestPasswordResetPage />),
  },
  {
    path: '/auth/reset-password/:token',
    element: withErrorBoundary(<ResetPasswordPage />),
  },
  {
    path: '/ct/reset-password/:token',
    element: withErrorBoundary(<ResetPasswordPage />),
  },

  // Control Tower routes
  {
    element: withErrorBoundary(<ProtectedRoute requiredAccess="CONTROL_TOWER" />),
    children: [
      {
        element: withErrorBoundary(<CTLayout />),
        children: [
          { path: '/ct/dashboard', element: <CTDashboardPage /> },
          { path: '/ct/payroll', element: <PayrollMastersPage /> },
          { path: '/ct/organisations', element: <OrganisationsPage /> },
          { path: '/ct/organisations/new', element: <NewOrganisationPage /> },
          { path: '/ct/organisations/:id/first-licence-batch', element: <FirstLicenceBatchPage /> },
          { path: '/ct/organisations/:organisationId/leave-cycles', element: <LeaveCyclesPage /> },
          { path: '/ct/organisations/:organisationId/leave-plans', element: <LeavePlansPage /> },
          { path: '/ct/organisations/:organisationId/leave-plans/new', element: <LeavePlanBuilderPage /> },
          { path: '/ct/organisations/:organisationId/leave-plans/:id', element: <LeavePlanBuilderPage /> },
          { path: '/ct/organisations/:organisationId/on-duty-policies', element: <OnDutyPoliciesPage /> },
          { path: '/ct/organisations/:organisationId/on-duty-policies/new', element: <OnDutyPolicyBuilderPage /> },
          { path: '/ct/organisations/:organisationId/on-duty-policies/:id', element: <OnDutyPolicyBuilderPage /> },
          { path: '/ct/organisations/:organisationId/approval-workflows', element: <ApprovalWorkflowsPage /> },
          { path: '/ct/organisations/:organisationId/approval-workflows/new', element: <ApprovalWorkflowBuilderPage /> },
          { path: '/ct/organisations/:organisationId/approval-workflows/:id', element: <ApprovalWorkflowBuilderPage /> },
          { path: '/ct/organisations/:organisationId/notices', element: <NoticesPage /> },
          { path: '/ct/organisations/:organisationId/notices/new', element: <NoticeEditorPage /> },
          { path: '/ct/organisations/:organisationId/notices/:id', element: <NoticeEditorPage /> },
          { path: '/ct/organisations/:organisationId/audit', element: <OrgAuditPage /> },
          { path: '/ct/organisations/:organisationId/payroll', element: <CtOrgPayrollPage /> },
          { path: '/ct/organisations/:id', element: <OrganisationDetailPage /> },
        ],
      },
    ],
  },

  // Organisation Admin routes
  {
    element: withErrorBoundary(<ProtectedRoute requiredAccess="ORG_ADMIN" />),
    children: [
      {
        element: withErrorBoundary(<OrgLayout />),
        children: [
          { path: '/org/setup', element: <OrgSetupPage /> },
          { path: '/org/dashboard', element: <OrgDashboardPage /> },
          { path: '/org/profile', element: <OrgProfilePage /> },
          { path: '/org/attendance', element: <AttendanceImportsPage /> },
          { path: '/org/biometric-devices', element: <BiometricDevicesPage /> },
          { path: '/org/payroll', element: <PayrollPage /> },
          { path: '/org/payroll/runs/:id', element: <PayrollRunDetailPage /> },
          { path: '/org/recruitment/jobs', element: <JobPostingsPage /> },
          { path: '/org/recruitment/applications', element: <ApplicationsPage /> },
          { path: '/org/recruitment/candidates/:id', element: <CandidateDetailPage /> },
          { path: '/org/performance/goals', element: <GoalCyclesPage /> },
          { path: '/org/performance/appraisals', element: <AppraisalCyclesPage /> },
          { path: '/org/reports', element: <ReportsPage /> },
          { path: '/org/locations', element: <LocationsPage /> },
          { path: '/org/departments', element: <DepartmentsPage /> },
          { path: '/org/employees', element: <EmployeesPage /> },
          { path: '/org/employees/:id', element: <EmployeeDetailPage /> },
          { path: '/org/holidays', element: <HolidaysPage /> },
          { path: '/org/leave-cycles', element: <LeaveCyclesPage /> },
          { path: '/org/leave-plans', element: <LeavePlansPage /> },
          { path: '/org/leave-plans/new', element: <LeavePlanBuilderPage /> },
          { path: '/org/leave-plans/:id', element: <LeavePlanBuilderPage /> },
          { path: '/org/on-duty-policies', element: <OnDutyPoliciesPage /> },
          { path: '/org/on-duty-policies/new', element: <OnDutyPolicyBuilderPage /> },
          { path: '/org/on-duty-policies/:id', element: <OnDutyPolicyBuilderPage /> },
          { path: '/org/approval-workflows', element: <ApprovalWorkflowsPage /> },
          { path: '/org/approval-workflows/new', element: <ApprovalWorkflowBuilderPage /> },
          { path: '/org/approval-workflows/:id', element: <ApprovalWorkflowBuilderPage /> },
          { path: '/org/notices', element: <NoticesPage /> },
          { path: '/org/notices/new', element: <NoticeEditorPage /> },
          { path: '/org/notices/:id', element: <NoticeEditorPage /> },
          { path: '/org/audit', element: <OrgAuditPage /> },
        ],
      },
    ],
  },

  // Employee routes
  {
    element: withErrorBoundary(<ProtectedRoute requiredAccess="EMPLOYEE" />),
    children: [
      {
        element: withErrorBoundary(<EmployeeLayout />),
        children: [
          { path: '/me/onboarding', element: <OnboardingPage /> },
          { path: '/me/dashboard', element: <EmployeeDashboardPage /> },
          { path: '/me/attendance', element: <AttendancePage /> },
          { path: '/me/profile', element: <ProfilePage /> },
          { path: '/me/education', element: <EducationPage /> },
          { path: '/me/documents', element: <DocumentsPage /> },
          { path: '/me/leave', element: <LeavePage /> },
          { path: '/me/od', element: <OnDutyPage /> },
          { path: '/me/payslips', element: <PayslipsPage /> },
          { path: '/me/performance', element: <PerformancePage /> },
          { path: '/me/approvals', element: <ApprovalsPage /> },
        ],
      },
    ],
  },

  // Root redirect
  { path: '/', element: withErrorBoundary(<Navigate to="/auth/login" replace />) },
  { path: '*', element: withErrorBoundary(<Navigate to="/auth/login" replace />) },
])
