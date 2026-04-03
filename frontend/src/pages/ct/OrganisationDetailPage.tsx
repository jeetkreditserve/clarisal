import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Activity,
  ArrowLeft,
  BadgeDollarSign,
  Building2,
  CalendarDays,
  Clock3,
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
import { AppCheckbox } from '@/components/ui/AppCheckbox'
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
  useCreateCtApprovalWorkflow,
  useCreateCtDepartment,
  useCreateCtHolidayCalendar,
  useCreateCtLeaveCycle,
  useCreateCtLeavePlan,
  useCreateCtLocation,
  useCreateCtOrgNote,
  useCreateCtNotice,
  useCreateCtOnDutyPolicy,
  useCreateLicenceBatch,
  useCreateOrganisationAddress,
  useCtAuditLogs,
  useCtHolidayCalendars,
  useCtOrgAttendanceSummary,
  useCtOrgApprovalSummary,
  useCtOrgConfiguration,
  useCtOrgEmployeeDetail,
  useCtOrgEmployees,
  useCtOrgOnboardingSummary,
  useCtOrgNotes,
  useDeactivateCtDepartment,
  useDeactivateCtLocation,
  useDeactivateCtOrgAdmin,
  useDeactivateOrganisationAddress,
  useInviteOrgAdmin,
  useMarkLicenceBatchPaid,
  useOrganisation,
  useOrgAdmins,
  usePublishCtNotice,
  usePublishCtHolidayCalendar,
  useReactivateCtOrgAdmin,
  useRevokePendingCtOrgAdmin,
  useResendOrgAdminInvite,
  useRestoreOrganisation,
  useSuspendOrganisation,
  useUpdateCtApprovalWorkflow,
  useUpdateCtBootstrapAdmin,
  useUpdateCtDepartment,
  useUpdateCtHolidayCalendar,
  useUpdateCtLeaveCycle,
  useUpdateCtLeavePlan,
  useUpdateCtLocation,
  useUpdateCtNotice,
  useUpdateCtOnDutyPolicy,
  useUpdateLicenceBatch,
  useUpdateOrganisation,
  useUpdateOrganisationAddress,
} from '@/hooks/useCtOrganisations'
import {
  APPROVAL_REQUEST_KIND_OPTIONS,
  createDefaultApprovalWorkflow,
  createDefaultHolidayCalendarForm,
  createDefaultLeaveCycleForm,
  createDefaultLeavePlanForm,
  createDefaultNoticeForm,
  createDefaultOnDutyPolicyForm,
  HOLIDAY_CLASSIFICATION_OPTIONS,
  HOLIDAY_SESSION_OPTIONS,
  LEAVE_CREDIT_FREQUENCY_OPTIONS,
  NOTICE_AUDIENCE_TYPE_OPTIONS,
} from '@/lib/constants'
import {
  getAddressCountryName,
  getAddressCountryOption,
  getAddressCountryRule,
  getBillingTaxLabel,
  getSubdivisionName,
  getSubdivisionOptions,
  resolveSubdivisionCode,
} from '@/lib/addressMetadata'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, formatDateTime, startCase } from '@/lib/format'
import {
  COUNTRY_OPTIONS,
  CURRENCY_OPTIONS,
  DEFAULT_COUNTRY_OPTION,
  ORGANISATION_ENTITY_TYPE_OPTIONS,
  getCountryOption,
  validatePhoneForCountry,
} from '@/lib/organisationMetadata'
import { ORG_ONBOARDING_STEPS } from '@/lib/status'
import type { ApprovalRequestKind, ApprovalWorkflowConfig, CtOrganisationApprovalSupportSummary, CtOrganisationAttendanceSupportSummary, CtOrganisationOnboardingSupportSummary, Department, HolidayCalendar, LeaveCycle, LeavePlan, Location, NoticeItem, OnDutyPolicy } from '@/types/hr'
import type { LicenceBatch, OrganisationAddress, OrganisationAddressType, OrganisationDetail, OrganisationEntityType } from '@/types/organisation'

type DetailTabKey =
  | 'overview'
  | 'details'
  | 'licences'
  | 'admins'
  | 'employees'
  | 'onboarding'
  | 'attendance'
  | 'approvals'
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

type ProfileFormState = {
  name: string
  pan_number: string
  country_code: string
  currency: string
  entity_type: OrganisationEntityType
}

type BootstrapAdminFormState = {
  first_name: string
  last_name: string
  email: string
  phone: string
}

type AddressFormState = {
  address_type: OrganisationAddressType
  label: string
  line1: string
  line2: string
  city: string
  state: string
  state_code: string
  country: string
  country_code: string
  pincode: string
  gstin: string
}

type LocationFormState = {
  name: string
  organisation_address_id: string
  is_remote: boolean
}

type DepartmentFormState = {
  name: string
  description: string
  parent_department_id: string
}

type LeaveCycleFormState = ReturnType<typeof createDefaultLeaveCycleForm>

type LeaveTypeFormState = {
  id?: string
  code: string
  name: string
  description: string
  color: string
  is_paid: boolean
  is_loss_of_pay: boolean
  annual_entitlement: string
  credit_frequency: string
  credit_day_of_period: number | null
  prorate_on_join: boolean
  carry_forward_mode: string
  carry_forward_cap: string | null
  max_balance: string | null
  allows_half_day: boolean
  requires_attachment: boolean
  attachment_after_days: string | null
  min_notice_days: number
  max_consecutive_days: number | null
  allow_past_request: boolean
  allow_future_request: boolean
  is_active: boolean
}

type LeavePlanRuleFormState = {
  id?: string
  name: string
  priority: number
  is_active: boolean
  department_id: string
  office_location_id: string
  specific_employee_id: string
  employment_type: string
  designation: string
}

type LeavePlanFormState = {
  leave_cycle_id: string
  name: string
  description: string
  is_default: boolean
  is_active: boolean
  priority: number
  leave_types: LeaveTypeFormState[]
  rules: LeavePlanRuleFormState[]
}

type HolidayFormState = ReturnType<typeof createDefaultHolidayCalendarForm>
type OnDutyPolicyFormState = ReturnType<typeof createDefaultOnDutyPolicyForm>
type WorkflowFormState = ReturnType<typeof createDefaultApprovalWorkflow>
type NoticeFormState = ReturnType<typeof createDefaultNoticeForm>

type ActionDialogState = {
  open: boolean
  note: string
}

const mandatoryAddressTypes: OrganisationAddressType[] = ['REGISTERED', 'BILLING']
const COUNTRY_SELECT_OPTIONS = COUNTRY_OPTIONS.map((country) => ({
  value: country.code,
  label: country.name,
  hint: `${country.dialCode} • ${country.defaultCurrency}`,
  keywords: [country.dialCode, country.defaultCurrency],
}))
const CURRENCY_SELECT_OPTIONS = CURRENCY_OPTIONS.map((currency) => ({
  value: currency.code,
  label: currency.label,
}))
const ENTITY_TYPE_OPTIONS = ORGANISATION_ENTITY_TYPE_OPTIONS.map((option) => ({
  value: option.value,
  label: option.label,
}))
const ADDRESS_TYPE_OPTIONS = ['REGISTERED', 'BILLING', 'HEADQUARTERS', 'WAREHOUSE', 'CUSTOM'].map((type) => ({
  value: type,
  label: startCase(type),
}))
const NOTICE_AUDIENCE_OPTIONS = NOTICE_AUDIENCE_TYPE_OPTIONS.map((value) => ({
  value,
  label: startCase(value),
}))

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
  { key: 'onboarding', label: 'Onboarding Support', icon: UserPlus },
  { key: 'attendance', label: 'Attendance Support', icon: Clock3 },
  { key: 'approvals', label: 'Approval Support', icon: FileText },
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

function createEmptyAddressForm(countryCode = DEFAULT_COUNTRY_OPTION.code): AddressFormState {
  return {
    address_type: 'CUSTOM',
    label: '',
    line1: '',
    line2: '',
    city: '',
    state: '',
    state_code: '',
    country: getAddressCountryName(countryCode),
    country_code: countryCode,
    pincode: '',
    gstin: '',
  }
}

function createEmptyLeaveTypeFormState(): LeaveTypeFormState {
  return {
    code: '',
    name: '',
    description: '',
    color: '#2563eb',
    is_paid: true,
    is_loss_of_pay: false,
    annual_entitlement: '0.00',
    credit_frequency: 'YEARLY',
    credit_day_of_period: null,
    prorate_on_join: true,
    carry_forward_mode: 'NONE',
    carry_forward_cap: null,
    max_balance: null,
    allows_half_day: true,
    requires_attachment: false,
    attachment_after_days: null,
    min_notice_days: 0,
    max_consecutive_days: null,
    allow_past_request: false,
    allow_future_request: true,
    is_active: true,
  }
}

function createProfileFormState(organisation: OrganisationDetail): ProfileFormState {
  return {
    name: organisation.name,
    pan_number: organisation.pan_number ?? '',
    country_code: organisation.country_code || DEFAULT_COUNTRY_OPTION.code,
    currency: organisation.currency || DEFAULT_COUNTRY_OPTION.defaultCurrency,
    entity_type: organisation.entity_type,
  }
}

function createBootstrapAdminFormState(
  bootstrapAdmin: OrganisationDetail['bootstrap_admin'],
): BootstrapAdminFormState {
  return {
    first_name: bootstrapAdmin?.first_name ?? '',
    last_name: bootstrapAdmin?.last_name ?? '',
    email: bootstrapAdmin?.email ?? '',
    phone: bootstrapAdmin?.phone ?? '',
  }
}

function createAddressFormState(address: OrganisationAddress): AddressFormState {
  return {
    address_type: address.address_type,
    label: address.label,
    line1: address.line1,
    line2: address.line2 ?? '',
    city: address.city,
    state: address.state,
    state_code: address.state_code,
    country: address.country,
    country_code: address.country_code,
    pincode: address.pincode,
    gstin: address.gstin ?? '',
  }
}

function createLocationFormState(location?: Location): LocationFormState {
  return {
    name: location?.name ?? '',
    organisation_address_id: location?.organisation_address_id ?? '',
    is_remote: location?.is_remote ?? false,
  }
}

function createDepartmentFormState(department?: Department): DepartmentFormState {
  return {
    name: department?.name ?? '',
    description: department?.description ?? '',
    parent_department_id: department?.parent_department_id ?? '',
  }
}

