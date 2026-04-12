import api from '@/lib/api'
import type {
  OrgDashboardStats,
  OrganisationEntityType,
  OrganisationAddress,
  OrganisationDetail,
  PaginatedResponse,
} from '@/types/organisation'
import type { OrgAdminSetupState } from '@/types/organisation'
import type {
  ApprovalActionItem,
  ApprovalDelegation,
  ApprovalWorkflowCatalog,
  AttendanceDayRecord,
  AttendanceImportJob,
  AttendancePolicy,
  AttendanceRegularization,
  AttendanceSourceConfig,
  BiometricDevice,
  BiometricDeviceHealth,
  BiometricSyncLog,
  AttendanceShift,
  AttendanceShiftAssignment,
  ApprovalWorkflowConfig,
  ApprovalWorkflowReadinessRow,
  ApprovalWorkflowSimulationRequest,
  ApprovalWorkflowSimulationResult,
  Arrears,
  CompensationAssignment,
  CompensationTemplate,
  CostCentre,
  CustomFieldDefinition,
  Department,
  DocumentRecord,
  EmployeeDocumentRequest,
  EmployeeCustomFieldValue,
  EmployeeDetail,
  EmployeeExitInterview,
  EmployeeListItem,
  FullAndFinalSettlement,
  HolidayCalendar,
  InvestmentDeclaration,
  LeaveCycle,
  LeavePlan,
  LeaveRequestRecord,
  Location,
  NoticeItem,
  OnDutyPolicy,
  OrgAttendanceDashboard,
  OrgAttendanceReport,
  OffboardingProcess,
  OffboardingTaskStatus,
  OnDutyRequestRecord,
  OnboardingDocumentType,
  OrgPayrollSummary,
  PayrollRun,
  PayrollRunItem,
  PayrollTdsChallan,
  StatutoryFilingBatch,
  PayrollTaxSlabSet,
} from '@/types/hr'

export async function fetchOrgDashboard() {
  const { data } = await api.get<OrgDashboardStats>('/org/dashboard/')
  return data
}

export async function fetchOrgSetup() {
  const { data } = await api.get<OrgAdminSetupState>('/org/setup/')
  return data
}

export async function updateOrgSetup(payload: { current_step?: string; completed?: boolean }) {
  const { data } = await api.patch<OrgAdminSetupState>('/org/setup/', payload)
  return data
}

export async function fetchOrgProfile() {
  const { data } = await api.get<OrganisationDetail>('/org/profile/')
  return data
}

export async function updateOrgProfile(payload: Partial<{
  name: string
  pan_number: string
  phone: string
  email: string
  country_code: string
  currency: string
  entity_type: OrganisationEntityType
  logo_url: string
  esi_branch_code: string
}>) {
  const { data } = await api.patch<OrganisationDetail>('/org/profile/', payload)
  return data
}

export async function createOrgAddress(payload: {
  address_type: string
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
}) {
  const { data } = await api.post<OrganisationAddress>('/org/profile/addresses/', payload)
  return data
}

export async function updateOrgAddress(addressId: string, payload: Partial<{
  address_type: string
  label: string
  line1: string
  line2: string
  city: string
  state: string
  state_code: string
  country: string
  country_code: string
  pincode: string
  gstin: string | null
}>) {
  const { data } = await api.patch<OrganisationAddress>(`/org/profile/addresses/${addressId}/`, payload)
  return data
}

export async function deactivateOrgAddress(addressId: string) {
  const { data } = await api.delete<OrganisationAddress>(`/org/profile/addresses/${addressId}/`)
  return data
}

export async function fetchLocations(includeInactive = false) {
  const { data } = await api.get<Location[]>('/org/locations/', {
    params: { include_inactive: includeInactive },
  })
  return data
}

export async function createLocation(payload: {
  name: string
  organisation_address_id: string
  is_remote?: boolean
}) {
  const { data } = await api.post<Location>('/org/locations/', payload)
  return data
}

