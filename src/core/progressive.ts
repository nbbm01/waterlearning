/** Modo Progressivo: começa no fácil e sobe conforme o aluno acerta. */
export interface Prog {
  level: 1 | 2 | 3
  run: number // positivo = acertos seguidos, negativo = erros seguidos
}

export const START_PROG: Prog = { level: 1, run: 0 }
export const UP_AFTER = 3
export const DOWN_AFTER = 2

export function stepProg(p: Prog, correct: boolean): { prog: Prog; changed: -1 | 0 | 1 } {
  const run = correct ? Math.max(p.run, 0) + 1 : Math.min(p.run, 0) - 1
  if (run >= UP_AFTER && p.level < 3) return { prog: { level: (p.level + 1) as Prog['level'], run: 0 }, changed: 1 }
  if (run <= -DOWN_AFTER && p.level > 1) return { prog: { level: (p.level - 1) as Prog['level'], run: 0 }, changed: -1 }
  return { prog: { level: p.level, run }, changed: 0 }
}
