-- De qual DLC é cada tecnologia, receita, estação, item e grupo.
--
-- O jogo só marca DLC em TechDefinition.requires_dlc (enum DLCEngine.DLCVersion:
-- 1 BreakingDead, 2 Stories, 3 Refugees, 4 Souls). Item, receita e estação não
-- têm campo nenhum, então o resto é DEDUZIDO do dado que já está no schema. A
-- regra está toda aqui, em SQL, e é reproduzível: mudou a regra, rode
-- scripts/aplica-schema.sh e scripts/importa.py. O README repete a regra em
-- português corrido.
--
-- Princípio: na dúvida, NULL (jogo base). Marcar errado é pior que não marcar.
--
-- Roda antes de 020-permissoes.sql, que dá SELECT em tudo do schema gk.

-- ── As DLCs, na ordem do enum do jogo ────────────────────────────────────────
-- `nome` é o nome do produto. A localização pt-br do jogo não traduz: os
-- popups `stranger_sins_popup_window`, `game_of_crone_popup_window` e
-- `better_save_soul_popup_window` usam o nome em inglês. Breaking Dead não tem
-- texto na localização; fica o nome do produto.
CREATE OR REPLACE VIEW gk.dlc AS
  SELECT * FROM (VALUES
    (1, 'breaking_dead',    'Breaking Dead'),
    (2, 'stranger_sins',    'Stranger Sins'),
    (3, 'game_of_crone',    'Game of Crone'),
    (4, 'better_save_soul', 'Better Save Soul')
  ) AS v(n, id, nome);

