"""Parámetros del Taller 1 (robo-advisor Markowitz): tasa libre de riesgo y motor financiero.

`ParametrosFinancieros` reúne los parámetros del motor (ver docs/taller-1/00 §4 y docs/taller-1/03)
para que no queden "mágicos" dispersos en el código.
"""

from dataclasses import dataclass

# Tasa libre de riesgo del proyecto: rendimiento del T-note de EE.UU. a 10 años (Yahoo `^TNX`).
RF_TICKER = "^TNX"
RF_NOMBRE = "T-note de EE.UU. a 10 años"
RF_FUENTE = f"yahoo:{RF_TICKER}"

# Portafolio de referencia: 11 ETF (el número del enunciado), uno o dos por clase de activo. Es el
# mismo para todos los perfiles, así se ve cómo cambia y* con A sin que cambie el universo.
UNIVERSO_REFERENCIA: dict[str, str] = {
    "SPY": "Acciones EE.UU. (S&P 500)",
    "QQQ": "Acciones EE.UU. (Nasdaq 100)",
    "EFA": "Acciones EAFE (desarrollados ex-EE.UU.)",
    "EEM": "Acciones mercados emergentes",
    "ILF": "Acciones Latinoamérica",
    "LQD": "Renta fija grado de inversión EE.UU.",
    "IEF": "Bonos del Tesoro EE.UU. 7-10 años",
    "HYG": "Renta fija alto rendimiento (HY) EE.UU.",
    "EMB": "Renta fija emergente en USD",
    "VNQ": "REIT (finca raíz EE.UU.)",
    "GLD": "Oro",
}


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
    peso_min_guardado: float = 0.0005  # activos por debajo de esto no se guardan (≈ 0 %)
    tol_vol: float = 0.25
    dias_stale: int = 5
    tilt_multiplos: float = 0.025
    min_obs_pe: int = 12  # fotos previas de P/E propio para dar señal (≈ 3 meses semanales)
    benchmark: str = "ACWI"

    @property
    def meses_historia(self) -> int:
        """Meses de precios a pedir para cubrir la ventana (con margen de 6)."""
        return self.ventana_dias // 21 + 6
