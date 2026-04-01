import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  Activity,
  ArrowLeft,
  BadgeDollarSign,
  Building2,
  CalendarDays,
  CreditCard,
  FileText,
  History,
  Mail,
  MessageSquare,
  UserPlus,
  Users,
} from 'lucide-react'
import { toast } from 'sonner'

import { AuditTimeline } from '@/components/ui/AuditTimeline'
import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import {
  SkeletonFormBlock,
  SkeletonMetricCard,
  SkeletonPageHeader,
  SkeletonTable,
} from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCreateCtHolidayCalendar,
  useCreateCtOrgNote,
  useCreateLicenceBatch,
  useCtAuditLogs,
  useCtHolidayCalendars,
  useCtOrgConfiguration,
  useCtOrgEmployeeDetail,
  useCtOrgEmployees,
  useCtOrgNotes,
  useInviteOrgAdmin,
  useMarkLicenceBatchPaid,
  useOrganisation,
  useOrgAdmins,
  usePublishCtHolidayCalendar,
  useResendOrgAdminInvite,
  useRestoreOrganisation,
  useSuspendOrganisation,
  useUpdateCtHolidayCalendar,
  useUpdateLicenceBatch,
} from '@/hooks/useCtOrganisations'
import { createDefaultHolidayCalendarForm, HOLIDAY_CLASSIFICATION_OPTIONS, HOLIDAY_SESSION_OPTIONS } from '@/lib/constants'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, formatDateTime, startCase } from '@/lib/format'
import { ORG_ONBOARDING_STEPS } from '@/lib/status'
import type { HolidayCalendar } from '@/types/hr'
import type { LicenceBatch } from '@/types/organisation'

type DetailTabKey =
  | 'overview'
  | 'details'
  | 'licences'
  | 'admins'
  | 'employees'
  | 'holidays'
  | 'configuration'
  | 'audit'
  | 'notes'

type BatchFormState = {
  quantity: string
  price_per_licence_per_month: string
  start_date: string
  end_date: string
  note: string
}

type ActionDialogState = {
  open: boolean
  note: string
}

const TAB_OPTIONS: Array<{
  key: DetailTabKey
  label: string
  icon: React.ComponentType<{ className?: string }>
}> = [
  { key: 'overview', label: 'Overview', icon: Activity },
  { key: 'details', label: 'Org Details', icon: Building2 },
  { key: 'licences', label: 'Org Licences', icon: CreditCard },
  { key: 'admins', label: 'Org Admins', icon: Users },
  { key: 'employees', label: 'Employees', icon: Users },
  { key: 'holidays', label: 'Org Holidays', icon: CalendarDays },
  { key: 'configuration', label: 'Configuration', icon: FileText },
  { key: 'audit', label: 'Audit Timeline', icon: History },
  { key: 'notes', label: 'Notes', icon: MessageSquare },
]

function calculateBillingMonths(startDate: string, endDate: string) {
  if (!startDate || !endDate) return 0
  const start = new Date(`${startDate}T00:00:00Z`)
  const end = new Date(`${endDate}T00:00:00Z`)
  const diffMs = end.getTime() - start.getTime()
  if (Number.isNaN(diffMs) || diffMs < 0) return 0
  const totalDays = Math.floor(diffMs / (24 * 60 * 60 * 1000)) + 1
  return Math.max(1, Math.ceil(totalDays / 30))
}

function formatMoney(value: string | number, currency = 'INR') {
  const numeric = typeof value === 'number' ? value : Number(value)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(numeric) ? numeric : 0)
}

function emptyBatchForm(): BatchFormState {
  return {
    quantity: '1',
    price_per_licence_per_month: '0.00',
    start_date: '',
    end_date: '',
    note: '',
  }
}

function DetailMetric({
  label,
  value,
  helper,
}: {
  label: string
  value: string
  helper?: string
}) {
  return (
    <div className="surface-muted rounded-[24px] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">{value}</p>
      {helper ? <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{helper}</p> : null}
    </div>
  )
}

function DetailListCard({
  title,
  children,
  footer,
}: {
  title: string
  children: React.ReactNode
  footer?: React.ReactNode
}) {
  return (
    <div className="surface-muted rounded-[24px] p-4">
      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{title}</p>
      <div className="mt-2 space-y-2 text-sm text-[hsl(var(--muted-foreground))]">{children}</div>
      {footer ? <div className="mt-4">{footer}</div> : null}
    </div>
  )
}

function InfoStack({
  items,
}: {
  items: Array<{ label: string; value: string | null | undefined }>
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="surface-muted rounded-[20px] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">{item.label}</p>
          <p className="mt-2 break-words text-sm font-medium text-[hsl(var(--foreground-strong))]">
            {item.value || 'Not set'}
          </p>
        </div>
      ))}
    </div>
  )
}

function createHolidayFormState(calendar?: HolidayCalendar) {
  if (!calendar) return createDefaultHolidayCalendarForm()
  return {
    name: calendar.name,
    year: calendar.year,
    description: calendar.description ?? '',
    is_default: calendar.is_default,
    holidays: calendar.holidays.map((holiday) => ({
      id: holiday.id,
      name: holiday.name,
      holiday_date: holiday.holiday_date,
      classification: holiday.classification,
      session: holiday.session,
      description: holiday.description ?? '',
    })),
    location_ids: [...calendar.location_ids],
  }
}

