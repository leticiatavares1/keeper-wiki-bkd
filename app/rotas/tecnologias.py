"""Tecnologias da árvore de pesquisa."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import consultas
from ..config import config
from ..db import busca_muitos, busca_um, busca_valor, pool
from ..modelos import FiltroDlc, Pagina, Tecnologia

rotas = APIRouter(prefix="/tecnologias", tags=["tecnologias"])


@rotas.get("", summary="Lista tecnologias, filtrando por ramo da árvore")
async def lista(
    busca: str | None = Query(None),
    ramo: int | None = Query(None, description="número do ramo (gk.tecnologia.ramo_n)"),
    incluir_ocultas: bool = Query(False),
    dlc: FiltroDlc | None = Query(None, description="id da DLC, ou 'base' para o que não é de DLC"),
    limite: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    banco: asyncpg.Pool = Depends(pool),
) -> Pagina[Tecnologia]:
    limite = min(limite, config.limite_maximo)
    filtros = (busca, ramo, incluir_ocultas, dlc)
    total = await busca_valor(banco, consultas.CONTA_TECNOLOGIAS, *filtros)
    linhas = await busca_muitos(banco, consultas.LISTA_TECNOLOGIAS, *filtros, limite, offset)
    return Pagina(total=total, limite=limite, offset=offset,
                  dados=[Tecnologia(**linha) for linha in linhas])


@rotas.get("/{tecnologia_id:path}", summary="Uma tecnologia pelo id do jogo")
async def detalhe(tecnologia_id: str, banco: asyncpg.Pool = Depends(pool)) -> Tecnologia:
    linha = await busca_um(banco, consultas.TECNOLOGIA_POR_ID, tecnologia_id)
    if not linha:
        raise HTTPException(404, f"tecnologia '{tecnologia_id}' não existe")
    return Tecnologia(**linha)
