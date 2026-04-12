import { useState } from 'react'
import { Link } from 'react-router-dom'
import { GitBranch, ShieldAlert, Users } from 'lucide-react'

import { OrgChartD3 } from '@/components/OrgChartD3'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useOrgChart, useOrgChartCycles } from '@/hooks/useOrgAdmin'
import { startCase } from '@/lib/format'
import { getEmployeeStatusTone } from '@/lib/status'
import type { OrgChartNode } from '@/lib/api/org-admin'

interface OrgChartBranchProps {
  node: OrgChartNode
}

function OrgChartBranch({ node }: OrgChartBranchProps) {
  return (
    <div className="space-y-3">
      <div className="surface-muted rounded-[24px] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <Link
              to={`/org/employees/${node.id}`}
              className="font-semibold text-[hsl(var(--foreground-strong))] hover:text-[hsl(var(--brand))]"
            >
              {node.name}
            </Link>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">{node.email}</p>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {[node.designation, node.department].filter(Boolean).join(' • ') || 'Role details not assigned'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {node.employee_code ? (
              <StatusBadge tone="neutral">{node.employee_code}</StatusBadge>
            ) : null}
            <StatusBadge tone={getEmployeeStatusTone(node.status)}>{startCase(node.status)}</StatusBadge>
          </div>
        </div>
      </div>

      {node.direct_reports.length > 0 ? (
        <div className="ml-4 border-l border-[hsl(var(--border))] pl-4">
          <div className="space-y-3">
            {node.direct_reports.map((directReport) => (
              <OrgChartBranch key={directReport.id} node={directReport} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function OrgChartPage() {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [fallbackOpen, setFallbackOpen] = useState(false)
  const { data: tree, isLoading } = useOrgChart(includeInactive)
  const { data: cycles } = useOrgChartCycles()

  if (isLoading && !tree) {
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
        eyebrow="People"
        title="Organisation chart"
        description="Inspect the current reporting structure, spot gaps, and trace who manages whom without leaving the admin workspace."
        actions={
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setIncludeInactive((current) => !current)}
          >
            {includeInactive ? 'Hide inactive employees' : 'Include inactive employees'}
          </button>
        }
      />

      {cycles?.has_cycles ? (
        <div className="rounded-[24px] border border-[hsl(var(--warning)_/_0.28)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 text-[hsl(var(--warning))]" />
            <div>
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">Reporting cycle detected</p>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                The reporting graph contains {cycles.cycles.length} cycle{cycles.cycles.length === 1 ? '' : 's'}.
                Fix those manager assignments before relying on this chart for approvals or escalation routing.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      <SectionCard
        title="Reporting hierarchy"
        description={includeInactive ? 'Showing active and inactive employee records.' : 'Showing active, invited, and pending employee records.'}
      >
        {tree && tree.length > 0 ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 text-sm text-[hsl(var(--muted-foreground))]">
              <span className="inline-flex items-center gap-2">
                <Users className="h-4 w-4" />
                {tree.length} root {tree.length === 1 ? 'leader' : 'leaders'}
              </span>
              <span className="inline-flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Search, pan, and zoom through the reporting map. Use the fallback below if you need a simple recursive tree.
              </span>
            </div>

            <OrgChartD3 data={tree} />

            <details className="rounded-[24px] border border-[hsl(var(--border))] bg-[hsl(var(--background-subtle))] px-5 py-4" onToggle={(event) => setFallbackOpen(event.currentTarget.open)}>
              <summary className="cursor-pointer font-medium text-[hsl(var(--foreground-strong))]">
                Accessible hierarchy fallback
              </summary>
              {fallbackOpen ? (
                <div className="mt-4 space-y-4">
                  {tree.map((node) => (
                    <OrgChartBranch key={node.id} node={node} />
                  ))}
                </div>
              ) : null}
            </details>
          </div>
        ) : (
          <EmptyState
            title="No reporting structure yet"
            description="Assign managers to employees and the organisation chart will populate here."
            icon={GitBranch}
          />
        )}
      </SectionCard>
    </div>
  )
}
