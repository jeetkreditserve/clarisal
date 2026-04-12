import api from '@/lib/api'
import type {
  AccessControlOverview,
  AccessRole,
  AccessRoleAssignment,
  AccessRoleAssignmentWritePayload,
  AccessRoleWritePayload,
  AccessSimulationPayload,
  AccessSimulationResult,
} from '@/types/access-control'

export async function fetchOrgAccessControlOverview(): Promise<AccessControlOverview> {
  const { data } = await api.get<AccessControlOverview>('/org/access-control/')
  return data
}

export async function createOrgAccessRole(payload: AccessRoleWritePayload): Promise<AccessRole> {
  const { data } = await api.post<AccessRole>('/org/access-control/roles/', payload)
  return data
}

export async function assignOrgAccessRole(payload: AccessRoleAssignmentWritePayload): Promise<AccessRoleAssignment> {
  const { data } = await api.post<AccessRoleAssignment>('/org/access-control/assignments/', payload)
  return data
}

export async function simulateOrgAccess(payload: AccessSimulationPayload): Promise<AccessSimulationResult> {
  const { data } = await api.post<AccessSimulationResult>('/org/access-control/simulate/', payload)
  return data
}

export async function fetchCtAccessControlOverview(): Promise<AccessControlOverview> {
  const { data } = await api.get<AccessControlOverview>('/ct/access-control/')
  return data
}

export async function createCtAccessRole(payload: AccessRoleWritePayload): Promise<AccessRole> {
  const { data } = await api.post<AccessRole>('/ct/access-control/roles/', payload)
  return data
}

export async function assignCtAccessRole(payload: AccessRoleAssignmentWritePayload): Promise<AccessRoleAssignment> {
  const { data } = await api.post<AccessRoleAssignment>('/ct/access-control/assignments/', payload)
  return data
}
