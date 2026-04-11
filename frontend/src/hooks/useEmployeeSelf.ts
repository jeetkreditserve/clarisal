import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/hooks/useAuth'
import { acknowledgeMyAssetAssignment, fetchMyAssetAssignments } from '@/lib/api/assets'
import {
  cancelMyExpenseClaim,
  createMyExpenseClaim,
  fetchMyExpenseClaims,
  fetchMyExpensePolicies,
  submitMyExpenseClaim,
  updateMyExpenseClaim,
  uploadMyExpenseReceipt,
} from '@/lib/api/expenses'
import {
  approveMyApprovalAction,
  createBankAccount,
  createMyAttendanceRegularization,
  createEmergencyContact,
  createEducation,
  createFamilyMember,
  createMyInvestmentDeclaration,
  createMyLeaveEncashment,
  createMyLeaveRequest,
  createMyOnDutyRequest,
  deleteBankAccount,
  deleteEmergencyContact,
  deleteEducation,
  deleteFamilyMember,
  deleteMyInvestmentDeclaration,
  downloadMyForm12BB,
  downloadMyPayslip,
  downloadMyPayslipsForFiscalYear,
  fetchBankAccounts,
  fetchEducation,
  fetchGovernmentIds,
  fetchMyAttendanceCalendar,
  fetchMyAttendanceHistory,
  fetchMyAttendancePolicy,
  fetchMyAttendanceRegularizations,
  fetchMyAttendanceSummary,
  fetchMyApprovalInbox,
  fetchMyCalendar,
  fetchMyDashboard,
  fetchMyDocumentRequests,
  fetchMyDocuments,
  fetchMyEvents,
  fetchMyInvestmentDeclarations,
  fetchMyLeaveEncashments,
  fetchMyLeaveOverview,
  fetchMyNotices,
  fetchMyOffboarding,
  fetchMyOnDutyPolicies,
  fetchMyOnDutyRequests,
  fetchMyOnboarding,
  fetchMyPayslip,
  fetchMyPayslips,
  fetchMyProfile,
  getMyDocumentDownloadUrl,
  punchIn,
  punchOut,
  rejectMyApprovalAction,
  updateEmergencyContact,
  updateMyAttendanceRegularization,
  updateBankAccount,
  updateEducation,
  updateFamilyMember,
  updateMyOnboarding,
  updateMyProfile,
  updateMyInvestmentDeclaration,
  uploadRequestedDocument,
  uploadMyDocument,
  upsertGovernmentId,
  withdrawMyAttendanceRegularization,
  withdrawMyLeaveRequest,
  withdrawMyOnDutyRequest,
} from '@/lib/api/self-service'

function useEmployeeScope() {
  const { user } = useAuth()
  return user?.organisation_id ?? 'unknown-employee-org'
}

export function useMyDashboard() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'dashboard'], queryFn: fetchMyDashboard })
}

export function useMyAssetAssignments() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'assets'], queryFn: fetchMyAssetAssignments })
}

export function useAcknowledgeMyAssetAssignment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: acknowledgeMyAssetAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyExpensePolicies() {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'expense-policies'],
    queryFn: fetchMyExpensePolicies,
  })
}

export function useMyExpenseClaims() {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'expense-claims'],
    queryFn: fetchMyExpenseClaims,
  })
}

export function useCreateMyExpenseClaim() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyExpenseClaim,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUpdateMyExpenseClaim() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateMyExpenseClaim(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useUploadMyExpenseReceipt() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ claimId, lineId, file }: { claimId: string; lineId: string; file: File }) => uploadMyExpenseReceipt(claimId, lineId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useSubmitMyExpenseClaim() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitMyExpenseClaim,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useCancelMyExpenseClaim() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: cancelMyExpenseClaim,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useMyAttendanceSummary() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'attendance-summary'], queryFn: fetchMyAttendanceSummary })
}

export function useMyAttendanceHistory(month?: string) {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'attendance-history', month],
    queryFn: () => fetchMyAttendanceHistory(month),
  })
}

export function useMyAttendanceCalendar(month?: string) {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'attendance-calendar', month],
    queryFn: () => fetchMyAttendanceCalendar(month),
  })
}

export function useMyAttendancePolicy() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'attendance-policy'], queryFn: fetchMyAttendancePolicy })
}

export function usePunchIn() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: punchIn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function usePunchOut() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: punchOut,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyAttendanceRegularizations() {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'attendance-regularizations'],
    queryFn: fetchMyAttendanceRegularizations,
  })
}

