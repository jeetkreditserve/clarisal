import type { CalendarMonthView } from '@/types/hr'

const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const entryThemes: Record<string, string> = {
  HOLIDAY: 'border-[#0f766e]/20 bg-[#0f766e]/10 text-[#115e59]',
  LEAVE: 'border-[#2563eb]/20 bg-[#2563eb]/10 text-[#1d4ed8]',
  ON_DUTY: 'border-[#4f46e5]/20 bg-[#4f46e5]/10 text-[#4338ca]',
  WFH: 'border-[#0284c7]/20 bg-[#0284c7]/10 text-[#0369a1]',
  COMP_OFF: 'border-[#0f766e]/20 bg-[#14b8a6]/10 text-[#0f766e]',
  LWP: 'border-[#dc2626]/20 bg-[#dc2626]/10 text-[#b91c1c]',
}

function getGridPrefix(month: CalendarMonthView) {
  if (!month.days.length) return 0
  const firstDate = new Date(month.days[0].date)
  const day = firstDate.getDay()
  return day === 0 ? 6 : day - 1
}

export function MonthCalendar({ month }: { month: CalendarMonthView }) {
  const prefix = getGridPrefix(month)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-7 gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
        {weekdayLabels.map((label) => (
          <div key={label} className="px-2 py-1">
            {label}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-3">
        {Array.from({ length: prefix }).map((_, index) => (
          <div key={`empty-${index}`} className="min-h-[7.5rem] rounded-[22px] border border-dashed border-[hsl(var(--border)_/_0.4)]" />
        ))}
        {month.days.map((day) => {
          const date = new Date(day.date)
          return (
            <div key={day.date} className="surface-shell min-h-[7.5rem] rounded-[22px] border border-[hsl(var(--border)_/_0.72)] p-3">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-medium text-[hsl(var(--muted-foreground))]">{date.toLocaleDateString('en-IN', { month: 'short' })}</span>
                <span className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">{date.getDate()}</span>
              </div>
              <div className="space-y-2">
                {day.entries.map((entry, index) => (
                  <div
                    key={`${entry.kind}-${entry.date}-${index}`}
                    className={`rounded-[16px] border px-2 py-2 text-[11px] font-medium leading-4 shadow-sm ${entryThemes[entry.kind] ?? 'border-[hsl(var(--border))] bg-[hsl(var(--surface-subtle))] text-[hsl(var(--foreground-strong))]'}`}
                    style={entryThemes[entry.kind] ? undefined : { borderColor: entry.color, backgroundColor: `${entry.color}15`, color: entry.color }}
                  >
                    <p>{entry.label}</p>
                    <p className="mt-1 text-[10px] uppercase tracking-[0.12em] opacity-70">{entry.status}</p>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
