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
    #: Nome do sprite; o PNG sai de GET /icones/{icone}.png.
    icone: str | None = None
    #: 1, 2 ou 3 (bronze, prata, ouro).
    estrela: int | None = None
    #: Id do grupo de níveis, quando o item é um nível de qualidade.
    grupo: str | None = None
    pode_usar: bool = False
    #: Efeito de usar, por recurso; negativo é perda.
    ao_usar: dict[str, float] = {}
    ao_usar_expr: list[str] = []


class Grupo(BaseModel):
    """Item com níveis de qualidade. Nome, ícone e tipo vêm do nível mais baixo."""

    id: str
    pt: str | None
    en: str | None
    icone: str | None
    tipo: str | None
    nao_usado: bool
    niveis: int


class GrupoDetalhe(Grupo):
    #: Os níveis, do mais baixo ao mais alto.
    itens: list[Item]


class Ingrediente(BaseModel):
    ref_id: str
    pt: str | None
    en: str | None
    qtd: float | None
    qtd_max: float | None = None
    qtd_expr: str | None = None
    #: Falso quando a referência não é item (estação, ponto de fé, b_empty:1).
    e_item: bool
    #: Verdadeiro quando a ponta pede o grupo de níveis (ref_id = id do grupo).
    e_grupo: bool = False
    grupo: str | None = None
    icone: str | None = None
    estrela: int | None = None


class Estacao(BaseModel):
    id: str
    pt: str | None
    en: str | None
    #: Sprite da estação (objeto de mundo), com o fallback do próprio jogo por
    #: interaction_type — não é só custom_icon. 169 dos 228 ids têm sprite.
    icone: str | None = None


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
    pontos_tecnologia: dict[str, float | None]
    acao: str | None
    objeto_id: str | None
    objeto_pt: str | None
    objeto_en: str | None
    #: Sprite do objeto de construção (mesmo padrão de Item.icone).
    objeto_icone: str | None = None
    entradas: list[Ingrediente]
    entradas_da_estacao: list[Ingrediente]


class TecRef(BaseModel):
    id: str
    pt: str | None
    en: str | None


class TecReceita(TecRef):
    #: Falso quando o binário aponta para uma receita que não está na lista.
    existe: bool


class Tecnologia(BaseModel):
    id: str
    pt: str | None
    en: str | None
    ramo_n: int | None
    ramo_pt: str | None
    #: Sprite fixo do ramo ("i_tbranch_" + ramo_n). Sempre preenchido.
    ramo_icone: str
    custo: dict[str, float]
    oculta: bool
    requer_dlc: int
    requer: list[TecRef]
    libera_receitas: list[TecReceita]
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
