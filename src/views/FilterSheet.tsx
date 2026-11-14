import { useEffect, useMemo, useState } from 'react'
import type { Bank } from '../core/data'
import { select } from '../core/filters'
import { fold } from '../core/search'
import { store } from '../core/store'
import { EMPTY_FILTER, type Difficulty, type Filter } from '../core/types'

const DIFFS: [Difficulty, string, string][] = [
  ['prog', 'Progressivo', 'Começa no fácil e sobe conforme você acerta'],
  [1, 'Fácil', ''], [2, 'Médio', ''], [3, 'Difícil', ''], [0, 'Todas', 'Qualquer nível, em ordem aleatória'],
]

const toggle = (list: number[], i: number) => (list.includes(i) ? list.filter((x) => x !== i) : [...list, i])

interface Props {
  bank: Bank
  initial: Filter
  onApply: (f: Filter) => void
  onClose: () => void
}

export function FilterSheet({ bank, initial, onApply, onClose }: Props) {
  const [f, setF] = useState<Filter>({ ...initial, subs: initial.subs ?? [] })
  const [topicQuery, setTopicQuery] = useState('')
  const count = useMemo(() => select(bank.rows, f, store).length, [bank, f])
  // quantas questões cada subtópico tem com os demais filtros aplicados
  const subCounts = useMemo(() => {
    const out: Record<number, number> = {}
    for (const r of select(bank.rows, { ...f, subs: [], topics: [] }, store)) if (r.u >= 0) out[r.u] = (out[r.u] ?? 0) + 1
    return out
  }, [bank, f])
  const years = useMemo(() => [...new Set(bank.rows.map((r) => r.y).filter(Boolean))].sort((a, b) => b - a), [bank])
  const patch = (p: Partial<Filter>) => setF((cur) => ({ ...cur, ...p }))

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'Enter' && !(e.target as HTMLElement).closest('button, select')) {
        e.preventDefault()
        if (count) onApply(f)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [count, f, onApply, onClose])

  const tq = fold(topicQuery)
  const matchesQuery = (name: string, aliases: string[]) => !tq || fold(name).includes(tq) || aliases.some((x) => fold(x).includes(tq))
  const topicGroups = bank.meta.subjects
    .map((s, si) => ({
      subject: s,
      topics: bank.topics
        .map((t, ti) => {
          const def = s.topics.find((x) => x.id === t.id)
          const subs = bank.subs.map((sb, ui) => ({ ...sb, ui })).filter((sb) => sb.topic === ti)
          const subHits = subs.filter((sb) => tq && matchesQuery(sb.name, def?.subs.find((x) => x.id === sb.id)?.aliases ?? []))
          return { ...t, ti, subs, show: !tq || (def && matchesQuery(t.name, def.aliases)) || subHits.length > 0, subHits }
        })
        .filter((t) => t.subject === si && t.show),
    }))
    .filter((g, si) => (!f.subjects.length || f.subjects.includes(si)) && g.topics.length)

  const toggleTopic = (ti: number) => {
    const on = f.topics.includes(ti)
    // desmarcar o tópico também desmarca os subtópicos dele
    patch({ topics: toggle(f.topics, ti), subs: on ? f.subs.filter((u) => bank.subs[u].topic !== ti) : f.subs })
  }

  const specials: [keyof Filter, string, string][] = [
    ['pending', 'Revisões pendentes', `${store.dueCards().length} para hoje`],
    ['unseen', 'Questões inéditas', 'Só o que você ainda não fez'],
    ['classic', 'Clássicas', 'Tópicos mais cobrados de cada banca'],
    ['military', 'Apenas militares', bank.meta.military.join(', ') || 'ITA, IME, AFA, EFOMM, EsPCEx'],
    ['commented', 'Com resolução comentada', 'Explicação passo a passo'],
  ]

  return (
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Filtros">
        <header className="sheet-head">
          <h2>Filtros</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar filtros">✕</button>
        </header>

        <div className="sheet-body">
          <section>
            <h3>Matéria</h3>
            <div className="chips">
              {bank.meta.subjects.map((s, i) => (
                <button key={s.id} className={`chip ${f.subjects.includes(i) ? 'on' : ''}`}
                  onClick={() => patch({ subjects: toggle(f.subjects, i), topics: [], subs: [] })}>{s.name}</button>
              ))}
            </div>
          </section>

          <section>
            <h3>Vestibular</h3>
            <div className="chips">
              {bank.meta.exams.map((e, i) => (
                <button key={e} className={`chip ${f.exams.includes(i) ? 'on' : ''}`}
                  onClick={() => patch({ exams: toggle(f.exams, i) })}>{e}</button>
              ))}
            </div>
          </section>

          <section>
            <h3>Dificuldade</h3>
            <div className="segmented">
              {DIFFS.map(([d, label, title]) => (
                <button key={label} title={title} className={f.diff === d ? 'on' : ''} onClick={() => patch({ diff: d })}>{label}</button>
              ))}
            </div>
          </section>

          <section>
            <h3>
              Tópico
              <input className="mini-input" placeholder="ex.: equação do 1º grau" value={topicQuery}
                onChange={(e) => setTopicQuery(e.target.value)} aria-label="Filtrar lista de tópicos" />
            </h3>
            {topicGroups.map((g) => (
              <div key={g.subject.id} className="topic-group">
                <span className="group-label">{g.subject.name}</span>
                <div className="chips">
                  {g.topics.map((t) => (
                    <button key={t.id} className={`chip ${f.topics.includes(t.ti) ? 'on' : ''}`}
                      onClick={() => toggleTopic(t.ti)}>{t.name}</button>
                  ))}
                </div>
                {g.topics.filter((t) => (f.topics.includes(t.ti) || t.subHits.length) && t.subs.length).map((t) => (
                  <div key={t.id} className="sub-row">
                    <span className="sub-label">{t.name} ›</span>
                    <div className="chips">
                      {(t.subHits.length && !f.topics.includes(t.ti) ? t.subHits : t.subs).map((sb) => (
                        <button key={sb.id} className={`chip small ${f.subs.includes(sb.ui) ? 'on' : ''}`}
                          onClick={() => patch({ subs: toggle(f.subs, sb.ui) })}>
                          {sb.name} <span className="chip-count">{subCounts[sb.ui] ?? 0}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
            {!topicGroups.length && <p className="muted">Nenhum tópico com esse nome.</p>}
          </section>

          <section>
            <h3>Ano</h3>
            <div className="year-range">
              <label>de
                <select value={f.yearMin} onChange={(e) => patch({ yearMin: Number(e.target.value) })}>
                  <option value={0}>qualquer</option>
                  {years.map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
              </label>
              <label>até
                <select value={f.yearMax} onChange={(e) => patch({ yearMax: Number(e.target.value) })}>
                  <option value={0}>qualquer</option>
                  {years.map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
              </label>
            </div>
          </section>

          <section>
            <h3>Atalhos</h3>
            <div className="specials">
              {specials.map(([key, label, hint]) => (
                <button key={key} className={`special ${f[key] ? 'on' : ''}`} aria-pressed={!!f[key]}
                  onClick={() => patch({ [key]: !f[key] } as Partial<Filter>)}>
                  <strong>{label}</strong>
                  <span>{hint}</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <footer className="sheet-foot">
          <span className="count" aria-live="polite">
            <b>{count.toLocaleString('pt-BR')}</b> {count === 1 ? 'questão encontrada' : 'questões encontradas'}
          </span>
          <button className="btn ghost" onClick={() => setF(EMPTY_FILTER)}>Limpar</button>
          <button className="btn primary" disabled={!count} onClick={() => onApply(f)}>Praticar <kbd>Enter</kbd></button>
        </footer>
      </div>
    </div>
  )
}
