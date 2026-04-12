import { useMemo, useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'

import { DocumentUploadWidget } from '@/components/DocumentUploadWidget'
import { AppSelect } from '@/components/ui/AppSelect'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCreateMyInvestmentDeclaration,
  useDeleteMyInvestmentDeclaration,
  useDownloadMyForm12BB,
  useMyInvestmentDeclarations,
  useUpdateMyInvestmentDeclaration,
} from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'

const SECTION_OPTIONS = [
  { value: '80C', label: '80C', hint: 'PPF, ELSS, LIC, EPF' },
  { value: '80D', label: '80D', hint: 'Mediclaim and health insurance' },
  { value: '80TTA', label: '80TTA', hint: 'Savings account interest' },
  { value: '80G', label: '80G', hint: 'Eligible donations' },
  { value: 'HRA', label: 'HRA', hint: 'House rent allowance' },
  { value: 'LTA', label: 'LTA', hint: 'Leave travel allowance' },
  { value: 'OTHER', label: 'OTHER', hint: 'Other declarations' },
]

const currentYear = new Date().getFullYear()
const defaultFiscalYear = new Date().getMonth() + 1 >= 4 ? `${currentYear}-${currentYear + 1}` : `${currentYear - 1}-${currentYear}`

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function TaxDeclarationsPage() {
  const [selectedFiscalYear, setSelectedFiscalYear] = useState(defaultFiscalYear)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({
    fiscal_year: defaultFiscalYear,
    section: '80C',
    description: '',
    declared_amount: '',
    proof_document_id: null as string | null,
    proof_document_file_name: null as string | null,
    proof_document_url: null as string | null,
  })

  const { data: declarations = [], isLoading } = useMyInvestmentDeclarations()
  const createMutation = useCreateMyInvestmentDeclaration()
  const updateMutation = useUpdateMyInvestmentDeclaration()
  const deleteMutation = useDeleteMyInvestmentDeclaration()
  const downloadForm12BBMutation = useDownloadMyForm12BB()

  const groupedDeclarations = useMemo(() => {
    return declarations.reduce<Record<string, typeof declarations>>((groups, declaration) => {
      const key = declaration.fiscal_year
      groups[key] = groups[key] ? [...groups[key], declaration] : [declaration]
      return groups
    }, {})
  }, [declarations])

  const fiscalYearDeclarations = groupedDeclarations[selectedFiscalYear] ?? []

  const resetForm = () => {
    setEditingId(null)
    setForm({
      fiscal_year: selectedFiscalYear,
      section: '80C',
      description: '',
      declared_amount: '',
      proof_document_id: null,
      proof_document_file_name: null,
      proof_document_url: null,
    })
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      fiscal_year: form.fiscal_year,
      section: form.section,
      description: form.description,
      declared_amount: form.declared_amount,
      proof_document_id: form.proof_document_id,
    }

    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, payload })
        toast.success('Tax declaration updated.')
      } else {
        await createMutation.mutateAsync(payload)
        toast.success('Tax declaration saved.')
      }
      setSelectedFiscalYear(form.fiscal_year)
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save the tax declaration.'))
    }
  }

  const handleEdit = (id: string) => {
    const declaration = declarations.find((item) => item.id === id)
    if (!declaration) return
    setEditingId(id)
    setForm({
      fiscal_year: declaration.fiscal_year,
      section: declaration.section,
      description: declaration.description,
      declared_amount: declaration.declared_amount,
      proof_document_id: declaration.proof_document_id,
      proof_document_file_name: declaration.proof_document_file_name,
      proof_document_url: declaration.proof_document_url,
    })
    setSelectedFiscalYear(declaration.fiscal_year)
  }

  const handleProofUpload = async (document: {
    id: string
    file_name: string
  }) => {
    if (editingId) {
      try {
        const updated = await updateMutation.mutateAsync({
          id: editingId,
          payload: { proof_document_id: document.id },
        })
        setForm((current) => ({
          ...current,
          proof_document_id: updated.proof_document_id,
          proof_document_file_name: updated.proof_document_file_name,
          proof_document_url: updated.proof_document_url,
        }))
        toast.success('Proof document linked.')
      } catch (error) {
        toast.error(getErrorMessage(error, 'Unable to link the proof document.'))
      }
      return
    }

    setForm((current) => ({
      ...current,
      proof_document_id: document.id,
      proof_document_file_name: document.file_name,
      proof_document_url: null,
    }))
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id)
      toast.success('Tax declaration deleted.')
      if (editingId === id) {
        resetForm()
      }
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to delete the tax declaration.'))
    }
  }

  const handleDownloadForm12BB = async () => {
    try {
      const blob = await downloadForm12BBMutation.mutateAsync(selectedFiscalYear)
      triggerDownload(blob, `form12bb-${selectedFiscalYear}.pdf`)
      toast.success('Form 12BB downloaded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download Form 12BB for this fiscal year.'))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Payroll"
        title="Tax declarations"
        description="Maintain section-wise tax declarations by fiscal year and download your current Form 12BB when the declaration set is ready."
        actions={
          <button
            type="button"
            className="btn-secondary"
            disabled={downloadForm12BBMutation.isPending}
            onClick={() => void handleDownloadForm12BB()}
          >
            <Download className="h-4 w-4" />
            {downloadForm12BBMutation.isPending ? 'Preparing...' : 'Download Form 12BB'}
          </button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title={editingId ? 'Edit declaration' : 'Add declaration'} description="Keep declarations organized by fiscal year so payroll review and Form 12BB generation stay aligned.">
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <div>
              <label className="field-label" htmlFor="tax-declaration-fiscal-year">
                Fiscal year
              </label>
              <input
                id="tax-declaration-fiscal-year"
                className="field-input"
                value={form.fiscal_year}
                onChange={(event) => {
                  const fiscalYear = event.target.value
                  setForm((current) => ({ ...current, fiscal_year: fiscalYear }))
                  setSelectedFiscalYear(fiscalYear)
                }}
                placeholder="2026-2027"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="tax-declaration-section">
                Section
              </label>
              <AppSelect
                id="tax-declaration-section"
                value={form.section}
                onValueChange={(value) => setForm((current) => ({ ...current, section: value }))}
                options={SECTION_OPTIONS}
                placeholder="Select section"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="tax-declaration-description">
                Description
              </label>
              <input
                id="tax-declaration-description"
                className="field-input"
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="PPF, rent, mediclaim, donation..."
              />
            </div>
            <div>
              <label className="field-label" htmlFor="tax-declaration-amount">
                Declared amount
              </label>
              <input
                id="tax-declaration-amount"
                className="field-input"
                value={form.declared_amount}
                onChange={(event) => setForm((current) => ({ ...current, declared_amount: event.target.value }))}
                placeholder="150000.00"
              />
            </div>
            <DocumentUploadWidget
              id="tax-declaration-proof"
              label="Proof document"
              existingFileName={form.proof_document_file_name}
              existingDownloadUrl={form.proof_document_url}
              onUpload={(document) => handleProofUpload(document)}
            />
            <div className="flex flex-wrap gap-3">
              <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingId ? 'Update declaration' : 'Save declaration'}
              </button>
              {editingId ? (
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancel edit
                </button>
              ) : null}
            </div>
          </form>
        </SectionCard>

        <SectionCard title="Declarations by fiscal year" description="Each declaration shows whether payroll has reviewed it. Editing a verified item moves it back to unverified status until it is reviewed again.">
          <div className="mb-4 max-w-sm">
            <label className="field-label" htmlFor="tax-declaration-filter-fiscal-year">
              Fiscal year filter
            </label>
            <input
              id="tax-declaration-filter-fiscal-year"
              className="field-input"
              value={selectedFiscalYear}
              onChange={(event) => setSelectedFiscalYear(event.target.value)}
              placeholder="2026-2027"
            />
          </div>

          {!fiscalYearDeclarations.length ? (
            <EmptyState
              title="No declarations for this fiscal year"
              description="Add your first section-wise declaration to make the payroll review and Form 12BB output meaningful."
            />
          ) : (
            <div className="space-y-3">
              {fiscalYearDeclarations.map((declaration) => (
                <div key={declaration.id} className="surface-shell rounded-[18px] px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{declaration.description}</p>
                        <StatusBadge tone={declaration.is_verified ? 'success' : 'warning'}>
                          {declaration.is_verified ? 'Verified' : 'Pending review'}
                        </StatusBadge>
                        <StatusBadge tone="info">{declaration.section}</StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        FY {declaration.fiscal_year} • ₹{declaration.declared_amount}
                        {declaration.section_limit ? ` • Section cap ₹${declaration.section_limit}` : ''}
                      </p>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {declaration.verified_by_name ? `Reviewed by ${declaration.verified_by_name}` : 'Awaiting payroll review'}
                      </p>
                      {declaration.proof_document_file_name ? (
                        <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                          Proof document:{' '}
                          {declaration.proof_document_url ? (
                            <a
                              href={declaration.proof_document_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[hsl(var(--brand))] hover:text-[hsl(var(--brand-strong))]"
                            >
                              {declaration.proof_document_file_name}
                            </a>
                          ) : declaration.proof_document_file_name}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="btn-secondary" onClick={() => handleEdit(declaration.id)}>
                        Edit
                      </button>
                      <ConfirmDialog
                        trigger={
                          <button type="button" className="btn-secondary">
                            Delete
                          </button>
                        }
                        title="Delete tax declaration?"
                        description="This removes the declaration from the selected fiscal year and from future Form 12BB output."
                        confirmLabel="Delete declaration"
                        variant="danger"
                        onConfirm={() => handleDelete(declaration.id)}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
