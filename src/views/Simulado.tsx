import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { countBy, loadQuestion, trackName, trackRows, type Bank } from '../core/data'
import { sounds } from '../core/sounds'
import { store, useStore, type SimResult } from '../core/store'
import { formatClock } from '../core/time'
import { F_DEEP, type Question, type Row } from '../core/types'
import { ExamGroups } from './FilterSheet'
import { LETTERS, optionCount, QuestionView } from './QuestionView'

const STANDARD_MIN_PER_Q = 3

interface Config {
  kind: 'padrao' | 'militar'
  exam: string // militar
  n: number
  subjects: number[]
  exams: number[] // padrão
  diff: 0 | 1 | 2 | 3
}

interface Running {
  config: Config
  rows: Row[]
  questions: Question[]
  borrowed: number // questões de outras bancas usadas para completar
  limit: number // segundos (0 = sem limite)
  startedAt: number
}

function shuffle<T>(list: T[]): T[] {
  const a = [...list]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/**
 * De onde sai o simulado: na prova oficial, as questões daquela banca (e só as matérias que ela cobra);
 * no padrão, a trilha do aluno. Sem matéria marcada, valem as matérias que existem ali.
 */
function scope(bank: Bank, c: Config, track: string): { base: Row[]; subjects: number[] } {
  const examIdx = bank.meta.exams.indexOf(c.exam)
  const base = c.kind === 'militar' ? bank.rows.filter((r) => r.e === examIdx) : trackRows(bank, track)
  const present = [...countBy(base, 's').keys()].sort((a, b) => a - b)
  return { base, subjects: c.subjects.length ? c.subjects.filter((s) => present.includes(s)) : present }
}

/** Sorteia as questões equilibrando as matérias escolhidas. */
function draw(bank: Bank, c: Config, track: string): { rows: Row[]; borrowed: number } {
  const { base, subjects } = scope(bank, c, track)
  const examIdx = bank.meta.exams.indexOf(c.exam)
  const own = (r: Row) => c.kind === 'militar' || ((c.exams.length ? c.exams.includes(r.e) : !(r.f & F_DEEP)) && (!c.diff || r.d === c.diff))
  const picked: Row[] = []
  let borrowed = 0
  subjects.forEach((s, k) => {
    const want = Math.floor(c.n / subjects.length) + (k < c.n % subjects.length ? 1 : 0)
    const mine = shuffle(base.filter((r) => r.s === s && own(r))).slice(0, want)
    picked.push(...mine)
    if (c.kind === 'militar' && mine.length < want) {
      // banca ainda com poucas questões no banco: completa com as mais difíceis da matéria
      const extra = shuffle(bank.rows.filter((r) => r.s === s && r.e !== examIdx && r.d === 3)).slice(0, want - mine.length)
      borrowed += extra.length
      picked.push(...extra)
    }
  })
  return { rows: picked, borrowed }
}

function available(bank: Bank, c: Config, track: string): number {
  return draw(bank, { ...c, n: 100_000 }, track).rows.length
}

export function Simulado({ bank, onFocusMode }: { bank: Bank; onFocusMode: (on: boolean) => void }) {
  const st = useStore()
  const sims = bank.meta.sims
  const milExams = Object.keys(sims)
  const [config, setConfig] = useState<Config>({ kind: 'padrao', exam: milExams[0] ?? '', n: 20, subjects: [], exams: [], diff: 0 })
  const [run, setRun] = useState<Running | null>(null)
  const [done, setDone] = useState<{ run: Running; answers: (number | null)[]; result: SimResult } | null>(null)
  const [loading, setLoading] = useState(false)
  const patch = (p: Partial<Config>) => setConfig((c) => ({ ...c, ...p }))
  const spec = sims[config.exam]
  const track = st.s.settings.track
  const max = useMemo(() => available(bank, config, track), [bank, config, track])
  const n = Math.min(config.n, max)
  const minutes = config.kind === 'militar' && spec ? Math.round(n * spec.minutesPerQuestion) : n * STANDARD_MIN_PER_Q
  const { base, subjects: inScope } = useMemo(() => scope(bank, { ...config, subjects: [] }, track), [bank, config, track])
  const ownCount = useMemo(() => {
    const subj = config.subjects.length ? config.subjects : inScope
    return base.filter((r) => subj.includes(r.s)).length
  }, [base, config.subjects, inScope])

  const start = async () => {
    setLoading(true)
    const { rows, borrowed } = draw(bank, { ...config, n }, track)
    const ordered = shuffle(rows).sort((a, b) => a.s - b.s)
    const questions = await Promise.all(ordered.map(loadQuestion))
    setLoading(false)
    setDone(null)
    setRun({ config: { ...config, n }, rows: ordered, questions, borrowed, limit: config.kind === 'militar' ? minutes * 60 : 0, startedAt: Date.now() })
    onFocusMode(true)
  }

  const finish = useCallback((r: Running, answers: (number | null)[]) => {
    const seconds = Math.round((Date.now() - r.startedAt) / 1000)
    const bySubject: SimResult['bySubject'] = {}
    let correct = 0
    let answered = 0
    r.rows.forEach((row, i) => {
      const name = bank.meta.subjects[row.s].name
      const ok = answers[i] === r.questions[i].ans
      bySubject[name] ??= { n: 0, ok: 0 }
      bySubject[name].n++
      if (ok) { bySubject[name].ok++; correct++ }
      if (answers[i] !== null) {
        answered++
        store.answer(bank, row, ok, (seconds * 1000) / r.rows.length, 'sim')
      }
    })
    const result: SimResult = {
      ts: Date.now(), kind: r.config.kind, exam: r.config.kind === 'militar' ? r.config.exam : undefined,
      total: r.rows.length, correct, answered, seconds, limit: r.limit, bySubject,
    }
    store.addSim(result)
    sounds.bell()
    setRun(null)
    setDone({ run: r, answers, result })
    onFocusMode(false)
    window.scrollTo({ top: 0 })
  }, [bank, onFocusMode])

  if (run) return <Exam bank={bank} run={run} onFinish={(a) => finish(run, a)} />
  if (done) return <Result bank={bank} {...done} onAgain={() => setDone(null)} />

  return (
    <main className="page sim-setup">
      <h1>Simulado</h1>
      <div className="segmented wide">
        <button className={config.kind === 'padrao' ? 'on' : ''} onClick={() => patch({ kind: 'padrao' })}>Padrão</button>
        <button className={config.kind === 'militar' ? 'on' : ''} onClick={() => patch({ kind: 'militar', n: 20, subjects: [] })}
          disabled={!milExams.length} title="Cronômetro oficial e nota de corte: ITA, EsPCEx, OAB">Prova oficial</button>
      </div>

      {config.kind === 'militar' && spec ? (
        <section>
          <h3>Prova</h3>
          <div className="chips">
            {milExams.map((e) => (
              <button key={e} className={`chip ${config.exam === e ? 'on' : ''}`} title={sims[e].name} onClick={() => patch({ exam: e, subjects: [] })}>{e}</button>
            ))}
          </div>
          <p className="muted">{spec.format}</p>
          <p className="muted">
            Condições de prova: cronômetro rígido de {spec.minutesPerQuestion.toLocaleString('pt-BR')} min por questão, sem gabarito até o fim.
            {ownCount < n && ` O banco tem ${ownCount} ${ownCount === 1 ? 'questão' : 'questões'} desta banca nas matérias escolhidas; o restante é completado com questões difíceis de outras bancas.`}
          </p>
        </section>
      ) : (
        <>
          <p className="muted">Questões de <b>{trackName(bank, track)}</b>. O objetivo se troca na barra da prática.</p>
          <section>
            <h3>Prova</h3>
            <ExamGroups bank={bank} rows={base} selected={config.exams} onChange={(exams) => patch({ exams })} />
          </section>
          <section>
            <h3>Dificuldade</h3>
            <div className="segmented">
              {(['Todas', 'Fácil', 'Médio', 'Difícil'] as const).map((label, d) => (
                <button key={label} className={config.diff === d ? 'on' : ''} onClick={() => patch({ diff: d as Config['diff'] })}>{label}</button>
              ))}
            </div>
          </section>
        </>
      )}

      <section>
        <h3>Matérias</h3>
        <div className="chips">
          {bank.meta.subjects.map((s, i) => inScope.includes(i) ? (
            <button key={s.id} className={`chip ${config.subjects.includes(i) ? 'on' : ''}`}
              onClick={() => patch({ subjects: config.subjects.includes(i) ? config.subjects.filter((x) => x !== i) : [...config.subjects, i] })}>{s.name}</button>
          ) : null)}
        </div>
      </section>

      <section>
        <h3>Quantidade de questões</h3>
        <div className="chips">
          {[10, 20, 30, 45, 60].map((v) => (
            <button key={v} className={`chip ${config.n === v ? 'on' : ''}`} onClick={() => patch({ n: v })}>{v}</button>
          ))}
          <label className="n-input">ou
            <input type="number" min={1} max={200} value={config.n} onChange={(e) => patch({ n: Math.max(1, Math.min(200, Number(e.target.value) || 1)) })} />
          </label>
        </div>
      </section>

      <footer className="sim-start">
        <span className="count">
          <b>{n}</b> {n === 1 ? 'questão' : 'questões'} · {config.kind === 'militar' ? `${formatClock(minutes * 60)} de prova` : `cerca de ${minutes} min, sem limite`}
          {max < config.n && <span className="muted"> (há {max} disponíveis)</span>}
        </span>
        <button className="btn primary" disabled={!n || loading} onClick={start}>{loading ? 'Preparando…' : 'Começar simulado'}</button>
      </footer>

      {st.sims.length > 0 && <p className="muted">Seus simulados anteriores ficam em “Ver detalhes”.</p>}
    </main>
  )
}

function Exam({ bank, run, onFinish }: { bank: Bank; run: Running; onFinish: (answers: (number | null)[]) => void }) {
  const [answers, setAnswers] = useState<(number | null)[]>(() => run.rows.map(() => null))
  const [i, setI] = useState(0)
  const [now, setNow] = useState(Date.now())
  const [confirming, setConfirming] = useState(false)
  const answersRef = useRef(answers)
  answersRef.current = answers
  const elapsed = Math.floor((now - run.startedAt) / 1000)
  const left = run.limit ? run.limit - elapsed : 0

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [])
  useEffect(() => {
    if (run.limit && left <= 0) onFinish(answersRef.current)
  }, [left, onFinish, run.limit])

  const mark = useCallback((choice: number) => {
    setAnswers((a) => a.map((v, k) => (k === i ? (v === choice ? null : choice) : v)))
  }, [i])
  const move = useCallback((d: number) => setI((k) => Math.max(0, Math.min(run.rows.length - 1, k + d))), [run.rows.length])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || confirming) return
      const key = e.key.toLowerCase()
      const idx = key.length === 1 && '12345'.includes(key) ? Number(key) - 1 : key.length === 1 ? 'abcde'.indexOf(key) : -1
      if (idx >= 0 && idx < optionCount(run.questions[i])) { e.preventDefault(); mark(idx) }
      else if (e.key === 'Enter' || e.key === 'ArrowRight') { e.preventDefault(); move(1) }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirming, i, mark, move, run.questions])

  const blank = answers.filter((a) => a === null).length
  const low = run.limit > 0 && left <= 300

  return (
    <main className="exam">
      <header className="exam-bar">
        <strong>{run.config.kind === 'militar' ? `Simulado ${run.config.exam}` : 'Simulado'}</strong>
        <span className={`exam-clock tabular ${low ? 'low' : ''}`} role="timer">
          {run.limit ? formatClock(left) : formatClock(elapsed)}
          <span className="muted">{run.limit ? ' restantes' : ' decorridos'}</span>
        </span>
        <button className="btn ghost small" onClick={() => setConfirming(true)}>Entregar prova</button>
      </header>

      <QuestionView bank={bank} row={run.rows[i]} question={run.questions[i]} selected={answers[i]} reveal={null}
        onSelect={mark} label={`Questão ${i + 1} de ${run.rows.length}`} />

      <div className="actions">
        <button className="btn ghost" disabled={i === 0} onClick={() => move(-1)}>← Anterior</button>
        {i < run.rows.length - 1
          ? <button className="btn primary" onClick={() => move(1)}>Próxima <kbd>Enter</kbd></button>
          : <button className="btn primary" onClick={() => setConfirming(true)}>Entregar prova</button>}
      </div>

      <nav className="exam-grid" aria-label="Questões do simulado">
        {run.rows.map((r, k) => (
          <button key={r.id} className={`${k === i ? 'current' : ''} ${answers[k] !== null ? 'answered' : ''}`} onClick={() => setI(k)}
            aria-label={`Questão ${k + 1}${answers[k] !== null ? `, marcada ${LETTERS[answers[k]!]}` : ', em branco'}`}>{k + 1}</button>
        ))}
      </nav>

      {confirming && (
        <div className="sheet-backdrop">
          <div className="sheet small" role="dialog" aria-modal="true" aria-label="Entregar prova">
            <div className="sheet-body">
              <h2>Entregar a prova?</h2>
              <p className="muted">{blank ? `${blank} ${blank === 1 ? 'questão está' : 'questões estão'} em branco.` : 'Todas as questões estão marcadas.'}</p>
            </div>
            <footer className="sheet-foot">
              <button className="btn ghost" onClick={() => setConfirming(false)}>Continuar a prova</button>
              <button className="btn primary" onClick={() => onFinish(answers)}>Entregar</button>
            </footer>
          </div>
        </div>
      )}
    </main>
  )
}

