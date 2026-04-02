import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchOrgAuditLogs } from '@/lib/api/audit'
import { useAuth } from '@/hooks/useAuth'
import {
  approveApprovalAction,
  assignEmployeeDocumentRequests,
  calculatePayrollRun,
  downloadAttendanceTemplate,
  downloadNormalizedAttendanceFile,
  createApprovalWorkflow,
  createCompensationAssignment,
  createCompensationTemplate,
  createDepartment,
  createHolidayCalendar,
  createOrgAddress,
  createPayrollRun,
  createPayrollTaxSlabSet,
  createLeaveCycle,
  createLeavePlan,
  createLocation,
  createNotice,
  createOnDutyPolicy,
  deactivateDepartment,
  deactivateOrgAddress,
  deactivateLocation,
  deleteEmployee,
  endEmployeeEmployment,
  fetchDepartments,
  fetchEmployeeDocumentRequests,
  fetchEmployeeDetail,
  fetchEmployeeDocuments,
  fetchEmployees,
  fetchHolidayCalendars,
  fetchLeaveCycles,
  fetchLeavePlans,
  fetchLocations,
  fetchNotices,
  fetchOnboardingDocumentTypes,
  fetchOnDutyPolicies,
  fetchOrgDashboard,
  fetchOrgSetup,
  fetchOrgLeaveRequests,
  fetchOrgOnDutyRequests,
  fetchOrgProfile,
  fetchPayrollSummary,
  fetchApprovalInbox,
  fetchAttendanceImports,
  fetchApprovalWorkflow,
  fetchApprovalWorkflows,
  fetchLeavePlan,
  finalizePayrollRun,
  getEmployeeDocumentDownloadUrl,
  inviteEmployee,
  markEmployeeJoined,
  publishHolidayCalendar,
  publishNotice,
  rejectApprovalAction,
  rejectEmployeeDocument,
  fetchNotice,
  fetchOnDutyPolicy,
  rerunPayrollRun,
  uploadAttendanceSheet,
  uploadPunchSheet,
  submitCompensationAssignment,
  submitCompensationTemplate,
  submitPayrollRun,
  updateCompensationTemplate,
  updateOrgAddress,
  updateOrgProfile,
  updatePayrollTaxSlabSet,
  updateOrgSetup,
  updateApprovalWorkflow,
  updateDepartment,
  updateEmployee,
  updateHolidayCalendar,
  updateLeaveCycle,
  updateLeavePlan,
  updateLocation,
  updateNotice,
  updateOnDutyPolicy,
  verifyEmployeeDocument,
} from '@/lib/api/org-admin'

function useOrgScope() {
  const { user } = useAuth()
  return user?.organisation_id ?? 'unknown-org'
}

export function useOrgDashboard() {
  const organisationId = useOrgScope()
  return useQuery({ queryKey: ['org', organisationId, 'dashboard'], queryFn: fetchOrgDashboard })
}

export function useOrgSetup() {
  const organisationId = useOrgScope()
  return useQuery({ queryKey: ['org', organisationId, 'setup'], queryFn: fetchOrgSetup })
}

export function useUpdateOrgSetup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateOrgSetup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useOrgAuditLogs(params?: Parameters<typeof fetchOrgAuditLogs>[0]) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'audit', params],
    queryFn: () => fetchOrgAuditLogs(params),
  })
}

export function useOrgProfile() {
  const organisationId = useOrgScope()
  return useQuery({ queryKey: ['org', organisationId, 'profile'], queryFn: fetchOrgProfile })
}

export function useUpdateOrgProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateOrgProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCreateOrgAddress() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createOrgAddress,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateOrgAddress() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateOrgAddress>[1] }) => updateOrgAddress(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDeactivateOrgAddress() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deactivateOrgAddress,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useLocations(includeInactive = false) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'locations', includeInactive],
    queryFn: () => fetchLocations(includeInactive),
  })
}

export function useCreateLocation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createLocation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateLocation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateLocation>[1] }) => updateLocation(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDeactivateLocation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deactivateLocation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDepartments(includeInactive = false) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'departments', includeInactive],
    queryFn: () => fetchDepartments(includeInactive),
  })
}

export function useCreateDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createDepartment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateDepartment>[1] }) => updateDepartment(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDeactivateDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deactivateDepartment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useEmployees(params?: { status?: string; search?: string; page?: number }) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', params],
    queryFn: () => fetchEmployees(params),
  })
}

export function useInviteEmployee() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: inviteEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useOnboardingDocumentTypes() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'document-types'],
    queryFn: fetchOnboardingDocumentTypes,
  })
}

export function useEmployeeDetail(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', id],
    queryFn: () => fetchEmployeeDetail(id),
    enabled: Boolean(id),
  })
}

