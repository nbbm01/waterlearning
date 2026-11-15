import { Rich } from '../core/rich'
import type { TheoryCard } from '../core/types'
import { bookHref, HAS_BOOKS } from './Runner'

/** Card lateral de teoria: aparece sem bloquear a questão e some com um clique. */
export function TheoryPanel({ card, onClose }: { card: TheoryCard; onClose: () => void }) {
  const ref = card.ref
  const href = ref?.file && HAS_BOOKS ? bookHref(ref.file, ref.page) : null
  return (
    <aside className="theory" aria-label="Resumo teórico">
      <header>
        <span className="eyebrow">Um reforço rápido</span>
        <button className="icon-btn" onClick={onClose} aria-label="Fechar resumo">✕</button>
      </header>
      <h2>{card.title}</h2>
      <Rich text={card.body} />
      {ref && (
        <footer>
          {href ? <a href={href} target="_blank" rel="noreferrer">Aprofundar: {ref.label} ↗</a> : <span>{ref.label}</span>}
        </footer>
      )}
    </aside>
  )
}
