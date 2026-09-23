"""O SQL da API, em um lugar só.

Tudo aqui é SELECT. Parâmetro sempre vai como $n — nada é interpolado em
string, nem os filtros opcionais, que são resolvidos com `$n IS NULL OR ...`.
"""

# Ingredientes e estações viram JSON no próprio Postgres: uma ida ao banco por
# requisição, sem N+1. O LEFT JOIN em gk.item existe porque nem toda referência
# de receita é item (estação, ponto de fé, b_empty:1) — daí o campo `e_item`.
# Referência a grupo de níveis (gk.grupo) não é item: e_item false, e_grupo true.
INGREDIENTES = """
  SELECT i.receita_id, i.papel,
         jsonb_agg(jsonb_build_object(
           'ref_id',   i.ref_id,
           'pt',       coalesce(it.pt, gr.pt, i.ref_pt),
           'en',       coalesce(it.en, gr.en, i.ref_en),
           'qtd',      i.qtd,
           'qtd_max',  i.qtd_max,
           'qtd_expr', i.qtd_expr,
           'e_item',   it.id IS NOT NULL,
           -- ponta que pede o grupo ("pumpkin_crop"), não um nível dele
           'e_grupo',  gr.id IS NOT NULL,
           'grupo',    it.grupo,
           'icone',    coalesce(it.icone, gr.icone),
           'estrela',  it.estrela
         ) ORDER BY i.ordem) AS lista
    FROM gk.receita_ingrediente i
    LEFT JOIN gk.item  it ON it.id = i.ref_id
    LEFT JOIN gk.grupo gr ON gr.id = i.ref_id AND it.id IS NULL
   GROUP BY i.receita_id, i.papel
"""

ESTACOES = """
  SELECT e.receita_id,
         jsonb_agg(jsonb_build_object(
           'id', e.estacao_id, 'pt', e.estacao_pt, 'en', e.estacao_en, 'icone', e.icone
         ) ORDER BY e.ordem) AS lista
    FROM gk.receita_estacao e
   GROUP BY e.receita_id
"""

_COLUNAS_RESUMO = """
    r.id, r.origem, r.tipo, r.oculta,
    coalesce(est.lista, '[]'::jsonb) AS estacoes,
    coalesce(sai.lista, '[]'::jsonb) AS saidas
"""

_COLUNAS_COMPLETAS = _COLUNAS_RESUMO + """,
    r.tempo_s, r.tempo_expr, r.energia, r.energia_expr, r.sanidade,
    r.dificuldade, r.precisa_desbloquear, r.perks, r.liberada_por,
    r.pontos_tecnologia, r.acao, r.objeto_id, r.objeto_pt, r.objeto_en,
    r.objeto_icone,
    coalesce(ent.lista, '[]'::jsonb) AS entradas,
    coalesce(ees.lista, '[]'::jsonb) AS entradas_da_estacao
"""

_JUNCOES_RESUMO = f"""
    FROM gk.receita r
    LEFT JOIN ({ESTACOES}) est ON est.receita_id = r.id
    LEFT JOIN ({INGREDIENTES}) sai ON sai.receita_id = r.id AND sai.papel = 'saida'
"""

_JUNCOES_COMPLETAS = _JUNCOES_RESUMO + f"""
    LEFT JOIN ({INGREDIENTES}) ent ON ent.receita_id = r.id AND ent.papel = 'entrada'
    LEFT JOIN ({INGREDIENTES}) ees ON ees.receita_id = r.id AND ees.papel = 'entrada_estacao'
"""

RECEITA_POR_ID = f"SELECT {_COLUNAS_COMPLETAS} {_JUNCOES_COMPLETAS} WHERE r.id = $1"

