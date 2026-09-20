"""Formato das respostas. Os nomes de campo são os mesmos do schema gk."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    total: int
    limite: int
    offset: int
    dados: list[T]


class Item(BaseModel):
    id: str
    pt: str | None
    en: str | None
    descricao_pt: str | None = None
    descricao_en: str | None = None
    tipo: str
    preco_base: float
    qualidade: float
    pilha: int
    eficiencia: float
    tem_durabilidade: bool
    nao_usado: bool
    tipos_de_produto: list[str]


class Ingrediente(BaseModel):
    ref_id: str
    pt: str | None
    en: str | None
    qtd: float | None
    qtd_max: float | None = None
    qtd_expr: str | None = None
    #: Falso quando a referência não é item (estação, ponto de fé, b_empty:1).
    e_item: bool


class Estacao(BaseModel):
    id: str
    pt: str | None
    en: str | None


class EstacaoContada(Estacao):
    receitas: int


class ReceitaResumo(BaseModel):
    id: str
    origem: str
    tipo: str
    oculta: bool
    estacoes: list[Estacao]
    saidas: list[Ingrediente]


class Receita(ReceitaResumo):
    tempo_s: float | None
    tempo_expr: str | None
    energia: float | None
    energia_expr: str | None
    sanidade: float | None
    dificuldade: float | None
    precisa_desbloquear: bool
    perks: list[str]
    liberada_por: list[str]
    pontos_tecnologia: dict[str, float]
    acao: str | None
    objeto_id: str | None
    objeto_pt: str | None
    objeto_en: str | None
    entradas: list[Ingrediente]
    entradas_da_estacao: list[Ingrediente]


class Tecnologia(BaseModel):
    id: str
    pt: str | None
    en: str | None
    ramo_n: int | None
    ramo_pt: str | None
    custo: dict[str, float]
    oculta: bool
    requer_dlc: int
    requer: list[str]
    libera_receitas: list[str]
    libera_perks: list[str]


class Importacao(BaseModel):
    feita_em: datetime
    build_do_jogo: str | None
    fonte: str
    itens: int
    receitas: int
    tecnologias: int


class Saude(BaseModel):
    ok: bool
    banco: str
    somente_leitura: bool
