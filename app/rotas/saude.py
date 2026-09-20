"""Saúde e procedência do dado."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from .. import consultas
from ..db import busca_um, busca_valor, pool
from ..modelos import Importacao, Saude

rotas = APIRouter(tags=["meta"])


@rotas.get("/saude", summary="A API responde e o banco está acessível")
async def saude(banco: asyncpg.Pool = Depends(pool)) -> Saude:
    try:
        leitura = await busca_valor(banco, "SHOW default_transaction_read_only")
    except Exception as erro:  # noqa: BLE001 - qualquer falha aqui é "banco fora"
        raise HTTPException(503, f"banco inacessível: {erro}") from erro
    return Saude(ok=True, banco="ok", somente_leitura=leitura == "on")


@rotas.get("/meta", summary="De qual extração veio o dado que está no ar")
async def meta(banco: asyncpg.Pool = Depends(pool)) -> Importacao:
    linha = await busca_um(banco, consultas.ULTIMA_IMPORTACAO)
    if not linha:
        raise HTTPException(503, "banco ainda sem importação; rode scripts/importa.py")
    return Importacao(**linha)