# $1 busca, $2 origem, $3 estação, $4 item usado (entrada ou saída), $5 incluir
# ocultas, $6 limite, $7 offset.
_FILTRO_RECEITA = """
   WHERE ($1::text IS NULL OR EXISTS (
           SELECT 1 FROM gk.receita_ingrediente b
            LEFT JOIN gk.item bi ON bi.id = b.ref_id
            WHERE b.receita_id = r.id AND b.papel = 'saida'
              AND (gk.normaliza(coalesce(bi.busca, b.ref_pt, b.ref_id))
                   LIKE '%' || gk.normaliza($1) || '%')
         ) OR gk.normaliza(r.id) LIKE '%' || gk.normaliza($1) || '%')
     AND ($2::text IS NULL OR r.origem = $2)
     AND ($3::text IS NULL OR EXISTS (
           SELECT 1 FROM gk.receita_estacao s
            WHERE s.receita_id = r.id AND s.estacao_id = $3))
     AND ($4::text IS NULL OR EXISTS (
           SELECT 1 FROM gk.receita_ingrediente u
            WHERE u.receita_id = r.id AND u.ref_id = $4))
     AND ($5::boolean OR NOT r.oculta)
"""

LISTA_RECEITAS = f"""
  SELECT {_COLUNAS_COMPLETAS}
    {_JUNCOES_COMPLETAS}
    {_FILTRO_RECEITA}
   ORDER BY r.id
   LIMIT $6 OFFSET $7
"""

CONTA_RECEITAS = f"SELECT count(*) FROM gk.receita r {_FILTRO_RECEITA}"

# "aco" casa com "Armadura de aço" e também com "Anotações". Ordena por quão
# bem casa: nome inteiro, começo do nome, começo de alguma palavra, e só então
# pedaço perdido no meio. $1 é sempre o termo de busca.
_RELEVANCIA = """
    CASE WHEN $1::text IS NULL THEN 0
         WHEN gk.normaliza({nome}) = gk.normaliza($1) THEN 0
         WHEN gk.normaliza({nome}) LIKE gk.normaliza($1) || '%' THEN 1
         WHEN gk.normaliza({nome}) LIKE '% ' || gk.normaliza($1) || '%' THEN 2
         ELSE 3 END
"""

_COLUNAS_ITEM = """
    id, pt, en, descricao_pt, descricao_en, tipo, preco_base, qualidade,
    pilha, eficiencia, tem_durabilidade, nao_usado, tipos_de_produto,
    icone, estrela, grupo, pode_usar, ao_usar, ao_usar_expr
"""

# $1 busca, $2 tipo, $3 incluir não usados, $4 limite, $5 offset.
_FILTRO_ITEM = """
   WHERE ($1::text IS NULL OR busca LIKE '%' || gk.normaliza($1) || '%')
     AND ($2::text IS NULL OR tipo = $2)
     AND ($3::boolean OR NOT nao_usado)
"""

LISTA_ITENS = f"""
  SELECT {_COLUNAS_ITEM} FROM gk.item
  {_FILTRO_ITEM}
  ORDER BY {_RELEVANCIA.format(nome="coalesce(pt, en, id)")}, coalesce(pt, en, id)
  LIMIT $4 OFFSET $5
"""

CONTA_ITENS = f"SELECT count(*) FROM gk.item {_FILTRO_ITEM}"

ITEM_POR_ID = f"SELECT {_COLUNAS_ITEM} FROM gk.item WHERE id = $1"

ITEM_EXISTE = "SELECT 1 FROM gk.item WHERE id = $1"

# Receitas que produzem ($2 = 'saida') ou consomem ($2 = 'entrada') algum dos
# ids em $1: um item, ou o grupo e todos os seus níveis.
RECEITAS_DO_ITEM = f"""
  SELECT {_COLUNAS_COMPLETAS}
    {_JUNCOES_COMPLETAS}
   WHERE EXISTS (
           SELECT 1 FROM gk.receita_ingrediente x
            WHERE x.receita_id = r.id AND x.ref_id = ANY($1::text[])
              AND x.papel = $2::gk.papel_ingrediente)
   ORDER BY r.id
"""

# ── Grupos de níveis de qualidade ────────────────────────────────────────────
# $1 incluir não usados, $2 limite, $3 offset.
LISTA_GRUPOS = """
  SELECT id, pt, en, icone, tipo, nao_usado, niveis FROM gk.grupo
   WHERE ($1::boolean OR NOT nao_usado)
   ORDER BY coalesce(pt, en, id), id
   LIMIT $2 OFFSET $3
"""

CONTA_GRUPOS = "SELECT count(*) FROM gk.grupo WHERE ($1::boolean OR NOT nao_usado)"

