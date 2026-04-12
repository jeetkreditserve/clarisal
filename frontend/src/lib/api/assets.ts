import api from '@/lib/api'
import type { AssetAssignment, AssetCategory, AssetItem, AssetMaintenance } from '@/types/hr'

export async function fetchAssetCategories() {
  const { data } = await api.get<AssetCategory[]>('/org/assets/categories/')
  return data
}

export async function createAssetCategory(payload: {
  name: string
  description?: string
  is_active?: boolean
}) {
  const { data } = await api.post<AssetCategory>('/org/assets/categories/', payload)
  return data
}

export async function fetchAssetItems(params?: {
  status?: string
  category?: string
}) {
  const { data } = await api.get<AssetItem[]>('/org/assets/items/', { params })
  return data
}

export async function createAssetItem(payload: {
  name: string
  asset_tag?: string
  serial_number?: string
  vendor?: string
  category?: string | null
  purchase_date?: string | null
  purchase_cost?: string | null
  warranty_expiry?: string | null
  condition?: string
  notes?: string
  metadata?: Record<string, unknown>
}) {
  const { data } = await api.post<AssetItem>('/org/assets/items/', payload)
  return data
}

export async function fetchAssetAssignments(params?: {
  status?: string
  employee?: string
}) {
  const { data } = await api.get<AssetAssignment[]>('/org/assets/assignments/', { params })
  return data
}

export async function createAssetAssignment(payload: {
  asset_id: string
  employee_id: string
  expected_return_date?: string | null
  condition_on_issue?: string
  notes?: string
}) {
  const { data } = await api.post<AssetAssignment>('/org/assets/assignments/', payload)
  return data
}

export async function returnAssetAssignment(
  id: string,
  payload: {
    condition_on_return?: string | null
    notes?: string
  },
) {
  const { data } = await api.post<AssetAssignment>(`/org/assets/assignments/${id}/return/`, payload)
  return data
}

export async function markAssetAssignmentLost(
  id: string,
  payload: {
    notes?: string
  },
) {
  const { data } = await api.post<AssetAssignment>(`/org/assets/assignments/${id}/lost/`, payload)
  return data
}

export async function fetchAssetMaintenance() {
  const { data } = await api.get<AssetMaintenance[]>('/org/assets/maintenance/')
  return data
}

export async function createAssetMaintenance(payload: {
  asset: string
  maintenance_type: string
  description?: string
  scheduled_date: string
  completed_date?: string | null
  cost?: string | null
  vendor?: string
  notes?: string
}) {
  const { data } = await api.post<AssetMaintenance>('/org/assets/maintenance/', payload)
  return data
}

export async function fetchMyAssetAssignments() {
  const { data } = await api.get<AssetAssignment[]>('/me/assets/')
  return data
}

export async function acknowledgeMyAssetAssignment(assignmentId: string) {
  const { data } = await api.post<AssetAssignment>(`/me/assets/${assignmentId}/acknowledge/`)
  return data
}
