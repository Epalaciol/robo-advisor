"""Selección de referencia de 11 activos según el perfil de riesgo (coeficiente A).

El enunciado pide un universo amplio (acciones de Colombia/Latam, EE.UU., EAFE y emergentes, TES,
renta fija IG, HY y global, REIT, cripto, etc.) y un portafolio de 11 activos. Esta sugerencia
arma esos 11 con una regla fija y explicable: **a menor A (menos aversión al riesgo) el universo se
inclina hacia activos de mayor riesgo y mayor retorno esperado**; a mayor A, hacia renta fija y
activos defensivos. Es solo un punto de partida: el usuario puede cambiarla antes de optimizar.

Validación (5 años de datos del catálogo, ventana común; ver docs/taller-1/03-motor-financiero.md):
volatilidad media anual de la selección ≈ 9 % (A=8) → 11 % (A=6) → 14 % (A=4) → 17 % (A=3) →
24 % (A=1); retorno medio histórico ≈ 8 % → 10 % → 13 % → 17 % → 18 %.
"""

# Clave: A. Cada selección tiene exactamente 11 tickers del catálogo (`supabase/seed/activos.csv`).
SELECCION_POR_A: dict[int, tuple[str, ...]] = {
    # Conservador: núcleo de renta fija (global, TIPS, agregada, Tesoros, IG, HY, emergente) + un
    # poco de acciones desarrolladas, REIT global y oro.
    8: ("BNDX", "TIP", "AGG", "IEF", "LQD", "HYG", "EMB", "SPY", "EFA", "VNQI", "GLD"),
    # Conservador a moderado: se suman TES de Colombia y REIT de EE.UU.; salen TIPS y REIT global.
    6: ("BNDX", "AGG", "IEF", "LQD", "HYG", "EMB", "SPY", "EFA", "VNQ", "GLD", "GXTESCOL.CL"),
    # Moderado: mitad renta variable (EE.UU., EAFE, emergentes, Colombia) y mitad renta fija.
    4: ("AGG", "LQD", "HYG", "EMB", "SPY", "EFA", "EEM", "VNQ", "GLD", "GXTESCOL.CL", "COLO"),
    # Moderado a agresivo: más acciones (Nasdaq, Latam) y sale la renta fija de menor retorno.
    3: ("HYG", "EMB", "SPY", "QQQ", "EFA", "EEM", "VNQ", "GLD", "GXTESCOL.CL", "COLO", "ILF"),
    # Agresivo: acciones de crecimiento (Nasdaq, semiconductores, small caps), emergentes y Latam,
    # y criptoactivos (bitcoin); sin renta fija de bajo retorno.
    1: ("SPY", "QQQ", "SMH", "IWM", "EEM", "ILF", "COLO", "GXTESCOL.CL", "VNQ", "IBIT", "GLD"),
}


def seleccion_referencia(a: float) -> list[str]:
    """Los 11 tickers sugeridos para un coeficiente A (se usa el perfil más cercano)."""
    mas_cercano = min(SELECCION_POR_A, key=lambda k: abs(k - a))
    return list(SELECCION_POR_A[mas_cercano])
