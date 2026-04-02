import { useState } from 'react'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useMyPayslips } from '@/hooks/useEmployeeSelf'

export function PayslipsPage() {
  const { data, isLoading } = useMyPayslips()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const selectedPayslip = data?.find((item) => item.id === selectedId) ?? data?.[0] ?? null

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Payroll"
        title="Payslips"
        description="Review published salary slips and the locked earnings and deduction snapshot for each payroll period."
      />

      {!data?.length ? (
        <EmptyState title="No payslips available yet" description="Payslips will appear here after payroll is finalized by your organisation." />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <SectionCard title="Available slips" description="Choose a period to inspect the published snapshot.">
            <div className="space-y-3">
              {data.map((payslip) => (
                <button
                  key={payslip.id}
                  type="button"
                  onClick={() => setSelectedId(payslip.id)}
                  className={`surface-shell w-full rounded-[18px] px-4 py-4 text-left ${selectedPayslip?.id === payslip.id ? 'ring-2 ring-[hsl(var(--brand)_/_0.35)]' : ''}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">
                      {payslip.period_month}/{payslip.period_year}
                    </p>
                    <StatusBadge tone="success">Published</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{payslip.slip_number}</p>
                </button>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Slip details" description="This is the finalized snapshot used to generate the salary slip.">
            {selectedPayslip ? (
              <div className="space-y-4">
                <div className="surface-muted rounded-[20px] px-4 py-4">
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Gross pay</p>
                  <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
                    {String(selectedPayslip.snapshot.gross_pay ?? '0')}
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Income tax</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">{String(selectedPayslip.snapshot.income_tax ?? '0')}</p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Total deductions</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">{String(selectedPayslip.snapshot.total_deductions ?? '0')}</p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Net pay</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">{String(selectedPayslip.snapshot.net_pay ?? '0')}</p>
                  </div>
                </div>
                <pre className="surface-shell overflow-x-auto rounded-[18px] px-4 py-4 text-sm text-[hsl(var(--foreground-strong))]">
                  {selectedPayslip.rendered_text}
                </pre>
              </div>
            ) : null}
          </SectionCard>
        </div>
      )}
    </div>
  )
}