-- ── A dedução, materializada ─────────────────────────────────────────────────
-- Uma linha por coisa que É de DLC; o que não aparece aqui é jogo base.
-- Materializada porque a conta passa por todas as receitas e itens (~0,5 s) e
-- o build da wiki chama /receitas 168 vezes. scripts/importa.py dá REFRESH
-- dentro da mesma transação da carga.
--
-- DROP + CREATE (e não IF NOT EXISTS) para a regra nova valer ao reaplicar.
DROP MATERIALIZED VIEW IF EXISTS gk.dlc_de;
CREATE MATERIALIZED VIEW gk.dlc_de AS
WITH RECURSIVE
-- Âncoras de zona. Em objs_data (reveng: out/gk1/data/balance/objs_data.json)
-- só as mesas de construção têm `zone_id`; estas cinco estão em zonas que só
-- existem com a DLC. A zona -> DLC é a do próprio jogo: o popup de compra de
-- cada DLC fala da taberna (Stranger Sins), do acampamento de refugiados (Game
-- of Crone) e da escotilha de cadáveres/almas (Better Save Soul).
mesa(estacao_id, dlc) AS (VALUES
  ('zombie_sawmill_builddesk',        'breaking_dead'),    -- zona zombie_sawmill
  ('players_tavern_builddesk',        'stranger_sins'),    -- zona players_tavern
  ('players_tavern_cellar_builddesk', 'stranger_sins'),    -- zona player_tavern_cellar
  ('refugee_builddesk',               'game_of_crone'),    -- zona refugees_camp
  ('souls_builddesk',                 'better_save_soul')  -- zona souls
),
-- Último recurso para estação que já vem posta no mapa (não é construída por
-- receita nenhuma, então nada no dado a liga a uma mesa): o prefixo do id.
-- Vale só para estação, nunca para item.
prefixo(padrao, dlc) AS (VALUES
  ('(^|_)zombie(_|$)',   'breaking_dead'),    -- zombie_*, mf_zombie_*, *_zombie
  ('^(players_)?tavern_', 'stranger_sins'),   -- a taberna do jogador (a do vilarejo não tem estação)
  ('^refugee_',          'game_of_crone'),
  ('^souls?_',           'better_save_soul')
),
-- 1. Tecnologia ──────────────────────────────────────────────────────────────
-- (a) requires_dlc do jogo; senão (b) toda receita que ela libera e que tem
-- estação é feita só em mesas de zona da mesma DLC (é o que acha a raiz do
-- ramo 8, Espiritualismo, que o jogo não marca: soul_sins_1 só libera
-- construções da souls_builddesk).
tec_direta AS (
  SELECT t.id, coalesce(
    (SELECT d.id FROM gk.dlc d WHERE d.n = t.requer_dlc),
    (SELECT CASE WHEN count(*) = count(m.dlc) AND count(DISTINCT m.dlc) = 1 THEN min(m.dlc) END
       FROM gk.tecnologia_receita c
       JOIN gk.receita_estacao e ON e.receita_id = c.receita_id
       LEFT JOIN mesa m ON m.estacao_id = e.estacao_id
      WHERE c.tecnologia_id = t.id)) AS dlc
  FROM gk.tecnologia t
),
-- (c) Sem nada direto, herda dos pré-requisitos: sobe a árvore parando em
-- quem já tem DLC direta. Se TODO ponto onde a subida para (tecnologia com
-- DLC direta, ou raiz sem pré-requisito) é da mesma DLC, não dá para pesquisar
-- a tecnologia sem ela.
sobe(tec, anc) AS (
  SELECT q.tecnologia_id, q.requer_id FROM gk.tecnologia_requisito q
  UNION
  SELECT s.tec, q.requer_id
    FROM sobe s
    JOIN gk.tecnologia_requisito q ON q.tecnologia_id = s.anc
    JOIN tec_direta d ON d.id = s.anc AND d.dlc IS NULL
),
parada AS (
  SELECT s.tec, d.dlc
    FROM sobe s LEFT JOIN tec_direta d ON d.id = s.anc
   WHERE d.dlc IS NOT NULL
      OR NOT EXISTS (SELECT 1 FROM gk.tecnologia_requisito q WHERE q.tecnologia_id = s.anc)
),
tec AS (
  SELECT d.id, coalesce(d.dlc,
    (SELECT CASE WHEN count(*) = count(p.dlc) AND count(DISTINCT p.dlc) = 1 THEN min(p.dlc) END
       FROM parada p WHERE p.tec = d.id)) AS dlc
  FROM tec_direta d
),
-- 2. Receita pela tecnologia: toda tecnologia que a libera é da mesma DLC.
-- Liberada também por tecnologia do jogo base -> não é de DLC por aqui.
rec_tec AS (
  SELECT c.receita_id AS id,
         CASE WHEN count(*) = count(t.dlc) AND count(DISTINCT t.dlc) = 1 THEN min(t.dlc) END AS dlc
    FROM gk.tecnologia_receita c JOIN tec t ON t.id = c.tecnologia_id
   GROUP BY c.receita_id
),
-- 3. Estação ─────────────────────────────────────────────────────────────────
-- Construção que ergue ou melhora (acao Put/None; demolir não conta) um
-- objeto, com a DLC dela: pela tecnologia que a libera ou pela mesa de zona.
ergue AS (
  SELECT r.id, r.objeto_id,
         coalesce(rt.dlc, (SELECT min(m.dlc) FROM gk.receita_estacao e
                             JOIN mesa m USING (estacao_id) WHERE e.receita_id = r.id)) AS dlc
    FROM gk.receita r LEFT JOIN rec_tec rt ON rt.id = r.id
   WHERE r.origem = 'construcao' AND r.acao IS DISTINCT FROM 'Remove'
     AND r.objeto_id IS NOT NULL
),
-- (a) é mesa de zona; (b) toda construção que a ergue (objeto_id = id ou
-- id_place) é da mesma DLC; (c) toda receita feita nela é liberada por
-- tecnologia da mesma DLC; (d) prefixo do id.
est_constr AS (
  SELECT e.id, CASE WHEN count(*) = count(c.dlc) AND count(DISTINCT c.dlc) = 1 THEN min(c.dlc) END AS dlc
    FROM gk.estacao e JOIN ergue c ON c.objeto_id IN (e.id, e.id || '_place')
   GROUP BY e.id
),
est_rec AS (
  SELECT e.estacao_id AS id,
         CASE WHEN count(*) = count(rt.dlc) AND count(DISTINCT rt.dlc) = 1 THEN min(rt.dlc) END AS dlc
    FROM gk.receita_estacao e LEFT JOIN rec_tec rt ON rt.id = e.receita_id
   GROUP BY e.estacao_id
),
est_prefixo AS (
  SELECT e.id, min(p.dlc) AS dlc
    FROM gk.estacao e JOIN prefixo p ON e.id ~ p.padrao
   GROUP BY e.id HAVING count(DISTINCT p.dlc) = 1
),
est AS (
  SELECT e.id, coalesce(m.dlc, c.dlc, r.dlc, p.dlc) AS dlc
    FROM gk.estacao e
    LEFT JOIN mesa m ON m.estacao_id = e.id
    LEFT JOIN est_constr c ON c.id = e.id
    LEFT JOIN est_rec r ON r.id = e.id
    LEFT JOIN est_prefixo p ON p.id = e.id
),
-- 4. Receita ─────────────────────────────────────────────────────────────────
-- (a) pela tecnologia (acima); (b) toda estação onde ela é feita é da mesma
-- DLC; (c) construção/demolição de um objeto que é estação de DLC. Duas
-- evidências de DLCs diferentes -> NULL.
rec_est AS (
  SELECT e.receita_id AS id,
         CASE WHEN count(*) = count(s.dlc) AND count(DISTINCT s.dlc) = 1 THEN min(s.dlc) END AS dlc
    FROM gk.receita_estacao e JOIN est s ON s.id = e.estacao_id
   GROUP BY e.receita_id
),
rec_obj AS (
  SELECT r.id, min(s.dlc) AS dlc
    FROM gk.receita r JOIN est s ON r.objeto_id IN (s.id, s.id || '_place')
   WHERE r.origem = 'construcao' AND s.dlc IS NOT NULL
   GROUP BY r.id HAVING count(DISTINCT s.dlc) = 1
),
rec_prova AS (
  SELECT id, dlc FROM rec_tec WHERE dlc IS NOT NULL
  UNION ALL SELECT id, dlc FROM rec_est WHERE dlc IS NOT NULL
  UNION ALL SELECT id, dlc FROM rec_obj
),
rec AS (
  SELECT id, min(dlc) AS dlc FROM rec_prova GROUP BY id HAVING count(DISTINCT dlc) = 1
),
-- 5. Item ────────────────────────────────────────────────────────────────────
-- (a) existe receita que o produz e TODAS as que o produzem são da mesma DLC;
-- e (b) nenhuma receita de fora dessa DLC (base ou outra) o consome, nem pelo
-- id do item nem pelo id do grupo dele. O (b) existe porque receita não é a
-- única fonte de item: carvão, minério, uva e lúpulo também caem de objeto do
-- mundo no jogo base, e isso não está no banco. Consumido pelo jogo base ->
-- na dúvida, base.
item AS (
  SELECT i.id,
    (SELECT CASE WHEN count(*) = count(r.dlc) AND count(DISTINCT r.dlc) = 1 THEN min(r.dlc) END
       FROM gk.receita_ingrediente s LEFT JOIN rec r ON r.id = s.receita_id
      WHERE s.ref_id = i.id AND s.papel = 'saida') AS dlc,
    i.grupo
  FROM gk.item i
),
item_final AS (
  SELECT i.id, i.grupo, i.dlc
    FROM item i
   WHERE i.dlc IS NOT NULL
     AND NOT EXISTS (
       SELECT 1 FROM gk.receita_ingrediente s LEFT JOIN rec r ON r.id = s.receita_id
        WHERE s.papel IN ('entrada', 'entrada_estacao')
          AND (s.ref_id = i.id OR s.ref_id = i.grupo)
          AND r.dlc IS DISTINCT FROM i.dlc)
),
-- 6. Grupo de níveis: todos os níveis são da mesma DLC.
grupo AS (
  SELECT g.grupo AS id, min(f.dlc) AS dlc
    FROM gk.item g LEFT JOIN item_final f ON f.id = g.id
   WHERE g.grupo IS NOT NULL
   GROUP BY g.grupo
  HAVING count(*) = count(f.dlc) AND count(DISTINCT f.dlc) = 1
)
SELECT 'tecnologia'::text AS tipo, id, dlc FROM tec WHERE dlc IS NOT NULL
UNION ALL SELECT 'receita', id, dlc FROM rec
UNION ALL SELECT 'estacao', id, dlc FROM est WHERE dlc IS NOT NULL
UNION ALL SELECT 'item', id, dlc FROM item_final
UNION ALL SELECT 'grupo', id, dlc FROM grupo;

CREATE UNIQUE INDEX dlc_de_chave ON gk.dlc_de (tipo, id);
CREATE INDEX dlc_de_dlc ON gk.dlc_de (tipo, dlc);
COMMENT ON MATERIALIZED VIEW gk.dlc_de IS
  'DLC deduzida (regra em db/015-dlc.sql e no README). Só as linhas de DLC: ausente = jogo base. REFRESH no scripts/importa.py.';
