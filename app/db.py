"""Pool de conexões. Uma coisa só, criada no lifespan do FastAPI."""

from __future__ import annotations

import json
from typing import Any

import asyncpg
from fastapi import Request

from .config import config


async def _prepara(conexao: asyncpg.Connection) -> None:
    """jsonb chega como dict em vez de string."""
    await conexao.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def abre_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        config.database_url,
        min_size=config.pool_min,
        max_size=config.pool_max,
        init=_prepara,
        command_timeout=15,
        # Terceira camada de leitura, além dos GRANTs e do ALTER ROLE do banco.
        server_settings={"default_transaction_read_only": "on",
                         "application_name": "keeper-wiki-api"},
    )


def pool(request: Request) -> asyncpg.Pool:
    """Dependência do FastAPI: o pool guardado no app.state."""
    return request.app.state.pool


async def busca_muitos(pool: asyncpg.Pool, sql: str, *args: Any) -> list[dict]:
    async with pool.acquire() as conexao:
        return [dict(linha) for linha in await conexao.fetch(sql, *args)]


async def busca_um(pool: asyncpg.Pool, sql: str, *args: Any) -> dict | None:
    async with pool.acquire() as conexao:
        linha = await conexao.fetchrow(sql, *args)
        return dict(linha) if linha else None


async def busca_valor(pool: asyncpg.Pool, sql: str, *args: Any) -> Any:
    async with pool.acquire() as conexao:
        return await conexao.fetchval(sql, *args)
