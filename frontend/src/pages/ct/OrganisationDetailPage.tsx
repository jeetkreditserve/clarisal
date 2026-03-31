import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CreditCard, History, Mail, ShieldAlert, UserPlus } from 'lucide-react'
import { toast } from 'sonner'
import {
  useInviteOrgAdmin,
  useMarkOrganisationPaid,
  useOrganisation,
  useOrgAdmins,
  useResendOrgAdminInvite,
  useRestoreOrganisation,
  useSuspendOrganisation,
  useUpdateOrgLicences,
} from '@/hooks/useCtOrganisations'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, formatDateTime, startCase } from '@/lib/format'
import {
  getAccessStateTone,
  getBillingStatusTone,
  getOrganisationStatusTone,
  ORG_ONBOARDING_STEPS,
} from '@/lib/status'
import { getErrorMessage } from '@/lib/errors'

export function OrganisationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const organisationId = id ?? ''
  const { data: organisation, isLoading } = useOrganisation(organisationId)
  const { data: admins } = useOrgAdmins(organisationId)
  const markPaidMutation = useMarkOrganisationPaid()
  const suspendMutation = useSuspendOrganisation()
  const restoreMutation = useRestoreOrganisation()
  const inviteAdminMutation = useInviteOrgAdmin(organisationId)
  const resendInviteMutation = useResendOrgAdminInvite(organisationId)
  const updateLicencesMutation = useUpdateOrgLicences(organisationId)

  const [actionNote, setActionNote] = useState('')
  const [licenceCountInput, setLicenceCountInput] = useState('')
  const [licenceNote, setLicenceNote] = useState('')
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteForm, setInviteForm] = useState({ email: '', first_name: '', last_name: '' })

  const completedSteps = useMemo(() => {
    const currentIndex = ORG_ONBOARDING_STEPS.findIndex((step) => step.id === organisation?.onboarding_stage)
    return currentIndex >= 0 ? currentIndex : 0
  }, [organisation?.onboarding_stage])

  if (isLoading || !organisation) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={6} />
        <div className="grid gap-5 lg:grid-cols-2">
          <SkeletonTable rows={5} />
          <SkeletonTable rows={5} />
        </div>
      </div>
    )
  }

  const handleMarkPaid = async () => {
    try {
      await markPaidMutation.mutateAsync({ id: organisation.id, note: actionNote })
      toast.success('Organisation marked as paid.')
      setActionNote('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update payment state.'))
    }
  }

  const handleSuspend = async () => {
    if (!window.confirm('Suspend this organisation and block admin and employee access?')) return
    try {
      await suspendMutation.mutateAsync({ id: organisation.id, note: actionNote })
      toast.success('Organisation suspended.')
      setActionNote('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to suspend organisation.'))
    }
  }

  const handleRestore = async () => {
    try {
      await restoreMutation.mutateAsync({ id: organisation.id, note: actionNote })
      toast.success('Organisation access restored.')
      setActionNote('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to restore organisation.'))
    }
  }

  const handleInviteAdmin = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await inviteAdminMutation.mutateAsync(inviteForm)
      toast.success('Organisation admin invite sent.')
      setInviteForm({ email: '', first_name: '', last_name: '' })
      setShowInviteForm(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to send admin invite.'))
    }
  }

  const handleResendInvite = async (userId: string) => {
    try {
      await resendInviteMutation.mutateAsync(userId)
      toast.success('Invite resent.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to resend invite.'))
    }
  }

  const handleUpdateLicences = async () => {
    try {
      await updateLicencesMutation.mutateAsync({
        count: Number(licenceCountInput || organisation.licence_summary.purchased),
        note: licenceNote,
      })
      toast.success('Licence allocation updated.')
      setLicenceNote('')
      setLicenceCountInput('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update licences.'))
    }
  }

  return (
    <div className="space-y-6">
      <Link to="/ct/organisations" className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]">
        <ArrowLeft className="h-4 w-4" />
        Back to organisations
      </Link>

      <PageHeader
        eyebrow="Organisation detail"
        title={organisation.name}
        description={`Tenant ${organisation.slug} is currently ${startCase(organisation.status)} with ${organisation.licence_summary.allocated} of ${organisation.licence_summary.purchased} licences allocated.`}
        actions={
          <>
            {organisation.status === 'PENDING' ? (
              <button onClick={handleMarkPaid} className="btn-primary" disabled={markPaidMutation.isPending}>
                Mark payment received
              </button>
            ) : null}
            {organisation.status === 'ACTIVE' ? (
              <button onClick={handleSuspend} className="btn-danger" disabled={suspendMutation.isPending}>
                Suspend access
              </button>
            ) : null}
            {organisation.status === 'SUSPENDED' ? (
              <button onClick={handleRestore} className="btn-primary" disabled={restoreMutation.isPending}>
                Restore access
              </button>
            ) : null}
            {(organisation.status === 'PAID' || organisation.status === 'ACTIVE') && (
              <button onClick={() => setShowInviteForm((current) => !current)} className="btn-secondary">
                <UserPlus className="h-4 w-4" />
                {showInviteForm ? 'Close invite' : 'Invite admin'}
              </button>
            )}
          </>
        }
      />

      <SectionCard title="Access state" description="Commercial readiness and access controls are enforced independently.">
        <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Lifecycle status</p>
              <div className="mt-3">
                <StatusBadge tone={getOrganisationStatusTone(organisation.status)}>{organisation.status}</StatusBadge>
              </div>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Billing status</p>
              <div className="mt-3">
                <StatusBadge tone={getBillingStatusTone(organisation.billing_status)}>{startCase(organisation.billing_status)}</StatusBadge>
              </div>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Access state</p>
              <div className="mt-3">
                <StatusBadge tone={getAccessStateTone(organisation.access_state)}>{startCase(organisation.access_state)}</StatusBadge>
              </div>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Primary admin</p>
              <p className="mt-3 text-sm font-medium text-[hsl(var(--foreground-strong))]">{organisation.primary_admin_email || 'Not assigned'}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Paid at</p>
              <p className="mt-3 text-sm font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(organisation.paid_marked_at)}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Activated at</p>
              <p className="mt-3 text-sm font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(organisation.activated_at)}</p>
            </div>
          </div>

          <div className="surface-muted space-y-3 rounded-[24px] p-5">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Action note</p>
            </div>
            <textarea
              value={actionNote}
              onChange={(event) => setActionNote(event.target.value)}
              className="field-textarea"
              placeholder="Optional note for payment confirmation, suspension, or restoration."
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Onboarding progress" description="The tenant readiness timeline mirrors backend lifecycle events and access rules.">
        <div className="space-y-4">
          {ORG_ONBOARDING_STEPS.map((step, index) => {
            const isCompleted = index <= completedSteps
            const isCurrent = organisation.onboarding_stage === step.id
            return (
              <div
                key={step.id}
                className={`flex gap-4 rounded-[24px] border p-4 ${
                  isCurrent
                    ? 'border-[hsla(var(--info),0.3)] bg-[hsl(var(--info-soft))]'
                    : isCompleted
                      ? 'border-[hsla(var(--success),0.26)] bg-[hsl(var(--success-soft))]'
                      : 'border-[hsla(var(--border),0.92)] bg-[hsla(var(--surface),0.92)]'
                }`}
              >
                <div
                  className={`mt-1 h-3 w-3 rounded-full ${
                    isCurrent
                      ? 'bg-[hsl(var(--info))]'
                      : isCompleted
                        ? 'bg-[hsl(var(--success))]'
                        : 'bg-[hsla(var(--border-strong),0.9)]'
                  }`}
                />
                <div>
                  <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">{step.label}</p>
                  <p className="mt-1 text-sm leading-6 text-[hsl(var(--muted-foreground))]">{step.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Licence control" description="Seat availability governs employee invitations and active onboarding.">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { label: 'Purchased', value: organisation.licence_summary.purchased },
              { label: 'Allocated', value: organisation.licence_summary.allocated },
              { label: 'Available', value: organisation.licence_summary.available },
            ].map((item) => (
              <div key={item.label} className="surface-muted rounded-[24px] p-5">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{item.label}</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">{item.value}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[160px_minmax(0,1fr)_auto]">
            <div>
              <label htmlFor="licence-count" className="field-label">
                New total
              </label>
              <input
                id="licence-count"
                type="number"
                min={organisation.licence_summary.allocated}
                value={licenceCountInput || String(organisation.licence_summary.purchased)}
                onChange={(event) => setLicenceCountInput(event.target.value)}
                className="field-input"
              />
            </div>
            <div>
              <label htmlFor="licence-note" className="field-label">
                Change note
              </label>
              <input
                id="licence-note"
                value={licenceNote}
                onChange={(event) => setLicenceNote(event.target.value)}
                className="field-input"
                placeholder="Optional context for the ledger entry"
              />
            </div>
            <div className="flex items-end">
              <button onClick={handleUpdateLicences} disabled={updateLicencesMutation.isPending} className="btn-primary">
                <CreditCard className="h-4 w-4" />
                Update licences
              </button>
            </div>
          </div>

          <div className="table-shell mt-6">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Delta</th>
                  <th className="pb-3 pr-4 font-semibold">Reason</th>
                  <th className="pb-3 pr-4 font-semibold">Note</th>
                  <th className="pb-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {organisation.licence_ledger_entries.map((entry) => (
                  <tr key={entry.id} className="table-row border-b border-[hsla(var(--border),0.76)] last:border-b-0">
                    <td className="table-primary py-4 pr-4 font-semibold">{entry.delta > 0 ? `+${entry.delta}` : entry.delta}</td>
                    <td className="table-secondary py-4 pr-4">{startCase(entry.reason)}</td>
                    <td className="table-secondary py-4 pr-4">{entry.note || 'No note'}</td>
                    <td className="table-secondary py-4">{formatDateTime(entry.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard
          title="Organisation admins"
          description="Invite the primary organisation administrator after payment is confirmed."
          action={
            organisation.status === 'PAID' || organisation.status === 'ACTIVE' ? (
              <button onClick={() => setShowInviteForm((current) => !current)} className="btn-secondary">
                <Mail className="h-4 w-4" />
                {showInviteForm ? 'Hide invite form' : 'Send invite'}
              </button>
            ) : null
          }
        >
          {showInviteForm ? (
            <form onSubmit={handleInviteAdmin} className="surface-muted mb-6 grid gap-4 rounded-[24px] p-5 lg:grid-cols-3">
              <div>
                <label className="field-label" htmlFor="invite-email">
                  Email
                </label>
                <input
                  id="invite-email"
                  type="email"
                  required
                  value={inviteForm.email}
                  onChange={(event) => setInviteForm((current) => ({ ...current, email: event.target.value }))}
                  className="field-input"
                />
              </div>
              <div>
                <label className="field-label" htmlFor="invite-first-name">
                  First name
                </label>
                <input
                  id="invite-first-name"
                  required
                  value={inviteForm.first_name}
                  onChange={(event) => setInviteForm((current) => ({ ...current, first_name: event.target.value }))}
                  className="field-input"
                />
              </div>
              <div>
                <label className="field-label" htmlFor="invite-last-name">
                  Last name
                </label>
                <input
                  id="invite-last-name"
                  required
                  value={inviteForm.last_name}
                  onChange={(event) => setInviteForm((current) => ({ ...current, last_name: event.target.value }))}
                  className="field-input"
                />
              </div>
              <div className="lg:col-span-3">
                <button type="submit" disabled={inviteAdminMutation.isPending} className="btn-primary">
                  Send admin invitation
                </button>
              </div>
            </form>
          ) : null}

          {!admins || admins.length === 0 ? (
            <EmptyState
              title="No organisation admins yet"
              description="After payment is marked, invite the primary admin so the organisation can activate its workspace."
              icon={UserPlus}
            />
          ) : (
            <div className="table-shell">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="table-head-row">
                    <th className="pb-3 pr-4 font-semibold">Admin</th>
                    <th className="pb-3 pr-4 font-semibold">Email</th>
                    <th className="pb-3 pr-4 font-semibold">State</th>
                    <th className="pb-3 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {admins.map((admin) => (
                    <tr key={admin.id} className="table-row border-b border-[hsla(var(--border),0.76)] last:border-b-0">
                      <td className="table-primary py-4 pr-4 font-semibold">{admin.full_name}</td>
                      <td className="table-secondary py-4 pr-4">{admin.email}</td>
                      <td className="py-4 pr-4">
                        <StatusBadge tone={admin.is_active ? 'success' : 'warning'}>
                          {admin.is_active ? 'Active' : 'Pending activation'}
                        </StatusBadge>
                      </td>
                      <td className="py-4 text-right">
                        {!admin.is_active ? (
                          <button onClick={() => handleResendInvite(admin.id)} className="btn-ghost">
                            Resend invite
                          </button>
                        ) : (
                          <span className="text-xs font-medium uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Active</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Lifecycle events" description="Append-only event feed for payment, activation, and onboarding changes.">
          {organisation.lifecycle_events.length === 0 ? (
            <EmptyState
              title="No lifecycle events"
              description="Events will appear here as Control Tower updates payment or onboarding state."
              icon={History}
            />
          ) : (
            <div className="space-y-3">
              {organisation.lifecycle_events.map((event) => (
                <div key={event.id} className="surface-muted rounded-[24px] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{startCase(event.event_type)}</p>
                    <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">{formatDateTime(event.created_at)}</p>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">Actor: {event.actor_email || 'System'}</p>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="State transitions" description="Legacy state transitions remain visible for operational traceability.">
          {organisation.state_transitions.length === 0 ? (
            <EmptyState
              title="No transitions recorded"
              description="Status transitions will appear once payment or access state changes are applied."
              icon={ShieldAlert}
            />
          ) : (
            <div className="space-y-3">
              {organisation.state_transitions.map((transition) => (
                <div key={transition.id} className="surface-muted rounded-[24px] p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusBadge tone={getOrganisationStatusTone(transition.from_status)}>{transition.from_status}</StatusBadge>
                    <span className="text-[hsl(var(--muted-foreground))]">to</span>
                    <StatusBadge tone={getOrganisationStatusTone(transition.to_status)}>{transition.to_status}</StatusBadge>
                  </div>
                  <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">{transition.note || 'No note provided.'}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                    {transition.transitioned_by_email} • {formatDate(transition.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