function createLeaveCycleDialogForm(cycle?: LeaveCycle): LeaveCycleFormState {
  if (!cycle) return createDefaultLeaveCycleForm()
  return {
    name: cycle.name,
    cycle_type: cycle.cycle_type,
    start_month: cycle.start_month,
    start_day: cycle.start_day,
    is_default: cycle.is_default,
    is_active: cycle.is_active,
  }
}

function createLeavePlanDialogForm(plan?: LeavePlan): LeavePlanFormState {
  if (!plan) {
    const defaultForm = createDefaultLeavePlanForm()
    return {
      ...defaultForm,
      leave_types: defaultForm.leave_types.map((leaveType) => ({
        ...createEmptyLeaveTypeFormState(),
        ...leaveType,
      })),
      rules: [],
    }
  }
  return {
    leave_cycle_id: plan.leave_cycle.id,
    name: plan.name,
    description: plan.description ?? '',
    is_default: plan.is_default,
    is_active: plan.is_active,
    priority: plan.priority,
    leave_types: plan.leave_types.map((leaveType) => ({
      id: leaveType.id,
      code: leaveType.code,
      name: leaveType.name,
      description: leaveType.description ?? '',
      color: leaveType.color,
      is_paid: leaveType.is_paid,
      is_loss_of_pay: leaveType.is_loss_of_pay,
      annual_entitlement: leaveType.annual_entitlement,
      credit_frequency: leaveType.credit_frequency,
      credit_day_of_period: leaveType.credit_day_of_period ?? null,
      prorate_on_join: leaveType.prorate_on_join,
      carry_forward_mode: leaveType.carry_forward_mode,
      carry_forward_cap: leaveType.carry_forward_cap ?? null,
      max_balance: leaveType.max_balance ?? null,
      allows_half_day: leaveType.allows_half_day,
      requires_attachment: leaveType.requires_attachment,
      attachment_after_days: leaveType.attachment_after_days ?? null,
      min_notice_days: leaveType.min_notice_days,
      max_consecutive_days: leaveType.max_consecutive_days ?? null,
      allow_past_request: leaveType.allow_past_request,
      allow_future_request: leaveType.allow_future_request,
      is_active: leaveType.is_active,
    })),
    rules: plan.rules.map((rule) => ({
      id: rule.id,
      name: rule.name,
      priority: rule.priority,
      is_active: rule.is_active,
      department_id: rule.department ?? '',
      office_location_id: rule.office_location ?? '',
      specific_employee_id: rule.specific_employee ?? '',
      employment_type: rule.employment_type,
      designation: rule.designation,
    })),
  }
}

function createOnDutyPolicyDialogForm(policy?: OnDutyPolicy): OnDutyPolicyFormState {
  if (!policy) return createDefaultOnDutyPolicyForm()
  return {
    name: policy.name,
    description: policy.description ?? '',
    is_default: policy.is_default,
    is_active: policy.is_active,
    allow_half_day: policy.allow_half_day,
    allow_time_range: policy.allow_time_range,
    requires_attachment: policy.requires_attachment,
    min_notice_days: policy.min_notice_days,
    allow_past_request: policy.allow_past_request,
    allow_future_request: policy.allow_future_request,
  }
}

function createWorkflowDialogForm(workflow?: ApprovalWorkflowConfig): WorkflowFormState {
  if (!workflow) return createDefaultApprovalWorkflow()
  return {
    name: workflow.name,
    description: workflow.description ?? '',
    is_default: workflow.is_default,
    default_request_kind: workflow.default_request_kind ?? 'LEAVE',
    is_active: workflow.is_active,
    rules: workflow.rules.map((rule) => ({
      id: rule.id,
      name: rule.name,
      request_kind: rule.request_kind,
      priority: rule.priority,
      is_active: rule.is_active,
      department_id: rule.department,
      office_location_id: rule.office_location,
      specific_employee_id: rule.specific_employee,
      employment_type: rule.employment_type,
      designation: rule.designation,
      leave_type_id: rule.leave_type,
    })),
    stages: workflow.stages.map((stage) => ({
      id: stage.id,
      name: stage.name,
      sequence: stage.sequence,
      mode: stage.mode,
      fallback_type: stage.fallback_type,
      fallback_employee_id: stage.fallback_employee_id,
      approvers: stage.approvers.map((approver) => ({
        id: approver.id,
        approver_type: approver.approver_type,
        approver_employee_id: approver.approver_employee_id,
      })),
    })),
  }
}

