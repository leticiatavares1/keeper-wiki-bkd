"""Grupos de níveis de qualidade: "Abóbora" reúne pumpkin_crop:1, :2 e :3."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import consultas
from ..config import config
from ..db import busca_muitos, busca_um, busca_valor, pool
from ..modelos import Grupo, GrupoDetalhe, Item, Pagina
from .itens import ReceitasDoItem, receitas_dos_ids

rotas = APIRouter(prefix="/grupos", tags=["grupos"])


@rotas.get("", summary="Lista os itens que têm níveis de qualidade")
async def lista(
    incluir_nao_usados: bool = Query(False, description="traz grupos que o jogo não usa"),
    limite: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    banco: asyncpg.Pool = Depends(pool),
) -> Pagina[Grupo]:
    limite = min(limite, config.limite_maximo)
    total = await busca_valor(banco, consultas.CONTA_GRUPOS, incluir_nao_usados)
    linhas = await busca_muitos(banco, consultas.LISTA_GRUPOS, incluir_nao_usados, limite, offset)
    return Pagina(total=total, limite=limite, offset=offset,
                  dados=[Grupo(**linha) for linha in linhas])


@rotas.get("/{grupo_id}", summary="Um grupo, com os níveis do mais baixo ao mais alto")
async def detalhe(grupo_id: str, banco: asyncpg.Pool = Depends(pool)) -> GrupoDetalhe:
    linha = await busca_um(banco, consultas.GRUPO_POR_ID, grupo_id)
    if not linha:
        raise HTTPException(404, f"grupo '{grupo_id}' não existe")
    niveis = await busca_muitos(banco, consultas.NIVEIS_DO_GRUPO, grupo_id)
    return GrupoDetalhe(**linha, itens=[Item(**n) for n in niveis])


@rotas.get("/{grupo_id}/receitas",
           summary="Receitas do grupo inteiro: as que pedem um nível e as que pedem o grupo")
async def receitas(grupo_id: str, banco: asyncpg.Pool = Depends(pool)) -> ReceitasDoItem:
    if not await busca_valor(banco, consultas.GRUPO_EXISTE, grupo_id):
        raise HTTPException(404, f"grupo '{grupo_id}' não existe")
    niveis = await busca_muitos(banco, consultas.IDS_DO_GRUPO, grupo_id)
    return await receitas_dos_ids(banco, [grupo_id, *(n["id"] for n in niveis)])
