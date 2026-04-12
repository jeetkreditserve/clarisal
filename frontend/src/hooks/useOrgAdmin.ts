import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createAssetAssignment,
  createAssetCategory,
  createAssetItem,
  createAssetMaintenance,
  fetchAssetAssignments,
  fetchAssetCategories,
  fetchAssetItems,
  fetchAssetMaintenance,
  markAssetAssignmentLost,
  returnAssetAssignment,
} from '@/lib/api/assets'
import { fetchOrgAuditLogs } from '@/lib/api/audit'
import {
  createOrgExpensePolicy,
  fetchOrgExpenseClaimSummary,
  fetchOrgExpenseClaims,
  fetchOrgExpensePolicies,
  updateOrgExpensePolicy,
} from '@/lib/api/expenses'
import { useAuth } from '@/hooks/useAuth'
import {
  approveApprovalAction,
  createAttendancePolicy,
  createAttendanceSource,
  createAttendanceShift,
  createAttendanceShiftAssignment,
  assignEmployeeDocumentRequests,
  calculatePayrollRun,
  cancelPayrollFiling,
  downloadAttendanceTemplate,
  downloadNormalizedAttendanceFile,
  downloadOrgForm12BBBulk,
  downloadPayrollFiling,
  downloadPayrollRunPayslipsZip,
  createApprovalWorkflow,
  createApprovalDelegation,
  createCompensationAssignment,
  createCompensationTemplate,
  createCostCentre,
  createDepartment,
  createHolidayCalendar,
  createOrgAddress,
  createOrgArrear,
  createPayrollRun,
  createPayrollTdsChallan,
  createPayrollTaxSlabSet,
  createLeaveCycle,
  createLeavePlan,
  createLocation,
  createNotice,
  createOnDutyPolicy,
  deactivateDepartment,
  deactivateCostCentre,
  deactivateOrgAddress,
  deactivateLocation,
  deleteEmployee,
  endEmployeeEmployment,
  completeEmployeeOffboarding,
  fetchDepartments,
  fetchDesignations,
  fetchEmployeeDocumentRequests,
  fetchEmployeeDetail,
  fetchEmployeeCustomFieldValues,
  fetchEmployeeDocuments,
  fetchEmployeeExitInterview,
  fetchEmployeeCareerTimeline,
  fetchEmployees,
  fetchCustomFieldDefinitions,
  fetchOrgChart,
  fetchOrgChartCycles,
  fetchOrgFullAndFinalSettlement,
  fetchOrgFullAndFinalSettlements,
  fetchOrgInvestmentDeclarations,
  fetchOrgArrears,
  fetchHolidayCalendars,
  fetchLeaveCycles,
  fetchLeavePlans,
  fetchLocations,
  fetchNotices,
  fetchOnboardingDocumentTypes,
  fetchOnDutyPolicies,
  fetchPayrollRunDetail,
  fetchPayrollRunItems,
  downloadPayslipPdf,
  fetchOrgDashboard,
  fetchOrgSetup,
  fetchOrgLeaveRequests,
  fetchOrgOnDutyRequests,
  fetchOrgProfile,
  fetchPayrollSummary,
  fetchApprovalInbox,
  fetchApprovalDelegations,
  fetchApprovalWorkflowCatalog,
  fetchApprovalWorkflowReadiness,
  fetchAttendanceDashboard,
  fetchAttendanceDays,
  fetchAttendanceImports,
  fetchAttendancePolicies,
  fetchAttendanceReport,
  fetchAttendanceRegularizations,
  fetchAttendanceSources,
  fetchAttendanceShiftAssignments,
  fetchAttendanceShifts,
  fetchApprovalWorkflow,
  fetchApprovalWorkflows,
  fetchLeavePlan,
  finalizePayrollRun,
  generatePayrollFiling,
  getEmployeeDocumentDownloadUrl,
  inviteEmployee,
  markEmployeeJoined,
  markEmployeeProbationComplete,
  overrideAttendanceDay,
  publishHolidayCalendar,
  publishNotice,
  rejectApprovalAction,
  rejectEmployeeDocument,
  fetchNotice,
  fetchOnDutyPolicy,
  rerunPayrollRun,
  simulateApprovalWorkflow,
  notifyPayrollRunPayslips,
  regeneratePayrollFiling,
  uploadAttendanceSheet,
  uploadPunchSheet,
  submitCompensationAssignment,
  submitCompensationTemplate,
  submitPayrollRun,
  updateCompensationTemplate,
  updateCostCentre,
  updateOrgInvestmentDeclarationReview,
  updateOrgAddress,
  updateOrgProfile,
  updatePayrollTaxSlabSet,
  updatePayrollTdsChallan,
  updateOrgSetup,
  updateApprovalWorkflow,
  updateApprovalDelegation,
  updateDepartment,
  updateEmployee,
  updateEmployeeCustomFieldValues,
  updateEmployeeOffboarding,
  updateEmployeeOffboardingTask,
  submitEmployeeExitInterview,
  updateHolidayCalendar,
  updateLeaveCycle,
  updateLeavePlan,
  updateLocation,
  updateNotice,
  updateOnDutyPolicy,
  updateAttendancePolicy,
  updateAttendanceSource,
  updateAttendanceShift,
  verifyEmployeeDocument,
} from '@/lib/api/org-admin'

