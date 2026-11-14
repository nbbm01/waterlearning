import type { Meta, Question, Row } from './types'

type RawRow = [string, number, number, number, number, 1 | 2 | 3, number, number, number]

export interface Bank {
  meta: Meta
  rows: Row[]
  byId: Map<string, Row>
  topics: { id: string; name: string; subject: number }[]
}

const chunks = new Map<number, Promise<Record<string, Question>>>()

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`Falha ao carregar ${path} (${res.status})`)
  return res.json() as Promise<T>
}

export async function loadBank(): Promise<Bank> {
  const [meta, raw] = await Promise.all([getJson<Meta>('/data/meta.json'), getJson<RawRow[]>('/data/index.json')])
  const rows = raw.map(([id, s, e, y, t, d, f, c, r]) => ({ id, s, e, y, t, d, f, c, r }))
  const topics = meta.subjects.flatMap((s, si) => s.topics.map((t) => ({ id: t.id, name: t.name, subject: si })))
  return { meta, rows, byId: new Map(rows.map((r) => [r.id, r])), topics }
}

function loadChunk(c: number): Promise<Record<string, Question>> {
  let p = chunks.get(c)
  if (!p) {
    p = getJson<Record<string, Question>>(`/data/chunks/${c}.json`)
    p.catch(() => chunks.delete(c))
    chunks.set(c, p)
  }
  return p
}

export async function loadQuestion(row: Row): Promise<Question> {
  const q = (await loadChunk(row.c))[row.id]
  if (!q) throw new Error(`Questão ${row.id} não encontrada`)
  return q
}

/** Aquece o bloco da próxima questão para a troca ser instantânea. */
export function prefetch(row: Row | null): void {
  if (row) void loadChunk(row.c).catch(() => {})
}
