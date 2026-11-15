#!/usr/bin/env bash
# Publica o site no GitHub Pages: gera o build na subpasta do repositório e envia para o branch gh-pages.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$(git remote get-url origin)
NAME=$(basename "$REPO" .git)
bunx tsc --noEmit
bunx vite build --base="/$NAME/"
touch dist/.nojekyll
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export GIT_DIR="$TMP/pages.git" GIT_WORK_TREE="$PWD/dist"
git init -q -b gh-pages
git add -A
git commit -qm "Publica site ($(date +%F))"
git push -qf "$REPO" gh-pages
echo "Publicado no branch gh-pages de $REPO"
