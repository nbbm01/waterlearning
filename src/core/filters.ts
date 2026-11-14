import { F_CLASSIC, F_COMMENTED, F_MILITARY, type Filter, type Row } from './types'

/** O que os filtros precisam saber do progresso do aluno. */
export interface ProgressView {
  seen(id: string): boolean
  due(id: string): boolean
}

export function matches(row: Row, f: Filter, p: ProgressView): boolean {
  if (f.subjects.length && !f.subjects.includes(row.s)) return false
  if (f.exams.length && !f.exams.includes(row.e)) return false
  if (f.topics.length && !f.topics.includes(row.t)) return false
  if (f.subs?.length && !f.subs.includes(row.u)) return false
  if (f.yearMin && (!row.y || row.y < f.yearMin)) return false
  if (f.yearMax && (!row.y || row.y > f.yearMax)) return false
  if (typeof f.diff === 'number' && f.diff && row.d !== f.diff) return false
  if (f.classic && !(row.f & F_CLASSIC)) return false
  if (f.military && !(row.f & F_MILITARY)) return false
  if (f.commented && !(row.f & F_COMMENTED)) return false
  if (f.unseen && p.seen(row.id)) return false
  if (f.pending && !p.due(row.id)) return false
  return true
}

export function select(rows: Row[], f: Filter, p: ProgressView): Row[] {
  return rows.filter((r) => matches(r, f, p))
}

export function isEmptyFilter(f: Filter): boolean {
  return !f.subjects.length && !f.exams.length && !f.topics.length && !f.subs?.length && !f.yearMin && !f.yearMax &&
    (f.diff === 'prog' || f.diff === 0) && !f.pending && !f.unseen && !f.classic && !f.military && !f.commented
}

/**
 * Escolhe a próxima questão do conjunto filtrado: evita as recentes, prefere as inéditas
 * e, no modo progressivo, fica no nível atual (caindo para o mais próximo se faltar questão).
 */
export function pickNext(
  pool: Row[], p: ProgressView, recent: readonly string[], level: 0 | 1 | 2 | 3, random: () => number = Math.random,
): Row | null {
  if (!pool.length) return null
  let cands = pool.filter((r) => !recent.includes(r.id))
  if (!cands.length) cands = pool
  if (level) {
    for (const d of [level, level - 1, level + 1, level - 2, level + 2]) {
      const sub = cands.filter((r) => r.d === d)
      if (sub.length) {
        cands = sub
        break
      }
    }
  }
  const fresh = cands.filter((r) => !p.seen(r.id))
  if (fresh.length) cands = fresh
  return cands[Math.floor(random() * cands.length)]
}
