// Renderiza todo texto do banco com o mesmo código do site e aponta fórmulas quebradas.
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { renderRich } from '../src/core/rich.tsx'

const dir = join(import.meta.dir, '..', 'public', 'data', 'chunks')
const bad: Record<string, string[]> = {}
let fields = 0
for (const f of readdirSync(dir)) {
  const chunk = JSON.parse(readFileSync(join(dir, f), 'utf8')) as Record<string, { stem?: string; opts: { t: string }[]; exp?: string }>
  for (const [id, q] of Object.entries(chunk)) {
    for (const text of [q.stem ?? '', q.exp ?? '', ...q.opts.map((o) => o.t)]) {
      if (!text) continue
      fields++
      const html = renderRich(text)
      const problems = []
      if (html.includes('katex-error')) problems.push('katex-error')
      if (/\\\(|\\\)/.test(html.replace(/<[^>]+>/g, ''))) problems.push('delimitador sobrando')
      if (/(^|[^\\a-z])(dfrac|frac|sqrt)\{/.test(text.replace(/\\(dfrac|frac|sqrt)/g, ''))) problems.push('comando sem barra')
      if (problems.length) (bad[id.split('-')[0]] ??= []).push(`${id}: ${problems.join(', ')} :: ${text.slice(0, 90)}`)
    }
  }
}
console.log(`${fields} textos renderizados`)
// quarentena: questão com fórmula quebrada não chega ao aluno (o build lê este arquivo)
const ids = Object.values(bad).flat().map((l) => l.split(':')[0])
const qfile = join(import.meta.dir, 'quarantine.json')
const previous: string[] = (() => { try { return JSON.parse(readFileSync(qfile, 'utf8')) } catch { return [] } })()
writeFileSync(qfile, JSON.stringify([...new Set([...previous, ...ids])].sort(), null, 1))
console.log(`quarentena: ${new Set([...previous, ...ids]).size} questões`)
for (const [src, list] of Object.entries(bad)) {
  console.log(`${src}: ${list.length} com problema`)
  for (const l of list.slice(0, 4)) console.log('   ', l)
}
