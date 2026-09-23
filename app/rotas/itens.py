"""Itens do jogo."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import consultas
from ..config import config
from ..db import busca_muitos, busca_um, busca_valor, pool
from ..modelos import FiltroDlc, Item, Pagina, Receita

rotas = APIRouter(prefix="/itens", tags=["itens"])


class ReceitasDoItem(BaseModel):
    produzem: list[Receita]
    consomem: list[Receita]


@rotas.get("", summary="Lista itens, com busca sem acento por nome pt/en/id")
async def lista(
    busca: str | None = Query(None, description="nome em português, em inglês ou id"),
    tipo: str | None = Query(None, description="valor de gk.item.tipo"),
    incluir_nao_usados: bool = Query(False, description="traz itens que o jogo não usa"),
    dlc: FiltroDlc | None = Query(None, description="id da DLC, ou 'base' para o que não é de DLC"),
    limite: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    banco: asyncpg.Pool = Depends(pool),
) -> Pagina[Item]:
    limite = min(limite, config.limite_maximo)
    filtros = (busca, tipo, incluir_nao_usados, dlc)
    total = await busca_valor(banco, consultas.CONTA_ITENS, *filtros)
    linhas = await busca_muitos(banco, consultas.LISTA_ITENS, *filtros, limite, offset)
    return Pagina(total=total, limite=limite, offset=offset,
                  dados=[Item(**linha) for linha in linhas])


@rotas.get("/{item_id}", summary="Um item pelo id do jogo")
async def detalhe(item_id: str, banco: asyncpg.Pool = Depends(pool)) -> Item:
    linha = await busca_um(banco, consultas.ITEM_POR_ID, item_id)
    if not linha:
        raise HTTPException(404, f"item '{item_id}' não existe")
    return Item(**linha)


async def receitas_dos_ids(banco: asyncpg.Pool, ids: list[str]) -> ReceitasDoItem:
    """Receitas que produzem e que consomem qualquer um dos ids."""
    produzem = await busca_muitos(banco, consultas.RECEITAS_DO_ITEM, ids, "saida")
    consomem = await busca_muitos(banco, consultas.RECEITAS_DO_ITEM, ids, "entrada")
    return ReceitasDoItem(
        produzem=[Receita(**linha) for linha in produzem],
        consomem=[Receita(**linha) for linha in consomem],
    )


@rotas.get("/{item_id}/receitas", summary="Receitas que produzem e que consomem o item")
async def receitas(item_id: str, banco: asyncpg.Pool = Depends(pool)) -> ReceitasDoItem:
    if not await busca_valor(banco, consultas.ITEM_EXISTE, item_id):
        raise HTTPException(404, f"item '{item_id}' não existe")
    return await receitas_dos_ids(banco, [item_id])
