import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { AppSelect } from '@/components/ui/AppSelect'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useNotices, usePublishNotice } from '@/hooks/useOrgAdmin'
import { useCtOrgConfiguration, usePublishCtNotice } from '@/hooks/useCtOrganisations'
import { NOTICE_AUDIENCE_TYPE_OPTIONS, NOTICE_STATUS_OPTIONS } from '@/lib/constants'
import { formatDateTime, startCase } from '@/lib/format'

export function NoticesPage() {
  const navigate = useNavigate()
  const { organisationId } = useParams()
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const [statusFilter, setStatusFilter] = useState('')
  const [audienceFilter, setAudienceFilter] = useState('')
  const [search, setSearch] = useState('')
  const { data: notices, isLoading } = useNotices({
    status: statusFilter || undefined,
    audience_type: audienceFilter || undefined,
    search: search || undefined,
  }, !isCtMode)
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const publishMutation = usePublishNotice()
  const publishCtMutation = usePublishCtNotice(organisationId ?? '')
  const resolvedNotices = isCtMode
    ? (configuration?.notices ?? []).filter((notice) => {
        const matchesStatus = !statusFilter || notice.status === statusFilter
        const matchesAudience = !audienceFilter || notice.audience_type === audienceFilter
        const searchValue = search.trim().toLowerCase()
        const matchesSearch =
          !searchValue ||
          notice.title.toLowerCase().includes(searchValue) ||
          notice.body.toLowerCase().includes(searchValue) ||
          notice.category.toLowerCase().includes(searchValue)
        return matchesStatus && matchesAudience && matchesSearch
      })
    : notices
  const pageLoading = isCtMode ? isCtLoading : isLoading

  if (pageLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const stickyCount = (resolvedNotices ?? []).filter((notice) => notice.is_sticky).length
  const publishedCount = (resolvedNotices ?? []).filter((notice) => notice.status === 'PUBLISHED').length
  const scheduledCount = (resolvedNotices ?? []).filter((notice) => notice.status === 'SCHEDULED').length
  const blockedCount = (resolvedNotices ?? []).filter((notice) => notice.is_automation_blocked).length

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • Notices' : 'Notices'}
        title="Announcement center"
        description="Publish richer internal notices with targeting, scheduling, sticky placement, and lifecycle status tracking."
        actions={
          <>
            {isCtMode ? (
              <button type="button" className="btn-secondary" onClick={() => navigate(basePath)}>
                Back to organisation
              </button>
            ) : null}
            <button type="button" className="btn-primary" onClick={() => navigate(`${basePath}/notices/new`)}>
              Compose notice
            </button>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-5">
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Visible in list</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{resolvedNotices?.length ?? 0}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Published</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{publishedCount}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Scheduled</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{scheduledCount}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Sticky notices</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{stickyCount}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Automation blocked</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{blockedCount}</p>
        </div>
      </div>

      <SectionCard title="Filters" description="Search and slice by audience or lifecycle state.">
        <div className="grid gap-4 xl:grid-cols-[2fr_1fr_1fr]">
          <div>
            <label className="field-label" htmlFor="notice-search">
              Search
            </label>
            <input
              id="notice-search"
              className="field-input"
              placeholder="Search title, body, or category"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <div>
            <label className="field-label">Status</label>
            <AppSelect
              value={statusFilter}
              onValueChange={setStatusFilter}
              options={[{ value: '', label: 'All statuses' }, ...NOTICE_STATUS_OPTIONS.map((value) => ({ value, label: startCase(value) }))]}
            />
          </div>
          <div>
            <label className="field-label">Audience</label>
            <AppSelect
              value={audienceFilter}
              onValueChange={setAudienceFilter}
              options={[{ value: '', label: 'All audiences' }, ...NOTICE_AUDIENCE_TYPE_OPTIONS.map((value) => ({ value, label: startCase(value) }))]}
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Notices" description="Drafts, scheduled announcements, live posts, and expired notices stay visible here in one operational view.">
        <div className="space-y-4">
          {(resolvedNotices ?? []).map((notice) => (
            <div key={notice.id} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{notice.title}</p>
                    <StatusBadge tone={notice.status === 'PUBLISHED' ? 'success' : notice.status === 'SCHEDULED' ? 'warning' : notice.status === 'EXPIRED' ? 'neutral' : 'info'}>
                      {startCase(notice.status)}
                    </StatusBadge>
                    <StatusBadge tone={notice.is_automation_blocked ? 'danger' : notice.automation_state === 'WAITING_TO_PUBLISH' ? 'warning' : 'info'}>
                      {startCase(notice.automation_state)}
                    </StatusBadge>
                    {notice.is_sticky ? <StatusBadge tone="info">Sticky</StatusBadge> : null}
                  </div>
                  <p className="max-w-3xl text-sm text-[hsl(var(--muted-foreground))]">{notice.body}</p>
                  {notice.is_automation_blocked ? (
                    <p className="text-sm text-[hsl(var(--danger))]">
                      Automation is blocked. Review the schedule or expiry window so the worker can complete this lifecycle transition.
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/notices/${notice.id}`)}>
                    Edit
                  </button>
                  {notice.status !== 'PUBLISHED' ? (
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={publishMutation.isPending || publishCtMutation.isPending}
                      onClick={async () => {
                        if (isCtMode && organisationId) {
                          await publishCtMutation.mutateAsync(notice.id)
                        } else {
                          await publishMutation.mutateAsync(notice.id)
                        }
                        toast.success('Notice published.')
                      }}
                    >
                      Publish
                    </button>
                  ) : null}
                </div>
              </div>

              <div className="mt-5 grid gap-3 xl:grid-cols-4">
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Category</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{startCase(notice.category)}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Audience</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{startCase(notice.audience_type)}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Scheduled</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(notice.scheduled_for)}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Expires</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(notice.expires_at)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
