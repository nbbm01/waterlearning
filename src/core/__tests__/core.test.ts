import { describe, expect, it } from 'vitest'
import { updateElo } from '../elo'
import { matches, pickNext, type ProgressView } from '../filters'
import { START_PROG, stepProg } from '../progressive'
import { renderRich } from '../rich'
import { GRADUATE_AFTER, schedule } from '../srs'
import { EMPTY_STREAK, studyOn, visibleStreak, type Streak } from '../streak'
import { EMPTY_FILTER, F_MILITARY, type Row } from '../types'

const row = (p: Partial<Row>): Row => ({ id: 'q', s: 0, e: 0, y: 2020, t: 0, d: 2, f: 0, c: 0, r: 1250, u: -1, ...p })
const none: ProgressView = { seen: () => false, due: () => false }

describe('srs', () => {
  it('acerto sem cartão não cria revisão', () => {
    expect(schedule(undefined, 'a', 'ok', 100)).toBeNull()
  })
  it('erro entra na fila para amanhã', () => {
    expect(schedule(undefined, 'a', 'wrong', 100)).toMatchObject({ due: 101, ivl: 1 })
  })
  it('intervalos crescem com acertos na data e o cartão se forma', () => {
    let c = schedule(undefined, 'a', 'wrong', 0)!
    const dues: number[] = []
    for (let i = 0; i < 20 && c; i++) {
      const next = schedule(c, 'a', 'ok', c.due)
      if (!next) break
      dues.push(next.ivl)
      c = next
    }
    expect(dues.slice(0, 3)).toEqual([3, 7, 16])
    expect(dues.every((v, i) => i === 0 || v > dues[i - 1])).toBe(true)
    expect(dues.at(-1)!).toBeLessThanOrEqual(GRADUATE_AFTER)
  })
  it('acerto antes do vencimento não mexe na agenda', () => {
    const c = schedule(undefined, 'a', 'wrong', 0)!
    expect(schedule(c, 'a', 'ok', 0)).toBe(c)
  })
  it('erro em revisão volta para 1 dia', () => {
    const c = { qid: 'a', due: 10, ivl: 7, ease: 2.5, reps: 3, lapses: 1 }
    expect(schedule(c, 'a', 'wrong', 10)).toMatchObject({ due: 11, ivl: 1, reps: 0, lapses: 2 })
  })
})

describe('elo', () => {
  it('acertar questão difícil rende mais que fácil', () => {
    expect(updateElo(1000, 1500, true) - 1000).toBeGreaterThan(updateElo(1000, 800, true) - 1000)
  })
  it('errar questão fácil custa mais que difícil', () => {
    expect(1000 - updateElo(1000, 700, false)).toBeGreaterThan(1000 - updateElo(1000, 1500, false))
  })
})

describe('streak', () => {
  const run = (days: number[]) => days.reduce<Streak>((s, d) => studyOn(s, d).streak, EMPTY_STREAK)
  it('conta dias seguidos e ignora repetição no mesmo dia', () => {
    expect(run([1, 1, 2, 3]).count).toBe(3)
  })
  it('ganha escudo a cada 7 dias, até 2', () => {
    expect(run([1, 2, 3, 4, 5, 6, 7]).shields).toBe(1)
    expect(run(Array.from({ length: 21 }, (_, i) => i + 1)).shields).toBe(2)
  })
  it('escudo absorve um dia perdido', () => {
    const s = run([1, 2, 3, 4, 5, 6, 7])
    const r = studyOn(s, 9)
    expect(r.event).toMatchObject({ kind: 'shielded', used: 1 })
    expect(r.streak).toMatchObject({ count: 8, shields: 0 })
  })
  it('sem escudo, a sequência recomeça', () => {
    const r = studyOn(run([1, 2, 3]), 5)
    expect(r.event).toMatchObject({ kind: 'restart', previous: 3 })
    expect(r.streak.count).toBe(1)
  })
  it('exibição considera escudos antes de estudar hoje', () => {
    const s = run([1, 2, 3, 4, 5, 6, 7])
    expect(visibleStreak(s, 9)).toMatchObject({ count: 7, atRisk: true, shieldsLeft: 0 })
    expect(visibleStreak(s, 10).count).toBe(0)
  })
})