function useOrgScope() {
  const { user } = useAuth()
  return user?.organisation_id ?? 'unknown-org'
}

export function useAssetCategories() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'asset-categories'],
    queryFn: fetchAssetCategories,
  })
}

export function useCreateAssetCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAssetCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAssetItems(filters?: Parameters<typeof fetchAssetItems>[0]) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'asset-items', filters],
    queryFn: () => fetchAssetItems(filters),
  })
}

export function useCreateAssetItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAssetItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAssetAssignments(filters?: Parameters<typeof fetchAssetAssignments>[0]) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'asset-assignments', filters],
    queryFn: () => fetchAssetAssignments(filters),
  })
}

export function useCreateAssetAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAssetAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useReturnAssetAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof returnAssetAssignment>[1] }) => returnAssetAssignment(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMarkAssetAssignmentLost() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof markAssetAssignmentLost>[1] }) => markAssetAssignmentLost(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAssetMaintenance() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'asset-maintenance'],
    queryFn: fetchAssetMaintenance,
  })
}

export function useCreateAssetMaintenance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAssetMaintenance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
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

export function useOrgAuditLogs(params?: Parameters<typeof fetchOrgAuditLogs>[0], enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'audit', params],
    queryFn: () => fetchOrgAuditLogs(params),
    enabled,
  })
}

export function useOrgExpensePolicies(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'expense-policies'],
    queryFn: fetchOrgExpensePolicies,
    enabled,
  })
}

export function useOrgExpenseClaims(params?: { status?: string; reimbursement_status?: string; employee?: string }, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'expense-claims', params],
    queryFn: () => fetchOrgExpenseClaims(params),
    enabled,
  })
}

export function useOrgExpenseClaimSummary(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'expense-claim-summary'],
    queryFn: fetchOrgExpenseClaimSummary,
    enabled,
  })
}

export function useCreateOrgExpensePolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createOrgExpensePolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateOrgExpensePolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateOrgExpensePolicy(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
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

export function useLocations(includeInactive = false, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'locations', includeInactive],
    queryFn: () => fetchLocations(includeInactive),
    enabled,
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

export function useDepartments(includeInactive = false, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'departments', includeInactive],
    queryFn: () => fetchDepartments(includeInactive),
    enabled,
  })
}

export function useDesignations(enabled = true) {
  return useQuery({
    queryKey: ['org', 'designations'],
    queryFn: fetchDesignations,
    enabled,
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

export function useEmployees(params?: { status?: string; search?: string; page?: number }, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', params],
    queryFn: () => fetchEmployees(params),
    enabled,
  })
}

export function useOrgChart(includeInactive = false) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'org-chart', includeInactive],
    queryFn: () => fetchOrgChart(includeInactive),
  })
}

export function useOrgChartCycles() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'org-chart', 'cycles'],
    queryFn: fetchOrgChartCycles,
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

export function useEmployeeCareerTimeline(employeeId: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', employeeId, 'career-timeline'],
    queryFn: () => fetchEmployeeCareerTimeline(employeeId),
    enabled: Boolean(employeeId),
  })
}

