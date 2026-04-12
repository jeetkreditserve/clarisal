import type { OnboardingProgress } from '@/types/hr'
import type { OrganisationDetail } from '@/types/organisation'

export type WizardPlanTier = 'STARTER' | 'GROWTH' | 'ENTERPRISE'
export type WizardBillingCycle = 'MONTHLY' | 'QUARTERLY' | 'ANNUAL'
export type WizardStepId = 'profile' | 'licences' | 'features' | 'payroll' | 'seed' | 'admin'

export interface WizardStepDefinition {
  id: WizardStepId
  title: string
  description: string
}

export const WIZARD_STEPS: WizardStepDefinition[] = [
  {
    id: 'profile',
    title: 'Organisation Profile',
    description: 'Capture the legal profile, statutory addresses, and bootstrap admin details.',
  },
  {
    id: 'licences',
    title: 'Licence Configuration',
    description: 'Set the commercial plan, seat count, billing cycle, and first draft batch.',
  },
  {
    id: 'features',
    title: 'Feature Flags',
    description: 'Choose which workforce modules should be provisioned from day one.',
  },
  {
    id: 'payroll',
    title: 'Payroll & Compliance Settings',
    description: 'Set the compliance identifiers that drive payroll filings and statutory setup.',
  },
  {
    id: 'seed',
    title: 'Seed Payroll Masters',
    description: 'Seed repeatable payroll and document defaults before the org admin takes over.',
  },
  {
    id: 'admin',
    title: 'Invite First Admin',
    description: 'Confirm the first admin contact and decide whether to invite now or later.',
  },
]

export const PLAN_TIER_PRICING: Record<WizardPlanTier, string> = {
  STARTER: '999.00',
  GROWTH: '1499.00',
  ENTERPRISE: '2499.00',
}

export const FEATURE_FLAG_DESCRIPTIONS: Record<string, string> = {
  ATTENDANCE: 'Daily attendance, punch capture, and attendance imports.',
  APPROVALS: 'Approvals, action routing, and request governance.',
  BIOMETRICS: 'Biometric devices and attendance-source integrations.',
  NOTICES: 'Operational notices and employee communications.',
  PAYROLL: 'Payroll runs, payslips, taxes, and statutory exports.',
  PERFORMANCE: 'Goal cycles, reviews, and performance workflows.',
  RECRUITMENT: 'Candidates, offers, and hiring handoff.',
  REPORTS: 'Operational dashboards and exports.',
  TIMEOFF: 'Leave cycles, leave plans, holidays, and on-duty policies.',
}

const WIZARD_NOTE_PREFIX = '[wizard]'

export function inferPlanTierFromPrice(price: string | null | undefined): WizardPlanTier {
  const normalizedPrice = Number(price ?? 0).toFixed(2)
  const match = Object.entries(PLAN_TIER_PRICING).find(([, tierPrice]) => tierPrice === normalizedPrice)
  return (match?.[0] as WizardPlanTier | undefined) ?? 'GROWTH'
}

export function buildWizardBatchNote(
  note: string,
  metadata: { planTier: WizardPlanTier; billingCycle: WizardBillingCycle; trialEndDate?: string | null },
) {
  const cleanedNote = stripWizardBatchMetadata(note).trim()
  const metadataParts = [
    `tier=${metadata.planTier}`,
    `cycle=${metadata.billingCycle}`,
    metadata.trialEndDate ? `trial_end=${metadata.trialEndDate}` : '',
  ].filter(Boolean)

  return [`${WIZARD_NOTE_PREFIX} ${metadataParts.join(' ')}`, cleanedNote].filter(Boolean).join('\n')
}

export function stripWizardBatchMetadata(note: string | null | undefined) {
  return (note ?? '')
    .split('\n')
    .filter((line) => !line.trim().startsWith(WIZARD_NOTE_PREFIX))
    .join('\n')
}

export function parseWizardBatchNote(note: string | null | undefined) {
  const metadataLine = (note ?? '')
    .split('\n')
    .find((line) => line.trim().startsWith(WIZARD_NOTE_PREFIX))
  const metadata: { planTier?: WizardPlanTier; billingCycle?: WizardBillingCycle; trialEndDate?: string | null } = {}

  if (!metadataLine) {
    return metadata
  }

  for (const part of metadataLine.replace(WIZARD_NOTE_PREFIX, '').trim().split(/\s+/)) {
    const [key, value] = part.split('=')
    if (!value) continue
    if (key === 'tier') metadata.planTier = value as WizardPlanTier
    if (key === 'cycle') metadata.billingCycle = value as WizardBillingCycle
    if (key === 'trial_end') metadata.trialEndDate = value
  }

  return metadata
}

export function buildPlanDefaults(planTier: WizardPlanTier) {
  return {
    ATTENDANCE: true,
    APPROVALS: true,
    BIOMETRICS: planTier !== 'STARTER',
    NOTICES: planTier !== 'STARTER',
    PAYROLL: true,
    PERFORMANCE: planTier === 'ENTERPRISE',
    RECRUITMENT: planTier !== 'STARTER',
    REPORTS: true,
    TIMEOFF: true,
  }
}

function isPayrollSeeded(progress: OnboardingProgress | undefined) {
  return Boolean(progress?.steps.find((step) => step.step === 'PAYROLL')?.is_completed)
}

function hasPersistedFeatureFlagChoices(organisation: OrganisationDetail) {
  return organisation.feature_flags.length > 0 && organisation.feature_flags.every((flag) => !flag.is_default)
}

function hasCompletedAdminReview(organisation: OrganisationDetail) {
  const admin = organisation.bootstrap_admin ?? organisation.primary_admin
  if (!admin) {
    return false
  }
  if (admin.status !== 'DRAFT') {
    return true
  }
  const adminModifiedAt = Date.parse(admin.modified_at ?? '')
  const orgCreatedAt = Date.parse(organisation.created_at ?? '')
  return Number.isFinite(adminModifiedAt) && Number.isFinite(orgCreatedAt) && adminModifiedAt > orgCreatedAt
}

export function getWizardResumeStepIndex(
  organisation: OrganisationDetail | undefined,
  progress: OnboardingProgress | undefined,
) {
  if (!organisation) {
    return 0
  }
  if (organisation.licence_batches.length === 0) {
    return 1
  }
  if (!hasPersistedFeatureFlagChoices(organisation)) {
    return 2
  }
  if (!((organisation.tan_number ?? '').trim() || organisation.esi_branch_code.trim())) {
    return 3
  }
  if (!isPayrollSeeded(progress)) {
    return 4
  }
  if (!hasCompletedAdminReview(organisation)) {
    return 5
  }
  return WIZARD_STEPS.length
}
