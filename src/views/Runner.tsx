import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { feedbackLine, needsBreak } from '../core/coach'
import { loadQuestion, prefetch, skillName, theoryKey, type Bank } from '../core/data'
import { DEEP_UNLOCK } from '../core/elo'
import { Rich } from '../core/rich'
import { MASTERY } from '../core/progressive'
import { sounds } from '../core/sounds'
import { store, type AnswerResult, type Mode } from '../core/store'
import type { StreakEvent } from '../core/streak'
import { toast } from '../core/toast'
import { STAGE, type Question, type Row } from '../core/types'
import { LETTERS, optionCount, QuestionView } from './QuestionView'
import { TheoryPanel } from './TheoryPanel'

const COMBO_MARKS = [3, 5, 10, 15, 20, 30, 50]

function announceStreak(ev: StreakEvent, count: number) {
  if (ev.kind === 'same') return
  if (ev.kind === 'start') return toast('Primeiro dia da sua sequência. Bom começo!', '🔥')
  if (ev.kind === 'restart') return toast('Uma nova sequência começa hoje. Tudo que você já aprendeu continua com você.', '🌱', 6500)
  if (ev.kind === 'shielded') {
    toast(`Seu escudo cobriu ${ev.used === 1 ? 'o dia' : `os ${ev.used} dias`} de pausa. Sequência de ${count} dias preservada, bom te ver de volta.`, '🛡️', 6500)
  } else {
    toast(`${count} dias seguidos de estudo.`, '🔥')
  }
  if (ev.shieldEarned) toast('Você ganhou um escudo de sequência: ele cobre um dia de folga.', '🛡️', 6000)
  sounds.streak()
}

interface Props {
  bank: Bank
  mode: Mode
  /** muda quando o conjunto de questões muda (filtros), para recomeçar */
  poolKey: string
  next: (recent: readonly string[]) => Row | null
  empty: ReactNode
  /** índice/total, para a revisão do dia */
  progress?: () => string
  onShow?: (row: Row | null) => void
}

