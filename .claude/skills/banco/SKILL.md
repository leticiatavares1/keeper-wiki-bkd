---
name: banco
description: Consulta o Postgres da wiki (schema gk — itens, receitas, tecnologias e estações do Graveyard Keeper) em modo SOMENTE LEITURA, pelo scripts/consulta.sh. Use SEMPRE que precisar de um dado do jogo — número, nome oficial em pt-BR, ingrediente, tempo, custo de tecnologia, o que uma estação fabrica, quantos itens existem — em vez de chutar, de abrir os JSON do reveng na mão ou de montar uma conexão própria. Use também antes de escrever qualquer rota nova da API.
---

# Consultar o banco da wiki

O dado do Graveyard Keeper está no schema `gk` do Postgres que roda em
`../keeper-wiki-db`. Ele veio do binário do jogo, não da wiki do fandom: é a
fonte boa para qualquer número que for parar no site.

## Regra única: só pelo `scripts/consulta.sh`

```sh
./scripts/consulta.sh "select pt, en, preco_base from gk.item where id = 'wooden_plank'"
./scripts/consulta.sh -f /tmp/consulta.sql        # consulta longa
./scripts/consulta.sh                             # console psql interativo
```

O script conecta como `keeper_claude`, um papel que **só tem SELECT**. Isso não
é convenção, é permissão no servidor: `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`,
`CREATE` e `DROP` são recusados pelo Postgres, e a sessão ainda abre com
`default_transaction_read_only = on` e `statement_timeout = 15s`.

**Nunca** use `DATABASE_URL_DONO`, `psql -U porti`, `docker exec ... psql` nem
qualquer outra credencial para ler. Existe uma porta de entrada só.

**Escrever no banco não é trabalho de consulta.** Mudança de schema vai em
`db/0*.sql` e entra com `./scripts/aplica-schema.sh`; recarga de dado é
`./scripts/importa.py`. Os dois exigem a credencial do dono, e você avisa o
usuário antes de rodar qualquer um.

## O que tem lá dentro

Quantidades de hoje: 1.157 itens, 2.634 receitas, 187 tecnologias, 228 estações.

### `gk.item` — os itens

`id` (pk, id do jogo) · `pt` `en` (tradução oficial; **NULL** quando o item não
tem entrada na localização — 212 casos) · `descricao_pt` `descricao_en` ·
`tipo` · `preco_base` `qualidade` `eficiencia` (numeric) · `pilha` (int) ·
`tem_durabilidade` `nao_usado` (bool) · `tipos_de_produto` (text[]) ·
`busca` (coluna gerada: pt + en + id, sem acento e em minúscula).

- `nao_usado = true` é item que existe no balanceamento mas não aparece no
  jogo. **Filtre fora** em qualquer coisa voltada ao jogador.
- `preco_base` guarda o float32 do binário tal como está (`0.10000000149…`).
  Arredonde na apresentação, não no banco.

### `gk.receita` — receitas e construções

`id` (pk; tem `:` no meio, tipo `alchemy_builddesk:p:mf_..._place`) ·
`origem` (`craft` = 2.101, `construcao` = 533) · `tipo` · `tempo_s` `energia`
`sanidade` `dificuldade` · `oculta` `precisa_desbloquear` · `perks`
`liberada_por` (text[]) · `pontos_tecnologia` (jsonb, chaves `g`/`b`/`r`) ·
`acao` `objeto_id` `objeto_pt` `objeto_en` (só em `construcao`).

- `tempo_s` e `energia` são **NULL** quando o jogo usa uma SmartExpression em
  vez de um número. A fórmula crua fica em `tempo_expr` / `energia_expr`
  (`300*(1-0.2*WGOpar("lvl")…)`). Se for publicar o número, olhe as duas.
- Em `origem = 'construcao'`, `acao = 'Put'` é construir (o custo está em
  `entradas`) e `acao = 'Remove'` é demolir (o que volta está em `saidas`).

### `gk.receita_ingrediente` — o que entra e o que sai

`receita_id` (fk) · `papel` (enum `entrada` | `entrada_estacao` | `saida`) ·
`ordem` · `ref_id` `ref_pt` `ref_en` · `qtd` `qtd_max` `qtd_expr`.

- **`ref_id` não tem FK para `gk.item`, e isso é de propósito.** Parte das
  referências não é item: `b_faith`, `b_empty:1`, `book:book_hard`. Sempre
  `LEFT JOIN gk.item`, nunca `JOIN`.
