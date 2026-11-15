import { useCallback, useMemo, useState } from 'react'
import { greeting, suggest, weakSpots } from '../core/coach'
import { skillKey, skillTarget, type Bank } from '../core/data'
import { DEEP_UNLOCK, expected, tier } from '../core/elo'
import { isEmptyFilter, pickNext, select } from '../core/filters'
import { pomodoro, usePomodoro } from '../core/pomodoro'
import { MASTERY, masteredCount } from '../core/progressive'
import { useStore } from '../core/store'
import { formatClock } from '../core/time'
import { DIFF_LABEL, EMPTY_FILTER, STAGE, type Filter, type Row } from '../core/types'
import { Runner } from './Runner'
import type { View } from './TopBar'

const BLOCK = 4

/**
 * Blocos curtos: ~4 questões do mesmo subtópico e depois troca. Intercalar assuntos ajuda a fixar,
 * mas pular a cada questão desorienta quem está começando.
 */
function practiceBlock(rows: Row[], recent: readonly string[], bank: Bank): Row[] {
  const base = rows
  const last = recent.slice(-BLOCK).map((id) => bank.byId.get(id))
  const current = last.at(-1)?.u ?? -1
  const run = [...last].reverse().findIndex((r) => r?.u !== current)
  const streak = run === -1 ? last.length : run
  if (current < 0) return base
  const same = base.filter((r) => r.u === current)
  const other = base.filter((r) => r.u !== current)
  if (streak < BLOCK && same.length) return same
  return other.length ? other : base
}

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
    filter.military ? 'Militares' : '', filter.commented ? 'Com resolução' : '', filter.deep ? 'Aprofundamento' : '',
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

/**
 * Uma linha de orientação acima da questão, só na prática livre: o que mais ajuda agora.
 * É um convite com um clique e some com outro; nunca impede de seguir estudando.
 */
function Coach({ bank, go }: { bank: Bank; go: (v: View) => void }) {
  const store = useStore()
  const [closed, setClosed] = useState(false)
  if (closed) return null
  const today = store.todayCount()
  const goal = store.dailyGoal()
  const weak = weakSpots(store.skills).filter((w) => skillTarget(bank, w.id))
  const tip = suggest({ due: store.dueCards().length, weak, today, goal })
  const close = <button className="icon-btn coach-close" onClick={() => setClosed(true)} aria-label="Dispensar sugestão">✕</button>

  if (tip?.kind === 'review') {
    return (
      <aside className="coach">
        <span><b>{tip.count} revisões</b> esperando por você, uns {tip.minutes} min. Rever na hora certa é o que mais fixa.</span>
        <button className="btn small primary" onClick={() => go('review')}>Revisar agora</button>
        {close}
      </aside>
    )
  }
  if (tip?.kind === 'weak') {
    const target = skillTarget(bank, tip.spot.id)!
    return (
      <aside className="coach">
        <span>Ponto a fortalecer: <b>{target.name}</b>, {tip.spot.pct}% em {tip.spot.n} questões. Dá para virar esse número.</span>
        <button className="btn small primary" onClick={() => store.setFilter({ ...EMPTY_FILTER, subs: target.subs, topics: target.topics })}>Treinar agora</button>
        {close}
      </aside>
    )
  }
  if (tip?.kind === 'goal') {
    return <aside className="coach"><span>Faltam <b>{tip.left}</b> para a meta de hoje. Você já fez a parte mais difícil: começar.</span>{close}</aside>
  }
  if (today === 0) {
    return <aside className="coach quiet"><span>{greeting(new Date().getHours(), { today, goal, streak: store.s.streak.count })}</span></aside>
  }
  return null
}

export function Practice({ bank, onOpenFilters, go }: { bank: Bank; onOpenFilters: () => void; go: (v: View) => void }) {
  const store = useStore()
  const filter = store.s.filter
  // o conjunto só muda quando o filtro muda; "inéditas" e "pendentes" são reavaliadas a cada escolha
  // aprofundamento se libera sozinho por matéria quando o Elo chega lá
  const unlocked = useCallback((r: Row) => store.elo(skillKey(bank, r)) >= DEEP_UNLOCK, [bank, store])
  const pool = useMemo(() => select(bank.rows, { ...filter, unseen: false, pending: false }, store, unlocked),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bank, filter, store, unlocked, Object.entries(store.s.elo).filter(([, v]) => v >= DEEP_UNLOCK).map(([k]) => k).join()])
  const poolKey = JSON.stringify(filter)

  const next = useCallback((recent: readonly string[]) => {
    let rows = pool
    if (filter.unseen) rows = rows.filter((r) => !store.seen(r.id))
    if (filter.pending) rows = rows.filter((r) => store.due(r.id))
    rows = practiceBlock(rows, recent, bank)
    const prog = filter.diff === 'prog'
    const chance = (r: Row) => expected(store.elo(skillKey(bank, r)), r.r)
    return pickNext(rows, store, recent, prog ? store.s.prog.level : 0, Math.random, prog ? chance : undefined)
  }, [bank, filter, pool, store])

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
          <span className="level" title={`Modo Progressivo: você sobe de degrau quando acerta ${MASTERY.need} das últimas ${MASTERY.window} deste degrau`}>
            Progressivo · <b>{STAGE[store.s.prog.level]}</b>
            {store.s.prog.level < 3 && (
              <span className="pips" aria-label={`${masteredCount(store.s.prog)} de ${MASTERY.need} acertos para dominar`}>
                {Array.from({ length: MASTERY.need }, (_, i) => <i key={i} className={masteredCount(store.s.prog) > i ? 'on' : ''} />)}
              </span>
            )}
          </span>
        )}
        <PomodoroChip subjectId={single?.id ?? null} subjectName={single?.name ?? ''} />
      </div>
      {isEmptyFilter(filter) && <Coach bank={bank} go={go} />}
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
