#!/usr/bin/env bash
# Cria/atualiza o schema gk e as permissões de leitura.
#
#     ./scripts/aplica-schema.sh
#
# Usa DATABASE_URL_DONO (o dono do banco) do .env — é a única credencial do
# projeto que escreve. A API e a skill do Claude nunca a usam.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] && set -a && source .env && set +a

: "${DATABASE_URL_DONO:?defina DATABASE_URL_DONO no .env}"

for arquivo in db/0*.sql; do
  echo "→ $arquivo"
  psql "$DATABASE_URL_DONO" -v ON_ERROR_STOP=1 --quiet -f "$arquivo"
done
echo "schema gk pronto"
