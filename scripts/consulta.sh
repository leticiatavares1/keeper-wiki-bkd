#!/usr/bin/env bash
# psql somente leitura. É por aqui que o Claude Code consulta o banco
# (ver .claude/skills/banco/SKILL.md).
#
#     ./scripts/consulta.sh "select count(*) from gk.item"
#     ./scripts/consulta.sh -f consulta.sql
#     ./scripts/consulta.sh                 # console interativo
#
# Conecta como keeper_claude, que só tem SELECT. Além disso a sessão já abre
# com default_transaction_read_only e statement_timeout curto: uma escrita
# falha aqui por falta de permissão, não por gentileza do script.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] && set -a && source .env && set +a

: "${DATABASE_URL_LEITURA:?defina DATABASE_URL_LEITURA no .env}"

export PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=15s'

if [[ $# -eq 0 ]]; then
  exec psql "$DATABASE_URL_LEITURA"
elif [[ $1 == -* ]]; then
  exec psql "$DATABASE_URL_LEITURA" -v ON_ERROR_STOP=1 "$@"
else
  exec psql "$DATABASE_URL_LEITURA" -v ON_ERROR_STOP=1 --pset pager=off -c "$1"
fi
