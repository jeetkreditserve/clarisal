import { useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useDownloadMyPayslip, useMyPayslips } from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'

export function PayslipsPage() {
  const { data, isLoading } = useMyPayslips()
  const downloadPayslipMutation = useDownloadMyPayslip()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const selectedPayslip = data?.find((item) => item.id === selectedId) ?? data?.[0] ?? null
  const lines = Array.isArray(selectedPayslip?.snapshot?.lines)
    ? (selectedPayslip?.snapshot?.lines as Array<Record<string, unknown>>)
    : []
  const earningLines = lines.filter((line) => {
    const componentType = String(line.component_type ?? '')
    return componentType === 'EARNING' || componentType === 'REIMBURSEMENT'
  })
  const deductionLines = lines.filter((line) => String(line.component_type ?? '') === 'EMPLOYEE_DEDUCTION')
  const employerLines = lines.filter((line) => String(line.component_type ?? '') === 'EMPLOYER_CONTRIBUTION')

  const handleDownload = async (payslipId: string, slipNumber: string) => {
    try {
      const blob = await downloadPayslipMutation.mutateAsync(payslipId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${slipNumber.replace(/\//g, '-')}.txt`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download the payslip.'))
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
        title="Payslips Preview"
        description="Review published salary slips and the locked earnings and deduction snapshot for each payroll period."
      />

      <div className="rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
        <p className="font-semibold">Payslips are generated from the current preview payroll engine.</p>
        <p className="mt-1 text-[hsl(var(--muted-foreground))]">
          Treat these slips as limited-scope previews until statutory payroll coverage is completed by your organisation.
        </p>
      </div>

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

          <SectionCard title="Slip details" description="This view organizes the finalized payroll snapshot into a document-style summary for the selected period.">
            {selectedPayslip ? (
              <div className="space-y-4">
                <div className="surface-muted rounded-[20px] px-5 py-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">Payslip period</p>
                      <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
                        {String(selectedPayslip.snapshot.period_label ?? `${selectedPayslip.period_month}/${selectedPayslip.period_year}`)}
                      </p>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">Slip number {selectedPayslip.slip_number}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <StatusBadge tone="success">Finalized snapshot</StatusBadge>
                      <button
                        type="button"
                        className="btn-secondary"
                        aria-label={`Download payslip ${selectedPayslip.slip_number}`}
                        disabled={downloadPayslipMutation.isPending}
                        onClick={() => void handleDownload(selectedPayslip.id, selectedPayslip.slip_number)}
                      >
                        <Download className="h-4 w-4" />
                        {downloadPayslipMutation.isPending ? 'Downloading...' : 'Download'}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Gross pay</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">{String(selectedPayslip.snapshot.gross_pay ?? '0')}</p>
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
                <div className="grid gap-4 xl:grid-cols-3">
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Earnings</p>
                    {earningLines.length ? (
                      <div className="mt-3 space-y-2">
                        {earningLines.map((line, index) => (
                          <div key={`${String(line.component_name ?? 'earning')}-${index}`} className="flex items-center justify-between gap-3 text-sm">
                            <span className="text-[hsl(var(--muted-foreground))]">{String(line.component_name ?? 'Component')}</span>
                            <span className="font-medium text-[hsl(var(--foreground-strong))]">{String(line.monthly_amount ?? '0')}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">No earning line details were stored for this preview slip.</p>
                    )}
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Employee deductions</p>
                    <div className="mt-3 space-y-2">
                      {deductionLines.length ? deductionLines.map((line, index) => (
                        <div key={`${String(line.component_name ?? 'deduction')}-${index}`} className="flex items-center justify-between gap-3 text-sm">
                          <span className="text-[hsl(var(--muted-foreground))]">{String(line.component_name ?? 'Component')}</span>
                          <span className="font-medium text-[hsl(var(--foreground-strong))]">{String(line.monthly_amount ?? '0')}</span>
                        </div>
                      )) : (
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">No line-level deductions were stored. Income tax is shown in the summary cards above.</p>
                      )}
                    </div>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-4">
                    <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Employer contributions</p>
                    <div className="mt-3 space-y-2">
                      {employerLines.length ? employerLines.map((line, index) => (
                        <div key={`${String(line.component_name ?? 'employer')}-${index}`} className="flex items-center justify-between gap-3 text-sm">
                          <span className="text-[hsl(var(--muted-foreground))]">{String(line.component_name ?? 'Component')}</span>
                          <span className="font-medium text-[hsl(var(--foreground-strong))]">{String(line.monthly_amount ?? '0')}</span>
                        </div>
                      )) : (
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">No employer contribution lines were stored for this preview slip.</p>
                      )}
                    </div>
                  </div>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-4">
                  <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Raw generated text</p>
                  <pre className="mt-3 overflow-x-auto text-sm text-[hsl(var(--foreground-strong))]">{selectedPayslip.rendered_text}</pre>
                </div>
              </div>
            ) : null}
          </SectionCard>
        </div>
      )}
    </div>
  )
}
