export const F_COMMENTED = 1
export const F_CLASSIC = 2
export const F_MILITARY = 4
export const F_IMAGE = 8
export const F_DEEP = 16

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
  k: number // trilhas a que pertence (bit i = meta.tracks[i])
}

export interface Option {
  t: string
  img?: string
  why?: string // alternativa errada: o erro que costuma levar a ela
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

/** bancas agrupadas para o filtro: ENEM, Vestibulares, Militares, Concursos... */
export interface ExamGroup {
  id: string
  name: string
  exams: number[]
}

/** objetivo do aluno: recorta o banco antes de qualquer filtro */
export interface Track {
  id: string
  name: string
  desc: string
}

export interface Meta {
  version: string
  subjects: Subject[]
  exams: string[]
  military: string[]
  total: number
  theory: Record<string, TheoryCard>
  sims: Record<string, SimSpec>
  groups: ExamGroup[]
  tracks: Track[]
  examInfo: Record<string, string>
}

/** trilha que não recorta nada */
export const ALL_TRACK = 'tudo'

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
  deep: boolean
}

export const EMPTY_FILTER: Filter = {
  subjects: [], exams: [], topics: [], subs: [], yearMin: 0, yearMax: 0, diff: 'prog',
  pending: false, unseen: false, classic: false, military: false, commented: false, deep: false,
}

export const DIFF_LABEL = ['', 'Fácil', 'Médio', 'Difícil'] as const
/** o que cada nível é, na lógica de um livro: fixação → aplicação → desafio */
export const STAGE = { 1: 'Fixação', 2: 'Aplicação', 3: 'Desafio' } as const
