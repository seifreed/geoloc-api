"""Configuración: única fuente de verdad para las variables de entorno."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_host: str = os.environ.get("DB_HOST", "localhost")
    db_port: int = int(os.environ.get("DB_PORT", "3306"))
    db_user: str = os.environ.get("DB_USER", "geo")
    db_pass: str = os.environ.get("DB_PASS", "geo")
    db_name: str = os.environ.get("DB_NAME", "geoloc")
    api_key: str | None = os.environ.get("API_KEY") or None


settings = Settings()
