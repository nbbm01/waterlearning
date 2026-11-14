import { useSyncExternalStore } from 'react'
import { sounds } from './sounds'

export interface Pomo {
  phase: 'focus' | 'break'
  running: boolean
  left: number // segundos
  done: number // blocos de foco concluídos hoje nesta sessão
}

let state: Pomo = { phase: 'focus', running: false, left: 25 * 60, done: 0 }
let minutes = { focus: 25, break: 5 }
let timer: ReturnType<typeof setInterval> | null = null
let endsAt = 0
const listeners = new Set<() => void>()

function set(next: Pomo) {
  state = next
  for (const fn of listeners) fn()
}

function tick() {
  const left = Math.max(0, Math.round((endsAt - Date.now()) / 1000))
  if (left > 0) return set({ ...state, left })
  sounds.bell()
  const phase = state.phase === 'focus' ? 'break' : 'focus'
  const total = minutes[phase] * 60
  endsAt = Date.now() + total * 1000
  set({ phase, running: true, left: total, done: state.done + (state.phase === 'focus' ? 1 : 0) })
}

export const pomodoro = {
  subscribe(fn: () => void) {
    listeners.add(fn)
    return () => void listeners.delete(fn)
  },
  get: () => state,
  configure(focus: number, rest: number) {
    minutes = { focus, break: rest }
    if (!state.running) set({ ...state, left: minutes[state.phase] * 60 })
  },
  toggle() {
    if (state.running) {
      if (timer) clearInterval(timer)
      timer = null
      return set({ ...state, running: false })
    }
    endsAt = Date.now() + state.left * 1000
    timer = setInterval(tick, 500)
    set({ ...state, running: true })
  },
  reset() {
    if (timer) clearInterval(timer)
    timer = null
    set({ phase: 'focus', running: false, left: minutes.focus * 60, done: state.done })
  },
}

export function usePomodoro(): Pomo {
  return useSyncExternalStore(pomodoro.subscribe, pomodoro.get)
}
