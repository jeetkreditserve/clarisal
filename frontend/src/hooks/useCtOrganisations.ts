import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCtStats, fetchOrganisations, fetchOrganisation,
  createOrganisation, updateOrganisation,
  activateOrganisation, suspendOrganisation,
  fetchOrgAdmins, inviteOrgAdmin, updateOrgLicences,
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

export function useActivateOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => activateOrganisation(id, note),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
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

export function useUpdateOrgLicences(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (count: number) => updateOrgLicences(orgId, count),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] }),
  })
}