export function useEmployeeExitInterview(employeeId: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', employeeId, 'exit-interview'],
    queryFn: () => fetchEmployeeExitInterview(employeeId),
    enabled: Boolean(employeeId),
  })
}

export function useCustomFieldDefinitions(placement = 'CUSTOM') {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'custom-fields', placement],
    queryFn: () => fetchCustomFieldDefinitions(placement),
  })
}

export function useEmployeeCustomFieldValues(employeeId: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'employees', employeeId, 'custom-fields'],
    queryFn: () => fetchEmployeeCustomFieldValues(employeeId),
    enabled: Boolean(employeeId),
  })
}

export function useUpdateEmployeeCustomFieldValues(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateEmployeeCustomFieldValues>[1]) => updateEmployeeCustomFieldValues(employeeId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
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

export function useUpdateEmployeeOffboarding(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateEmployeeOffboarding>[1]) => updateEmployeeOffboarding(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useSubmitEmployeeExitInterview(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof submitEmployeeExitInterview>[1]) =>
      submitEmployeeExitInterview(employeeId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateEmployeeOffboardingTask(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: Parameters<typeof updateEmployeeOffboardingTask>[2] }) =>
      updateEmployeeOffboardingTask(employeeId, taskId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCompleteEmployeeOffboarding(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => completeEmployeeOffboarding(employeeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useMarkEmployeeProbationComplete(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => markEmployeeProbationComplete(employeeId),
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

export function useApprovalWorkflows(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-workflows'],
    queryFn: fetchApprovalWorkflows,
    enabled,
  })
}

export function useApprovalWorkflow(id: string, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-workflows', id],
    queryFn: () => fetchApprovalWorkflow(id),
    enabled: enabled && Boolean(id),
  })
}

export function useApprovalWorkflowCatalog(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-workflow-catalog'],
    queryFn: fetchApprovalWorkflowCatalog,
    enabled,
  })
}

export function useApprovalWorkflowReadiness(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-workflow-readiness'],
    queryFn: fetchApprovalWorkflowReadiness,
    enabled,
  })
}

export function useSimulateApprovalWorkflow() {
  return useMutation({
    mutationFn: simulateApprovalWorkflow,
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

export function useApprovalInbox(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-inbox'],
    queryFn: fetchApprovalInbox,
    enabled,
  })
}

export function useApprovalDelegations(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'approval-delegations'],
    queryFn: fetchApprovalDelegations,
    enabled,
  })
}

export function useCreateApprovalDelegation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createApprovalDelegation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateApprovalDelegation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateApprovalDelegation(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAttendanceDashboard(date?: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-dashboard', date],
    queryFn: () => fetchAttendanceDashboard(date),
  })
}

export function useAttendancePolicies() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-policies'],
    queryFn: fetchAttendancePolicies,
  })
}

export function useCreateAttendancePolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAttendancePolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateAttendancePolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateAttendancePolicy>[1] }) =>
      updateAttendancePolicy(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAttendanceShifts() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-shifts'],
    queryFn: fetchAttendanceShifts,
  })
}

export function useCreateAttendanceShift() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAttendanceShift,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateAttendanceShift() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateAttendanceShift>[1] }) =>
      updateAttendanceShift(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAttendanceShiftAssignments() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-shift-assignments'],
    queryFn: fetchAttendanceShiftAssignments,
  })
}

export function useCreateAttendanceShiftAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAttendanceShiftAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAttendanceDays(params?: { date?: string; status?: string; employee_id?: string }) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-days', params],
    queryFn: () => fetchAttendanceDays(params),
  })
}

export function useOverrideAttendanceDay() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof overrideAttendanceDay>[1] }) =>
      overrideAttendanceDay(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useAttendanceRegularizations(statusValue?: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-regularizations', statusValue],
    queryFn: () => fetchAttendanceRegularizations(statusValue),
  })
}

export function useAttendanceSources() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-sources'],
    queryFn: fetchAttendanceSources,
  })
}

export function useCreateAttendanceSource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAttendanceSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateAttendanceSource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateAttendanceSource>[1] }) =>
      updateAttendanceSource(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useAttendanceReport(month?: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'attendance-report', month],
    queryFn: () => fetchAttendanceReport(month),
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

export function useOrgInvestmentDeclarations(params?: {
  employee_id?: string
  fiscal_year?: string
  section?: string
  is_verified?: boolean
}) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'investment-declarations', params],
    queryFn: () => fetchOrgInvestmentDeclarations(params),
  })
}

