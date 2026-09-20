# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Leia o `README.md` antes de mexer em qualquer coisa** — ele tem o desenho, as
rotas e o passo a passo de subir tudo.

## O que este projeto é

API de leitura em **Python 3.13 + FastAPI + asyncpg**, em container, que serve o
dado do **Graveyard Keeper** para a wiki em `../keeper-wiki-fnd/`. O dado mora no
Postgres de `../keeper-wiki-db/` e vem do binário do jogo, extraído em
`../reveng-graveyard-keeper/`.

**A extração fica no `reveng-graveyard-keeper`, não aqui.** Se faltar um campo,
a correção é lá: mexa no `catalogo.py`, regere `out/data/wiki/*.json` e rode
`scripts/importa.py`. Não invente o dado no meio do caminho.

Tudo em português (pt-BR), inclusive comentários, nomes de rota e de coluna.

## Comandos

```sh
./scripts/aplica-schema.sh                     # cria/atualiza o schema gk
./.venv/bin/python scripts/importa.py          # carrega o dado do reveng
./scripts/consulta.sh "select ..."             # psql somente leitura
docker compose up -d --build api               # API em 127.0.0.1:8000 (/docs)
docker compose --profile dev up dev            # reload a cada salvamento
```

`scripts/importa.py` e `aplica-schema.sh` precisam de `set -a; source .env; set +a`
ou das variáveis já no ambiente.

## Para consultar o banco, use a skill `banco`

Qualquer dado do jogo — nome em pt-BR, quantidade de ingrediente, custo de
tecnologia, o que uma estação fabrica — sai de uma consulta, não de palpite nem
de leitura dos JSON na mão. Carregue `.claude/skills/banco/SKILL.md`: ela tem o
mapa do schema, as pegadinhas e as consultas prontas.

## Regras

- **A API não escreve. Ponto.** Toda rota é `GET`, e `keeper_api` só tem `SELECT`
  no schema `gk`. Se alguma vez for preciso escrever, isso é decisão de produto,
  não detalhe de implementação: pergunte antes.
- **Três credenciais, uma escreve.** `DATABASE_URL`/`DATABASE_URL_DOCKER` é a da
  API, `DATABASE_URL_LEITURA` é a do `consulta.sh`, e `DATABASE_URL_DONO` é do
  dono do banco, usada só por `aplica-schema.sh` e `importa.py`. Nunca troque
  uma pela outra "para testar".
- **`.env` nunca entra no git.** Ele tem as senhas dos papéis.
- **Nada de FK contra `gk.item` em referência de receita.** 95 referências não
  são item (`b_faith`, `b_empty:1`, `book:book_hard`), e estação e objeto
  construído são objetos de mundo. É `LEFT JOIN`, sempre.
- **Número de receita pode não ser número.** `tempo_s` e `energia` ficam NULL
  quando o jogo usa SmartExpression; a fórmula está em `tempo_expr`/`energia_expr`.
- **Filtre `nao_usado` e `oculta`** em tudo que o jogador vai ver. O padrão das
  rotas já filtra; não remova sem motivo.
- **Todo SQL vive em `app/consultas.py`**, parametrizado com `$n`. Filtro
  opcional se resolve com `$n IS NULL OR ...`, nunca concatenando string.
- **Mudou o schema?** O arquivo em `db/` e o SQL de `app/consultas.py` mudam no
  mesmo commit, e `scripts/importa.py` roda de novo para provar que a carga
  ainda passa.
- **Contagem é teste.** Depois de importar têm que sair 1.157 itens, 2.634
  receitas e 187 tecnologias. Número diferente sem o jogo ter sido atualizado é
  importação torta — pare e investigue.

## O front consome no build

A `keeper-wiki-fnd` usa `adapter-static`: as páginas são pré-renderizadas. A
ideia é o prerender buscar desta API na hora do build, então **o site não
depende da API no ar** e o `CORS_ORIGENS` fica vazio. Se um dia alguma página
passar a buscar no navegador, aí sim preencha `CORS_ORIGENS` — e diga isso no
commit, porque muda o que precisa estar de pé em produção.

## Commits

Use a skill do projeto `.claude/skills/commit` para qualquer commit: Conventional
Commits (Angular) em pt-BR, com os termos técnicos em inglês — a mesma convenção
da `keeper-wiki-fnd` e da `reveng-graveyard-keeper`. **Nunca coloque o Claude
como coautor nem cite IA na mensagem** (sem `Co-Authored-By: Claude`, sem
"Generated with Claude Code").
