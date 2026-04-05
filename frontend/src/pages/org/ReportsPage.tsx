import { useState } from 'react'
import { BarChart3, Calculator, Download, FileSpreadsheet, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { downloadOrgReport, type OrgReportFormat } from '@/lib/api/org-admin'
import { getErrorMessage } from '@/lib/errors'
import { usePayrollSummary } from '@/hooks/useOrgAdmin'

const REPORT_TYPES = [
  {
    value: 'headcount',
    label: 'Headcount',
    description: 'Active employees, probation counts, and department-location staffing shape.',
    icon: Users,
  },
  {
    value: 'attrition',
    label: 'Attrition',
    description: 'Exited employees with last working day and exit reason context.',
    icon: BarChart3,
  },
  {
    value: 'leave-utilization',
    label: 'Leave utilization',
    description: 'Accrued, used, pending, and available leave balances by employee.',
    icon: Calculator,
  },
  {
    value: 'attendance-summary',
    label: 'Attendance summary',
    description: 'Monthly present, half-day, absent, leave, and late-mark totals.',
    icon: FileSpreadsheet,
  },
  {
    value: 'tax-summary',
    label: 'Tax summary',
    description: 'Professional tax, TDS, PF, and ESI totals across the fiscal year.',
    icon: Calculator,
  },
  {
    value: 'payroll-register',
    label: 'Payroll register',
    description: 'Gross, deductions, net, and statutory components for a finalized run.',
    icon: FileSpreadsheet,
  },
]

function getCurrentMonthValue() {
  return new Date().toISOString().slice(0, 7)
}

function getCurrentFiscalYear() {
  const today = new Date()
  const startYear = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1
  return `${startYear}-${startYear + 1}`
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function ReportsPage() {
  const [reportType, setReportType] = useState('headcount')
  const [fileFormat, setFileFormat] = useState<Exclude<OrgReportFormat, 'json'>>('xlsx')
  const [attendanceMonth, setAttendanceMonth] = useState(getCurrentMonthValue())
  const [fiscalYear, setFiscalYear] = useState(getCurrentFiscalYear())
  const [payRunId, setPayRunId] = useState('')
  const [attritionStartDate, setAttritionStartDate] = useState('')
  const [attritionEndDate, setAttritionEndDate] = useState('')
  const [isDownloading, setIsDownloading] = useState(false)

  const { data: payrollSummary } = usePayrollSummary()

  const selectedReport = REPORT_TYPES.find((report) => report.value === reportType) ?? REPORT_TYPES[0]
  const payRunOptions = payrollSummary?.pay_runs ?? []

  const handleDownload = async () => {
    const params: Record<string, string> = {}

    if (reportType === 'payroll-register') {
      if (!payRunId) {
        toast.error('Choose a payroll run before downloading the payroll register.')
        return
      }
      params.pay_run_id = payRunId
    }

    if (reportType === 'attendance-summary') {
      const [year, month] = attendanceMonth.split('-')
      params.year = year
      params.month = String(Number(month))
    }

    if (reportType === 'tax-summary') {
      params.fiscal_year = fiscalYear
    }

    if (reportType === 'attrition') {
      if (attritionStartDate) params.start_date = attritionStartDate
      if (attritionEndDate) params.end_date = attritionEndDate
    }

    setIsDownloading(true)
    const toastId = toast.loading('Generating report…')
    try {
      const result = await downloadOrgReport(reportType, params, fileFormat)
      if (result && typeof result === 'object' && 'blob' in result && result.blob instanceof Blob) {
        triggerDownload(result.blob, result.filename)
      }
      toast.success('Report downloaded.', { id: toastId })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to generate the report.'), { id: toastId })
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="panel-grid">
      <PageHeader
        eyebrow="Insights"
        title="Reports"
        description="Export payroll, workforce, attendance, leave, and tax views without leaving the organisation workspace."
        actions={
          <button type="button" className="btn-primary" onClick={() => void handleDownload()} disabled={isDownloading}>
            <Download className="h-4 w-4" />
            {isDownloading ? 'Generating…' : 'Download report'}
          </button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        {REPORT_TYPES.map((report) => {
          const Icon = report.icon
          const isActive = report.value === reportType
          return (
            <button
              key={report.value}
              type="button"
              onClick={() => setReportType(report.value)}
              className={`rounded-[28px] border p-5 text-left transition ${
                isActive
                  ? 'border-[hsl(var(--brand)_/_0.42)] bg-[linear-gradient(180deg,hsl(var(--brand)_/_0.14),hsl(var(--surface)_/_0.98))] shadow-[0_22px_46px_rgba(37,99,235,0.12)]'
                  : 'border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface)_/_0.84)] hover:-translate-y-0.5 hover:bg-[hsl(var(--surface-elevated)_/_0.96)]'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-[18px] bg-[hsl(var(--surface-contrast)_/_0.9)] text-[hsl(var(--surface-contrast-foreground))]">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-base font-semibold text-[hsl(var(--foreground-strong))]">{report.label}</p>
                  <p className="mt-1 text-sm leading-6 text-[hsl(var(--muted-foreground))]">{report.description}</p>
                </div>
              </div>
            </button>
          )
        })}
      </div>

      <SectionCard
        title={`${selectedReport.label} configuration`}
        description="Choose the export format and any required period filters. Report generation runs synchronously and downloads immediately."
      >
        <div className="grid gap-5 md:grid-cols-2">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Report type</span>
            <select className="field-input" value={reportType} onChange={(event) => setReportType(event.target.value)}>
              {REPORT_TYPES.map((report) => (
                <option key={report.value} value={report.value}>
                  {report.label}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">File format</span>
            <select className="field-input" value={fileFormat} onChange={(event) => setFileFormat(event.target.value as 'xlsx' | 'csv')}>
              <option value="xlsx">Excel (.xlsx)</option>
              <option value="csv">CSV (.csv)</option>
            </select>
          </label>

          {reportType === 'attendance-summary' ? (
            <label className="grid gap-2">
              <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Attendance month</span>
              <input className="field-input" type="month" value={attendanceMonth} onChange={(event) => setAttendanceMonth(event.target.value)} />
            </label>
          ) : null}

          {reportType === 'tax-summary' ? (
            <label className="grid gap-2">
              <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Fiscal year</span>
              <input
                className="field-input"
                value={fiscalYear}
                onChange={(event) => setFiscalYear(event.target.value)}
                placeholder="2026-2027"
              />
            </label>
          ) : null}

          {reportType === 'payroll-register' ? (
            <label className="grid gap-2 md:col-span-2">
              <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Payroll run</span>
              <select className="field-input" value={payRunId} onChange={(event) => setPayRunId(event.target.value)}>
                <option value="">Select a finalized or calculated payroll run</option>
                {payRunOptions.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.name} • {run.period_month}/{run.period_year} • {run.status}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {reportType === 'attrition' ? (
            <>
              <label className="grid gap-2">
                <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Start date</span>
                <input className="field-input" type="date" value={attritionStartDate} onChange={(event) => setAttritionStartDate(event.target.value)} />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-medium text-[hsl(var(--foreground-strong))]">End date</span>
                <input className="field-input" type="date" value={attritionEndDate} onChange={(event) => setAttritionEndDate(event.target.value)} />
              </label>
            </>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard
        title="Statutory filing exports"
        description="PF ECR, ESI monthly, Form 24Q, PT returns, and Form 16 now live under Payroll so filing batches stay versioned and auditable."
      >
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[22px] border border-[hsl(var(--border)_/_0.76)] bg-[hsl(var(--surface)_/_0.9)] px-4 py-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Use Payroll → Filings when you need a downloadable statutory artifact instead of an analytics report.
          </p>
          <Link to="/org/payroll" className="btn-secondary">
            Open payroll filings
          </Link>
        </div>
      </SectionCard>
    </div>
  )
}
