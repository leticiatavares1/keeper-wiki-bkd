"""Ícones (PNG) dos itens, servidos de uma pasta somente leitura.

Não vêm do banco: são arquivos extraídos pelo `../reveng-graveyard-keeper`
(`out/gk1/icones/`), montados no container em `ICONES_DIR`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import config

rotas = APIRouter(prefix="/icones", tags=["ícones"])

# O jogo não muda com a API no ar: um dia de cache no navegador/nginx basta.
CACHE = "public, max-age=86400"


class ListaIcones(BaseModel):
    total: int
    dados: list[str]


@lru_cache(maxsize=1)
def _nomes() -> dict[str, Path]:
    """Nome do sprite (sem extensão) -> arquivo. Só o que existe na pasta.

    Lido uma vez: a pasta é somente leitura e varrê-la a cada request custa
    segundos num bind mount do Docker Desktop. Trocou os PNGs? Reinicie a API.
    """
    pasta = Path(config.icones_dir)
    if not pasta.is_dir():
        return {}
    return {p.stem: p for p in pasta.glob("*.png") if p.is_file()}


@rotas.get("", summary="Nomes dos sprites disponíveis, sem extensão")
async def lista() -> ListaIcones:
    nomes = sorted(_nomes())
    return ListaIcones(total=len(nomes), dados=nomes)


@rotas.get("/{nome}.png", summary="O PNG de um sprite", response_class=FileResponse)
async def png(nome: str) -> FileResponse:
    # O nome só vale se for um arquivo que a listagem conhece: nada do que o
    # cliente digita vira caminho no disco (sem `..`, sem `/`).
    arquivo = _nomes().get(nome)
    if arquivo is None:
        raise HTTPException(404, f"ícone '{nome}' não existe")
    return FileResponse(arquivo, media_type="image/png",
                        headers={"Cache-Control": CACHE})
