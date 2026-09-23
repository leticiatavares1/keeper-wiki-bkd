#!/usr/bin/env python3
"""Carrega o dado extraído do jogo no Postgres.

    ./scripts/importa.py [--wiki ../reveng-graveyard-keeper/out/gk1/data/wiki]

Lê `itens.json`, `receitas.json` e `tecnologias.json` produzidos pelo
`catalogo.py` do ../reveng-graveyard-keeper (a extração vive lá, não aqui) e
reescreve o schema gk inteiro dentro de uma transação: ou entra tudo, ou o
banco fica como estava.

Usa DATABASE_URL_DONO, a única credencial do projeto que escreve.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import asyncpg

RAIZ = Path(__file__).resolve().parent.parent
PADRAO_WIKI = RAIZ.parent / "reveng-graveyard-keeper" / "out" / "gk1" / "data" / "wiki"


def texto(valor) -> str | None:
    """String vazia da extração vira NULL: item sem tradução não tem nome."""
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def numero(valor) -> Decimal | None:
    """Número vira Decimal; SmartExpression (str) devolve None — vai na coluna _expr."""
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    return None


def expressao(valor) -> str | None:
    return valor if isinstance(valor, str) else None


def carrega(pasta: Path, nome: str) -> list[dict]:
    caminho = pasta / f"{nome}.json"
    if not caminho.exists():
        sys.exit(f"não achei {caminho}. Rode o catalogo.py no reveng-graveyard-keeper.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def linhas_item(itens: list[dict]):
    for it in itens:
        yield (
            it["id"],
            texto(it.get("pt")),
            texto(it.get("en")),
            texto(it.get("descricao_pt")),
            texto(it.get("descricao_en")),
            it.get("tipo") or "None",
            numero(it.get("preco_base")) or Decimal(0),
            numero(it.get("qualidade")) or Decimal(0),
            int(it.get("pilha") or 1),
            numero(it.get("eficiencia")) or Decimal(1),
            bool(it.get("tem_durabilidade")),
            bool(it.get("nao_usado")),
            list(it.get("tipos_de_produto") or []),
            texto(it.get("icone")),
            int(it["estrela"]) if it.get("estrela") is not None else None,
            texto(it.get("grupo")),
            bool(it.get("pode_usar")),
            json.dumps(it.get("ao_usar") or {}),
            list(it.get("ao_usar_expr") or []),
        )


def linhas_receita(receitas: list[dict]):
    for r in receitas:
        objeto = r.get("objeto_construido") or {}
        yield (
            r["id"],
            r["origem"],
            r.get("tipo") or "None",
            numero(r.get("tempo_s")),
            expressao(r.get("tempo_s")),
            numero(r.get("energia")),
            expressao(r.get("energia")),
            numero(r.get("sanidade")),
            numero(r.get("dificuldade")),
            bool(r.get("oculta")),
            bool(r.get("precisa_desbloquear")),
            list(r.get("perks") or []),
            list(r.get("liberada_por") or []),
            json.dumps(r.get("pontos_tecnologia") or {}),
            texto(r.get("acao")),
            texto(objeto.get("id")),
            texto(objeto.get("pt")),
            texto(objeto.get("en")),
            texto(objeto.get("icone")),
        )


PAPEIS = {
    "entradas": "entrada",
    "entradas_da_estacao": "entrada_estacao",
    "saidas": "saida",
}


def linhas_ingrediente(receitas: list[dict]):
    for r in receitas:
        for chave, papel in PAPEIS.items():
            for ordem, ing in enumerate(r.get(chave) or []):
                yield (
                    r["id"],
                    papel,
                    ordem,
                    ing["id"],
                    texto(ing.get("pt")),
                    texto(ing.get("en")),
                    numero(ing.get("qtd")),
                    numero(ing.get("qtd_max")),
                    expressao(ing.get("qtd_expr")),
                )


def linhas_estacao(receitas: list[dict]):
    for r in receitas:
        for ordem, est in enumerate(r.get("estacoes") or []):
            yield (
                r["id"], ordem, est["id"], texto(est.get("pt")), texto(est.get("en")),
                texto(est.get("icone")),
            )


def linhas_tecnologia(tecnologias: list[dict]):
    for t in tecnologias:
        ramo = t.get("ramo") or {}
        yield (
            t["id"],
            texto(t.get("pt")),
            texto(t.get("en")),
            int(ramo["n"]) if ramo.get("n") is not None else None,
            texto(ramo.get("pt")),
            texto(ramo.get("icone")) or "",
            json.dumps(t.get("custo") or {}),
            bool(t.get("oculta")),
            int(t.get("requer_dlc") or 0),
        )


def linhas_ligacao(tecnologias: list[dict], chave: str):
    """Ligações tecnologia -> alvo, sem repetir e sem o vazio.

    A extração escreve "sem pré-requisito" como string vazia (55 casos em
    `requer`). Guardar isso viraria um requisito fantasma em toda consulta.
    """
    for t in tecnologias:
        alvos = [a for a in dict.fromkeys(t.get(chave) or []) if texto(a)]
        for alvo in alvos:
            yield (t["id"], alvo)


async def principal(pasta: Path, url: str) -> None:
    itens = carrega(pasta, "itens")
    receitas = carrega(pasta, "receitas")
    tecnologias = carrega(pasta, "tecnologias")
    print(f"lido de {pasta}: {len(itens)} itens, {len(receitas)} receitas, "
          f"{len(tecnologias)} tecnologias")

    conexao = await asyncpg.connect(url)
    try:
        async with conexao.transaction():
            # CASCADE limpa as filhas; a ordem das inserções respeita as FKs.
            await conexao.execute(
                "TRUNCATE gk.item, gk.receita, gk.tecnologia RESTART IDENTITY CASCADE"
            )

            async def copia(tabela: str, colunas: list[str], registros) -> int:
                registros = list(registros)
                await conexao.copy_records_to_table(
                    tabela.split(".")[1], schema_name="gk",
                    columns=colunas, records=registros,
                )
                return len(registros)

            await copia("gk.item", [
                "id", "pt", "en", "descricao_pt", "descricao_en", "tipo",
                "preco_base", "qualidade", "pilha", "eficiencia",
                "tem_durabilidade", "nao_usado", "tipos_de_produto",
                "icone", "estrela", "grupo", "pode_usar", "ao_usar", "ao_usar_expr",
            ], linhas_item(itens))

            await copia("gk.receita", [
                "id", "origem", "tipo", "tempo_s", "tempo_expr", "energia",
                "energia_expr", "sanidade", "dificuldade", "oculta",
                "precisa_desbloquear", "perks", "liberada_por",
                "pontos_tecnologia", "acao", "objeto_id", "objeto_pt", "objeto_en",
                "objeto_icone",
            ], linhas_receita(receitas))

            n_ing = await copia("gk.receita_ingrediente", [
                "receita_id", "papel", "ordem", "ref_id", "ref_pt", "ref_en",
                "qtd", "qtd_max", "qtd_expr",
            ], linhas_ingrediente(receitas))

            n_est = await copia("gk.receita_estacao", [
                "receita_id", "ordem", "estacao_id", "estacao_pt", "estacao_en", "icone",
            ], linhas_estacao(receitas))

            await copia("gk.tecnologia", [
                "id", "pt", "en", "ramo_n", "ramo_pt", "ramo_icone", "custo", "oculta",
                "requer_dlc",
            ], linhas_tecnologia(tecnologias))

            await copia("gk.tecnologia_requisito", ["tecnologia_id", "requer_id"],
                        linhas_ligacao(tecnologias, "requer"))
            await copia("gk.tecnologia_receita", ["tecnologia_id", "receita_id"],
                        linhas_ligacao(tecnologias, "libera_receitas"))
            await copia("gk.tecnologia_perk", ["tecnologia_id", "perk_id"],
                        linhas_ligacao(tecnologias, "libera_perks"))

            await conexao.execute(
                """INSERT INTO gk.importacao
                       (build_do_jogo, fonte, itens, receitas, tecnologias)
                   VALUES ($1, $2, $3, $4, $5)""",
                os.environ.get("GK_BUILD"), str(pasta),
                len(itens), len(receitas), len(tecnologias),
            )
        print(f"gravado: {n_ing} ingredientes, {n_est} vínculos de estação")
        await conexao.execute("ANALYZE")
    finally:
        await conexao.close()


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--wiki", type=Path, default=PADRAO_WIKI,
                            help="pasta out/gk1/data/wiki do reveng-graveyard-keeper")
    opcoes = argumentos.parse_args()

    url = os.environ.get("DATABASE_URL_DONO")
    if not url:
        sys.exit("defina DATABASE_URL_DONO (veja .env.example)")
    asyncio.run(principal(opcoes.wiki.resolve(), url))