export function OrganisationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const organisationId = id ?? ''
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = (searchParams.get('tab') ?? 'overview') as DetailTabKey
  const activeTab = TAB_OPTIONS.some((tab) => tab.key === requestedTab) ? requestedTab : 'overview'

  const [inviteDialogOpen, setInviteDialogOpen] = useState(false)
  const [batchDialogOpen, setBatchDialogOpen] = useState(false)
  const [markPaidDialogOpen, setMarkPaidDialogOpen] = useState(false)
  const [holidayDialogOpen, setHolidayDialogOpen] = useState(false)
  const [employeeDetailOpen, setEmployeeDetailOpen] = useState(false)
  const [suspendDialog, setSuspendDialog] = useState<ActionDialogState>({ open: false, note: '' })
  const [restoreDialog, setRestoreDialog] = useState<ActionDialogState>({ open: false, note: '' })
  const [inviteForm, setInviteForm] = useState({ email: '', first_name: '', last_name: '' })
  const [noteBody, setNoteBody] = useState('')
  const [employeesPage, setEmployeesPage] = useState(1)
  const [employeeStatusFilter, setEmployeeStatusFilter] = useState('')
  const [employeeSearch, setEmployeeSearch] = useState('')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')
  const [editingBatchId, setEditingBatchId] = useState<string | null>(null)
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)
  const [batchPaidAt, setBatchPaidAt] = useState('')
  const [batchForm, setBatchForm] = useState<BatchFormState>(emptyBatchForm)
  const [editingHolidayId, setEditingHolidayId] = useState<string | null>(null)
  const [holidayForm, setHolidayForm] = useState(createDefaultHolidayCalendarForm)

  const { data: organisation, isLoading } = useOrganisation(organisationId)
  const { data: admins } = useOrgAdmins(organisationId, activeTab === 'admins')
  const { data: employees, isLoading: employeesLoading } = useCtOrgEmployees(
    organisationId,
    { page: employeesPage, search: employeeSearch || undefined, status: employeeStatusFilter || undefined },
    activeTab === 'employees',
  )
  const { data: selectedEmployee, isLoading: employeeDetailLoading } = useCtOrgEmployeeDetail(
    organisationId,
    selectedEmployeeId,
    employeeDetailOpen,
  )
  const { data: holidayCalendars, isLoading: holidaysLoading } = useCtHolidayCalendars(
    organisationId,
    activeTab === 'holidays' || holidayDialogOpen,
  )
  const { data: configuration, isLoading: configurationLoading } = useCtOrgConfiguration(
    organisationId,
    activeTab === 'configuration' || holidayDialogOpen,
  )
  const { data: auditLogs } = useCtAuditLogs(organisationId, activeTab === 'audit')
  const { data: notes, isLoading: notesLoading } = useCtOrgNotes(organisationId, activeTab === 'notes')

  const suspendMutation = useSuspendOrganisation()
  const restoreMutation = useRestoreOrganisation()
  const inviteAdminMutation = useInviteOrgAdmin(organisationId)
  const resendInviteMutation = useResendOrgAdminInvite(organisationId)
  const createBatchMutation = useCreateLicenceBatch(organisationId)
  const updateBatchMutation = useUpdateLicenceBatch(organisationId)
  const markBatchPaidMutation = useMarkLicenceBatchPaid(organisationId)
  const createHolidayMutation = useCreateCtHolidayCalendar(organisationId)
  const updateHolidayMutation = useUpdateCtHolidayCalendar(organisationId)
  const publishHolidayMutation = usePublishCtHolidayCalendar(organisationId)
  const createNoteMutation = useCreateCtOrgNote(organisationId)

  const bootstrapAdmin = organisation?.bootstrap_admin ?? organisation?.primary_admin ?? null
  const additionalAdmins = useMemo(
    () =>
      (admins ?? []).filter(
        (admin) => !bootstrapAdmin || admin.email.toLowerCase() !== bootstrapAdmin.email.toLowerCase()
      ),
    [admins, bootstrapAdmin],
  )

  const completedSteps = useMemo(() => {
    const currentIndex = ORG_ONBOARDING_STEPS.findIndex((step) => step.id === organisation?.onboarding_stage)
    return currentIndex >= 0 ? currentIndex : 0
  }, [organisation?.onboarding_stage])

  const onlyDraftBatch =
    organisation?.licence_batches.length === 1 && organisation.licence_batches[0].payment_status === 'DRAFT'
      ? organisation.licence_batches[0]
      : null

  const effectiveBatchForm = useMemo<BatchFormState>(() => {
    if (!organisation || editingBatchId) return batchForm
    return {
      quantity: batchForm.quantity || '1',
      price_per_licence_per_month:
        batchForm.price_per_licence_per_month || organisation.batch_defaults.price_per_licence_per_month,
      start_date: batchForm.start_date || organisation.batch_defaults.start_date,
      end_date: batchForm.end_date || organisation.batch_defaults.end_date,
      note: batchForm.note,
    }
  }, [batchForm, editingBatchId, organisation])

  const pricingPreview = useMemo(() => {
    const months = calculateBillingMonths(effectiveBatchForm.start_date, effectiveBatchForm.end_date)
    const quantity = Number(effectiveBatchForm.quantity || 0)
    const price = Number(effectiveBatchForm.price_per_licence_per_month || 0)
    return {
      billingMonths: months,
      totalAmount: quantity * price * months,
    }
  }, [effectiveBatchForm])

  const locationOptions =
    configuration?.locations
      .filter((location) => location.is_active)
      .map((location) => ({
        value: location.id,
        label: location.name,
        hint: location.organisation_address ? `${location.organisation_address.label} • ${location.city}` : 'No linked address',
      })) ?? []

  const tabSelectOptions = TAB_OPTIONS.map((tab) => ({ value: tab.key, label: tab.label }))
  const employeeStatusOptions = [
    { value: '', label: 'All statuses' },
    { value: 'INVITED', label: 'Invited' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'ACTIVE', label: 'Active' },
    { value: 'RESIGNED', label: 'Resigned' },
    { value: 'RETIRED', label: 'Retired' },
    { value: 'TERMINATED', label: 'Terminated' },
  ]
  const holidayClassificationOptions = HOLIDAY_CLASSIFICATION_OPTIONS.map((classification) => ({
    value: classification,
    label: startCase(classification),
  }))
  const holidaySessionOptions = HOLIDAY_SESSION_OPTIONS.map((session) => ({
    value: session,
    label: startCase(session),
  }))

  const setActiveTab = (tab: DetailTabKey) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tab)
    setSearchParams(next, { replace: true })
  }

  const resetBatchDialog = () => {
    setEditingBatchId(null)
    setSelectedBatchId(null)
    setBatchPaidAt('')
    setBatchForm(emptyBatchForm())
    setBatchDialogOpen(false)
    setMarkPaidDialogOpen(false)
  }

  const openCreateBatchDialog = () => {
    setEditingBatchId(null)
    setBatchForm(emptyBatchForm())
    setBatchDialogOpen(true)
  }

  const openEditBatchDialog = (batch: LicenceBatch) => {
    setEditingBatchId(batch.id)
    setBatchForm({
      quantity: String(batch.quantity),
      price_per_licence_per_month: batch.price_per_licence_per_month,
      start_date: batch.start_date,
      end_date: batch.end_date,
      note: batch.note,
    })
    setBatchDialogOpen(true)
  }

  const openMarkPaidDialog = (batchId: string) => {
    setSelectedBatchId(batchId)
    setBatchPaidAt('')
    setMarkPaidDialogOpen(true)
  }

  const openHolidayDialog = (calendar?: HolidayCalendar) => {
    setEditingHolidayId(calendar?.id ?? null)
    setHolidayForm(createHolidayFormState(calendar))
    setHolidayDialogOpen(true)
  }

  const handleInviteAdmin = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await inviteAdminMutation.mutateAsync(inviteForm)
      toast.success('Organisation admin invite sent.')
      setInviteForm({ email: '', first_name: '', last_name: '' })
      setInviteDialogOpen(false)
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

  const handleSaveBatch = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      quantity: Number(effectiveBatchForm.quantity),
      price_per_licence_per_month: effectiveBatchForm.price_per_licence_per_month,
      start_date: effectiveBatchForm.start_date,
      end_date: effectiveBatchForm.end_date,
      note: effectiveBatchForm.note,
    }
    try {
      if (editingBatchId) {
        await updateBatchMutation.mutateAsync({ batchId: editingBatchId, payload })
        toast.success('Draft batch updated.')
      } else {
        await createBatchMutation.mutateAsync(payload)
        toast.success('Draft batch created.')
      }
      resetBatchDialog()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save licence batch.'))
    }
  }

  const handleMarkBatchPaid = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!selectedBatchId) return
    try {
      await markBatchPaidMutation.mutateAsync({
        batchId: selectedBatchId,
        paidAt: batchPaidAt || undefined,
      })
      toast.success(
        organisation?.status === 'PENDING'
          ? 'Batch marked paid. The onboarding email has been queued for the primary admin.'
          : 'Batch marked paid.',
      )
      resetBatchDialog()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to mark this batch as paid.'))
    }
  }

  const handleSuspend = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!organisation) return
    try {
      await suspendMutation.mutateAsync({ id: organisation.id, note: suspendDialog.note })
      toast.success('Organisation suspended.')
      setSuspendDialog({ open: false, note: '' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to suspend organisation.'))
    }
  }

  const handleRestore = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!organisation) return
    try {
      await restoreMutation.mutateAsync({ id: organisation.id, note: restoreDialog.note })
      toast.success('Organisation restored.')
      setRestoreDialog({ open: false, note: '' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to restore organisation.'))
    }
  }

  const handleSaveHolidayCalendar = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingHolidayId) {
        await updateHolidayMutation.mutateAsync({ calendarId: editingHolidayId, payload: holidayForm })
        toast.success('Holiday calendar updated.')
      } else {
        await createHolidayMutation.mutateAsync(holidayForm)
        toast.success('Holiday calendar created.')
      }
      setHolidayDialogOpen(false)
      setEditingHolidayId(null)
      setHolidayForm(createDefaultHolidayCalendarForm())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save holiday calendar.'))
    }
  }

  const handlePublishHolidayCalendar = async (calendarId: string) => {
    try {
      await publishHolidayMutation.mutateAsync(calendarId)
      toast.success('Holiday calendar published.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to publish holiday calendar.'))
    }
  }

  const handleCreateNote = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createNoteMutation.mutateAsync(noteBody.trim())
      toast.success('Note added.')
      setNoteBody('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to add note.'))
    }
  }

  if (isLoading || !organisation) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonMetricCard key={index} />
          ))}
        </div>
        <SkeletonFormBlock rows={5} />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const renderOverviewTab = () => (
    <div className="space-y-6">
      <SectionCard
        title="Access state and onboarding"
        description="Track where this organisation sits across billing, activation, and onboarding."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          <DetailMetric
            label="Lifecycle status"
            value={startCase(organisation.status)}
            helper={`Updated ${formatDateTime(organisation.updated_at)}`}
          />
          <DetailMetric
            label="Billing status"
            value={startCase(organisation.billing_status)}
            helper={organisation.paid_marked_at ? `Paid ${formatDateTime(organisation.paid_marked_at)}` : 'Payment not confirmed'}
          />
          <DetailMetric
            label="Access state"
            value={startCase(organisation.access_state)}
            helper={
              organisation.suspended_at
                ? `Suspended ${formatDateTime(organisation.suspended_at)}`
                : organisation.activated_at
                  ? `Activated ${formatDateTime(organisation.activated_at)}`
                  : 'Awaiting activation'
            }
          />
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {ORG_ONBOARDING_STEPS.map((step, index) => (
            <div
              key={step.id}
              className={`rounded-[22px] border px-4 py-4 ${
                index <= completedSteps
                  ? 'border-[hsl(var(--brand)_/_0.3)] bg-[hsl(var(--brand)_/_0.08)]'
                  : 'border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface-subtle))]'
              }`}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                Step {index + 1}
              </p>
              <p className="mt-2 text-sm font-semibold text-[hsl(var(--foreground-strong))]">{step.label}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Commercial and workforce snapshot" description="Seat allocation, admin presence, and org activity at a glance.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DetailMetric
            label="Active paid seats"
            value={String(organisation.licence_summary.active_paid_quantity)}
            helper={`${organisation.licence_summary.available} available`}
          />
          <DetailMetric
            label="Allocated employees"
            value={String(organisation.licence_summary.allocated)}
            helper={organisation.licence_summary.has_overage ? `${organisation.licence_summary.overage} overage` : 'Within licence capacity'}
          />
          <DetailMetric label="Org admins" value={String(organisation.admin_count)} helper="Bootstrap and additional admins" />
          <DetailMetric label="Notes" value={String(organisation.note_count)} helper="Control Tower internal notes" />
        </div>
      </SectionCard>
    </div>
  )

  const renderDetailsTab = () => (
    <div className="space-y-6">
      <SectionCard title="Legal profile" description="Core organisation identity, geography, and commercial defaults.">
        <InfoStack
          items={[
            { label: 'Organisation name', value: organisation.name },
            { label: 'Slug', value: organisation.slug },
            { label: 'Entity type', value: organisation.entity_type_label },
            { label: 'PAN', value: organisation.pan_number },
            { label: 'Country', value: organisation.country_code },
            { label: 'Currency', value: organisation.currency },
            { label: 'Created by', value: organisation.created_by_email },
            { label: 'Created at', value: formatDateTime(organisation.created_at) },
          ]}
        />
      </SectionCard>

      <SectionCard title="Address directory" description="Registered, billing, and operational addresses saved for this organisation.">
        <div className="grid gap-4 xl:grid-cols-2">
          {organisation.addresses.map((address) => (
            <DetailListCard
              key={address.id}
              title={address.label || address.address_type_label}
              footer={
                <div className="flex flex-wrap gap-2">
                  <StatusBadge tone={address.is_active ? 'success' : 'warning'}>
                    {address.is_active ? 'Active' : 'Inactive'}
                  </StatusBadge>
                  {address.gstin ? <StatusBadge tone="info">{address.gstin}</StatusBadge> : null}
                </div>
              }
            >
              <p>{[address.line1, address.line2].filter(Boolean).join(', ')}</p>
              <p>{[address.city, address.state, address.country, address.pincode].filter(Boolean).join(', ')}</p>
            </DetailListCard>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Tax registrations" description="Primary legal and billing identifiers captured against the organisation.">
        <div className="grid gap-4 xl:grid-cols-2">
          <DetailListCard title="Legal identifiers">
            {organisation.legal_identifiers.length > 0 ? (
              organisation.legal_identifiers.map((identifier) => (
                <p key={identifier.id}>
                  {identifier.identifier_type_label}: {identifier.identifier}
                  {identifier.is_primary ? ' • Primary' : ''}
                </p>
              ))
            ) : (
              <p>No legal identifiers captured.</p>
            )}
          </DetailListCard>
          <DetailListCard title="Tax registrations">
            {organisation.tax_registrations.length > 0 ? (
              organisation.tax_registrations.map((registration) => (
                <p key={registration.id}>
                  {registration.registration_type_label}: {registration.identifier}
                  {registration.state_code ? ` • ${registration.state_code}` : ''}
                  {registration.is_primary_billing ? ' • Primary billing' : ''}
                </p>
              ))
            ) : (
              <p>No tax registrations captured.</p>
            )}
          </DetailListCard>
        </div>
      </SectionCard>
    </div>
  )

  const renderLicencesTab = () => (
    <div className="space-y-6">
      <SectionCard
        title="Seat summary"
        description="Track paid capacity, allocated employees, and utilisation."
        action={
          <button type="button" className="btn-primary" onClick={openCreateBatchDialog}>
            <CreditCard className="h-4 w-4" />
            Create new batch
          </button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DetailMetric label="Paid seats" value={String(organisation.licence_summary.active_paid_quantity)} />
          <DetailMetric label="Allocated" value={String(organisation.licence_summary.allocated)} />
          <DetailMetric label="Available" value={String(organisation.licence_summary.available)} />
          <DetailMetric
            label="Utilisation"
            value={`${organisation.licence_summary.utilisation_percent}%`}
            helper={
              organisation.licence_summary.has_overage
                ? `${organisation.licence_summary.overage} employees over capacity`
                : 'No overage'
            }
          />
        </div>
      </SectionCard>

      <SectionCard title="Licence batches" description="Draft batches stay editable until paid. Paid batches become read-only records.">
        {organisation.licence_batches.length > 0 ? (
          <div className="space-y-3">
            {organisation.licence_batches.map((batch) => (
              <div key={batch.id} className="surface-muted rounded-[24px] p-4">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">
                        {batch.quantity} licences • {formatMoney(batch.total_amount, organisation.currency)}
                      </p>
                      <StatusBadge tone={batch.payment_status === 'PAID' ? 'success' : 'warning'}>
                        {batch.payment_status}
                      </StatusBadge>
                      <StatusBadge tone={batch.lifecycle_state === 'ACTIVE' ? 'success' : batch.lifecycle_state === 'EXPIRED' ? 'warning' : 'info'}>
                        {startCase(batch.lifecycle_state)}
                      </StatusBadge>
                    </div>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(batch.start_date)} to {formatDate(batch.end_date)} • {batch.billing_months} billing months
                    </p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatMoney(batch.price_per_licence_per_month, organisation.currency)} per licence per month
                    </p>
                    {batch.note ? <p className="text-sm text-[hsl(var(--muted-foreground))]">{batch.note}</p> : null}
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {batch.payment_status === 'DRAFT' ? (
                      <>
                        <button type="button" className="btn-secondary" onClick={() => openEditBatchDialog(batch)}>
                          Edit draft
                        </button>
                        <button type="button" className="btn-primary" onClick={() => openMarkPaidDialog(batch.id)}>
                          Mark paid
                        </button>
                      </>
                    ) : (
                      <div className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                        Paid {formatDate(batch.paid_at)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No licence batches yet"
            description="Create the first commercial batch to start commercial tracking and onboarding."
            icon={BadgeDollarSign}
            action={
              <button type="button" className="btn-primary" onClick={openCreateBatchDialog}>
                Create new batch
              </button>
            }
          />
        )}
      </SectionCard>
    </div>
  )

  const renderAdminsTab = () => (
    <div className="space-y-6">
      <SectionCard
        title="Bootstrap admin"
        description="Primary organisation admin bootstrap details captured during org creation."
        action={
          <button type="button" className="btn-secondary" onClick={() => setInviteDialogOpen(true)}>
            <UserPlus className="h-4 w-4" />
            Invite additional admin
          </button>
        }
      >
        {bootstrapAdmin ? (
          <div className="surface-muted rounded-[24px] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">{bootstrapAdmin.full_name}</p>
              <StatusBadge
                tone={
                  bootstrapAdmin.status === 'INVITE_ACCEPTED'
                    ? 'success'
                    : bootstrapAdmin.status === 'INVITE_PENDING'
                      ? 'warning'
                      : 'neutral'
                }
              >
                {startCase(bootstrapAdmin.status)}
              </StatusBadge>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Email</p>
                <p className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{bootstrapAdmin.email}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Phone</p>
                <p className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{bootstrapAdmin.phone || 'Not set'}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Invite sent</p>
                <p className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDateTime(bootstrapAdmin.invitation_sent_at)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Accepted</p>
                <p className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDateTime(bootstrapAdmin.accepted_at)}</p>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="Bootstrap admin not configured"
            description="This organisation does not yet have a bootstrap admin profile attached."
            icon={Mail}
          />
        )}
      </SectionCard>

      <SectionCard title="Additional admins" description="All organisation admins with Control Tower visibility into invite state and membership.">
        {admins ? (
          additionalAdmins.length > 0 ? (
            <div className="space-y-3">
              {additionalAdmins.map((admin) => (
                <div key={admin.id} className="surface-muted flex flex-col gap-4 rounded-[24px] p-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{admin.full_name || admin.email}</p>
                      <StatusBadge tone={admin.is_active ? 'success' : 'warning'}>
                        {admin.is_active ? 'Active' : 'Inactive'}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{admin.email}</p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {admin.is_onboarding_email_sent ? (
                      <button type="button" className="btn-secondary" onClick={() => handleResendInvite(admin.id)}>
                        Resend invite
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No additional org admins"
              description="Invite more organisation admins when support or delegated operations are needed."
              icon={Users}
              action={
                <button type="button" className="btn-primary" onClick={() => setInviteDialogOpen(true)}>
                  Invite admin
                </button>
              }
            />
          )
        ) : (
          <SkeletonTable rows={4} />
        )}
      </SectionCard>
    </div>
  )

  const renderEmployeesTab = () => (
    <div className="space-y-6">
      <SectionCard title="Employee directory" description="Read-only CT visibility into the workforce for this organisation.">
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.9fr_auto]">
          <input
            className="field-input"
            placeholder="Search employee code, email, or name"
            value={employeeSearch}
            onChange={(event) => {
              setEmployeeSearch(event.target.value)
              setEmployeesPage(1)
            }}
          />
          <AppSelect
            value={employeeStatusFilter}
            onValueChange={(value) => {
              setEmployeeStatusFilter(value)
              setEmployeesPage(1)
            }}
            options={employeeStatusOptions}
            placeholder="All statuses"
          />
          <div className="flex items-center justify-end text-sm text-[hsl(var(--muted-foreground))]">
            {employees?.count ?? 0} employees
          </div>
        </div>

        <div className="mt-5">
          {employeesLoading ? (
            <SkeletonTable rows={6} />
          ) : employees && employees.results.length > 0 ? (
            <div className="space-y-3">
              {employees.results.map((employee) => (
                <div key={employee.id} className="surface-muted rounded-[24px] p-4">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{employee.full_name}</p>
                        <StatusBadge
                          tone={
                            employee.status === 'ACTIVE'
                              ? 'success'
                              : employee.status === 'PENDING' || employee.status === 'INVITED'
                                ? 'warning'
                                : 'neutral'
                          }
                        >
                          {employee.status}
                        </StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{employee.email}</p>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {employee.designation || 'No designation'} • {employee.department_name || 'No department'} • {employee.office_location_name || 'No location'}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setSelectedEmployeeId(employee.id)
                          setEmployeeDetailOpen(true)
                        }}
                      >
                        View employee
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No employees found"
              description="Employees will appear here once the organisation admin begins onboarding the workforce."
              icon={Users}
            />
          )}
        </div>

        {employees && employees.count > 0 ? (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Page {employeesPage}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                className="btn-secondary"
                disabled={!employees.previous}
                onClick={() => setEmployeesPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={!employees.next}
                onClick={() => setEmployeesPage((current) => current + 1)}
              >
                Next
              </button>
            </div>
          </div>
        ) : null}
      </SectionCard>
    </div>
  )

  const renderHolidaysTab = () => (
    <div className="space-y-6">
      <SectionCard
        title="Holiday calendars"
        description="Control Tower can create, update, and publish calendars while reviewing location assignments."
        action={
          <button type="button" className="btn-primary" onClick={() => openHolidayDialog()}>
            <CalendarDays className="h-4 w-4" />
            Create calendar
          </button>
        }
      >
        {holidaysLoading ? (
          <SkeletonTable rows={5} />
        ) : holidayCalendars && holidayCalendars.length > 0 ? (
          <div className="space-y-3">
            {holidayCalendars.map((calendar) => (
              <div key={calendar.id} className="surface-muted rounded-[24px] p-4">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{calendar.name}</p>
                      <StatusBadge tone={calendar.status === 'PUBLISHED' ? 'success' : 'warning'}>
                        {calendar.status}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {calendar.year} • {calendar.holidays.length} holidays • {calendar.location_ids.length || 'All'} locations
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {calendar.holidays.map((holiday) => (
                        <StatusBadge
                          key={holiday.id}
                          tone={holiday.classification === 'PUBLIC' ? 'success' : holiday.classification === 'RESTRICTED' ? 'warning' : 'info'}
                        >
                          {holiday.name}
                        </StatusBadge>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button type="button" className="btn-secondary" onClick={() => openHolidayDialog(calendar)}>
                      Edit
                    </button>
                    {calendar.status !== 'PUBLISHED' ? (
                      <button type="button" className="btn-primary" onClick={() => handlePublishHolidayCalendar(calendar.id)}>
                        Publish
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No holiday calendars yet"
            description="Create a holiday calendar so Control Tower can review and publish location-specific holiday plans."
            icon={CalendarDays}
            action={
              <button type="button" className="btn-primary" onClick={() => openHolidayDialog()}>
                Create calendar
              </button>
            }
          />
        )}
      </SectionCard>
    </div>
  )

  const renderConfigurationTab = () => (
    <div className="space-y-6">
      <SectionCard title="Workplace structure" description="Locations and departments configured for this tenant.">
        {configurationLoading ? (
          <SkeletonTable rows={5} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <DetailListCard title={`Locations (${configuration?.locations.length ?? 0})`}>
              {configuration?.locations.length ? (
                configuration.locations.map((location) => (
                  <p key={location.id}>
                    {location.name} • {location.is_remote ? 'Remote' : 'Office'} • {location.is_active ? 'Active' : 'Inactive'}
                  </p>
                ))
              ) : (
                <p>No office locations configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`Departments (${configuration?.departments.length ?? 0})`}>
              {configuration?.departments.length ? (
                configuration.departments.map((department) => (
                  <p key={department.id}>
                    {department.name}
                    {department.parent_department_name ? ` • Parent: ${department.parent_department_name}` : ' • Top level'}
                    {department.is_active ? ' • Active' : ' • Inactive'}
                  </p>
                ))
              ) : (
                <p>No departments configured.</p>
              )}
            </DetailListCard>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Leave and attendance configuration" description="Leave cycles, plans, and on-duty policies visible to Control Tower.">
        {configurationLoading ? (
          <SkeletonTable rows={5} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-3">
            <DetailListCard title={`Leave cycles (${configuration?.leave_cycles.length ?? 0})`}>
              {configuration?.leave_cycles.length ? (
                configuration.leave_cycles.map((cycle) => (
                  <p key={cycle.id}>
                    {cycle.name} • {startCase(cycle.cycle_type)}
                    {cycle.is_default ? ' • Default' : ''}
                  </p>
                ))
              ) : (
                <p>No leave cycles configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`Leave plans (${configuration?.leave_plans.length ?? 0})`}>
              {configuration?.leave_plans.length ? (
                configuration.leave_plans.map((plan) => (
                  <p key={plan.id}>
                    {plan.name} • {plan.leave_cycle?.name || 'No cycle'} • {plan.leave_types.length} leave types
                  </p>
                ))
              ) : (
                <p>No leave plans configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`On-duty policies (${configuration?.on_duty_policies.length ?? 0})`}>
              {configuration?.on_duty_policies.length ? (
                configuration.on_duty_policies.map((policy) => (
                  <p key={policy.id}>
                    {policy.name}
                    {policy.is_default ? ' • Default' : ''}
                    {policy.is_active ? ' • Active' : ' • Inactive'}
                  </p>
                ))
              ) : (
                <p>No on-duty policies configured.</p>
              )}
            </DetailListCard>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Approvals and communication" description="Approval workflow routing and employee noticeboard visibility from Control Tower.">
        {configurationLoading ? (
          <SkeletonTable rows={5} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <DetailListCard title={`Approval workflows (${configuration?.approval_workflows.length ?? 0})`}>
              {configuration?.approval_workflows.length ? (
                configuration.approval_workflows.map((workflow) => (
                  <p key={workflow.id}>
                    {workflow.name} • {workflow.rules.length} rules • {workflow.stages.length} stages
                    {workflow.is_default ? ' • Default' : ''}
                  </p>
                ))
              ) : (
                <p>No approval workflows configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`Notices (${configuration?.notices.length ?? 0})`}>
              {configuration?.notices.length ? (
                configuration.notices.map((notice) => (
                  <p key={notice.id}>
                    {notice.title} • {startCase(notice.status)}
                    {notice.published_at ? ` • ${formatDateTime(notice.published_at)}` : ''}
                  </p>
                ))
              ) : (
                <p>No notices configured.</p>
              )}
            </DetailListCard>
          </div>
        )}
      </SectionCard>
    </div>
  )

  const renderAuditTab = () => (
    <SectionCard title="Audit timeline" description="Complete organisation-level audit activity visible to Control Tower.">
      <AuditTimeline
        entries={auditLogs?.results}
        emptyTitle="No audit activity yet"
        emptyDescription="Audit events will appear here as Control Tower and org users act inside this tenant."
      />
    </SectionCard>
  )

  const renderNotesTab = () => (
    <div className="space-y-6">
      <SectionCard title="Control Tower notes" description="Append-only operational notes for this organisation.">
        <form onSubmit={handleCreateNote} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="organisation-note">
              Add note
            </label>
            <textarea
              id="organisation-note"
              className="field-textarea"
              placeholder="Record a follow-up, payment conversation, escalation, or operational context."
              value={noteBody}
              onChange={(event) => setNoteBody(event.target.value)}
              required
            />
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={createNoteMutation.isPending || !noteBody.trim()}>
              Add note
            </button>
          </div>
        </form>
      </SectionCard>

      <SectionCard title="Notes history" description="Newest first, with author and timestamp preserved for every note.">
        {notesLoading ? (
          <SkeletonTable rows={5} />
        ) : notes && notes.length > 0 ? (
          <div className="space-y-3">
            {notes.map((note) => (
              <div key={note.id} className="surface-muted rounded-[24px] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">
                      {note.created_by.full_name || note.created_by.email}
                    </p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{note.created_by.email}</p>
                  </div>
                  <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                    {formatDateTime(note.created_at)}
                  </p>
                </div>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-[hsl(var(--foreground-strong))]">{note.body}</p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No notes yet"
            description="Add the first Control Tower note to capture operational context for this organisation."
            icon={MessageSquare}
          />
        )}
      </SectionCard>
    </div>
  )

  return (
    <div className="space-y-6">
      <Link
        to="/ct/organisations"
        className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to organisations
      </Link>

      <PageHeader
        eyebrow="Organisation detail"
        title={organisation.name}
        description={`Tenant ${organisation.slug} is ${startCase(organisation.status)} with ${organisation.licence_summary.allocated} allocated employees against ${organisation.licence_summary.active_paid_quantity} active paid seats.`}
        actions={
          <>
            {onlyDraftBatch ? (
              <button type="button" className="btn-primary" onClick={() => openMarkPaidDialog(onlyDraftBatch.id)}>
                Mark paid & send onboarding
              </button>
            ) : null}
            <button type="button" className="btn-secondary" onClick={openCreateBatchDialog}>
              Create new batch
            </button>
            <button type="button" className="btn-secondary" onClick={() => setInviteDialogOpen(true)}>
              Invite admin
            </button>
            {organisation.status === 'ACTIVE' ? (
              <button type="button" className="btn-danger" onClick={() => setSuspendDialog({ open: true, note: '' })}>
                Suspend access
              </button>
            ) : null}
            {organisation.status === 'SUSPENDED' ? (
              <button type="button" className="btn-primary" onClick={() => setRestoreDialog({ open: true, note: '' })}>
                Restore access
              </button>
            ) : null}
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DetailMetric label="Status" value={startCase(organisation.status)} helper={`Onboarding: ${startCase(organisation.onboarding_stage)}`} />
        <DetailMetric label="Billing" value={startCase(organisation.billing_status)} helper={`Access: ${startCase(organisation.access_state)}`} />
        <DetailMetric label="Employees" value={String(organisation.employee_count)} helper={`${organisation.admin_count} org admins`} />
        <DetailMetric label="Holiday calendars" value={String(organisation.holiday_calendar_count)} helper={`${organisation.note_count} CT notes`} />
      </div>

      <div className="md:hidden">
        <AppSelect value={activeTab} onValueChange={(value) => setActiveTab(value as DetailTabKey)} options={tabSelectOptions} />
      </div>

      <div className="hidden md:flex md:flex-wrap md:gap-2">
        {TAB_OPTIONS.map((tab) => {
          const Icon = tab.icon
          const isActive = tab.key === activeTab
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
                isActive
                  ? 'border-[hsl(var(--brand)_/_0.35)] bg-[hsl(var(--brand)_/_0.12)] text-[hsl(var(--foreground-strong))]'
                  : 'border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {activeTab === 'overview' ? renderOverviewTab() : null}
      {activeTab === 'details' ? renderDetailsTab() : null}
      {activeTab === 'licences' ? renderLicencesTab() : null}
      {activeTab === 'admins' ? renderAdminsTab() : null}
      {activeTab === 'employees' ? renderEmployeesTab() : null}
      {activeTab === 'holidays' ? renderHolidaysTab() : null}
      {activeTab === 'configuration' ? renderConfigurationTab() : null}
      {activeTab === 'audit' ? renderAuditTab() : null}
      {activeTab === 'notes' ? renderNotesTab() : null}

      <AppDialog
        open={batchDialogOpen}
        onOpenChange={(open) => {
          if (!open) resetBatchDialog()
          else setBatchDialogOpen(true)
        }}
        title={editingBatchId ? 'Edit draft licence batch' : 'Create licence batch'}
        description="Draft batches stay editable until payment is confirmed."
      >
        <form onSubmit={handleSaveBatch} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="batch-quantity">
                Quantity
              </label>
              <input
                id="batch-quantity"
                className="field-input"
                type="number"
                min={1}
                value={effectiveBatchForm.quantity}
                onChange={(event) => setBatchForm((current) => ({ ...current, quantity: event.target.value }))}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="batch-price">
                Price per licence per month
              </label>
              <input
                id="batch-price"
                className="field-input"
                type="number"
                min={0}
                step="0.01"
                value={effectiveBatchForm.price_per_licence_per_month}
                onChange={(event) =>
                  setBatchForm((current) => ({ ...current, price_per_licence_per_month: event.target.value }))
                }
                required
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label">Start date</label>
              <AppDatePicker
                value={effectiveBatchForm.start_date}
                onValueChange={(value) => setBatchForm((current) => ({ ...current, start_date: value }))}
                placeholder="Select start date"
              />
            </div>
            <div>
              <label className="field-label">End date</label>
              <AppDatePicker
                value={effectiveBatchForm.end_date}
                onValueChange={(value) => setBatchForm((current) => ({ ...current, end_date: value }))}
                placeholder="Select end date"
              />
            </div>
          </div>
          <div className="surface-muted rounded-[22px] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Commercial preview</p>
            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
              {pricingPreview.billingMonths} billing months • {formatMoney(pricingPreview.totalAmount, organisation.currency)}
            </p>
          </div>
          <div>
            <label className="field-label" htmlFor="batch-note">
              Note
            </label>
            <textarea
              id="batch-note"
              className="field-textarea"
              value={effectiveBatchForm.note}
              onChange={(event) => setBatchForm((current) => ({ ...current, note: event.target.value }))}
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetBatchDialog}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createBatchMutation.isPending || updateBatchMutation.isPending}>
              {editingBatchId ? 'Save draft' : 'Create batch'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={markPaidDialogOpen}
        onOpenChange={(open) => {
          if (!open) resetBatchDialog()
          else setMarkPaidDialogOpen(true)
        }}
        title="Mark batch paid"
        description="Once marked paid, the batch becomes read-only. If this is the first paid batch, onboarding is sent automatically."
      >
        <form onSubmit={handleMarkBatchPaid} className="grid gap-4">
          <div>
            <label className="field-label">Paid date</label>
            <AppDatePicker value={batchPaidAt} onValueChange={setBatchPaidAt} placeholder="Use today or select a date" />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetBatchDialog}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={markBatchPaidMutation.isPending}>
              Mark paid
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={inviteDialogOpen}
        onOpenChange={setInviteDialogOpen}
        title="Invite organisation admin"
        description="Invite another administrator for this organisation."
      >
        <form onSubmit={handleInviteAdmin} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="invite-first-name">
                First name
              </label>
              <input
                id="invite-first-name"
                className="field-input"
                value={inviteForm.first_name}
                onChange={(event) => setInviteForm((current) => ({ ...current, first_name: event.target.value }))}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="invite-last-name">
                Last name
              </label>
              <input
                id="invite-last-name"
                className="field-input"
                value={inviteForm.last_name}
                onChange={(event) => setInviteForm((current) => ({ ...current, last_name: event.target.value }))}
                required
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="invite-email">
              Email
            </label>
            <input
              id="invite-email"
              className="field-input"
              type="email"
              value={inviteForm.email}
              onChange={(event) => setInviteForm((current) => ({ ...current, email: event.target.value }))}
              required
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setInviteDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={inviteAdminMutation.isPending}>
              Send invite
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={holidayDialogOpen}
        onOpenChange={(open) => {
          setHolidayDialogOpen(open)
          if (!open) {
            setEditingHolidayId(null)
            setHolidayForm(createDefaultHolidayCalendarForm())
          }
        }}
        title={editingHolidayId ? 'Edit holiday calendar' : 'Create holiday calendar'}
        description="Date-based annual holiday calendars with optional office-location assignments."
        contentClassName="sm:w-[min(94vw,52rem)]"
      >
        <form onSubmit={handleSaveHolidayCalendar} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="holiday-calendar-name">
                Calendar name
              </label>
              <input
                id="holiday-calendar-name"
                className="field-input"
                value={holidayForm.name}
                onChange={(event) => setHolidayForm((current) => ({ ...current, name: event.target.value }))}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="holiday-calendar-year">
                Year
              </label>
              <input
                id="holiday-calendar-year"
                className="field-input"
                type="number"
                min={2000}
                max={2100}
                value={holidayForm.year}
                onChange={(event) => setHolidayForm((current) => ({ ...current, year: Number(event.target.value) }))}
                required
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="holiday-calendar-description">
              Description
            </label>
            <textarea
              id="holiday-calendar-description"
              className="field-textarea"
              value={holidayForm.description}
              onChange={(event) => setHolidayForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div className="grid gap-2">
            <p className="field-label">Assigned office locations</p>
            <div className="grid gap-2 md:grid-cols-2">
              {locationOptions.map((location) => (
                <label key={location.value} className="surface-muted flex items-start gap-3 rounded-[18px] px-3 py-3 text-sm">
                  <input
                    type="checkbox"
                    checked={holidayForm.location_ids.includes(location.value)}
                    onChange={(event) =>
                      setHolidayForm((current) => ({
                        ...current,
                        location_ids: event.target.checked
                          ? [...current.location_ids, location.value]
                          : current.location_ids.filter((id) => id !== location.value),
                      }))
                    }
                  />
                  <span>
                    <span className="block font-medium text-[hsl(var(--foreground-strong))]">{location.label}</span>
                    {location.hint ? <span className="mt-1 block text-xs text-[hsl(var(--muted-foreground))]">{location.hint}</span> : null}
                  </span>
                </label>
              ))}
              {locationOptions.length === 0 ? (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">No active office locations available for assignment.</p>
              ) : null}
            </div>
          </div>
          <div className="space-y-3">
            {holidayForm.holidays.map((holiday, index) => (
              <div key={`${holiday.name || 'holiday'}-${index}`} className="surface-muted rounded-[22px] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">Holiday entry {index + 1}</p>
                  <button
                    type="button"
                    className="text-sm font-medium text-[hsl(var(--danger))] disabled:opacity-40"
                    disabled={holidayForm.holidays.length === 1}
                    onClick={() =>
                      setHolidayForm((current) => ({
                        ...current,
                        holidays: current.holidays.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }
                  >
                    Remove
                  </button>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="field-label">Holiday name</label>
                    <input
                      className="field-input"
                      value={holiday.name}
                      onChange={(event) =>
                        setHolidayForm((current) => ({
                          ...current,
                          holidays: current.holidays.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, name: event.target.value } : item,
                          ),
                        }))
                      }
                      required
                    />
                  </div>
                  <div>
                    <label className="field-label">Holiday date</label>
                    <AppDatePicker
                      value={holiday.holiday_date}
                      onValueChange={(value) =>
                        setHolidayForm((current) => ({
                          ...current,
                          holidays: current.holidays.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, holiday_date: value } : item,
                          ),
                        }))
                      }
                      placeholder="Select holiday date"
                    />
                  </div>
                  <div>
                    <label className="field-label">Classification</label>
                    <AppSelect
                      value={holiday.classification}
                      onValueChange={(value) =>
                        setHolidayForm((current) => ({
                          ...current,
                          holidays: current.holidays.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, classification: value } : item,
                          ),
                        }))
                      }
                      options={holidayClassificationOptions}
                    />
                  </div>
                  <div>
                    <label className="field-label">Session</label>
                    <AppSelect
                      value={holiday.session}
                      onValueChange={(value) =>
                        setHolidayForm((current) => ({
                          ...current,
                          holidays: current.holidays.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, session: value } : item,
                          ),
                        }))
                      }
                      options={holidaySessionOptions}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              setHolidayForm((current) => ({
                ...current,
                holidays: [...current.holidays, { name: '', holiday_date: '', classification: 'PUBLIC', session: 'FULL_DAY', description: '' }],
              }))
            }
          >
            Add holiday
          </button>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setHolidayDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createHolidayMutation.isPending || updateHolidayMutation.isPending}>
              {editingHolidayId ? 'Save changes' : 'Save calendar'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={employeeDetailOpen}
        onOpenChange={(open) => {
          setEmployeeDetailOpen(open)
          if (!open) setSelectedEmployeeId('')
        }}
        title={selectedEmployee?.full_name || 'Employee details'}
        description="Read-only employee visibility from Control Tower."
      >
        {employeeDetailLoading || !selectedEmployee ? (
          <SkeletonFormBlock rows={5} />
        ) : (
          <div className="space-y-5">
            <InfoStack
              items={[
                { label: 'Email', value: selectedEmployee.email },
                { label: 'Status', value: startCase(selectedEmployee.status) },
                { label: 'Onboarding', value: startCase(selectedEmployee.onboarding_status) },
                { label: 'Designation', value: selectedEmployee.designation },
                { label: 'Department', value: selectedEmployee.department },
                { label: 'Office location', value: selectedEmployee.office_location },
                { label: 'Reporting to', value: selectedEmployee.reporting_to },
                { label: 'Date of joining', value: formatDate(selectedEmployee.date_of_joining) },
              ]}
            />
            {selectedEmployee.profile ? (
              <SectionCard title="Profile summary" description="Basic contact and address data captured by the employee.">
                <InfoStack
                  items={[
                    { label: 'Phone', value: selectedEmployee.profile.phone_personal },
                    { label: 'Nationality', value: selectedEmployee.profile.nationality },
                    { label: 'Blood type', value: startCase(selectedEmployee.profile.blood_type || '') },
                    {
                      label: 'Address',
                      value: [
                        selectedEmployee.profile.address_line1,
                        selectedEmployee.profile.address_line2,
                        selectedEmployee.profile.city,
                        selectedEmployee.profile.state,
                        selectedEmployee.profile.country,
                        selectedEmployee.profile.pincode,
                      ]
                        .filter(Boolean)
                        .join(', '),
                    },
                  ]}
                />
              </SectionCard>
            ) : null}
          </div>
        )}
      </AppDialog>

      <AppDialog
        open={suspendDialog.open}
        onOpenChange={(open) => setSuspendDialog((current) => ({ ...current, open }))}
        title="Suspend organisation"
        description="Suspending blocks organisation access until restored."
      >
        <form onSubmit={handleSuspend} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="suspend-note">
              Action note (optional)
            </label>
            <textarea
              id="suspend-note"
              className="field-textarea"
              value={suspendDialog.note}
              onChange={(event) => setSuspendDialog((current) => ({ ...current, note: event.target.value }))}
              placeholder="Capture why access is being suspended."
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setSuspendDialog({ open: false, note: '' })}>
              Cancel
            </button>
            <button type="submit" className="btn-danger" disabled={suspendMutation.isPending}>
              Suspend access
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={restoreDialog.open}
        onOpenChange={(open) => setRestoreDialog((current) => ({ ...current, open }))}
        title="Restore organisation"
        description="Restoring reopens access according to the organisation lifecycle state."
      >
        <form onSubmit={handleRestore} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="restore-note">
              Action note (optional)
            </label>
            <textarea
              id="restore-note"
              className="field-textarea"
              value={restoreDialog.note}
              onChange={(event) => setRestoreDialog((current) => ({ ...current, note: event.target.value }))}
              placeholder="Capture why access is being restored."
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setRestoreDialog({ open: false, note: '' })}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={restoreMutation.isPending}>
              Restore access
            </button>
          </div>
        </form>
      </AppDialog>
    </div>
  )
}
