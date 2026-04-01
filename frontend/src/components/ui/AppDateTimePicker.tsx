import * as Popover from '@radix-ui/react-popover'
import { format, parseISO } from 'date-fns'
import { CalendarClock } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { DayPicker } from 'react-day-picker'

import { cn } from '@/lib/utils'

interface AppDateTimePickerProps {
  id?: string
  value?: string | null
  onValueChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
}

export function AppDateTimePicker({
  id,
  value,
  onValueChange,
  placeholder = 'Select date and time',
  disabled,
}: AppDateTimePickerProps) {
  const [open, setOpen] = useState(false)
  const selectedDateTime = useMemo(() => {
    if (!value) return null
    try {
      return parseISO(value)
    } catch {
      return null
    }
  }, [value])
  const [draftDate, setDraftDate] = useState<Date | undefined>(selectedDateTime ?? undefined)
  const [draftTime, setDraftTime] = useState(selectedDateTime ? format(selectedDateTime, 'HH:mm') : '09:00')

  useEffect(() => {
    setDraftDate(selectedDateTime ?? undefined)
    setDraftTime(selectedDateTime ? format(selectedDateTime, 'HH:mm') : '09:00')
  }, [selectedDateTime])

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          id={id}
          type="button"
          disabled={disabled}
          className={cn(
            'field-input flex items-center justify-between gap-3 text-left disabled:cursor-not-allowed disabled:opacity-60',
            !selectedDateTime && 'text-[hsl(var(--muted-foreground))]',
          )}
        >
          <span>{selectedDateTime ? format(selectedDateTime, 'dd MMM yyyy, HH:mm') : placeholder}</span>
          <CalendarClock className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={8}
          align="start"
          className="z-50 rounded-[1.4rem] border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-3 shadow-[var(--shadow-card)] backdrop-blur-xl"
        >
          <div className="grid gap-4 md:grid-cols-[1fr_auto]">
            <DayPicker
              mode="single"
              selected={draftDate}
              onSelect={setDraftDate}
              showOutsideDays
              classNames={{
                months: 'flex flex-col',
                month: 'space-y-3',
                caption: 'flex items-center justify-between px-1 pt-1',
                caption_label: 'text-sm font-semibold text-[hsl(var(--foreground-strong))]',
                nav: 'flex items-center gap-1',
                button_previous:
                  'inline-flex h-8 w-8 items-center justify-center rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface))] text-[hsl(var(--foreground))] transition hover:bg-[hsl(var(--surface-subtle))]',
                button_next:
                  'inline-flex h-8 w-8 items-center justify-center rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface))] text-[hsl(var(--foreground))] transition hover:bg-[hsl(var(--surface-subtle))]',
                weekdays: 'grid grid-cols-7 gap-1',
                weekday:
                  'h-8 w-10 text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]',
                week: 'grid grid-cols-7 gap-1',
                day: 'inline-flex h-10 w-10 items-center justify-center rounded-[0.95rem] text-sm font-medium text-[hsl(var(--foreground))] transition hover:bg-[hsl(var(--surface-subtle))]',
                selected: 'bg-[hsl(var(--brand))] text-[hsl(var(--brand-foreground))] hover:bg-[hsl(var(--brand))]',
                today: 'border border-[hsl(var(--ring)/0.35)]',
                outside: 'text-[hsl(var(--muted-foreground))] opacity-45',
              }}
            />
            <div className="flex min-w-40 flex-col gap-3">
              <label className="field-label mb-0" htmlFor={id ? `${id}-time` : undefined}>
                Time
              </label>
              <input
                id={id ? `${id}-time` : undefined}
                type="time"
                className="field-input"
                value={draftTime}
                onChange={(event) => setDraftTime(event.target.value)}
              />
              <button
                type="button"
                className="btn-primary"
                disabled={!draftDate}
                onClick={() => {
                  if (!draftDate) return
                  onValueChange(`${format(draftDate, 'yyyy-MM-dd')}T${draftTime}`)
                  setOpen(false)
                }}
              >
                Apply date and time
              </button>
            </div>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