export function Runner({ bank, mode, poolKey, next, empty, progress, onShow }: Props) {
  const [row, setRow] = useState<Row | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [error, setError] = useState('')
  const [theory, setTheory] = useState<string | null>(null)
  const [marked, setMarked] = useState(false)
  const [example, setExample] = useState<{ row: Row; q: Question } | null>(null)
  const recent = useRef<string[]>([])
  // respostas desta sessão, para perceber cansaço; a pausa é sugerida no máximo uma vez
  const session = useRef<{ ok: boolean; ms: number }[]>([])
  const breakOffered = useRef(false)
  const upcoming = useRef<Row | null>(null)
  const started = useRef(0)
  const nextRef = useRef(next)
  nextRef.current = next
  const onShowRef = useRef(onShow)
  onShowRef.current = onShow
  const nextBtn = useRef<HTMLButtonElement>(null)

  const show = useCallback((r: Row | null) => {
    setRow(r)
    setQuestion(null)
    setSelected(null)
    setResult(null)
    setMarked(false)
    setExample(null)
    setError('')
    onShowRef.current?.(r)
    if (!r) return
    loadQuestion(r).then(
      (q) => {
        setQuestion(q)
        started.current = Date.now()
      },
      () => setError('Não consegui carregar esta questão.'),
    )
  }, [])

  const advance = useCallback(() => {
    const r = upcoming.current ?? nextRef.current(recent.current)
    upcoming.current = null
    show(r)
    window.scrollTo({ top: 0 })
  }, [show])

  useEffect(() => {
    recent.current = []
    upcoming.current = null
    setTheory(null)
    show(nextRef.current([]))
  }, [poolKey, show])

  const confirm = useCallback((choice: number) => {
    if (!row || !question || result) return
    const ok = choice === question.ans
    const ms = Date.now() - started.current
    const res = store.answer(bank, row, ok, ms, mode)
    session.current.push({ ok, ms })
    setSelected(choice)
    setResult(res)
    recent.current = [...recent.current, row.id].slice(-40)
    upcoming.current = nextRef.current(recent.current)
    prefetch(upcoming.current)
    if (ok) {
      if (COMBO_MARKS.includes(res.combo)) {
        sounds.combo()
        toast(`${res.combo} acertos seguidos!`, '✨')
      } else if (res.levelChange > 0) sounds.levelUp()
      else if (mode === 'review') sounds.drop()
      else sounds.correct(res.combo)
    }
    if (res.levelChange > 0) {
      const done = STAGE[(store.s.prog.level - 1) as 1 | 2]
      toast(`${done} dominada: ${MASTERY.need} de ${MASTERY.window}! Agora vem ${STAGE[store.s.prog.level].toLowerCase()}.`, '📈', 5000)
    }
    if (res.levelChange < 0) toast(`Vamos firmar a base com questões de ${STAGE[store.s.prog.level].toLowerCase()} antes de subir de novo.`, '🌊')
    announceStreak(res.streakEvent, store.s.streak.count)
    if (res.goalHit) {
      sounds.streak()
      toast(`Meta de hoje cumprida: ${store.dailyGoal()} questões. Parar agora é mérito; seguir é bônus.`, '🎯', 6500)
    } else if (!breakOffered.current && needsBreak(session.current)) {
      breakOffered.current = true
      toast('As últimas vieram rápidas e erradas: sinal de cansaço, não de falta de capacidade. Cinco minutos de pausa ajudam a fixar.', '🌿', 8000)
    }
    if (res.skillElo >= DEEP_UNLOCK && res.skillElo - res.skillDelta < DEEP_UNLOCK) {
      toast(`Você desbloqueou o aprofundamento em ${skillName(bank, row)}: questões de ITA, IME e de olimpíada começam a aparecer.`, '🏔️', 7000)
    }
    if (res.theoryTopic) setTheory(res.theoryTopic)
    requestAnimationFrame(() => nextBtn.current?.focus({ preventScroll: true }))
  }, [bank, mode, question, result, row])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement
      if (e.ctrlKey || e.metaKey || e.altKey || el.closest('input, textarea, select, [role="dialog"]')) return
      if (!question) return
      const key = e.key.toLowerCase()
      const n = optionCount(question)
      const idx = '12345'.includes(key) && key ? Number(key) - 1 : 'abcde'.indexOf(key)
      if (!result && idx >= 0 && idx < n && key.length === 1) {
        e.preventDefault()
        if (selected === idx) return confirm(idx) // mesma tecla duas vezes confirma
        sounds.select()
        return setSelected(idx)
      }
      if (e.key === 'Enter' || e.key === ' ') {
        if (el.closest('button:not(.option), a')) return // deixa o botão focado agir
        e.preventDefault()
        if (result) advance()
        else if (selected !== null) confirm(selected)
      } else if (key === 'r' && result && selected === question.ans && !marked) {
        store.markHard(row!.id)
        setMarked(true)
      } else if (key === 'e' && result && selected !== question.ans && !question.exp && row && row.u >= 0) {
        const pool = bank.rows.filter((r) => r.u === row.u && r.id.startsWith('autoral-') && r.id !== row.id)
        const pick = pool[Math.floor(Math.random() * pool.length)]
        if (pick) loadQuestion(pick).then((q) => setExample({ row: pick, q }), () => {})
      } else if (key === 't' && row && theoryKey(bank, row)) {
        const card = theoryKey(bank, row)
        setTheory((t) => (t ? null : card))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [advance, bank, confirm, marked, question, result, row, selected])

  if (!row) return <>{empty}</>
  if (error) {
    return (
      <div className="empty">
        <p>{error}</p>
        <button className="btn primary" onClick={advance}>Tentar outra questão</button>
      </div>
    )
  }
  if (!question) return <div className="question skeleton" aria-busy="true" />

  const correct = result && selected === question.ans
  const card = theoryKey(bank, row)
  // exemplo resolvido: questão autoral do mesmo subtópico, com o passo a passo
  const examples = row.u >= 0 ? bank.rows.filter((r) => r.u === row.u && r.id.startsWith('autoral-') && r.id !== row.id) : []
  const showExample = () => {
    const pick = examples[Math.floor(Math.random() * examples.length)]
    if (pick) loadQuestion(pick).then((q) => setExample({ row: pick, q }), () => {})
  }
  const hasTheory = !!card
  const pick = (i: number) => {
    if (result) return
    sounds.select()
    setSelected(i)
  }

  return (
    <div className="runner">
      <QuestionView
        bank={bank} row={row} question={question} selected={selected}
        reveal={result ? question.ans : null} onSelect={pick} label={progress?.()}
      />

      {!result ? (
        <div className="actions">
          <button className="btn primary" disabled={selected === null} onClick={() => selected !== null && confirm(selected)}>
            Responder <kbd>Enter</kbd>
          </button>
          <span className="hint">
            <kbd>A</kbd>–<kbd>{LETTERS[optionCount(question) - 1]}</kbd> ou <kbd>1</kbd>–<kbd>{optionCount(question)}</kbd> para marcar
          </span>
        </div>
      ) : (
        <section className={`feedback ${correct ? 'good' : 'soft'}`}>
          <div className="fb-head">
            <strong>
              {feedbackLine({ ok: !!correct, recovered: result.recovered, slow: result.slow, combo: result.combo, level: row.d, wrongRun: result.wrongRun }, hash(row.id))}
              {!correct && <> A resposta é a <b>{LETTERS[question.ans]}</b>.</>}
            </strong>
            {/* só o ganho aparece: mostrar a perda logo após o erro é aversão à perda, e o Elo continua honesto nos Detalhes */}
            {result.eloDelta > 0 && (
              <span className="elo-delta up">
                +{result.eloDelta} Elo
              </span>
            )}
            {correct && result.combo >= 2 && <span className="combo">{result.combo} seguidas</span>}
          </div>
          {!correct && selected !== null && question.opts[selected]?.why && (
            // diz o erro da alternativa que o aluno marcou, não só qual era a certa
            <p className="diagnosis">
              <span className="eyebrow">Você marcou a {LETTERS[selected]}</span>
              <Rich text={question.opts[selected].why!} className="inline" />
            </p>
          )}
          {question.exp ? (
            <Rich text={question.exp} className="explanation" />
          ) : !correct ? (
            <p className="muted">Esta questão ainda não tem resolução comentada.{hasTheory && ' O resumo do tópico pode ajudar.'}</p>
          ) : null}
          {!correct && result.queued && <p className="muted">Ela volta sozinha na sua revisão, daqui a um dia.</p>}
          {!correct && !question.exp && examples.length > 0 && !example && (
            <button className="btn ghost example-btn" onClick={showExample}>Ver um exemplo parecido resolvido <kbd>E</kbd></button>
          )}
          {example && (
            <div className="worked">
              <span className="eyebrow">Exemplo resolvido · {bank.subs[example.row.u]?.name}</span>
              <Rich text={example.q.stem ?? ''} />
              <p><b>Resposta:</b> <Rich text={example.q.opts[example.q.ans]?.t ?? ''} className="inline" /></p>
              <Rich text={example.q.exp ?? ''} className="explanation" />
              <p className="muted">Agora volte à questão de cima com esse caminho em mente.</p>
            </div>
          )}
          <div className="actions">
            <button ref={nextBtn} className="btn primary" onClick={advance}>Próxima <kbd>Enter</kbd></button>
            {hasTheory && (
              <button className="btn ghost" onClick={() => setTheory(card)}>Teoria do tópico <kbd>T</kbd></button>
            )}
            {correct && (
              <button className="btn ghost" disabled={marked} onClick={() => { store.markHard(row.id); setMarked(true) }}>
                {marked ? 'Vai voltar na revisão' : <>Rever depois <kbd>R</kbd></>}
              </button>
            )}
            {question.src && (
              <span className="source">
                {question.src}
                {question.book && HAS_BOOKS && <> · <a href={bookHref(question.book.file, question.book.page)} target="_blank" rel="noreferrer">abrir no livro ↗</a></>}
              </span>
            )}
          </div>
        </section>
      )}

      {theory && bank.meta.theory[theory] && (
        <TheoryPanel card={bank.meta.theory[theory]} onClose={() => setTheory(null)} />
      )}
    </div>
  )
}

/** os PDFs dos livros só existem no servidor local (vite.config.ts); no site publicado o link não aparece */
export const HAS_BOOKS = import.meta.env.DEV

export function bookHref(file: string, page?: number): string {
  return `/livros/${encodeURIComponent(file)}${page ? `#page=${page}` : ''}`
}

/** variação estável de texto por questão */
function hash(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return h
}
