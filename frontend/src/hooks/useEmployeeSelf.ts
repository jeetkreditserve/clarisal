import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/hooks/useAuth'
import {
  approveMyApprovalAction,
  createBankAccount,
  createEmergencyContact,
  createEducation,
  createFamilyMember,
  createMyLeaveRequest,
  createMyOnDutyRequest,
  deleteBankAccount,
  deleteEmergencyContact,
  deleteEducation,
  deleteFamilyMember,
  fetchBankAccounts,
  fetchEducation,
  fetchGovernmentIds,
  fetchMyApprovalInbox,
  fetchMyCalendar,
  fetchMyDashboard,
  fetchMyDocumentRequests,
  fetchMyDocuments,
  fetchMyEvents,
  fetchMyLeaveOverview,
  fetchMyNotices,
  fetchMyOnDutyPolicies,
  fetchMyOnDutyRequests,
  fetchMyOnboarding,
  fetchMyProfile,
  getMyDocumentDownloadUrl,
  rejectMyApprovalAction,
  updateEmergencyContact,
  updateBankAccount,
  updateEducation,
  updateFamilyMember,
  updateMyOnboarding,
  updateMyProfile,
  uploadRequestedDocument,
  uploadMyDocument,
  upsertGovernmentId,
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

export function useMyProfile() {
  const organisationId = useEmployeeScope()
  return useQuery({ queryKey: ['me', organisationId, 'profile'], queryFn: fetchMyProfile })
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