export function useUpdateEmployee(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateEmployee>[1]) => updateEmployee(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useMarkEmployeeJoined(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof markEmployeeJoined>[1]) => markEmployeeJoined(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useEndEmployeeEmployment(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof endEmployeeEmployment>[1]) => endEmployeeEmployment(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDeleteEmployee(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => deleteEmployee(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useEmployeeDocuments(employeeId: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', employeeId, 'documents'],
    queryFn: () => fetchEmployeeDocuments(employeeId),
    enabled: Boolean(employeeId),
  })
}

export function useEmployeeDocumentRequests(employeeId: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', employeeId, 'document-requests'],
    queryFn: () => fetchEmployeeDocumentRequests(employeeId),
    enabled: Boolean(employeeId),
  })
}

export function useAssignEmployeeDocumentRequests(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (documentTypeIds: string[]) => assignEmployeeDocumentRequests(employeeId, documentTypeIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useVerifyEmployeeDocument(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => verifyEmployeeDocument(employeeId, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useRejectEmployeeDocument(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ documentId, note }: { documentId: string; note: string }) =>
      rejectEmployeeDocument(employeeId, documentId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useEmployeeDocumentDownload() {
  return useMutation({
    mutationFn: ({ employeeId, documentId }: { employeeId: string; documentId: string }) =>
      getEmployeeDocumentDownloadUrl(employeeId, documentId),
  })
}

export function useApprovalWorkflows() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-workflows'],
    queryFn: fetchApprovalWorkflows,
  })
}

export function useApprovalWorkflow(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-workflows', id],
    queryFn: () => fetchApprovalWorkflow(id),
    enabled: Boolean(id),
  })
}

export function useCreateApprovalWorkflow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createApprovalWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateApprovalWorkflow(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateApprovalWorkflow(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useApprovalInbox() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-inbox'],
    queryFn: fetchApprovalInbox,
  })
}

export function useAttendanceImports() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-imports'],
    queryFn: fetchAttendanceImports,
  })
}

export function useUploadAttendanceSheet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadAttendanceSheet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUploadPunchSheet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadPunchSheet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDownloadAttendanceTemplate() {
  return useMutation({
    mutationFn: downloadAttendanceTemplate,
  })
}

export function useDownloadNormalizedAttendanceFile() {
  return useMutation({
    mutationFn: downloadNormalizedAttendanceFile,
  })
}

export function usePayrollSummary() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'payroll'],
    queryFn: fetchPayrollSummary,
  })
}

export function useCreatePayrollTaxSlabSet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPayrollTaxSlabSet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdatePayrollTaxSlabSet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updatePayrollTaxSlabSet(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCreateCompensationTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCompensationTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateCompensationTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateCompensationTemplate(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useSubmitCompensationTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitCompensationTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useCreateCompensationAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCompensationAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useSubmitCompensationAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitCompensationAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useCreatePayrollRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPayrollRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCalculatePayrollRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: calculatePayrollRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useSubmitPayrollRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitPayrollRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useFinalizePayrollRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: finalizePayrollRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useRerunPayrollRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: rerunPayrollRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useApproveApprovalAction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ actionId, comment }: { actionId: string; comment?: string }) => approveApprovalAction(actionId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useRejectApprovalAction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ actionId, comment }: { actionId: string; comment?: string }) => rejectApprovalAction(actionId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useHolidayCalendars() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'holiday-calendars'],
    queryFn: fetchHolidayCalendars,
  })
}

export function useCreateHolidayCalendar() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createHolidayCalendar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateHolidayCalendar(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateHolidayCalendar(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function usePublishHolidayCalendar() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: publishHolidayCalendar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useLeaveCycles() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-cycles'],
    queryFn: fetchLeaveCycles,
  })
}

export function useCreateLeaveCycle() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createLeaveCycle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateLeaveCycle(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateLeaveCycle(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useLeavePlans() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-plans'],
    queryFn: fetchLeavePlans,
  })
}

export function useLeavePlan(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-plans', id],
    queryFn: () => fetchLeavePlan(id),
    enabled: Boolean(id),
  })
}

export function useCreateLeavePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createLeavePlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateLeavePlan(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateLeavePlan(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useOnDutyPolicies() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'on-duty-policies'],
    queryFn: fetchOnDutyPolicies,
  })
}

export function useOnDutyPolicy(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'on-duty-policies', id],
    queryFn: () => fetchOnDutyPolicy(id),
    enabled: Boolean(id),
  })
}

export function useCreateOnDutyPolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createOnDutyPolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateOnDutyPolicy(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateOnDutyPolicy(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useOrgLeaveRequests() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-requests'],
    queryFn: fetchOrgLeaveRequests,
  })
}

export function useOrgOnDutyRequests() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'on-duty-requests'],
    queryFn: fetchOrgOnDutyRequests,
  })
}

export function useNotices(params?: Parameters<typeof fetchNotices>[0]) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'notices', params],
    queryFn: () => fetchNotices(params),
  })
}

export function useNotice(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'notices', id],
    queryFn: () => fetchNotice(id),
    enabled: Boolean(id),
  })
}

export function useCreateNotice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createNotice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateNotice(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateNotice(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function usePublishNotice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: publishNotice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}