export async function updateLocation(id: string, payload: Partial<{
  name: string
  organisation_address_id: string
  is_remote: boolean
}>) {
  const { data } = await api.patch<Location>(`/org/locations/${id}/`, payload)
  return data
}

export async function deactivateLocation(id: string) {
  const { data } = await api.post<Location>(`/org/locations/${id}/deactivate/`)
  return data
}

export async function fetchDepartments(includeInactive = false) {
  const { data } = await api.get<Department[]>('/org/departments/', {
    params: { include_inactive: includeInactive },
  })
  return data
}

export interface Designation {
  id: string
  name: string
  level: number
  is_active: boolean
  created_at: string
}

export async function fetchDesignations() {
  const { data } = await api.get<Designation[]>('/org/designations/')
  return data
}

export async function createDepartment(payload: {
  name: string
  description?: string
  parent_department_id?: string | null
}) {
  const { data } = await api.post<Department>('/org/departments/', payload)
  return data
}

export async function updateDepartment(
  id: string,
  payload: Partial<{ name: string; description: string; parent_department_id: string | null }>
) {
  const { data } = await api.patch<Department>(`/org/departments/${id}/`, payload)
  return data
}

export async function deactivateDepartment(id: string) {
  const { data } = await api.post<Department>(`/org/departments/${id}/deactivate/`)
  return data
}

export async function fetchEmployees(params?: {
  status?: string
  search?: string
  page?: number
}) {
  const { data } = await api.get<PaginatedResponse<EmployeeListItem>>('/org/employees/', { params })
  return data
}

export async function inviteEmployee(payload: {
  first_name: string
  last_name: string
  company_email: string
  designation?: string
  employment_type?: string
  date_of_joining?: string | null
  department_id?: string | null
  office_location_id?: string | null
  required_document_type_ids?: string[]
}) {
  const { data } = await api.post<{
    employee: EmployeeDetail
    invitation: { email: string; expires_at: string }
  }>('/org/employees/', payload)
  return data
}

export async function fetchEmployeeDetail(id: string) {
  const { data } = await api.get<EmployeeDetail>(`/org/employees/${id}/`)
  return data
}

export interface OrgChartNode {
  id: string
  name: string
  email: string
  employee_code: string | null
  designation: string | null
  department: string | null
  status: EmployeeDetail['status']
  profile_picture: string | null
  direct_reports: OrgChartNode[]
}

export interface OrgChartCyclesResponse {
  has_cycles: boolean
  cycles: string[][]
}

export async function fetchOrgChart(includeInactive = false) {
  const { data } = await api.get<OrgChartNode[]>('/org/org-chart/', {
    params: includeInactive ? { include_inactive: true } : undefined,
  })
  return data
}

export async function fetchOrgChartCycles() {
  const { data } = await api.get<OrgChartCyclesResponse>('/org/org-chart/cycles/')
  return data
}

export interface CareerTimelineEntry {
  type: 'PROMOTION' | 'TRANSFER'
  id: string
  date: string
  status: string
  from_department: string | null
  to_department: string | null
  from_location: string | null
  to_location: string | null
  from_designation: string | null
  to_designation: string | null
  has_compensation_change?: boolean
  reason: string
  requested_by: string | null
  approved_by: string | null
}

export async function fetchEmployeeCareerTimeline(employeeId: string) {
  const { data } = await api.get<CareerTimelineEntry[]>(`/org/employees/${employeeId}/career-timeline/`)
  return data
}

export async function fetchCustomFieldDefinitions(placement = 'CUSTOM') {
  const { data } = await api.get<CustomFieldDefinition[]>('/org/custom-fields/', {
    params: placement ? { placement } : undefined,
  })
  return data
}

export async function fetchEmployeeCustomFieldValues(employeeId: string) {
  const { data } = await api.get<EmployeeCustomFieldValue[]>(`/org/employees/${employeeId}/custom-fields/`)
  return data
}

export async function updateEmployeeCustomFieldValues(
  employeeId: string,
  payload: {
    custom_fields: Array<{
      field_definition_id: string
      value_text?: string
      value_number?: string | null
      value_date?: string | null
      value_boolean?: boolean
    }>
  },
) {
  const { data } = await api.put<EmployeeCustomFieldValue[]>(`/org/employees/${employeeId}/custom-fields/`, payload)
  return data
}

