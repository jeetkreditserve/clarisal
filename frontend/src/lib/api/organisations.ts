import api from '@/lib/api'
import type { ImpersonationSession } from '@/types/auth'
import type {
  CtOrganisationAnalytics,
  CtDashboardStats,
  LicenceBatch,
  OrganisationFeatureFlag,
  OrganisationNote,
  OrgAdmin,
  OrganisationEntityType,
  OrganisationAddress,
  OrganisationDetail,
  OrganisationListItem,
  PaginatedResponse,
  TenantDataExportBatch,
  TenantDataExportDownloadResponse,
  TenantDataExportType,
} from '@/types/organisation'
import type {
  CtOrganisationAttendanceSupportSummary,
  ApprovalWorkflowConfig,
  CtOrganisationOnboardingSupportSummary,
  CtOrganisationApprovalSupportSummary,
  CtOrganisationPayrollSupportSummary,
  CtEmployeeDetail,
  CtEmployeeListItem,
  PayrollTaxSlabSet,
  Department,
  HolidayCalendar,
  LeaveCycle,
  LeavePlan,
  Location,
  NoticeItem,
  OnDutyPolicy,
  CtPayrollStatutoryMastersResponse,
  CtOnboardingChecklist,
  OnboardingProgress,
  OnboardingProgressStep,
} from '@/types/hr'

export interface OrganisationAddressInput {
  address_type: 'REGISTERED' | 'BILLING' | 'HEADQUARTERS' | 'WAREHOUSE' | 'CUSTOM'
  label?: string
  line1: string
  line2?: string
  city: string
  state: string
  state_code?: string
  country?: string
  country_code?: string
  pincode: string
  gstin?: string | null
}

export async function fetchCtStats(): Promise<CtDashboardStats> {
  const { data } = await api.get('/ct/dashboard/')
  return data
}

export async function fetchOrganisations(params?: {
  search?: string
  status?: string
  page?: number
}): Promise<PaginatedResponse<OrganisationListItem>> {
  const { data } = await api.get('/ct/organisations/', { params })
  return data
}

export async function fetchOrganisation(id: string): Promise<OrganisationDetail> {
  const { data } = await api.get(`/ct/organisations/${id}/`)
  return data
}

export async function updateCtOrganisationFeatureFlags(
  id: string,
  payload: Array<{ feature_code: string; is_enabled: boolean }>
): Promise<OrganisationFeatureFlag[]> {
  const { data } = await api.patch(`/ct/organisations/${id}/feature-flags/`, payload)
  return data
}

export async function startCtImpersonation(
  id: string,
  payload: {
    reason: string
    target_org_admin_id?: string | null
  }
): Promise<ImpersonationSession> {
  const { data } = await api.post(`/ct/organisations/${id}/act-as/`, payload)
  return {
    session_id: data.id,
    organisation_id: data.organisation_id,
    organisation_name: data.organisation_name,
    reason: data.reason,
    started_at: data.started_at,
    refreshed_at: data.refreshed_at,
    is_active: data.is_active,
    return_path: `/ct/organisations/${data.organisation_id}`,
    target_org_admin: data.target_org_admin,
  }
}

export async function refreshCtImpersonation(): Promise<ImpersonationSession> {
  const { data } = await api.post('/ct/act-as/refresh/', {})
  return {
    session_id: data.id,
    organisation_id: data.organisation_id,
    organisation_name: data.organisation_name,
    reason: data.reason,
    started_at: data.started_at,
    refreshed_at: data.refreshed_at,
    is_active: data.is_active,
    return_path: `/ct/organisations/${data.organisation_id}`,
    target_org_admin: data.target_org_admin,
  }
}

export async function stopCtImpersonation(): Promise<ImpersonationSession> {
  const { data } = await api.post('/ct/act-as/stop/', {})
  return {
    session_id: data.id,
    organisation_id: data.organisation_id,
    organisation_name: data.organisation_name,
    reason: data.reason,
    started_at: data.started_at,
    refreshed_at: data.refreshed_at,
    is_active: data.is_active,
    return_path: `/ct/organisations/${data.organisation_id}`,
    target_org_admin: data.target_org_admin,
  }
}

