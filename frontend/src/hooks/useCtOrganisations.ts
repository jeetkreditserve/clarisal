import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createOrganisation,
  fetchCtStats,
  fetchOrganisation,
  fetchOrgAdmins,
  fetchOrganisations,
  inviteOrgAdmin,
  markOrganisationPaid,
  resendOrgAdminInvite,
  restoreOrganisation,
  suspendOrganisation,
  updateOrganisation,
  updateOrgLicences,
} from '@/lib/api/organisations'

export function useCtStats() {
  return useQuery({ queryKey: ['ct', 'stats'], queryFn: fetchCtStats })
}

export function useOrganisations(params?: { search?: string; status?: string; page?: number }) {
  return useQuery({
    queryKey: ['ct', 'organisations', params],
    queryFn: () => fetchOrganisations(params),
  })
}

export function useOrganisation(id: string) {
  return useQuery({
    queryKey: ['ct', 'organisations', id],
    queryFn: () => fetchOrganisation(id),
    enabled: !!id,
  })
}

export function useCreateOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createOrganisation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations'] }),
  })
}

export function useUpdateOrganisation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateOrganisation>[1]) => updateOrganisation(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] }),
  })
}

export function useMarkOrganisationPaid() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => markOrganisationPaid(id, note),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations'] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
    },
  })
}

export function useSuspendOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => suspendOrganisation(id, note),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations'] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
    },
  })
}

export function useRestoreOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => restoreOrganisation(id, note),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations'] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
    },
  })
}

export function useOrgAdmins(orgId: string) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'admins'],
    queryFn: () => fetchOrgAdmins(orgId),
    enabled: !!orgId,
  })
}

export function useInviteOrgAdmin(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof inviteOrgAdmin>[1]) => inviteOrgAdmin(orgId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'admins'] }),
  })
}

export function useResendOrgAdminInvite(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => resendOrgAdminInvite(orgId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'admins'] }),
  })
}

export function useUpdateOrgLicences(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ count, note }: { count: number; note?: string }) => updateOrgLicences(orgId, count, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations'] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
    },
  })
}
