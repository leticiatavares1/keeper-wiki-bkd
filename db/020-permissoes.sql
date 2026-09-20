-- Permissões do schema gk. Roda depois de 010-schema.sql, pelo dono do banco.
--
-- Os papéis keeper_api e keeper_claude nascem em ../keeper-wiki-db/init/002-papeis.sh.
-- Aqui só se concede SELECT: nenhum GRANT de INSERT/UPDATE/DELETE/TRUNCATE existe
-- neste arquivo, e é essa ausência que trava a escrita. Se algum dia aparecer um,
-- a garantia de somente leitura acabou.

GRANT USAGE ON SCHEMA gk TO keeper_leitura;
GRANT SELECT ON ALL TABLES IN SCHEMA gk TO keeper_leitura;

-- Tabela nova criada depois disso já nasce legível, sem precisar rodar de novo.
ALTER DEFAULT PRIVILEGES IN SCHEMA gk GRANT SELECT ON TABLES TO keeper_leitura;

-- keeper_api não enxerga nada fora do gk.
REVOKE ALL ON SCHEMA public FROM keeper_api;