export async function createOrganisation(payload: {
  name: string
  pan_number: string
  country_code?: string
  currency?: string
  entity_type: OrganisationEntityType
  billing_same_as_registered?: boolean
  primary_admin: {
    first_name: string
    last_name: string
    email: string
    phone?: string
  }
  addresses: OrganisationAddressInput[]
}): Promise<OrganisationDetail> {
  const { data } = await api.post('/ct/organisations/', payload)
  return data
}

export async function updateOrganisation(id: string, payload: {
  name?: string
  pan_number?: string
  tan_number?: string
  phone?: string
  email?: string
  country_code?: string
  currency?: string
  entity_type?: OrganisationEntityType
  logo_url?: string
  esi_branch_code?: string
  primary_admin?: {
    first_name: string
    last_name: string
    email: string
    phone?: string
  }
}): Promise<OrganisationDetail> {
  const { data } = await api.patch(`/ct/organisations/${id}/`, payload)
  return data
}

export async function updateCtBootstrapAdmin(
  id: string,
  payload: {
    first_name: string
    last_name: string
    email: string
    phone?: string
  }
): Promise<OrganisationDetail> {
  const { data } = await api.patch(`/ct/organisations/${id}/`, { primary_admin: payload })
  return data
}

export async function createOrganisationAddress(id: string, payload: OrganisationAddressInput): Promise<OrganisationAddress> {
  const { data } = await api.post(`/ct/organisations/${id}/addresses/`, payload)
  return data
}

export async function updateOrganisationAddress(
  id: string,
  addressId: string,
  payload: Partial<OrganisationAddressInput>
): Promise<OrganisationAddress> {
  const { data } = await api.patch(`/ct/organisations/${id}/addresses/${addressId}/`, payload)
  return data
}

export async function deactivateOrganisationAddress(id: string, addressId: string): Promise<OrganisationAddress> {
  const { data } = await api.delete(`/ct/organisations/${id}/addresses/${addressId}/`)
  return data
}

export async function markOrganisationPaid(id: string, note?: string): Promise<OrganisationDetail> {
  const { data } = await api.post(`/ct/organisations/${id}/activate/`, { note: note ?? '' })
  return data
}

export async function suspendOrganisation(id: string, note?: string): Promise<OrganisationDetail> {
  const { data } = await api.post(`/ct/organisations/${id}/suspend/`, { note: note ?? '' })
  return data
}

export async function restoreOrganisation(id: string, note?: string): Promise<OrganisationDetail> {
  const { data } = await api.post(`/ct/organisations/${id}/restore/`, { note: note ?? '' })
  return data
}

export async function fetchOrgLicences(id: string): Promise<{
  total_count: number
  used_count: number
  available_count: number
  overage_count: number
  utilisation_percent: number
}> {
  const { data } = await api.get(`/ct/organisations/${id}/licences/`)
  return data
}

export async function fetchLicenceBatches(id: string): Promise<LicenceBatch[]> {
  const { data } = await api.get(`/ct/organisations/${id}/licence-batches/`)
  return data
}

export async function createLicenceBatch(
  id: string,
  payload: {
    quantity: number
    price_per_licence_per_month: string
    start_date: string
    end_date: string
    note?: string
  }
): Promise<LicenceBatch> {
  const { data } = await api.post(`/ct/organisations/${id}/licence-batches/`, payload)
  return data
}

export async function updateLicenceBatch(
  id: string,
  batchId: string,
  payload: Partial<{
    quantity: number
    price_per_licence_per_month: string
    start_date: string
    end_date: string
    note: string
  }>
): Promise<LicenceBatch> {
  const { data } = await api.patch(`/ct/organisations/${id}/licence-batches/${batchId}/`, payload)
  return data
}

export async function markLicenceBatchPaid(
  id: string,
  batchId: string,
  payload?: { paid_at?: string }
): Promise<LicenceBatch> {
  const { data } = await api.post(`/ct/organisations/${id}/licence-batches/${batchId}/mark-paid/`, payload ?? {})
  return data
}

