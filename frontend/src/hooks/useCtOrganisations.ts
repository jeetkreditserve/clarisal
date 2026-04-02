import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCtAuditLogs } from '@/lib/api/audit'
import {
  createCtApprovalWorkflow,
  createCtPayrollTaxSlabSet,
  createCtHolidayCalendar,
  createCtLeaveCycle,
  createCtLeavePlan,
  createCtLocation,
  createCtOrgNote,
  createCtNotice,
  createCtOnDutyPolicy,
  createLicenceBatch,
  createOrganisation,
  createOrganisationAddress,
  createCtDepartment,
  deactivateCtDepartment,
  deactivateCtLocation,
  deactivateCtOrgAdmin,
  deactivateOrganisationAddress,
  fetchCtHolidayCalendars,
  fetchCtOrgConfiguration,
  fetchCtOrgEmployeeDetail,
  fetchCtOrgEmployees,
  fetchCtOrgNotes,
  fetchCtPayrollTaxSlabSets,
  fetchCtStats,
  fetchLicenceBatches,
  fetchOrganisation,
  fetchOrgAdmins,
  fetchOrganisations,
  inviteOrgAdmin,
  publishCtHolidayCalendar,
  publishCtNotice,
  markLicenceBatchPaid,
  markOrganisationPaid,
  reactivateCtOrgAdmin,
  resendOrgAdminInvite,
  restoreOrganisation,
  revokePendingCtOrgAdmin,
  suspendOrganisation,
  updateCtApprovalWorkflow,
  updateCtOrgEmployeeDetail,
  updateCtBootstrapAdmin,
  updateCtDepartment,
  updateCtHolidayCalendar,
  updateCtLeaveCycle,
  updateCtLeavePlan,
  updateCtLocation,
  updateCtNotice,
  updateCtOnDutyPolicy,
  updateLicenceBatch,
  updateOrganisation,
  updateOrganisationAddress,
} from '@/lib/api/organisations'

export function useCtStats() {
  return useQuery({ queryKey: ['ct', 'stats'], queryFn: fetchCtStats })
}

export function useCtPayrollTaxSlabSets() {
  return useQuery({ queryKey: ['ct', 'payroll', 'tax-slab-sets'], queryFn: fetchCtPayrollTaxSlabSets })
}

export function useCreateCtPayrollTaxSlabSet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createCtPayrollTaxSlabSet,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'payroll'] }),
  })
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

export function useCtAuditLogs(params?: Parameters<typeof fetchCtAuditLogs>[0], enabled = true) {
  return useQuery({
    queryKey: ['ct', 'audit', params],
    queryFn: () => fetchCtAuditLogs(params),
    enabled,
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

export function useUpdateCtBootstrapAdmin(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateCtBootstrapAdmin>[1]) => updateCtBootstrapAdmin(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id, 'admins'] })
    },
  })
}

export function useCreateOrganisationAddress(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof createOrganisationAddress>[1]) => createOrganisationAddress(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id, 'configuration'] })
    },
  })
}

export function useUpdateOrganisationAddress(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ addressId, payload }: { addressId: string; payload: Parameters<typeof updateOrganisationAddress>[2] }) =>
      updateOrganisationAddress(id, addressId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id, 'configuration'] })
    },
  })
}

export function useDeactivateOrganisationAddress(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (addressId: string) => deactivateOrganisationAddress(id, addressId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id, 'configuration'] })
    },
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

export function useOrgAdmins(orgId: string, enabled = true) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'admins'],
    queryFn: () => fetchOrgAdmins(orgId),
    enabled: !!orgId && enabled,
  })
}

export function useCtOrgEmployees(orgId: string, params?: { status?: string; search?: string; page?: number }, enabled = true) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'employees', params],
    queryFn: () => fetchCtOrgEmployees(orgId, params),
    enabled: !!orgId && enabled,
  })
}

export function useCtOrgEmployeeDetail(orgId: string, employeeId: string, enabled = true) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'employees', employeeId],
    queryFn: () => fetchCtOrgEmployeeDetail(orgId, employeeId),
    enabled: Boolean(orgId && employeeId && enabled),
  })
}

