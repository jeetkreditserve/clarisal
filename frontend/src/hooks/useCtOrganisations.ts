import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCtAuditLogs } from '@/lib/api/audit'
import {
  createLicenceBatch,
  createOrganisation,
  fetchCtStats,
  fetchLicenceBatches,
  fetchOrganisation,
  fetchOrgAdmins,
  fetchOrganisations,
  inviteOrgAdmin,
  markLicenceBatchPaid,
  markOrganisationPaid,
  resendOrgAdminInvite,
  restoreOrganisation,
  suspendOrganisation,
  updateLicenceBatch,
  updateOrganisation,
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

export function useCtAuditLogs(organisationId?: string) {
  return useQuery({
    queryKey: ['ct', 'audit', organisationId],
    queryFn: () => fetchCtAuditLogs(organisationId),
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

export function useLicenceBatches(orgId: string) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'licence-batches'],
    queryFn: () => fetchLicenceBatches(orgId),
    enabled: !!orgId,
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

export function useCreateLicenceBatch(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof createLicenceBatch>[1]) => createLicenceBatch(orgId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations'] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'licence-batches'] })
    },
  })
}

export function useUpdateLicenceBatch(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ batchId, payload }: { batchId: string; payload: Parameters<typeof updateLicenceBatch>[2] }) =>
      updateLicenceBatch(orgId, batchId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'licence-batches'] })
    },
  })
}

export function useMarkLicenceBatchPaid(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ batchId, paidAt }: { batchId: string; paidAt?: string }) =>
      markLicenceBatchPaid(orgId, batchId, paidAt ? { paid_at: paidAt } : undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations'] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'licence-batches'] })
    },
  })
}