describe('progressivo', () => {
  it('sobe após 3 acertos e desce após 2 erros', () => {
    let p = START_PROG
    for (let i = 0; i < 3; i++) p = stepProg(p, true).prog
    expect(p.level).toBe(2)
    p = stepProg(stepProg(p, false).prog, false).prog
    expect(p.level).toBe(1)
  })
})

describe('filtros', () => {
  it('filtra por subtópico', () => {
    expect(matches(row({ u: 3 }), { ...EMPTY_FILTER, subs: [3] }, none)).toBe(true)
    expect(matches(row({ u: -1 }), { ...EMPTY_FILTER, subs: [3] }, none)).toBe(false)
  })
  it('combina matéria, banca, ano, dificuldade e atalhos', () => {
    const r = row({ s: 1, e: 2, y: 2018, d: 3, f: F_MILITARY })
    expect(matches(r, { ...EMPTY_FILTER, subjects: [1], exams: [2], yearMin: 2015, diff: 3, military: true }, none)).toBe(true)
    expect(matches(r, { ...EMPTY_FILTER, yearMax: 2017 }, none)).toBe(false)
    expect(matches(r, { ...EMPTY_FILTER, classic: true }, none)).toBe(false)
    expect(matches(r, { ...EMPTY_FILTER, unseen: true }, { seen: () => true, due: () => false })).toBe(false)
  })
  it('progressivo prefere o nível atual e questões inéditas', () => {
    const pool = [row({ id: 'a', d: 1 }), row({ id: 'b', d: 2 }), row({ id: 'c', d: 2 })]
    const seen: ProgressView = { seen: (id) => id === 'b', due: () => false }
    expect(pickNext(pool, seen, [], 2)!.id).toBe('c')
    expect(pickNext(pool, none, ['b', 'c'], 2)!.id).toBe('a')
  })
})

describe('texto rico', () => {
  it('renderiza KaTeX e preserva valores em reais', () => {
    const html = renderRich('Custa R$ 5,00 e R$ 7,00. Calcule \\(x^2\\).')
    expect(html).toContain('R$ 5,00 e R$ 7,00')
    expect(html).toContain('katex')
  })
  it('escapa HTML do enunciado', () => {
    expect(renderRich('<script>x</script>')).not.toContain('<script>')
  })
})

describe('busca de tópico', async () => {
  const { searchAll } = await import('../search')
  const meta = {
    subjects: [{ id: 'mat', name: 'Matemática', topics: [
      { id: 'f', name: 'Funções, Equações e Inequações', aliases: ['função afim', 'bhaskara'], subs: [{ id: 'e1', name: 'Equação do 1º grau', aliases: ['equação do primeiro grau'] }] },
      { id: 'l', name: 'Logaritmos e Exponenciais', aliases: ['logaritmo'], subs: [] },
    ] }],
    version: 't', exams: ['ENEM', 'ITA'], military: [], total: 2, theory: {}, sims: {},
  }
  const rows = [row({ id: 'a', t: 0, u: 0 }), row({ id: 'b', t: 1, e: 1 })]
  it('entende "primeiro" como "1º" e ignora "do"', () => {
    expect(searchAll(meta, rows, 'equação do primeiro grau')[0]).toMatchObject({ kind: 'sub', label: 'Equação do 1º grau' })
    expect(searchAll(meta, rows, 'equacao 1o grau')[0]).toMatchObject({ kind: 'sub', label: 'Equação do 1º grau' })
  })
  it('casa por prefixo e plural', () => {
    expect(searchAll(meta, rows, 'logaritmos')[0].label).toBe('Logaritmos e Exponenciais')
    expect(searchAll(meta, rows, 'log')[0].label).toBe('Logaritmos e Exponenciais')
  })
  it('acha banca pelo nome', () => {
    expect(searchAll(meta, rows, 'ita')[0]).toMatchObject({ kind: 'exam', label: 'ITA' })
  })
})
