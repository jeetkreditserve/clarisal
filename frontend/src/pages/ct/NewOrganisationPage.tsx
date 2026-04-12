import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { WizardProgress } from '@/components/wizard/WizardProgress'
import { WizardStep } from '@/components/wizard/WizardStep'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import {
  useCreateLicenceBatch,
  useCreateOrganisation,
  useCreateOrganisationAddress,
  useCtOrgOnboardingProgress,
  useInviteOrgAdmin,
  useOrganisation,
  useSeedCtOrgMasters,
  useUpdateCtOrganisationFeatureFlags,
  useUpdateLicenceBatch,
  useUpdateOrganisation,
  useUpdateOrganisationAddress,
} from '@/hooks/useCtOrganisations'
import type { OrganisationAddressInput } from '@/lib/api/organisations'
import {
  buildPlanDefaults,
  buildWizardBatchNote,
  FEATURE_FLAG_DESCRIPTIONS,
  getWizardResumeStepIndex,
  inferPlanTierFromPrice,
  parseWizardBatchNote,
  PLAN_TIER_PRICING,
  type WizardBillingCycle,
  type WizardPlanTier,
  WIZARD_STEPS,
} from '@/lib/ctOnboardingWizard'
import {
  getAddressCountryName,
  getAddressCountryOption,
  getAddressCountryRule,
  getBillingTaxLabel,
  getSubdivisionName,
  getSubdivisionOptions,
  isBillingTaxRequired,
  resolveCountryCode,
  resolveSubdivisionCode,
  validateBillingTaxIdentifier,
  validatePostalCodeForCountry,
} from '@/lib/addressMetadata'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import {
  COUNTRY_OPTIONS,
  CURRENCY_OPTIONS,
  DEFAULT_COUNTRY_CODE,
  DEFAULT_COUNTRY_OPTION,
  ORGANISATION_ENTITY_TYPE_OPTIONS,
  getCountryOption,
  validatePhoneForCountry,
} from '@/lib/organisationMetadata'
import type { OrganisationDetail, OrganisationEntityType } from '@/types/organisation'

type AddressFormState = OrganisationAddressInput & {
  country_code: string
  state_code: string
}

type AddressFieldKey = keyof AddressFormState

type ProfileFormState = {
  name: string
  pan_number: string
  country_code: string
  currency: string
  entity_type: OrganisationEntityType
  primary_admin: {
    first_name: string
    last_name: string
    email: string
    phone: string
  }
  addresses: {
    REGISTERED: AddressFormState
    BILLING: AddressFormState
  }
}

type LicenceFormState = {
  plan_tier: WizardPlanTier
  seat_count: string
  billing_cycle: WizardBillingCycle
  start_date: string
  trial_end_date: string
  note: string
}

type PayrollSettingsState = {
  tan_number: string
  esi_branch_code: string
}

type SeedSummary = {
  payroll_components: {
    created_count: number
    existing_count: number
    total_count: number
    codes: string[]
  }
  document_types: {
    created_count: number
    existing_count: number
    total_count: number
  }
}

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

const PLAN_TIER_OPTIONS = [
  { value: 'STARTER', label: 'Starter', hint: 'Lean rollout for smaller teams' },
  { value: 'GROWTH', label: 'Growth', hint: 'Balanced default for scaling teams' },
  { value: 'ENTERPRISE', label: 'Enterprise', hint: 'Broadest module footprint and reporting' },
]

const BILLING_CYCLE_OPTIONS = [
  { value: 'MONTHLY', label: 'Monthly' },
  { value: 'QUARTERLY', label: 'Quarterly' },
  { value: 'ANNUAL', label: 'Annual' },
]

const today = new Date().toISOString().slice(0, 10)

const emptyAddress = (
  address_type: 'REGISTERED' | 'BILLING',
  countryCode = DEFAULT_COUNTRY_CODE,
): AddressFormState => ({
  address_type,
  line1: '',
  line2: '',
  city: '',
  state: '',
  state_code: '',
  country: getAddressCountryName(countryCode),
  country_code: countryCode,
  pincode: '',
  gstin: '',
})

function createEmptyProfileForm(): ProfileFormState {
  return {
    name: '',
    pan_number: '',
    country_code: DEFAULT_COUNTRY_CODE,
    currency: DEFAULT_COUNTRY_OPTION.defaultCurrency,
    entity_type: 'PRIVATE_LIMITED',
    primary_admin: {
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
    },
    addresses: {
      REGISTERED: emptyAddress('REGISTERED'),
      BILLING: emptyAddress('BILLING'),
    },
  }
}

function createEmptyLicenceForm(): LicenceFormState {
  return {
    plan_tier: 'GROWTH',
    seat_count: '1',
    billing_cycle: 'MONTHLY',
    start_date: today,
    trial_end_date: '',
    note: '',
  }
}

function createEmptyPayrollSettings(): PayrollSettingsState {
  return {
    tan_number: '',
    esi_branch_code: '',
  }
}

const syncAddressCountry = (address: AddressFormState, previousCountryCode: string, nextCountryCode: string) => {
  if (!address.country_code || address.country_code === previousCountryCode) {
    return {
      ...address,
      state: '',
      state_code: '',
      country: getAddressCountryName(nextCountryCode),
      country_code: nextCountryCode,
      pincode: '',
    }
  }
  return address
}

const buildBillingAddress = (
  registeredAddress: AddressFormState,
  billingDraft: AddressFormState,
  useRegisteredAddress: boolean,
): AddressFormState => {
  if (!useRegisteredAddress) {
    return billingDraft
  }
  return {
    ...registeredAddress,
    address_type: 'BILLING',
  }
}

function formatDateInput(dateValue: Date) {
  return dateValue.toISOString().slice(0, 10)
}

