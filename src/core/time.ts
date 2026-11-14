const DAY = 86_400_000

/** Número do dia local (dias desde a época), para comparar dias sem fuso atrapalhar. */
export function dayNumber(ts: number = Date.now()): number {
  const d = new Date(ts)
  return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY)
}

export function dayToDate(day: number): Date {
  const d = new Date(day * DAY)
  return new Date(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
}

/** Dia em que começa a semana (segunda-feira) do dia informado. */
export function weekStart(day: number): number {
  const dow = (dayToDate(day).getDay() + 6) % 7
  return day - dow
}

export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const pad = (n: number) => String(n).padStart(2, '0')
  return h ? `${h}:${pad(m)}:${pad(s % 60)}` : `${pad(m)}:${pad(s % 60)}`
}

export function formatHours(ms: number): string {
  const min = Math.round(ms / 60_000)
  if (min < 60) return `${min} min`
  return `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min`
}
