import Dexie, { type Table } from 'dexie'
import { useSyncExternalStore } from 'react'
import { dailyGoal, type SkillStat } from './coach'
import { skillKey, theoryKey, type Bank } from './data'
import { START_ELO, updateElo } from './elo'
import type { ProgressView } from './filters'
import { START_PROG, stepProg, type Prog } from './progressive'
import { setSoundEnabled } from './sounds'
import { isDue, schedule, type Card } from './srs'
import { EMPTY_STREAK, studyOn, type Streak, type StreakEvent } from './streak'
import { dayNumber, weekStart } from './time'
import { EMPTY_FILTER, type Filter, type Row } from './types'

export type Mode = 'practice' | 'review' | 'sim'

export interface Attempt {
  id?: number
  qid: string
  ts: number
  ok: boolean
  ms: number
  s: string
  t: string
  d: number
  mode: Mode
}

export interface DayStat {
  n: number
  ok: number
  ms: number
}

export interface SimResult {
  id?: number
  ts: number
  kind: 'padrao' | 'militar'
  exam?: string
  total: number
  correct: number
  answered: number
  seconds: number
  limit: number
  bySubject: Record<string, { n: number; ok: number }>
}

export interface Settings {
  sound: boolean
  theme: 'dark' | 'light'
  weeklyGoal: number
  pomoFocus: number
  pomoBreak: number
}

interface Saved {
  elo: Record<string, number>
  streak: Streak
  days: Record<number, DayStat>
  topics: Record<string, { n: number; ok: number }>
  prog: Prog
  errRun: Record<string, number>
  settings: Settings
  filter: Filter
  filterSig: string
  combo: number
}

export interface AnswerResult {
  eloDelta: number
  elo: number
  skillElo: number // Elo do subtópico da questão
  skillDelta: number
  combo: number
  streakEvent: StreakEvent
  levelChange: -1 | 0 | 1
  theoryTopic: string | null
  queued: boolean // entrou (ou ficou) na fila de revisão
  recovered: boolean // já tinha errado esta questão e agora acertou
  slow: boolean
  wrongRun: number // erros seguidos no assunto, contando este
  goalHit: boolean // a meta do dia foi batida nesta resposta
}

const THEORY_AFTER = 4
const SLOW_MS = 5 * 60_000
/** acerto demorado: merece o elogio à persistência */
const SLOW_ANSWER_MS = 3 * 60_000
const IDLE_CAP_MS = 10 * 60_000

class DB extends Dexie {
  attempts!: Table<Attempt, number>
  cards!: Table<Card, string>
  sims!: Table<SimResult, number>
  kv!: Table<{ key: string; value: unknown }, string>

  constructor() {
    super('waterlearning')
    this.version(1).stores({ attempts: '++id, qid, ts', cards: 'qid, due', sims: '++id, ts', kv: 'key' })
  }
}

function fresh(): Saved {
  return {
    elo: {}, streak: EMPTY_STREAK, days: {}, topics: {}, prog: START_PROG, errRun: {},
    settings: { sound: true, theme: 'dark', weeklyGoal: 100, pomoFocus: 25, pomoBreak: 5 },
    filter: EMPTY_FILTER, filterSig: '', combo: 0,
  }
}

class Store implements ProgressView {
  private db = new DB()
  private listeners = new Set<() => void>()
  private version = 0
  s: Saved = fresh()
  seenMap = new Map<string, number>() // qid → nº de acertos
  cards = new Map<string, Card>()
  sims: SimResult[] = []
  /** acertos e tentativas por habilidade (subtópico, ou tópico se não houver) */
  skills = new Map<string, SkillStat>()
  /** questões erradas que ainda não foram acertadas depois */
  private missed = new Set<string>()
  /** quantas questões o aluno errou e depois acertou */
  recovered = 0
  ready = false

  subscribe = (fn: () => void) => {
    this.listeners.add(fn)
    return () => void this.listeners.delete(fn)
  }
  snapshot = () => this.version

  private emit() {
    this.version++
    for (const fn of this.listeners) fn()
  }

  private persist() {
    void this.db.kv.put({ key: 'state', value: this.s }).catch(() => {})
  }

