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
| `GET /icones` | nomes dos sprites (`{total, dados}`, sem paginação) |
| `GET /icones/{nome}.png` | o PNG do sprite (`image/png`, cache público; 404 se não existir) |
| `GET /itens` | lista (com `icone`, `estrela`, `grupo`, `pode_usar`, `ao_usar`, `dlc`) com busca sem acento (`busca`, `tipo`, `incluir_nao_usados`, `dlc`) |
| `GET /itens/{id}` | um item |
| `GET /itens/{id}/receitas` | receitas (completas) que produzem e que consomem o item |
| `GET /grupos` | itens com níveis de qualidade, um por grupo (`incluir_nao_usados`, `dlc`) |
| `GET /grupos/{id}` | o grupo com os níveis (`itens`), do mais baixo ao mais alto |
| `GET /grupos/{id}/receitas` | `{produzem, consomem}` do grupo e de todos os seus níveis |
| `GET /receitas` | lista (`busca`, `origem`, `estacao`, `item`, `incluir_ocultas`, `dlc`) |
| `GET /receitas/{id}` | receita com entradas, saídas e estações |
| `GET /estacoes` | estações de trabalho e quantas receitas cada uma tem (`dlc`) |
| `GET /tecnologias` | árvore de pesquisa (`busca`, `ramo`, `incluir_ocultas` — padrão `true`, `dlc`) |
| `GET /tecnologias/{id}` | uma tecnologia |
| `GET /dlcs` | as quatro DLCs, na ordem do jogo, com quantas tecnologias, receitas, estações e itens são de cada uma |

Os ícones são arquivos, não banco: vêm de `../reveng-graveyard-keeper/out/gk1/icones/`, montada em `/icones` (somente leitura) pelo `compose.yaml`; `ICONES_DIR` muda o caminho.

As listagens devolvem `{total, limite, offset, dados}`. `limite` vai até 500.

Tecnologia, receita (e a estação dentro dela), estação, item e grupo trazem
`dlc`: `"breaking_dead"`, `"stranger_sins"`, `"game_of_crone"`,
`"better_save_soul"` ou `null` (jogo base). O filtro `?dlc=` das listagens
aceita um desses ids ou `base` (= `dlc` null); outro valor é 422.

`/tecnologias` traz as ocultas por padrão: em tecnologia, `oculta` quer dizer
"começa escondida" (`hidden`/`invisible` no `TechDefinition`), e o jogo as
revela durante a partida (`GameSave.RevealHiddenTech`, `Flow_RevealTech`) —
"Iron" é uma delas, e quase todas as de DLC também. `incluir_ocultas=false`
devolve a lista antiga, só com as visíveis desde o começo.

## De qual DLC é cada coisa

O jogo só marca DLC na tecnologia (`TechDefinition.requires_dlc`, enum
`DLCEngine.DLCVersion`: 1 Breaking Dead, 2 Stranger Sins, 3 Game of Crone,
4 Better Save Soul). Receita, estação e item não têm campo nenhum, então a API
**deduz**. A regra está em [`db/015-dlc.sql`](db/015-dlc.sql), numa visão
materializada (`gk.dlc_de`) que o `importa.py` recalcula a cada carga. Na
dúvida, o resultado é `null`: marcar errado é pior que não marcar.

1. **Tecnologia.** (a) `requer_dlc`, direto. (b) Senão, se toda receita com
   estação que ela libera é feita só em mesas de construção de zona da mesma
   DLC (ver 3a). (c) Senão, herda dos pré-requisitos: sobe a árvore parando em
   quem tem DLC por (a)/(b); se todo ponto de parada (tecnologia de DLC ou raiz
   sem pré-requisito) é da mesma DLC, a tecnologia é dela. É assim que o ramo 8
   (Espiritualismo), que o jogo não marca, sai Better Save Soul: a raiz
   `soul_sins_1` só libera construções da `souls_builddesk`.
2. **Receita pela tecnologia.** Toda tecnologia que a libera é da mesma DLC.
3. **Estação**, na ordem, a primeira que decidir:
   (a) é uma das cinco mesas de construção cujo `zone_id` (em `objs_data`) é
   uma zona de DLC — `zombie_sawmill_builddesk` (Breaking Dead),
   `players_tavern_builddesk` e `players_tavern_cellar_builddesk` (Stranger
   Sins), `refugee_builddesk` (Game of Crone), `souls_builddesk` (Better Save
   Soul);
   (b) toda construção que a ergue ou melhora (`objeto_id` = id ou `id_place`;
   demolir não conta) é da mesma DLC, pela mesa (3a) ou pela tecnologia (2);
   (c) toda receita feita nela é de DLC pela tecnologia (2), a mesma;
   (d) último recurso, para o que já vem posto no mapa e nada no dado liga a
   uma mesa: o prefixo do id — `zombie` como palavra (Breaking Dead),
   `tavern_`/`players_tavern_` (Stranger Sins; a taberna do vilarejo não tem
   estação), `refugee_` (Game of Crone), `soul_`/`souls_` (Better Save Soul).
4. **Receita.** É da DLC que qualquer uma destas apontar, desde que não
   apontem DLCs diferentes (aí fica `null`): a tecnologia (2); toda estação
   onde ela é feita; ou o objeto que ela constrói/demole ser estação de DLC.
5. **Item.** Existe receita que o produz, **todas** as que o produzem são da
   mesma DLC, **e** nenhuma receita de fora dessa DLC o consome (nem pelo id
   do item, nem pelo do grupo). A segunda condição existe porque receita não é
   a única fonte de item — carvão, minério, uva e lúpulo também caem de objeto
   do mundo, e isso não está no banco. Item sem receita que o produza é `null`.
6. **Grupo.** Todos os níveis são da mesma DLC.

O que ficou `null` sabendo que talvez não seja base: estações postas no mapa
sem prefixo (`rat_cell`, `eurics_room_*`, `contraband_box`, `elevator_top`,
`mf_crematorium_corp`/`_burning`) e itens que o jogo base consome (`butter`,
`cheese`). Resolver de vez pede a zona de cada objeto do mapa, que está na cena
do jogo e não em `objs_data`: é extração, no `reveng-graveyard-keeper`.

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
./.venv/bin/python scripts/importa.py            # --wiki aponta outra pasta; o padrão é `out/gk1/data/wiki`
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
