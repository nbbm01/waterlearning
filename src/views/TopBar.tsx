import { useEffect, useMemo, useRef, useState } from 'react'
import type { Bank } from '../core/data'
import { isEmptyFilter } from '../core/filters'
import { searchAll, type Hit } from '../core/search'
import { useStore } from '../core/store'
import { visibleStreak } from '../core/streak'
import { dayNumber } from '../core/time'
import { EMPTY_FILTER } from '../core/types'

export type View = 'practice' | 'review' | 'sim' | 'details'

interface Props {
  bank: Bank
  view: View
  go: (v: View) => void
  onOpenFilters: () => void
}

function Search({ bank, onPick }: { bank: Bank; onPick: (h: Hit) => void }) {
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const [open, setOpen] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const hits = useMemo(() => searchAll(bank.meta, bank.rows, q), [bank, q])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && !(e.target as HTMLElement).closest('input, textarea')) {
        e.preventDefault()
        input.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const pick = (h: Hit | undefined) => {
    if (!h) return
    onPick(h)
    setQ('')
    setOpen(false)
    input.current?.blur()
  }

  return (
    <div className="search">
      <input
        ref={input} type="search" value={q} placeholder="Buscar tópico: logaritmo, cinemática, Era Vargas…"
        aria-label="Buscar tópico, matéria ou vestibular" role="combobox" aria-expanded={open && hits.length > 0} aria-controls="search-hits"
        onChange={(e) => { setQ(e.target.value); setActive(0); setOpen(true) }}
        onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, hits.length - 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
          else if (e.key === 'Enter') { e.preventDefault(); pick(hits[active]) }
          else if (e.key === 'Escape') { setQ(''); input.current?.blur() }
        }}
      />
      <kbd className="search-key">/</kbd>
      {open && q.trim() && (
        <ul className="search-hits" id="search-hits" role="listbox">
          {hits.map((h, i) => (
            <li key={`${h.kind}-${h.index}`} role="option" aria-selected={i === active}
              className={i === active ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); pick(h) }} onMouseEnter={() => setActive(i)}>
              <span>{h.label}</span>
              <span className="muted">{h.hint} · {h.count.toLocaleString('pt-BR')} {h.count === 1 ? 'questão' : 'questões'}</span>
            </li>
          ))}
          {!hits.length && <li className="none">Nada encontrado. Tente outro nome para o tópico.</li>}
        </ul>
      )}
    </div>
  )
}

export function TopBar({ bank, view, go, onOpenFilters }: Props) {
  const store = useStore()
  const today = dayNumber()
  const streak = visibleStreak(store.s.streak, today)
  const week = store.weekCount(today)
  const goal = store.s.settings.weeklyGoal
  const due = store.dueCards(today).length
  const { sound, theme } = store.s.settings
  const filtered = !isEmptyFilter(store.s.filter)

  const pickHit = (h: Hit) => {
    const f = { ...EMPTY_FILTER }
    if (h.kind === 'topic') f.topics = [h.index]
    else if (h.kind === 'sub') f.subs = [h.index]
    else if (h.kind === 'exam') f.exams = [h.index]
    else f.subjects = [h.index]
    store.setFilter(f)
    go('practice')
  }

  return (
    <header className="topbar">
      <div className="topbar-main">
        <button className="brand" onClick={() => go('practice')} aria-label="Waterlearning: ir para a prática">
          <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true"><path d="M16 3c5 7 9 11 9 16a9 9 0 0 1-18 0c0-5 4-9 9-16z" fill="currentColor" /></svg>
          <span>Waterlearning</span>
        </button>
        <Search bank={bank} onPick={pickHit} />
        <button className={`btn ghost filters-btn ${filtered ? 'on' : ''}`} onClick={onOpenFilters} title="Filtros (F)">
          Filtros{filtered && <i className="dot" aria-label="filtros ativos" />}
        </button>
        <nav className="tabs" aria-label="Seções">
          <button className={view === 'practice' ? 'on' : ''} onClick={() => go('practice')}>Praticar</button>
          <button className={view === 'review' ? 'on' : ''} onClick={() => go('review')}>
            Revisão{due > 0 && <span className="badge">{due}</span>}
          </button>
          <button className={view === 'sim' ? 'on' : ''} onClick={() => go('sim')}>Simulado</button>
        </nav>
        <div className="toggles">
          <button className="icon-btn" onClick={() => store.setSettings({ sound: !sound })}
            aria-label={sound ? 'Silenciar sons' : 'Ativar sons'} title={sound ? 'Silenciar sons' : 'Ativar sons'}>{sound ? '🔔' : '🔕'}</button>
          <button className="icon-btn" onClick={() => store.setSettings({ theme: theme === 'dark' ? 'light' : 'dark' })}
            aria-label={theme === 'dark' ? 'Usar tema claro' : 'Usar tema escuro'} title="Alternar tema">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              {theme === 'dark'
                ? <><circle cx="12" cy="12" r="4.5" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>
                : <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />}
            </svg>
          </button>
        </div>
      </div>

      <div className="dash">
        <span className={`streak ${streak.count ? '' : 'idle'} ${streak.atRisk ? 'pending' : ''}`}
          title={streak.atRisk ? 'Responda uma questão hoje para continuar a sequência' : 'Dias seguidos de estudo'}>
          🔥 <b className="tabular">{streak.count}</b> {streak.count === 1 ? 'dia' : 'dias'}
          {streak.shieldsLeft > 0 && <span className="shields" title="Escudos: cada um cobre um dia de folga">{'🛡️'.repeat(streak.shieldsLeft)}</span>}
        </span>
        <span className="week" title="Questões respondidas nesta semana">
          <span className="meter" role="progressbar" aria-valuemin={0} aria-valuemax={goal} aria-valuenow={Math.min(week, goal)}>
            <i style={{ width: `${Math.min(100, (week / goal) * 100)}%` }} />
          </span>
          <b className="tabular">{week}/{goal}</b> questões na semana
        </span>
        {view !== 'practice' && <button className="btn primary small" onClick={() => go('practice')}>Continuar estudando</button>}
        <button className="link details-link" onClick={() => go(view === 'details' ? 'practice' : 'details')}>
          {view === 'details' ? 'Voltar à prática' : 'Ver detalhes'}
        </button>
      </div>
    </header>
  )
}
