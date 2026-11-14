/// <reference types="vitest/config" />
import { createReadStream, existsSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { join, normalize } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type Connect, type Plugin } from 'vite'

// Serve os PDFs de ~/Downloads/conteudo em /livros/ (só local; não entram no build).
const BOOKS = join(homedir(), 'Downloads', 'conteudo')
const serveBooks: Connect.NextHandleFunction = (req, res, next) => {
  if (!req.url?.startsWith('/livros/')) return next()
  const name = decodeURIComponent(req.url.slice('/livros/'.length).split(/[?#]/)[0])
  const file = normalize(join(BOOKS, name))
  if (!file.startsWith(BOOKS) || !existsSync(file) || !statSync(file).isFile()) {
    res.statusCode = 404
    return res.end('Livro não encontrado')
  }
  res.setHeader('Content-Type', 'application/pdf')
  res.setHeader('Content-Length', statSync(file).size)
  createReadStream(file).pipe(res)
}
// Em dev, /data sai direto do disco: o pipeline reescreve esses arquivos com o servidor no ar
// e a lista de arquivos públicos que o Vite guarda em memória fica desatualizada.
const DATA = join(import.meta.dirname, 'public', 'data')
const serveData: Connect.NextHandleFunction = (req, res, next) => {
  if (!req.url?.startsWith('/data/')) return next()
  const file = normalize(join(DATA, decodeURIComponent(req.url.slice('/data/'.length).split(/[?#]/)[0])))
  if (!file.startsWith(DATA) || !existsSync(file) || !statSync(file).isFile()) {
    res.statusCode = 404
    return res.end()
  }
  const types: Record<string, string> = { json: 'application/json', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp', svg: 'image/svg+xml', gif: 'image/gif' }
  res.setHeader('Content-Type', types[file.split('.').pop()!.toLowerCase()] ?? 'application/octet-stream')
  res.setHeader('Cache-Control', 'no-cache')
  createReadStream(file).pipe(res)
}

const books = (): Plugin => ({
  name: 'livros-locais',
  configureServer: (s) => {
    s.middlewares.use(serveData)
    s.middlewares.use(serveBooks)
  },
  configurePreviewServer: (s) => void s.middlewares.use(serveBooks),
})

export default defineConfig({
  plugins: [react(), books()],
  test: { environment: 'node' },
})
