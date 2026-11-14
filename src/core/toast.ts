import { useSyncExternalStore } from 'react'

export interface Toast {
  id: number
  text: string
  icon?: string
}

let toasts: Toast[] = []
let seq = 0
const listeners = new Set<() => void>()

function set(next: Toast[]) {
  toasts = next
  for (const fn of listeners) fn()
}

export function toast(text: string, icon?: string, ms = 4200): void {
  const id = ++seq
  set([...toasts, { id, text, icon }])
  setTimeout(() => set(toasts.filter((t) => t.id !== id)), ms)
}

export function useToasts(): Toast[] {
  return useSyncExternalStore((fn) => {
    listeners.add(fn)
    return () => void listeners.delete(fn)
  }, () => toasts)
}