export function useCreateMyAttendanceRegularization() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyAttendanceRegularization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateMyAttendanceRegularization() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateMyAttendanceRegularization>[1] }) =>
      updateMyAttendanceRegularization(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useWithdrawMyAttendanceRegularization() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: withdrawMyAttendanceRegularization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyProfile() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'profile'], queryFn: fetchMyProfile })
}

export function useMyOffboarding() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'offboarding'], queryFn: fetchMyOffboarding })
}

export function useMyOnboarding() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'onboarding'], queryFn: fetchMyOnboarding })
}

export function useUpdateMyOnboarding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateMyOnboarding,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateMyProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateMyProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useEducation() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'education'], queryFn: fetchEducation })
}

export function useCreateEducation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createEducation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateEducation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateEducation>[1] }) => updateEducation(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useDeleteEducation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteEducation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useCreateFamilyMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createFamilyMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateFamilyMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateFamilyMember>[1] }) => updateFamilyMember(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useDeleteFamilyMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteFamilyMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useCreateEmergencyContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createEmergencyContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateEmergencyContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateEmergencyContact>[1] }) =>
      updateEmergencyContact(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useDeleteEmergencyContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteEmergencyContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useGovernmentIds() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'government-ids'], queryFn: fetchGovernmentIds })
}

export function useUpsertGovernmentId() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: upsertGovernmentId,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useBankAccounts() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'bank-accounts'], queryFn: fetchBankAccounts })
}

export function useMyPayslips(params?: { fiscal_year?: string; search?: string }) {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'payslips', params],
    queryFn: () => fetchMyPayslips(params),
  })
}

export function useMyPayslip(id: string) {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'payslips', id],
    queryFn: () => fetchMyPayslip(id),
    enabled: Boolean(id),
  })
}

export function useDownloadMyPayslip() {
  return useMutation({
    mutationFn: downloadMyPayslip,
  })
}

export function useDownloadMyPayslipsForFiscalYear() {
  return useMutation({
    mutationFn: downloadMyPayslipsForFiscalYear,
  })
}

export function useMyInvestmentDeclarations(params?: { fiscal_year?: string }) {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'investment-declarations', params],
    queryFn: () => fetchMyInvestmentDeclarations(params),
  })
}

export function useCreateMyInvestmentDeclaration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyInvestmentDeclaration,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateMyInvestmentDeclaration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateMyInvestmentDeclaration>[1] }) =>
      updateMyInvestmentDeclaration(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useDeleteMyInvestmentDeclaration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteMyInvestmentDeclaration,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useDownloadMyForm12BB() {
  return useMutation({
    mutationFn: downloadMyForm12BB,
  })
}

export function useCreateBankAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createBankAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUpdateBankAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateBankAccount>[1] }) => updateBankAccount(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useDeleteBankAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteBankAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyDocuments() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'documents'], queryFn: fetchMyDocuments })
}

export function useMyDocumentRequests() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'document-requests'], queryFn: fetchMyDocumentRequests })
}

export function useUploadMyDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadMyDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useUploadRequestedDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadRequestedDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyDocumentDownload() {
  return useMutation({
    mutationFn: getMyDocumentDownloadUrl,
  })
}

export function useMyNotices() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'notices'], queryFn: fetchMyNotices })
}

export function useMyEvents() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'events'], queryFn: fetchMyEvents })
}

export function useMyApprovalInbox() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'approval-inbox'], queryFn: fetchMyApprovalInbox })
}

export function useApproveMyApprovalAction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ actionId, comment }: { actionId: string; comment?: string }) => approveMyApprovalAction(actionId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useRejectMyApprovalAction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ actionId, comment }: { actionId: string; comment?: string }) => rejectMyApprovalAction(actionId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
  })
}

export function useMyLeaveOverview() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'leave-overview'], queryFn: fetchMyLeaveOverview })
}

export function useCreateMyLeaveRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyLeaveRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useWithdrawMyLeaveRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: withdrawMyLeaveRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyLeaveEncashments() {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'leave-encashments'],
    queryFn: fetchMyLeaveEncashments,
  })
}

export function useCreateMyLeaveEncashment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyLeaveEncashment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyOnDutyPolicies() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'od-policies'], queryFn: fetchMyOnDutyPolicies })
}

export function useMyOnDutyRequests() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'od-requests'], queryFn: fetchMyOnDutyRequests })
}

export function useCreateMyOnDutyRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyOnDutyRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useWithdrawMyOnDutyRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: withdrawMyOnDutyRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useMyCalendar(month?: string) {
  const organisationId = useEmployeeScope()
  return useQuery({
    queryKey: ['me', organisationId, 'calendar', month],
    queryFn: () => fetchMyCalendar(month),
  })
}