export async function updateEmployee(
  id: string,
  payload: Partial<{
    designation: string
    employment_type: string
    date_of_joining: string | null
    department_id: string | null
    office_location_id: string | null
    leave_approval_workflow_id: string | null
    on_duty_approval_workflow_id: string | null
    attendance_regularization_approval_workflow_id: string | null
    expense_approval_workflow_id: string | null
  }>
) {
  const { data } = await api.patch<EmployeeDetail>(`/org/employees/${id}/`, payload)
  return data
}

export async function markEmployeeJoined(
  id: string,
  payload: {
    employee_code: string
    date_of_joining: string
    designation: string
    reporting_to_employee_id: string
  }
) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/mark-joined/`, payload)
  return data
}

export async function fetchOnboardingDocumentTypes() {
  const { data } = await api.get<OnboardingDocumentType[]>('/org/document-types/')
  return data
}

export async function fetchEmployeeDocumentRequests(employeeId: string) {
  const { data } = await api.get<EmployeeDocumentRequest[]>(`/org/employees/${employeeId}/document-requests/`)
  return data
}

export async function assignEmployeeDocumentRequests(employeeId: string, documentTypeIds: string[]) {
  const { data } = await api.post<EmployeeDocumentRequest[]>(
    `/org/employees/${employeeId}/document-requests/`,
    { document_type_ids: documentTypeIds }
  )
  return data
}

export async function endEmployeeEmployment(
  id: string,
  payload: { status: 'RESIGNED' | 'RETIRED' | 'TERMINATED'; date_of_exit: string; exit_reason?: string; exit_notes?: string }
) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/end-employment/`, payload)
  return data
}

export async function updateEmployeeOffboarding(
  id: string,
  payload: Partial<{ exit_reason: string; exit_notes: string }>
) {
  const { data } = await api.patch<OffboardingProcess>(`/org/employees/${id}/offboarding/`, payload)
  return data
}

export async function fetchEmployeeExitInterview(employeeId: string) {
  const { data } = await api.get<EmployeeExitInterview | null>(`/org/employees/${employeeId}/exit-interview/`)
  return data
}

export async function submitEmployeeExitInterview(
  employeeId: string,
  payload: Partial<{
    interview_date: string | null
    exit_reason: string
    interviewer_id: string | null
    overall_satisfaction: number | null
    would_recommend_org: boolean | null
    feedback: string
    areas_of_improvement: string
  }>
) {
  const { data } = await api.patch<EmployeeExitInterview>(`/org/employees/${employeeId}/exit-interview/`, payload)
  return data
}

export async function updateEmployeeOffboardingTask(
  employeeId: string,
  taskId: string,
  payload: { status: OffboardingTaskStatus; note?: string }
) {
  const { data } = await api.patch<OffboardingProcess>(`/org/employees/${employeeId}/offboarding/tasks/${taskId}/`, payload)
  return data
}

export async function completeEmployeeOffboarding(id: string) {
  const { data } = await api.post<OffboardingProcess>(`/org/employees/${id}/offboarding/complete/`)
  return data
}

