"""Parámetros del Taller 2 (curva cero cupón Nelson-Siegel de TES tasa fija en pesos).

Todos los supuestos del modelo viven aquí (ver docs/taller-2/07-taller2-metodologia.md).
"""

from dataclasses import dataclass, field

# Betas guardados en el "Modelo Nelson Siegel.xlsx" del profesor (ejemplo del 17-mar-2026).
BETAS_EXCEL_PROFESOR = (0.12790448628048, -0.0313297355745254, 0.0436569038355564)

# 1.000'000.000 COP (mil millones de pesos) de valor nominal = 10**9 (NO 10**12, que es un billón).
NOMINAL_DV01 = 1_000_000_000

PB = 0.0001  # 1 punto básico


@dataclass(frozen=True)
class ParametrosTES:
    """Supuestos del modelo. Los valores por defecto replican el Excel del profesor."""

    tau: float = 3.7  # fijo, como en el Solver del Excel del profesor
    dias_ano: int = 365  # t = días / 365
    # Conteo de días: "NL/365" = convención del mercado de TES (sin 29 de febrero; reproduce la
    # tasa SEN de IRC) o "Act/365" = días calendario, la del Excel del profesor y del grupo.
    conteo_dias: str = "NL/365"
    dias_curva: int = 10_950  # curva de 1 a 10.950 días (30 años), hoja DatosCurvaSpot
    nominal_dv01: int = NOMINAL_DV01
    # Regla de decisión: "sigma" = 1 desviación estándar de los spreads del día (la del Excel
    # y el .py del grupo); "sigma_robusta" = 1,4826·MAD (no la infla un papel atípico);
    # o un número = umbral fijo en pb.
    umbral: str | float = "sigma"
    usar_origen: str = "todos"  # "todos" (como el Excel) o "SEN" (solo tasas de operaciones)
    ponderacion: str = "ninguna"  # "ninguna" (Excel) o "duracion" (aprox. error en tasa)
    arranques: tuple[tuple[float, float, float], ...] = field(
        default=(
            BETAS_EXCEL_PROFESOR,
            (0.13, -0.01, 0.0),
            (0.12, 0.0, 0.0),
            (0.14, -0.03, 0.02),
        )
    )
    dias_habiles_datos_viejos: int = 5
    # V1: el total publicado puede diferir de la suma de filas por redondeo a millones de la
    # fuente; tolerancia = este factor × número de filas (en millones). Más que eso = error.
    tol_total_por_fila_mm: float = 0.5
    # Cupón que se paga en la fecha del informe: entra en t = 0 si sucio − limpio ≈ cupón (± tol).
    tol_cupon_hoy: float = 0.10
