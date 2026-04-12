import { useMemo, useState } from 'react'
import { ReceiptText } from 'lucide-react'
import { toast } from 'sonner'

import { AppSelect } from '@/components/ui/AppSelect'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCancelMyExpenseClaim,
  useCreateMyExpenseClaim,
  useMyExpenseClaims,
  useMyExpensePolicies,
  useSubmitMyExpenseClaim,
  useUpdateMyExpenseClaim,
  useUploadMyExpenseReceipt,
} from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime, formatINR } from '@/lib/format'

const today = new Date().toISOString().slice(0, 10)

type ClaimLineForm = {
  id?: string
  category_id: string
  category_name: string
  expense_date: string
  merchant: string
  description: string
  amount: string
  currency: string
}

function emptyLine(): ClaimLineForm {
  return {
    category_id: '',
    category_name: '',
    expense_date: today,
    merchant: '',
    description: '',
    amount: '',
    currency: 'INR',
  }
}

function getClaimTone(status: string) {
  switch (status) {
    case 'APPROVED':
      return 'success' as const
    case 'REJECTED':
      return 'danger' as const
    case 'SUBMITTED':
      return 'warning' as const
    case 'CANCELLED':
      return 'neutral' as const
    default:
      return 'info' as const
  }
}

function getReimbursementTone(status: string) {
  switch (status) {
    case 'PAID':
      return 'success' as const
    case 'INCLUDED_IN_PAYROLL':
      return 'info' as const
    case 'PENDING_PAYROLL':
      return 'warning' as const
    default:
      return 'neutral' as const
  }
}

