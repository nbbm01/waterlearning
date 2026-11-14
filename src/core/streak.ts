export interface Streak {
  count: number
  lastDay: number // último dia com estudo (0 = nunca)
  shields: number
  best: number
}

export const MAX_SHIELDS = 2
export const SHIELD_EVERY = 7
export const EMPTY_STREAK: Streak = { count: 0, lastDay: 0, shields: 0, best: 0 }

export type StreakEvent =
  | { kind: 'same' }
  | { kind: 'start' }
  | { kind: 'continue'; shieldEarned: boolean }
  | { kind: 'shielded'; used: number; shieldEarned: boolean }
  | { kind: 'restart'; previous: number }

/** Registra estudo no dia `today` e diz o que aconteceu com a sequência. */
export function studyOn(s: Streak, today: number): { streak: Streak; event: StreakEvent } {
  if (s.lastDay === today) return { streak: s, event: { kind: 'same' } }
  if (!s.lastDay || s.count === 0) {
    return { streak: { ...s, count: 1, lastDay: today, best: Math.max(s.best, 1) }, event: { kind: 'start' } }
  }
  const missed = today - s.lastDay - 1
  if (missed > s.shields) {
    return { streak: { count: 1, lastDay: today, shields: 0, best: s.best }, event: { kind: 'restart', previous: s.count } }
  }
  const count = s.count + 1
  const shieldEarned = count % SHIELD_EVERY === 0
  const shields = Math.min(MAX_SHIELDS, s.shields - missed + (shieldEarned ? 1 : 0))
  const streak = { count, lastDay: today, shields, best: Math.max(s.best, count) }
  return {
    streak,
    event: missed > 0 ? { kind: 'shielded', used: missed, shieldEarned } : { kind: 'continue', shieldEarned },
  }
}

/** Sequência a exibir hoje, antes de o aluno estudar: os escudos ainda seguram as faltas? */
export function visibleStreak(s: Streak, today: number): { count: number; atRisk: boolean; shieldsLeft: number } {
  if (!s.lastDay) return { count: 0, atRisk: false, shieldsLeft: 0 }
  const missed = Math.max(0, today - s.lastDay - 1)
  if (missed > s.shields) return { count: 0, atRisk: false, shieldsLeft: 0 }
  return { count: s.count, atRisk: s.lastDay !== today, shieldsLeft: s.shields - missed }
}
