"""Configuração vinda do ambiente (.env em desenvolvimento)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Credencial da API. É a do papel keeper_api, que só tem SELECT no schema gk.
    # Nunca aponte para o dono do banco: a API não escreve, por construção.
    database_url: str = "postgresql://keeper_api@localhost:5432/porti"

    # Origens liberadas no CORS. Vazio = nenhuma, que é o caso quando o
    # keeper-wiki-fnd consome a API só no build (adapter-static).
    cors_origens: list[str] = []

    pool_min: int = 1
    pool_max: int = 8

    # Teto do `limite` das listagens.
    limite_maximo: int = 500

    # Pasta dos PNGs dos ícones (volume somente leitura, ver compose.yaml).
    icones_dir: str = "/icones"

    titulo: str = "Keeper Wiki API"
    raiz: str = ""


config = Config()