  async load(bank: Bank): Promise<void> {
    try {
      const [state, attempts, cards, sims] = await Promise.all([
        this.db.kv.get('state'), this.db.attempts.toArray(), this.db.cards.toArray(), this.db.sims.toArray(),
      ])
      if (state) this.s = { ...fresh(), ...(state.value as Saved) }
      this.s.settings = { ...fresh().settings, ...this.s.settings }
      this.s.filter = { ...EMPTY_FILTER, ...this.s.filter }
      for (const a of attempts.sort((x, y) => x.ts - y.ts)) {
        this.seenMap.set(a.qid, (this.seenMap.get(a.qid) ?? 0) + (a.ok ? 1 : 0))
        const row = bank.byId.get(a.qid)
        this.track(row ? skillKey(bank, row) : a.t, a.qid, a.ok)
      }
      for (const c of cards) if (bank.byId.has(c.qid)) this.cards.set(c.qid, c)
      this.sims = sims
    } catch {
      // sem IndexedDB (janela anônima, por exemplo): segue só em memória
    }
    // filtros guardam índices; se o banco mudou de forma, recomeça do filtro vazio
    const sig = bankSignature(bank)
    if (this.s.filterSig !== sig) this.s = { ...this.s, filter: EMPTY_FILTER, filterSig: sig }
    setSoundEnabled(this.s.settings.sound)
    this.ready = true
    this.emit()
  }

  /** conta a resposta na habilidade e diz se foi uma recuperação (errou antes, acertou agora) */
  private track(skill: string, qid: string, ok: boolean): boolean {
    const v = this.skills.get(skill) ?? { n: 0, ok: 0 }
    this.skills.set(skill, { n: v.n + 1, ok: v.ok + (ok ? 1 : 0) })
    if (!ok) {
      this.missed.add(qid)
      return false
    }
    const back = this.missed.delete(qid)
    if (back) this.recovered++
    return back
  }

  // ----- leitura -----
  todayCount(today = dayNumber()): number {
    return this.s.days[today]?.n ?? 0
  }
  dailyGoal(): number {
    return dailyGoal(this.s.settings.weeklyGoal)
  }
  seen(id: string): boolean {
    return this.seenMap.has(id)
  }
  due(id: string): boolean {
    const c = this.cards.get(id)
    return !!c && isDue(c, dayNumber())
  }
  dueCards(today = dayNumber()): Card[] {
    return [...this.cards.values()].filter((c) => isDue(c, today)).sort((a, b) => a.due - b.due)
  }
  /** Elo de uma matéria ("mat") ou de uma habilidade ("mat-equacao-2grau") */
  elo(id: string): number {
    return this.s.elo[id] ?? START_ELO
  }
  weekCount(today = dayNumber()): number {
    const start = weekStart(today)
    let n = 0
    for (let d = start; d <= today; d++) n += this.s.days[d]?.n ?? 0
    return n
  }
  totalMs(): number {
    return Object.values(this.s.days).reduce((sum, d) => sum + d.ms, 0)
  }

  // ----- escrita -----
  setFilter(filter: Filter) {
    // assunto novo começa na fixação, como capítulo novo do livro: o degrau do Progressivo não vem junto
    const sameSubject = JSON.stringify([filter.subjects, filter.topics, filter.subs]) ===
      JSON.stringify([this.s.filter.subjects, this.s.filter.topics, this.s.filter.subs])
    this.s = { ...this.s, filter, prog: sameSubject ? this.s.prog : START_PROG }
    this.persist()
    this.emit()
  }

  setSettings(patch: Partial<Settings>) {
    this.s = { ...this.s, settings: { ...this.s.settings, ...patch } }
    setSoundEnabled(this.s.settings.sound)
    if (patch.theme) {
      document.documentElement.dataset.theme = patch.theme
      try {
        localStorage.setItem('wl-theme', patch.theme)
      } catch {
        // tema só não fica lembrado
      }
    }
    this.persist()
    this.emit()
  }

