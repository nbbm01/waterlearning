import { useCallback, useRef } from 'react'
import type { Bank } from '../core/data'
import { useStore } from '../core/store'
import { dayNumber } from '../core/time'
import type { View } from './TopBar'
import { Runner } from './Runner'

/** Revisão do Dia: tudo que o aluno errou volta sozinho, no intervalo certo. */
export function Review({ bank, go }: { bank: Bank; go: (v: View) => void }) {
  const store = useStore()
  const today = dayNumber()
  const total = useRef(store.dueCards(today).length)
  const remaining = store.dueCards(today).length
  total.current = Math.max(total.current, remaining)
  const shown = useRef(0)

  const next = useCallback((recent: readonly string[]) => {
    const due = store.dueCards(dayNumber())
    const card = due.find((c) => !recent.includes(c.qid)) ?? due[0]
    return card ? bank.byId.get(card.qid) ?? null : null
  }, [bank, store])

  const all = [...store.cards.values()]
  const tomorrow = all.filter((c) => c.due === today + 1).length
  const week = all.filter((c) => c.due > today && c.due <= today + 7).length

  return (
    <main className="practice">
      <div className="practice-bar">
        <span className="level">Revisão do Dia · <b>{remaining}</b> {remaining === 1 ? 'questão pendente' : 'questões pendentes'}</span>
      </div>
      <Runner
        bank={bank} mode="review" poolKey="review" next={next}
        onShow={(r) => { if (r) shown.current++ }}
        progress={() => `Revisão ${Math.min(shown.current, total.current)} de ${total.current}`}
        empty={
          <div className="empty">
            <div className="big-emoji" aria-hidden="true">💧</div>
            <h2>{total.current ? 'Revisão de hoje concluída' : 'Nada para revisar hoje'}</h2>
            <p className="muted">
              {all.length
                ? `Sua fila tem ${all.length} ${all.length === 1 ? 'questão' : 'questões'}: ${tomorrow} para amanhã, ${week} nos próximos 7 dias.`
                : 'As questões que você errar ou marcar para rever aparecem aqui sozinhas, depois de alguns dias.'}
            </p>
            <div className="actions center">
              <button className="btn primary" onClick={() => go('practice')}>Continuar estudando</button>
            </div>
          </div>
        }
      />
    </main>
  )
}