export async function extendLicenceBatchExpiry(
  id: string,
  batchId: string,
  payload: {
    new_end_date: string
    reason?: string
  },
): Promise<LicenceBatch> {
  const { data } = await api.post(`/ct/organisations/${id}/licence-batches/${batchId}/extend-expiry/`, payload)
  return data
}

export async function fetchCtTenantDataExports(id: string): Promise<TenantDataExportBatch[]> {
  const { data } = await api.get(`/ct/organisations/${id}/exports/`)
  return data
}

export async function createCtTenantDataExport(
  id: string,
  payload: { export_type: TenantDataExportType },
): Promise<TenantDataExportBatch> {
  const { data } = await api.post(`/ct/organisations/${id}/exports/`, payload)
  return data
}

export async function fetchCtTenantDataExportDownloadUrl(
  id: string,
  exportId: string,
): Promise<TenantDataExportDownloadResponse> {
  const { data } = await api.post(`/ct/organisations/${id}/exports/${exportId}/download-url/`)
  return data
}

export async function fetchOrgAdmins(id: string): Promise<OrgAdmin[]> {
  const { data } = await api.get(`/ct/organisations/${id}/admins/`)
  return data
}

export async function fetchCtPayrollTaxSlabSets(): Promise<PayrollTaxSlabSet[]> {
  const { data } = await api.get('/ct/payroll/tax-slab-sets/')
  return data
}

export async function createCtPayrollTaxSlabSet(payload: Record<string, unknown>): Promise<PayrollTaxSlabSet> {
  const { data } = await api.post('/ct/payroll/tax-slab-sets/', payload)
  return data
}

export async function updateCtPayrollTaxSlabSet(id: string, payload: Record<string, unknown>): Promise<PayrollTaxSlabSet> {
  const { data } = await api.patch(`/ct/payroll/tax-slab-sets/${id}/`, payload)
  return data
}

export async function deleteCtPayrollTaxSlabSet(id: string): Promise<void> {
  await api.delete(`/ct/payroll/tax-slab-sets/${id}/`)
}

export async function fetchCtOrgEmployees(
  id: string,
  params?: { status?: string; search?: string; page?: number }
): Promise<PaginatedResponse<CtEmployeeListItem>> {
  const { data } = await api.get(`/ct/organisations/${id}/employees/`, { params })
  return data
}

export async function fetchCtOrgEmployeeDetail(id: string, employeeId: string): Promise<CtEmployeeDetail> {
  const { data } = await api.get(`/ct/organisations/${id}/employees/${employeeId}/`)
  return data
}

export async function fetchCtOrgPayrollSummary(id: string): Promise<CtOrganisationPayrollSupportSummary> {
  const { data } = await api.get(`/ct/organisations/${id}/payroll/`)
  return data
}

export async function fetchCtPayrollStatutoryMasters(stateCode?: string): Promise<CtPayrollStatutoryMastersResponse> {
  const params = stateCode ? { state_code: stateCode } : undefined
  const { data } = await api.get('/ct/payroll/statutory-masters/', { params })
  return data
}

export async function fetchCtOrgOnboardingChecklist(id: string): Promise<CtOnboardingChecklist> {
  const { data } = await api.get(`/ct/organisations/${id}/onboarding-checklist/`)
  return data
}

export async function fetchCtOrgAttendanceSummary(id: string): Promise<CtOrganisationAttendanceSupportSummary> {
  const { data } = await api.get(`/ct/organisations/${id}/attendance/`)
  return data
}

export async function fetchCtOrgOnboardingSummary(id: string): Promise<CtOrganisationOnboardingSupportSummary> {
  const { data } = await api.get(`/ct/organisations/${id}/onboarding-support/`)
  return data
}

export async function fetchCtOrgApprovalSummary(id: string): Promise<CtOrganisationApprovalSupportSummary> {
  const { data } = await api.get(`/ct/organisations/${id}/approvals/`)
  return data
}

export async function fetchCtHolidayCalendars(id: string): Promise<HolidayCalendar[]> {
  const { data } = await api.get(`/ct/organisations/${id}/holiday-calendars/`)
  return data
}