- `qtd_max` preenchido = a receita devolve uma faixa, não um valor fixo.

### `gk.receita_estacao` e `gk.estacao`

`receita_id` · `ordem` · `estacao_id` `estacao_pt` `estacao_en`. A visão
`gk.estacao` agrega isso em `id, pt, en, receitas`. Estação **não é item**: só
algumas têm linha em `gk.item`.

### `gk.tecnologia` e as ligações

`id` (pk, em inglês: `Advanced alchemy`) · `pt` `en` · `ramo_n` `ramo_pt` ·
`custo` (jsonb: `g`, `b`, `r`, `gratitude_points`) · `oculta` `requer_dlc` ·
`busca`. As ligações ficam em `gk.tecnologia_requisito` (`requer_id`),
`gk.tecnologia_receita` (`receita_id`) e `gk.tecnologia_perk` (`perk_id`).

- `requer_id` e `receita_id` também **não** têm FK: 165 das receitas liberadas
  por tecnologia não existem na lista de receitas. Isso é fiel ao binário, não
  é bug para consertar aqui — confira antes de dizer que uma tecnologia libera
  uma receita.

### `gk.dlc` e `gk.dlc_de`

`gk.dlc` são as quatro DLCs (`n`, `id`, `nome`). `gk.dlc_de` (visão
materializada: `tipo`, `id`, `dlc`) diz de qual DLC é cada `tecnologia`,
`receita`, `estacao`, `item` e `grupo`. Só tem as linhas de DLC — sem linha é
jogo base, então é `LEFT JOIN`. É **dedução**, não campo do jogo: a regra está
em `db/015-dlc.sql` e no README. O único dado de DLC que veio do binário é
`gk.tecnologia.requer_dlc`.

```sql
select i.id, i.pt, d.dlc from gk.item i
  left join gk.dlc_de d on d.tipo = 'item' and d.id = i.id
 where d.dlc = 'game_of_crone' and not i.nao_usado;
```

### `gk.importacao`

Uma linha por rodada do `importa.py`. A mais recente diz de onde veio o dado
que está no ar. Consulte antes de afirmar que um número está atualizado.

## Busca sem acento

`gk.normaliza(texto)` tira acento e caixa, e é IMMUTABLE (dá para usar em
índice). As colunas `busca` de `gk.item` e `gk.tecnologia` já estão
normalizadas e têm índice trigram.

```sql
select id, pt from gk.item
 where busca like '%' || gk.normaliza('aço') || '%' and not nao_usado;
```

## Consultas que já resolvem a maioria das perguntas

Receita completa de um item, com estação e ingredientes:

```sql
select r.id, e.estacao_pt, i.papel, coalesce(it.pt, i.ref_pt) as nome, i.qtd
  from gk.receita r
  join gk.receita_ingrediente i on i.receita_id = r.id
  left join gk.item it on it.id = i.ref_id
  left join gk.receita_estacao e on e.receita_id = r.id
 where r.id in (select receita_id from gk.receita_ingrediente
                 where ref_id = 'wooden_plank' and papel = 'saida')
 order by r.id, i.papel, i.ordem;
```

Onde um item é consumido:

```sql
select distinct r.id, r.origem
  from gk.receita_ingrediente i join gk.receita r on r.id = i.receita_id
 where i.ref_id = 'ingot_steel' and i.papel = 'entrada';
```

O que uma estação fabrica:

```sql
select r.id, coalesce(it.pt, s.ref_pt) as produz, s.qtd
  from gk.receita_estacao e
  join gk.receita r on r.id = e.receita_id
  join gk.receita_ingrediente s on s.receita_id = r.id and s.papel = 'saida'
  left join gk.item it on it.id = s.ref_id
 where e.estacao_id = 'mf_alchemy_craft_03' and not r.oculta;
```

Árvore de tecnologia de um ramo:

```sql
select t.pt, t.custo, q.requer_id
  from gk.tecnologia t
  left join gk.tecnologia_requisito q on q.tecnologia_id = t.id
 where t.ramo_n = 1 and not t.oculta order by t.pt;
```

## Na hora de escrever no site

Nome de item **sempre** sai de `gk.item.pt` — é a tradução oficial do jogo. A
wiki do fandom diverge em metade dos nomes, e quem manda aqui é o binário. Se
`pt` for NULL, o item não tem tradução: diga isso, não invente nome.
