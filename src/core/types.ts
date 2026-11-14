export const F_COMMENTED = 1
export const F_CLASSIC = 2
export const F_MILITARY = 4
export const F_IMAGE = 8

/** Linha compacta do índice: tudo que os filtros precisam, sem o conteúdo. */
export interface Row {
  id: string
  s: number // matéria
  e: number // banca
  y: number // ano (0 = desconhecido)
  t: number // tópico (índice global)
  d: 1 | 2 | 3
  f: number // flags
  c: number // bloco de conteúdo
  r: number // Elo da questão
  u: number // subtópico (índice global, -1 = sem)
}

export interface Option {
  t: string
  img?: string
}

export interface Question {
  k: 'text' | 'image'
  stem?: string
  opts: Option[]
  n?: number // nº de alternativas (questões em recorte)
  imgs?: string[]
  ans: number
  exp?: string
  src?: string
  book?: { file: string; page: number }
}

export interface Sub {
  id: string
  name: string
  aliases: string[]
}

export interface Topic {
  id: string
  name: string
  aliases: string[]
  subs: Sub[]
}

export interface Subject {
  id: string
  name: string
  topics: Topic[]
}

export interface TheoryCard {
  title: string
  body: string
  ref?: { label: string; file?: string; page?: number }
}

export interface SimSpec {
  name: string
  minutesPerQuestion: number
  format: string
  cutoff?: { percent: number; note: string; source: string }
}

export interface Meta {
  version: string
  subjects: Subject[]
  exams: string[]
  military: string[]
  total: number
  theory: Record<string, TheoryCard>
  sims: Record<string, SimSpec>
}

export type Difficulty = 0 | 1 | 2 | 3 | 'prog'

export interface Filter {
  subjects: number[]
  exams: number[]
  topics: number[]
  subs: number[]
  yearMin: number
  yearMax: number
  diff: Difficulty
  pending: boolean
  unseen: boolean
  classic: boolean
  military: boolean
  commented: boolean
}

export const EMPTY_FILTER: Filter = {
  subjects: [], exams: [], topics: [], subs: [], yearMin: 0, yearMax: 0, diff: 'prog',
  pending: false, unseen: false, classic: false, military: false, commented: false,
}

export const DIFF_LABEL = ['', 'Fácil', 'Médio', 'Difícil'] as const
