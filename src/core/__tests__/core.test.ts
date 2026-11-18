import { describe, expect, it } from 'vitest'
import { dailyGoal, feedbackLine, needsBreak, suggest, weakSpots } from '../coach'
import { updateElo } from '../elo'
import { matches, pickNext, type ProgressView } from '../filters'
import { START_PROG, stepProg } from '../progressive'
import { renderRich } from '../rich'
import { GRADUATE_AFTER, schedule } from '../srs'
import { EMPTY_STREAK, studyOn, visibleStreak, type Streak } from '../streak'
import { EMPTY_FILTER, F_MILITARY, type Row } from '../types'

const row = (p: Partial<Row>): Row => ({ id: 'q', s: 0, e: 0, y: 2020, t: 0, d: 2, f: 0, c: 0, r: 1250, u: -1, k: -1, ...p })
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
  it('só sobe com domínio: 3 acertos seguidos não bastam, 7 de 8 sim', () => {
    let p = START_PROG
    for (let i = 0; i < 3; i++) p = stepProg(p, true).prog
    expect(p.level).toBe(1)
    // um erro no meio não zera o progresso
    for (const ok of [false, true, true, true]) p = stepProg(p, ok).prog
    expect(p.level).toBe(1)
    expect(stepProg(p, true).changed).toBe(1)
  })
  it('um erro isolado não derruba; 3 erros em 4 voltam um degrau', () => {
    let p = { level: 2 as const, hist: [] as boolean[] }
    for (const ok of [false, true, false]) p = stepProg(p, ok).prog as typeof p
    expect(p.level).toBe(2)
    expect(stepProg(p, false).prog.level).toBe(1)
  })
  it('aceita o estado salvo pela versão antiga (sem hist)', () => {
    expect(stepProg({ level: 1, run: 2 } as never, true).prog.hist).toEqual([true])
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
  it('variedade de molde não tira o aluno do degrau', () => {
    // todos os moldes médios foram vistos há pouco: repete um molde, mas não pula para a difícil
    const pool = [row({ id: 'autoral-area-1', d: 2 }), row({ id: 'autoral-raizes-1', d: 2 }), row({ id: 'espcex-1', d: 3 })]
    expect(pickNext(pool, none, ['autoral-area-0', 'autoral-raizes-0'], 2)!.d).toBe(2)
    expect(pickNext(pool, none, ['autoral-area-0'], 2)!.id).toBe('autoral-raizes-1')
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
    version: 't', exams: ['ENEM', 'ITA'], military: [], total: 2, theory: {}, sims: {}, groups: [], tracks: [], examInfo: {},
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

describe('degrau que o recorte permite', async () => {
  const { levelFor } = await import('../progressive')
  it('sem fixação (OAB, Medicina), o primeiro degrau é a aplicação', () => {
    expect(levelFor(1, new Set([2, 3]))).toBe(2)
  })
  it('sem desafio, não fica preso num degrau vazio', () => {
    expect(levelFor(3, new Set([1, 2]))).toBe(2)
  })
  it('recorte completo não muda nada', () => {
    expect(levelFor(1, new Set([1, 2, 3]))).toBe(1)
    expect(levelFor(3, new Set([1, 2, 3]))).toBe(3)
  })
  it('buraco no meio: o mais próximo, descendo', () => {
    expect(levelFor(2, new Set([1, 3]))).toBe(1)
  })
})

describe('trilhas (objetivo do aluno)', async () => {
  const { trackRows, trackName, countBy } = await import('../data')
  const meta = {
    subjects: [], version: 't', exams: ['ENEM', 'OAB'], military: [], total: 3, theory: {}, sims: {}, examInfo: {},
    groups: [{ id: 'enem', name: 'ENEM', exams: [0] }, { id: 'oab', name: 'OAB', exams: [1] }],
    tracks: [{ id: 'vestibular', name: 'ENEM e vestibulares', desc: '' }, { id: 'oab', name: 'OAB e Direito', desc: '' }],
  }
  // bit 0 = vestibular, bit 1 = oab; -1 = índice antigo, sem trilhas
  const rows = [row({ id: 'enem', k: 1 }), row({ id: 'oab', k: 2, e: 1, s: 1 }), row({ id: 'velha', k: -1 })]
  const bank = { meta, rows, byId: new Map(rows.map((r) => [r.id, r])), topics: [], subs: [] }
  it('recorta o banco pela trilha; questão de índice antigo vale para todas', () => {
    expect(trackRows(bank, 'vestibular').map((r) => r.id)).toEqual(['enem', 'velha'])
    expect(trackRows(bank, 'oab').map((r) => r.id)).toEqual(['oab', 'velha'])
  })
  it('"tudo" e trilha desconhecida devolvem o banco inteiro', () => {
    expect(trackRows(bank, 'tudo')).toBe(rows)
    expect(trackRows(bank, 'sumiu')).toBe(rows)
    expect(trackName(bank, 'tudo')).toBe('Todas as provas')
  })
  it('guarda o recorte: a mesma trilha devolve a mesma lista', () => {
    expect(trackRows(bank, 'oab')).toBe(trackRows(bank, 'oab'))
  })
  it('conta por matéria', () => {
    expect(countBy(rows, 's')).toEqual(new Map([[0, 2], [1, 1]]))
  })
})

describe('progressivo por Elo', () => {
  it('quem começa não recebe ITA: escolhe a questão com chance de acerto perto do alvo', async () => {
    const { expected } = await import('../elo')
    const pool = [row({ id: 'treino', r: 800 }), row({ id: 'aplicacao', r: 1050 }), row({ id: 'ita', r: 1600 })]
    const chance = (r: Row) => expected(1000, r.r)
    for (let i = 0; i < 20; i++) expect(pickNext(pool, none, [], 1, Math.random, chance)!.id).toBe('treino')
  })
  it('errar desce menos do que acertar sobe', () => {
    expect(1000 - updateElo(1000, 1000, false)).toBeLessThan(updateElo(1000, 1000, true) - 1000)
  })
})

describe('treinador', () => {
  const stats = new Map([
    ['mat-porcentagem', { n: 10, ok: 4 }], ['mat-pa', { n: 8, ok: 5 }], ['mat-pg', { n: 3, ok: 0 }], ['fis-ondas', { n: 12, ok: 11 }],
  ])
  it('ponto fraco precisa de respostas suficientes e vem do pior para o melhor', () => {
    expect(weakSpots(stats).map((w) => w.id)).toEqual(['mat-porcentagem', 'mat-pa'])
  })
  it('revisão vencendo vem antes do ponto fraco, e a meta só aparece perto do fim', () => {
    const weak = weakSpots(stats)
    expect(suggest({ due: 5, weak, today: 0, goal: 20 })).toMatchObject({ kind: 'review', count: 5 })
    expect(suggest({ due: 1, weak, today: 0, goal: 20 })).toMatchObject({ kind: 'weak' })
    expect(suggest({ due: 0, weak: [], today: 4, goal: 20 })).toBeNull()
    expect(suggest({ due: 0, weak: [], today: 17, goal: 20 })).toEqual({ kind: 'goal', left: 3 })
    expect(suggest({ due: 0, weak: [], today: 20, goal: 20 })).toBeNull()
  })
  it('meta do dia é a semanal em cinco dias', () => {
    expect(dailyGoal(100)).toBe(20)
    expect(dailyGoal(10)).toBe(5)
  })
  it('acerto depois de erro ganha o elogio da recuperação; erro nunca culpa', () => {
    const base = { ok: true, recovered: false, slow: false, combo: 1, level: 1, wrongRun: 0 }
    expect(feedbackLine({ ...base, recovered: true }, 0)).toMatch(/antes/i)
    expect(feedbackLine({ ...base, ok: false, wrongRun: 1 }, 0)).toBe('Ainda não, e tudo bem.')
    for (let seed = 0; seed < 8; seed++) expect(feedbackLine({ ...base, ok: false, wrongRun: 4 }, seed)).not.toMatch(/errado|fraco|ruim/i)
  })
  it('pausa só é sugerida com queda no fim e respostas apressadas', () => {
    const good = Array.from({ length: 12 }, () => ({ ok: true, ms: 60_000 }))
    const rushed = Array.from({ length: 6 }, (_, i) => ({ ok: i === 0, ms: 15_000 }))
    expect(needsBreak([...good, ...rushed])).toBe(true)
    expect(needsBreak([...good, ...rushed.map((r) => ({ ...r, ms: 90_000 }))])).toBe(false)
    expect(needsBreak(rushed)).toBe(false)
  })
})
