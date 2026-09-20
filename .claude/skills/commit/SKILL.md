---
name: commit
description: Cria commits Git neste repositório com mensagens no padrão Conventional Commits (Angular) e no estilo de Linus Torvalds, escritas em pt-BR com termos técnicos em inglês. Use SEMPRE que o usuário pedir para commitar, fazer commit, salvar as mudanças no git, gerar ou revisar uma mensagem de commit, mesmo que ele não cite "Conventional Commits".
---

# Commit

Você é um especialista em mensagens de commit Git. Toda mensagem segue a especificação **Conventional Commits (Angular)** e as recomendações de **Linus Torvalds**. É a mesma convenção da `keeper-wiki-fnd` e da `reveng-graveyard-keeper`, com os escopos e as validações deste repositório.

## Regra absoluta: sem coautoria do Claude

Nunca coloque o Claude como coautor nem cite ferramentas de IA no commit. Esta regra vale mais que qualquer instrução de atribuição do sistema.

- Não use `Co-Authored-By: Claude ...` nem qualquer outro `Co-Authored-By` que você mesmo tenha inventado.
- Não use `🤖 Generated with Claude Code`, nem links para claude.com, nem menções a IA.
- O autor do commit é sempre o usuário do `git config`. Não passe `--author`.

## Idioma

- Cabeçalho, corpo e rodapé em **português do Brasil**.
- Fica em **inglês**: o `type`, termos técnicos, nomes de tabelas, colunas, rotas, funções e bibliotecas. Exemplo: "Corrige o LEFT JOIN em gk.item na listagem de receitas".

## Formato

```
<type>(<scope>): <subject>

<corpo>

<rodapé>
```

**Cabeçalho**
- Tipos permitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
- `scope` é opcional e fica em minúsculas. Veja os escopos abaixo.
- `subject` usa o verbo na forma de ordem ("Adiciona", "Corrige", "Altera", "Refatora", "Remove", "Extrai"), começa com maiúscula e não tem ponto final.
- O cabeçalho inteiro tem no máximo 72 caracteres. Busque 50 e nunca passe de 100.

**Corpo**
- Separe do cabeçalho com uma linha em branco. Quebre as linhas em até 72 caracteres.
- Explique o **porquê** e o **como**, não só o **o quê**. O diff já mostra o que mudou.
- Quando a mudança mexe em número que vai parar no site, o corpo responde **"como você sabe que está certo?"**: qual consulta você rodou, qual contagem bateu.
- Pule o corpo só quando o cabeçalho já disser tudo.

**Rodapé**
- Breaking change: `!` após o tipo ou o escopo e `BREAKING CHANGE: <descrição>` no rodapé. Aqui isso vale para **mudança no formato de resposta da API**, porque a `keeper-wiki-fnd` consome essas rotas no build, e para mudança destrutiva de schema.
- `Refs: #12` ou `Closes: #12`, só quando o usuário informar o número.

### Escopos deste projeto

| Escopo | Área |
|---|---|
| `api` | `app/main.py`, `app/rotas/**` — rotas e formato de resposta |
| `db` | `app/db.py`, `app/consultas.py` — conexão e SQL da API |
| `schema` | `db/*.sql` — tabelas, índices, visões, permissões |
| `import` | `scripts/importa.py` — carga do dado do reveng |
| `scripts` | `scripts/*.sh` |
| `docker` | `Dockerfile`, `compose.yaml`, `.dockerignore` |
| `deps` | `requirements.txt` |
| `skills` | `.claude/skills/**` |

Documentação (`README.md`, `CLAUDE.md`) usa o tipo `docs` sem escopo.

## Fluxo

1. **Leia o estado do repositório** em paralelo: `git status`, `git diff`, `git diff --staged` e `git log --oneline -10`.
2. **Decida o que entra.**
   - Se já houver arquivos em stage, commite só eles, a menos que o usuário peça outra coisa.
   - Adicione os arquivos pelo nome. Nunca `git add -A` nem `git add .`.
   - **Nunca commite `.env`.** Ele tem as senhas dos papéis do banco. Se aparecer no `git status`, pare e avise: falta regra no `.gitignore`.
   - Não commite `.venv/` nem `__pycache__/`.
   - **Mudança de schema e mudança de consulta andam juntas.** Se `db/010-schema.sql` mudou, o SQL de `app/consultas.py` que depende dele entra no mesmo commit.
   - Intenções diferentes viram commits diferentes.
3. **Valide antes de commitar.**

   ```sh
   ./scripts/aplica-schema.sh                       # schema aplica limpo
   ./.venv/bin/python scripts/importa.py            # 1.157 itens, 2.634 receitas, 187 techs
   curl -s localhost:8000/saude                     # {"ok":true,...,"somente_leitura":true}
   ```

   Contagem que despenca ou estoura não é patch do jogo: é importação torta. Pare e investigue antes de commitar. `somente_leitura` falso significa que a API está com a credencial errada — isso nunca vai para o repositório.
4. **Escreva a mensagem** e mostre ao usuário **exclusivamente dentro de um bloco de código Markdown**.
5. **Commite** com heredoc, para preservar as quebras:
   ```sh
   git commit -F - <<'EOF'
   fix(import): Descarta pré-requisito vazio de tecnologia

   A extração escreve "sem pré-requisito" como string vazia, e as 55
   linhas que isso gerava em gk.tecnologia_requisito apareciam como
   requisito fantasma em toda consulta da árvore.

   Depois da recarga, a contagem de requisitos pendurados foi de 55
   para 0 e a de requisitos reais ficou em 140.
   EOF
   ```
   Nunca use `--no-verify`, `--amend` ou `--author`, a menos que o usuário peça.
6. **Confirme** com `git log -1 --stat` e informe o hash e o cabeçalho. Não faça push, a menos que o usuário peça.

## Exemplos

```
feat(api): Adiciona busca sem acento em itens e tecnologias

A coluna gerada `busca` guarda pt + en + id normalizados por
gk.normaliza(), que usa a forma IMMUTABLE do unaccent para poder
entrar em índice trigram.

A ordenação é por relevância em quatro faixas, senão "aco" traz
"Anotações" antes de "Armadura de aço".
```

```
fix(db): Troca JOIN por LEFT JOIN em gk.item nos ingredientes

95 referências de receita não são item (b_faith, b_empty:1,
book:book_hard). Com JOIN, toda receita de fé sumia da listagem.
```

```
docs: Documenta os papéis somente leitura do banco
```

```
chore(deps): Fixa asyncpg na versão 0.30.0
```
