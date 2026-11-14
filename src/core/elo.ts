export const START_ELO = 1000
const K = 28

export function expected(player: number, question: number): number {
  return 1 / (1 + 10 ** ((question - player) / 400))
}

/** Novo Elo do aluno: acertar questão difícil sobe muito, errar fácil desce mais. */
export function updateElo(player: number, question: number, correct: boolean): number {
  const next = player + K * ((correct ? 1 : 0) - expected(player, question))
  return Math.max(100, Math.round(next))
}

const TIERS: [number, string][] = [
  [0, 'Nascente'], [900, 'Riacho'], [1100, 'Rio'], [1300, 'Correnteza'], [1500, 'Cachoeira'], [1700, 'Oceano'],
]

export function tier(elo: number): string {
  let name = TIERS[0][1]
  for (const [min, label] of TIERS) if (elo >= min) name = label
  return name
}
