/** Sons sintetizados na hora (sem arquivos). Só há sons de recompensa: errar é silencioso. */
let ctx: AudioContext | null = null
let enabled = true

export function setSoundEnabled(on: boolean): void {
  enabled = on
}

function audio(): AudioContext | null {
  if (!enabled || typeof AudioContext === 'undefined') return null
  ctx ??= new AudioContext()
  if (ctx.state === 'suspended') void ctx.resume()
  return ctx
}

interface Note {
  freq: number
  at?: number
  dur?: number
  gain?: number
  type?: OscillatorType
}

/** Uma nota com ataque rápido e cauda suave, mais um harmônico leve para soar como kalimba. */
function pluck(ac: AudioContext, out: AudioNode, { freq, at = 0, dur = 0.5, gain = 0.16, type = 'sine' }: Note): void {
  const t = ac.currentTime + at
  for (const [mult, level] of [[1, 1], [2, 0.28], [3.01, 0.08]] as const) {
    const osc = ac.createOscillator()
    const g = ac.createGain()
    osc.type = type
    osc.frequency.setValueAtTime(freq * mult, t)
    g.gain.setValueAtTime(0, t)
    g.gain.linearRampToValueAtTime(gain * level, t + 0.008)
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur / mult)
    osc.connect(g).connect(out)
    osc.start(t)
    osc.stop(t + dur + 0.05)
  }
}

function play(notes: Note[]): void {
  const ac = audio()
  if (!ac) return
  // eco curto dá sensação de espaço, como gota em água
  const dry = ac.createGain()
  const delay = ac.createDelay()
  const wet = ac.createGain()
  delay.delayTime.value = 0.19
  wet.gain.value = 0.22
  dry.connect(ac.destination)
  dry.connect(delay).connect(wet).connect(ac.destination)
  for (const n of notes) pluck(ac, dry, n)
}

// pentatônica maior: qualquer sequência soa bem
const SCALE = [523.25, 587.33, 659.25, 783.99, 880, 1046.5, 1174.66, 1318.51, 1567.98, 1760]

export const sounds = {
  /** Clique discreto ao marcar uma alternativa. */
  select() {
    play([{ freq: 392, dur: 0.07, gain: 0.05, type: 'triangle' }])
  },
  /** Acerto: duas notas que sobem na escala a cada acerto seguido. */
  correct(combo: number) {
    const i = Math.min(Math.max(combo - 1, 0), SCALE.length - 3)
    play([{ freq: SCALE[i] }, { freq: SCALE[i + 2], at: 0.09, dur: 0.6 }])
  },
  /** Marco de acertos seguidos (3, 5, 10...). */
  combo() {
    play([0, 2, 4, 5, 7].map((s, k) => ({ freq: SCALE[s], at: k * 0.07, dur: 0.7, gain: 0.13 })))
  },
  /** Subiu de nível no modo progressivo. */
  levelUp() {
    play([{ freq: 392, dur: 0.5 }, { freq: 523.25, at: 0.1 }, { freq: 659.25, at: 0.2 }, { freq: 1046.5, at: 0.32, dur: 0.9 }])
  },
  /** Primeiro estudo do dia / sequência de dias. */
  streak() {
    play([5, 7, 9, 7, 9].map((s, k) => ({ freq: SCALE[s], at: k * 0.085, dur: 0.8, gain: 0.1 })))
  },
  /** Sino calmo: fim de bloco do Pomodoro ou do simulado. */
  bell() {
    play([{ freq: 440, dur: 1.8, gain: 0.14 }, { freq: 659.25, dur: 1.6, gain: 0.08 }, { freq: 880, at: 0.5, dur: 1.6, gain: 0.07 }])
  },
  /** Gota: revisão concluída. */
  drop() {
    const ac = audio()
    if (!ac) return
    const osc = ac.createOscillator()
    const g = ac.createGain()
    const t = ac.currentTime
    osc.frequency.setValueAtTime(1400, t)
    osc.frequency.exponentialRampToValueAtTime(520, t + 0.14)
    g.gain.setValueAtTime(0.15, t)
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.25)
    osc.connect(g).connect(ac.destination)
    osc.start(t)
    osc.stop(t + 0.3)
  },
}
