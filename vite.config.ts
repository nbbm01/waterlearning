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
const books = (): Plugin => ({
  name: 'livros-locais',
  configureServer: (s) => void s.middlewares.use(serveBooks),
  configurePreviewServer: (s) => void s.middlewares.use(serveBooks),
})

export default defineConfig({
  plugins: [react(), books()],
  test: { environment: 'node' },
})
