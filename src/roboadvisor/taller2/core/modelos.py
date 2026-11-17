"""Tipos del motor del Taller 2. Puros: sin red, sin Supabase, sin Streamlit."""

from dataclasses import dataclass
from datetime import date

import numpy as np


@dataclass(frozen=True)
class Papel:
    """Un TES de la tabla "Tasa Fija en Pesos" del informe diario (por $100 de facial)."""

    nemotecnico: str
    vencimiento: date
    cupon: float  # % del facial; 0 en los TCO
    precio_sucio: float
    precio_limpio: float | None = None
    duracion_informe: float | None = None  # Macaulay, redondeada a 2 decimales en el informe
    tasa_pub: float | None = None  # decimal (11,607 % → 0.11607)
    origen_tasa: str | None = None  # "VAL" o "SEN"
    valor_nominal_mm: int | None = None  # millones de COP, saldo en circulación

    @property
    def tipo(self) -> str:
        for prefijo in ("TCO", "TFIT", "TFVT", "TUVT"):
            if self.nemotecnico.startswith(prefijo):
                return prefijo
        return self.nemotecnico[:4]


@dataclass(frozen=True)
class Flujos:
    """Flujos futuros de un papel: fechas, tiempo en años (días/365) y montos por $100."""

    fechas: tuple[date, ...]
    t: np.ndarray
    montos: np.ndarray


@dataclass(frozen=True)
class Betas:
    b0: float
    b1: float
    b2: float

    def como_tupla(self) -> tuple[float, float, float]:
        return (self.b0, self.b1, self.b2)


@dataclass(frozen=True)
class Calibracion:
    betas: Betas
    tau: float
    sse: float  # Σ (P_sucio − P_est)², sin ponderar (como la celda del Solver)
    rmse: float
    n: int
    convergio: bool
    arranque: tuple[float, float, float]
    ponderacion: str
    usar_origen: str
