import { useState } from 'react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateOrgExpensePolicy, useOrgExpensePolicies, useUpdateOrgExpensePolicy } from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatINR } from '@/lib/format'

type CategoryForm = {
  code: string
  name: string
  per_claim_limit: string
  requires_receipt: boolean
}

function emptyCategory(): CategoryForm {
  return {
    code: '',
    name: '',
    per_claim_limit: '',
    requires_receipt: false,
  }
}

export function ExpensePoliciesPage() {
  const { data: policies = [], isLoading } = useOrgExpensePolicies()
  const createPolicyMutation = useCreateOrgExpensePolicy()
  const updatePolicyMutation = useUpdateOrgExpensePolicy()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: '',
    description: '',
    currency: 'INR',
    categories: [emptyCategory()],
  })

  const resetForm = () => {
    setEditingId(null)
    setForm({
      name: '',
      description: '',
      currency: 'INR',
      categories: [emptyCategory()],
    })
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      name: form.name,
      description: form.description,
      currency: form.currency,
      categories: form.categories.map((category) => ({
        code: category.code,
        name: category.name,
        per_claim_limit: category.per_claim_limit || null,
        requires_receipt: category.requires_receipt,
      })),
    }

    try {
      if (editingId) {
        await updatePolicyMutation.mutateAsync({ id: editingId, payload })
        toast.success('Expense policy updated.')
      } else {
        await createPolicyMutation.mutateAsync(payload)
        toast.success('Expense policy created.')
      }
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save the expense policy.'))
    }
  }

  const handleEdit = (policyId: string) => {
    const policy = policies.find((item) => item.id === policyId)
    if (!policy) return
    setEditingId(policy.id)
    setForm({
      name: policy.name,
      description: policy.description,
      currency: policy.currency,
      categories: policy.categories.length
        ? policy.categories.map((category) => ({
            code: category.code,
            name: category.name,
            per_claim_limit: category.per_claim_limit || '',
            requires_receipt: category.requires_receipt,
          }))
        : [emptyCategory()],
    })
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
        eyebrow="Expenses"
        title="Expense policies"
        description="Define reimbursable categories, limits, and receipt requirements before employees start filing claims."
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title={editingId ? 'Edit policy' : 'New policy'} description="Policies bundle category rules so claim validation and payroll reimbursement stay consistent.">
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="expense-policy-name">Policy name</label>
                <input id="expense-policy-name" className="field-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Travel and meals" />
              </div>
              <div>
                <label className="field-label" htmlFor="expense-policy-currency">Currency</label>
                <input id="expense-policy-currency" className="field-input" value={form.currency} onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} placeholder="INR" />
              </div>
            </div>
            <div>
              <label className="field-label" htmlFor="expense-policy-description">Description</label>
              <textarea id="expense-policy-description" className="field-textarea" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Who uses this policy and what it covers." />
            </div>

            {form.categories.map((category, index) => (
              <div key={`${category.code}-${index}`} className="rounded-[20px] border border-[hsl(var(--border)_/_0.84)] p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="field-label" htmlFor={`expense-category-code-${index}`}>Code</label>
                    <input id={`expense-category-code-${index}`} className="field-input" value={category.code} onChange={(event) => setForm((current) => ({ ...current, categories: current.categories.map((item, itemIndex) => itemIndex === index ? { ...item, code: event.target.value.toUpperCase() } : item) }))} placeholder="TRAVEL" />
                  </div>
                  <div>
                    <label className="field-label" htmlFor={`expense-category-name-${index}`}>Name</label>
                    <input id={`expense-category-name-${index}`} className="field-input" value={category.name} onChange={(event) => setForm((current) => ({ ...current, categories: current.categories.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item) }))} placeholder="Travel" />
                  </div>
                  <div>
                    <label className="field-label" htmlFor={`expense-category-limit-${index}`}>Per-claim limit</label>
                    <input id={`expense-category-limit-${index}`} className="field-input" value={category.per_claim_limit} onChange={(event) => setForm((current) => ({ ...current, categories: current.categories.map((item, itemIndex) => itemIndex === index ? { ...item, per_claim_limit: event.target.value } : item) }))} placeholder="5000.00" />
                  </div>
                  <label className="flex items-center gap-3 rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-4 py-3 text-sm">
                    <input type="checkbox" checked={category.requires_receipt} onChange={(event) => setForm((current) => ({ ...current, categories: current.categories.map((item, itemIndex) => itemIndex === index ? { ...item, requires_receipt: event.target.checked } : item) }))} />
                    Receipt required
                  </label>
                </div>
              </div>
            ))}

            <div className="flex flex-wrap gap-3">
              <button type="button" className="btn-secondary" onClick={() => setForm((current) => ({ ...current, categories: [...current.categories, emptyCategory()] }))}>
                Add category
              </button>
              <button type="submit" className="btn-primary" disabled={createPolicyMutation.isPending || updatePolicyMutation.isPending}>
                {editingId ? 'Update policy' : 'Create policy'}
              </button>
              {editingId ? (
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancel edit
                </button>
              ) : null}
            </div>
          </form>
        </SectionCard>

        <SectionCard title="Policy catalogue" description="Category definitions stay visible here so admins can validate what employees are allowed to claim.">
          {policies.length ? (
            <div className="space-y-4">
              {policies.map((policy) => (
                <div key={policy.id} className="rounded-[24px] border border-[hsl(var(--border))] bg-white/70 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{policy.name}</p>
                        <StatusBadge tone={policy.is_active ? 'success' : 'neutral'}>
                          {policy.is_active ? 'Active' : 'Inactive'}
                        </StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{policy.description || 'No description captured.'}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{policy.currency} • {policy.categories.length} categories</p>
                    </div>
                    <button type="button" className="btn-secondary" onClick={() => handleEdit(policy.id)}>
                      Edit
                    </button>
                  </div>
                  <div className="mt-4 grid gap-3">
                    {policy.categories.map((category) => (
                      <div key={category.id} className="rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-4 py-3">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="font-medium text-[hsl(var(--foreground-strong))]">{category.code} · {category.name}</p>
                            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                              {category.per_claim_limit ? `Limit ${formatINR(category.per_claim_limit)}` : 'No fixed limit'} • {category.requires_receipt ? 'Receipt required' : 'Receipt optional'}
                            </p>
                          </div>
                          <StatusBadge tone={category.is_active ? 'info' : 'neutral'}>
                            {category.is_active ? 'Active' : 'Inactive'}
                          </StatusBadge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No expense policies yet" description="Create the first policy before enabling employee expense claims." />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