export function ExpensesPage() {
  const { data: policies = [], isLoading: policiesLoading } = useMyExpensePolicies()
  const { data: claims = [], isLoading: claimsLoading } = useMyExpenseClaims()
  const createClaimMutation = useCreateMyExpenseClaim()
  const updateClaimMutation = useUpdateMyExpenseClaim()
  const uploadReceiptMutation = useUploadMyExpenseReceipt()
  const submitClaimMutation = useSubmitMyExpenseClaim()
  const cancelClaimMutation = useCancelMyExpenseClaim()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({
    title: '',
    claim_date: today,
    policy: '',
    currency: 'INR',
    lines: [emptyLine()],
  })
  const [receiptFiles, setReceiptFiles] = useState<Record<string, File | null>>({})

  const selectedPolicy = useMemo(
    () => policies.find((policy) => policy.id === form.policy) ?? null,
    [form.policy, policies],
  )

  const policyOptions = useMemo(
    () => [{ value: '', label: 'No policy' }, ...policies.map((policy) => ({ value: policy.id, label: policy.name, hint: policy.currency }))],
    [policies],
  )

  const categoryOptions = useMemo(
    () => [
      { value: '', label: 'Manual category' },
      ...((selectedPolicy?.categories ?? []).map((category) => ({
        value: category.id,
        label: category.name,
        hint: category.per_claim_limit ? `Limit ${formatINR(category.per_claim_limit)}` : undefined,
      }))),
    ],
    [selectedPolicy],
  )

  const pageLoading = policiesLoading || claimsLoading

  const resetForm = () => {
    setEditingId(null)
    setForm({
      title: '',
      claim_date: today,
      policy: '',
      currency: 'INR',
      lines: [emptyLine()],
    })
  }

  const updateLine = (index: number, patch: Partial<ClaimLineForm>) => {
    setForm((current) => ({
      ...current,
      lines: current.lines.map((line, lineIndex) => (lineIndex === index ? { ...line, ...patch } : line)),
    }))
  }

  const buildPayload = (submit: boolean) => ({
    title: form.title,
    claim_date: form.claim_date,
    policy: form.policy || null,
    currency: form.currency,
    submit,
    lines: form.lines.map((line) => ({
      category_id: line.category_id || undefined,
      category_name: line.category_name || undefined,
      expense_date: line.expense_date,
      merchant: line.merchant,
      description: line.description,
      amount: line.amount,
      currency: line.currency || form.currency,
    })),
  })

  const saveClaim = async (submit: boolean) => {
    try {
      if (editingId) {
        await updateClaimMutation.mutateAsync({ id: editingId, payload: buildPayload(submit) })
        toast.success(submit ? 'Expense claim updated and submitted.' : 'Expense claim updated.')
      } else {
        await createClaimMutation.mutateAsync(buildPayload(submit))
        toast.success(submit ? 'Expense claim submitted.' : 'Expense claim saved as draft.')
      }
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save this expense claim.'))
    }
  }

  const handleEdit = (claimId: string) => {
    const claim = claims.find((item) => item.id === claimId)
    if (!claim) return
    setEditingId(claim.id)
    setForm({
      title: claim.title,
      claim_date: claim.claim_date,
      policy: claim.policy_id || '',
      currency: claim.currency,
      lines: claim.lines.map((line) => ({
        id: line.id,
        category_id: line.category || '',
        category_name: line.category_name,
        expense_date: line.expense_date,
        merchant: line.merchant,
        description: line.description,
        amount: line.amount,
        currency: line.currency,
      })),
    })
  }

  const handleSubmitClaim = async (claimId: string) => {
    try {
      await submitClaimMutation.mutateAsync(claimId)
      toast.success('Expense claim submitted.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to submit this expense claim.'))
    }
  }

  const handleCancelClaim = async (claimId: string) => {
    try {
      await cancelClaimMutation.mutateAsync(claimId)
      toast.success('Expense claim cancelled.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to cancel this expense claim.'))
    }
  }

  const handleUploadReceipt = async (claimId: string, lineId: string) => {
    const file = receiptFiles[lineId]
    if (!file) {
      toast.error('Select a file before uploading a receipt.')
      return
    }
    try {
      await uploadReceiptMutation.mutateAsync({ claimId, lineId, file })
      setReceiptFiles((current) => ({ ...current, [lineId]: null }))
      toast.success('Receipt uploaded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to upload this receipt.'))
    }
  }

  if (pageLoading) {
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
        eyebrow="Expenses"
        title="Expense claims"
        description="Save claims as drafts while you gather receipts, then submit them into the approval workflow so approved reimbursements flow into payroll."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <SectionCard title="Draft or rejected" description="Claims you can still edit.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
            {claims.filter((claim) => claim.status === 'DRAFT' || claim.status === 'REJECTED').length}
          </p>
        </SectionCard>
        <SectionCard title="Awaiting payroll" description="Approved claims not yet paid.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
            {claims.filter((claim) => claim.reimbursement_status === 'PENDING_PAYROLL').length}
          </p>
        </SectionCard>
        <SectionCard title="Paid claims" description="Already reimbursed through payroll.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
            {claims.filter((claim) => claim.reimbursement_status === 'PAID').length}
          </p>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <SectionCard title={editingId ? 'Edit expense claim' : 'New expense claim'} description="Use categories from an active policy when available so limits, receipt rules, and payroll accounting stay aligned.">
          <form
            className="grid gap-4"
            onSubmit={(event) => {
              event.preventDefault()
              void saveClaim(false)
            }}
          >
            <div>
              <label className="field-label" htmlFor="expense-title">Title</label>
              <input id="expense-title" className="field-input" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="April client visit" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="expense-claim-date">Claim date</label>
                <input id="expense-claim-date" type="date" className="field-input" value={form.claim_date} onChange={(event) => setForm((current) => ({ ...current, claim_date: event.target.value }))} />
              </div>
              <div>
                <label className="field-label" htmlFor="expense-policy">Policy</label>
                <AppSelect id="expense-policy" value={form.policy} onValueChange={(value) => setForm((current) => ({ ...current, policy: value }))} options={policyOptions} placeholder="Select policy" />
              </div>
            </div>

            {form.lines.map((line, index) => (
              <div key={line.id ?? `${index}-${line.expense_date}`} className="rounded-[20px] border border-[hsl(var(--border)_/_0.84)] p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="field-label" htmlFor={`expense-line-category-${index}`}>Category</label>
                    <AppSelect
                      id={`expense-line-category-${index}`}
                      value={line.category_id}
                      onValueChange={(value) => updateLine(index, { category_id: value, category_name: value ? '' : line.category_name })}
                      options={categoryOptions}
                      placeholder="Select category"
                    />
                  </div>
                  {!line.category_id ? (
                    <div>
                      <label className="field-label" htmlFor={`expense-line-category-name-${index}`}>Manual category</label>
                      <input id={`expense-line-category-name-${index}`} className="field-input" value={line.category_name} onChange={(event) => updateLine(index, { category_name: event.target.value })} placeholder="Travel, meals, stay..." />
                    </div>
                  ) : (
                    <div>
                      <label className="field-label" htmlFor={`expense-line-date-${index}`}>Expense date</label>
                      <input id={`expense-line-date-${index}`} type="date" className="field-input" value={line.expense_date} onChange={(event) => updateLine(index, { expense_date: event.target.value })} />
                    </div>
                  )}
                  {line.category_id ? null : (
                    <div>
                      <label className="field-label" htmlFor={`expense-line-date-${index}`}>Expense date</label>
                      <input id={`expense-line-date-${index}`} type="date" className="field-input" value={line.expense_date} onChange={(event) => updateLine(index, { expense_date: event.target.value })} />
                    </div>
                  )}
                  <div>
                    <label className="field-label" htmlFor={`expense-line-merchant-${index}`}>Merchant</label>
                    <input id={`expense-line-merchant-${index}`} className="field-input" value={line.merchant} onChange={(event) => updateLine(index, { merchant: event.target.value })} placeholder="Uber, Indian Railways, hotel..." />
                  </div>
                  <div>
                    <label className="field-label" htmlFor={`expense-line-amount-${index}`}>Amount</label>
                    <input id={`expense-line-amount-${index}`} className="field-input" value={line.amount} onChange={(event) => updateLine(index, { amount: event.target.value })} placeholder="1250.00" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="field-label" htmlFor={`expense-line-description-${index}`}>Description</label>
                    <textarea id={`expense-line-description-${index}`} className="field-textarea" value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} placeholder="Describe why the expense was incurred." />
                  </div>
                </div>
                {form.lines.length > 1 ? (
                  <div className="mt-3 flex justify-end">
                    <button type="button" className="btn-secondary" onClick={() => setForm((current) => ({ ...current, lines: current.lines.filter((_, lineIndex) => lineIndex !== index) }))}>
                      Remove line
                    </button>
                  </div>
                ) : null}
              </div>
            ))}

            <div className="flex flex-wrap gap-3">
              <button type="button" className="btn-secondary" onClick={() => setForm((current) => ({ ...current, lines: [...current.lines, emptyLine()] }))}>
                Add line
              </button>
              <button type="submit" className="btn-primary" disabled={createClaimMutation.isPending || updateClaimMutation.isPending}>
                {editingId ? 'Update draft' : 'Save draft'}
              </button>
              <button type="button" className="btn-secondary" onClick={() => void saveClaim(true)} disabled={createClaimMutation.isPending || updateClaimMutation.isPending}>
                {editingId ? 'Update and submit' : 'Save and submit'}
              </button>
              {editingId ? (
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancel edit
                </button>
              ) : null}
            </div>
          </form>
        </SectionCard>

        <SectionCard title="My claims" description="Receipts can be uploaded while a claim is editable. Once approved, reimbursement status follows payroll automatically.">
          {claims.length ? (
            <div className="space-y-4">
              {claims.map((claim) => (
                <div key={claim.id} className="rounded-[24px] border border-[hsl(var(--border))] bg-white/70 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{claim.title}</p>
                        <StatusBadge tone={getClaimTone(claim.status)}>{claim.status}</StatusBadge>
                        <StatusBadge tone={getReimbursementTone(claim.reimbursement_status)}>{claim.reimbursement_status}</StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        Claimed {claim.claim_date} • Total {formatINR(claim.total_amount)} • Created {formatDateTime(claim.created_at)}
                      </p>
                      {claim.rejection_reason ? (
                        <p className="mt-2 text-sm text-[hsl(var(--danger))]">Reviewer note: {claim.rejection_reason}</p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(claim.status === 'DRAFT' || claim.status === 'REJECTED') ? (
                        <>
                          <button type="button" className="btn-secondary" onClick={() => handleEdit(claim.id)}>
                            Edit
                          </button>
                          <button type="button" className="btn-secondary" onClick={() => void handleSubmitClaim(claim.id)}>
                            Submit
                          </button>
                          <ConfirmDialog
                            trigger={<button type="button" className="btn-secondary">Cancel</button>}
                            title="Cancel expense claim?"
                            description="This keeps the historical record but removes the claim from approval and payroll reimbursement flows."
                            confirmLabel="Cancel claim"
                            variant="danger"
                            onConfirm={() => handleCancelClaim(claim.id)}
                          />
                        </>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {claim.lines.map((line) => (
                      <div key={line.id} className="rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-4 py-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-[hsl(var(--foreground-strong))]">{line.category_name}</p>
                            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                              {line.expense_date} • {line.merchant || 'Merchant not captured'} • {formatINR(line.amount)}
                            </p>
                            {line.description ? <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{line.description}</p> : null}
                          </div>
                          <div className="text-sm text-[hsl(var(--muted-foreground))]">
                            {line.receipts.length ? `${line.receipts.length} receipt${line.receipts.length !== 1 ? 's' : ''}` : 'No receipts'}
                          </div>
                        </div>

                        {line.receipts.length ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {line.receipts.map((receipt) => (
                              <a key={receipt.id} className="btn-secondary" href={receipt.download_url} target="_blank" rel="noreferrer">
                                {receipt.file_name}
                              </a>
                            ))}
                          </div>
                        ) : null}

                        {(claim.status === 'DRAFT' || claim.status === 'REJECTED') ? (
                          <div className="mt-3 flex flex-wrap items-center gap-3">
                            <input type="file" className="field-input max-w-sm" onChange={(event) => setReceiptFiles((current) => ({ ...current, [line.id]: event.target.files?.[0] ?? null }))} />
                            <button type="button" className="btn-secondary" onClick={() => void handleUploadReceipt(claim.id, line.id)}>
                              Upload receipt
                            </button>
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={ReceiptText}
              title="No expense claims yet"
              description="Save the first draft when you incur a reimbursable expense, then add receipts and submit it for approval."
            />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
