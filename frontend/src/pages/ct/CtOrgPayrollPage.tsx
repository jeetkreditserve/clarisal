import { useNavigate, useParams } from 'react-router-dom'
import { BadgeDollarSign } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCtOrgPayrollSummary } from '@/hooks/useCtOrganisations'
import { formatDateTime, startCase } from '@/lib/format'
import type { CtOrganisationPayrollSupportSummary, CtSupportDiagnostic } from '@/types/hr'

function PayrollMetric({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="surface-muted rounded-[24px] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">{value}</p>
      {helper ? <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{helper}</p> : null}
    </div>
  )
}

function diagnosticTone(severity: CtSupportDiagnostic['severity']) {
  if (severity === 'critical') return 'danger' as const
  if (severity === 'warning') return 'warning' as const
  return 'info' as const
}

function PayrollDiagnostics({ diagnostics }: { diagnostics: CtSupportDiagnostic[] }) {
  if (!diagnostics.length) return null
  return (
    <SectionCard
      title="Needs CT attention"
      description="These diagnostics turn zero-value summaries into actionable support guidance so Control Tower can explain what is misconfigured or blocked."
    >
      <div className="space-y-3">
        {diagnostics.map((diagnostic) => (
          <div key={diagnostic.code} className="surface-muted rounded-[22px] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">{diagnostic.title}</p>
              <StatusBadge tone={diagnosticTone(diagnostic.severity)}>{startCase(diagnostic.severity)}</StatusBadge>
            </div>
            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{diagnostic.detail}</p>
            <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">{diagnostic.action}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

export function CtOrgPayrollPage() {
  const navigate = useNavigate()
  const { organisationId } = useParams()
  const { data: payrollSummary, isLoading } = useCtOrgPayrollSummary(organisationId ?? '')

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={5} />
      </div>
    )
  }

  const summary = payrollSummary as CtOrganisationPayrollSupportSummary | undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Control Tower • Payroll"
        title="Payroll preview"
        description="Sanitized payroll support visibility for Control Tower. Run state, exception counts, and assignment health are visible here, while employee-level pay remains hidden."
        actions={
          <button type="button" className="btn-secondary" onClick={() => navigate(`/ct/organisations/${organisationId}`)}>
            Back to organisation
          </button>
        }
      />

      {!summary ? (
        <EmptyState
          title="Payroll support data unavailable"
          description="Payroll support visibility may not yet be enabled for this organisation."
          icon={BadgeDollarSign}
        />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <PayrollMetric label="Tax slab sets" value={String(summary.tax_slab_set_count)} helper="Org-scoped preview masters" />
            <PayrollMetric label="Templates" value={String(summary.compensation_template_count)} helper="Reusable structures" />
            <PayrollMetric label="Approved assignments" value={String(summary.approved_assignment_count)} helper="Salary records ready" />
            <PayrollMetric label="Pending assignments" value={String(summary.pending_assignment_count)} helper="Waiting on approval" />
            <PayrollMetric label="Payslips" value={String(summary.payslip_count)} helper="Generated preview slips" />
          </div>

          <PayrollDiagnostics diagnostics={summary.diagnostics} />

          <SectionCard
            title="Payroll run history"
            description="Sanitized payroll support visibility for Control Tower. Run state and exception counts are visible here, while employee-level pay remains hidden."
          >
            {summary.payroll_runs.length ? (
              <div className="space-y-3">
                {summary.payroll_runs.map((run) => (
                  <div key={run.id} className="surface-muted rounded-[24px] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-[hsl(var(--foreground-strong))]">{run.name}</p>
                          <StatusBadge tone={run.status === 'FINALIZED' ? 'success' : run.status === 'REJECTED' ? 'danger' : 'info'}>
                            {run.status}
                          </StatusBadge>
                          {run.exception_count ? <StatusBadge tone="warning">{run.exception_count} exceptions</StatusBadge> : null}
                        </div>
                        <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                          {run.period_month}/{run.period_year} • {run.run_type} • {run.ready_count} ready items
                        </p>
                        <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                          Attendance-linked payable days: {run.attendance_snapshot_summary.use_attendance_inputs ? 'enabled' : 'not applied'}
                        </p>
                        {run.attendance_snapshot_summary.attendance_source && run.attendance_snapshot_summary.use_attendance_inputs ? (
                          <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                            Attendance inputs: {run.attendance_snapshot_summary.total_attendance_paid_days} paid days •{' '}
                            {run.attendance_snapshot_summary.total_lop_days} LOP days •{' '}
                            {run.attendance_snapshot_summary.total_overtime_minutes} overtime minutes
                          </p>
                        ) : null}
                      </div>
                      <div className="text-right text-sm text-[hsl(var(--muted-foreground))]">
                        <p>Created {formatDateTime(run.created_at)}</p>
                        <p>
                          {run.finalized_at
                            ? `Finalized ${formatDateTime(run.finalized_at)}`
                            : run.calculated_at
                              ? `Calculated ${formatDateTime(run.calculated_at)}`
                              : 'Not finalized yet'}
                        </p>
                      </div>
                    </div>
                    {run.exception_messages.length ? (
                      <div className="mt-4 rounded-[18px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-4 py-3 text-sm text-[hsl(var(--foreground-strong))]">
                        <p className="font-medium">Why this run is blocked</p>
                        <ul className="mt-2 space-y-1 text-[hsl(var(--muted-foreground))]">
                          {run.exception_messages.map((message) => (
                            <li key={message}>{message}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No payroll runs yet"
                description="Once this organisation starts payroll preview processing, CT will be able to inspect run status here without seeing salary amounts."
                icon={BadgeDollarSign}
              />
            )}
          </SectionCard>
        </>
      )}
    </div>
  )
}