function createNoticeDialogForm(notice?: NoticeItem): NoticeFormState {
  if (!notice) return createDefaultNoticeForm()
  return {
    title: notice.title,
    body: notice.body,
    category: notice.category,
    audience_type: notice.audience_type,
    status: notice.status,
    is_sticky: notice.is_sticky,
    scheduled_for: notice.scheduled_for,
    expires_at: notice.expires_at,
    department_ids: [...notice.department_ids],
    office_location_ids: [...notice.office_location_ids],
    employee_ids: [...notice.employee_ids],
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

function diagnosticTone(severity: 'critical' | 'warning' | 'info') {
  if (severity === 'critical') return 'danger'
  if (severity === 'warning') return 'warning'
  return 'info'
}

function SupportDiagnostics({
  diagnostics,
}: {
  diagnostics: Array<{
    code: string
    severity: 'critical' | 'warning' | 'info'
    title: string
    detail: string
    action: string
  }>
}) {
  if (!diagnostics.length) return null

  return (
    <SectionCard
      title="Needs CT attention"
      description="These diagnostics turn zero-value summaries into actionable support guidance so Control Tower can explain what is misconfigured or blocked."
    >
      <div className="space-y-3">
        {diagnostics.map((diagnostic) => (
          <div key={diagnostic.code} className="surface-muted rounded-[22px] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">{diagnostic.title}</p>
              <StatusBadge tone={diagnosticTone(diagnostic.severity)}>{startCase(diagnostic.severity)}</StatusBadge>
            </div>
            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{diagnostic.detail}</p>
            <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">{diagnostic.action}</p>
          </div>
        ))}
      </div>
    </SectionCard>
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
  const navigate = useNavigate()
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
  const [profileDialogOpen, setProfileDialogOpen] = useState(false)
  const [bootstrapAdminDialogOpen, setBootstrapAdminDialogOpen] = useState(false)
  const [addressDialogOpen, setAddressDialogOpen] = useState(false)
  const [locationDialogOpen, setLocationDialogOpen] = useState(false)
  const [departmentDialogOpen, setDepartmentDialogOpen] = useState(false)
  const [leaveCycleDialogOpen, setLeaveCycleDialogOpen] = useState(false)
  const [leavePlanDialogOpen, setLeavePlanDialogOpen] = useState(false)
  const [onDutyPolicyDialogOpen, setOnDutyPolicyDialogOpen] = useState(false)
  const [workflowDialogOpen, setWorkflowDialogOpen] = useState(false)
  const [noticeDialogOpen, setNoticeDialogOpen] = useState(false)
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
  const [holidayForm, setHolidayForm] = useState<HolidayFormState>(createDefaultHolidayCalendarForm)
  const [profileForm, setProfileForm] = useState<ProfileFormState | null>(null)
  const [bootstrapAdminForm, setBootstrapAdminForm] = useState<BootstrapAdminFormState | null>(null)
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null)
  const [addressForm, setAddressForm] = useState<AddressFormState>(createEmptyAddressForm())
  const [editingLocationId, setEditingLocationId] = useState<string | null>(null)
  const [locationForm, setLocationForm] = useState<LocationFormState>(createLocationFormState())
  const [editingDepartmentId, setEditingDepartmentId] = useState<string | null>(null)
  const [departmentForm, setDepartmentForm] = useState<DepartmentFormState>(createDepartmentFormState())
  const [editingLeaveCycleId, setEditingLeaveCycleId] = useState<string | null>(null)
  const [leaveCycleForm, setLeaveCycleForm] = useState<LeaveCycleFormState>(createDefaultLeaveCycleForm)
  const [editingLeavePlanId, setEditingLeavePlanId] = useState<string | null>(null)
  const [leavePlanForm, setLeavePlanForm] = useState<LeavePlanFormState>(createLeavePlanDialogForm())
  const [editingOnDutyPolicyId, setEditingOnDutyPolicyId] = useState<string | null>(null)
  const [onDutyPolicyForm, setOnDutyPolicyForm] = useState<OnDutyPolicyFormState>(createDefaultOnDutyPolicyForm)
  const [editingWorkflowId, setEditingWorkflowId] = useState<string | null>(null)
  const [workflowForm, setWorkflowForm] = useState<WorkflowFormState>(createDefaultApprovalWorkflow)
  const [editingNoticeId, setEditingNoticeId] = useState<string | null>(null)
  const [noticeForm, setNoticeForm] = useState<NoticeFormState>(createDefaultNoticeForm)
  const [hasProfileCurrencyManualOverride, setHasProfileCurrencyManualOverride] = useState(false)

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
    Boolean(organisationId),
  )
  const { data: onboardingSummary, isLoading: onboardingSummaryLoading } = useCtOrgOnboardingSummary(
    organisationId,
    activeTab === 'onboarding',
  )
  const { data: attendanceSummary, isLoading: attendanceSummaryLoading } = useCtOrgAttendanceSummary(organisationId, activeTab === 'attendance')
  const { data: approvalSummary, isLoading: approvalSummaryLoading } = useCtOrgApprovalSummary(organisationId, activeTab === 'approvals')
  const { data: auditLogs } = useCtAuditLogs(organisationId, activeTab === 'audit')
  const { data: notes, isLoading: notesLoading } = useCtOrgNotes(organisationId, activeTab === 'notes')
  const updateOrganisationMutation = useUpdateOrganisation(organisationId)
  const updateBootstrapAdminMutation = useUpdateCtBootstrapAdmin(organisationId)
  const createAddressMutation = useCreateOrganisationAddress(organisationId)
  const updateAddressMutation = useUpdateOrganisationAddress(organisationId)
  const deactivateAddressMutation = useDeactivateOrganisationAddress(organisationId)
  const suspendMutation = useSuspendOrganisation()
  const restoreMutation = useRestoreOrganisation()
  const inviteAdminMutation = useInviteOrgAdmin(organisationId)
  const resendInviteMutation = useResendOrgAdminInvite(organisationId)
  const deactivateAdminMutation = useDeactivateCtOrgAdmin(organisationId)
  const reactivateAdminMutation = useReactivateCtOrgAdmin(organisationId)
  const revokeAdminMutation = useRevokePendingCtOrgAdmin(organisationId)
  const createBatchMutation = useCreateLicenceBatch(organisationId)
  const updateBatchMutation = useUpdateLicenceBatch(organisationId)
  const markBatchPaidMutation = useMarkLicenceBatchPaid(organisationId)
  const createHolidayMutation = useCreateCtHolidayCalendar(organisationId)
  const updateHolidayMutation = useUpdateCtHolidayCalendar(organisationId)
  const publishHolidayMutation = usePublishCtHolidayCalendar(organisationId)
  const createNoteMutation = useCreateCtOrgNote(organisationId)
  const createLocationMutation = useCreateCtLocation(organisationId)
  const updateLocationMutation = useUpdateCtLocation(organisationId)
  const deactivateLocationMutation = useDeactivateCtLocation(organisationId)
  const createDepartmentMutation = useCreateCtDepartment(organisationId)
  const updateDepartmentMutation = useUpdateCtDepartment(organisationId)
  const deactivateDepartmentMutation = useDeactivateCtDepartment(organisationId)
  const createLeaveCycleMutation = useCreateCtLeaveCycle(organisationId)
  const updateLeaveCycleMutation = useUpdateCtLeaveCycle(organisationId)
  const createLeavePlanMutation = useCreateCtLeavePlan(organisationId)
  const updateLeavePlanMutation = useUpdateCtLeavePlan(organisationId)
  const createOnDutyPolicyMutation = useCreateCtOnDutyPolicy(organisationId)
  const updateOnDutyPolicyMutation = useUpdateCtOnDutyPolicy(organisationId)
  const createWorkflowMutation = useCreateCtApprovalWorkflow(organisationId)
  const updateWorkflowMutation = useUpdateCtApprovalWorkflow(organisationId)
  const createNoticeMutation = useCreateCtNotice(organisationId)
  const updateNoticeMutation = useUpdateCtNotice(organisationId)
  const publishNoticeMutation = usePublishCtNotice(organisationId)

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

  const selectedProfileCountry =
    getCountryOption(profileForm?.country_code ?? organisation?.country_code ?? DEFAULT_COUNTRY_OPTION.code) ?? DEFAULT_COUNTRY_OPTION
  const addressCountry = getAddressCountryOption(addressForm.country_code || addressForm.country) ?? selectedProfileCountry
  const addressRule = getAddressCountryRule(addressCountry.code)
  const addressSubdivisions = getSubdivisionOptions(addressCountry.code).map((subdivision) => ({
    value: subdivision.code,
    label: subdivision.label,
    hint: subdivision.taxRegionCode ? `Tax region ${subdivision.taxRegionCode}` : undefined,
  }))
  const departmentOptions = [
    { value: '', label: 'No parent department' },
    ...(configuration?.departments
      .filter((department) => department.is_active && department.id !== editingDepartmentId)
      .map((department) => ({
        value: department.id,
        label: department.name,
      })) ?? []),
  ]
  const leaveCycleOptions = [
    { value: '', label: 'Select leave cycle' },
    ...(configuration?.leave_cycles.map((cycle) => ({
      value: cycle.id,
      label: cycle.name,
    })) ?? []),
  ]
  const noticeDepartmentOptions =
    configuration?.departments.filter((department) => department.is_active) ?? []

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
  const noticeAudienceOptions = NOTICE_AUDIENCE_OPTIONS
  const leaveCreditFrequencyOptions = LEAVE_CREDIT_FREQUENCY_OPTIONS.map((frequency) => ({
    value: frequency,
    label: startCase(frequency),
  }))

  const setActiveTab = (tab: DetailTabKey) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tab)
    setSearchParams(next, { replace: true })
  }

  const openProfileDialog = () => {
    if (!organisation) return
    setProfileForm(createProfileFormState(organisation))
    setHasProfileCurrencyManualOverride(false)
    setProfileDialogOpen(true)
  }

  const openBootstrapAdminDialog = () => {
    setBootstrapAdminForm(createBootstrapAdminFormState(bootstrapAdmin))
    setBootstrapAdminDialogOpen(true)
  }

  const openAddressDialog = (address?: OrganisationAddress) => {
    setEditingAddressId(address?.id ?? null)
    setAddressForm(address ? createAddressFormState(address) : createEmptyAddressForm(selectedProfileCountry.code))
    setAddressDialogOpen(true)
  }

  const openLocationDialog = (location?: Location) => {
    setEditingLocationId(location?.id ?? null)
    setLocationForm(createLocationFormState(location))
    setLocationDialogOpen(true)
  }

  const openDepartmentDialog = (department?: Department) => {
    setEditingDepartmentId(department?.id ?? null)
    setDepartmentForm(createDepartmentFormState(department))
    setDepartmentDialogOpen(true)
  }

  const openLeaveCycleDialog = (cycle?: LeaveCycle) => {
    setEditingLeaveCycleId(cycle?.id ?? null)
    setLeaveCycleForm(createLeaveCycleDialogForm(cycle))
    setLeaveCycleDialogOpen(true)
  }

  const openLeavePlanDialog = (plan?: LeavePlan) => {
    setEditingLeavePlanId(plan?.id ?? null)
    setLeavePlanForm(createLeavePlanDialogForm(plan))
    setLeavePlanDialogOpen(true)
  }

  const openOnDutyPolicyDialog = (policy?: OnDutyPolicy) => {
    setEditingOnDutyPolicyId(policy?.id ?? null)
    setOnDutyPolicyForm(createOnDutyPolicyDialogForm(policy))
    setOnDutyPolicyDialogOpen(true)
  }

  const openWorkflowDialog = (workflow?: ApprovalWorkflowConfig) => {
    setEditingWorkflowId(workflow?.id ?? null)
    setWorkflowForm(createWorkflowDialogForm(workflow))
    setWorkflowDialogOpen(true)
  }

  const openNoticeDialog = (notice?: NoticeItem) => {
    setEditingNoticeId(notice?.id ?? null)
    setNoticeForm(createNoticeDialogForm(notice))
    setNoticeDialogOpen(true)
  }

  const setAddressCountry = (countryCode: string) => {
    setAddressForm((current) => ({
      ...current,
      country_code: countryCode,
      country: getAddressCountryName(countryCode),
      state: '',
      state_code: '',
      pincode: '',
      gstin: '',
    }))
  }

  const setAddressState = (stateCode: string) => {
    setAddressForm((current) => ({
      ...current,
      state_code: stateCode,
      state: getSubdivisionName(addressCountry.code, stateCode, ''),
    }))
  }

  const handleProfileCountryChange = (nextCountryCode: string) => {
    setProfileForm((current) => {
      if (!current) return current
      const previousCountry = getCountryOption(current.country_code) ?? DEFAULT_COUNTRY_OPTION
      const nextCountry = getCountryOption(nextCountryCode) ?? DEFAULT_COUNTRY_OPTION
      const shouldAutoUpdateCurrency =
        !hasProfileCurrencyManualOverride || current.currency === previousCountry.defaultCurrency
      return {
        ...current,
        country_code: nextCountryCode,
        currency: shouldAutoUpdateCurrency ? nextCountry.defaultCurrency : current.currency,
      }
    })
    if (!hasProfileCurrencyManualOverride || profileForm?.currency === selectedProfileCountry.defaultCurrency) {
      setHasProfileCurrencyManualOverride(false)
    }
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

  const handleDeactivateAdmin = async (userId: string) => {
    try {
      await deactivateAdminMutation.mutateAsync(userId)
      toast.success('Organisation admin deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate this admin.'))
    }
  }

  const handleReactivateAdmin = async (userId: string) => {
    try {
      await reactivateAdminMutation.mutateAsync(userId)
      toast.success('Organisation admin reactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to reactivate this admin.'))
    }
  }

  const handleRevokePendingAdmin = async (userId: string) => {
    try {
      await revokeAdminMutation.mutateAsync(userId)
      toast.success('Pending admin invite revoked.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to revoke this pending invite.'))
    }
  }

  const handleSaveProfile = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!profileForm) return
    try {
      await updateOrganisationMutation.mutateAsync(profileForm)
      toast.success('Organisation profile updated.')
      setProfileDialogOpen(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update organisation profile.'))
    }
  }

  const handleSaveBootstrapAdmin = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!bootstrapAdminForm || !organisation) return
    try {
      const phoneError = validatePhoneForCountry(bootstrapAdminForm.phone, organisation.country_code)
      if (phoneError) {
        toast.error(phoneError)
        return
      }
      await updateBootstrapAdminMutation.mutateAsync(bootstrapAdminForm)
      toast.success('Bootstrap admin updated.')
      setBootstrapAdminDialogOpen(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update bootstrap admin.'))
    }
  }

  const handleSaveAddress = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      ...addressForm,
      label: mandatoryAddressTypes.includes(addressForm.address_type) ? undefined : addressForm.label,
      gstin: addressForm.gstin || null,
    }
    try {
      if (editingAddressId) {
        await updateAddressMutation.mutateAsync({ addressId: editingAddressId, payload })
        toast.success('Address updated.')
      } else {
        await createAddressMutation.mutateAsync(payload)
        toast.success('Address created.')
      }
      setAddressDialogOpen(false)
      setEditingAddressId(null)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save address.'))
    }
  }

  const handleDeactivateAddress = async (addressId: string) => {
    try {
      await deactivateAddressMutation.mutateAsync(addressId)
      toast.success('Address deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate this address.'))
    }
  }

  const handleSaveLocation = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingLocationId) {
        await updateLocationMutation.mutateAsync({ locationId: editingLocationId, payload: locationForm })
        toast.success('Location updated.')
      } else {
        await createLocationMutation.mutateAsync(locationForm)
        toast.success('Location created.')
      }
      setLocationDialogOpen(false)
      setEditingLocationId(null)
      setLocationForm(createLocationFormState())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save location.'))
    }
  }

  const handleDeactivateLocation = async (locationId: string) => {
    try {
      await deactivateLocationMutation.mutateAsync(locationId)
      toast.success('Location deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate this location.'))
    }
  }

  const handleSaveDepartment = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      ...departmentForm,
      parent_department_id: departmentForm.parent_department_id || null,
    }
    try {
      if (editingDepartmentId) {
        await updateDepartmentMutation.mutateAsync({ departmentId: editingDepartmentId, payload })
        toast.success('Department updated.')
      } else {
        await createDepartmentMutation.mutateAsync(payload)
        toast.success('Department created.')
      }
      setDepartmentDialogOpen(false)
      setEditingDepartmentId(null)
      setDepartmentForm(createDepartmentFormState())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save department.'))
    }
  }

  const handleDeactivateDepartment = async (departmentId: string) => {
    try {
      await deactivateDepartmentMutation.mutateAsync(departmentId)
      toast.success('Department deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate this department.'))
    }
  }

  const handleSaveLeaveCycle = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingLeaveCycleId) {
        await updateLeaveCycleMutation.mutateAsync({ cycleId: editingLeaveCycleId, payload: leaveCycleForm })
        toast.success('Leave cycle updated.')
      } else {
        await createLeaveCycleMutation.mutateAsync(leaveCycleForm)
        toast.success('Leave cycle created.')
      }
      setLeaveCycleDialogOpen(false)
      setEditingLeaveCycleId(null)
      setLeaveCycleForm(createDefaultLeaveCycleForm())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save leave cycle.'))
    }
  }

  const handleSaveLeavePlan = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingLeavePlanId) {
        await updateLeavePlanMutation.mutateAsync({ planId: editingLeavePlanId, payload: leavePlanForm })
        toast.success('Leave plan updated.')
      } else {
        await createLeavePlanMutation.mutateAsync(leavePlanForm)
        toast.success('Leave plan created.')
      }
      setLeavePlanDialogOpen(false)
      setEditingLeavePlanId(null)
      setLeavePlanForm(createLeavePlanDialogForm())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save leave plan.'))
    }
  }

  const handleSaveOnDutyPolicy = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingOnDutyPolicyId) {
        await updateOnDutyPolicyMutation.mutateAsync({ policyId: editingOnDutyPolicyId, payload: onDutyPolicyForm })
        toast.success('On-duty policy updated.')
      } else {
        await createOnDutyPolicyMutation.mutateAsync(onDutyPolicyForm)
        toast.success('On-duty policy created.')
      }
      setOnDutyPolicyDialogOpen(false)
      setEditingOnDutyPolicyId(null)
      setOnDutyPolicyForm(createDefaultOnDutyPolicyForm())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save on-duty policy.'))
    }
  }

  const handleSaveWorkflow = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingWorkflowId) {
        await updateWorkflowMutation.mutateAsync({ workflowId: editingWorkflowId, payload: workflowForm })
        toast.success('Approval workflow updated.')
      } else {
        await createWorkflowMutation.mutateAsync(workflowForm)
        toast.success('Approval workflow created.')
      }
      setWorkflowDialogOpen(false)
      setEditingWorkflowId(null)
      setWorkflowForm(createDefaultApprovalWorkflow())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save approval workflow.'))
    }
  }

  const handleSaveNotice = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingNoticeId) {
        await updateNoticeMutation.mutateAsync({ noticeId: editingNoticeId, payload: noticeForm })
        toast.success('Notice updated.')
      } else {
        await createNoticeMutation.mutateAsync(noticeForm)
        toast.success('Notice created.')
      }
      setNoticeDialogOpen(false)
      setEditingNoticeId(null)
      setNoticeForm(createDefaultNoticeForm())
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save notice.'))
    }
  }

  const handlePublishNotice = async (noticeId: string) => {
    try {
      await publishNoticeMutation.mutateAsync(noticeId)
      toast.success('Notice published.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to publish this notice.'))
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
      {organisation.operations_guard.licence_expired ? (
        <div className="rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
          <p className="font-semibold">This organisation is currently blocked by licence state.</p>
          <p className="mt-1 text-[hsl(var(--muted-foreground))]">{organisation.operations_guard.reason}</p>
          <p className="mt-2 text-[hsl(var(--muted-foreground))]">
            Admin mutations: {organisation.operations_guard.admin_mutations_blocked ? 'blocked' : 'available'} • Approval actions: {organisation.operations_guard.approval_actions_blocked ? 'blocked' : 'available'}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" className="btn-secondary" onClick={() => setSearchParams({ tab: 'licences' })}>
              Review licences
            </button>
            <button type="button" className="btn-secondary" onClick={() => setSearchParams({ tab: 'approvals' })}>
              Review approval support
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/payroll`)}>
              Review payroll support
            </button>
          </div>
        </div>
      ) : null}

      <SectionCard
        title="Access state and onboarding"
        description="Track where this organisation sits across billing, activation, and onboarding."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          <DetailMetric
            label="Lifecycle status"
            value={startCase(organisation.status)}
            helper={`Modified ${formatDateTime(organisation.modified_at)}`}
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
      <SectionCard
        title="Legal profile"
        description="Core organisation identity, geography, and commercial defaults."
        action={
          <button type="button" className="btn-secondary" onClick={openProfileDialog}>
            Edit details
          </button>
        }
      >
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

      <SectionCard
        title="Bootstrap admin"
        description="Primary organisation admin bootstrap details can be edited until the first paid batch is confirmed."
        action={
          organisation.billing_status !== 'PAID' ? (
            <button type="button" className="btn-secondary" onClick={openBootstrapAdminDialog}>
              Edit bootstrap admin
            </button>
          ) : null
        }
      >
        {bootstrapAdmin ? (
          <InfoStack
            items={[
              { label: 'Full name', value: bootstrapAdmin.full_name },
              { label: 'Email', value: bootstrapAdmin.email },
              { label: 'Phone', value: bootstrapAdmin.phone },
              { label: 'Status', value: startCase(bootstrapAdmin.status) },
              { label: 'Invite sent', value: formatDateTime(bootstrapAdmin.invitation_sent_at) },
              { label: 'Accepted', value: formatDateTime(bootstrapAdmin.accepted_at) },
            ]}
          />
        ) : (
          <EmptyState
            title="Bootstrap admin not configured"
            description="Capture the primary admin so onboarding can be sent once the first batch is paid."
            icon={Mail}
            action={
              <button type="button" className="btn-primary" onClick={openBootstrapAdminDialog}>
                Add bootstrap admin
              </button>
            }
          />
        )}
      </SectionCard>

      <SectionCard
        title="Address directory"
        description="Registered, billing, and operational addresses saved for this organisation."
        action={
          <button type="button" className="btn-primary" onClick={() => openAddressDialog()}>
            Add address
          </button>
        }
      >
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
              <div className="mt-3 flex flex-wrap gap-3">
                <button type="button" className="btn-secondary" onClick={() => openAddressDialog(address)}>
                  Edit
                </button>
                {address.is_active && !['REGISTERED', 'BILLING'].includes(address.address_type) ? (
                  <button type="button" className="btn-danger" onClick={() => void handleDeactivateAddress(address.id)}>
                    Deactivate
                  </button>
                ) : null}
              </div>
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
            {organisation.billing_status !== 'PAID' ? (
              <div className="mt-4">
                <button type="button" className="btn-secondary" onClick={openBootstrapAdminDialog}>
                  Edit bootstrap admin
                </button>
              </div>
            ) : null}
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
                      <StatusBadge
                        tone={
                          admin.membership_status === 'ACTIVE'
                            ? 'success'
                            : admin.membership_status === 'INVITED'
                              ? 'warning'
                              : 'neutral'
                        }
                      >
                        {startCase(admin.membership_status)}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{admin.email}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                      Invited {formatDateTime(admin.invited_at)}
                      {admin.accepted_at ? ` • Accepted ${formatDateTime(admin.accepted_at)}` : ''}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {admin.membership_status === 'INVITED' && admin.is_onboarding_email_sent ? (
                      <button type="button" className="btn-secondary" onClick={() => handleResendInvite(admin.id)}>
                        Resend invite
                      </button>
                    ) : null}
                    {admin.membership_status === 'INVITED' ? (
                      <button type="button" className="btn-danger" onClick={() => void handleRevokePendingAdmin(admin.id)}>
                        Revoke invite
                      </button>
                    ) : null}
                    {admin.membership_status === 'ACTIVE' ? (
                      <button type="button" className="btn-danger" onClick={() => void handleDeactivateAdmin(admin.id)}>
                        Deactivate
                      </button>
                    ) : null}
                    {admin.membership_status === 'INACTIVE' ? (
                      <button type="button" className="btn-primary" onClick={() => void handleReactivateAdmin(admin.id)}>
                        Reactivate
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
            placeholder="Search employee code or name"
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
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {[employee.employee_code || 'No employee code', employee.designation || 'No designation', employee.department_name || 'No department', employee.office_location_name || 'No location']
                          .filter(Boolean)
                          .join(' • ')}
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

  const renderOnboardingTab = () => {
    if (onboardingSummaryLoading) {
      return <SkeletonTable rows={5} />
    }

    const summary = onboardingSummary as CtOrganisationOnboardingSupportSummary | undefined
    if (!summary) {
      return (
        <EmptyState
          title="Onboarding support data unavailable"
          description="This tab will show Control Tower blocker visibility for invites, profile completion, and document follow-up."
          icon={UserPlus}
        />
      )
    }

    const openDocumentBlockers =
      (summary.document_request_status_counts.REQUESTED ?? 0)
      + (summary.document_request_status_counts.SUBMITTED ?? 0)
      + (summary.document_request_status_counts.REJECTED ?? 0)

    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <DetailMetric label="Not started" value={String(summary.onboarding_status_counts.NOT_STARTED ?? 0)} helper="Invite accepted or pending action missing" />
          <DetailMetric label="Basic details pending" value={String(summary.onboarding_status_counts.BASIC_DETAILS_PENDING ?? 0)} helper="Employee still has profile setup to finish" />
          <DetailMetric label="Documents pending" value={String(summary.onboarding_status_counts.DOCUMENTS_PENDING ?? 0)} helper="Operational follow-up still required" />
          <DetailMetric label="Open document blockers" value={String(openDocumentBlockers)} helper={`${summary.document_request_status_counts.REJECTED ?? 0} rejected submissions`} />
          <DetailMetric label="Blocked employees" value={String(summary.blocked_employees.length)} helper="Highest-friction onboarding cases" />
        </div>

        <SectionCard
          title="Onboarding blockers"
          description="Control Tower can inspect who is blocked and why, without opening employee PII or the underlying document contents."
        >
          {summary.blocked_employees.length ? (
            <div className="space-y-3">
              {summary.blocked_employees.map((employee) => (
                <div key={employee.id} className="surface-muted rounded-[24px] p-4">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{employee.full_name}</p>
                        <StatusBadge tone={employee.status === 'ACTIVE' ? 'success' : employee.status === 'PENDING' ? 'warning' : 'info'}>
                          {employee.status}
                        </StatusBadge>
                        <StatusBadge tone={employee.onboarding_status === 'COMPLETE' ? 'success' : 'warning'}>
                          {startCase(employee.onboarding_status)}
                        </StatusBadge>
                        {employee.pending_document_requests > 0 ? (
                          <StatusBadge tone="warning">{employee.pending_document_requests} open document blocker{employee.pending_document_requests === 1 ? '' : 's'}</StatusBadge>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {[employee.employee_code || 'No employee code', employee.designation || 'No designation'].filter(Boolean).join(' • ')}
                      </p>
                    </div>
                    <div className="text-right text-sm text-[hsl(var(--muted-foreground))]">
                      <p>{employee.latest_document_activity_at ? `Last document activity ${formatDateTime(employee.latest_document_activity_at)}` : 'No document upload yet'}</p>
                      <p>CT view is limited to blocker metadata only</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No onboarding blockers"
              description="This organisation currently has no employees stalled in onboarding or document verification."
              icon={UserPlus}
            />
          )}
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard
            title="Top blocker types"
            description="Shows which request types are creating the largest onboarding queue without exposing submitted files."
          >
            {summary.top_blocker_types.length ? (
              <div className="space-y-3">
                {summary.top_blocker_types.map((blocker) => (
                  <div key={blocker.document_type_code} className="surface-muted flex flex-wrap items-center justify-between gap-3 rounded-[22px] p-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{blocker.document_type_name}</p>
                        <StatusBadge tone="info">{blocker.document_type_code}</StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{blocker.blocked_employee_count} employees currently blocked</p>
                    </div>
                    <p className="text-sm font-medium text-[hsl(var(--foreground-strong))]">{blocker.blocked_employee_count}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No document blocker types"
                description="Document request blockers will appear here when onboarding tasks need org admin follow-up."
                icon={FileText}
              />
            )}
          </SectionCard>

          <SectionCard
            title="Document request queue"
            description="This queue view helps CT tell whether the organisation is waiting on employee submission, admin review, or completed verification."
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailMetric label="Requested" value={String(summary.document_request_status_counts.REQUESTED ?? 0)} helper="Waiting on employee submission" />
              <DetailMetric label="Submitted" value={String(summary.document_request_status_counts.SUBMITTED ?? 0)} helper="Waiting on admin review" />
              <DetailMetric label="Rejected" value={String(summary.document_request_status_counts.REJECTED ?? 0)} helper="Employee needs resubmission" />
              <DetailMetric label="Verified" value={String(summary.document_request_status_counts.VERIFIED ?? 0)} helper="Cleared requests" />
            </div>
          </SectionCard>
        </div>
      </div>
    )
  }

  const renderAttendanceTab = () => {
    if (attendanceSummaryLoading) {
      return <SkeletonTable rows={5} />
    }

    const summary = attendanceSummary as CtOrganisationAttendanceSupportSummary | undefined
    if (!summary) {
      return (
        <EmptyState
          title="Attendance support data unavailable"
          description="This tab will show sanitized attendance operations health for Control Tower support."
          icon={Clock3}
        />
      )
    }

    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DetailMetric label="Policies" value={String(summary.policy_count)} helper="Attendance policy coverage" />
          <DetailMetric label="Sources" value={String(summary.source_count)} helper={`${summary.active_source_count} active adapters`} />
          <DetailMetric label="Pending regularizations" value={String(summary.pending_regularizations)} helper="Corrections still awaiting approval" />
          <DetailMetric label="Today's incomplete" value={String(summary.today_summary.incomplete_count)} helper={`${summary.today_summary.absent_count} absent today`} />
        </div>

        <SupportDiagnostics diagnostics={summary.diagnostics} />

        <SectionCard
          title="Today attendance health"
          description="Sanitized daily summary for Control Tower support. This shows org-level operational status without exposing detailed employee movement data."
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <DetailMetric label="Present" value={String(summary.today_summary.present_count)} helper={summary.today_summary.date} />
            <DetailMetric label="Half day" value={String(summary.today_summary.half_day_count)} helper="Requires attendance or leave review" />
            <DetailMetric label="On leave" value={String(summary.today_summary.on_leave_count)} helper="Approved leave impact" />
            <DetailMetric label="On duty" value={String(summary.today_summary.on_duty_count)} helper="Approved duty travel / field work" />
          </div>
        </SectionCard>

        <SectionCard
          title="Recent attendance imports"
          description="Import health helps CT guide org admins when attendance uploads or external source handoffs are failing."
        >
          {summary.recent_imports.length ? (
            <div className="space-y-3">
              {summary.recent_imports.map((item) => (
                <div key={item.id} className="surface-muted rounded-[22px] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{item.original_filename}</p>
                        <StatusBadge tone={item.status === 'POSTED' ? 'success' : item.status === 'READY_FOR_REVIEW' ? 'info' : 'danger'}>
                          {item.status}
                        </StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {item.mode.replace(/_/g, ' ')} • Valid {item.valid_rows} • Errors {item.error_rows} • Posted {item.posted_rows}
                      </p>
                    </div>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{formatDateTime(item.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No attendance imports yet"
              description="Once the organisation begins uploading attendance or punch workbooks, CT can inspect recent import health here."
              icon={Clock3}
            />
          )}
        </SectionCard>
      </div>
    )
  }

  const renderApprovalsTab = () => {
    if (approvalSummaryLoading) {
      return <SkeletonTable rows={5} />
    }

    const summary = approvalSummary as CtOrganisationApprovalSupportSummary | undefined
    if (!summary) {
      return (
        <EmptyState
          title="Approval support data unavailable"
          description="This tab will show workflow health and recent approval runs for Control Tower support."
          icon={FileText}
        />
      )
    }

    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DetailMetric label="Workflows" value={String(summary.workflows_count)} helper={`${summary.active_workflows_count} active`} />
          <DetailMetric label="Default workflows" value={String(summary.default_workflows_count)} helper="Per request type where configured" />
          <DetailMetric label="Pending runs" value={String(summary.pending_runs_count)} helper={`${summary.pending_actions_count} runs still need approver action`} />
          <DetailMetric label="Rejected runs" value={String(summary.rejected_runs_count)} helper={`${summary.approved_runs_count} approved historically`} />
        </div>

        <SectionCard
          title="Recent approval activity"
          description="Control Tower can inspect request type, workflow, requester, and run status here without acting as an approver."
        >
          {summary.recent_runs.length ? (
            <div className="space-y-3">
              {summary.recent_runs.map((run) => (
                <div key={run.id} className="surface-muted rounded-[24px] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{run.subject_label}</p>
                        <StatusBadge tone={run.status === 'APPROVED' ? 'success' : run.status === 'REJECTED' ? 'danger' : 'warning'}>
                          {run.status}
                        </StatusBadge>
                        {run.pending_actions_count ? <StatusBadge tone="warning">{run.pending_actions_count} pending actions</StatusBadge> : null}
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {run.request_kind.replace(/_/g, ' ')} • {run.workflow_name} • Stage {run.current_stage_sequence}
                      </p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        Requested by {run.requester_name || 'Unknown requester'}
                      </p>
                    </div>
                    <div className="text-right text-sm text-[hsl(var(--muted-foreground))]">
                      <p>Created {formatDateTime(run.created_at)}</p>
                      <p>Updated {formatDateTime(run.modified_at)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No approval runs yet"
              description="Approval requests will appear here once the organisation starts using leave, on-duty, or payroll approval flows."
              icon={FileText}
            />
          )}
        </SectionCard>
      </div>
    )
  }

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
      <SectionCard
        title="Workplace structure"
        description="Locations and departments configured for this tenant."
        action={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => openLocationDialog()}>
              Add location
            </button>
            <button type="button" className="btn-primary" onClick={() => openDepartmentDialog()}>
              Add department
            </button>
          </div>
        }
      >
        {configurationLoading ? (
          <SkeletonTable rows={5} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <DetailListCard title={`Locations (${configuration?.locations.length ?? 0})`}>
              {configuration?.locations.length ? (
                configuration.locations.map((location) => (
                  <div key={location.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {location.name} • {location.is_remote ? 'Remote' : 'Office'} • {location.is_active ? 'Active' : 'Inactive'}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openLocationDialog(location)}>
                        Edit
                      </button>
                      {location.is_active ? (
                        <button type="button" className="btn-danger" onClick={() => void handleDeactivateLocation(location.id)}>
                          Deactivate
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))
              ) : (
                <p>No office locations configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`Departments (${configuration?.departments.length ?? 0})`}>
              {configuration?.departments.length ? (
                configuration.departments.map((department) => (
                  <div key={department.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {department.name}
                      {department.parent_department_name ? ` • Parent: ${department.parent_department_name}` : ' • Top level'}
                      {department.is_active ? ' • Active' : ' • Inactive'}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openDepartmentDialog(department)}>
                        Edit
                      </button>
                      {department.is_active ? (
                        <button type="button" className="btn-danger" onClick={() => void handleDeactivateDepartment(department.id)}>
                          Deactivate
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))
              ) : (
                <p>No departments configured.</p>
              )}
            </DetailListCard>
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Leave and attendance configuration"
        description="Leave cycles, plans, and on-duty policies visible to Control Tower."
        action={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/leave-cycles`)}>
              Manage cycles
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/leave-plans`)}>
              Manage plans
            </button>
            <button type="button" className="btn-primary" onClick={() => navigate(`/ct/organisations/${id}/on-duty-policies`)}>
              Manage OD policies
            </button>
          </div>
        }
      >
        {configurationLoading ? (
          <SkeletonTable rows={5} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-3">
            <DetailListCard title={`Leave cycles (${configuration?.leave_cycles.length ?? 0})`}>
              {configuration?.leave_cycles.length ? (
                configuration.leave_cycles.map((cycle) => (
                  <div key={cycle.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {cycle.name} • {startCase(cycle.cycle_type)}
                      {cycle.is_default ? ' • Default' : ''}
                      {cycle.is_active ? ' • Active' : ' • Inactive'}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openLeaveCycleDialog(cycle)}>
                        Quick edit
                      </button>
                      <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/leave-cycles`)}>
                        Open module
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p>No leave cycles configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`Leave plans (${configuration?.leave_plans.length ?? 0})`}>
              {configuration?.leave_plans.length ? (
                configuration.leave_plans.map((plan) => (
                  <div key={plan.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {plan.name} • {plan.leave_cycle?.name || 'No cycle'} • {plan.leave_types.length} leave types
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openLeavePlanDialog(plan)}>
                        Quick edit
                      </button>
                      <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/leave-plans/${plan.id}`)}>
                        Open builder
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p>No leave plans configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`On-duty policies (${configuration?.on_duty_policies.length ?? 0})`}>
              {configuration?.on_duty_policies.length ? (
                configuration.on_duty_policies.map((policy) => (
                  <div key={policy.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {policy.name}
                      {policy.is_default ? ' • Default' : ''}
                      {policy.is_active ? ' • Active' : ' • Inactive'}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openOnDutyPolicyDialog(policy)}>
                        Quick edit
                      </button>
                      <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/on-duty-policies/${policy.id}`)}>
                        Open builder
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p>No on-duty policies configured.</p>
              )}
            </DetailListCard>
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Approvals and communication"
        description="Approval workflow routing and employee noticeboard visibility from Control Tower."
        action={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/approval-workflows`)}>
              Manage workflows
            </button>
            <button type="button" className="btn-primary" onClick={() => navigate(`/ct/organisations/${id}/notices`)}>
              Manage notices
            </button>
          </div>
        }
      >
        {configurationLoading ? (
          <SkeletonTable rows={5} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <DetailListCard title={`Approval workflows (${configuration?.approval_workflows.length ?? 0})`}>
              {configuration?.approval_workflows.length ? (
                configuration.approval_workflows.map((workflow) => (
                  <div key={workflow.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {workflow.name} • {workflow.rules.length} rules • {workflow.stages.length} stages
                      {workflow.is_default ? ` • Default ${workflow.default_request_kind?.replace(/_/g, ' ')}` : ''}
                      {workflow.is_active ? ' • Active' : ' • Inactive'}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openWorkflowDialog(workflow)}>
                        Quick edit
                      </button>
                      <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/approval-workflows/${workflow.id}`)}>
                        Open builder
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p>No approval workflows configured.</p>
              )}
            </DetailListCard>
            <DetailListCard title={`Notices (${configuration?.notices.length ?? 0})`}>
              {configuration?.notices.length ? (
                configuration.notices.map((notice) => (
                  <div key={notice.id} className="space-y-2 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-3 py-3">
                    <p>
                      {notice.title} • {startCase(notice.status)}
                      {notice.published_at ? ` • ${formatDateTime(notice.published_at)}` : ''}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => openNoticeDialog(notice)}>
                        Quick edit
                      </button>
                      <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/notices/${notice.id}`)}>
                        Open builder
                      </button>
                      {notice.status !== 'PUBLISHED' ? (
                        <button type="button" className="btn-primary" onClick={() => void handlePublishNotice(notice.id)}>
                          Publish
                        </button>
                      ) : null}
                    </div>
                  </div>
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
    <SectionCard
      title="Audit timeline"
      description="Complete organisation-level audit activity visible to Control Tower."
      action={
        <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${id}/audit`)}>
          Open full explorer
        </button>
      }
    >
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
      {activeTab === 'onboarding' ? renderOnboardingTab() : null}
      {activeTab === 'attendance' ? renderAttendanceTab() : null}
      {activeTab === 'approvals' ? renderApprovalsTab() : null}
      {activeTab === 'holidays' ? renderHolidaysTab() : null}
      {activeTab === 'configuration' ? renderConfigurationTab() : null}
      {activeTab === 'audit' ? renderAuditTab() : null}
      {activeTab === 'notes' ? renderNotesTab() : null}

      <AppDialog
        open={profileDialogOpen}
        onOpenChange={setProfileDialogOpen}
        title="Edit organisation profile"
        description="Update the legal identity and country/currency defaults for this tenant."
      >
        <form onSubmit={handleSaveProfile} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-org-name">
              Organisation name
            </label>
            <input
              id="ct-org-name"
              className="field-input"
              value={profileForm?.name ?? ''}
              onChange={(event) => setProfileForm((current) => (current ? { ...current, name: event.target.value } : current))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="ct-org-pan">
              PAN number
            </label>
            <input
              id="ct-org-pan"
              className="field-input"
              value={profileForm?.pan_number ?? ''}
              onChange={(event) => setProfileForm((current) => (current ? { ...current, pan_number: event.target.value.toUpperCase() } : current))}
              required
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label">Country</label>
              <AppSelect
                value={profileForm?.country_code ?? DEFAULT_COUNTRY_OPTION.code}
                onValueChange={handleProfileCountryChange}
                options={COUNTRY_SELECT_OPTIONS}
              />
            </div>
            <div>
              <label className="field-label">Currency</label>
              <AppSelect
                value={profileForm?.currency ?? DEFAULT_COUNTRY_OPTION.defaultCurrency}
                onValueChange={(value) => {
                  setHasProfileCurrencyManualOverride(true)
                  setProfileForm((current) => (current ? { ...current, currency: value } : current))
                }}
                options={CURRENCY_SELECT_OPTIONS}
              />
            </div>
          </div>
          <div>
            <label className="field-label">Entity type</label>
            <AppSelect
              value={profileForm?.entity_type ?? organisation.entity_type}
              onValueChange={(value) =>
                setProfileForm((current) => (current ? { ...current, entity_type: value as OrganisationEntityType } : current))
              }
              options={ENTITY_TYPE_OPTIONS}
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setProfileDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={updateOrganisationMutation.isPending}>
              Save changes
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={bootstrapAdminDialogOpen}
        onOpenChange={setBootstrapAdminDialogOpen}
        title="Edit bootstrap admin"
        description="These details define the primary org-admin onboarding recipient until the first paid batch is confirmed."
      >
        <form onSubmit={handleSaveBootstrapAdmin} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="bootstrap-first-name">
                First name
              </label>
              <input
                id="bootstrap-first-name"
                className="field-input"
                value={bootstrapAdminForm?.first_name ?? ''}
                onChange={(event) =>
                  setBootstrapAdminForm((current) => (current ? { ...current, first_name: event.target.value } : current))
                }
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="bootstrap-last-name">
                Last name
              </label>
              <input
                id="bootstrap-last-name"
                className="field-input"
                value={bootstrapAdminForm?.last_name ?? ''}
                onChange={(event) =>
                  setBootstrapAdminForm((current) => (current ? { ...current, last_name: event.target.value } : current))
                }
                required
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="bootstrap-email">
              Email
            </label>
            <input
              id="bootstrap-email"
              className="field-input"
              type="email"
              value={bootstrapAdminForm?.email ?? ''}
              onChange={(event) =>
                setBootstrapAdminForm((current) => (current ? { ...current, email: event.target.value } : current))
              }
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="bootstrap-phone">
              Phone
            </label>
            <input
              id="bootstrap-phone"
              className="field-input"
              value={bootstrapAdminForm?.phone ?? ''}
              onChange={(event) =>
                setBootstrapAdminForm((current) => (current ? { ...current, phone: event.target.value } : current))
              }
              placeholder={`Must start with ${selectedProfileCountry.dialCode}`}
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setBootstrapAdminDialogOpen(false)}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={updateBootstrapAdminMutation.isPending || organisation.billing_status === 'PAID'}
            >
              Save changes
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={addressDialogOpen}
        onOpenChange={(open) => {
          setAddressDialogOpen(open)
          if (!open) {
            setEditingAddressId(null)
            setAddressForm(createEmptyAddressForm(selectedProfileCountry.code))
          }
        }}
        title={editingAddressId ? 'Edit address' : 'Add address'}
        description="Manage the registered, billing, and operational address directory used across the tenant."
        contentClassName="sm:w-[min(94vw,52rem)]"
      >
        <form onSubmit={handleSaveAddress} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label">Address type</label>
              <AppSelect
                value={addressForm.address_type}
                onValueChange={(value) =>
                  setAddressForm((current) => ({
                    ...current,
                    address_type: value as OrganisationAddressType,
                    label: mandatoryAddressTypes.includes(value as OrganisationAddressType) ? '' : current.label,
                  }))
                }
                options={ADDRESS_TYPE_OPTIONS}
              />
            </div>
            {!mandatoryAddressTypes.includes(addressForm.address_type) ? (
              <div>
                <label className="field-label" htmlFor="address-label">
                  Label
                </label>
                <input
                  id="address-label"
                  className="field-input"
                  value={addressForm.label}
                  onChange={(event) => setAddressForm((current) => ({ ...current, label: event.target.value }))}
                  required
                />
              </div>
            ) : null}
          </div>
          <div>
            <label className="field-label" htmlFor="address-line1">
              Address line 1
            </label>
            <input
              id="address-line1"
              className="field-input"
              value={addressForm.line1}
              onChange={(event) => setAddressForm((current) => ({ ...current, line1: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="address-line2">
              Address line 2
            </label>
            <input
              id="address-line2"
              className="field-input"
              value={addressForm.line2}
              onChange={(event) => setAddressForm((current) => ({ ...current, line2: event.target.value }))}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label">Country</label>
              <AppSelect
                value={addressForm.country_code}
                onValueChange={setAddressCountry}
                options={COUNTRY_SELECT_OPTIONS}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="address-city">
                City
              </label>
              <input
                id="address-city"
                className="field-input"
                value={addressForm.city}
                onChange={(event) => setAddressForm((current) => ({ ...current, city: event.target.value }))}
                required
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label">{addressRule.subdivisionLabel}</label>
              {addressSubdivisions.length > 0 ? (
                <AppSelect
                  value={addressForm.state_code || resolveSubdivisionCode(addressCountry.code, addressForm.state, '')}
                  onValueChange={setAddressState}
                  options={addressSubdivisions}
                  placeholder={`Select ${addressRule.subdivisionLabel.toLowerCase()}`}
                />
              ) : (
                <input
                  className="field-input"
                  value={addressForm.state}
                  onChange={(event) =>
                    setAddressForm((current) => ({
                      ...current,
                      state: event.target.value,
                      state_code: '',
                    }))
                  }
                  required
                />
              )}
            </div>
            <div>
              <label className="field-label" htmlFor="address-postal">
                {addressRule.postalLabel}
              </label>
              <input
                id="address-postal"
                className="field-input"
                value={addressForm.pincode}
                onChange={(event) => setAddressForm((current) => ({ ...current, pincode: event.target.value }))}
                required
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="address-tax-id">
              {getBillingTaxLabel(addressCountry.code)}
            </label>
            <input
              id="address-tax-id"
              className="field-input"
              value={addressForm.gstin}
              onChange={(event) => setAddressForm((current) => ({ ...current, gstin: event.target.value.toUpperCase() }))}
              placeholder={addressForm.address_type === 'BILLING' ? 'Required for billing where applicable' : 'Optional unless required by country rule'}
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setAddressDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createAddressMutation.isPending || updateAddressMutation.isPending}>
              {editingAddressId ? 'Save changes' : 'Create address'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={locationDialogOpen}
        onOpenChange={(open) => {
          setLocationDialogOpen(open)
          if (!open) {
            setEditingLocationId(null)
            setLocationForm(createLocationFormState())
          }
        }}
        title={editingLocationId ? 'Edit location' : 'Add location'}
        description="Every office location must point to an active organisation address."
      >
        <form onSubmit={handleSaveLocation} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-location-name">
              Location name
            </label>
            <input
              id="ct-location-name"
              className="field-input"
              value={locationForm.name}
              onChange={(event) => setLocationForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label">Linked address</label>
            <AppSelect
              value={locationForm.organisation_address_id}
              onValueChange={(value) => setLocationForm((current) => ({ ...current, organisation_address_id: value }))}
              options={organisation.addresses.filter((address) => address.is_active).map((address) => ({
                value: address.id,
                label: `${address.label} • ${address.city}, ${address.state}`,
              }))}
              placeholder="Select an organisation address"
            />
          </div>
          <AppCheckbox
            checked={locationForm.is_remote}
            onCheckedChange={(checked) => setLocationForm((current) => ({ ...current, is_remote: checked }))}
            label="Mark as remote office location"
          />
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setLocationDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createLocationMutation.isPending || updateLocationMutation.isPending}>
              {editingLocationId ? 'Save changes' : 'Create location'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={departmentDialogOpen}
        onOpenChange={(open) => {
          setDepartmentDialogOpen(open)
          if (!open) {
            setEditingDepartmentId(null)
            setDepartmentForm(createDepartmentFormState())
          }
        }}
        title={editingDepartmentId ? 'Edit department' : 'Add department'}
        description="Define the hierarchy and descriptions org admins will use for workforce assignment."
      >
        <form onSubmit={handleSaveDepartment} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-department-name">
              Department name
            </label>
            <input
              id="ct-department-name"
              className="field-input"
              value={departmentForm.name}
              onChange={(event) => setDepartmentForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="ct-department-description">
              Description
            </label>
            <textarea
              id="ct-department-description"
              className="field-textarea"
              value={departmentForm.description}
              onChange={(event) => setDepartmentForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div>
            <label className="field-label">Parent department</label>
            <AppSelect
              value={departmentForm.parent_department_id}
              onValueChange={(value) => setDepartmentForm((current) => ({ ...current, parent_department_id: value }))}
              options={departmentOptions}
              placeholder="No parent department"
            />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setDepartmentDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createDepartmentMutation.isPending || updateDepartmentMutation.isPending}>
              {editingDepartmentId ? 'Save changes' : 'Create department'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={leaveCycleDialogOpen}
        onOpenChange={(open) => {
          setLeaveCycleDialogOpen(open)
          if (!open) {
            setEditingLeaveCycleId(null)
            setLeaveCycleForm(createDefaultLeaveCycleForm())
          }
        }}
        title={editingLeaveCycleId ? 'Edit leave cycle' : 'Add leave cycle'}
        description="Control Tower can shape the leave year model used by this tenant."
      >
        <form onSubmit={handleSaveLeaveCycle} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-leave-cycle-name">
              Cycle name
            </label>
            <input
              id="ct-leave-cycle-name"
              className="field-input"
              value={leaveCycleForm.name}
              onChange={(event) => setLeaveCycleForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label">Cycle type</label>
            <AppSelect
              value={leaveCycleForm.cycle_type}
              onValueChange={(value) => setLeaveCycleForm((current) => ({ ...current, cycle_type: value }))}
              options={[
                { value: 'CALENDAR_YEAR', label: 'Calendar year' },
                { value: 'FINANCIAL_YEAR', label: 'Financial year' },
                { value: 'CUSTOM_FIXED_START', label: 'Custom fixed start' },
                { value: 'EMPLOYEE_JOINING_DATE', label: 'Employee joining date' },
              ]}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="ct-leave-cycle-month">
                Start month
              </label>
              <input
                id="ct-leave-cycle-month"
                className="field-input"
                type="number"
                min={1}
                max={12}
                value={leaveCycleForm.start_month}
                onChange={(event) => setLeaveCycleForm((current) => ({ ...current, start_month: Number(event.target.value) }))}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="ct-leave-cycle-day">
                Start day
              </label>
              <input
                id="ct-leave-cycle-day"
                className="field-input"
                type="number"
                min={1}
                max={31}
                value={leaveCycleForm.start_day}
                onChange={(event) => setLeaveCycleForm((current) => ({ ...current, start_day: Number(event.target.value) }))}
              />
            </div>
          </div>
          <AppCheckbox
            checked={leaveCycleForm.is_default}
            onCheckedChange={(checked) => setLeaveCycleForm((current) => ({ ...current, is_default: checked }))}
            label="Default leave cycle"
          />
          <AppCheckbox
            checked={leaveCycleForm.is_active}
            onCheckedChange={(checked) => setLeaveCycleForm((current) => ({ ...current, is_active: checked }))}
            label="Cycle is active"
          />
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setLeaveCycleDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createLeaveCycleMutation.isPending || updateLeaveCycleMutation.isPending}>
              {editingLeaveCycleId ? 'Save changes' : 'Create cycle'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={leavePlanDialogOpen}
        onOpenChange={(open) => {
          setLeavePlanDialogOpen(open)
          if (!open) {
            setEditingLeavePlanId(null)
            setLeavePlanForm(createLeavePlanDialogForm())
          }
        }}
        title={editingLeavePlanId ? 'Edit leave plan' : 'Add leave plan'}
        description="Manage the current leave-plan shape and its visible leave types from Control Tower."
        contentClassName="sm:w-[min(94vw,52rem)]"
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setLeavePlanDialogOpen(false)}>
              Cancel
            </button>
            <button
              type="submit"
              form="ct-leave-plan-form"
              className="btn-primary"
              disabled={createLeavePlanMutation.isPending || updateLeavePlanMutation.isPending}
            >
              {editingLeavePlanId ? 'Save changes' : 'Create plan'}
            </button>
          </div>
        }
      >
        <form id="ct-leave-plan-form" onSubmit={handleSaveLeavePlan} className="grid gap-4">
          <div>
            <label className="field-label">Leave cycle</label>
            <AppSelect
              value={leavePlanForm.leave_cycle_id}
              onValueChange={(value) => setLeavePlanForm((current) => ({ ...current, leave_cycle_id: value }))}
              options={leaveCycleOptions}
              placeholder="Select leave cycle"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="ct-leave-plan-name">
                Plan name
              </label>
              <input
                id="ct-leave-plan-name"
                className="field-input"
                value={leavePlanForm.name}
                onChange={(event) => setLeavePlanForm((current) => ({ ...current, name: event.target.value }))}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="ct-leave-plan-priority">
                Priority
              </label>
              <input
                id="ct-leave-plan-priority"
                className="field-input"
                type="number"
                min={0}
                value={leavePlanForm.priority}
                onChange={(event) => setLeavePlanForm((current) => ({ ...current, priority: Number(event.target.value) }))}
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="ct-leave-plan-description">
              Description
            </label>
            <textarea
              id="ct-leave-plan-description"
              className="field-textarea"
              value={leavePlanForm.description}
              onChange={(event) => setLeavePlanForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <AppCheckbox
            checked={leavePlanForm.is_default}
            onCheckedChange={(checked) => setLeavePlanForm((current) => ({ ...current, is_default: checked }))}
            label="Default leave plan"
          />
          <AppCheckbox
            checked={leavePlanForm.is_active}
            onCheckedChange={(checked) => setLeavePlanForm((current) => ({ ...current, is_active: checked }))}
            label="Plan is active"
          />
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <p className="field-label !mb-0">Leave types</p>
              <button
                type="button"
                className="btn-secondary"
                onClick={() =>
                  setLeavePlanForm((current) => ({
                    ...current,
                    leave_types: [
                      ...current.leave_types,
                      createEmptyLeaveTypeFormState(),
                    ],
                  }))
                }
              >
                Add leave type
              </button>
            </div>
            {leavePlanForm.leave_types.map((leaveType, index) => (
              <div key={`${leaveType.code || 'leave-type'}-${index}`} className="surface-muted rounded-[22px] p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="field-label">Leave type name</label>
                    <input
                      className="field-input"
                      value={leaveType.name}
                      onChange={(event) =>
                        setLeavePlanForm((current) => ({
                          ...current,
                          leave_types: current.leave_types.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, name: event.target.value } : item,
                          ),
                        }))
                      }
                      required
                    />
                  </div>
                  <div>
                    <label className="field-label">Code</label>
                    <input
                      className="field-input"
                      value={leaveType.code}
                      onChange={(event) =>
                        setLeavePlanForm((current) => ({
                          ...current,
                          leave_types: current.leave_types.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, code: event.target.value.toUpperCase() } : item,
                          ),
                        }))
                      }
                      required
                    />
                  </div>
                  <div>
                    <label className="field-label">Annual entitlement</label>
                    <input
                      className="field-input"
                      value={leaveType.annual_entitlement}
                      onChange={(event) =>
                        setLeavePlanForm((current) => ({
                          ...current,
                          leave_types: current.leave_types.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, annual_entitlement: event.target.value } : item,
                          ),
                        }))
                      }
                    />
                  </div>
                  <div>
                    <label className="field-label">Credit frequency</label>
                    <AppSelect
                      value={leaveType.credit_frequency}
                      onValueChange={(value) =>
                        setLeavePlanForm((current) => ({
                          ...current,
                          leave_types: current.leave_types.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, credit_frequency: value } : item,
                          ),
                        }))
                      }
                      options={leaveCreditFrequencyOptions}
                    />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <AppCheckbox
                    checked={leaveType.is_active}
                    onCheckedChange={(checked) =>
                      setLeavePlanForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, is_active: checked } : item,
                        ),
                      }))
                    }
                    label="Active"
                  />
                  <AppCheckbox
                    checked={leaveType.is_paid}
                    onCheckedChange={(checked) =>
                      setLeavePlanForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, is_paid: checked } : item,
                        ),
                      }))
                    }
                    label="Paid"
                  />
                </div>
              </div>
            ))}
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={onDutyPolicyDialogOpen}
        onOpenChange={(open) => {
          setOnDutyPolicyDialogOpen(open)
          if (!open) {
            setEditingOnDutyPolicyId(null)
            setOnDutyPolicyForm(createDefaultOnDutyPolicyForm())
          }
        }}
        title={editingOnDutyPolicyId ? 'Edit on-duty policy' : 'Add on-duty policy'}
        description="Control Tower can manage OD rules without touching employee requests."
      >
        <form onSubmit={handleSaveOnDutyPolicy} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-od-name">
              Policy name
            </label>
            <input
              id="ct-od-name"
              className="field-input"
              value={onDutyPolicyForm.name}
              onChange={(event) => setOnDutyPolicyForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="ct-od-description">
              Description
            </label>
            <textarea
              id="ct-od-description"
              className="field-textarea"
              value={onDutyPolicyForm.description}
              onChange={(event) => setOnDutyPolicyForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div className="grid gap-3">
            <AppCheckbox checked={onDutyPolicyForm.is_default} onCheckedChange={(checked) => setOnDutyPolicyForm((current) => ({ ...current, is_default: checked }))} label="Default policy" />
            <AppCheckbox checked={onDutyPolicyForm.is_active} onCheckedChange={(checked) => setOnDutyPolicyForm((current) => ({ ...current, is_active: checked }))} label="Policy is active" />
            <AppCheckbox checked={onDutyPolicyForm.allow_half_day} onCheckedChange={(checked) => setOnDutyPolicyForm((current) => ({ ...current, allow_half_day: checked }))} label="Allow half-day OD" />
            <AppCheckbox checked={onDutyPolicyForm.allow_time_range} onCheckedChange={(checked) => setOnDutyPolicyForm((current) => ({ ...current, allow_time_range: checked }))} label="Allow time-range OD" />
            <AppCheckbox checked={onDutyPolicyForm.requires_attachment} onCheckedChange={(checked) => setOnDutyPolicyForm((current) => ({ ...current, requires_attachment: checked }))} label="Require attachment" />
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setOnDutyPolicyDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createOnDutyPolicyMutation.isPending || updateOnDutyPolicyMutation.isPending}>
              {editingOnDutyPolicyId ? 'Save changes' : 'Create policy'}
            </button>
          </div>
        </form>
      </AppDialog>

      <AppDialog
        open={workflowDialogOpen}
        onOpenChange={(open) => {
          setWorkflowDialogOpen(open)
          if (!open) {
            setEditingWorkflowId(null)
            setWorkflowForm(createDefaultApprovalWorkflow())
          }
        }}
        title={editingWorkflowId ? 'Edit approval workflow' : 'Add approval workflow'}
        description="Manage workflow metadata and the current visible stage/rule structure from Control Tower."
        contentClassName="sm:w-[min(94vw,52rem)]"
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setWorkflowDialogOpen(false)}>
              Cancel
            </button>
            <button
              type="submit"
              form="ct-workflow-form"
              className="btn-primary"
              disabled={createWorkflowMutation.isPending || updateWorkflowMutation.isPending}
            >
              {editingWorkflowId ? 'Save changes' : 'Create workflow'}
            </button>
          </div>
        }
      >
        <form id="ct-workflow-form" onSubmit={handleSaveWorkflow} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-workflow-name">
              Workflow name
            </label>
            <input
              id="ct-workflow-name"
              className="field-input"
              value={workflowForm.name}
              onChange={(event) => setWorkflowForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="ct-workflow-description">
              Description
            </label>
            <textarea
              id="ct-workflow-description"
              className="field-textarea"
              value={workflowForm.description}
              onChange={(event) => setWorkflowForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
          <div className="grid gap-3">
            <AppCheckbox checked={workflowForm.is_default} onCheckedChange={(checked) => setWorkflowForm((current) => ({ ...current, is_default: checked }))} label="Default workflow" />
            <AppCheckbox checked={workflowForm.is_active} onCheckedChange={(checked) => setWorkflowForm((current) => ({ ...current, is_active: checked }))} label="Workflow is active" />
          </div>
          {workflowForm.is_default ? (
            <AppSelect
              value={workflowForm.default_request_kind ?? ''}
              onValueChange={(value) => setWorkflowForm((current) => ({ ...current, default_request_kind: value as ApprovalRequestKind }))}
              options={APPROVAL_REQUEST_KIND_OPTIONS.map((value) => ({ value, label: startCase(value) }))}
              placeholder="Default request kind"
            />
          ) : null}
          <SectionCard title="Rules" description="Lightweight rule editing keeps the current routing visible without entering employee actions.">
            <div className="space-y-3">
              {workflowForm.rules.map((rule, index) => (
                <div key={`${rule.name || 'rule'}-${index}`} className="surface-muted rounded-[20px] p-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <input
                      className="field-input"
                      value={rule.name}
                      onChange={(event) =>
                        setWorkflowForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, name: event.target.value } : item,
                          ),
                        }))
                      }
                      placeholder="Rule name"
                    />
                    <AppSelect
                      value={rule.request_kind}
                      onValueChange={(value) =>
                        setWorkflowForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, request_kind: value } : item,
                          ),
                        }))
                      }
                      options={[
                        { value: 'LEAVE', label: 'Leave' },
                        { value: 'ON_DUTY', label: 'On duty' },
                        { value: 'ATTENDANCE_REGULARIZATION', label: 'Attendance regularization' },
                      ]}
                    />
                    <input
                      className="field-input"
                      type="number"
                      min={0}
                      value={rule.priority}
                      onChange={(event) =>
                        setWorkflowForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, priority: Number(event.target.value) } : item,
                          ),
                        }))
                      }
                      placeholder="Priority"
                    />
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
          <SectionCard title="Stages" description="Stage ordering and approver routing remain editable from Control Tower.">
            <div className="space-y-3">
              {workflowForm.stages.map((stage, index) => (
                <div key={`${stage.name || 'stage'}-${index}`} className="surface-muted rounded-[20px] p-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <input
                      className="field-input"
                      value={stage.name}
                      onChange={(event) =>
                        setWorkflowForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, name: event.target.value } : item,
                          ),
                        }))
                      }
                      placeholder="Stage name"
                    />
                    <input
                      className="field-input"
                      type="number"
                      min={1}
                      value={stage.sequence}
                      onChange={(event) =>
                        setWorkflowForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, sequence: Number(event.target.value) } : item,
                          ),
                        }))
                      }
                    />
                    <AppSelect
                      value={stage.mode}
                      onValueChange={(value) =>
                        setWorkflowForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, mode: value } : item,
                          ),
                        }))
                      }
                      options={[
                        { value: 'ALL', label: 'All approvers' },
                        { value: 'ANY', label: 'Any approver' },
                      ]}
                    />
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        </form>
      </AppDialog>

      <AppDialog
        open={noticeDialogOpen}
        onOpenChange={(open) => {
          setNoticeDialogOpen(open)
          if (!open) {
            setEditingNoticeId(null)
            setNoticeForm(createDefaultNoticeForm())
          }
        }}
        title={editingNoticeId ? 'Edit notice' : 'Add notice'}
        description="Control Tower can publish or update the noticeboard configuration for this tenant."
      >
        <form onSubmit={handleSaveNotice} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="ct-notice-title">
              Title
            </label>
            <input
              id="ct-notice-title"
              className="field-input"
              value={noticeForm.title}
              onChange={(event) => setNoticeForm((current) => ({ ...current, title: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="ct-notice-body">
              Body
            </label>
            <textarea
              id="ct-notice-body"
              className="field-textarea"
              value={noticeForm.body}
              onChange={(event) => setNoticeForm((current) => ({ ...current, body: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label">Audience</label>
            <AppSelect
              value={noticeForm.audience_type}
              onValueChange={(value) => setNoticeForm((current) => ({ ...current, audience_type: value }))}
              options={noticeAudienceOptions}
            />
          </div>
          {noticeForm.audience_type === 'DEPARTMENTS' ? (
            <div className="grid gap-2">
              {noticeDepartmentOptions.map((department) => (
                <AppCheckbox
                  key={department.id}
                  id={`ct-notice-department-${department.id}`}
                  checked={noticeForm.department_ids.includes(department.id)}
                  onCheckedChange={(checked) =>
                    setNoticeForm((current) => ({
                      ...current,
                      department_ids: checked
                        ? [...current.department_ids, department.id]
                        : current.department_ids.filter((id) => id !== department.id),
                    }))
                  }
                  label={department.name}
                />
              ))}
            </div>
          ) : null}
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setNoticeDialogOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={createNoticeMutation.isPending || updateNoticeMutation.isPending}>
              {editingNoticeId ? 'Save changes' : 'Create notice'}
            </button>
          </div>
        </form>
      </AppDialog>

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
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setHolidayDialogOpen(false)}>
              Cancel
            </button>
            <button
              type="submit"
              form="ct-holiday-calendar-form"
              className="btn-primary"
              disabled={createHolidayMutation.isPending || updateHolidayMutation.isPending}
            >
              {editingHolidayId ? 'Save changes' : 'Save calendar'}
            </button>
          </div>
        }
      >
        <form id="ct-holiday-calendar-form" onSubmit={handleSaveHolidayCalendar} className="grid gap-4">
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
        </form>
      </AppDialog>

      <AppDialog
        open={employeeDetailOpen}
        onOpenChange={(open) => {
          setEmployeeDetailOpen(open)
          if (!open) setSelectedEmployeeId('')
        }}
        title={selectedEmployee?.full_name || 'Employee details'}
        description="Read-only, sanitised employment visibility from Control Tower."
      >
        {employeeDetailLoading || !selectedEmployee ? (
          <SkeletonFormBlock rows={5} />
        ) : (
          <div className="space-y-5">
            <InfoStack
              items={[
                { label: 'Employee code', value: selectedEmployee.employee_code },
                { label: 'Status', value: startCase(selectedEmployee.status) },
                { label: 'Onboarding', value: startCase(selectedEmployee.onboarding_status) },
                { label: 'Designation', value: selectedEmployee.designation },
                { label: 'Employment type', value: startCase(selectedEmployee.employment_type) },
                { label: 'Department', value: selectedEmployee.department_name },
                { label: 'Office location', value: selectedEmployee.office_location_name },
                { label: 'Reporting to', value: selectedEmployee.reporting_to_name },
                { label: 'Date of joining', value: formatDate(selectedEmployee.date_of_joining) },
                { label: 'Date of exit', value: formatDate(selectedEmployee.date_of_exit) },
              ]}
            />
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
