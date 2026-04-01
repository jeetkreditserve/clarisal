import { useState } from 'react'
import { CreditCard, IdCard } from 'lucide-react'
import { toast } from 'sonner'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import {
  useBankAccounts,
  useCreateBankAccount,
  useDeleteBankAccount,
  useGovernmentIds,
  useMyProfile,
  useUpdateBankAccount,
  useUpdateMyProfile,
  useUpsertGovernmentId,
} from '@/hooks/useEmployeeSelf'
import {
  getAddressCountryName,
  getAddressCountryOption,
  getAddressCountryRule,
  getSubdivisionName,
  getSubdivisionOptions,
  resolveCountryCode,
  resolveSubdivisionCode,
} from '@/lib/addressMetadata'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { getErrorMessage } from '@/lib/errors'
import { COUNTRY_OPTIONS, DEFAULT_COUNTRY_OPTION } from '@/lib/organisationMetadata'
import type { BankAccountType, GovernmentIdType } from '@/types/hr'

type ProfileDraft = {
  date_of_birth?: string
  gender?: string
  marital_status?: string
  nationality?: string
  phone_personal?: string
  phone_emergency?: string
  emergency_contact_name?: string
  emergency_contact_relation?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  state_code?: string
  country?: string
  country_code?: string
  pincode?: string
}

const emptyBankForm = {
  account_holder_name: '',
  bank_name: '',
  account_number: '',
  ifsc: '',
  account_type: 'SALARY',
  branch_name: '',
  is_primary: true,
}

const COUNTRY_SELECT_OPTIONS = COUNTRY_OPTIONS.map((country) => ({
  value: country.code,
  label: country.name,
  hint: `${country.dialCode} • ${country.defaultCurrency}`,
  keywords: [country.dialCode, country.defaultCurrency],
}))

const BANK_ACCOUNT_TYPE_OPTIONS: Array<{ value: BankAccountType; label: string }> = [
  { value: 'SALARY', label: 'Salary' },
  { value: 'SAVINGS', label: 'Savings' },
  { value: 'CURRENT', label: 'Current' },
]

