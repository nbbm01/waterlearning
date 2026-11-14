import type { Meta, Question, Row } from './types'

type RawRow = [string, number, number, number, number, 1 | 2 | 3, number, number, number, number]

export interface Bank {
  meta: Meta
  rows: Row[]
  byId: Map<string, Row>
  topics: { id: string; name: string; subject: number }[]
  subs: { id: string; name: string; topic: number }[]
}

const chunks = new Map<number, Promise<Record<string, Question>>>()
let version = ''

async function getJson<T>(path: string, fresh = false): Promise<T> {
  const res = await fetch(path, fresh ? { cache: 'no-store' } : undefined)
  if (!res.ok || !res.headers.get('content-type')?.includes('json')) throw new Error(`Falha ao carregar ${path} (${res.status})`)
  return res.json() as Promise<T>
}

export async function loadBank(): Promise<Bank> {
  const [meta, raw] = await Promise.all([getJson<Meta>('/data/meta.json'), getJson<RawRow[]>('/data/index.json')])
  version = meta.version
  const rows = raw.map(([id, s, e, y, t, d, f, c, r, u]) => ({ id, s, e, y, t, d, f, c, r, u: u ?? -1 }))
  const topics = meta.subjects.flatMap((s, si) => s.topics.map((t) => ({ id: t.id, name: t.name, subject: si })))
  const subs = meta.subjects.flatMap((s) => s.topics).flatMap((t, ti) => (t.subs ?? []).map((sb) => ({ id: sb.id, name: sb.name, topic: ti })))
  return { meta, rows, byId: new Map(rows.map((r) => [r.id, r])), topics, subs }
}

function loadChunk(c: number): Promise<Record<string, Question>> {
  let p = chunks.get(c)
  if (!p) {
    p = getJson<Record<string, Question>>(`/data/chunks/${c}.json?v=${version}`)
    p.catch(() => chunks.delete(c))
    chunks.set(c, p)
  }
  return p
}

export async function loadQuestion(row: Row): Promise<Question> {
  try {
    const q = (await loadChunk(row.c))[row.id]
    if (q) return q
  } catch {
    // cai na checagem de versão abaixo
  }
  // o banco foi reconstruído com a página aberta: recarrega para pegar o índice novo
  const meta = await getJson<Meta>('/data/meta.json', true).catch(() => null)
  if (meta && meta.version !== version) {
    location.reload()
    return new Promise<Question>(() => {})
  }
  throw new Error(`Questão ${row.id} não encontrada`)
}

/** Aquece o bloco da próxima questão para a troca ser instantânea. */
export function prefetch(row: Row | null): void {
  if (row) void loadChunk(row.c).catch(() => {})
}
