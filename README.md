# keeper-wiki-bkd

API de leitura que serve o dado do **Graveyard Keeper** para a wiki
[`keeper-wiki-fnd`](../keeper-wiki-fnd/). Python + FastAPI em container, sobre
o Postgres do [`keeper-wiki-db`](../keeper-wiki-db/).

O dado vem do binário do jogo: quem extrai é o
[`reveng-graveyard-keeper`](../reveng-graveyard-keeper/), e **a extração
continua lá**. Este repositório só carrega o resultado no banco e o serve.

```
reveng-graveyard-keeper        keeper-wiki-bkd              keeper-wiki-fnd
   (binário do jogo)    ──▶   importa.py ─▶ Postgres ─▶ API ──▶ build estático
   out/data/wiki/*.json        (escreve)     (gk.*)   (só lê)    (nginx)
```

## Subindo

O banco vem primeiro: é o compose dele que cria a rede `keeper-wiki`.

```sh
cd ../keeper-wiki-db && docker compose up -d     # Postgres + papéis de leitura
cd ../keeper-wiki-bkd
cp .env.example .env                             # preencha com as senhas do ../keeper-wiki-db/.env
./scripts/aplica-schema.sh                       # cria o schema gk
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
set -a; source .env; set +a
./.venv/bin/python scripts/importa.py            # carrega o dado do reveng
docker compose up -d --build api                 # API em http://127.0.0.1:8000
```

Documentação interativa das rotas em <http://127.0.0.1:8000/docs>.

```sh
docker compose --profile dev up dev              # reload a cada salvamento
docker compose logs -f api
```

## Rotas

| Rota | O que devolve |
|---|---|
| `GET /saude` | a API responde e o banco está acessível |
| `GET /meta` | de qual extração veio o dado que está no ar |
| `GET /itens` | lista com busca sem acento (`busca`, `tipo`, `incluir_nao_usados`) |
| `GET /itens/{id}` | um item |
| `GET /itens/{id}/receitas` | receitas que produzem e que consomem o item |
| `GET /receitas` | lista (`busca`, `origem`, `estacao`, `item`, `incluir_ocultas`) |
| `GET /receitas/{id}` | receita com entradas, saídas e estações |
| `GET /estacoes` | estações de trabalho e quantas receitas cada uma tem |
| `GET /tecnologias` | árvore de pesquisa (`busca`, `ramo`) |
| `GET /tecnologias/{id}` | uma tecnologia |

As listagens devolvem `{total, limite, offset, dados}`. `limite` vai até 500.

Não existe rota de escrita: a API inteira é `GET`.

## Somente leitura, de verdade

São três credenciais, e só uma escreve:

| Papel | Quem usa | Pode |
|---|---|---|
| `keeper_api` | a API | `SELECT` no schema `gk`, e nada fora dele |
| `keeper_claude` | `scripts/consulta.sh`, o Claude Code | `SELECT`, com timeout de 15s |
| dono do banco | `aplica-schema.sh` e `importa.py` | tudo |

Os dois primeiros não têm `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` nem `CREATE`
em lugar nenhum, e ainda abrem toda sessão com `default_transaction_read_only`.
Forçar `set transaction_read_only = off` não ajuda: cai em `permission denied`,
porque o `GRANT` de escrita nunca existiu. Os papéis nascem em
[`../keeper-wiki-db/init/002-papeis.sh`](../keeper-wiki-db/init/002-papeis.sh).

Para consultar o banco:

```sh
./scripts/consulta.sh "select pt, preco_base from gk.item where id = 'wooden_plank'"
```

## Recarregar o dado

Quando o jogo for atualizado e o `reveng-graveyard-keeper` reextrair:

```sh
set -a; source .env; set +a
./.venv/bin/python scripts/importa.py            # --wiki aponta outra pasta
```

A carga é uma transação só: ou entra tudo, ou o banco fica como estava. Cada
rodada deixa uma linha em `gk.importacao`, que é o que o `GET /meta` devolve.

## Estrutura

```
app/            a API
  main.py       aplicação, CORS, ciclo de vida do pool
  config.py     configuração vinda do ambiente
  db.py         pool asyncpg
  consultas.py  todo o SQL, em um lugar só
  modelos.py    formato das respostas
  rotas/        uma rota por assunto
db/             schema e permissões (SQL versionado, aplicado em ordem)
scripts/        aplica-schema.sh, importa.py, consulta.sh
```
