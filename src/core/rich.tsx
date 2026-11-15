import katex from 'katex'
import { memo } from 'react'

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const asset = (p: string) => (/^(https?:)?\/\//.test(p) || p.startsWith('/') ? p : `${import.meta.env.BASE_URL}${p}`)

function math(tex: string, display: boolean): string {
  try {
    // vírgula decimal: no TeX a vírgula é pontuação e ganha espaço ("0, 5"); entre chaves vira dígito
    // ...menos em ponto e intervalo, "P(2,2)" e "[1,2]", a não ser que venha expoente: "(1,05)^2" é decimal
    tex = tex
      .replace(/([([]\s*-?\d+),(\d+\s*[)\]])(?!\s*\^)/g, '$1\u0000$2')
      .replace(/(\d),(?=\d)/g, '$1{,}')
      .replace(/\u0000/g, ',')
    return katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: false })
  } catch {
    return esc(tex)
  }
}

/**
 * Markdown enxuto + KaTeX. Fórmulas usam \( \) e \[ \] (ou $$ $$): o cifrão simples fica livre
 * para valores em reais, que aparecem o tempo todo nos enunciados.
 */
export function renderRich(src: string): string {
  const stash: string[] = []
  const keep = (html: string) => `\u0000${stash.push(html) - 1}\u0000`
  let text = src
    .replace(/\\\[([\s\S]+?)\\\]|\$\$([\s\S]+?)\$\$/g, (_, a, b) => keep(math(a ?? b, true)))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, a) => keep(math(a, false)))
    .replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, (_, alt, url) =>
      keep(`<img src="${esc(asset(url))}" alt="${esc(alt || 'Figura da questão')}" loading="lazy" />`))
  text = esc(text)
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/gm, '$1<em>$2</em>')
    .replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,;:!?]|$)/gm, '$1<em>$2</em>')
    .replace(/^#{1,6}\s+(.+)$/gm, '<strong>$1</strong>')
  const html = text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${p.replace(/\n/g, '<br />')}</p>`)
    .join('')
  return html.replace(/\u0000(\d+)\u0000/g, (_, i) => stash[Number(i)])
}

export const Rich = memo(function Rich({ text, className }: { text: string; className?: string }) {
  return <div className={`rich ${className ?? ''}`} dangerouslySetInnerHTML={{ __html: renderRich(text) }} />
})
