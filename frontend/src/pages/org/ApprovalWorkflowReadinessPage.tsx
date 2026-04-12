import { useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useApprovalWorkflowReadiness } from '@/hooks/useOrgAdmin'

export function ApprovalWorkflowReadinessPage() {
  const navigate = useNavigate()
  const { data: readiness = [], isLoading } = useApprovalWorkflowReadiness()
  const missing = readiness.filter((row) => !row.ready)

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={9} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Approvals"
        title="Workflow readiness"
        description="Keep every request type covered by an active default workflow before teams rely on approvals."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => navigate('/org/approval-workflows')}>
              Back to workflows
            </button>
            <button type="button" className="btn-primary" onClick={() => navigate('/org/approval-workflows/new')}>
              Build workflow
            </button>
          </>
        }
      />

      <SectionCard title="Coverage" description="Default workflows protect requests when no assignment or routing rule applies.">
        <div className="surface-muted rounded-[18px] px-4 py-4">
          <p className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">
            {missing.length === 0
              ? 'Every request kind has an active default workflow.'
              : `${missing.length} request kind${missing.length === 1 ? ' needs' : 's need'} configuration.`}
          </p>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">
              <tr>
                <th className="px-3 py-2">Module</th>
                <th className="px-3 py-2">Request type</th>
                <th className="px-3 py-2">Default workflow</th>
                <th className="px-3 py-2">Rules</th>
                <th className="px-3 py-2">Ready</th>
              </tr>
            </thead>
            <tbody>
              {readiness.map((row) => (
                <tr key={row.kind} className="border-t border-[hsl(var(--border)_/_0.7)]">
                  <td className="px-3 py-3 text-[hsl(var(--muted-foreground))]">{row.module}</td>
                  <td className="px-3 py-3 font-medium text-[hsl(var(--foreground-strong))]">{row.label}</td>
                  <td className="px-3 py-3">{row.has_default_workflow ? 'Configured' : 'Missing'}</td>
                  <td className="px-3 py-3">{row.active_rule_count}</td>
                  <td className="px-3 py-3">
                    <StatusBadge tone={row.ready ? 'success' : 'warning'}>{row.ready ? 'Ready' : 'Needs workflow'}</StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}
