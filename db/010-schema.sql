-- Schema `gk`: o dado do jogo extraído em ../reveng-graveyard-keeper.
-- Aplique com scripts/aplica-schema.sh. É idempotente e não guarda estado
-- editorial: os artigos da wiki continuam em TypeScript no keeper-wiki-fnd.

CREATE SCHEMA IF NOT EXISTS gk;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Busca sem acento e sem caixa. A forma de dois argumentos do unaccent() é
-- IMMUTABLE (a de um argumento é só STABLE), então dá para usar em coluna
-- gerada e em índice.
CREATE OR REPLACE FUNCTION gk.normaliza(texto text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
$$ SELECT lower(public.unaccent('public.unaccent', texto)) $$;

-- ── Procedência ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gk.importacao (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  feita_em      timestamptz NOT NULL DEFAULT now(),
  build_do_jogo text,
  fonte         text    NOT NULL,
  itens         integer NOT NULL,
  receitas      integer NOT NULL,
  tecnologias   integer NOT NULL
);
COMMENT ON TABLE gk.importacao IS
  'Uma linha por rodada de scripts/importa.py. A mais recente descreve o que está nas tabelas.';

-- ── Itens ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gk.item (
  id               text PRIMARY KEY,
  pt               text,
  en               text,
  descricao_pt     text,
  descricao_en     text,
  tipo             text    NOT NULL,
  preco_base       numeric NOT NULL,
  qualidade        numeric NOT NULL,
  pilha            integer NOT NULL,
  eficiencia       numeric NOT NULL,
  tem_durabilidade boolean NOT NULL,
  nao_usado        boolean NOT NULL,
  tipos_de_produto text[]  NOT NULL DEFAULT '{}',
  busca text GENERATED ALWAYS AS (
    gk.normaliza(coalesce(pt, '') || ' ' || coalesce(en, '') || ' ' || id)
  ) STORED
);
COMMENT ON COLUMN gk.item.pt IS 'Tradução oficial pt-BR do binário; NULL quando o item não tem entrada na localização.';
COMMENT ON COLUMN gk.item.nao_usado IS 'Item existe no balanceamento mas não aparece no jogo. Filtre fora por padrão.';

-- ── Receitas ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gk.receita (
  id                  text PRIMARY KEY,
  origem              text NOT NULL CHECK (origem IN ('craft', 'construcao')),
  tipo                text NOT NULL,
  -- tempo e energia podem ser SmartExpression ("10-Ppar(\"p_woodworker\")*5"):
  -- o número vai na coluna numérica, a fórmula crua na coluna _expr.
  tempo_s             numeric,
  tempo_expr          text,
  energia             numeric,
  energia_expr        text,
  sanidade            numeric,
  dificuldade         numeric,
  oculta              boolean NOT NULL,
  precisa_desbloquear boolean NOT NULL,
  perks               text[]  NOT NULL DEFAULT '{}',
  liberada_por        text[]  NOT NULL DEFAULT '{}',
  pontos_tecnologia   jsonb   NOT NULL DEFAULT '{}',
  -- só em origem = 'construcao'
  acao                text,
  objeto_id           text,
  objeto_pt           text,
  objeto_en           text
);
COMMENT ON COLUMN gk.receita.pontos_tecnologia IS 'Pontos rendidos ao fabricar, por cor: g (verde), b (azul), r (vermelho).';

DO $$ BEGIN
  CREATE TYPE gk.papel_ingrediente AS ENUM ('entrada', 'entrada_estacao', 'saida');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Atenção: ref_id NÃO tem FK para gk.item de propósito. Entradas e saídas também
-- referenciam coisas que não são item (b_empty:1, b_faith, book:book_hard), e
-- estação/objeto construído são objetos de mundo. Junte com LEFT JOIN.
CREATE TABLE IF NOT EXISTS gk.receita_ingrediente (
  receita_id text     NOT NULL REFERENCES gk.receita(id) ON DELETE CASCADE,
  papel      gk.papel_ingrediente NOT NULL,
  ordem      smallint NOT NULL,
  ref_id     text     NOT NULL,
  ref_pt     text,
  ref_en     text,
  qtd        numeric,
  qtd_max    numeric,
  qtd_expr   text,
  PRIMARY KEY (receita_id, papel, ordem)
);

CREATE TABLE IF NOT EXISTS gk.receita_estacao (
  receita_id text     NOT NULL REFERENCES gk.receita(id) ON DELETE CASCADE,
  ordem      smallint NOT NULL,
  estacao_id text     NOT NULL,
  estacao_pt text,
  estacao_en text,
  PRIMARY KEY (receita_id, ordem)
);

-- ── Tecnologias ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gk.tecnologia (
  id         text PRIMARY KEY,
  pt         text,
  en         text,
  ramo_n     integer,
  ramo_pt    text,
  custo      jsonb   NOT NULL DEFAULT '{}',
  oculta     boolean NOT NULL,
  requer_dlc integer NOT NULL DEFAULT 0,
  busca text GENERATED ALWAYS AS (
    gk.normaliza(coalesce(pt, '') || ' ' || coalesce(en, '') || ' ' || id)
  ) STORED
);

-- requer_id e receita_id ficam sem FK: 165 das receitas liberadas por
-- tecnologia não existem na lista de receitas. Guardar o dado como veio do
-- binário vale mais que forçar integridade aqui.
CREATE TABLE IF NOT EXISTS gk.tecnologia_requisito (
  tecnologia_id text NOT NULL REFERENCES gk.tecnologia(id) ON DELETE CASCADE,
  requer_id     text NOT NULL,
  PRIMARY KEY (tecnologia_id, requer_id)
);

CREATE TABLE IF NOT EXISTS gk.tecnologia_receita (
  tecnologia_id text NOT NULL REFERENCES gk.tecnologia(id) ON DELETE CASCADE,
  receita_id    text NOT NULL,
  PRIMARY KEY (tecnologia_id, receita_id)
);

CREATE TABLE IF NOT EXISTS gk.tecnologia_perk (
  tecnologia_id text NOT NULL REFERENCES gk.tecnologia(id) ON DELETE CASCADE,
  perk_id       text NOT NULL,
  PRIMARY KEY (tecnologia_id, perk_id)
);

-- ── Índices ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS item_busca_trgm      ON gk.item      USING gin (busca gin_trgm_ops);
CREATE INDEX IF NOT EXISTS item_tipo            ON gk.item (tipo);
CREATE INDEX IF NOT EXISTS tecnologia_busca_trgm ON gk.tecnologia USING gin (busca gin_trgm_ops);
CREATE INDEX IF NOT EXISTS tecnologia_ramo      ON gk.tecnologia (ramo_n);
CREATE INDEX IF NOT EXISTS receita_origem       ON gk.receita (origem);
CREATE INDEX IF NOT EXISTS ingrediente_ref      ON gk.receita_ingrediente (ref_id, papel);
CREATE INDEX IF NOT EXISTS estacao_ref          ON gk.receita_estacao (estacao_id);

-- ── Visões ───────────────────────────────────────────────────────────────────
-- Estações não são itens, então a lista sai das próprias receitas.
CREATE OR REPLACE VIEW gk.estacao AS
  SELECT estacao_id AS id,
         min(estacao_pt) AS pt,
         min(estacao_en) AS en,
         count(DISTINCT receita_id)::integer AS receitas
    FROM gk.receita_estacao
   GROUP BY estacao_id;
