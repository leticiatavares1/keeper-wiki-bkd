"""A aplicação. Só leitura: nenhuma rota é POST, PUT, PATCH ou DELETE."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .db import abre_pool
from .rotas import dlcs, grupos, icones, itens, receitas, saude, tecnologias

DESCRICAO = """
Dado do **Graveyard Keeper** tirado do binário do jogo
(`../reveng-graveyard-keeper`), servido para a wiki `../keeper-wiki-fnd`.

A API não escreve no banco: conecta com um papel que só tem `SELECT`.
Quem carrega o dado é `scripts/importa.py`, com outra credencial.
"""


@asynccontextmanager
async def ciclo(app: FastAPI):
    app.state.pool = await abre_pool()
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(
    title=config.titulo,
    description=DESCRICAO,
    version="0.1.0",
    root_path=config.raiz,
    lifespan=ciclo,
)

if config.cors_origens:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origens,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

app.include_router(saude.rotas)
app.include_router(icones.rotas)
app.include_router(grupos.rotas)
app.include_router(itens.rotas)
app.include_router(receitas.rotas)
app.include_router(tecnologias.rotas)
app.include_router(dlcs.rotas)
