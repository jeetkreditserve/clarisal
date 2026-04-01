export interface AuditLogEntry {
  id: string
  actor_email: string | null
  actor_name: string | null
  organisation_name: string | null
  action: string
  module: string
  target_type: string | null
  target_id: string | null
  target_label: string
  payload: Record<string, unknown>
  payload_summary: string
  ip_address: string | null
  user_agent: string | null
  created_at: string
}
