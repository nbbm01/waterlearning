#!/usr/bin/env bash
# Laço diário: gasta a cota do dia da API das Questões em matérias de concurso (Português, Raciocínio Lógico,
# Informática, Direito...), importa e reconstrói o banco. Retoma de onde parou; rodar duas vezes no mesmo dia não gasta nada.
#
# Para rodar sozinho todo dia (systemd do usuário):
#   systemd-run --user --on-calendar='*-*-* 07:00' --unit=waterlearning-crescer "$PWD/scripts/crescer.sh"
# ou no crontab:  0 7 * * *  /caminho/para/waterlearning/scripts/crescer.sh >> /tmp/waterlearning-crescer.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
# questão real primeiro: Química de vestibulares (FUVEST, UNICAMP, UERJ, EsPCEx...), que é a matéria mais fina do banco;
# o que sobrar da cota vai para o rodízio das matérias de concurso. Cota acabada não é erro: o laço só para.
python3 pipeline/sources/qdq_fetch.py fetch 300 - qui || true
python3 pipeline/sources/qdq_fetch.py amplo || true
python3 pipeline/sources/qdq.py
bun run data
