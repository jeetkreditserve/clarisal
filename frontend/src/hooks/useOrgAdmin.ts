import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/hooks/useAuth'
import {
  createDepartment,
  createLocation,
  deactivateDepartment,
  deactivateLocation,
  fetchDepartments,
  fetchEmployeeDetail,
  fetchEmployeeDocuments,
  fetchEmployees,
  fetchLocations,
  fetchOrgDashboard,
  getEmployeeDocumentDownloadUrl,
  inviteEmployee,
  rejectEmployeeDocument,
  terminateEmployee,
  updateDepartment,
  updateEmployee,
  updateLocation,
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

export function useTerminateEmployee(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => terminateEmployee(id),
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