function calculateBillingMonths(startDate: string, endDate: string) {
  if (!startDate || !endDate) return 0
  const start = new Date(`${startDate}T00:00:00Z`)
  const end = new Date(`${endDate}T00:00:00Z`)
  const diffMs = end.getTime() - start.getTime()
  if (Number.isNaN(diffMs) || diffMs < 0) return 0
  const totalDays = Math.floor(diffMs / (24 * 60 * 60 * 1000)) + 1
  return Math.max(1, Math.ceil(totalDays / 30))
}

function calculateBillingEndDate(startDate: string, billingCycle: WizardBillingCycle) {
  const start = new Date(`${startDate || today}T00:00:00Z`)
  const end = new Date(start)
  const monthDelta =
    billingCycle === 'MONTHLY' ? 1 : billingCycle === 'QUARTERLY' ? 3 : 12
  end.setUTCMonth(end.getUTCMonth() + monthDelta)
  end.setUTCDate(end.getUTCDate() - 1)
  return formatDateInput(end)
}

function inferBillingCycle(startDate: string | undefined, endDate: string | undefined): WizardBillingCycle {
  if (!startDate || !endDate) {
    return 'MONTHLY'
  }
  const days =
    (Date.parse(`${endDate}T00:00:00Z`) - Date.parse(`${startDate}T00:00:00Z`)) / (24 * 60 * 60 * 1000) + 1
  if (days > 180) return 'ANNUAL'
  if (days > 45) return 'QUARTERLY'
  return 'MONTHLY'
}

function formatMoney(value: number | string, currency = 'INR') {
  const numeric = typeof value === 'number' ? value : Number(value)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(numeric) ? numeric : 0)
}

function areAddressesEquivalent(left: AddressFormState, right: AddressFormState) {
  return (
    left.line1 === right.line1 &&
    (left.line2 ?? '') === (right.line2 ?? '') &&
    left.city === right.city &&
    left.state === right.state &&
    left.state_code === right.state_code &&
    left.country_code === right.country_code &&
    left.pincode === right.pincode &&
    (left.gstin ?? '') === (right.gstin ?? '')
  )
}

function getOrganisationAddress(organisation: OrganisationDetail, addressType: 'REGISTERED' | 'BILLING') {
  const existing = organisation.addresses.find((address) => address.address_type === addressType && address.is_active)
  if (!existing) {
    return emptyAddress(addressType, organisation.country_code)
  }
  return {
    address_type: addressType,
    label: existing.label,
    line1: existing.line1,
    line2: existing.line2 ?? '',
    city: existing.city,
    state: existing.state,
    state_code: existing.state_code,
    country: existing.country,
    country_code: existing.country_code,
    pincode: existing.pincode,
    gstin: existing.gstin ?? '',
  }
}

function buildFeatureSelectionState(organisation: OrganisationDetail | null, planTier: WizardPlanTier) {
  if (!organisation) {
    return buildPlanDefaults(planTier)
  }
  return organisation.feature_flags.reduce<Record<string, boolean>>((acc, flag) => {
    acc[flag.feature_code] = flag.is_enabled
    return acc
  }, {})
}

