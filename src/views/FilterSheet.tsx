import { useEffect, useMemo, useState } from 'react'
import { countBy, skillKey, trackName, trackRows, type Bank } from '../core/data'
import { select } from '../core/filters'
import { fold } from '../core/search'
import { store } from '../core/store'
import { EMPTY_FILTER, type Difficulty, type Filter, type Row } from '../core/types'
import { DEEP_UNLOCK } from '../core/elo'

const DIFFS: [Difficulty, string, string][] = [
  ['prog', 'Progressivo', 'Começa no fácil e sobe conforme você acerta'],
  [1, 'Fácil', ''], [2, 'Médio', ''], [3, 'Difícil', ''], [0, 'Todas', 'Qualquer nível, em ordem aleatória'],
]

const toggle = (list: number[], i: number) => (list.includes(i) ? list.filter((x) => x !== i) : [...list, i])
const n = (v: number) => v.toLocaleString('pt-BR')
// grupo com até tantas bancas fica sempre aberto; nos maiores, a lista abre com um clique e mostra as mais frequentes
const SMALL_GROUP = 8
const FIRST_EXAMS = 30

/** Bancas por grupo (ENEM, Vestibulares, Militares...), só as que a trilha tem, das mais frequentes às raras. */
export function ExamGroups({ bank, rows, selected, onChange }: {
  bank: Bank; rows: Row[]; selected: number[]; onChange: (exams: number[]) => void
}) {
  const counts = useMemo(() => countBy(rows, 'e'), [rows])
  const [open, setOpen] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [all, setAll] = useState(false)
  const groups = bank.meta.groups.length ? bank.meta.groups : [{ id: 'all', name: 'Provas', exams: bank.meta.exams.map((_, i) => i) }]
  const q = fold(query)
  return (
    <>
      {groups.map((g) => {
        const exams = g.exams.filter((i) => counts.get(i)).sort((a, b) => counts.get(b)! - counts.get(a)!)
        if (!exams.length) return null
        const total = exams.reduce((s, i) => s + counts.get(i)!, 0)
        const chosen = exams.filter((i) => selected.includes(i))
        const small = exams.length <= SMALL_GROUP
        const isOpen = small || open === g.id
        const shown = small ? exams : exams.filter((i) => !q || fold(bank.meta.exams[i]).includes(q))
        const everything = chosen.length === exams.length
        return (
          <div key={g.id} className={`exam-group ${isOpen ? 'open' : ''}`}>
            {small ? <span className="group-label">{g.name}</span> : (
              <button className="group-head" aria-expanded={isOpen} onClick={() => { setOpen(isOpen ? null : g.id); setQuery(''); setAll(false) }}>
                <span className="caret" aria-hidden="true">▶</span>
                {g.name} <span className="chip-count">{exams.length} provas · {n(total)} questões{chosen.length ? ` · ${chosen.length} marcadas` : ''}</span>
              </button>
            )}
            {isOpen && (
              <>
                {!small && exams.length > FIRST_EXAMS && (
                  <input className="mini-input" placeholder={`buscar entre as ${exams.length} provas`} value={query} autoFocus
                    onChange={(e) => setQuery(e.target.value)} aria-label={`Buscar prova em ${g.name}`} style={{ marginBottom: 6 }} />
                )}
                <div className="chips">
                  {!small && (
                    <button className={`chip small ${everything ? 'on' : ''}`}
                      onClick={() => onChange(everything ? selected.filter((i) => !exams.includes(i)) : [...new Set([...selected, ...exams])])}>
                      {everything ? 'Desmarcar todas' : 'Todas'}
                    </button>
                  )}
                  {(all || q ? shown : shown.slice(0, FIRST_EXAMS)).map((i) => (
                    <button key={i} className={`chip small ${selected.includes(i) ? 'on' : ''}`} title={bank.meta.examInfo[bank.meta.exams[i]]}
                      onClick={() => onChange(toggle(selected, i))}>
                      {bank.meta.exams[i]} <span className="chip-count">{n(counts.get(i)!)}</span>
                    </button>
                  ))}
                  {!all && !q && shown.length > FIRST_EXAMS && (
                    <button className="link" onClick={() => setAll(true)}>mais {shown.length - FIRST_EXAMS}</button>
                  )}
                </div>
              </>
            )}
          </div>
        )
      })}
    </>
  )
}

