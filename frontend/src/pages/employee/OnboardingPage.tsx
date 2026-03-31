import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import {
  useCreateEmergencyContact,
  useCreateFamilyMember,
  useDeleteEmergencyContact,
  useDeleteFamilyMember,
  useMyDocumentRequests,
  useMyOnboarding,
  useUpdateMyOnboarding,
  useUploadRequestedDocument,
} from '@/hooks/useEmployeeSelf'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { getErrorMessage } from '@/lib/errors'
import { getDocumentRequestStatusTone, getEmployeeStatusTone, getOnboardingStatusTone } from '@/lib/status'
import type { FamilyRelation } from '@/types/hr'

const emptyFamilyForm = {
  full_name: '',
  relation: 'OTHER' as FamilyRelation,
  date_of_birth: '',
  contact_number: '',
  is_dependent: false,
}

const emptyEmergencyForm = {
  full_name: '',
  relation: '',
  phone_number: '',
  alternate_phone_number: '',
  address: '',
  is_primary: true,
}

export function OnboardingPage() {
  const { data, isLoading } = useMyOnboarding()
  const { data: documentRequests } = useMyDocumentRequests()
  const updateMutation = useUpdateMyOnboarding()
  const createFamilyMutation = useCreateFamilyMember()
  const deleteFamilyMutation = useDeleteFamilyMember()
  const createEmergencyMutation = useCreateEmergencyContact()
  const deleteEmergencyMutation = useDeleteEmergencyContact()
  const uploadRequestedDocumentMutation = useUploadRequestedDocument()

  const [draft, setDraft] = useState<Record<string, string>>({})
  const [familyForm, setFamilyForm] = useState(emptyFamilyForm)
  const [emergencyForm, setEmergencyForm] = useState(emptyEmergencyForm)
  const [selectedFiles, setSelectedFiles] = useState<Record<string, File | null>>({})

  const governmentIds = useMemo(() => {
    const pan = data?.government_ids.find((item) => item.id_type === 'PAN')
    const aadhaar = data?.government_ids.find((item) => item.id_type === 'AADHAAR')
    return { pan, aadhaar }
  }, [data])

  if (isLoading || !data) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={8} />
        <div className="grid gap-6 xl:grid-cols-2">
          <SkeletonTable rows={5} />
          <SkeletonTable rows={5} />
        </div>
      </div>
    )
  }

  const profile = {
    date_of_birth: draft.date_of_birth ?? data.profile.date_of_birth ?? '',
    gender: draft.gender ?? data.profile.gender ?? '',
    marital_status: draft.marital_status ?? data.profile.marital_status ?? '',
    nationality: draft.nationality ?? data.profile.nationality ?? '',
    blood_type: draft.blood_type ?? data.profile.blood_type ?? '',
    phone_personal: draft.phone_personal ?? data.profile.phone_personal ?? '',
    address_line1: draft.address_line1 ?? data.profile.address_line1 ?? '',
    address_line2: draft.address_line2 ?? data.profile.address_line2 ?? '',
    city: draft.city ?? data.profile.city ?? '',
    state: draft.state ?? data.profile.state ?? '',
    country: draft.country ?? data.profile.country ?? 'India',
    pincode: draft.pincode ?? data.profile.pincode ?? '',
    pan_identifier: draft.pan_identifier ?? '',
    aadhaar_identifier: draft.aadhaar_identifier ?? '',
  }

  const handleSaveBasics = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await updateMutation.mutateAsync(profile)
      toast.success('Onboarding basics saved.')
      setDraft({})
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save onboarding details.'))
    }
  }

  const handleAddFamily = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createFamilyMutation.mutateAsync({
        ...familyForm,
        date_of_birth: familyForm.date_of_birth || null,
      })
      toast.success('Family member added.')
      setFamilyForm(emptyFamilyForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to add family member.'))
    }
  }

  const handleAddEmergency = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createEmergencyMutation.mutateAsync(emergencyForm)
      toast.success('Emergency contact added.')
      setEmergencyForm(emptyEmergencyForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to add emergency contact.'))
    }
  }

  const handleUploadRequestedDocument = async (requestId: string) => {
    const file = selectedFiles[requestId]
    if (!file) {
      toast.error('Choose a file before uploading.')
      return
    }
    try {
      await uploadRequestedDocumentMutation.mutateAsync({ request_id: requestId, file })
      toast.success('Document uploaded.')
      setSelectedFiles((current) => ({ ...current, [requestId]: null }))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to upload requested document.'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Employee onboarding"
        title="Finish your setup"
        description="Add your personal details, identity numbers, family and emergency information, and upload the documents your organisation requested."
        actions={
          <div className="flex items-center gap-3">
            <StatusBadge tone={getEmployeeStatusTone(data.summary.employee_status)}>{data.summary.employee_status}</StatusBadge>
            <StatusBadge tone={getOnboardingStatusTone(data.summary.onboarding_status)}>{data.summary.onboarding_status}</StatusBadge>
            {data.summary.onboarding_status === 'COMPLETE' ? (
              <Link to="/me/dashboard" className="btn-primary">
                Open dashboard
              </Link>
            ) : null}
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Basic details" description="These details are required before your employee record can move forward for joining.">
          <form onSubmit={handleSaveBasics} className="grid gap-4 lg:grid-cols-2">
            {[
              ['date_of_birth', 'Date of birth', 'date'],
              ['gender', 'Gender', 'text'],
              ['marital_status', 'Marital status', 'text'],
              ['nationality', 'Nationality', 'text'],
              ['blood_type', 'Blood type', 'text'],
              ['phone_personal', 'Personal phone', 'text'],
              ['city', 'City', 'text'],
              ['state', 'State', 'text'],
              ['country', 'Country', 'text'],
              ['pincode', 'Pincode', 'text'],
              ['pan_identifier', `PAN number${governmentIds.pan ? ` • ${governmentIds.pan.identifier}` : ''}`, 'text'],
              ['aadhaar_identifier', `Aadhaar number${governmentIds.aadhaar ? ` • ${governmentIds.aadhaar.identifier}` : ''}`, 'text'],
            ].map(([field, label, type]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  type={type}
                  className="field-input"
                  value={profile[field as keyof typeof profile]}
                  onChange={(event) => setDraft((current) => ({ ...current, [field]: event.target.value }))}
                />
              </div>
            ))}
            <div className="lg:col-span-2">
              <label className="field-label" htmlFor="address_line1">
                Address line 1
              </label>
              <textarea
                id="address_line1"
                className="field-textarea"
                value={profile.address_line1}
                onChange={(event) => setDraft((current) => ({ ...current, address_line1: event.target.value }))}
              />
            </div>
            <div className="lg:col-span-2">
              <label className="field-label" htmlFor="address_line2">
                Address line 2
              </label>
              <textarea
                id="address_line2"
                className="field-textarea"
                value={profile.address_line2}
                onChange={(event) => setDraft((current) => ({ ...current, address_line2: event.target.value }))}
              />
            </div>
            <div className="lg:col-span-2">
              <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
                Save basic details
              </button>
            </div>
          </form>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="Completion summary" description="Your onboarding progress updates automatically as you complete the required sections.">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="surface-muted rounded-[24px] p-5">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Completion</p>
                <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
                  {data.summary.profile_completion.percent}%
                </p>
              </div>
              <div className="surface-muted rounded-[24px] p-5">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Required documents</p>
                <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
                  {data.summary.submitted_document_count}/{data.summary.required_document_count}
                </p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {data.summary.profile_completion.completed_sections.map((section) => (
                <StatusBadge key={section} tone="success">
                  {section.replaceAll('_', ' ')}
                </StatusBadge>
              ))}
              {data.summary.profile_completion.missing_sections.map((section) => (
                <StatusBadge key={section} tone="warning">
                  {section.replaceAll('_', ' ')}
                </StatusBadge>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Family details" description="Add at least one family or dependent record.">
            <form onSubmit={handleAddFamily} className="grid gap-4">
              <input className="field-input" placeholder="Full name" value={familyForm.full_name} onChange={(event) => setFamilyForm((current) => ({ ...current, full_name: event.target.value }))} />
              <select className="field-select" value={familyForm.relation} onChange={(event) => setFamilyForm((current) => ({ ...current, relation: event.target.value as FamilyRelation }))}>
                {['SPOUSE', 'FATHER', 'MOTHER', 'SON', 'DAUGHTER', 'BROTHER', 'SISTER', 'OTHER'].map((relation) => (
                  <option key={relation} value={relation}>
                    {relation.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
              <div className="grid gap-4 md:grid-cols-2">
                <input className="field-input" type="date" value={familyForm.date_of_birth} onChange={(event) => setFamilyForm((current) => ({ ...current, date_of_birth: event.target.value }))} />
                <input className="field-input" placeholder="Contact number" value={familyForm.contact_number} onChange={(event) => setFamilyForm((current) => ({ ...current, contact_number: event.target.value }))} />
              </div>
              <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                <input type="checkbox" checked={familyForm.is_dependent} onChange={(event) => setFamilyForm((current) => ({ ...current, is_dependent: event.target.checked }))} />
                Is dependent
              </label>
              <button type="submit" className="btn-secondary" disabled={createFamilyMutation.isPending}>
                Add family member
              </button>
            </form>
            <div className="mt-5 space-y-3">
              {data.family_members.length > 0 ? (
                data.family_members.map((member) => (
                  <div key={member.id} className="surface-muted flex items-center justify-between rounded-[20px] px-4 py-3">
                    <div>
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{member.full_name}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">{member.relation.replaceAll('_', ' ')}</p>
                    </div>
                    <button className="btn-secondary" onClick={() => void deleteFamilyMutation.mutateAsync(member.id)}>
                      Remove
                    </button>
                  </div>
                ))
              ) : (
                <EmptyState title="No family details yet" description="Add at least one family or dependent entry." />
              )}
            </div>
          </SectionCard>

          <SectionCard title="Emergency contacts" description="Add at least one primary contact for emergency and medical situations.">
            <form onSubmit={handleAddEmergency} className="grid gap-4">
              <input className="field-input" placeholder="Full name" value={emergencyForm.full_name} onChange={(event) => setEmergencyForm((current) => ({ ...current, full_name: event.target.value }))} />
              <input className="field-input" placeholder="Relation" value={emergencyForm.relation} onChange={(event) => setEmergencyForm((current) => ({ ...current, relation: event.target.value }))} />
              <div className="grid gap-4 md:grid-cols-2">
                <input className="field-input" placeholder="Phone number" value={emergencyForm.phone_number} onChange={(event) => setEmergencyForm((current) => ({ ...current, phone_number: event.target.value }))} />
                <input className="field-input" placeholder="Alternate phone" value={emergencyForm.alternate_phone_number} onChange={(event) => setEmergencyForm((current) => ({ ...current, alternate_phone_number: event.target.value }))} />
              </div>
              <textarea className="field-textarea" placeholder="Address" value={emergencyForm.address} onChange={(event) => setEmergencyForm((current) => ({ ...current, address: event.target.value }))} />
              <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                <input type="checkbox" checked={emergencyForm.is_primary} onChange={(event) => setEmergencyForm((current) => ({ ...current, is_primary: event.target.checked }))} />
                Primary contact
              </label>
              <button type="submit" className="btn-secondary" disabled={createEmergencyMutation.isPending}>
                Add emergency contact
              </button>
            </form>
            <div className="mt-5 space-y-3">
              {data.emergency_contacts.length > 0 ? (
                data.emergency_contacts.map((contact) => (
                  <div key={contact.id} className="surface-muted flex items-center justify-between rounded-[20px] px-4 py-3">
                    <div>
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{contact.full_name}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        {contact.relation} • {contact.phone_number}
                      </p>
                    </div>
                    <button className="btn-secondary" onClick={() => void deleteEmergencyMutation.mutateAsync(contact.id)}>
                      Remove
                    </button>
                  </div>
                ))
              ) : (
                <EmptyState title="No emergency contacts yet" description="Add a primary emergency contact to continue." />
              )}
            </div>
          </SectionCard>
        </div>
      </div>

      <SectionCard title="Requested documents" description="Upload the onboarding documents requested by your organisation administrator.">
        {documentRequests && documentRequests.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {documentRequests.map((request) => (
              <div key={request.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{request.document_type.name}</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{request.document_type.category.replaceAll('_', ' ')}</p>
                  </div>
                  <StatusBadge tone={getDocumentRequestStatusTone(request.status)}>{request.status}</StatusBadge>
                </div>
                {request.rejection_note ? (
                  <p className="mt-3 rounded-[18px] bg-[hsl(var(--danger)_/_0.12)] px-3 py-2 text-sm text-[hsl(var(--danger))]">
                    {request.rejection_note}
                  </p>
                ) : null}
                <div className="mt-4 grid gap-3">
                  <input
                    type="file"
                    className="field-input"
                    onChange={(event) =>
                      setSelectedFiles((current) => ({
                        ...current,
                        [request.id]: event.target.files?.[0] ?? null,
                      }))
                    }
                  />
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => void handleUploadRequestedDocument(request.id)}
                    disabled={uploadRequestedDocumentMutation.isPending}
                  >
                    Upload document
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No requested documents" description="Your administrator has not assigned any onboarding documents yet." />
        )}
      </SectionCard>
    </div>
  )
}
