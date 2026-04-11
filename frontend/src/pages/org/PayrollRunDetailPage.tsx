import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronDown, ChevronUp, Download, Eye } from 'lucide-react'
import { toast } from 'sonner'

import { AppDialog } from '@/components/ui/AppDialog'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useDownloadPayslipPdf,
  useDownloadPayrollRunPayslipsZip,
  useFinalizePayrollRun,
  useNotifyPayrollRunPayslips,
  usePayrollRunDetail,
  usePayrollRunItems,
  useRerunPayrollRun,
  useSubmitPayrollRun,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime, formatINR } from '@/lib/format'
import { getPayrollRunStatusTone } from '@/lib/status'
import type { PayrollRunItem } from '@/types/hr'

function getStatusBadgeTone(status: string) {
  return getPayrollRunStatusTone(status) as 'success' | 'warning' | 'danger' | 'info' | 'neutral'
}

function getPeriodLabel(month: number, year: number) {
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  return `${monthNames[month - 1]} ${year}`
}

const PAYROLL_RUN_ITEMS_PAGE_SIZE = 20

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

function ExpandedRow({ item }: { item: PayrollRunItem }) {
  const snapshot = item.snapshot as Record<string, unknown>
  const lines = (snapshot?.lines as Array<{
    component_type: string
    component_name: string
    monthly_amount: string
    cost_centre_name?: string
  }>) ?? []

  const earnings = lines
    .filter((l) => l.component_type === 'EARNING')
    .map((l) => ({ label: l.component_name, amount: l.monthly_amount, costCentre: l.cost_centre_name }))
  const deductions = lines
    .filter((l) => l.component_type === 'EMPLOYEE_DEDUCTION')
    .map((l) => ({ label: l.component_name, amount: l.monthly_amount, costCentre: l.cost_centre_name }))
  const employerContributions = lines
    .filter((l) => l.component_type === 'EMPLOYER_CONTRIBUTION')
    .map((l) => ({ label: l.component_name, amount: l.monthly_amount, costCentre: l.cost_centre_name }))

  return (
    <div className="bg-[hsl(var(--muted)/0.5)] px-6 py-4">
      <div className="grid gap-6 xl:grid-cols-3">
        {earnings.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Earnings</p>
            <dl className="space-y-1">
              {earnings.map((e) => (
                <div key={e.label} className="flex justify-between text-sm">
                  <dt>{e.label}{e.costCentre ? ` · ${e.costCentre}` : ''}</dt>
                  <dd className="font-medium tabular-nums">{formatINR(e.amount)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        {deductions.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Deductions</p>
            <dl className="space-y-1">
              {deductions.map((d) => (
                <div key={d.label} className="flex justify-between text-sm">
                  <dt>{d.label}{d.costCentre ? ` · ${d.costCentre}` : ''}</dt>
                  <dd className="font-medium tabular-nums text-[hsl(var(--danger))]">{formatINR(d.amount)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        {employerContributions.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Employer Contributions</p>
            <dl className="space-y-1">
              {employerContributions.map((c) => (
                <div key={c.label} className="flex justify-between text-sm">
                  <dt>{c.label}{c.costCentre ? ` · ${c.costCentre}` : ''}</dt>
                  <dd className="tabular-nums text-[hsl(var(--success))]">{formatINR(c.amount)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
      {item.message && (
        <p className="mt-3 rounded border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-3 py-2 text-sm">
          {item.message}
        </p>
      )}
    </div>
  )
}

function PayslipPreviewModal({
  item,
  onClose,
}: {
  item: PayrollRunItem
  onClose: () => void
}) {
  const downloadPdfMutation = useDownloadPayslipPdf()
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function loadPreview() {
    setLoading(true)
    try {
      const result = await downloadPdfMutation.mutateAsync(item.id)
      const url = URL.createObjectURL(result.blob)
      setPdfUrl(url)
    } catch (err) {
      toast.error(getErrorMessage(err))
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppDialog
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title={`Payslip preview — ${item.employee_name}`}
      description={`${item.employee_code}${item.department ? ` · ${item.department}` : ''}`}
    >
      {!pdfUrl ? (
        <div className="flex flex-col items-center gap-4 py-8">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-[hsl(var(--border))] border-t-[hsl(var(--foreground))]" />
              Generating preview...
            </div>
          ) : (
            <button
              type="button"
              className="btn-primary"
              onClick={() => void loadPreview()}
            >
              <Eye className="size-4" />
              Load payslip preview
            </button>
          )}
        </div>
      ) : (
        <div className="relative mt-4 overflow-hidden rounded-[14px] border border-[hsl(var(--border))]">
          <iframe
            src={pdfUrl}
            title={`Payslip preview for ${item.employee_name}`}
            className="w-full"
            style={{ height: '80vh' }}
          />
        </div>
      )}
    </AppDialog>
  )
}

function ItemTableRow({
  item,
  canDownloadPayslip,
  onPreview,
  isSelected,
  selectable,
  onToggleSelected,
}: {
  item: PayrollRunItem
  canDownloadPayslip: boolean
  onPreview: (item: PayrollRunItem) => void
  isSelected: boolean
  selectable: boolean
  onToggleSelected: (itemId: string, checked: boolean) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const downloadPdfMutation = useDownloadPayslipPdf()

  const handleDownloadPayslip = async () => {
    try {
      const result = await downloadPdfMutation.mutateAsync(item.id)
      triggerDownload(result.blob, result.filename)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <>
      <tr className="border-b border-[hsl(var(--border))] transition-colors hover:bg-[hsl(var(--muted)/0.3)]">
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {selectable ? (
              <input
                type="checkbox"
                aria-label={`Select ${item.employee_name}`}
                checked={isSelected}
                onChange={(event) => onToggleSelected(item.id, event.target.checked)}
              />
            ) : null}
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))]"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            <div>
              <p className="font-medium text-[hsl(var(--foreground-strong))]">{item.employee_name}</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">{item.employee_code}</p>
            </div>
          </div>
        </td>
        <td className="px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">{item.department || '—'}</td>
        <td className="px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
          {item.status === 'EXCEPTION' ? (
            <StatusBadge tone="warning">Exception</StatusBadge>
          ) : (
            <StatusBadge tone="success">Ready</StatusBadge>
          )}
        </td>
        <td className="px-4 py-3 text-right font-medium tabular-nums">{formatINR(item.gross_pay)}</td>
        <td className="px-4 py-3 text-right tabular-nums text-[hsl(var(--muted-foreground))]">{formatINR(item.esi_employee)}</td>
        <td className="px-4 py-3 text-right tabular-nums text-[hsl(var(--muted-foreground))]">{formatINR(item.pt_monthly)}</td>
        <td className="px-4 py-3 text-right tabular-nums text-[hsl(var(--danger))]">{formatINR(item.income_tax)}</td>
        <td className="px-4 py-3 text-right tabular-nums text-[hsl(var(--muted-foreground))]">{item.lop_days}</td>
        <td className="px-4 py-3 text-right font-bold tabular-nums text-[hsl(var(--foreground-strong))]">{formatINR(item.net_pay)}</td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-1.5">
            {canDownloadPayslip ? (
              <>
                <button
                  type="button"
                  onClick={() => onPreview(item)}
                  className="btn-secondary flex h-8 items-center gap-1 px-2 text-xs"
                  title="Preview payslip"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Preview
                </button>
                <button
                  type="button"
                  onClick={handleDownloadPayslip}
                  disabled={downloadPdfMutation.isPending}
                  className="btn-secondary flex h-8 items-center gap-1 px-2 text-xs"
                  title="Download payslip"
                >
                  <Download className="h-3.5 w-3.5" />
                  PDF
                </button>
              </>
            ) : null}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={10} className="p-0">
            <ExpandedRow item={item} />
          </td>
        </tr>
      )}
    </>
  )
}

export function PayrollRunDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const runId = id ?? ''

  const { data: run, isLoading: runLoading } = usePayrollRunDetail(runId)
  const submitRunMutation = useSubmitPayrollRun()
  const finalizeRunMutation = useFinalizePayrollRun()
  const rerunMutation = useRerunPayrollRun()
  const downloadSelectedPayslipsMutation = useDownloadPayrollRunPayslipsZip()
  const notifySelectedPayslipsMutation = useNotifyPayrollRunPayslips()
  const [showExceptionsOnly, setShowExceptionsOnly] = useState(false)
  const [itemPage, setItemPage] = useState(1)
  const [previewItem, setPreviewItem] = useState<PayrollRunItem | null>(null)
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([])
  const itemQueryParams = {
    page: itemPage,
    ...(showExceptionsOnly ? { has_exception: true } : {}),
  }
  const { data: itemsData, isLoading: itemsLoading } = usePayrollRunItems(runId, itemQueryParams)

  const handleSubmit = async () => {
    try {
      await submitRunMutation.mutateAsync(runId)
      toast.success('Payroll run submitted for approval.')
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const handleFinalize = async () => {
    try {
      await finalizeRunMutation.mutateAsync(runId)
      toast.success('Payroll run finalized. Payslips are now available.')
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const handleRerun = async () => {
    try {
      const newRun = await rerunMutation.mutateAsync(runId)
      toast.success('New payroll rerun created.')
      navigate(`/org/payroll/runs/${newRun.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const handleDownloadSelectedPayslips = async () => {
    try {
      const result = await downloadSelectedPayslipsMutation.mutateAsync({
        runId,
        item_ids: selectedItemIds,
      })
      triggerDownload(result.blob, result.filename)
      toast.success('Selected payslips downloaded.')
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const handleNotifySelectedPayslips = async () => {
    try {
      await notifySelectedPayslipsMutation.mutateAsync({
        runId,
        item_ids: selectedItemIds,
      })
      toast.success('Selected payslip notices sent.')
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  if (runLoading) {
    return (
      <div className="space-y-6">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
      </div>
    )
  }

  if (!run) {
    return (
      <EmptyState
        title="Payroll run not found"
        description="This payroll run may have been deleted or you may not have access."
        action={
          <Link to="/org/payroll" className="btn-primary">
            Back to payroll
          </Link>
        }
      />
    )
  }

  const displayedItems = itemsData?.results ?? []
  const totalItems = itemsData?.count ?? displayedItems.length
  const exceptionCount = run.exception_count ?? displayedItems.filter((i) => i.status === 'EXCEPTION').length
  const periodLabel = getPeriodLabel(run.period_month, run.period_year)
  const canBulkManagePayslips = run.status === 'FINALIZED' && displayedItems.length > 0
  const allDisplayedSelected = displayedItems.length > 0 && displayedItems.every((item) => selectedItemIds.includes(item.id))
  const pageStart = totalItems === 0 ? 0 : (itemPage - 1) * PAYROLL_RUN_ITEMS_PAGE_SIZE + 1
  const pageEnd = totalItems === 0 ? 0 : pageStart + displayedItems.length - 1
  const hasPagination = Boolean(itemsData?.next || itemsData?.previous || itemPage > 1)

  function toggleExceptionFilter() {
    setShowExceptionsOnly((current) => !current)
    setItemPage(1)
    setSelectedItemIds([])
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 text-sm text-[hsl(var(--muted-foreground))]">
        <Link to="/org/payroll" className="flex items-center gap-1.5 hover:text-[hsl(var(--foreground))]">
          <ArrowLeft className="h-4 w-4" />
          Back to payroll
        </Link>
      </div>

      <PageHeader
        eyebrow="Payroll run"
        title={run.name || periodLabel}
        description={periodLabel}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={getStatusBadgeTone(run.status)}>{run.status}</StatusBadge>
            {exceptionCount > 0 && <StatusBadge tone="warning">{exceptionCount} exceptions</StatusBadge>}
            {run.use_attendance_inputs && <StatusBadge tone="info">Attendance-linked</StatusBadge>}
            {run.status === 'CALCULATED' && !exceptionCount && (
              <button type="button" className="btn-primary" onClick={() => void handleSubmit()}>
                Submit for Approval
              </button>
            )}
            {run.status === 'APPROVED' && (
              <ConfirmDialog
                trigger={<button type="button" className="btn-primary">Finalize Run</button>}
                title="Finalize payroll run?"
                description="This will publish payslips to all employees. This action cannot be undone."
                confirmLabel="Finalize"
                variant="primary"
                onConfirm={() => void handleFinalize()}
              />
            )}
            {run.status === 'FINALIZED' && (
              <>
                {selectedItemIds.length ? (
                  <>
                    <button type="button" className="btn-secondary" onClick={() => void handleDownloadSelectedPayslips()}>
                      Download selected payslips
                    </button>
                    <ConfirmDialog
                      trigger={<button type="button" className="btn-secondary">Send selected payslip notices</button>}
                      title="Send selected payslip notices?"
                      description="Each selected employee will receive the standard payslip-ready notification and email again."
                      confirmLabel="Send selected"
                      variant="primary"
                      onConfirm={() => void handleNotifySelectedPayslips()}
                    />
                  </>
                ) : null}
                <ConfirmDialog
                  trigger={<button type="button" className="btn-secondary">Create Rerun</button>}
                  title="Create payroll rerun?"
                  description="This will create a new draft run for the same period."
                  confirmLabel="Create rerun"
                  variant="primary"
                  onConfirm={() => void handleRerun()}
                />
              </>
            )}
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-4">
        <SectionCard title="Summary" className="xl:col-span-1">
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Total Gross</p>
              <p className="mt-1 text-2xl font-bold tabular-nums">{formatINR(run.total_gross ?? '0')}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Total Net</p>
              <p className="mt-1 text-2xl font-bold tabular-nums">{formatINR(run.total_net ?? '0')}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Total Deductions</p>
              <p className="mt-1 text-xl font-semibold tabular-nums text-[hsl(var(--danger))]">{formatINR(run.total_deductions ?? '0')}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Employees</p>
              <p className="mt-1 text-xl font-semibold">{run.employee_count ?? 0}</p>
            </div>
          </div>
        </SectionCard>

        {run.attendance_snapshot && run.use_attendance_inputs && (
          <SectionCard title="Attendance Summary" className="xl:col-span-3">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Paid Days</p>
                <p className="mt-1 font-semibold">{run.attendance_snapshot.total_attendance_paid_days}</p>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">LOP Days</p>
                <p className="mt-1 font-semibold">{run.attendance_snapshot.total_lop_days}</p>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">OT Minutes</p>
                <p className="mt-1 font-semibold">{run.attendance_snapshot.total_overtime_minutes}</p>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Source</p>
                <p className="mt-1 font-semibold">{run.attendance_snapshot.attendance_source}</p>
              </div>
            </div>
          </SectionCard>
        )}
      </div>

      <SectionCard title="Employee Items">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">
              Employee Items
              <span className="ml-2 text-[hsl(var(--muted-foreground))]">
                ({showExceptionsOnly ? `${displayedItems.length} of ${totalItems}` : totalItems})
              </span>
            </p>
          </div>
          {exceptionCount > 0 && (
            <button
              type="button"
              onClick={toggleExceptionFilter}
              className="btn-secondary text-xs"
            >
              {showExceptionsOnly ? 'Show all' : 'Show exceptions only'}
            </button>
          )}
        </div>

        {canBulkManagePayslips ? (
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                type="checkbox"
                aria-label="Select all displayed payslips"
                checked={allDisplayedSelected}
                onChange={(event) =>
                  setSelectedItemIds((current) => {
                    if (!event.target.checked) {
                      return current.filter((id) => !displayedItems.some((item) => item.id === id))
                    }
                    return Array.from(new Set([...current, ...displayedItems.map((item) => item.id)]))
                  })
                }
              />
              Select all displayed payslips
            </label>
            {selectedItemIds.length ? (
              <span className="text-sm text-[hsl(var(--muted-foreground))]">{selectedItemIds.length} selected</span>
            ) : null}
          </div>
        ) : null}

        {itemsLoading ? (
          <SkeletonTable rows={10} />
        ) : displayedItems.length === 0 ? (
          <EmptyState title="No items found" description={showExceptionsOnly ? 'No exceptions to display.' : 'This payroll run has no employee items.'} />
        ) : (
          <div className="overflow-x-auto rounded-[14px] border border-[hsl(var(--border))]">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Employee</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Dept</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Gross</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">ESI</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">PT</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">TDS</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">LOP Days</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Net Pay</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayedItems.map((item) => (
                  <ItemTableRow
                    key={item.id}
                    item={item}
                    canDownloadPayslip={run.status === 'FINALIZED'}
                    onPreview={setPreviewItem}
                    isSelected={selectedItemIds.includes(item.id)}
                    selectable={canBulkManagePayslips}
                    onToggleSelected={(itemId, checked) =>
                      setSelectedItemIds((current) =>
                        checked ? Array.from(new Set([...current, itemId])) : current.filter((id) => id !== itemId),
                      )
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {itemsData?.next && (
          <p className="mt-3 text-center text-sm text-[hsl(var(--muted-foreground))]">
            More items are available on the next page.
          </p>
        )}

        {hasPagination ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[hsl(var(--border))] pt-4">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Showing {pageStart}-{pageEnd} of {totalItems} {showExceptionsOnly ? 'exception items' : 'items'}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn-secondary text-xs"
                disabled={!itemsData?.previous || itemPage <= 1}
                onClick={() => setItemPage((current) => Math.max(1, current - 1))}
              >
                Previous page
              </button>
              <span className="text-xs font-medium text-[hsl(var(--muted-foreground))]">Page {itemPage}</span>
              <button
                type="button"
                className="btn-secondary text-xs"
                disabled={!itemsData?.next}
                onClick={() => setItemPage((current) => current + 1)}
              >
                Next page
              </button>
            </div>
          </div>
        ) : null}
      </SectionCard>

      {previewItem && (
        <PayslipPreviewModal
          item={previewItem}
          onClose={() => setPreviewItem(null)}
        />
      )}
    </div>
  )
}
