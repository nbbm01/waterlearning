import { useCallback, useEffect, useState } from 'react'
import { loadBank, type Bank } from './core/data'
import { pomodoro } from './core/pomodoro'
import { store, useStore } from './core/store'
import { useToasts } from './core/toast'
import { Details } from './views/Details'
import { FilterSheet } from './views/FilterSheet'
import { Practice } from './views/Practice'
import { Review } from './views/Review'
import { Simulado } from './views/Simulado'
import { TopBar, type View } from './views/TopBar'

export function App() {
  const st = useStore()
  const toasts = useToasts()
  const [bank, setBank] = useState<Bank | null>(null)
  const [error, setError] = useState('')
  const [view, setView] = useState<View>('practice')
  const [filters, setFilters] = useState(false)
  const [focusMode, setFocusMode] = useState(false)

  useEffect(() => {
    loadBank()
      .then(async (b) => {
        await store.load(b)
        pomodoro.configure(store.s.settings.pomoFocus, store.s.settings.pomoBreak)
        setBank(b)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Erro ao carregar as questões.'))
  }, [])

  const go = useCallback((v: View) => {
    setView(v)
    window.scrollTo({ top: 0 })
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || focusMode || filters) return
      if ((e.target as HTMLElement).closest('input, textarea, select')) return
      if (e.key.toLowerCase() === 'f') {
        e.preventDefault()
        setFilters(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [filters, focusMode])

  if (error) {
    return (
      <div className="empty">
        <h2>Não foi possível abrir o banco de questões</h2>
        <p className="muted">{error} Rode <code>bun run data</code> para gerar os dados e recarregue a página.</p>
      </div>
    )
  }
  if (!bank || !st.ready) return <div className="boot"><div className="question skeleton" aria-busy="true" /></div>

  return (
    <>
      {!focusMode && <TopBar bank={bank} view={view} go={go} onOpenFilters={() => setFilters(true)} />}
      {view === 'practice' && <Practice bank={bank} onOpenFilters={() => setFilters(true)} go={go} />}
      {view === 'review' && <Review bank={bank} go={go} />}
      {view === 'sim' && <Simulado bank={bank} onFocusMode={setFocusMode} />}
      {view === 'details' && <Details bank={bank} go={go} />}
      {filters && (
        <FilterSheet bank={bank} initial={st.s.filter} onClose={() => setFilters(false)}
          onApply={(f) => { store.setFilter(f); setFilters(false); go('practice') }} />
      )}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast">{t.icon && <span aria-hidden="true">{t.icon}</span>}{t.text}</div>
        ))}
      </div>
    </>
  )
}
