import { useEffect, useRef, useState } from 'react'
import { trackName, trackRows, type Bank } from '../core/data'
import { useStore } from '../core/store'
import { ALL_TRACK } from '../core/types'

/** As trilhas e a opção "todas as provas", com quantas questões cada uma tem. */
export function trackOptions(bank: Bank) {
  return [
    ...bank.meta.tracks.map((t) => ({ ...t, count: trackRows(bank, t.id).length })),
    { id: ALL_TRACK, name: 'Todas as provas', desc: 'O banco inteiro, sem recorte', count: bank.rows.length },
  ]
}

const n = (v: number) => v.toLocaleString('pt-BR')

/**
 * O objetivo do aluno, discreto na barra da prática. Trocar é um clique e nunca tira a questão da tela:
 * quem abre o site continua caindo direto numa questão.
 */
export function TrackPicker({ bank }: { bank: Bank }) {
  const store = useStore()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const current = store.s.settings.track

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!bank.meta.tracks.length) return null
  return (
    <div className="track" ref={box}>
      <button className="track-btn" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="listbox"
        title="Seu objetivo: escolhe de quais provas vêm as questões">
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
          <circle cx="8" cy="8" r="6.2" /><circle cx="8" cy="8" r="3.2" /><circle cx="8" cy="8" r="0.6" fill="currentColor" />
        </svg>
        {trackName(bank, current)} <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul className="track-menu" role="listbox" aria-label="Objetivo">
          {trackOptions(bank).map((t) => (
            <li key={t.id} role="option" aria-selected={t.id === current}>
              <button className={t.id === current ? 'on' : ''} onClick={() => { store.setTrack(t.id); setOpen(false) }}>
                <strong>{t.name}</strong>
                <span>{t.desc}</span>
                <span className="track-count">{n(t.count)} questões</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/**
 * Na primeira visita, acima da questão: "para qual prova você estuda?". Responder é opcional;
 * a questão já está na tela e o padrão (ENEM e vestibulares) serve para a maioria.
 */
export function TrackQuestion({ bank }: { bank: Bank }) {
  const store = useStore()
  if (store.s.settings.trackChosen || !bank.meta.tracks.length) return null
  const current = store.s.settings.track
  return (
    <aside className="coach track-ask">
      <span>Para qual prova você está estudando? <span className="muted">Dá para trocar depois, no topo da página.</span></span>
      <div className="chips">
        {bank.meta.tracks.map((t) => (
          <button key={t.id} className={`chip ${t.id === current ? 'on' : ''}`} title={t.desc} onClick={() => store.setTrack(t.id)}>{t.name}</button>
        ))}
      </div>
      <button className="icon-btn coach-close" onClick={() => store.setSettings({ trackChosen: true })} aria-label="Manter ENEM e vestibulares">✕</button>
    </aside>
  )
}
