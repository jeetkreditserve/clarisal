import { useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useDownloadMyPayslip, useDownloadMyPayslipsForFiscalYear, useMyPayslips } from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'

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

export function PayslipsPage() {
  const [selectedFiscalYear, setSelectedFiscalYear] = useState(defaultFiscalYear)
  const [search, setSearch] = useState('')
  const { data, isLoading } = useMyPayslips({ fiscal_year: selectedFiscalYear, search })
  const downloadPayslipMutation = useDownloadMyPayslip()
  const downloadFiscalYearMutation = useDownloadMyPayslipsForFiscalYear()
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
      triggerDownload(blob, `${slipNumber.replace(/\//g, '-')}.pdf`)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download the payslip.'))
    }
  }

  const handleDownloadFiscalYear = async () => {
    try {
      const blob = await downloadFiscalYearMutation.mutateAsync(selectedFiscalYear)
      triggerDownload(blob, `payslips-${selectedFiscalYear}.zip`)
      toast.success('Fiscal-year payslips downloaded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download payslips for the selected fiscal year.'))
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
        title="Payslips"
        description="Filter finalized salary slips by fiscal year, search by slip number, and download one slip or a full fiscal-year ZIP."
        actions={
          <button
            type="button"
            className="btn-secondary"
            disabled={downloadFiscalYearMutation.isPending}
            onClick={() => void handleDownloadFiscalYear()}
          >
            <Download className="h-4 w-4" />
            {downloadFiscalYearMutation.isPending ? 'Preparing...' : 'Download fiscal year ZIP'}
          </button>
        }
      />

      <div className="rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
        <p className="font-semibold">Payslips are generated from the current preview payroll engine.</p>
        <p className="mt-1 text-[hsl(var(--muted-foreground))]">
          Treat these slips as limited-scope previews until statutory payroll coverage is completed by your organisation.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Available slips" description="Choose a period to inspect the published snapshot.">
          <div className="mb-4 grid gap-3">
            <div>
              <label className="field-label" htmlFor="payslip-fiscal-year">
                Fiscal year
              </label>
              <input
                id="payslip-fiscal-year"
                className="field-input"
                value={selectedFiscalYear}
                onChange={(event) => setSelectedFiscalYear(event.target.value)}
                placeholder="2026-2027"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="payslip-search">
                Search slip number
              </label>
              <input
                id="payslip-search"
                className="field-input"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by slip number"
              />
            </div>
          </div>
          {!data?.length ? (
            <EmptyState title="No payslips available yet" description="Payslips will appear here after payroll is finalized by your organisation." />
          ) : (
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
          )}
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
              </div>
            ) : (
              <EmptyState title="Select a payslip" description="Choose a payslip from the filtered list to inspect the finalized snapshot." />
            )}
          </SectionCard>
      </div>
    </div>
  )
}
