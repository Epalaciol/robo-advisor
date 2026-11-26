"""Presentación de la página pública del Taller 2 (funciones puras, fáciles de probar)."""

import pandas as pd

COLUMNAS = {
    "nemotecnico": "Nemotécnico",
    "vencimiento": "Vencimiento",
    "origen_tasa": "Tasa",
    "cupon": "Cupón (%)",
    "precio_sucio": "Precio sucio",
    "precio_estimado": "Precio estimado",
    "tir_observada": "TIR observada",
    "tir_estimada": "TIR estimada",
    "spread_pb": "Dif. (pb)",
    "senal": "Decisión",
    "duracion_modificada": "Duración mod.",
    "convexidad": "Convexidad",
    "dv01_cop": "DV01 por 1.000'000.000 COP",
}


def pesos(x: float) -> str:
    """Formato colombiano: 653823.95 → '653.824 COP'."""
    return f"{x:,.0f}".replace(",", ".") + " COP"


def tabla_presentacion(df: pd.DataFrame) -> pd.DataFrame:
    t = df[list(COLUMNAS)].copy()
    t["tir_observada"] = (t["tir_observada"] * 100).map("{:.3f} %".format)
    t["tir_estimada"] = (t["tir_estimada"] * 100).map("{:.3f} %".format)
    t["dv01_cop"] = t["dv01_cop"].map(pesos)
    for c in ("precio_sucio", "precio_estimado"):
        t[c] = t[c].astype(float).round(3)
    for c in ("spread_pb", "duracion_modificada", "convexidad"):
        t[c] = t[c].astype(float).round(2)
    return t.rename(columns=COLUMNAS)


def conteo(df: pd.DataFrame) -> dict[str, int]:
    c = df["senal"].value_counts().to_dict()
    return {k: int(c.get(k, 0)) for k in ("Comprar", "Vender", "Mantener")}
