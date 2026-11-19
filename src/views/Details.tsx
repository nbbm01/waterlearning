import { useEffect, useMemo, useRef, useState } from 'react'
import { strongSpots, weakSpots } from '../core/coach'
import { countBy, skillTarget, trackRows, type Bank } from '../core/data'
import { START_ELO, tier } from '../core/elo'
import { pomodoro } from '../core/pomodoro'
import { useStore } from '../core/store'
import { MAX_SHIELDS, SHIELD_EVERY, visibleStreak } from '../core/streak'
import { dayNumber, dayToDate, formatClock, formatHours, weekStart } from '../core/time'
import { toast } from '../core/toast'
import { EMPTY_FILTER } from '../core/types'
import type { View } from './TopBar'

const WEEKS = 18
const MIN_ATTEMPTS = 3

function heatLevel(n: number): number {
  return n === 0 ? 0 : n < 10 ? 1 : n < 25 ? 2 : n < 50 ? 3 : 4
}

function masteryLevel(pct: number): number {
  return pct < 40 ? 1 : pct < 60 ? 2 : pct < 80 ? 3 : 4
}

export function Details({ bank, go }: { bank: Bank; go: (v: View) => void }) {
  const store = useStore()
  const today = dayNumber()
  const streak = visibleStreak(store.s.streak, today)
  const { settings, days, topics } = store.s
  // 18 matérias e 190 tópicos de uma vez afogam o que importa: aparecem as do objetivo e as já praticadas
  const inTrack = useMemo(() => countBy(trackRows(bank, settings.track), 's'), [bank, settings.track])
  const shown = bank.meta.subjects.filter((s, i) => inTrack.has(i) || s.id in store.s.elo)
  const file = useRef<HTMLInputElement>(null)
  const [focus, setFocus] = useState(settings.pomoFocus)
  const [rest, setRest] = useState(settings.pomoBreak)

  useEffect(() => {
    pomodoro.configure(settings.pomoFocus, settings.pomoBreak)
  }, [settings.pomoFocus, settings.pomoBreak])

  const first = weekStart(today) - (WEEKS - 1) * 7
  const studiedDays = Object.values(days).filter((d) => d.n > 0).length
  const totalN = Object.values(days).reduce((s, d) => s + d.n, 0)
  const totalOk = Object.values(days).reduce((s, d) => s + d.ok, 0)
  const toNextShield = SHIELD_EVERY - (store.s.streak.count % SHIELD_EVERY)

  const named = (list: ReturnType<typeof weakSpots>) =>
    list.flatMap((w) => { const t = skillTarget(bank, w.id); return t ? [{ ...w, ...t }] : [] })
  const weak = named(weakSpots(store.skills, 4))
  const strong = named(strongSpots(store.skills, 4))
  const train = (t: { subs: number[]; topics: number[] }) => {
    store.setFilter({ ...EMPTY_FILTER, subs: t.subs, topics: t.topics })
    go('practice')
  }
  const todayN = store.todayCount(today)
  const dayGoal = store.dailyGoal()

  const exportBackup = async () => {
    const blob = new Blob([await store.exportAll()], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `waterlearning-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const importBackup = async (f: File | undefined) => {
    if (!f) return
    if (!confirm('Importar este backup substitui todo o progresso salvo neste navegador. Continuar?')) return
    try {
      await store.importAll(await f.text())
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Não consegui ler este arquivo.', '⚠️')
    }
  }

  return (
    <main className="page details">
      <h1>Seu progresso</h1>

      <section className="stats">
        <div className="stat"><span>Tempo líquido de estudo</span><b>{formatHours(store.totalMs())}</b></div>
        <div className="stat"><span>Questões respondidas</span><b className="tabular">{totalN.toLocaleString('pt-BR')}</b></div>
        <div className="stat"><span>Aproveitamento</span><b className="tabular">{totalN ? `${Math.round((totalOk / totalN) * 100)}%` : '–'}</b></div>
        <div className="stat"><span>Dias estudados</span><b className="tabular">{studiedDays}</b></div>
      </section>

      <section>
        <h3>O que você já construiu</h3>
        <ul className="wins">
          <li><b className="tabular">{store.recovered}</b><span>{store.recovered === 1 ? 'questão que você errou e depois acertou' : 'questões que você errou e depois acertou'}</span></li>
          <li><b className="tabular">{totalOk.toLocaleString('pt-BR')}</b><span>acertos somados até aqui</span></li>
          <li><b className="tabular">{todayN}/{dayGoal}</b><span>{todayN >= dayGoal ? 'meta de hoje cumprida' : 'na meta de hoje'}</span></li>
        </ul>
        {strong.length > 0 && (
          <p className="muted">Onde você já vai bem: {strong.map((w) => `${w.name} (${w.pct}%)`).join(', ')}.</p>
        )}
        <p className="muted">Errar e voltar a acertar é a prova mais direta de que você aprendeu, e vale mais do que acertar de primeira.</p>
      </section>

      <section>
        <h3>Onde focar agora</h3>
        {weak.length ? (
          <ul className="focus-list">
            {weak.map((w) => (
              <li key={w.id}>
                <span className="focus-name">{w.name}</span>
                <span className="meter"><i style={{ width: `${w.pct}%` }} /></span>
                <span className="muted tabular">{w.pct}% em {w.n}</span>
                <button className="btn ghost small" onClick={() => train(w)}>Treinar</button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Nenhum ponto fraco à vista. Um assunto entra aqui quando fica abaixo de 65% em pelo menos 6 questões.</p>
        )}
      </section>

      <section>
        <h3>Sequência e escudos</h3>
        <p>
          🔥 <b>{streak.count}</b> {streak.count === 1 ? 'dia seguido' : 'dias seguidos'} · melhor marca: <b>{store.s.streak.best}</b> ·
          escudos: <b>{streak.shieldsLeft}</b> de {MAX_SHIELDS}
        </p>
        <p className="muted">
          A cada {SHIELD_EVERY} dias seguidos você ganha um escudo (até {MAX_SHIELDS}). Se faltar um dia, o escudo cobre a falta e a sequência continua.
          {streak.count > 0 && streak.shieldsLeft < MAX_SHIELDS && ` Faltam ${toNextShield} ${toNextShield === 1 ? 'dia' : 'dias'} para o próximo.`}
        </p>
      </section>

      <section>
        <h3>Dias estudados</h3>
        <div className="heatmap" role="img" aria-label={`Calendário das últimas ${WEEKS} semanas: ${studiedDays} dias com estudo`}>
          {Array.from({ length: WEEKS * 7 }, (_, k) => {
            const day = first + k
            const n = days[day]?.n ?? 0
            const label = `${dayToDate(day).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' })}: ${n} ${n === 1 ? 'questão' : 'questões'}`
            return <i key={day} className={`h${heatLevel(n)} ${day > today ? 'future' : ''} ${day === today ? 'today' : ''}`} title={label} />
          })}
        </div>
        <div className="legend"><span>menos</span>{[0, 1, 2, 3, 4].map((l) => <i key={l} className={`h${l}`} />)}<span>mais</span></div>
      </section>

      <section>
        <h3>Elo por matéria</h3>
        <div className="elos">
          {shown.map((s) => {
            const elo = store.elo(s.id)
            const played = s.id in store.s.elo
            return (
              <div key={s.id} className="elo-card">
                <span>{s.name}</span>
                <b className="tabular">{elo}</b>
                <span className="muted">{played ? tier(elo) : `começa em ${START_ELO}`}</span>
              </div>
            )
          })}
        </div>
        <p className="muted">O Elo sobe mais quando você acerta questões difíceis e desce pouco quando erra questões acima do seu nível.</p>
      </section>

      <section>
        <h3>Domínio por tópico</h3>
        {shown.map((s) => (
          <div key={s.id} className="mastery-group">
            <span className="group-label">{s.name}</span>
            <div className="mastery">
              {s.topics.map((t) => {
                const v = topics[t.id]
                const pct = v && v.n >= MIN_ATTEMPTS ? Math.round((v.ok / v.n) * 100) : null
                return (
                  <div key={t.id} className={`tile m${pct === null ? 0 : masteryLevel(pct)}`}
                    title={v ? `${v.ok} acertos em ${v.n} questões` : 'Ainda sem questões respondidas'}>
                    <span>{t.name}</span>
                    <b className="tabular">{pct === null ? '–' : `${pct}%`}</b>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
        <p className="muted">A porcentagem aparece a partir de {MIN_ATTEMPTS} questões respondidas no tópico.</p>
      </section>

      <section>
        <h3>Histórico de simulados</h3>
        {store.sims.length ? (
          <table className="sims">
            <thead><tr><th>Data</th><th>Simulado</th><th>Acertos</th><th>Tempo</th></tr></thead>
            <tbody>
              {[...store.sims].reverse().map((r) => (
                <tr key={r.ts}>
                  <td>{new Date(r.ts).toLocaleDateString('pt-BR')}</td>
                  <td>{r.exam ? `Oficial · ${r.exam}` : 'Padrão'}</td>
                  <td className="tabular">{r.correct}/{r.total} ({Math.round((r.correct / r.total) * 100)}%)</td>
                  <td className="tabular">{formatClock(r.seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="muted">Nenhum simulado feito ainda.</p>}
      </section>

      <section>
        <h3>Ajustes</h3>
        <div className="settings">
          <label>Meta semanal de questões
            <input type="number" min={10} max={2000} step={10} value={settings.weeklyGoal}
              onChange={(e) => store.setSettings({ weeklyGoal: Math.max(10, Number(e.target.value) || 100) })} />
          </label>
          <label>Pomodoro: foco (min)
            <input type="number" min={5} max={120} value={focus} onChange={(e) => setFocus(Number(e.target.value))}
              onBlur={() => store.setSettings({ pomoFocus: Math.max(5, Math.min(120, focus || 25)) })} />
          </label>
          <label>Pomodoro: pausa (min)
            <input type="number" min={1} max={60} value={rest} onChange={(e) => setRest(Number(e.target.value))}
              onBlur={() => store.setSettings({ pomoBreak: Math.max(1, Math.min(60, rest || 5)) })} />
          </label>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={exportBackup}>Exportar backup</button>
          <button className="btn ghost" onClick={() => file.current?.click()}>Importar backup</button>
          <input ref={file} type="file" accept="application/json" hidden onChange={(e) => importBackup(e.target.files?.[0])} />
        </div>
        <p className="muted">Seu progresso fica salvo só neste navegador. O backup serve para levar a outro aparelho.</p>
      </section>
    </main>
  )
}
