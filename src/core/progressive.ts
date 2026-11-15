/**
 * Modo Progressivo por domínio (mastery learning): começa na fixação e só sobe quando o degrau
 * está firme, como numa lista de exercícios de livro. Um chute de sorte não basta para subir
 * e um erro isolado não derruba ninguém.
 */
export interface Prog {
  level: 1 | 2 | 3
  hist: boolean[] // resultados recentes no degrau atual, o mais novo por último
}

export const START_PROG: Prog = { level: 1, hist: [] }
/** domínio: 7 acertos nas últimas 8 do degrau (~87%) */
export const MASTERY = { window: 8, need: 7 }
/** dificuldade persistente: 3 erros nas últimas 4 voltam um degrau */
export const SLIP = { window: 4, wrong: 3 }

export function masteredCount(p: Prog): number {
  return (p.hist ?? []).filter(Boolean).length
}

export function stepProg(p: Prog, correct: boolean): { prog: Prog; changed: -1 | 0 | 1 } {
  // estado salvo antes desta versão não tem hist
  const hist = [...(p.hist ?? []), correct].slice(-MASTERY.window)
  if (p.level < 3 && hist.length >= MASTERY.window && hist.filter(Boolean).length >= MASTERY.need) {
    return { prog: { level: (p.level + 1) as Prog['level'], hist: [] }, changed: 1 }
  }
  const recent = hist.slice(-SLIP.window)
  if (p.level > 1 && recent.length >= SLIP.window && recent.filter((ok) => !ok).length >= SLIP.wrong) {
    return { prog: { level: (p.level - 1) as Prog['level'], hist: [] }, changed: -1 }
  }
  return { prog: { level: p.level, hist }, changed: 0 }
}
