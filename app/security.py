"""Autenticación: API key por header X-API-Key (opcional)."""
import secrets

from fastapi import Header, HTTPException

from .config import settings


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    """Si API_KEY está configurada exige el header; si no, API abierta (localhost).

    Compara en tiempo constante (secrets.compare_digest) para evitar timing attacks.
    """
    if settings.api_key is None:
        return
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(401, "missing or invalid API key")
