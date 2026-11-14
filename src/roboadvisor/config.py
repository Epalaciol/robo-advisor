"""Configuración: variables de entorno y parámetros financieros fijos.

`Settings` lee credenciales de Supabase desde `.env` (nunca hardcodeadas).
`ParametrosFinancieros` reúne los parámetros del motor (ver docs/00 §4 y docs/03)
para que no queden "mágicos" dispersos en el código.
"""

from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Credenciales de Supabase. `service_role` solo la usa el pipeline, nunca la app."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_DB_URL: str | None = None


@dataclass(frozen=True)
class ParametrosFinancieros:
    """Parámetros fijos del motor financiero (sin valores mágicos en el código)."""

    ventana_dias: int = 1260  # ≈ 5 años de retornos diarios (252 días/año)
    min_dias: int = 252  # ≈ 1 año; permite ETF jóvenes (IBIT, GXTESCOL)
    w_min: float = 0.0  # peso mínimo por activo elegido (0 = sin mínimo)
    w_max: float = 0.40
    n_min_activos: int = 3
    n_max_activos: int = 11
    umbral_desvio: float = 0.05
    min_peso_alerta: float = 0.05
    tol_vol: float = 0.25
    dias_stale: int = 5
    tilt_multiplos: float = 0.025
    benchmark: str = "ACWI"

    @property
    def meses_historia(self) -> int:
        """Meses de precios a pedir para cubrir la ventana (con margen de 6)."""
        return self.ventana_dias // 21 + 6
