/** Revisão espaçada no estilo SM-2, sem nada para o aluno configurar. */
export interface Card {
  qid: string
  due: number // dia em que volta
  ivl: number // intervalo atual, em dias
  ease: number
  reps: number // acertos seguidos em revisão
  lapses: number
}

// o erro já agenda a primeira volta para amanhã; depois disso: 3, 7 e 16 dias
const FIRST_INTERVALS = [3, 7, 16]
const MIN_EASE = 1.3
/** Depois de um intervalo deste tamanho a questão é considerada aprendida e sai da fila. */
export const GRADUATE_AFTER = 90

export type Outcome = 'wrong' | 'hard' | 'ok'

/**
 * Atualiza (ou cria) o cartão de uma questão. Devolve null quando não há o que revisar:
 * acerto tranquilo sem cartão, ou cartão que já amadureceu.
 */
export function schedule(card: Card | undefined, qid: string, outcome: Outcome, today: number): Card | null {
  if (!card) {
    if (outcome === 'ok') return null
    const ivl = outcome === 'wrong' ? 1 : 3
    return { qid, due: today + ivl, ivl, ease: 2.3, reps: 0, lapses: outcome === 'wrong' ? 1 : 0 }
  }
  if (outcome === 'wrong') {
    return { ...card, due: today + 1, ivl: 1, ease: Math.max(MIN_EASE, card.ease - 0.2), reps: 0, lapses: card.lapses + 1 }
  }
  // acerto antes da hora (prática livre) não adianta a agenda
  if (today < card.due) return card
  const reps = card.reps + 1
  const ease = outcome === 'hard' ? Math.max(MIN_EASE, card.ease - 0.1) : card.ease + 0.05
  const grown = reps <= FIRST_INTERVALS.length ? FIRST_INTERVALS[reps - 1] : Math.round(card.ivl * ease)
  const ivl = outcome === 'hard' ? Math.max(2, Math.round(grown * 0.6)) : Math.max(grown, card.ivl + 1)
  if (ivl > GRADUATE_AFTER) return null
  return { ...card, due: today + ivl, ivl, ease, reps }
}

export function isDue(card: Card, today: number): boolean {
  return card.due <= today
}
