/**
 * O "treinador" do site: decide o que sugerir e como falar com o aluno. Tudo aqui é função pura.
 * As regras vêm da pesquisa em aprendizagem e psicologia positiva:
 * - elogio ao processo, não ao talento (mentalidade de crescimento, Dweck);
 * - erro tratado com gentileza e como informação (autocompaixão, Neff);
 * - meta pequena e visível por dia (efeito do gradiente de meta);
 * - mostrar o que já foi conquistado (saborear o progresso, Seligman);
 * - o aluno escolhe: toda sugestão é um convite, nunca uma trava (autodeterminação, Deci e Ryan).
 */

export interface SkillStat {
  n: number
  ok: number
}

export interface WeakSpot {
  id: string
  n: number
  pct: number
}

/** mínimo de respostas para um assunto contar como ponto a fortalecer: menos que isso é ruído */
export const WEAK_MIN = 6
const WEAK_BELOW = 65

/** Assuntos com aproveitamento baixo, do mais fraco para o menos fraco. */
export function weakSpots(stats: ReadonlyMap<string, SkillStat>, limit = 3): WeakSpot[] {
  const out: WeakSpot[] = []
  for (const [id, v] of stats) {
    const pct = Math.round((v.ok / v.n) * 100)
    if (v.n >= WEAK_MIN && pct < WEAK_BELOW) out.push({ id, n: v.n, pct })
  }
  return out.sort((a, b) => a.pct - b.pct || b.n - a.n).slice(0, limit)
}

/** Assuntos em que o aluno já vai bem: servem para lembrar o que deu certo. */
export function strongSpots(stats: ReadonlyMap<string, SkillStat>, limit = 3): WeakSpot[] {
  const out: WeakSpot[] = []
  for (const [id, v] of stats) {
    const pct = Math.round((v.ok / v.n) * 100)
    if (v.n >= WEAK_MIN && pct >= 80) out.push({ id, n: v.n, pct })
  }
  return out.sort((a, b) => b.pct - a.pct || b.n - a.n).slice(0, limit)
}

/** meta do dia: a semanal dividida em cinco dias de estudo (sobram dois de folga) */
export function dailyGoal(weeklyGoal: number): number {
  return Math.max(5, Math.ceil(weeklyGoal / 5))
}

export type Suggestion =
  | { kind: 'review'; count: number; minutes: number }
  | { kind: 'weak'; spot: WeakSpot }
  | { kind: 'goal'; left: number }

/** Uma sugestão por vez, na ordem do que mais ajuda: revisar o que está vencendo, depois o ponto fraco, depois a meta. */
export function suggest(p: { due: number; weak: WeakSpot[]; today: number; goal: number }): Suggestion | null {
  if (p.due >= 3) return { kind: 'review', count: p.due, minutes: Math.max(1, Math.round(p.due * 1.2)) }
  if (p.weak.length) return { kind: 'weak', spot: p.weak[0] }
  const left = p.goal - p.today
  // perto do fim a meta puxa mais: só aparece quando falta pouco
  if (p.today > 0 && left > 0 && left <= Math.ceil(p.goal / 4)) return { kind: 'goal', left }
  return null
}

export interface AnswerContext {
  ok: boolean
  /** já tinha errado esta questão e agora acertou */
  recovered: boolean
  /** demorou bastante e acertou */
  slow: boolean
  combo: number
  /** nível da questão (1 a 3) */
  level: number
  /** erros seguidos no assunto, contando este */
  wrongRun: number
}

const EFFORT = ['Isso!', 'Boa!', 'Certinho.', 'Mandou bem.', 'Exato.']
const HARD_WIN = ['Essa era difícil, e você resolveu.', 'Questão exigente, raciocínio firme.', 'Desafio vencido.']
const SLOW_WIN = ['Você insistiu até fechar. É isso que constrói.', 'Sem pressa e certo: persistência conta.']
const RECOVERED = ['Você errou esta antes e agora acertou. O estudo funcionou.', 'Antes não saía, agora saiu. Isso é aprender.']
const COMFORT = ['Ainda não, e tudo bem.', 'Quase lá.', 'Faz parte do treino.', 'Essa é das que ensinam.']
const COMFORT_RUN = ['Esse assunto está pedindo calma. Um erro de cada vez.', 'Errar em sequência é sinal de assunto novo, não de limite.']

/** Frase curta depois da resposta. `seed` escolhe a variação de forma estável por questão. */
export function feedbackLine(c: AnswerContext, seed: number): string {
  const pick = (list: readonly string[]) => list[seed % list.length]
  if (!c.ok) return pick(c.wrongRun >= 3 ? COMFORT_RUN : COMFORT)
  if (c.recovered) return pick(RECOVERED)
  if (c.slow) return pick(SLOW_WIN)
  if (c.level >= 3) return pick(HARD_WIN)
  return pick(EFFORT)
}

/**
 * Cansaço: muitas respostas, queda forte no fim e respostas cada vez mais rápidas (chute).
 * Sugere pausa só nesse caso; pausa sugerida à toa vira ruído.
 */
export function needsBreak(results: readonly { ok: boolean; ms: number }[]): boolean {
  if (results.length < 16) return false
  const last = results.slice(-6)
  const before = results.slice(0, -6)
  const rate = (r: readonly { ok: boolean }[]) => r.filter((x) => x.ok).length / r.length
  const avg = (r: readonly { ms: number }[]) => r.reduce((s, x) => s + x.ms, 0) / r.length
  return rate(last) <= 0.34 && rate(before) >= 0.6 && avg(last) < avg(before) * 0.75
}

/** Saudação do topo: curta e ligada ao que o aluno já fez. */
export function greeting(hour: number, p: { today: number; goal: number; streak: number }): string {
  if (p.today >= p.goal) return 'Meta de hoje cumprida. O que vier agora é bônus.'
  if (p.today > 0) return `Faltam ${p.goal - p.today} para a meta de hoje.`
  const hello = hour < 5 ? 'Boa madrugada' : hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'
  if (p.streak >= 2) return `${hello}. ${p.streak} dias seguidos: uma questão já mantém a sequência.`
  return `${hello}. Comece por uma questão, o resto vem.`
}
