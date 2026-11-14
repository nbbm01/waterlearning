import type { Meta, Row } from './types'

export interface Hit {
  kind: 'topic' | 'exam' | 'subject'
  index: number
  label: string
  hint: string
  count: number
}

export function fold(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

function score(query: string, words: string[]): number {
  let best = 0
  for (const w of words) {
    const f = fold(w)
    if (f === query) best = Math.max(best, 100)
    else if (f.startsWith(query)) best = Math.max(best, 80)
    else if (f.split(/[\s,]+/).some((p) => p.startsWith(query))) best = Math.max(best, 60)
    else if (query.length >= 3 && f.includes(query)) best = Math.max(best, 40)
  }
  return best
}

/** Busca por tópico, banca ou matéria: o aluno digita e já sai praticando. */
export function searchAll(meta: Meta, rows: Row[], raw: string, limit = 8): Hit[] {
  const query = fold(raw)
  if (!query) return []
  const byTopic = new Map<number, number>()
  const byExam = new Map<number, number>()
  const bySubject = new Map<number, number>()
  for (const r of rows) {
    byTopic.set(r.t, (byTopic.get(r.t) ?? 0) + 1)
    byExam.set(r.e, (byExam.get(r.e) ?? 0) + 1)
    bySubject.set(r.s, (bySubject.get(r.s) ?? 0) + 1)
  }
  const hits: (Hit & { sc: number })[] = []
  let ti = 0
  meta.subjects.forEach((s, si) => {
    const sc = score(query, [s.name])
    if (sc) hits.push({ kind: 'subject', index: si, label: s.name, hint: 'Matéria', count: bySubject.get(si) ?? 0, sc: sc + 5 })
    for (const t of s.topics) {
      const named = score(query, [t.name])
      const alias = score(query, t.aliases)
      const tsc = Math.max(named + 3, alias)
      if (tsc > 3) hits.push({ kind: 'topic', index: ti, label: t.name, hint: s.name, count: byTopic.get(ti) ?? 0, sc: tsc })
      ti++
    }
  })
  meta.exams.forEach((e, ei) => {
    const sc = score(query, [e])
    if (sc) hits.push({ kind: 'exam', index: ei, label: e, hint: 'Vestibular', count: byExam.get(ei) ?? 0, sc: sc + 4 })
  })
  return hits.filter((h) => h.count > 0).sort((a, b) => b.sc - a.sc || b.count - a.count).slice(0, limit)
}
