"""Parámetros del Taller 1 (robo-advisor Markowitz): tasa libre de riesgo y motor financiero.

`ParametrosFinancieros` reúne los parámetros del motor (ver docs/taller-1/00 §4 y docs/taller-1/03)
para que no queden "mágicos" dispersos en el código.
"""

from dataclasses import dataclass

# Tasa libre de riesgo del proyecto: rendimiento del T-note de EE.UU. a 10 años (Yahoo `^TNX`).
RF_TICKER = "^TNX"
RF_NOMBRE = "T-note de EE.UU. a 10 años"
RF_FUENTE = f"yahoo:{RF_TICKER}"

# Portafolio de referencia: 11 ETF (el número del enunciado) sin apalancamiento y con ≥ 5 años de
# historia, que cubren las clases del enunciado. Es el mismo para todos los perfiles, así se ve cómo
# cambia y* con A sin que cambie el universo. Con los 25 activos elegibles del catálogo el Sharpe
# máximo es el mismo que con estos 11 (ver docs/taller-1/03 §11).
UNIVERSO_REFERENCIA: dict[str, str] = {
    "QQQ": "Acciones EE.UU. (Nasdaq 100)",
    "SMH": "Acciones EE.UU. (semiconductores)",
    "COLO": "Acciones Colombia (MSCI Colombia)",
    "ILF": "Acciones Latinoamérica",
    "EFA": "Acciones EAFE (desarrollados ex-EE.UU.)",
    "EEM": "Acciones mercados emergentes",
    "LQD": "Renta fija grado de inversión EE.UU.",
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
    # Peso mínimo por activo elegido. Sin piso (0 %) Markowitz con retornos históricos deja
    # portafolios extremos (40-40-20 en 3 de 11 activos); con 5 % entran todos los elegidos.
    w_min: float = 0.05
    w_max: float = 0.40
    n_min_activos: int = 3
    n_max_activos: int = 11
    umbral_desvio: float = 0.05
    min_peso_alerta: float = 0.05
    peso_min_guardado: float = 0.0005  # activos por debajo de esto no se guardan (≈ 0 %)
    tol_vol: float = 0.25
    dias_stale: int = 5
    tilt_multiplos: float = 0.025
    # P/E relativo al índice mundial (ACWI): < 0,85 → barata; > 1,15 → cara (informe del Taller 1)
    pe_relativo_barata: float = 0.85
    pe_relativo_cara: float = 1.15
    min_obs_pe: int = 12  # fotos previas de P/E propio para dar señal (≈ 3 meses semanales)
    benchmark: str = "ACWI"

    @property
    def meses_historia(self) -> int:
        """Meses de precios a pedir para cubrir la ventana (con margen de 6)."""
        return self.ventana_dias // 21 + 6