interface Props {
  bank: Bank
  initial: Filter
  onApply: (f: Filter) => void
  onClose: () => void
}

export function FilterSheet({ bank, initial, onApply, onClose }: Props) {
  const [f, setF] = useState<Filter>({ ...initial, subs: initial.subs ?? [] })
  const [topicQuery, setTopicQuery] = useState('')
  const unlocked = (r: Row) => store.elo(skillKey(bank, r)) >= DEEP_UNLOCK
  // tudo aqui é dentro da trilha (objetivo) do aluno
  const track = store.s.settings.track
  const rows = trackRows(bank, track)
  const count = useMemo(() => select(rows, f, store, unlocked).length, [rows, f])
  const subjectCounts = useMemo(() => countBy(rows, 's'), [rows])
  // quantas questões cada tópico e subtópico têm com os demais filtros aplicados
  const [topicCounts, subCounts] = useMemo(() => {
    const topics: Record<number, number> = {}
    const subs: Record<number, number> = {}
    for (const r of select(rows, { ...f, subs: [], topics: [] }, store, unlocked)) {
      topics[r.t] = (topics[r.t] ?? 0) + 1
      if (r.u >= 0) subs[r.u] = (subs[r.u] ?? 0) + 1
    }
    return [topics, subs]
  }, [rows, f])
  const years = useMemo(() => [...new Set(rows.map((r) => r.y).filter(Boolean))].sort((a, b) => b - a), [rows])
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
        // tópico sem questão na trilha (ou nos demais filtros) só atrapalha a escolha
        .filter((t) => t.subject === si && t.show && (topicCounts[t.ti] || f.topics.includes(t.ti))),
    }))
    .filter((g, si) => (!f.subjects.length || f.subjects.includes(si)) && subjectCounts.get(si) && g.topics.length)

  const toggleTopic = (ti: number) => {
    const on = f.topics.includes(ti)
    // desmarcar o tópico também desmarca os subtópicos dele
    patch({ topics: toggle(f.topics, ti), subs: on ? f.subs.filter((u) => bank.subs[u].topic !== ti) : f.subs })
  }

  const specials: [keyof Filter, string, string][] = [
    ['pending', 'Revisões pendentes', `${store.dueCards().length} para hoje`],
    ['unseen', 'Questões inéditas', 'Só o que você ainda não fez'],
    ['classic', 'Clássicas', 'Tópicos mais cobrados de cada banca'],
    ['military', 'Apenas militares', 'EsPCEx, ESA, EEAR, AFA, EFOMM, ITA, IME, Colégio Naval e outras'],
    ['commented', 'Com resolução comentada', 'Explicação passo a passo'],
    ['deep', 'Aprofundamento', 'ITA, IME e olimpíada (liberadas sozinhas quando seu Elo chega lá)'],
  ]

  return (
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Filtros">
        <header className="sheet-head">
          <h2>Filtros</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar filtros">✕</button>
        </header>

        <div className="sheet-body">
          <p className="muted sheet-track">
            Dentro de <b>{trackName(bank, track)}</b> ({n(rows.length)} questões). O objetivo se troca na barra da prática.
          </p>

          <section>
            <h3>Matéria</h3>
            <div className="chips">
              {bank.meta.subjects.map((s, i) => subjectCounts.get(i) ? (
                <button key={s.id} className={`chip ${f.subjects.includes(i) ? 'on' : ''}`}
                  onClick={() => patch({ subjects: toggle(f.subjects, i), topics: [], subs: [] })}>
                  {s.name} <span className="chip-count">{n(subjectCounts.get(i)!)}</span>
                </button>
              ) : null)}
            </div>
          </section>

          <section>
            <h3>Prova</h3>
            <ExamGroups bank={bank} rows={rows} selected={f.exams} onChange={(exams) => patch({ exams })} />
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