  answer(bank: Bank, row: Row, ok: boolean, ms: number, mode: Mode, now = Date.now()): AnswerResult {
    const today = dayNumber(now)
    const subject = bank.meta.subjects[row.s].id
    const topic = bank.topics[row.t].id
    const s = this.s

    void this.db.attempts.add({ qid: row.id, ts: now, ok, ms, s: subject, t: topic, d: row.d, mode }).catch(() => {})
    this.seenMap.set(row.id, (this.seenMap.get(row.id) ?? 0) + (ok ? 1 : 0))

    const day = s.days[today] ?? { n: 0, ok: 0, ms: 0 }
    const days = { ...s.days, [today]: { n: day.n + 1, ok: day.ok + (ok ? 1 : 0), ms: day.ms + Math.min(ms, IDLE_CAP_MS) } }
    const tp = s.topics[topic] ?? { n: 0, ok: 0 }
    const topics = { ...s.topics, [topic]: { n: tp.n + 1, ok: tp.ok + (ok ? 1 : 0) } }

    const before = this.elo(subject)
    const after = updateElo(before, row.r, ok)
    const skill = skillKey(bank, row)
    const skillBefore = this.elo(skill)
    const skillAfter = updateElo(skillBefore, row.r, ok)
    const recovered = this.track(skill, row.id, ok)
    const goal = this.dailyGoal()
    const goalHit = day.n + 1 === goal
    const { streak, event } = studyOn(s.streak, today)

    let prog = s.prog
    let levelChange: -1 | 0 | 1 = 0
    let theoryTopic: string | null = null
    let wrongRun = 0
    const errRun = { ...s.errRun }
    if (mode !== 'sim') {
      if (mode === 'practice' && s.filter.diff === 'prog') {
        const step = stepProg(prog, ok)
        prog = step.prog
        levelChange = step.changed
      }
      errRun[topic] = ok ? 0 : (errRun[topic] ?? 0) + 1
      wrongRun = errRun[topic]
      if (errRun[topic] >= THEORY_AFTER) {
        errRun[topic] = 0
        theoryTopic = theoryKey(bank, row)
      }
    }

    const outcome = !ok ? 'wrong' : ms > SLOW_MS ? 'hard' : 'ok'
    const queued = this.reschedule(row.id, outcome, today)
    const combo = mode === 'sim' ? s.combo : ok ? s.combo + 1 : 0

    this.s = { ...s, days, topics, elo: { ...s.elo, [subject]: after, [skill]: skillAfter }, streak, prog, errRun, combo }
    this.persist()
    this.emit()
    return {
      eloDelta: after - before, elo: after, skillElo: skillAfter, skillDelta: skillAfter - skillBefore, combo, streakEvent: event, levelChange, theoryTopic, queued,
      recovered, slow: ok && ms > SLOW_ANSWER_MS, wrongRun, goalHit,
    }
  }

  private reschedule(qid: string, outcome: 'wrong' | 'hard' | 'ok', today: number): boolean {
    const next = schedule(this.cards.get(qid), qid, outcome, today)
    if (next) {
      this.cards.set(qid, next)
      void this.db.cards.put(next).catch(() => {})
    } else if (this.cards.delete(qid)) {
      void this.db.cards.delete(qid).catch(() => {})
    }
    return !!next
  }

  /** "Rever depois": o aluno acertou, mas quer ver a questão de novo. */
  markHard(qid: string) {
    const today = dayNumber()
    const card = this.cards.get(qid)
    const next: Card = card ? { ...card, due: Math.min(card.due, today + 3) } : { qid, due: today + 3, ivl: 3, ease: 2.3, reps: 0, lapses: 0 }
    this.cards.set(qid, next)
    void this.db.cards.put(next).catch(() => {})
    this.emit()
  }

  addSim(result: SimResult) {
    this.sims = [...this.sims, result]
    void this.db.sims.add(result).catch(() => {})
    this.emit()
  }

  async exportAll(): Promise<string> {
    const attempts = await this.db.attempts.toArray().catch(() => [])
    return JSON.stringify({ app: 'waterlearning', version: 1, state: this.s, attempts, cards: [...this.cards.values()], sims: this.sims })
  }

  async importAll(json: string): Promise<void> {
    const data = JSON.parse(json)
    if (data?.app !== 'waterlearning' || !data.state) throw new Error('Este arquivo não é um backup do Waterlearning.')
    await this.db.transaction('rw', this.db.attempts, this.db.cards, this.db.sims, this.db.kv, async () => {
      await Promise.all([this.db.attempts.clear(), this.db.cards.clear(), this.db.sims.clear()])
      await this.db.attempts.bulkAdd((data.attempts ?? []).map(({ id: _id, ...a }: Attempt) => a))
      await this.db.cards.bulkPut(data.cards ?? [])
      await this.db.sims.bulkAdd((data.sims ?? []).map(({ id: _id, ...r }: SimResult) => r))
      await this.db.kv.put({ key: 'state', value: data.state })
    })
    location.reload()
  }
}

function bankSignature(bank: Bank): string {
  return `${bank.meta.exams.join(',')}|${bank.topics.length}|${bank.subs.length}`
}

export const store = new Store()

/** Re-renderiza o componente quando o progresso muda. */
export function useStore(): Store {
  useSyncExternalStore(store.subscribe, store.snapshot)
  return store
}