export async function createCtHolidayCalendar(id: string, payload: Record<string, unknown>): Promise<HolidayCalendar> {
  const { data } = await api.post(`/ct/organisations/${id}/holiday-calendars/`, payload)
  return data
}

export async function updateCtHolidayCalendar(
  id: string,
  calendarId: string,
  payload: Record<string, unknown>
): Promise<HolidayCalendar> {
  const { data } = await api.patch(`/ct/organisations/${id}/holiday-calendars/${calendarId}/`, payload)
  return data
}

export async function publishCtHolidayCalendar(id: string, calendarId: string): Promise<HolidayCalendar> {
  const { data } = await api.post(`/ct/organisations/${id}/holiday-calendars/${calendarId}/publish/`)
  return data
}

export async function fetchCtOrgConfiguration(id: string): Promise<{
  locations: Location[]
  departments: Department[]
  leave_cycles: LeaveCycle[]
  leave_plans: LeavePlan[]
  on_duty_policies: OnDutyPolicy[]
  approval_workflows: ApprovalWorkflowConfig[]
  notices: NoticeItem[]
}> {
  const { data } = await api.get(`/ct/organisations/${id}/configuration/`)
  return data
}

export async function fetchCtOrgNotes(id: string): Promise<OrganisationNote[]> {
  const { data } = await api.get(`/ct/organisations/${id}/notes/`)
  return data
}

export async function createCtOrgNote(id: string, body: string): Promise<OrganisationNote> {
  const { data } = await api.post(`/ct/organisations/${id}/notes/`, { body })
  return data
}

export async function inviteOrgAdmin(id: string, payload: {
  email: string
  first_name: string
  last_name: string
}): Promise<{ user_id: string; email: string; status: string; expires_at: string }> {
  const { data } = await api.post(`/ct/organisations/${id}/admins/invite/`, payload)
  return data
}

export async function resendOrgAdminInvite(orgId: string, userId: string): Promise<void> {
  await api.post(`/ct/organisations/${orgId}/admins/${userId}/resend-invite/`)
}

export async function deactivateCtOrgAdmin(orgId: string, userId: string): Promise<OrgAdmin> {
  const { data } = await api.post(`/ct/organisations/${orgId}/admins/${userId}/deactivate/`)
  return data
}

export async function reactivateCtOrgAdmin(orgId: string, userId: string): Promise<OrgAdmin> {
  const { data } = await api.post(`/ct/organisations/${orgId}/admins/${userId}/reactivate/`)
  return data
}

export async function revokePendingCtOrgAdmin(orgId: string, userId: string): Promise<OrgAdmin> {
  const { data } = await api.post(`/ct/organisations/${orgId}/admins/${userId}/revoke-pending/`)
  return data
}

export async function createCtLocation(
  id: string,
  payload: {
    name: string
    organisation_address_id: string
    is_remote?: boolean
  },
): Promise<Location> {
  const { data } = await api.post(`/ct/organisations/${id}/locations/`, payload)
  return data
}

export async function updateCtLocation(
  id: string,
  locationId: string,
  payload: Partial<{
    name: string
    organisation_address_id: string
    is_remote: boolean
  }>,
): Promise<Location> {
  const { data } = await api.patch(`/ct/organisations/${id}/locations/${locationId}/`, payload)
  return data
}

export async function deactivateCtLocation(id: string, locationId: string): Promise<Location> {
  const { data } = await api.post(`/ct/organisations/${id}/locations/${locationId}/deactivate/`)
  return data
}

export async function createCtDepartment(
  id: string,
  payload: {
    name: string
    description?: string
    parent_department_id?: string | null
  },
): Promise<Department> {
  const { data } = await api.post(`/ct/organisations/${id}/departments/`, payload)
  return data
}

export async function updateCtDepartment(
  id: string,
  departmentId: string,
  payload: Partial<{ name: string; description: string; parent_department_id: string | null }>,
): Promise<Department> {
  const { data } = await api.patch(`/ct/organisations/${id}/departments/${departmentId}/`, payload)
  return data
}

