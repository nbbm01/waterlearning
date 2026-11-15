import { F_CLASSIC, F_COMMENTED, F_DEEP, F_MILITARY, type Filter, type Row } from './types'

/** O que os filtros precisam saber do progresso do aluno. */
export interface ProgressView {
  seen(id: string): boolean
  due(id: string): boolean
}

export function matches(row: Row, f: Filter, p: ProgressView, unlocked?: (r: Row) => boolean): boolean {
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
  // aprofundamento só entra quando pedido (atalho) ou quando a banca foi escolhida de propósito
  if (row.f & F_DEEP && !f.deep && !f.exams.length && !unlocked?.(row)) return false
  if (f.unseen && p.seen(row.id)) return false
  if (f.pending && !p.due(row.id)) return false
  return true
}

export function select(rows: Row[], f: Filter, p: ProgressView, unlocked?: (r: Row) => boolean): Row[] {
  return rows.filter((r) => matches(r, f, p, unlocked))
}

export function isEmptyFilter(f: Filter): boolean {
  return !f.subjects.length && !f.exams.length && !f.topics.length && !f.subs?.length && !f.yearMin && !f.yearMax &&
    (f.diff === 'prog' || f.diff === 0) && !f.pending && !f.unseen && !f.classic && !f.military && !f.commented && !f.deep
}

/** chance de acerto desejada em cada degrau do modo Progressivo */
export const TARGET = { 1: 0.82, 2: 0.74, 3: 0.65 } as const

/** molde da questão autoral (autoral-<gerador>-<semente>), para não repetir o mesmo molde em sequência */
export const mold = (id: string) => (id.startsWith('autoral-') ? id.split('-')[1] : id)

/**
 * Escolhe a próxima questão do conjunto filtrado: evita as recentes, prefere as inéditas
 * e, no modo progressivo, fica no nível atual (caindo para o mais próximo se faltar questão).
 */
export function pickNext(
  pool: Row[], p: ProgressView, recent: readonly string[], level: 0 | 1 | 2 | 3, random: () => number = Math.random,
  chance?: (r: Row) => number,
): Row | null {
  if (!pool.length) return null
  let cands = pool.filter((r) => !recent.includes(r.id))
  if (!cands.length) cands = pool
  if (level) {
    // o degrau manda (como no livro: depois da fixação vêm os problemas); o Elo só escolhe dentro dele
    for (const d of [level, level - 1, level + 1, level - 2, level + 2]) {
      const sub = cands.filter((r) => r.d === d)
      if (sub.length) {
        cands = sub
        break
      }
    }
  }
  // variedade dentro do degrau: evita repetir o molde das últimas questões, se houver outro disponível
  // (antes do degrau, esvaziava os moldes fáceis e só sobrava questão difícil)
  const recentMolds = new Set(recent.slice(-4).map(mold))
  const varied = cands.filter((r) => !recentMolds.has(mold(r.id)))
  if (varied.length) cands = varied
  if (level && chance) {
    // zona de desenvolvimento proximal: dentro do degrau, mira uma chance de acerto alta
    const target = TARGET[level]
    const fresh = cands.filter((r) => !p.seen(r.id))
    const base = fresh.length ? fresh : cands
    const scored = base.map((r) => ({ r, gap: Math.abs(chance(r) - target) }))
    scored.sort((a, b) => a.gap - b.gap)
    const best = scored.filter((x) => x.gap <= scored[0].gap + 0.06).slice(0, 40)
    return best[Math.floor(random() * best.length)].r
  }
  const fresh = cands.filter((r) => !p.seen(r.id))
  if (fresh.length) cands = fresh
  return cands[Math.floor(random() * cands.length)]
}
