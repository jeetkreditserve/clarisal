import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/hooks/useAuth'
import {
  createBankAccount,
  createEducation,
  deleteBankAccount,
  deleteEducation,
  fetchBankAccounts,
  fetchEducation,
  fetchGovernmentIds,
  fetchMyDashboard,
  fetchMyDocuments,
  fetchMyProfile,
  getMyDocumentDownloadUrl,
  updateBankAccount,
  updateEducation,
  updateMyProfile,
  uploadMyDocument,
  upsertGovernmentId,
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

export function useUploadMyDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadMyDocument,
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