GRUPO_POR_ID = "SELECT id, pt, en, icone, tipo, nao_usado, niveis FROM gk.grupo WHERE id = $1"

GRUPO_EXISTE = "SELECT 1 FROM gk.grupo WHERE id = $1"

IDS_DO_GRUPO = "SELECT id FROM gk.item WHERE grupo = $1"

# Níveis do grupo $1, do mais baixo ao mais alto.
NIVEIS_DO_GRUPO = f"""
  SELECT {_COLUNAS_ITEM} FROM gk.item WHERE grupo = $1
   ORDER BY estrela NULLS LAST, id
"""

LISTA_ESTACOES = """
  SELECT e.id, coalesce(e.pt, i.pt) AS pt, coalesce(e.en, i.en) AS en,
         coalesce(e.icone, i.icone) AS icone, e.receitas
    FROM gk.estacao e
    LEFT JOIN gk.item i ON i.id = e.id
   ORDER BY coalesce(e.pt, i.pt, e.id)
"""

_COLUNAS_TECNOLOGIA = """
    t.id, t.pt, t.en, t.ramo_n, t.ramo_pt, t.ramo_icone, t.custo, t.oculta, t.requer_dlc,
    coalesce((SELECT jsonb_agg(jsonb_build_object('id', q.requer_id, 'pt', rq.pt, 'en', rq.en)
                              ORDER BY q.requer_id)
                FROM gk.tecnologia_requisito q
                LEFT JOIN gk.tecnologia rq ON rq.id = q.requer_id
               WHERE q.tecnologia_id = t.id), '[]'::jsonb) AS requer,
    -- A receita não tem nome próprio: usa o do primeiro item que ela produz.
    -- `existe` é falso nas receitas que o binário cita e a lista não tem.
    coalesce((SELECT jsonb_agg(jsonb_build_object(
                       'id', c.receita_id, 'pt', nm.pt, 'en', nm.en,
                       'existe', rc.id IS NOT NULL) ORDER BY c.receita_id)
                FROM gk.tecnologia_receita c
                LEFT JOIN gk.receita rc ON rc.id = c.receita_id
                LEFT JOIN LATERAL (
                  SELECT coalesce(si.pt, s.ref_pt) AS pt, coalesce(si.en, s.ref_en) AS en
                    FROM gk.receita_ingrediente s
                    LEFT JOIN gk.item si ON si.id = s.ref_id
                   WHERE s.receita_id = c.receita_id AND s.papel = 'saida'
                   ORDER BY s.ordem LIMIT 1) nm ON true
               WHERE c.tecnologia_id = t.id), '[]'::jsonb) AS libera_receitas,
    coalesce((SELECT array_agg(p.perk_id ORDER BY p.perk_id)
                FROM gk.tecnologia_perk p WHERE p.tecnologia_id = t.id), '{}') AS libera_perks
"""

# $1 busca, $2 ramo, $3 incluir ocultas.
_FILTRO_TECNOLOGIA = """
   WHERE ($1::text IS NULL OR t.busca LIKE '%' || gk.normaliza($1) || '%')
     AND ($2::integer IS NULL OR t.ramo_n = $2)
     AND ($3::boolean OR NOT t.oculta)
"""

LISTA_TECNOLOGIAS = f"""
  SELECT {_COLUNAS_TECNOLOGIA} FROM gk.tecnologia t
  {_FILTRO_TECNOLOGIA}
  ORDER BY {_RELEVANCIA.format(nome="coalesce(t.pt, t.en, t.id)")},
           t.ramo_n NULLS LAST, coalesce(t.pt, t.en, t.id)
  LIMIT $4 OFFSET $5
"""

CONTA_TECNOLOGIAS = f"SELECT count(*) FROM gk.tecnologia t {_FILTRO_TECNOLOGIA}"

TECNOLOGIA_POR_ID = f"SELECT {_COLUNAS_TECNOLOGIA} FROM gk.tecnologia t WHERE t.id = $1"

ULTIMA_IMPORTACAO = """
  SELECT feita_em, build_do_jogo, fonte, itens, receitas, tecnologias
    FROM gk.importacao ORDER BY feita_em DESC LIMIT 1
"""
