"""Configuración común a ambos talleres: credenciales de Supabase (mismo proyecto).

`Settings` lee credenciales de Supabase desde `.env` (nunca hardcodeadas).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Credenciales de Supabase. `service_role` solo la usa el pipeline, nunca la app."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_DB_URL: str | None = None