export function NewOrganisationPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialResumeIdRef = useRef(searchParams.get('organisationId'))
  const hydratedResumeIdRef = useRef<string | null>(null)

  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [profileForm, setProfileForm] = useState<ProfileFormState>(createEmptyProfileForm)
  const [licenceForm, setLicenceForm] = useState<LicenceFormState>(createEmptyLicenceForm)
  const [featureSelections, setFeatureSelections] = useState<Record<string, boolean>>(buildPlanDefaults('GROWTH'))
  const [payrollSettings, setPayrollSettings] = useState<PayrollSettingsState>(createEmptyPayrollSettings)
  const [billingSameAsRegistered, setBillingSameAsRegistered] = useState(false)
  const [hasCurrencyManualOverride, setHasCurrencyManualOverride] = useState(false)
  const [hasFeatureOverrides, setHasFeatureOverrides] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [workingOrganisation, setWorkingOrganisation] = useState<OrganisationDetail | null>(null)
  const [draftBatchId, setDraftBatchId] = useState<string | null>(null)
  const [seedSummary, setSeedSummary] = useState<SeedSummary | null>(null)

  const organisationId = workingOrganisation?.id ?? initialResumeIdRef.current ?? ''
  const organisationQuery = useOrganisation(organisationId)
  const organisation = workingOrganisation ?? organisationQuery.data ?? null
  const onboardingProgressQuery = useCtOrgOnboardingProgress(organisation?.id ?? '', Boolean(organisation?.id))
  const onboardingProgress = onboardingProgressQuery.data

  const createOrganisationMutation = useCreateOrganisation()
  const updateOrganisationMutation = useUpdateOrganisation(organisation?.id ?? '')
  const createAddressMutation = useCreateOrganisationAddress(organisation?.id ?? '')
  const updateAddressMutation = useUpdateOrganisationAddress(organisation?.id ?? '')
  const createLicenceBatchMutation = useCreateLicenceBatch(organisation?.id ?? '')
  const updateLicenceBatchMutation = useUpdateLicenceBatch(organisation?.id ?? '')
  const updateFeatureFlagsMutation = useUpdateCtOrganisationFeatureFlags(organisation?.id ?? '')
  const seedMastersMutation = useSeedCtOrgMasters(organisation?.id ?? '')
  const inviteAdminMutation = useInviteOrgAdmin(organisation?.id ?? '')

  const selectedCountry = getCountryOption(profileForm.country_code) ?? DEFAULT_COUNTRY_OPTION
  const effectiveBillingAddress = buildBillingAddress(
    profileForm.addresses.REGISTERED,
    profileForm.addresses.BILLING,
    billingSameAsRegistered,
  )
  const batchEndDate = calculateBillingEndDate(licenceForm.start_date, licenceForm.billing_cycle)
  const billingMonths = calculateBillingMonths(licenceForm.start_date, batchEndDate)
  const pricePerSeat = Number(PLAN_TIER_PRICING[licenceForm.plan_tier] ?? '0')
  const totalPrice = Number(licenceForm.seat_count || '0') * pricePerSeat * billingMonths
  const featureFlagOptions = organisation?.feature_flags.length
    ? organisation.feature_flags
    : Object.keys(buildPlanDefaults(licenceForm.plan_tier)).map((featureCode) => ({
        feature_code: featureCode,
        label: featureCode.split('_').join(' '),
        is_enabled: Boolean(featureSelections[featureCode]),
        is_default: true,
      }))
  const wizardResumeStepIndex = getWizardResumeStepIndex(organisation ?? undefined, onboardingProgress)
  const seedStepReady = Boolean(seedSummary) || wizardResumeStepIndex > 4
  const shouldShowLoadingState =
    Boolean(initialResumeIdRef.current) &&
    (organisationQuery.isLoading || (organisation && !onboardingProgressQuery.isFetched))

  useEffect(() => {
    if (hasFeatureOverrides) {
      return
    }
    setFeatureSelections(buildPlanDefaults(licenceForm.plan_tier))
  }, [hasFeatureOverrides, licenceForm.plan_tier])

  useEffect(() => {
    if (!organisation || !initialResumeIdRef.current) {
      return
    }
    if (!onboardingProgressQuery.isFetched || hydratedResumeIdRef.current === organisation.id) {
      return
    }

    hydratedResumeIdRef.current = organisation.id
    const registeredAddress = getOrganisationAddress(organisation, 'REGISTERED')
    const billingAddress = getOrganisationAddress(organisation, 'BILLING')
    const admin = organisation.bootstrap_admin ?? organisation.primary_admin
    const draftBatch = organisation.licence_batches.find((batch) => batch.payment_status === 'DRAFT') ?? organisation.licence_batches[0] ?? null
    const parsedBatchNote = parseWizardBatchNote(draftBatch?.note)
    const planTier = parsedBatchNote.planTier ?? inferPlanTierFromPrice(draftBatch?.price_per_licence_per_month)
    const billingCycle = parsedBatchNote.billingCycle ?? inferBillingCycle(draftBatch?.start_date, draftBatch?.end_date)

    setProfileForm({
      name: organisation.name,
      pan_number: organisation.pan_number ?? '',
      country_code: organisation.country_code,
      currency: organisation.currency,
      entity_type: organisation.entity_type,
      primary_admin: {
        first_name: admin?.first_name ?? '',
        last_name: admin?.last_name ?? '',
        email: admin?.email ?? '',
        phone: admin?.phone ?? '',
      },
      addresses: {
        REGISTERED: registeredAddress,
        BILLING: billingAddress,
      },
    })
    setBillingSameAsRegistered(areAddressesEquivalent(registeredAddress, billingAddress))
    setHasCurrencyManualOverride(true)
    setLicenceForm({
      plan_tier: planTier,
      seat_count: draftBatch ? String(draftBatch.quantity) : '1',
      billing_cycle: billingCycle,
      start_date: draftBatch?.start_date ?? organisation.batch_defaults.start_date,
      trial_end_date: parsedBatchNote.trialEndDate ?? '',
      note: draftBatch?.note ? draftBatch.note.split('\n').slice(1).join('\n').trim() : '',
    })
    setFeatureSelections(buildFeatureSelectionState(organisation, planTier))
    setHasFeatureOverrides(true)
    setPayrollSettings({
      tan_number: organisation.tan_number ?? '',
      esi_branch_code: organisation.esi_branch_code,
    })
    setDraftBatchId(draftBatch?.id ?? null)

    const nextStepIndex = Math.min(wizardResumeStepIndex, WIZARD_STEPS.length - 1)
    setCurrentStep(nextStepIndex)
    setCompletedSteps(Array.from({ length: Math.min(wizardResumeStepIndex, WIZARD_STEPS.length) }, (_, index) => index))
  }, [organisation, onboardingProgressQuery.isFetched, wizardResumeStepIndex])

  const setField =
    (field: 'name' | 'pan_number') =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setProfileForm((current) => ({ ...current, [field]: event.target.value }))

  const setPrimaryAdminField =
    (field: 'first_name' | 'last_name' | 'email' | 'phone') =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setProfileForm((current) => ({
        ...current,
        primary_admin: {
          ...current.primary_admin,
          [field]: event.target.value,
        },
      }))

  const setOrganisationSelectField = (field: 'currency' | 'entity_type', value: string) => {
    setProfileForm((current) => ({ ...current, [field]: value }))
    if (field === 'currency') {
      setHasCurrencyManualOverride(true)
    }
  }

  const handleCountryChange = (nextCountryCode: string) => {
    setProfileForm((current) => {
      const previousCountry = getCountryOption(current.country_code) ?? DEFAULT_COUNTRY_OPTION
      const nextCountry = getCountryOption(nextCountryCode) ?? DEFAULT_COUNTRY_OPTION
      const shouldAutoUpdateCurrency =
        !hasCurrencyManualOverride || current.currency === previousCountry.defaultCurrency

      return {
        ...current,
        country_code: nextCountryCode,
        currency: shouldAutoUpdateCurrency ? nextCountry.defaultCurrency : current.currency,
        addresses: {
          REGISTERED: syncAddressCountry(current.addresses.REGISTERED, previousCountry.code, nextCountry.code),
          BILLING: syncAddressCountry(current.addresses.BILLING, previousCountry.code, nextCountry.code),
        },
      }
    })
    if (!hasCurrencyManualOverride || profileForm.currency === selectedCountry.defaultCurrency) {
      setHasCurrencyManualOverride(false)
    }
  }

  const setAddressField =
    (addressType: 'REGISTERED' | 'BILLING', field: AddressFieldKey) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setProfileForm((current) => ({
        ...current,
        addresses: {
          ...current.addresses,
          [addressType]: {
            ...current.addresses[addressType],
            [field]: event.target.value,
          },
        },
      }))

  const setAddressCountry = (addressType: 'REGISTERED' | 'BILLING', countryCode: string) => {
    setProfileForm((current) => ({
      ...current,
      addresses: {
        ...current.addresses,
        [addressType]: {
          ...current.addresses[addressType],
          country_code: countryCode,
          country: getAddressCountryName(countryCode),
          state: '',
          state_code: '',
          pincode: '',
          gstin: current.addresses[addressType].gstin ?? '',
        },
      },
    }))
  }

  const setAddressState = (addressType: 'REGISTERED' | 'BILLING', stateCode: string) => {
    const countryCode = profileForm.addresses[addressType].country_code
    setProfileForm((current) => ({
      ...current,
      addresses: {
        ...current.addresses,
        [addressType]: {
          ...current.addresses[addressType],
          state_code: stateCode,
          state: getSubdivisionName(countryCode, stateCode, ''),
        },
      },
    }))
  }

  const addressErrorKey = (addressType: 'REGISTERED' | 'BILLING', field: string) => `${addressType}.${field}`

  const validateProfileStep = () => {
    const nextErrors: Record<string, string> = {}
    const phoneError = validatePhoneForCountry(profileForm.primary_admin.phone, profileForm.country_code)
    if (phoneError) {
      nextErrors['primary_admin.phone'] = phoneError
    }

    ;(['REGISTERED', 'BILLING'] as const).forEach((addressType) => {
      const address = addressType === 'BILLING' ? effectiveBillingAddress : profileForm.addresses[addressType]
      const countryCode = resolveCountryCode(address.country_code || address.country || profileForm.country_code)
      const stateCode = resolveSubdivisionCode(countryCode, address.state, address.state_code)

      const postalError = validatePostalCodeForCountry(address.pincode, countryCode)
      if (postalError) {
        nextErrors[addressErrorKey(addressType, 'pincode')] = postalError
      }

      const billingTaxError = validateBillingTaxIdentifier({
        addressType,
        countryCode,
        stateCode,
        panNumber: profileForm.pan_number,
        identifier: address.gstin,
      })
      if (billingTaxError) {
        const targetAddressType = billingSameAsRegistered && addressType === 'BILLING' ? 'REGISTERED' : addressType
        nextErrors[addressErrorKey(targetAddressType, 'gstin')] = billingTaxError
      }
    })

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const markStepComplete = (stepIndex: number) => {
    setCompletedSteps((current) => Array.from(new Set([...current, stepIndex])).sort((left, right) => left - right))
  }

  const syncAddressesForOrganisation = async (targetOrganisation: OrganisationDetail, addresses: AddressFormState[]) => {
    const results = await Promise.all(
      addresses.map(async (address) => {
        const existingAddress = targetOrganisation.addresses.find(
          (item) => item.address_type === address.address_type && item.is_active,
        )
        if (existingAddress) {
          return updateAddressMutation.mutateAsync({
            addressId: existingAddress.id,
            payload: address,
          })
        }
        return createAddressMutation.mutateAsync(address)
      }),
    )

    return {
      ...targetOrganisation,
      addresses: [
        ...targetOrganisation.addresses.filter(
          (item) => !results.some((updatedAddress) => updatedAddress.address_type === item.address_type),
        ),
        ...results,
      ],
    }
  }

  const handleProfileStep = async () => {
    setError(null)
    if (!validateProfileStep()) {
      return
    }

    try {
      setFieldErrors({})
      const payload = {
        name: profileForm.name,
        pan_number: profileForm.pan_number,
        country_code: profileForm.country_code,
        currency: profileForm.currency,
        entity_type: profileForm.entity_type,
        billing_same_as_registered: billingSameAsRegistered,
        primary_admin: profileForm.primary_admin,
        addresses: [profileForm.addresses.REGISTERED, effectiveBillingAddress],
      }

      if (!organisation) {
        const createdOrganisation = await createOrganisationMutation.mutateAsync(payload)
        setWorkingOrganisation(createdOrganisation)
        setSearchParams({ organisationId: createdOrganisation.id })
        setLicenceForm((current) => ({
          ...current,
          start_date: createdOrganisation.batch_defaults.start_date || current.start_date,
        }))
        toast.success('Organisation shell created.')
      } else {
        const updatedOrganisation = await updateOrganisationMutation.mutateAsync({
          name: payload.name,
          pan_number: payload.pan_number,
          country_code: payload.country_code,
          currency: payload.currency,
          entity_type: payload.entity_type,
          primary_admin: payload.primary_admin,
        })
        const organisationWithAddresses = await syncAddressesForOrganisation(updatedOrganisation, payload.addresses)
        setWorkingOrganisation(organisationWithAddresses)
        toast.success('Organisation profile updated.')
      }

      markStepComplete(0)
      setCurrentStep(1)
    } catch (err: unknown) {
      setFieldErrors(getFieldErrors(err))
      setError(getErrorMessage(err, 'Failed to save the organisation profile.'))
    }
  }

  const handleLicenceStep = async () => {
    if (!organisation) {
      return
    }
    setError(null)

    try {
      const payload = {
        quantity: Number(licenceForm.seat_count || '0'),
        price_per_licence_per_month: PLAN_TIER_PRICING[licenceForm.plan_tier],
        start_date: licenceForm.start_date,
        end_date: batchEndDate,
        note: buildWizardBatchNote(licenceForm.note, {
          planTier: licenceForm.plan_tier,
          billingCycle: licenceForm.billing_cycle,
          trialEndDate: licenceForm.trial_end_date || null,
        }),
      }

      const savedBatch = draftBatchId
        ? await updateLicenceBatchMutation.mutateAsync({ batchId: draftBatchId, payload })
        : await createLicenceBatchMutation.mutateAsync(payload)

      setDraftBatchId(savedBatch.id)
      setWorkingOrganisation((current) => {
        if (!current) {
          return current
        }
        const nextBatches = draftBatchId
          ? current.licence_batches.map((batch) => (batch.id === savedBatch.id ? savedBatch : batch))
          : [savedBatch, ...current.licence_batches]
        return {
          ...current,
          licence_batches: nextBatches,
        }
      })
      toast.success('Draft licence batch saved.')
      markStepComplete(1)
      setCurrentStep(2)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Unable to save the licence configuration.'))
    }
  }

  const handleFeatureFlagStep = async () => {
    if (!organisation) {
      return
    }
    setError(null)

    try {
      const updatedFlags = await updateFeatureFlagsMutation.mutateAsync(
        Object.entries(featureSelections).map(([feature_code, is_enabled]) => ({
          feature_code,
          is_enabled,
        })),
      )
      setWorkingOrganisation((current) => (current ? { ...current, feature_flags: updatedFlags } : current))
      toast.success('Feature flags saved.')
      markStepComplete(2)
      setCurrentStep(3)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Unable to save feature flags.'))
    }
  }

  const handlePayrollSettingsStep = async () => {
    if (!organisation) {
      return
    }
    setError(null)

    try {
      const updatedOrganisation = await updateOrganisationMutation.mutateAsync({
        tan_number: payrollSettings.tan_number,
        esi_branch_code: payrollSettings.esi_branch_code,
      })
      setWorkingOrganisation(updatedOrganisation)
      toast.success('Payroll settings saved.')
      markStepComplete(3)
      setCurrentStep(4)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Unable to save payroll settings.'))
    }
  }

  const handleSeedDefaults = async () => {
    if (!organisation) {
      return
    }
    setError(null)

    try {
      const response = await seedMastersMutation.mutateAsync()
      setSeedSummary(response.seeded)
      await onboardingProgressQuery.refetch()
      toast.success('Default masters seeded.')
      markStepComplete(4)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Unable to seed default masters.'))
    }
  }

  const handleFinish = async (sendInvite: boolean) => {
    if (!organisation) {
      return
    }
    setError(null)

    try {
      const updatedOrganisation = await updateOrganisationMutation.mutateAsync({
        primary_admin: profileForm.primary_admin,
      })
      setWorkingOrganisation(updatedOrganisation)
      if (sendInvite && (updatedOrganisation.status === 'PAID' || updatedOrganisation.status === 'ACTIVE')) {
        await inviteAdminMutation.mutateAsync({
          first_name: profileForm.primary_admin.first_name,
          last_name: profileForm.primary_admin.last_name,
          email: profileForm.primary_admin.email,
        })
      }
      markStepComplete(5)
      toast.success(sendInvite ? 'Admin invite sent.' : 'Onboarding progress saved.')
      navigate(`/ct/organisations/${updatedOrganisation.id}`, { replace: true })
    } catch (err: unknown) {
      setFieldErrors(getFieldErrors(err))
      setError(getErrorMessage(err, 'Unable to finish the onboarding wizard.'))
    }
  }

  const handleSaveAndExit = () => {
    if (organisation) {
      navigate(`/ct/organisations/${organisation.id}`, { replace: true })
      return
    }
    navigate(-1)
  }

  const renderAddressForm = (addressType: 'REGISTERED' | 'BILLING') => {
    const address = profileForm.addresses[addressType]
    const addressCountry = getAddressCountryOption(address.country_code || address.country) ?? DEFAULT_COUNTRY_OPTION
    const addressRule = getAddressCountryRule(addressCountry.code)
    const subdivisions = getSubdivisionOptions(addressCountry.code)
    const gstLabel = getBillingTaxLabel(addressCountry.code)
    const showGstAsRequired =
      (addressType === 'BILLING' && isBillingTaxRequired(addressCountry.code)) ||
      (addressType === 'REGISTERED' && billingSameAsRegistered && isBillingTaxRequired(addressCountry.code))

    return (
      <div className="grid gap-4">
        <div>
          <label className="field-label" htmlFor={`${addressType}-line1`}>
            Address line 1
            <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
          </label>
          <input
            id={`${addressType}-line1`}
            className="field-input"
            required
            value={address.line1}
            onChange={setAddressField(addressType, 'line1')}
          />
        </div>
        <div>
          <label className="field-label" htmlFor={`${addressType}-line2`}>
            Address line 2
          </label>
          <input
            id={`${addressType}-line2`}
            className="field-input"
            value={address.line2 ?? ''}
            onChange={setAddressField(addressType, 'line2')}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor={`${addressType}-country`}>
              Country
              <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
            </label>
            <AppSelect
              id={`${addressType}-country`}
              value={addressCountry.code}
              onValueChange={(value) => setAddressCountry(addressType, value)}
              options={COUNTRY_SELECT_OPTIONS}
              placeholder="Select country"
            />
          </div>
          <div>
            <label className="field-label" htmlFor={`${addressType}-city`}>
              City
              <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
            </label>
            <input
              id={`${addressType}-city`}
              className="field-input"
              required
              value={address.city}
              onChange={setAddressField(addressType, 'city')}
            />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor={`${addressType}-state`}>
              {addressRule.subdivisionLabel}
              <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
            </label>
            {subdivisions.length > 0 ? (
              <AppSelect
                id={`${addressType}-state`}
                value={resolveSubdivisionCode(addressCountry.code, address.state, address.state_code)}
                onValueChange={(value) => setAddressState(addressType, value)}
                options={subdivisions.map((option) => ({
                  value: option.code,
                  label: option.label,
                  hint: option.taxRegionCode ? `Tax region ${option.taxRegionCode}` : undefined,
                }))}
                placeholder={`Select ${addressRule.subdivisionLabel.toLowerCase()}`}
              />
            ) : (
              <input
                id={`${addressType}-state`}
                className="field-input"
                value={address.state}
                onChange={setAddressField(addressType, 'state')}
                required
              />
            )}
          </div>
          <div>
            <label className="field-label" htmlFor={`${addressType}-pincode`}>
              {addressRule.postalLabel}
              {addressRule.postalRequired === false ? null : <span className="ml-1 text-[hsl(var(--destructive))]">*</span>}
            </label>
            <input
              id={`${addressType}-pincode`}
              className="field-input"
              required={addressRule.postalRequired !== false}
              value={address.pincode}
              placeholder={addressRule.postalPlaceholder}
              onChange={setAddressField(addressType, 'pincode')}
            />
            <FieldErrorText message={fieldErrors[addressErrorKey(addressType, 'pincode')]} />
          </div>
        </div>
        <div>
          <label className="field-label" htmlFor={`${addressType}-gstin`}>
            {gstLabel}
            {showGstAsRequired ? <span className="ml-1 text-[hsl(var(--destructive))]">*</span> : null}
          </label>
          <input
            id={`${addressType}-gstin`}
            className="field-input"
            required={showGstAsRequired}
            value={address.gstin ?? ''}
            placeholder={addressRule.taxPlaceholder}
            onChange={setAddressField(addressType, 'gstin')}
          />
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            {billingSameAsRegistered && addressType === 'REGISTERED'
              ? `${gstLabel} will also be saved on the billing address because billing is set to the registered address.`
              : addressRule.taxHelperText || `${gstLabel} is optional unless your billing country requires it.`}
          </p>
          <FieldErrorText message={fieldErrors[addressErrorKey(addressType, 'gstin')]} />
        </div>
      </div>
    )
  }

  const renderCurrentStep = () => {
    if (currentStep === 0) {
      return (
        <WizardStep
          title="Organisation Profile"
          description="Create the tenant shell with the legal identifiers, addresses, and bootstrap admin required for provisioning."
          onBack={!organisation ? handleSaveAndExit : undefined}
          onNext={() => void handleProfileStep()}
          backLabel={organisation ? 'Back' : 'Cancel'}
          nextLabel={organisation ? 'Save and continue' : 'Next'}
          isLoading={createOrganisationMutation.isPending || updateOrganisationMutation.isPending}
          error={error}
        >
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <label htmlFor="name" className="field-label">
                Organisation name
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <input id="name" required value={profileForm.name} onChange={setField('name')} className="field-input" />
            </div>
            <div>
              <label htmlFor="pan_number" className="field-label">
                PAN number
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <input
                id="pan_number"
                required
                value={profileForm.pan_number}
                onChange={setField('pan_number')}
                className="field-input"
              />
            </div>
            <div>
              <label htmlFor="country_code" className="field-label">
                Country
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <AppSelect
                id="country_code"
                value={profileForm.country_code}
                onValueChange={handleCountryChange}
                options={COUNTRY_SELECT_OPTIONS}
                placeholder="Select country"
              />
            </div>
            <div>
              <label htmlFor="currency" className="field-label">
                Currency
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <AppSelect
                id="currency"
                value={profileForm.currency}
                onValueChange={(value) => setOrganisationSelectField('currency', value)}
                options={CURRENCY_SELECT_OPTIONS}
                placeholder="Select currency"
              />
            </div>
            <div className="lg:col-span-2">
              <label htmlFor="entity_type" className="field-label">
                Organisation entity type
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <AppSelect
                id="entity_type"
                value={profileForm.entity_type}
                onValueChange={(value) => setOrganisationSelectField('entity_type', value)}
                options={ENTITY_TYPE_OPTIONS}
                placeholder="Select entity type"
              />
            </div>
          </div>

          <div className="surface-muted rounded-[26px] p-5">
            <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Bootstrap admin</p>
            <p className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
              The first admin is captured here so the wizard can hand the tenant off cleanly at the end.
            </p>
            <div className="mt-4 grid gap-5 lg:grid-cols-2">
              <div>
                <label htmlFor="primary-admin-first-name" className="field-label">
                  First name
                  <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
                </label>
                <input
                  id="primary-admin-first-name"
                  required
                  value={profileForm.primary_admin.first_name}
                  onChange={setPrimaryAdminField('first_name')}
                  className="field-input"
                />
                <FieldErrorText message={fieldErrors['primary_admin.first_name']} />
              </div>
              <div>
                <label htmlFor="primary-admin-last-name" className="field-label">
                  Last name
                  <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
                </label>
                <input
                  id="primary-admin-last-name"
                  required
                  value={profileForm.primary_admin.last_name}
                  onChange={setPrimaryAdminField('last_name')}
                  className="field-input"
                />
                <FieldErrorText message={fieldErrors['primary_admin.last_name']} />
              </div>
              <div>
                <label htmlFor="primary-admin-email" className="field-label">
                  Work email
                  <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
                </label>
                <input
                  id="primary-admin-email"
                  type="email"
                  required
                  value={profileForm.primary_admin.email}
                  onChange={setPrimaryAdminField('email')}
                  className="field-input"
                />
                <FieldErrorText message={fieldErrors['primary_admin.email']} />
              </div>
              <div>
                <label htmlFor="primary-admin-phone" className="field-label">
                  Work phone
                </label>
                <input
                  id="primary-admin-phone"
                  value={profileForm.primary_admin.phone}
                  onChange={setPrimaryAdminField('phone')}
                  className="field-input"
                />
                <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
                  Must start with {selectedCountry.dialCode} for {selectedCountry.name}.
                </p>
                <FieldErrorText message={fieldErrors['primary_admin.phone']} />
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <div className="surface-muted rounded-[26px] p-5">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Registered address</p>
              <p className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
                This is the statutory address used for legal records and initial defaults.
              </p>
              <div className="mt-4">{renderAddressForm('REGISTERED')}</div>
            </div>

            <div className="surface-muted rounded-[26px] p-5">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Billing address</p>
              <p className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
                Billing uses a separate active address unless you mirror the registered office.
              </p>
              <div className="mt-4">
                <AppCheckbox
                  id="billing-same-as-registered"
                  checked={billingSameAsRegistered}
                  onCheckedChange={setBillingSameAsRegistered}
                  label="Same as registered address"
                  description="Save a distinct billing row using the registered office values."
                />
              </div>
              <div className="mt-4">
                {billingSameAsRegistered ? (
                  <div className="rounded-[22px] border border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] p-4 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
                    {[
                      effectiveBillingAddress.line1,
                      effectiveBillingAddress.line2,
                      effectiveBillingAddress.city,
                      effectiveBillingAddress.state,
                      effectiveBillingAddress.country,
                      effectiveBillingAddress.pincode,
                    ]
                      .filter(Boolean)
                      .join(', ') || `The billing address will mirror the registered office once you complete it.`}
                  </div>
                ) : (
                  renderAddressForm('BILLING')
                )}
              </div>
            </div>
          </div>
        </WizardStep>
      )
    }

    if (currentStep === 1) {
      return (
        <WizardStep
          title="Licence Configuration"
          description="Create the first draft batch so billing and workspace provisioning stay aligned."
          onBack={() => setCurrentStep(0)}
          onNext={() => void handleLicenceStep()}
          isLoading={createLicenceBatchMutation.isPending || updateLicenceBatchMutation.isPending}
          error={error}
        >
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <label htmlFor="plan-tier" className="field-label">
                Plan tier
              </label>
              <AppSelect
                id="plan-tier"
                value={licenceForm.plan_tier}
                onValueChange={(value) => {
                  setLicenceForm((current) => ({ ...current, plan_tier: value as WizardPlanTier }))
                  setHasFeatureOverrides(false)
                }}
                options={PLAN_TIER_OPTIONS}
                placeholder="Select plan tier"
              />
            </div>
            <div>
              <label htmlFor="seat-count" className="field-label">
                Seat count
              </label>
              <input
                id="seat-count"
                type="number"
                min={1}
                className="field-input"
                value={licenceForm.seat_count}
                onChange={(event) => setLicenceForm((current) => ({ ...current, seat_count: event.target.value }))}
              />
            </div>
            <div>
              <label htmlFor="billing-cycle" className="field-label">
                Billing cycle
              </label>
              <AppSelect
                id="billing-cycle"
                value={licenceForm.billing_cycle}
                onValueChange={(value) => setLicenceForm((current) => ({ ...current, billing_cycle: value as WizardBillingCycle }))}
                options={BILLING_CYCLE_OPTIONS}
                placeholder="Select billing cycle"
              />
            </div>
            <div>
              <label htmlFor="licence-start-date" className="field-label">
                Start date
              </label>
              <AppDatePicker
                id="licence-start-date"
                value={licenceForm.start_date}
                onValueChange={(value) => setLicenceForm((current) => ({ ...current, start_date: value || today }))}
                placeholder="Select start date"
              />
            </div>
            <div>
              <label htmlFor="trial-end-date" className="field-label">
                Trial end date
              </label>
              <AppDatePicker
                id="trial-end-date"
                value={licenceForm.trial_end_date}
                onValueChange={(value) => setLicenceForm((current) => ({ ...current, trial_end_date: value }))}
                placeholder="Optional trial end date"
              />
            </div>
            <div className="lg:col-span-2">
              <label htmlFor="licence-note" className="field-label">
                Commercial note
              </label>
              <input
                id="licence-note"
                className="field-input"
                value={licenceForm.note}
                onChange={(event) => setLicenceForm((current) => ({ ...current, note: event.target.value }))}
                placeholder="Optional context for the first batch"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="surface-muted rounded-[24px] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                Price per seat
              </p>
              <p className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
                {formatMoney(pricePerSeat, organisation?.currency ?? 'INR')}
              </p>
            </div>
            <div className="surface-muted rounded-[24px] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                Billing months
              </p>
              <p className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">{billingMonths}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                Draft total
              </p>
              <p className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
                {formatMoney(totalPrice, organisation?.currency ?? 'INR')}
              </p>
            </div>
          </div>
        </WizardStep>
      )
    }

    if (currentStep === 2) {
      return (
        <WizardStep
          title="Feature Flags"
          description="Persist the starting module mix now so the org detail page reflects the intended scope."
          onBack={() => setCurrentStep(1)}
          onNext={() => void handleFeatureFlagStep()}
          isLoading={updateFeatureFlagsMutation.isPending}
          error={error}
        >
          <div className="grid gap-4">
            {featureFlagOptions.map((featureFlag) => (
              <AppCheckbox
                key={featureFlag.feature_code}
                id={`feature-${featureFlag.feature_code}`}
                checked={Boolean(featureSelections[featureFlag.feature_code])}
                onCheckedChange={(checked) => {
                  setHasFeatureOverrides(true)
                  setFeatureSelections((current) => ({
                    ...current,
                    [featureFlag.feature_code]: checked,
                  }))
                }}
                label={featureFlag.label}
                description={FEATURE_FLAG_DESCRIPTIONS[featureFlag.feature_code] ?? 'Module provisioning for this tenant.'}
              />
            ))}
          </div>
        </WizardStep>
      )
    }

    if (currentStep === 3) {
      return (
        <WizardStep
          title="Payroll & Compliance Settings"
          description="Capture the statutory identifiers that payroll exports and seeded defaults depend on."
          onBack={() => setCurrentStep(2)}
          onNext={() => void handlePayrollSettingsStep()}
          canProceed={Boolean(payrollSettings.tan_number.trim() || payrollSettings.esi_branch_code.trim())}
          isLoading={updateOrganisationMutation.isPending}
          error={error}
        >
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <label htmlFor="tan-number" className="field-label">
                TDS TAN number
              </label>
              <input
                id="tan-number"
                className="field-input"
                value={payrollSettings.tan_number}
                onChange={(event) =>
                  setPayrollSettings((current) => ({ ...current, tan_number: event.target.value.toUpperCase() }))
                }
                placeholder="BLRA12345B"
              />
            </div>
            <div>
              <label htmlFor="esi-branch-code" className="field-label">
                ESI branch code
              </label>
              <input
                id="esi-branch-code"
                className="field-input"
                value={payrollSettings.esi_branch_code}
                onChange={(event) =>
                  setPayrollSettings((current) => ({ ...current, esi_branch_code: event.target.value }))
                }
                placeholder="Optional branch reference"
              />
            </div>
          </div>
          <div className="surface-muted rounded-[24px] p-4 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            Payroll seeding uses the registered-office state saved in step 1 for PT and LWF defaults. TAN or ESI is
            enough to continue through the wizard, and you can enrich the rest from the org profile later.
          </div>
        </WizardStep>
      )
    }

    if (currentStep === 4) {
      return (
        <WizardStep
          title="Seed Payroll Masters"
          description="Run the idempotent seed so payroll components and document types are ready before handoff."
          onBack={() => setCurrentStep(3)}
          error={error}
          footer={
            <div className="flex flex-wrap gap-3">
              <button type="button" className="btn-secondary" onClick={() => setCurrentStep(3)}>
                Back
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void handleSeedDefaults()}
                disabled={seedMastersMutation.isPending}
              >
                {seedMastersMutation.isPending ? 'Seeding...' : 'Seed default masters'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  markStepComplete(4)
                  setCurrentStep(5)
                }}
                disabled={!seedStepReady}
              >
                Continue
              </button>
            </div>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div className="surface-muted rounded-[24px] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                Payroll components
              </p>
              <p className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
                {seedSummary?.payroll_components.total_count ?? 0}
              </p>
              <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                {seedSummary
                  ? `${seedSummary.payroll_components.created_count} created, ${seedSummary.payroll_components.existing_count} already present`
                  : 'Run the seed to provision repeatable payroll defaults.'}
              </p>
            </div>
            <div className="surface-muted rounded-[24px] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                Document types
              </p>
              <p className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
                {seedSummary?.document_types.total_count ?? 0}
              </p>
              <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                {seedSummary
                  ? `${seedSummary.document_types.created_count} created, ${seedSummary.document_types.existing_count} already present`
                  : 'Default onboarding document categories will be added here.'}
              </p>
            </div>
          </div>
          <div className="rounded-[22px] border border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] p-4 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            {seedStepReady
              ? 'The org already has seeded payroll defaults. Continue when you are ready to review the admin handoff.'
              : 'This action is safe to rerun. It only creates the missing defaults for this organisation.'}
          </div>
        </WizardStep>
      )
    }

    const canSendInviteNow = organisation?.status === 'PAID' || organisation?.status === 'ACTIVE'
    return (
      <WizardStep
        title="Invite First Admin"
        description="Confirm the bootstrap admin one last time and decide whether to invite now or defer until the tenant is commercially ready."
        onBack={() => setCurrentStep(4)}
        error={error}
        footer={
          <div className="flex flex-wrap gap-3">
            <button type="button" className="btn-secondary" onClick={() => setCurrentStep(4)}>
              Back
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void handleFinish(false)}
              disabled={updateOrganisationMutation.isPending || inviteAdminMutation.isPending}
            >
              Save and finish later
            </button>
            {canSendInviteNow ? (
              <button
                type="button"
                className="btn-primary"
                onClick={() => void handleFinish(true)}
                disabled={updateOrganisationMutation.isPending || inviteAdminMutation.isPending}
              >
                Send invite and finish
              </button>
            ) : null}
          </div>
        }
      >
        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <label htmlFor="review-first-name" className="field-label">
              First name
            </label>
            <input
              id="review-first-name"
              className="field-input"
              value={profileForm.primary_admin.first_name}
              onChange={setPrimaryAdminField('first_name')}
            />
          </div>
          <div>
            <label htmlFor="review-last-name" className="field-label">
              Last name
            </label>
            <input
              id="review-last-name"
              className="field-input"
              value={profileForm.primary_admin.last_name}
              onChange={setPrimaryAdminField('last_name')}
            />
          </div>
          <div>
            <label htmlFor="review-email" className="field-label">
              Work email
            </label>
            <input
              id="review-email"
              className="field-input"
              type="email"
              value={profileForm.primary_admin.email}
              onChange={setPrimaryAdminField('email')}
            />
          </div>
          <div>
            <label htmlFor="review-phone" className="field-label">
              Work phone
            </label>
            <input
              id="review-phone"
              className="field-input"
              value={profileForm.primary_admin.phone}
              onChange={setPrimaryAdminField('phone')}
            />
          </div>
        </div>
        <div className="rounded-[22px] border border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] p-4 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
          {canSendInviteNow
            ? 'This tenant is already commercially ready, so you can send the org-admin invite directly from the wizard.'
            : 'The tenant is still pending payment, so this step saves the bootstrap admin details and leaves the actual invite for later.'}
        </div>
      </WizardStep>
    )
  }

  if (shouldShowLoadingState) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Provisioning"
          title="Resume onboarding"
          description="Loading the latest Control Tower onboarding state for this organisation."
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Provisioning"
        title={organisation ? `Onboard ${organisation.name}` : 'Create organisation'}
        description="Move through the Control Tower setup flow in order, save progress as you go, and hand off the tenant cleanly."
        actions={
          <button type="button" className="btn-secondary" onClick={handleSaveAndExit}>
            {organisation ? 'Save & Exit' : 'Cancel'}
          </button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[22rem,minmax(0,1fr)]">
        <WizardProgress
          steps={WIZARD_STEPS}
          currentStep={currentStep}
          completedSteps={completedSteps}
          onStepSelect={setCurrentStep}
        />
        {renderCurrentStep()}
      </div>
    </div>
  )
}
