import { useCallback, useMemo, useState } from 'react'
import type { Bank } from '../core/data'
import { tier } from '../core/elo'
import { isEmptyFilter, pickNext, select } from '../core/filters'
import { pomodoro, usePomodoro } from '../core/pomodoro'
import { useStore } from '../core/store'
import { formatClock } from '../core/time'
import { DIFF_LABEL, EMPTY_FILTER, type Filter } from '../core/types'
import { Runner } from './Runner'

function FilterSummary({ bank, filter, count, onClear, onOpen }: {
  bank: Bank; filter: Filter; count: number; onClear: () => void; onOpen: () => void
}) {
  const parts = [
    ...filter.subjects.map((i) => bank.meta.subjects[i].name),
    ...filter.exams.map((i) => bank.meta.exams[i]),
    ...filter.topics.map((i) => bank.topics[i].name),
    ...(filter.subs ?? []).map((i) => bank.subs[i].name),
    filter.yearMin || filter.yearMax ? `${filter.yearMin || '…'}–${filter.yearMax || '…'}` : '',
    typeof filter.diff === 'number' && filter.diff ? DIFF_LABEL[filter.diff] : '',
    filter.pending ? 'Revisões pendentes' : '', filter.unseen ? 'Inéditas' : '', filter.classic ? 'Clássicas' : '',
    filter.military ? 'Militares' : '', filter.commented ? 'Com resolução' : '',
  ].filter(Boolean)
  if (!parts.length) return null
  return (
    <div className="filter-summary">
      <button className="link" onClick={onOpen}>{parts.join(' · ')}</button>
      <span className="muted">{count.toLocaleString('pt-BR')} {count === 1 ? 'questão' : 'questões'}</span>
      <button className="link" onClick={onClear}>limpar</button>
    </div>
  )
}

function PomodoroChip({ subjectId, subjectName }: { subjectId: string | null; subjectName: string }) {
  const p = usePomodoro()
  const store = useStore()
  const elo = subjectId ? store.elo(subjectId) : null
  return (
    <div className="pomo">
      <button className={`pomo-timer ${p.running ? 'running' : ''} ${p.phase}`} onClick={() => pomodoro.toggle()}
        title={p.running ? 'Pausar' : 'Iniciar bloco de foco'} aria-label={`Pomodoro: ${p.phase === 'focus' ? 'foco' : 'pausa'}, ${formatClock(p.left)}`}>
        <span aria-hidden="true">{p.running ? '❚❚' : '▶'}</span>
        <span className="tabular">{formatClock(p.left)}</span>
        <span className="pomo-phase">{p.phase === 'focus' ? 'foco' : 'pausa'}</span>
      </button>
      {(p.running || p.left !== store.s.settings.pomoFocus * 60) && (
        <button className="link" onClick={() => pomodoro.reset()}>zerar</button>
      )}
      {elo !== null && (
        <span className="pomo-elo" title={`Elo em ${subjectName}`}>
          {subjectName} <b className="tabular">{elo}</b> <span className="muted">{tier(elo)}</span>
        </span>
      )}
    </div>
  )
}

export function Practice({ bank, onOpenFilters }: { bank: Bank; onOpenFilters: () => void }) {
  const store = useStore()
  const filter = store.s.filter
  // o conjunto só muda quando o filtro muda; "inéditas" e "pendentes" são reavaliadas a cada escolha
  const pool = useMemo(() => select(bank.rows, { ...filter, unseen: false, pending: false }, store), [bank, filter, store])
  const poolKey = JSON.stringify(filter)

  const next = useCallback((recent: readonly string[]) => {
    let rows = pool
    if (filter.unseen) rows = rows.filter((r) => !store.seen(r.id))
    if (filter.pending) rows = rows.filter((r) => store.due(r.id))
    return pickNext(rows, store, recent, filter.diff === 'prog' ? store.s.prog.level : 0)
  }, [filter, pool, store])

  const liveCount = useMemo(
    () => (filter.unseen || filter.pending ? select(bank.rows, filter, store).length : pool.length),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bank, filter, pool, store, store.snapshot()],
  )
  const [subject, setSubject] = useState<number | null>(null)
  const single = subject !== null ? bank.meta.subjects[subject] : null

  return (
    <main className="practice">
      <div className="practice-bar">
        <FilterSummary bank={bank} filter={filter} count={liveCount} onOpen={onOpenFilters}
          onClear={() => store.setFilter(EMPTY_FILTER)} />
        {filter.diff === 'prog' && (
          <span className="level" title="Modo Progressivo: 3 acertos seguidos sobem o nível">
            Progressivo · <b>{DIFF_LABEL[store.s.prog.level]}</b>
            <span className="pips" aria-hidden="true">
              {[0, 1, 2].map((i) => <i key={i} className={store.s.prog.run > i ? 'on' : ''} />)}
            </span>
          </span>
        )}
        <PomodoroChip subjectId={single?.id ?? null} subjectName={single?.name ?? ''} />
      </div>
      <Runner
        bank={bank} mode="practice" poolKey={poolKey} next={next} onShow={(r) => setSubject(r ? r.s : null)}
        empty={
          <div className="empty">
            <h2>{filter.pending ? 'Nenhuma revisão pendente por aqui' : filter.unseen ? 'Você já fez todas as questões deste recorte' : 'Nenhuma questão com esses filtros'}</h2>
            <p className="muted">Ajuste os filtros ou volte para a prática livre.</p>
            <div className="actions center">
              <button className="btn primary" onClick={onOpenFilters}>Ajustar filtros</button>
              {!isEmptyFilter(filter) && <button className="btn ghost" onClick={() => store.setFilter(EMPTY_FILTER)}>Prática livre</button>}
            </div>
          </div>
        }
      />
    </main>
  )
}
