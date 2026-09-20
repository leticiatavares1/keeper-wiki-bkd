"""Receitas e estações."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import consultas
from ..config import config
from ..db import busca_muitos, busca_um, busca_valor, pool
from ..modelos import EstacaoContada, Pagina, Receita, ReceitaResumo

rotas = APIRouter(tags=["receitas"])


@rotas.get("/receitas", summary="Lista receitas, filtrando por estação, item ou origem")
async def lista(
    busca: str | None = Query(None, description="nome do que a receita produz, ou id"),
    origem: str | None = Query(None, pattern="^(craft|construcao)$"),
    estacao: str | None = Query(None, description="id da estação (ver /estacoes)"),
    item: str | None = Query(None, description="id de item usado ou produzido"),
    incluir_ocultas: bool = Query(False),
    limite: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    banco: asyncpg.Pool = Depends(pool),
) -> Pagina[ReceitaResumo]:
    limite = min(limite, config.limite_maximo)
    filtros = (busca, origem, estacao, item, incluir_ocultas)
    total = await busca_valor(banco, consultas.CONTA_RECEITAS, *filtros)
    linhas = await busca_muitos(banco, consultas.LISTA_RECEITAS, *filtros, limite, offset)
    return Pagina(total=total, limite=limite, offset=offset,
                  dados=[ReceitaResumo(**linha) for linha in linhas])


@rotas.get("/receitas/{receita_id:path}", summary="Uma receita, com entradas e saídas")
async def detalhe(receita_id: str, banco: asyncpg.Pool = Depends(pool)) -> Receita:
    # O id de receita tem ':' e '/' ("alchemy_builddesk:p:mf_..."), daí o :path.
    linha = await busca_um(banco, consultas.RECEITA_POR_ID, receita_id)
    if not linha:
        raise HTTPException(404, f"receita '{receita_id}' não existe")
    return Receita(**linha)


@rotas.get("/estacoes", summary="Estações de trabalho, com quantas receitas cada uma tem")
async def estacoes(banco: asyncpg.Pool = Depends(pool)) -> list[EstacaoContada]:
    linhas = await busca_muitos(banco, consultas.LISTA_ESTACOES)
    return [EstacaoContada(**linha) for linha in linhas]