export function usePayrollRunDetail(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'payroll-runs', id],
    queryFn: () => fetchPayrollRunDetail(id),
    enabled: Boolean(id),
  })
}

export function usePayrollRunItems(
  runId: string,
  params?: { employee?: string; has_exception?: boolean; page?: number },
) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'payroll-runs', runId, 'items', params],
    queryFn: () => fetchPayrollRunItems(runId, params),
    enabled: Boolean(runId),
  })
}

export function useDownloadPayslipPdf() {
  return useMutation({
    mutationFn: downloadPayslipPdf,
  })
}

export function useDownloadPayrollRunPayslipsZip() {
  return useMutation({
    mutationFn: ({ runId, item_ids }: { runId: string; item_ids?: string[] }) => downloadPayrollRunPayslipsZip(runId, { item_ids }),
  })
}

export function useNotifyPayrollRunPayslips() {
  return useMutation({
    mutationFn: ({ runId, item_ids }: { runId: string; item_ids?: string[] }) => notifyPayrollRunPayslips(runId, { item_ids }),
  })
}

export function useOrgFullAndFinalSettlements() {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'fnf-settlements'],
    queryFn: fetchOrgFullAndFinalSettlements,
  })
}

export function useOrgFullAndFinalSettlement(id: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'fnf-settlements', id],
    queryFn: () => fetchOrgFullAndFinalSettlement(id),
    enabled: Boolean(id),
  })
}

export function useOrgArrears(employeeId?: string) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'arrears', employeeId ?? 'all'],
    queryFn: () => fetchOrgArrears(employeeId),
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

export function useCreateCostCentre() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCostCentre,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateCostCentre() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateCostCentre>[1] }) => updateCostCentre(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDeactivateCostCentre() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deactivateCostCentre,
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

export function useCreateOrgArrear() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createOrgArrear,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCreatePayrollTdsChallan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPayrollTdsChallan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdatePayrollTdsChallan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updatePayrollTdsChallan>[1] }) =>
      updatePayrollTdsChallan(id, payload),
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

export function useGeneratePayrollFiling() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: generatePayrollFiling,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useRegeneratePayrollFiling() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: regeneratePayrollFiling,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCancelPayrollFiling() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: cancelPayrollFiling,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useDownloadPayrollFiling() {
  return useMutation({
    mutationFn: downloadPayrollFiling,
  })
}

export function useDownloadOrgForm12BBBulk() {
  return useMutation({
    mutationFn: downloadOrgForm12BBBulk,
  })
}

export function useReviewOrgInvestmentDeclaration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_verified }: { id: string; is_verified: boolean }) =>
      updateOrgInvestmentDeclarationReview(id, { is_verified }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
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

export function useLeaveCycles(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-cycles'],
    queryFn: fetchLeaveCycles,
    enabled,
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

export function useLeavePlans(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-plans'],
    queryFn: fetchLeavePlans,
    enabled,
  })
}

export function useLeavePlan(id: string, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'leave-plans', id],
    queryFn: () => fetchLeavePlan(id),
    enabled: enabled && Boolean(id),
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

export function useOnDutyPolicies(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'on-duty-policies'],
    queryFn: fetchOnDutyPolicies,
    enabled,
  })
}

export function useOnDutyPolicy(id: string, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'on-duty-policies', id],
    queryFn: () => fetchOnDutyPolicy(id),
    enabled: enabled && Boolean(id),
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

export function useOrgOnDutyRequests(enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'on-duty-requests'],
    queryFn: fetchOrgOnDutyRequests,
    enabled,
  })
}

export function useNotices(params?: Parameters<typeof fetchNotices>[0], enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'notices', params],
    queryFn: () => fetchNotices(params),
    enabled,
  })
}

export function useNotice(id: string, enabled = true) {
  const organisationId = useOrgScope()
  return useQuery({
    queryKey: ['org', organisationId, 'notices', id],
    queryFn: () => fetchNotice(id),
    enabled: enabled && Boolean(id),
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
