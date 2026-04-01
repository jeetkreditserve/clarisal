export interface AuditLogEntry {
  id: string
  actor_email: string | null
  organisation_name: string | null
  action: string
  target_type: string | null
  target_id: string | null
  payload: Record<string, unknown>
  ip_address: string | null
  user_agent: string | null
  created_at: string
}