export async function markEmployeeProbationComplete(id: string) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/probation-complete/`)
  return data
}

export async function deleteEmployee(id: string) {
  const { data } = await api.delete<EmployeeDetail>(`/org/employees/${id}/delete/`)
  return data
}

export async function fetchEmployeeDocuments(employeeId: string) {
  const { data } = await api.get<DocumentRecord[]>(`/org/employees/${employeeId}/documents/`)
  return data
}

export async function verifyEmployeeDocument(employeeId: string, documentId: string) {
  const { data } = await api.post<DocumentRecord>(`/org/employees/${employeeId}/documents/${documentId}/verify/`)
  return data
}

export async function rejectEmployeeDocument(employeeId: string, documentId: string, note: string) {
  const { data } = await api.post<DocumentRecord>(`/org/employees/${employeeId}/documents/${documentId}/reject/`, {
    note,
  })
  return data
}

export async function getEmployeeDocumentDownloadUrl(employeeId: string, documentId: string) {
  const { data } = await api.get<{ url: string }>(`/org/employees/${employeeId}/documents/${documentId}/download/`)
  return data
}

export async function fetchApprovalWorkflows() {
  const { data } = await api.get<ApprovalWorkflowConfig[]>('/org/approvals/workflows/')
  return data
}

export async function fetchApprovalWorkflow(id: string) {
  const { data } = await api.get<ApprovalWorkflowConfig>(`/org/approvals/workflows/${id}/`)
  return data
}

export async function fetchApprovalWorkflowCatalog() {
  const { data } = await api.get<ApprovalWorkflowCatalog>('/org/approvals/workflows/catalog/')
  return data
}

export async function fetchApprovalWorkflowReadiness() {
  const { data } = await api.get<ApprovalWorkflowReadinessRow[]>('/org/approvals/workflows/readiness/')
  return data
}

export async function simulateApprovalWorkflow(payload: ApprovalWorkflowSimulationRequest) {
  const { data } = await api.post<ApprovalWorkflowSimulationResult>('/org/approvals/workflows/simulate/', payload)
  return data
}

export async function createApprovalWorkflow(payload: Record<string, unknown>) {
  const { data } = await api.post<ApprovalWorkflowConfig>('/org/approvals/workflows/', payload)
  return data
}

export async function updateApprovalWorkflow(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<ApprovalWorkflowConfig>(`/org/approvals/workflows/${id}/`, payload)
  return data
}

export async function fetchApprovalInbox() {
  const { data } = await api.get<ApprovalActionItem[]>('/org/approvals/inbox/')
  return data
}

export async function fetchApprovalDelegations() {
  const { data } = await api.get<ApprovalDelegation[]>('/org/approvals/delegations/')
  return data
}

export async function createApprovalDelegation(payload: Record<string, unknown>) {
  const { data } = await api.post<ApprovalDelegation>('/org/approvals/delegations/', payload)
  return data
}

export async function updateApprovalDelegation(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<ApprovalDelegation>(`/org/approvals/delegations/${id}/`, payload)
  return data
}

export async function approveApprovalAction(actionId: string, comment = '') {
  const { data } = await api.post<ApprovalActionItem>(`/org/approvals/actions/${actionId}/approve/`, { comment })
  return data
}

export async function rejectApprovalAction(actionId: string, comment = '') {
  const { data } = await api.post<ApprovalActionItem>(`/org/approvals/actions/${actionId}/reject/`, { comment })
  return data
}

export async function fetchHolidayCalendars() {
  const { data } = await api.get<HolidayCalendar[]>('/org/holiday-calendars/')
  return data
}

export async function createHolidayCalendar(payload: Record<string, unknown>) {
  const { data } = await api.post<HolidayCalendar>('/org/holiday-calendars/', payload)
  return data
}

export async function updateHolidayCalendar(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<HolidayCalendar>(`/org/holiday-calendars/${id}/`, payload)
  return data
}

export async function publishHolidayCalendar(id: string) {
  const { data } = await api.post<HolidayCalendar>(`/org/holiday-calendars/${id}/publish/`)
  return data
}

export async function fetchLeaveCycles() {
  const { data } = await api.get<LeaveCycle[]>('/org/leave-cycles/')
  return data
}

export async function createLeaveCycle(payload: Record<string, unknown>) {
  const { data } = await api.post<LeaveCycle>('/org/leave-cycles/', payload)
  return data
}

export async function updateLeaveCycle(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<LeaveCycle>(`/org/leave-cycles/${id}/`, payload)
  return data
}

export async function fetchLeavePlans() {
  const { data } = await api.get<LeavePlan[]>('/org/leave-plans/')
  return data
}

export async function fetchLeavePlan(id: string) {
  const { data } = await api.get<LeavePlan>(`/org/leave-plans/${id}/`)
  return data
}

export async function createLeavePlan(payload: Record<string, unknown>) {
  const { data } = await api.post<LeavePlan>('/org/leave-plans/', payload)
  return data
}

export async function updateLeavePlan(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<LeavePlan>(`/org/leave-plans/${id}/`, payload)
  return data
}

export async function fetchOnDutyPolicies() {
  const { data } = await api.get<OnDutyPolicy[]>('/org/on-duty-policies/')
  return data
}

export async function fetchOnDutyPolicy(id: string) {
  const { data } = await api.get<OnDutyPolicy>(`/org/on-duty-policies/${id}/`)
  return data
}

export async function createOnDutyPolicy(payload: Record<string, unknown>) {
  const { data } = await api.post<OnDutyPolicy>('/org/on-duty-policies/', payload)
  return data
}

export async function updateOnDutyPolicy(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<OnDutyPolicy>(`/org/on-duty-policies/${id}/`, payload)
  return data
}

export async function fetchOrgLeaveRequests() {
  const { data } = await api.get<LeaveRequestRecord[]>('/org/leave-requests/')
  return data
}

export async function fetchOrgOnDutyRequests() {
  const { data } = await api.get<OnDutyRequestRecord[]>('/org/on-duty-requests/')
  return data
}

export async function fetchAttendanceImports() {
  const { data } = await api.get<AttendanceImportJob[]>('/org/attendance/imports/')
  return data
}

export async function fetchAttendanceDashboard(date?: string) {
  const { data } = await api.get<OrgAttendanceDashboard>('/org/attendance/dashboard/', {
    params: date ? { date } : undefined,
  })
  return data
}

export async function fetchAttendancePolicies() {
  const { data } = await api.get<AttendancePolicy[]>('/org/attendance/policies/')
  return data
}

export async function createAttendancePolicy(payload: Partial<AttendancePolicy>) {
  const { data } = await api.post<AttendancePolicy>('/org/attendance/policies/', payload)
  return data
}

export async function updateAttendancePolicy(id: string, payload: Partial<AttendancePolicy>) {
  const { data } = await api.patch<AttendancePolicy>(`/org/attendance/policies/${id}/`, payload)
  return data
}

export async function fetchAttendanceShifts() {
  const { data } = await api.get<AttendanceShift[]>('/org/attendance/shifts/')
  return data
}

export async function createAttendanceShift(payload: Partial<AttendanceShift>) {
  const { data } = await api.post<AttendanceShift>('/org/attendance/shifts/', payload)
  return data
}

export async function updateAttendanceShift(id: string, payload: Partial<AttendanceShift>) {
  const { data } = await api.patch<AttendanceShift>(`/org/attendance/shifts/${id}/`, payload)
  return data
}

export async function fetchAttendanceShiftAssignments() {
  const { data } = await api.get<AttendanceShiftAssignment[]>('/org/attendance/shift-assignments/')
  return data
}

export async function createAttendanceShiftAssignment(payload: {
  employee_id: string
  shift_id: string
  start_date: string
  end_date?: string | null
}) {
  const { data } = await api.post<AttendanceShiftAssignment>('/org/attendance/shift-assignments/', payload)
  return data
}

export async function fetchAttendanceDays(params?: {
  date?: string
  status?: string
  employee_id?: string
}) {
  const { data } = await api.get<AttendanceDayRecord[]>('/org/attendance/days/', { params })
  return data
}

export async function overrideAttendanceDay(id: string, payload: {
  check_in?: string | null
  check_out?: string | null
  note?: string
}) {
  const { data } = await api.patch<AttendanceDayRecord>(`/org/attendance/days/${id}/`, payload)
  return data
}

export async function fetchAttendanceRegularizations(statusValue?: string) {
  const { data } = await api.get<AttendanceRegularization[]>('/org/attendance/regularizations/', {
    params: statusValue ? { status: statusValue } : undefined,
  })
  return data
}

export async function fetchAttendanceSources() {
  const { data } = await api.get<AttendanceSourceConfig[]>('/org/attendance/sources/')
  return data
}

export async function createAttendanceSource(payload: {
  name: string
  kind: 'API' | 'EXCEL' | 'DEVICE'
  configuration?: Record<string, unknown>
  is_active?: boolean
}) {
  const { data } = await api.post<AttendanceSourceConfig>('/org/attendance/sources/', payload)
  return data
}

export async function updateAttendanceSource(
  id: string,
  payload: {
    name?: string
    configuration?: Record<string, unknown>
    is_active?: boolean
    rotate_api_key?: boolean
  }
) {
  const { data } = await api.patch<AttendanceSourceConfig>(`/org/attendance/sources/${id}/`, payload)
  return data
}

export async function fetchAttendanceReport(month?: string) {
  const { data } = await api.get<OrgAttendanceReport>('/org/attendance/reports/summary/', {
    params: month ? { month } : undefined,
  })
  return data
}

export async function uploadAttendanceSheet(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<AttendanceImportJob>('/org/attendance/imports/attendance-sheet/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function uploadPunchSheet(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<AttendanceImportJob>('/org/attendance/imports/punch-sheet/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function downloadAttendanceTemplate(mode: 'attendance-sheet' | 'punch-sheet') {
  const { data, headers } = await api.get<Blob>(`/org/attendance/imports/templates/${mode}/`, {
    responseType: 'blob',
  })
  return {
    blob: data,
    filename: headers['content-disposition']?.match(/filename=\"?([^"]+)\"?/)?.[1] || `${mode}.xlsx`,
  }
}

export async function downloadNormalizedAttendanceFile(jobId: string) {
  const { data, headers } = await api.get<Blob>(`/org/attendance/imports/${jobId}/normalized-file/`, {
    responseType: 'blob',
  })
  return {
    blob: data,
    filename: headers['content-disposition']?.match(/filename=\"?([^"]+)\"?/)?.[1] || `normalized-attendance-${jobId}.xlsx`,
  }
}

export async function getBiometricDevices() {
  const { data } = await api.get<BiometricDevice[]>('/org/biometrics/devices/')
  return data
}

export async function createBiometricDevice(payload: {
  name: string
  device_serial?: string
  protocol: BiometricDevice['protocol']
  ip_address?: string
  port?: number
  auth_username?: string
  api_key?: string
  oauth_client_id?: string
  oauth_client_secret?: string
  is_active?: boolean
}) {
  const { data } = await api.post<BiometricDevice>('/org/biometrics/devices/', payload)
  return data
}

export async function deleteBiometricDevice(id: string) {
  await api.delete(`/org/biometrics/devices/${id}/`)
}

export async function getDeviceSyncLogs(deviceId: string) {
  const { data } = await api.get<BiometricSyncLog[]>(`/org/biometrics/devices/${deviceId}/sync-logs/`)
  return data
}

export async function checkDeviceHealth(deviceId: string) {
  const { data } = await api.get<BiometricDeviceHealth>(`/org/biometrics/devices/${deviceId}/health/`)
  return data
}

export async function fetchPayrollSummary() {
  const { data } = await api.get<OrgPayrollSummary>('/org/payroll/summary/')
  return data
}

export async function fetchOrgInvestmentDeclarations(params?: {
  employee_id?: string
  fiscal_year?: string
  section?: string
  is_verified?: boolean
}) {
  const { data } = await api.get<InvestmentDeclaration[]>('/org/payroll/investment-declarations/', { params })
  return data
}

export async function updateOrgInvestmentDeclarationReview(id: string, payload: { is_verified: boolean }) {
  const { data } = await api.patch<InvestmentDeclaration>(`/org/payroll/investment-declarations/${id}/`, payload)
  return data
}

export async function fetchPayrollRunDetail(id: string) {
  const { data } = await api.get<PayrollRun>(`/org/payroll/runs/${id}/`)
  return data
}

export async function fetchPayrollRunItems(
  runId: string,
  params?: { employee?: string; has_exception?: boolean; page?: number },
) {
  const { data } = await api.get<PaginatedResponse<PayrollRunItem>>(`/org/payroll/runs/${runId}/items/`, { params })
  return data
}

export async function downloadPayslipPdf(id: string) {
  const response = await api.get<Blob>(`/org/payroll/payslips/${id}/download/`, {
    responseType: 'blob',
  })
  return {
    blob: response.data as Blob,
    filename: response.headers['content-disposition']?.match(/filename="?([^"]+)"?/)?.[1] || `payslip-${id}.pdf`,
  }
}

export async function downloadPayrollRunPayslipsZip(runId: string, payload: { item_ids?: string[] }) {
  const response = await api.post<Blob>(`/org/payroll/runs/${runId}/payslips/download/`, payload, {
    responseType: 'blob',
  })
  return {
    blob: response.data as Blob,
    filename: response.headers['content-disposition']?.match(/filename="?([^"]+)"?/)?.[1] || `payslips-${runId}.zip`,
  }
}

export async function notifyPayrollRunPayslips(runId: string, payload: { item_ids?: string[] }) {
  const { data } = await api.post<{ selected_count: number; notified_count: number }>(`/org/payroll/runs/${runId}/payslips/notify/`, payload)
  return data
}

export async function fetchOrgFullAndFinalSettlements() {
  const { data } = await api.get<FullAndFinalSettlement[]>('/org/payroll/full-and-final-settlements/')
  return data
}

export async function fetchOrgFullAndFinalSettlement(id: string) {
  const { data } = await api.get<FullAndFinalSettlement>(`/org/payroll/full-and-final-settlements/${id}/`)
  return data
}

export async function fetchOrgArrears(employeeId?: string) {
  const { data } = await api.get<Arrears[]>('/org/payroll/arrears/')
  if (!employeeId) return data
  return data.filter((arrear) => arrear.employee_id === employeeId)
}

export async function createOrgArrear(payload: {
  employee_id: string
  for_period_year: number
  for_period_month: number
  reason: string
  amount: string
}) {
  const { data } = await api.post<Arrears>('/org/payroll/arrears/', payload)
  return data
}

export type OrgReportFormat = 'json' | 'csv' | 'xlsx'

export async function downloadOrgReport(
  reportType: string,
  params: Record<string, string> = {},
  fileFormat: OrgReportFormat = 'xlsx',
) {
  const response = await api.get<Blob | Record<string, unknown>>(`/org/reports/${reportType}/`, {
    params: { ...params, file_format: fileFormat },
    responseType: fileFormat === 'json' ? 'json' : 'blob',
  })

  if (fileFormat === 'json') {
    return response.data
  }

  return {
    blob: response.data as Blob,
    filename: response.headers['content-disposition']?.match(/filename=\"?([^"]+)\"?/)?.[1] || `${reportType}.${fileFormat}`,
  }
}

export async function createPayrollTaxSlabSet(payload: Record<string, unknown>) {
  const { data } = await api.post<PayrollTaxSlabSet>('/org/payroll/tax-slab-sets/', payload)
  return data
}

export async function createCostCentre(payload: {
  code: string
  name: string
  gl_code?: string
  parent_id?: string | null
  is_active?: boolean
}) {
  const { data } = await api.post<CostCentre>('/org/payroll/cost-centres/', payload)
  return data
}

export async function updateCostCentre(id: string, payload: Partial<{
  code: string
  name: string
  gl_code: string
  parent_id: string | null
  is_active: boolean
}>) {
  const { data } = await api.patch<CostCentre>(`/org/payroll/cost-centres/${id}/`, payload)
  return data
}

export async function deactivateCostCentre(id: string) {
  await api.delete(`/org/payroll/cost-centres/${id}/`)
}

export async function updatePayrollTaxSlabSet(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<PayrollTaxSlabSet>(`/org/payroll/tax-slab-sets/${id}/`, payload)
  return data
}

export async function createCompensationTemplate(payload: Record<string, unknown>) {
  const { data } = await api.post<CompensationTemplate>('/org/payroll/templates/', payload)
  return data
}

export async function updateCompensationTemplate(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<CompensationTemplate>(`/org/payroll/templates/${id}/`, payload)
  return data
}

export async function submitCompensationTemplate(id: string) {
  const { data } = await api.post<CompensationTemplate>(`/org/payroll/templates/${id}/submit/`)
  return data
}

export async function createCompensationAssignment(payload: Record<string, unknown>) {
  const { data } = await api.post<CompensationAssignment>('/org/payroll/compensations/', payload)
  return data
}

export async function submitCompensationAssignment(id: string) {
  const { data } = await api.post<CompensationAssignment>(`/org/payroll/compensations/${id}/submit/`)
  return data
}

export async function createPayrollRun(payload: Record<string, unknown>) {
  const { data } = await api.post<PayrollRun>('/org/payroll/runs/', payload)
  return data
}

export async function createPayrollTdsChallan(payload: Record<string, unknown>) {
  const { data } = await api.post<PayrollTdsChallan>('/org/payroll/tds-challans/', payload)
  return data
}

export async function updatePayrollTdsChallan(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<PayrollTdsChallan>(`/org/payroll/tds-challans/${id}/`, payload)
  return data
}

export async function calculatePayrollRun(id: string) {
  const { data } = await api.post<PayrollRun>(`/org/payroll/runs/${id}/calculate/`)
  return data
}

export async function submitPayrollRun(id: string) {
  const { data } = await api.post<PayrollRun>(`/org/payroll/runs/${id}/submit/`)
  return data
}

export async function finalizePayrollRun(id: string) {
  const { data } = await api.post<PayrollRun>(`/org/payroll/runs/${id}/finalize/`)
  return data
}

export async function rerunPayrollRun(id: string) {
  const { data } = await api.post<PayrollRun>(`/org/payroll/runs/${id}/rerun/`)
  return data
}

export async function generatePayrollFiling(payload: Record<string, unknown>) {
  const { data } = await api.post<StatutoryFilingBatch>('/org/payroll/filings/', payload)
  return data
}

export async function regeneratePayrollFiling(id: string) {
  const { data } = await api.post<StatutoryFilingBatch>(`/org/payroll/filings/${id}/regenerate/`)
  return data
}

export async function cancelPayrollFiling(id: string) {
  const { data } = await api.post<StatutoryFilingBatch>(`/org/payroll/filings/${id}/cancel/`)
  return data
}

export async function downloadPayrollFiling(id: string) {
  const response = await api.get<Blob>(`/org/payroll/filings/${id}/download/`, {
    responseType: 'blob',
  })

  const contentType = response.headers['content-type'] ?? ''
  if (contentType.includes('application/json')) {
    const payload = JSON.parse(await (response.data as Blob).text()) as { url: string; file_name?: string }
    const downloadResponse = await fetch(payload.url)
    const blob = await downloadResponse.blob()
    return {
      blob,
      filename: payload.file_name || `statutory-filing-${id}`,
    }
  }

  return {
    blob: response.data as Blob,
    filename: response.headers['content-disposition']?.match(/filename=\"?([^"]+)\"?/)?.[1] || `statutory-filing-${id}`,
  }
}

export async function fetchNotices(params?: { status?: string; audience_type?: string; search?: string }) {
  const { data } = await api.get<NoticeItem[]>('/org/notices/', { params })
  return data
}

export async function fetchNotice(id: string) {
  const { data } = await api.get<NoticeItem>(`/org/notices/${id}/`)
  return data
}

export async function createNotice(payload: Record<string, unknown>) {
  const { data } = await api.post<NoticeItem>('/org/notices/', payload)
  return data
}

export async function updateNotice(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<NoticeItem>(`/org/notices/${id}/`, payload)
  return data
}

export async function publishNotice(id: string) {
  const { data } = await api.post<NoticeItem>(`/org/notices/${id}/publish/`)
  return data
}

export async function downloadOrgForm12BBBulk(fiscalYear: string): Promise<Blob> {
  const response = await api.get<Blob>(`/org/payroll/form-12bb/${fiscalYear}/download/`, {
    responseType: 'blob',
  })
  return response.data
}