export function ProfilePage() {
  const { data: profileData, isLoading } = useMyProfile()
  const { data: governmentIds } = useGovernmentIds()
  const { data: bankAccounts } = useBankAccounts()
  const updateProfileMutation = useUpdateMyProfile()
  const upsertGovernmentIdMutation = useUpsertGovernmentId()
  const createBankAccountMutation = useCreateBankAccount()
  const updateBankAccountMutation = useUpdateBankAccount()
  const deleteBankAccountMutation = useDeleteBankAccount()

  const [profileDraft, setProfileDraft] = useState<ProfileDraft>({})
  const [panForm, setPanForm] = useState({ identifier: '', name_on_id: '' })
  const [aadhaarForm, setAadhaarForm] = useState({ identifier: '', name_on_id: '' })
  const [bankForm, setBankForm] = useState(emptyBankForm)
  const [editingBankId, setEditingBankId] = useState<string | null>(null)

  const handleProfileSave = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await updateProfileMutation.mutateAsync(profileValues)
      toast.success('Profile saved.')
      setProfileDraft({})
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save profile.'))
    }
  }

  const handleGovernmentIdSave = async (idType: GovernmentIdType) => {
    const form = idType === 'PAN' ? panForm : aadhaarForm
    try {
      await upsertGovernmentIdMutation.mutateAsync({
        id_type: idType,
        identifier: form.identifier,
        name_on_id: form.name_on_id,
      })
      toast.success(`${idType} details saved.`)
      if (idType === 'PAN') setPanForm((current) => ({ ...current, identifier: '' }))
      if (idType === 'AADHAAR') setAadhaarForm((current) => ({ ...current, identifier: '' }))
    } catch (error) {
      toast.error(getErrorMessage(error, `Unable to save ${idType}.`))
    }
  }

  const handleBankSave = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingBankId) {
        await updateBankAccountMutation.mutateAsync({
          id: editingBankId,
          payload: {
            account_holder_name: bankForm.account_holder_name,
            bank_name: bankForm.bank_name,
            branch_name: bankForm.branch_name,
            account_type: bankForm.account_type,
            is_primary: bankForm.is_primary,
            ...(bankForm.account_number ? { account_number: bankForm.account_number } : {}),
            ...(bankForm.ifsc ? { ifsc: bankForm.ifsc } : {}),
          },
        })
        toast.success('Bank account updated.')
      } else {
        await createBankAccountMutation.mutateAsync(bankForm)
        toast.success('Bank account added.')
      }
      setEditingBankId(null)
      setBankForm(emptyBankForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save bank account.'))
    }
  }

  const handleEditBank = (bankId: string) => {
    const account = bankAccounts?.find((item) => item.id === bankId)
    if (!account) return
    setEditingBankId(account.id)
    setBankForm({
      account_holder_name: account.account_holder_name,
      bank_name: account.bank_name,
      account_number: '',
      ifsc: '',
      account_type: account.account_type,
      branch_name: account.branch_name,
      is_primary: account.is_primary,
    })
  }

  const handleDeleteBank = async (bankId: string) => {
    if (!window.confirm('Remove this bank account?')) return
    try {
      await deleteBankAccountMutation.mutateAsync(bankId)
      toast.success('Bank account removed.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to remove bank account.'))
    }
  }

  if (isLoading || !profileData) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <div className="grid gap-6 xl:grid-cols-2">
          <SkeletonFormBlock rows={8} />
          <SkeletonTable rows={7} />
        </div>
      </div>
    )
  }

  const currentPan = governmentIds?.find((item) => item.id_type === 'PAN')
  const currentAadhaar = governmentIds?.find((item) => item.id_type === 'AADHAAR')
  const profileValues = {
    date_of_birth: profileDraft.date_of_birth ?? profileData.profile.date_of_birth ?? '',
    gender: profileDraft.gender ?? profileData.profile.gender ?? '',
    marital_status: profileDraft.marital_status ?? profileData.profile.marital_status ?? '',
    nationality: profileDraft.nationality ?? profileData.profile.nationality ?? '',
    phone_personal: profileDraft.phone_personal ?? profileData.profile.phone_personal ?? '',
    phone_emergency: profileDraft.phone_emergency ?? profileData.profile.phone_emergency ?? '',
    emergency_contact_name: profileDraft.emergency_contact_name ?? profileData.profile.emergency_contact_name ?? '',
    emergency_contact_relation: profileDraft.emergency_contact_relation ?? profileData.profile.emergency_contact_relation ?? '',
    address_line1: profileDraft.address_line1 ?? profileData.profile.address_line1 ?? '',
    address_line2: profileDraft.address_line2 ?? profileData.profile.address_line2 ?? '',
    city: profileDraft.city ?? profileData.profile.city ?? '',
    state: profileDraft.state ?? profileData.profile.state ?? '',
    state_code: profileDraft.state_code ?? profileData.profile.state_code ?? '',
    country: profileDraft.country ?? profileData.profile.country ?? DEFAULT_COUNTRY_OPTION.name,
    country_code: profileDraft.country_code ?? profileData.profile.country_code ?? resolveCountryCode(profileData.profile.country),
    pincode: profileDraft.pincode ?? profileData.profile.pincode ?? '',
  }
  const addressCountry = getAddressCountryOption(profileValues.country_code || profileValues.country) ?? DEFAULT_COUNTRY_OPTION
  const addressRule = getAddressCountryRule(addressCountry.code)
  const addressSubdivisions = getSubdivisionOptions(addressCountry.code)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="My profile"
        title="Profile and identity"
        description={`Completion: ${profileData.profile_completion.percent}% across personal, identity, bank, and address details.`}
      />

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionCard title="Personal details" description="These fields are used for onboarding and future payroll setup.">
          <form onSubmit={handleProfileSave} className="grid gap-4 lg:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="date_of_birth">
                Date of birth
              </label>
              <AppDatePicker
                id="date_of_birth"
                value={profileValues.date_of_birth}
                onValueChange={(value) => setProfileDraft((current) => ({ ...current, date_of_birth: value }))}
                placeholder="Select date of birth"
              />
            </div>
            {[
              ['gender', 'Gender'],
              ['marital_status', 'Marital status'],
              ['nationality', 'Nationality'],
              ['phone_personal', 'Personal phone'],
              ['phone_emergency', 'Emergency phone'],
              ['emergency_contact_name', 'Emergency contact name'],
              ['emergency_contact_relation', 'Emergency relation'],
              ['city', 'City'],
            ].map(([field, label]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  className="field-input"
                  value={profileValues[field as keyof typeof profileValues]}
                  onChange={(event) => setProfileDraft((current) => ({ ...current, [field]: event.target.value }))}
                />
              </div>
            ))}
            <div>
              <label className="field-label" htmlFor="country">
                Country
              </label>
              <AppSelect
                id="country"
                value={addressCountry.code}
                onValueChange={(value) =>
                  setProfileDraft((current) => ({
                    ...current,
                    country_code: value,
                    country: getAddressCountryName(value),
                    state_code: '',
                    state: '',
                    pincode: '',
                  }))
                }
                options={COUNTRY_SELECT_OPTIONS}
                placeholder="Select country"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="state">
                {addressRule.subdivisionLabel}
              </label>
              {addressSubdivisions.length > 0 ? (
                <AppSelect
                  id="state"
                  value={resolveSubdivisionCode(addressCountry.code, profileValues.state, profileValues.state_code)}
                  onValueChange={(value) =>
                    setProfileDraft((current) => ({
                      ...current,
                      state_code: value,
                      state: getSubdivisionName(addressCountry.code, value, ''),
                    }))
                  }
                  options={addressSubdivisions.map((option) => ({
                    value: option.code,
                    label: option.label,
                    hint: option.taxRegionCode ? `Tax region ${option.taxRegionCode}` : undefined,
                  }))}
                  placeholder={`Select ${addressRule.subdivisionLabel.toLowerCase()}`}
                />
              ) : (
                <input
                  id="state"
                  className="field-input"
                  value={profileValues.state}
                  onChange={(event) => setProfileDraft((current) => ({ ...current, state: event.target.value }))}
                />
              )}
            </div>
            <div>
              <label className="field-label" htmlFor="pincode">
                {addressRule.postalLabel}
              </label>
              <input
                id="pincode"
                className="field-input"
                value={profileValues.pincode}
                placeholder={addressRule.postalPlaceholder}
                onChange={(event) => setProfileDraft((current) => ({ ...current, pincode: event.target.value }))}
              />
            </div>
            <div className="lg:col-span-2">
              <label className="field-label" htmlFor="address_line1">
                Address line 1
              </label>
              <textarea
                id="address_line1"
                className="field-textarea"
                value={profileValues.address_line1}
                onChange={(event) => setProfileDraft((current) => ({ ...current, address_line1: event.target.value }))}
              />
            </div>
            <div className="lg:col-span-2">
              <label className="field-label" htmlFor="address_line2">
                Address line 2
              </label>
              <textarea
                id="address_line2"
                className="field-textarea"
                value={profileValues.address_line2}
                onChange={(event) => setProfileDraft((current) => ({ ...current, address_line2: event.target.value }))}
              />
            </div>
            <div className="lg:col-span-2">
              <button type="submit" className="btn-primary" disabled={updateProfileMutation.isPending}>
                Save personal details
              </button>
            </div>
          </form>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="Completion snapshot" description="A quick view of the sections still shaping payroll readiness.">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="surface-muted rounded-[24px] p-5">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Profile completion</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">
                  {profileData.profile_completion.percent}%
                </p>
              </div>
              <div className="surface-muted rounded-[24px] p-5">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Employee record</p>
                <p className="mt-3 text-sm font-medium text-[hsl(var(--foreground-strong))]">{profileData.employee.full_name}</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{profileData.employee.email}</p>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Government IDs" description="Enter the full value again when updating a masked identifier.">
            <div className="space-y-6">
              <div className="surface-muted rounded-[24px] p-5">
                <div className="flex items-center gap-3">
                  <IdCard className="h-4 w-4 text-[hsl(var(--brand))]" />
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">PAN</p>
                  {currentPan ? (
                    <StatusBadge tone={currentPan.status === 'VERIFIED' ? 'success' : currentPan.status === 'REJECTED' ? 'danger' : 'warning'}>
                      {currentPan.status}
                    </StatusBadge>
                  ) : null}
                </div>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">Current value: {currentPan?.identifier || 'Not provided'}</p>
                <div className="mt-4 grid gap-4">
                  <div>
                    <label className="field-label" htmlFor="pan-identifier">
                      PAN number
                    </label>
                    <input
                      id="pan-identifier"
                      className="field-input"
                      value={panForm.identifier}
                      onChange={(event) => setPanForm((current) => ({ ...current, identifier: event.target.value }))}
                      placeholder="Enter full PAN value"
                    />
                  </div>
                  <div>
                    <label className="field-label" htmlFor="pan-name">
                      Name on ID
                    </label>
                    <input
                      id="pan-name"
                      className="field-input"
                      value={panForm.name_on_id}
                      onChange={(event) => setPanForm((current) => ({ ...current, name_on_id: event.target.value }))}
                      placeholder={currentPan?.name_on_id || 'Name on PAN'}
                    />
                  </div>
                  <button type="button" className="btn-primary" onClick={() => handleGovernmentIdSave('PAN')} disabled={upsertGovernmentIdMutation.isPending}>
                    Save PAN
                  </button>
                </div>
              </div>

              <div className="surface-muted rounded-[24px] p-5">
                <div className="flex items-center gap-3">
                  <IdCard className="h-4 w-4 text-[hsl(var(--brand))]" />
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">Aadhaar</p>
                  {currentAadhaar ? (
                    <StatusBadge tone={currentAadhaar.status === 'VERIFIED' ? 'success' : currentAadhaar.status === 'REJECTED' ? 'danger' : 'warning'}>
                      {currentAadhaar.status}
                    </StatusBadge>
                  ) : null}
                </div>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">Current value: {currentAadhaar?.identifier || 'Not provided'}</p>
                <div className="mt-4 grid gap-4">
                  <div>
                    <label className="field-label" htmlFor="aadhaar-identifier">
                      Aadhaar number
                    </label>
                    <input
                      id="aadhaar-identifier"
                      className="field-input"
                      value={aadhaarForm.identifier}
                      onChange={(event) => setAadhaarForm((current) => ({ ...current, identifier: event.target.value }))}
                      placeholder="Enter full Aadhaar value"
                    />
                  </div>
                  <div>
                    <label className="field-label" htmlFor="aadhaar-name">
                      Name on ID
                    </label>
                    <input
                      id="aadhaar-name"
                      className="field-input"
                      value={aadhaarForm.name_on_id}
                      onChange={(event) => setAadhaarForm((current) => ({ ...current, name_on_id: event.target.value }))}
                      placeholder={currentAadhaar?.name_on_id || 'Name on Aadhaar'}
                    />
                  </div>
                  <button type="button" className="btn-primary" onClick={() => handleGovernmentIdSave('AADHAAR')} disabled={upsertGovernmentIdMutation.isPending}>
                    Save Aadhaar
                  </button>
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Bank accounts" description="Primary bank details will support future payroll disbursement flows.">
            {bankAccounts && bankAccounts.length > 0 ? (
              <div className="mb-5 space-y-3">
                {bankAccounts.map((account) => (
                  <div key={account.id} className="surface-muted rounded-[24px] px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <CreditCard className="h-4 w-4 text-[hsl(var(--brand))]" />
                        <p className="font-medium text-[hsl(var(--foreground-strong))]">{account.bank_name || 'Bank account'}</p>
                        {account.is_primary ? <StatusBadge tone="success">Primary</StatusBadge> : null}
                      </div>
                      <div className="flex gap-2">
                        <button type="button" className="btn-secondary" onClick={() => handleEditBank(account.id)}>
                          Edit
                        </button>
                        <button type="button" className="btn-danger" onClick={() => handleDeleteBank(account.id)}>
                          Remove
                        </button>
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {account.account_holder_name} • {account.account_number} • {account.ifsc}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}

            <form onSubmit={handleBankSave} className="grid gap-4">
              {[
                ['account_holder_name', 'Account holder name'],
                ['bank_name', 'Bank name'],
                ['branch_name', 'Branch name'],
                ['account_number', editingBankId ? 'Account number (leave blank to keep existing)' : 'Account number'],
                ['ifsc', editingBankId ? 'IFSC (leave blank to keep existing)' : 'IFSC'],
              ].map(([field, label]) => (
                <div key={field}>
                  <label className="field-label" htmlFor={field}>
                    {label}
                  </label>
                  <input
                    id={field}
                    className="field-input"
                    value={bankForm[field as keyof typeof bankForm] as string}
                    onChange={(event) => setBankForm((current) => ({ ...current, [field]: event.target.value }))}
                    required={!editingBankId && (field === 'account_holder_name' || field === 'account_number' || field === 'ifsc')}
                  />
                </div>
              ))}
              <div>
                <label className="field-label" htmlFor="account-type">
                  Account type
                </label>
                <AppSelect
                  id="account-type"
                  value={bankForm.account_type}
                  onValueChange={(value) => setBankForm((current) => ({ ...current, account_type: value }))}
                  options={BANK_ACCOUNT_TYPE_OPTIONS}
                  placeholder="Select account type"
                />
              </div>
              <AppCheckbox
                checked={bankForm.is_primary}
                onCheckedChange={(checked) => setBankForm((current) => ({ ...current, is_primary: checked }))}
                label="Set as primary account"
                description="Primary bank accounts are used first for future payroll disbursement flows."
              />
              <div className="flex flex-wrap gap-3">
                {editingBankId ? (
                  <button type="button" className="btn-secondary" onClick={() => {
                    setEditingBankId(null)
                    setBankForm(emptyBankForm)
                  }}>
                    Cancel
                  </button>
                ) : null}
                <button type="submit" className="btn-primary" disabled={createBankAccountMutation.isPending || updateBankAccountMutation.isPending}>
                  {editingBankId ? 'Save bank account' : 'Add bank account'}
                </button>
              </div>
            </form>
            {!bankAccounts || bankAccounts.length === 0 ? (
              <div className="mt-5">
                <EmptyState
                  title="No bank accounts saved yet"
                  description="Add a primary bank account now so future payroll disbursement can be configured without more profile cleanup."
                  icon={CreditCard}
                />
              </div>
            ) : null}
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
