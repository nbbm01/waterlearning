import { ALL_TRACK, type Meta, type Question, type Row } from './types'

type RawRow = [string, number, number, number, number, 1 | 2 | 3, number, number, number, number, number]

export interface Bank {
  meta: Meta
  rows: Row[]
  byId: Map<string, Row>
  topics: { id: string; name: string; subject: number }[]
  subs: { id: string; name: string; topic: number }[]
}

/**
 * Habilidade da questão: o subtópico (ou o tópico, se não houver). O Elo que escolhe questões é o dela:
 * dominar equação do 1º grau não diz nada sobre quem acabou de ver equação do 2º grau.
 */
export function skillKey(bank: Bank, row: Row): string {
  return row.u >= 0 ? bank.subs[row.u].id : bank.topics[row.t].id
}

export function skillName(bank: Bank, row: Row): string {
  return row.u >= 0 ? bank.subs[row.u].name : bank.topics[row.t].name
}

/** Nome e filtro de uma habilidade pelo id (subtópico ou tópico); null se o banco não a tem mais. */
export function skillTarget(bank: Bank, id: string): { name: string; subs: number[]; topics: number[] } | null {
  const u = bank.subs.findIndex((x) => x.id === id)
  if (u >= 0) return { name: bank.subs[u].name, subs: [u], topics: [] }
  const t = bank.topics.findIndex((x) => x.id === id)
  return t >= 0 ? { name: bank.topics[t].name, subs: [], topics: [t] } : null
}

/** card de teoria da questão: o do subtópico quando existe (quem erra equação do 1º grau não deve ver Bhaskara), senão o do tópico */
export function theoryKey(bank: Bank, row: Row): string | null {
  const sub = row.u >= 0 ? bank.subs[row.u].id : ''
  if (sub && bank.meta.theory[sub]) return sub
  const topic = bank.topics[row.t].id
  return bank.meta.theory[topic] ? topic : null
}

const BASE = import.meta.env.BASE_URL
const chunks = new Map<number, Promise<Record<string, Question>>>()
let version = ''

async function getJson<T>(path: string, fresh = false): Promise<T> {
  const res = await fetch(path, fresh ? { cache: 'no-store' } : undefined)
  if (!res.ok || !res.headers.get('content-type')?.includes('json')) throw new Error(`Falha ao carregar ${path} (${res.status})`)
  return res.json() as Promise<T>
}

export async function loadBank(): Promise<Bank> {
  const [meta, raw] = await Promise.all([getJson<Meta>(BASE + 'data/meta.json'), getJson<RawRow[]>(BASE + 'data/index.json')])
  version = meta.version
  meta.groups ??= []
  meta.tracks ??= []
  meta.examInfo ??= {}
  // índice antigo, sem trilhas: a questão vale para todas
  const rows = raw.map(([id, s, e, y, t, d, f, c, r, u, k]) => ({ id, s, e, y, t, d, f, c, r, u: u ?? -1, k: k ?? -1 }))
  const topics = meta.subjects.flatMap((s, si) => s.topics.map((t) => ({ id: t.id, name: t.name, subject: si })))
  const subs = meta.subjects.flatMap((s) => s.topics).flatMap((t, ti) => (t.subs ?? []).map((sb) => ({ id: sb.id, name: sb.name, topic: ti })))
  return { meta, rows, byId: new Map(rows.map((r) => [r.id, r])), topics, subs }
}

const trackCache = new WeakMap<Bank, Map<string, Row[]>>()

/** As questões da trilha (objetivo) escolhida; "tudo" ou trilha desconhecida devolve o banco inteiro. */
export function trackRows(bank: Bank, track: string): Row[] {
  const bit = bank.meta.tracks.findIndex((t) => t.id === track)
  if (track === ALL_TRACK || bit < 0) return bank.rows
  let cache = trackCache.get(bank)
  if (!cache) trackCache.set(bank, (cache = new Map()))
  let rows = cache.get(track)
  if (!rows) cache.set(track, (rows = bank.rows.filter((r) => r.k & (1 << bit))))
  return rows
}

/** nome da trilha para mostrar ao aluno */
export function trackName(bank: Bank, track: string): string {
  return bank.meta.tracks.find((t) => t.id === track)?.name ?? 'Todas as provas'
}

/** quantas questões cada matéria (ou banca) tem num conjunto de linhas */
export function countBy(rows: Row[], key: 's' | 'e'): Map<number, number> {
  const out = new Map<number, number>()
  for (const r of rows) out.set(r[key], (out.get(r[key]) ?? 0) + 1)
  return out
}

function loadChunk(c: number): Promise<Record<string, Question>> {
  let p = chunks.get(c)
  if (!p) {
    p = getJson<Record<string, Question>>(`${BASE}data/chunks/${c}.json?v=${version}`)
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
  const meta = await getJson<Meta>(BASE + 'data/meta.json', true).catch(() => null)
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
