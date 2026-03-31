import { useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateHolidayCalendar, useHolidayCalendars, useLocations, usePublishHolidayCalendar } from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'

const emptyCalendarForm = {
  name: '',
  year: new Date().getFullYear(),
  description: '',
  is_default: true,
  holidays: [{ name: '', holiday_date: '', classification: 'PUBLIC', session: 'FULL_DAY', description: '' }],
  location_ids: [] as string[],
}

export function HolidaysPage() {
  const { data, isLoading } = useHolidayCalendars()
  const { data: locations } = useLocations()
  const createMutation = useCreateHolidayCalendar()
  const publishMutation = usePublishHolidayCalendar()
  const [form, setForm] = useState(emptyCalendarForm)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createMutation.mutateAsync(form)
      toast.success('Holiday calendar created.')
      setForm(emptyCalendarForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create holiday calendar.'))
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
      <PageHeader eyebrow="Holidays" title="Holiday calendars" description="Define and publish annual holiday calendars, then assign them to office locations." />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Create holiday calendar" description="Holiday calendars are date-based and managed year by year, while leave cycles remain separately configurable.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            <input className="field-input" placeholder="Calendar name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required />
            <input className="field-input" type="number" value={form.year} onChange={(event) => setForm((current) => ({ ...current, year: Number(event.target.value) }))} required />
            <textarea className="field-textarea" placeholder="Description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input type="checkbox" checked={form.is_default} onChange={(event) => setForm((current) => ({ ...current, is_default: event.target.checked }))} />
              Default calendar for this year
            </label>
            <div className="grid gap-2">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Assigned office locations</p>
              {locations?.filter((location) => location.is_active).map((location) => (
                <label key={location.id} className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                  <input
                    type="checkbox"
                    checked={form.location_ids.includes(location.id)}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        location_ids: event.target.checked
                          ? [...current.location_ids, location.id]
                          : current.location_ids.filter((id) => id !== location.id),
                      }))
                    }
                  />
                  {location.name}
                </label>
              ))}
            </div>
            {form.holidays.map((holiday, index) => (
              <div key={index} className="surface-muted grid gap-3 rounded-[22px] p-4">
                <input className="field-input" placeholder="Holiday name" value={holiday.name} onChange={(event) => setForm((current) => ({ ...current, holidays: current.holidays.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item) }))} required />
                <input className="field-input" type="date" value={holiday.holiday_date} onChange={(event) => setForm((current) => ({ ...current, holidays: current.holidays.map((item, itemIndex) => itemIndex === index ? { ...item, holiday_date: event.target.value } : item) }))} required />
                <div className="grid gap-3 md:grid-cols-2">
                  <select className="field-select" value={holiday.classification} onChange={(event) => setForm((current) => ({ ...current, holidays: current.holidays.map((item, itemIndex) => itemIndex === index ? { ...item, classification: event.target.value } : item) }))}>
                    {['PUBLIC', 'RESTRICTED', 'COMPANY'].map((classification) => (
                      <option key={classification} value={classification}>
                        {classification}
                      </option>
                    ))}
                  </select>
                  <select className="field-select" value={holiday.session} onChange={(event) => setForm((current) => ({ ...current, holidays: current.holidays.map((item, itemIndex) => itemIndex === index ? { ...item, session: event.target.value } : item) }))}>
                    {['FULL_DAY', 'FIRST_HALF', 'SECOND_HALF'].map((session) => (
                      <option key={session} value={session}>
                        {session.replaceAll('_', ' ')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
            <button type="button" className="btn-secondary" onClick={() => setForm((current) => ({ ...current, holidays: [...current.holidays, { name: '', holiday_date: '', classification: 'PUBLIC', session: 'FULL_DAY', description: '' }] }))}>
              Add holiday
            </button>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              Save holiday calendar
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Published and draft calendars" description="Use separate calendars when different office locations observe different holiday schedules.">
          <div className="space-y-4">
            {data?.map((calendar) => (
              <div key={calendar.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{calendar.name}</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{calendar.year} • {calendar.holidays.length} holidays</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge tone={calendar.status === 'PUBLISHED' ? 'success' : 'warning'}>{calendar.status}</StatusBadge>
                    {calendar.status !== 'PUBLISHED' ? (
                      <button className="btn-secondary" onClick={() => void publishMutation.mutateAsync(calendar.id)}>
                        Publish
                      </button>
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {calendar.holidays.map((holiday) => (
                    <StatusBadge key={holiday.id} tone={holiday.classification === 'PUBLIC' ? 'success' : holiday.classification === 'RESTRICTED' ? 'warning' : 'info'}>
                      {holiday.name}
                    </StatusBadge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