function Result({ bank, run, answers, result, onAgain }: {
  bank: Bank; run: Running; answers: (number | null)[]; result: SimResult; onAgain: () => void
}) {
  const [open, setOpen] = useState<number | null>(null)
  const pct = result.total ? Math.round((result.correct / result.total) * 100) : 0
  const spec = result.exam ? bank.meta.sims[result.exam] : undefined
  const cut = spec?.cutoff
  const gap = cut ? pct - cut.percent : 0
  return (
    <main className="page sim-result">
      <h1>{result.exam ? `Simulado ${result.exam}` : 'Simulado'} concluído</h1>
      <div className="score">
        <div className="score-main"><b className="tabular">{pct}%</b><span>{result.correct} de {result.total} questões</span></div>
        <div className="score-side">
          <span>Tempo: <b className="tabular">{formatClock(result.seconds)}</b>{result.limit ? ` de ${formatClock(result.limit)}` : ''}</span>
          <span>Em branco: <b>{result.total - result.answered}</b></span>
        </div>
      </div>

      {result.exam && (
        <section className="cutoff">
          <h3>Comparação com a nota de corte</h3>
          {cut ? (
            <>
              <div className="cut-bar" aria-hidden="true">
                <i className="you" style={{ width: `${pct}%` }} />
                <span className="mark" style={{ left: `${cut.percent}%` }} />
              </div>
              <p>
                {gap >= 0
                  ? <>Você ficou <b>{gap} {gap === 1 ? 'ponto' : 'pontos'}</b> acima da referência de <b>{cut.percent}%</b> de acertos.</>
                  : <>A referência é de <b>{cut.percent}%</b> de acertos; faltaram <b>{-gap} {gap === -1 ? 'ponto' : 'pontos'}</b>. As matérias abaixo mostram onde há mais a ganhar.</>}
              </p>
              <p className="muted">{cut.note} Fonte: {cut.source}</p>
            </>
          ) : (
            <p className="muted">Ainda não há uma nota de corte histórica confiável cadastrada para esta instituição.</p>
          )}
          {run.borrowed > 0 && (
            <p className="muted">{run.borrowed} das {result.total} questões vieram de outras bancas, em nível difícil, porque o banco ainda tem poucas desta instituição. A comparação é uma aproximação.</p>
          )}
        </section>
      )}

      <section>
        <h3>Por matéria</h3>
        <ul className="bars">
          {Object.entries(result.bySubject).map(([name, v]) => (
            <li key={name}>
              <span>{name}</span>
              <span className="meter"><i style={{ width: `${(v.ok / v.n) * 100}%` }} /></span>
              <b className="tabular">{v.ok}/{v.n}</b>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Gabarito</h3>
        <p className="muted">As questões que você errou já entraram na sua revisão.</p>
        <div className="exam-grid result">
          {run.rows.map((r, k) => {
            const ok = answers[k] === run.questions[k].ans
            return (
              <button key={r.id} className={`${ok ? 'right' : answers[k] === null ? '' : 'missed'} ${open === k ? 'current' : ''}`}
                onClick={() => setOpen(open === k ? null : k)} aria-label={`Questão ${k + 1}: ${ok ? 'certa' : answers[k] === null ? 'em branco' : 'errada'}`}>
                {k + 1}
              </button>
            )
          })}
        </div>
        {open !== null && (
          <QuestionView bank={bank} row={run.rows[open]} question={run.questions[open]} selected={answers[open]}
            reveal={run.questions[open].ans} onSelect={() => {}} label={`Questão ${open + 1}`} />
        )}
      </section>

      <div className="actions">
        <button className="btn primary" onClick={onAgain}>Novo simulado</button>
      </div>
    </main>
  )
}
