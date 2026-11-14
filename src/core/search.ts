import type { Meta, Row } from './types'

export interface Hit {
  kind: 'topic' | 'sub' | 'exam' | 'subject'
  index: number
  label: string
  hint: string
  count: number
}

const STOP = new Set(['de', 'do', 'da', 'dos', 'das', 'e', 'o', 'a', 'os', 'as', 'em', 'no', 'na', 'com', 'para', 'por', 'um', 'uma'])
const ORDINALS: Record<string, string> = {
  primeiro: '1', primeira: '1', '1o': '1', '1a': '1', segundo: '2', segunda: '2', '2o': '2', '2a': '2',
  terceiro: '3', '3o': '3', mu: 'mru', mruv: 'muv',
}

export function fold(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/º|ª/g, 'o').trim()
}

/** palavras significativas, com "primeiro"/"1º" e afins unificados */
function words(text: string): string[] {
  return fold(text)
    .split(/[^a-z0-9]+/)
    .filter((w) => w && !STOP.has(w))
    .map((w) => ORDINALS[w] ?? w)
}

/** quanto a consulta casa com um rótulo: todas as palavras precisam aparecer (por prefixo) */
function score(query: string[], label: string): number {
  if (!query.length) return 0
  const target = words(label)
  let total = 0
  for (const q of query) {
    let best = 0
    for (const t of target) {
      if (t === q) best = Math.max(best, 3)
      else if (t.startsWith(q) && q.length >= 2) best = Math.max(best, 2)
      else if (q.length >= 4 && t.startsWith(q.slice(0, -1))) best = Math.max(best, 1) // plural/singular
    }
    if (!best) return 0
    total += best
  }
  // casar o rótulo inteiro vale mais que casar parte dele
  return (total / query.length) * 30 + (target.length === query.length ? 10 : 0)
}

function bestOf(query: string[], labels: string[]): number {
  return Math.max(0, ...labels.map((l) => score(query, l)))
}

/** Busca por tópico, banca ou matéria: o aluno digita e já sai praticando. */
export function searchAll(meta: Meta, rows: Row[], raw: string, limit = 8): Hit[] {
  const query = words(raw)
  if (!query.length) return []
  const byTopic = new Map<number, number>()
  const byExam = new Map<number, number>()
  const bySubject = new Map<number, number>()
  const bySub = new Map<number, number>()
  for (const r of rows) {
    if (r.u >= 0) bySub.set(r.u, (bySub.get(r.u) ?? 0) + 1)
    byTopic.set(r.t, (byTopic.get(r.t) ?? 0) + 1)
    byExam.set(r.e, (byExam.get(r.e) ?? 0) + 1)
    bySubject.set(r.s, (bySubject.get(r.s) ?? 0) + 1)
  }
  const hits: (Hit & { sc: number })[] = []
  let ti = 0
  let ui = 0
  meta.subjects.forEach((s, si) => {
    const sc = bestOf(query, [s.name])
    if (sc) hits.push({ kind: 'subject', index: si, label: s.name, hint: 'Matéria', count: bySubject.get(si) ?? 0, sc: sc + 5 })
    for (const t of s.topics) {
      const named = bestOf(query, [t.name])
      const alias = bestOf(query, t.aliases)
      const sc = Math.max(named + 3, alias)
      if (sc > 3) {
        // mostra qual apelido casou, para o aluno entender por que o tópico apareceu
        const matched = !named ? t.aliases.find((a) => score(query, a) === alias) : undefined
        hits.push({
          kind: 'topic', index: ti, label: t.name, hint: matched ? `${s.name} · “${matched}”` : s.name,
          count: byTopic.get(ti) ?? 0, sc,
        })
      }
      for (const sb of t.subs ?? []) {
        const sc = Math.max(bestOf(query, [sb.name]) + 4, bestOf(query, sb.aliases) + 2)
        if (sc > 4) hits.push({ kind: 'sub', index: ui, label: sb.name, hint: `${s.name} · ${t.name}`, count: bySub.get(ui) ?? 0, sc })
        ui++
      }
      ti++
    }
  })
  meta.exams.forEach((e, ei) => {
    const sc = bestOf(query, [e])
    if (sc) hits.push({ kind: 'exam', index: ei, label: e, hint: 'Vestibular', count: byExam.get(ei) ?? 0, sc: sc + 4 })
  })
  return hits.filter((h) => h.count > 0).sort((a, b) => b.sc - a.sc || b.count - a.count).slice(0, limit)
}