export function useUpdateCtOrgEmployeeDetail(orgId: string, employeeId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateCtOrgEmployeeDetail>[2]) => updateCtOrgEmployeeDetail(orgId, employeeId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'employees', employeeId] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'employees'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'configuration'] })
    },
  })
}

export function useCtHolidayCalendars(orgId: string, enabled = true) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'holiday-calendars'],
    queryFn: () => fetchCtHolidayCalendars(orgId),
    enabled: !!orgId && enabled,
  })
}

export function useCreateCtHolidayCalendar(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCtHolidayCalendar(orgId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'holiday-calendars'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
  })
}

export function useUpdateCtHolidayCalendar(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ calendarId, payload }: { calendarId: string; payload: Record<string, unknown> }) =>
      updateCtHolidayCalendar(orgId, calendarId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'holiday-calendars'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
  })
}

export function usePublishCtHolidayCalendar(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (calendarId: string) => publishCtHolidayCalendar(orgId, calendarId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'holiday-calendars'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
  })
}

export function useCtOrgConfiguration(orgId: string, enabled = true) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'configuration'],
    queryFn: () => fetchCtOrgConfiguration(orgId),
    enabled: !!orgId && enabled,
  })
}

export function useCtOrgNotes(orgId: string, enabled = true) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'notes'],
    queryFn: () => fetchCtOrgNotes(orgId),
    enabled: !!orgId && enabled,
  })
}

export function useCreateCtOrgNote(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: string) => createCtOrgNote(orgId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'notes'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
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

export function useDeactivateCtOrgAdmin(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => deactivateCtOrgAdmin(orgId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'admins'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
  })
}

export function useReactivateCtOrgAdmin(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => reactivateCtOrgAdmin(orgId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'admins'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
  })
}

export function useRevokePendingCtOrgAdmin(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => revokePendingCtOrgAdmin(orgId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'admins'] })
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
    },
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

function invalidateCtConfiguration(qc: ReturnType<typeof useQueryClient>, orgId: string) {
  qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] })
  qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'configuration'] })
}

export function useCreateCtLocation(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof createCtLocation>[1]) => createCtLocation(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtLocation(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ locationId, payload }: { locationId: string; payload: Parameters<typeof updateCtLocation>[2] }) =>
      updateCtLocation(orgId, locationId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useDeactivateCtLocation(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (locationId: string) => deactivateCtLocation(orgId, locationId),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useCreateCtDepartment(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof createCtDepartment>[1]) => createCtDepartment(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtDepartment(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ departmentId, payload }: { departmentId: string; payload: Parameters<typeof updateCtDepartment>[2] }) =>
      updateCtDepartment(orgId, departmentId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useDeactivateCtDepartment(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (departmentId: string) => deactivateCtDepartment(orgId, departmentId),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useCreateCtLeaveCycle(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCtLeaveCycle(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtLeaveCycle(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ cycleId, payload }: { cycleId: string; payload: Record<string, unknown> }) =>
      updateCtLeaveCycle(orgId, cycleId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useCreateCtLeavePlan(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCtLeavePlan(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtLeavePlan(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ planId, payload }: { planId: string; payload: Record<string, unknown> }) =>
      updateCtLeavePlan(orgId, planId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useCreateCtOnDutyPolicy(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCtOnDutyPolicy(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtOnDutyPolicy(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ policyId, payload }: { policyId: string; payload: Record<string, unknown> }) =>
      updateCtOnDutyPolicy(orgId, policyId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useCreateCtApprovalWorkflow(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCtApprovalWorkflow(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtApprovalWorkflow(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workflowId, payload }: { workflowId: string; payload: Record<string, unknown> }) =>
      updateCtApprovalWorkflow(orgId, workflowId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useCreateCtNotice(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => createCtNotice(orgId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function useUpdateCtNotice(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ noticeId, payload }: { noticeId: string; payload: Record<string, unknown> }) =>
      updateCtNotice(orgId, noticeId, payload),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}

export function usePublishCtNotice(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (noticeId: string) => publishCtNotice(orgId, noticeId),
    onSuccess: () => invalidateCtConfiguration(qc, orgId),
  })
}
