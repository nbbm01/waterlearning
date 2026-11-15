import type { Bank } from '../core/data'
import { Rich } from '../core/rich'
import { DIFF_LABEL, type Question, type Row } from '../core/types'

export const LETTERS = ['A', 'B', 'C', 'D', 'E']

export function optionCount(q: Question): number {
  return q.k === 'text' ? q.opts.length : (q.n ?? 5)
}

interface Props {
  bank: Bank
  row: Row
  question: Question
  selected: number | null
  /** índice correto, quando o gabarito já pode aparecer */
  reveal: number | null
  onSelect: (i: number) => void
  label?: string
}

export function QuestionView({ bank, row, question, selected, reveal, onSelect, label }: Props) {
  const subject = bank.meta.subjects[row.s]
  const n = optionCount(question)
  const state = (i: number) => {
    if (reveal === null) return selected === i ? 'picked' : ''
    if (i === reveal) return selected === i ? 'right' : 'answer'
    return selected === i ? 'missed' : 'dim'
  }
  return (
    <article className="question" aria-live="polite">
      <header className="q-meta">
        {label && <span className="q-label">{label}</span>}
        <span className="q-exam">{bank.meta.exams[row.e]}{row.y ? ` ${row.y}` : ''}</span>
        <span>{subject.name}</span>
        <span>{row.u >= 0 ? bank.subs[row.u].name : bank.topics[row.t].name}</span>
        <span className={`q-diff d${row.d}`}>{DIFF_LABEL[row.d]}</span>
      </header>

      {question.k === 'text' ? (
        <Rich text={question.stem ?? ''} className="q-stem" />
      ) : (
        <div className="q-scan">
          {(question.imgs ?? []).map((src) => (
            <img key={src} src={`${import.meta.env.BASE_URL}${src}`} alt="Enunciado da questão, reproduzido da fonte original" />
          ))}
        </div>
      )}

      <ol className={`options ${question.k === 'image' ? 'compact' : ''}`}>
        {Array.from({ length: n }, (_, i) => {
          const opt = question.opts[i]
          return (
            <li key={i}>
              <button
                type="button"
                className={`option ${state(i)}`}
                onClick={() => onSelect(i)}
                disabled={reveal !== null}
                aria-pressed={selected === i}
              >
                <kbd>{LETTERS[i]}</kbd>
                {opt?.img ? (
                  <img src={`${import.meta.env.BASE_URL}${opt.img}`} alt={`Alternativa ${LETTERS[i]}`} loading="lazy" />
                ) : opt?.t ? (
                  <Rich text={opt.t} />
                ) : (
                  <span className="sr-only">Alternativa {LETTERS[i]}</span>
                )}
              </button>
            </li>
          )
        })}
      </ol>
    </article>
  )
}
