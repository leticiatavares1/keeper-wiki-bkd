"""As DLCs do jogo e quanto de cada coisa é de cada uma.

A DLC de receita, estação e item é deduzida, não vem do jogo: a regra está em
db/015-dlc.sql e no README.
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from .. import consultas
from ..db import busca_muitos, pool
from ..modelos import Dlc

rotas = APIRouter(prefix="/dlcs", tags=["dlcs"])


@rotas.get("", summary="As quatro DLCs, na ordem do jogo, com as contagens")
async def lista(banco: asyncpg.Pool = Depends(pool)) -> list[Dlc]:
    linhas = await busca_muitos(banco, consultas.LISTA_DLCS)
    return [Dlc(**linha) for linha in linhas]