export async function deactivateCtDepartment(id: string, departmentId: string): Promise<Department> {
  const { data } = await api.post(`/ct/organisations/${id}/departments/${departmentId}/deactivate/`)
  return data
}

export async function createCtLeaveCycle(id: string, payload: Record<string, unknown>): Promise<LeaveCycle> {
  const { data } = await api.post(`/ct/organisations/${id}/leave-cycles/`, payload)
  return data
}

export async function updateCtLeaveCycle(id: string, cycleId: string, payload: Record<string, unknown>): Promise<LeaveCycle> {
  const { data } = await api.patch(`/ct/organisations/${id}/leave-cycles/${cycleId}/`, payload)
  return data
}

export async function createCtLeavePlan(id: string, payload: Record<string, unknown>): Promise<LeavePlan> {
  const { data } = await api.post(`/ct/organisations/${id}/leave-plans/`, payload)
  return data
}

export async function updateCtLeavePlan(id: string, planId: string, payload: Record<string, unknown>): Promise<LeavePlan> {
  const { data } = await api.patch(`/ct/organisations/${id}/leave-plans/${planId}/`, payload)
  return data
}

export async function createCtOnDutyPolicy(id: string, payload: Record<string, unknown>): Promise<OnDutyPolicy> {
  const { data } = await api.post(`/ct/organisations/${id}/on-duty-policies/`, payload)
  return data
}

export async function updateCtOnDutyPolicy(id: string, policyId: string, payload: Record<string, unknown>): Promise<OnDutyPolicy> {
  const { data } = await api.patch(`/ct/organisations/${id}/on-duty-policies/${policyId}/`, payload)
  return data
}

export async function createCtApprovalWorkflow(id: string, payload: Record<string, unknown>): Promise<ApprovalWorkflowConfig> {
  const { data } = await api.post(`/ct/organisations/${id}/approval-workflows/`, payload)
  return data
}

export async function updateCtApprovalWorkflow(
  id: string,
  workflowId: string,
  payload: Record<string, unknown>,
): Promise<ApprovalWorkflowConfig> {
  const { data } = await api.patch(`/ct/organisations/${id}/approval-workflows/${workflowId}/`, payload)
  return data
}

export async function createCtNotice(id: string, payload: Record<string, unknown>): Promise<NoticeItem> {
  const { data } = await api.post(`/ct/organisations/${id}/notices/`, payload)
  return data
}

export async function updateCtNotice(id: string, noticeId: string, payload: Record<string, unknown>): Promise<NoticeItem> {
  const { data } = await api.patch(`/ct/organisations/${id}/notices/${noticeId}/`, payload)
  return data
}

export async function publishCtNotice(id: string, noticeId: string): Promise<NoticeItem> {
  const { data } = await api.post(`/ct/organisations/${id}/notices/${noticeId}/publish/`)
  return data
}

export async function fetchCtOrgOnboardingProgress(id: string): Promise<OnboardingProgress> {
  const { data } = await api.get(`/ct/organisations/${id}/onboarding/`)
  return data
}

export async function syncCtOrgOnboardingProgress(id: string): Promise<OnboardingProgress> {
  const { data } = await api.post(`/ct/organisations/${id}/onboarding/`)
  return data
}

export async function seedCtOrgMasters(id: string): Promise<{
  seeded: {
    payroll_components: {
      created_count: number
      existing_count: number
      total_count: number
      codes: string[]
    }
    document_types: {
      created_count: number
      existing_count: number
      total_count: number
    }
  }
}> {
  const { data } = await api.post(`/ct/organisations/${id}/seed-masters/`)
  return data
}

export async function postCtOrgOnboardingStepAction(
  id: string,
  step: string,
  action: 'complete' | 'reset',
  payload?: { reason?: string },
): Promise<OnboardingProgressStep> {
  const { data } = await api.post(`/ct/organisations/${id}/onboarding/${step}/${action}/`, payload ?? {})
  return data
}

export async function fetchCtOrganisationAnalytics(id: string): Promise<CtOrganisationAnalytics> {
  const { data } = await api.get(`/ct/organisations/${id}/analytics/`)
  return data
}
