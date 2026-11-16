"""
Taller 2 – Inversiones (MFAC, EAFIT)
Curva cero cupón de TES tasa fija en pesos con el modelo de Nelson-Siegel

Qué hace el código (los mismos pasos que el Excel "Modelo Nelson Siegel.xlsx"):
  1. Lee el informe diario de deuda pública (www.irc.gov.co) de un día cualquiera,
     en PDF o en Excel, y toma la tabla "Tasa Fija en Pesos" (TCO y TFIT/TFVT).
  2. Construye los flujos de cada bono (cupones anuales + 100 al vencimiento).
  3. Estima los betas de Nelson-Siegel minimizando la suma de errores al cuadrado
     entre el precio sucio observado y el precio teórico (tau fijo = 3,7).
  4. Calcula la curva cero cupón (1 a 10.950 días).
  5. Calcula la TIR observada (con el precio sucio) y la TIR estimada (con el
     precio de la curva) y decide comprar / vender / mantener.
  6. Calcula duración, convexidad y el DV01 por cada $1.000 millones de nominal.
  7. Exporta todo a Excel y una gráfica.

Uso:
    python taller2_nelson_siegel.py Informe_Diario_02_de_Octubre_de_2026.pdf
    python taller2_nelson_siegel.py informe.xlsx --fecha 2026-10-02
    python taller2_nelson_siegel.py informe.pdf --umbral 10        (umbral fijo en pb)
    python taller2_nelson_siegel.py informe.pdf --solo-sen         (curva solo con bonos transados)

Requisitos:  pip install numpy pandas scipy matplotlib openpyxl pdfplumber
"""

import argparse
import datetime as dt
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize

# ----------------------------------------------------------------------------
# 0. Parámetros del modelo
# ----------------------------------------------------------------------------
TAU = 3.7                                    # fijo, como en el Excel del profesor
BETAS_INICIALES = [0.12002, 0.01472, 0.03446]  # punto de partida para el optimizador
DIAS_ANO = 365                               # convención del Excel: días / 365
NOMINAL_DV01 = 1_000_000_000                 # DV01 por cada $1.000 millones
PB = 0.0001                                  # 1 punto básico

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
         "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
         "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}


# ----------------------------------------------------------------------------
# 1. Lectura del informe diario
# ----------------------------------------------------------------------------
def _numero(texto):
    """'5.351.599' -> 5351599 ; '99,430' -> 99.43 (formato colombiano)."""
    return float(str(texto).replace(".", "").replace(",", "."))


def _corregir_fecha(fecha):
    """Excel a veces convierte '18-sep-30' en 1930. Se corrige a 20xx."""
    if fecha.year < 2000:
        fecha = fecha.replace(year=fecha.year + 100)
    return fecha


def _fecha_en_texto(texto):
    """Busca 'viernes, 2 de octubre de 2026' dentro de un texto."""
    m = re.search(r"(\d{1,2}) de ([a-záéíóú]+) de (\d{4})", texto.lower())
    if m and m.group(2) in MESES:
        return dt.date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
    return None


def leer_pdf(ruta):
    import pdfplumber
    with pdfplumber.open(ruta) as pdf:
        texto = pdf.pages[0].extract_text()
    fecha = _fecha_en_texto(texto)
    patron = re.compile(
        r"(\d{1,2})-([a-z]{3})-(\d{2})\s+(T(?:CO|FIT|FVT)\w+)\s+([\d.]+)\s+([\d,]+)\s+"
        r"([\d.,]+)\s+([\d.,]+)\s+([\d,]+)\s+([\d,]+)\s+(VAL|SEN)")
    filas = []
    for linea in texto.splitlines():
        m = patron.search(linea)
        if m:
            g = m.groups()
            filas.append(dict(
                vencimiento=dt.date(2000 + int(g[2]), MESES[g[1]], int(g[0])),
                nemotecnico=g[3], nominal=_numero(g[4]), cupon=_numero(g[5]),
                limpio=_numero(g[6]), sucio=_numero(g[7]), duracion_inf=_numero(g[8]),
                tasa_inf=_numero(g[9]), mercado=g[10]))
    return pd.DataFrame(filas), fecha


def leer_excel(ruta):
    """Sirve para el Excel que se descarga del IRC (las columnas cambian de lugar
    según el día): en cada fila busca la fecha y lee los valores que le siguen."""
    import openpyxl
    wb = openpyxl.load_workbook(ruta, data_only=True)
    filas, fecha = [], None
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            celdas = [c for c in row if c is not None]
            if fecha is None:
                for c in celdas:
                    if isinstance(c, str):
                        fecha = _fecha_en_texto(c) or fecha
            for i, c in enumerate(celdas[:-1]):
                nemo = celdas[i + 1]
                if isinstance(c, dt.datetime) and isinstance(nemo, str) \
                        and re.match(r"T(CO|FIT|FVT)", nemo):
                    v = celdas[i + 2:]
                    nums = [x for x in v if isinstance(x, (int, float))]
                    mercado = next((x for x in v if x in ("SEN", "VAL")), None)
                    filas.append(dict(
                        vencimiento=_corregir_fecha(c.date()), nemotecnico=nemo,
                        nominal=nums[0], cupon=nums[1], limpio=nums[2], sucio=nums[3],
                        duracion_inf=nums[4], tasa_inf=nums[5] if len(nums) > 5 else np.nan,
                        mercado=mercado))
                    break
        if filas:
            break
    return pd.DataFrame(filas), fecha


def leer_informe(ruta, fecha=None):
    ruta = Path(ruta)
    df, fecha_leida = (leer_pdf if ruta.suffix.lower() == ".pdf" else leer_excel)(ruta)
    fecha = fecha or fecha_leida
    if fecha is None:
        raise ValueError("No encontré la fecha del informe: pásala con --fecha AAAA-MM-DD")
    # Un TCO es cero cupón: si el informe trae otro valor es un error de transcripción
    malos = df["nemotecnico"].str.startswith("TCO") & (df["cupon"] != 0)
    for nemo in df.loc[malos, "nemotecnico"]:
        print(f"  ! {nemo} es TCO pero trae cupón ≠ 0 en el informe: se corrige a 0")
    df.loc[malos, "cupon"] = 0.0
    return df.reset_index(drop=True), fecha


# ----------------------------------------------------------------------------
# 2. Flujos de cada bono
# ----------------------------------------------------------------------------
def generar_flujos(vencimiento, cupon, fecha_val):
    """Desde el vencimiento se resta un año hasta pasar la fecha de valoración.
    Solo cuentan las fechas POSTERIORES a la valoración. El último flujo es cupón + 100."""
    flujos, f = [], vencimiento
    while f > fecha_val:
        flujos.append((f, cupon + (100 if f == vencimiento else 0)))
        f = f.replace(year=f.year - 1)
    flujos.sort()
    fechas = [x[0] for x in flujos]
    montos = np.array([x[1] for x in flujos], dtype=float)
    t = np.array([(x - fecha_val).days for x in fechas]) / DIAS_ANO
    return fechas, montos, t


# ----------------------------------------------------------------------------
# 3. Nelson-Siegel y precio teórico
# ----------------------------------------------------------------------------
def tasa_spot(t, b0, b1, b2, tau=TAU):
    x = np.asarray(t, dtype=float) / tau
    carga = (1 - np.exp(-x)) / x
    return b0 + b1 * carga + b2 * (carga - np.exp(-x))


def precio_curva(t, montos, betas, tau=TAU):
    s = tasa_spot(t, *betas, tau=tau)
    return float(np.sum(montos / (1 + s) ** t))


def suma_errores2(betas, bonos, tau=TAU):
    return sum((b["sucio"] - precio_curva(b["t"], b["montos"], betas, tau)) ** 2
               for b in bonos)


def estimar_betas(bonos, tau=TAU, inicial=BETAS_INICIALES):
    """Equivale a Solver: minimiza la suma de errores² cambiando b0, b1, b2.
    Se prueban varios puntos de partida para no quedarse en un mínimo local."""
    mejor = None
    for x0 in [inicial, [0.13, -0.01, 0.0], [0.12, 0.0, 0.0], [0.14, -0.03, 0.02]]:
        r = minimize(suma_errores2, x0, args=(bonos, tau), method="Nelder-Mead",
                     options=dict(xatol=1e-12, fatol=1e-12, maxiter=40000))
        if mejor is None or r.fun < mejor.fun:
            mejor = r
    return mejor.x, mejor.fun


# ----------------------------------------------------------------------------
# 4. TIR, duración, convexidad y DV01
# ----------------------------------------------------------------------------
def valor_presente(y, t, montos):
    return float(np.sum(montos / (1 + y) ** t))


def tir(precio, t, montos):
    """Equivale a TIR.NO.PER de Excel: la tasa que iguala los flujos al precio."""
    return brentq(lambda y: valor_presente(y, t, montos) - precio, -0.5, 2.0)


def duracion_macaulay(y, t, montos):
    vp = montos / (1 + y) ** t
    return float(np.sum(t * vp) / np.sum(vp))


def convexidad(y, t, montos):
    vp = montos / (1 + y) ** t
    return float(np.sum(t * (t + 1) * vp) / (np.sum(vp) * (1 + y) ** 2))


# ----------------------------------------------------------------------------
# 5. Modelo completo
# ----------------------------------------------------------------------------
def correr_modelo(ruta, fecha=None, tau=TAU, umbral="sigma", solo_sen=False):
    df, fecha = leer_informe(ruta, fecha)
    print(f"Informe del {fecha:%d-%m-%Y}: {len(df)} bonos de tasa fija en pesos")

    bonos = []
    for _, r in df.iterrows():
        fechas, montos, t = generar_flujos(r["vencimiento"], r["cupon"], fecha)
        bonos.append(dict(r, fechas=fechas, montos=montos, t=t))

    # Estimación de la curva (con todos los bonos o solo con los transados)
    usados = [b for b in bonos if (b["mercado"] == "SEN" or not solo_sen)]
    betas, sse = estimar_betas(usados, tau)
    print(f"Betas: b0={betas[0]:.6f}  b1={betas[1]:.6f}  b2={betas[2]:.6f}  "
          f"tau={tau}  | suma errores² = {sse:.6f}  ({len(usados)} bonos)")

    filas, tabla_flujos = [], []
    for i, b in enumerate(bonos, start=1):
        t, m = b["t"], b["montos"]
        p_est = precio_curva(t, m, betas, tau)
        tir_obs, tir_est = tir(b["sucio"], t, m), tir(p_est, t, m)
        d_mac = duracion_macaulay(tir_obs, t, m)
        d_mod = d_mac / (1 + tir_obs)
        # DV01 como en el Excel (col. P y Q): duración del informe / (1 + TIR) × sucio × 1000
        d_mod_inf = b["duracion_inf"] / (1 + tir_obs)
        dv01_excel = d_mod_inf * b["sucio"] * PB * NOMINAL_DV01 / 100
        # DV01 exacto: por fórmula (duración calculada) y por revaluación (±0,5 pb)
        dv01_formula = d_mod * b["sucio"] * PB * NOMINAL_DV01 / 100
        dv01_reval = (valor_presente(tir_obs - PB / 2, t, m)
                      - valor_presente(tir_obs + PB / 2, t, m)) * NOMINAL_DV01 / 100
        # Validación: cupón corrido = sucio - limpio
        ultimo_cupon = b["fechas"][0].replace(year=b["fechas"][0].year - 1)
        corrido = b["cupon"] * (fecha - ultimo_cupon).days / DIAS_ANO if b["cupon"] else 0
        filas.append(dict(
            bono=i, nemotecnico=b["nemotecnico"], vencimiento=b["vencimiento"],
            mercado=b["mercado"], cupon=b["cupon"], n_flujos=len(m),
            precio_limpio=b["limpio"], precio_sucio=b["sucio"], precio_estimado=p_est,
            error=b["sucio"] - p_est, error2=(b["sucio"] - p_est) ** 2,
            tir_observada=tir_obs, tir_estimada=tir_est,
            dif_pb=(tir_obs - tir_est) / PB,
            duracion_macaulay=d_mac, duracion_informe=b["duracion_inf"],
            duracion_modificada_informe=d_mod_inf, dv01_excel=dv01_excel,
            duracion_modificada=d_mod, convexidad=convexidad(tir_obs, t, m),
            dv01_formula=dv01_formula, dv01_revaluacion=dv01_reval,
            tasa_informe=b["tasa_inf"] / 100,
            control_cupon_corrido=b["limpio"] + corrido - b["sucio"]))
        for f, monto, tt in zip(b["fechas"], m, t):
            s = tasa_spot(tt, *betas, tau=tau)
            tabla_flujos.append(dict(bono=i, nemotecnico=b["nemotecnico"], fecha_flujo=f,
                                     flujo=monto, dias=round(tt * DIAS_ANO), anos=tt,
                                     tasa_spot=s, factor_desc=1 / (1 + s) ** tt,
                                     valor_presente=monto / (1 + s) ** tt))
    res = pd.DataFrame(filas)

    # Decisión: comprar si TIR obs > TIR est por más del umbral, vender si es menor
    u = res["dif_pb"].std(ddof=1) if umbral == "sigma" else float(umbral)
    res["decision"] = np.where(res["dif_pb"] > u, "Comprar",
                               np.where(res["dif_pb"] < -u, "Vender", "Mantener"))
    print(f"Umbral de decisión: ±{u:.2f} pb "
          f"({'1 desviación estándar' if umbral == 'sigma' else 'fijo'})")

    dias = np.arange(1, 30 * DIAS_ANO + 1)
    curva = pd.DataFrame(dict(dias=dias, anos=dias / DIAS_ANO,
                              tasa_spot=tasa_spot(dias / DIAS_ANO, *betas, tau=tau)))
    return dict(fecha=fecha, betas=betas, tau=tau, sse=sse, umbral=u, resultados=res,
                flujos=pd.DataFrame(tabla_flujos), curva=curva, solo_sen=solo_sen)


# ----------------------------------------------------------------------------
# 6. Sensibilidad de tau (análisis adicional)
# ----------------------------------------------------------------------------
def sensibilidad_tau(ruta, fecha=None, taus=(0.5, 1, 1.5, 2, 2.5, 3, 3.7, 4.5, 5, 6, 8, 10)):
    df, fecha = leer_informe(ruta, fecha)
    bonos = []
    for _, r in df.iterrows():
        _, m, t = generar_flujos(r["vencimiento"], r["cupon"], fecha)
        bonos.append(dict(sucio=r["sucio"], montos=m, t=t))
    filas = []
    for tau in taus:
        b, sse = estimar_betas(bonos, tau)
        filas.append(dict(tau=tau, joroba_en_anos=1.7934 * tau, b0=b[0], b1=b[1], b2=b[2],
                          suma_errores2=sse))
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------
# 7. Salidas: Excel y gráfica
# ----------------------------------------------------------------------------
def exportar(m, sens=None, carpeta="."):
    carpeta = Path(carpeta)
    nombre = f"resultados_NS_{m['fecha']:%Y%m%d}{'_soloSEN' if m['solo_sen'] else ''}"
    params = pd.DataFrame(dict(
        parametro=["fecha_valoracion", "b0", "b1", "b2", "tau", "suma_errores2",
                   "umbral_pb", "curva_solo_SEN"],
        valor=[m["fecha"], *m["betas"], m["tau"], m["sse"], m["umbral"], m["solo_sen"]]))
    with pd.ExcelWriter(carpeta / f"{nombre}.xlsx") as xl:
        params.to_excel(xl, sheet_name="Parametros", index=False)
        m["resultados"].to_excel(xl, sheet_name="Resultados", index=False)
        m["flujos"].to_excel(xl, sheet_name="Flujos", index=False)
        m["curva"].to_excel(xl, sheet_name="Curva", index=False)
        if sens is not None:
            sens.to_excel(xl, sheet_name="Sensibilidad_tau", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = m["resultados"]
    plazo = res["vencimiento"].apply(lambda v: (v - m["fecha"]).days / DIAS_ANO)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(m["curva"]["anos"], m["curva"]["tasa_spot"] * 100, color="#1F3864", lw=2,
            label="Curva cero cupón (Nelson-Siegel)")
    colores = {"Comprar": "#2E7D32", "Vender": "#C62828", "Mantener": "#9E9E9E"}
    for dec, c in colores.items():
        for merc, marca in (("SEN", "o"), ("VAL", "^")):
            sel = (res["decision"] == dec) & (res["mercado"] == merc)
            if sel.any():
                ax.scatter(plazo[sel], res.loc[sel, "tir_observada"] * 100, color=c,
                           marker=marca, s=45, zorder=3, label=f"{dec} ({merc})")
    ax.set_xlabel("Plazo (años)")
    ax.set_ylabel("Tasa (%)")
    ax.set_title(f"TES tasa fija COP – {m['fecha']:%d-%m-%Y}: curva cero cupón y TIR observadas")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(carpeta / f"{nombre}.png", dpi=150)
    print(f"Archivos guardados: {nombre}.xlsx y {nombre}.png")


# ----------------------------------------------------------------------------
# 8. Comparación con el Excel (Libro-taller2.xlsx, Hoja1)
#    Columnas: F precio sucio · H precio estimado · I TIR obs · J TIR est
#              K dif pb · L decisión · N umbral · Q DV01 · B35:E35 parámetros
# ----------------------------------------------------------------------------
def comparar_con_excel(modelo, ruta_excel, hoja="Hoja1", fila_ini=3):
    import openpyxl
    ws = openpyxl.load_workbook(ruta_excel, data_only=True)[hoja]
    res = modelo["resultados"]
    n = len(res)
    col = lambda letra: [ws[f"{letra}{fila_ini + i}"].value for i in range(n)]
    xl = pd.DataFrame(dict(nemo=col("B"), precio_estimado=col("H"), tir_observada=col("I"),
                           tir_estimada=col("J"), dif_pb=col("K"), decision=col("L"),
                           dv01=col("Q")))
    print("\nComparación Python vs. Excel")
    betas_xl = [ws[c].value for c in ("B35", "C35", "D35")]
    print(f"  betas Excel : {np.round(betas_xl, 6)}")
    print(f"  betas Python: {np.round(modelo['betas'], 6)}")
    print(f"  umbral Excel (N3) = {ws['N3'].value}  |  Python = {modelo['umbral']:.4f}")
    for py, x in [("precio_estimado", "precio_estimado"), ("tir_observada", "tir_observada"),
                  ("tir_estimada", "tir_estimada"), ("dif_pb", "dif_pb"), ("dv01_excel", "dv01")]:
        dif = (res[py] - pd.to_numeric(xl[x])).abs().max()
        print(f"  máx. diferencia {py:16s}: {dif:.6g}")
    malas = res.index[res["decision"].values != xl["decision"].values]
    if len(malas):
        print(f"  ! Decisiones distintas en {len(malas)} bonos (filas Excel "
              f"{', '.join(str(fila_ini + i) for i in malas)}): revisa la celda del umbral")
    else:
        print("  Decisiones: todas iguales")


# ----------------------------------------------------------------------------
# 9. Ejecución
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Curva cero cupón TES con Nelson-Siegel")
    ap.add_argument("informe", help="Informe diario del IRC (.pdf o .xlsx)")
    ap.add_argument("--fecha", help="Fecha de valoración AAAA-MM-DD (si no está en el informe)")
    ap.add_argument("--tau", type=float, default=TAU)
    ap.add_argument("--umbral", default="sigma", help="'sigma' (1 desv. estándar) o un número en pb")
    ap.add_argument("--solo-sen", action="store_true", help="Estimar la curva solo con bonos SEN")
    ap.add_argument("--sin-sensibilidad", action="store_true")
    ap.add_argument("--comparar", help="Excel del taller (Libro-taller2.xlsx) para comparar resultados")
    a = ap.parse_args()

    fecha = dt.date.fromisoformat(a.fecha) if a.fecha else None
    modelo = correr_modelo(a.informe, fecha, a.tau, a.umbral, a.solo_sen)
    pd.set_option("display.width", 200)
    print(modelo["resultados"][["nemotecnico", "mercado", "precio_sucio", "precio_estimado",
                                "tir_observada", "tir_estimada", "dif_pb", "decision",
                                "dv01_excel"]].round(4).to_string(index=False))
    if a.comparar:
        comparar_con_excel(modelo, a.comparar)
    sens = None if a.sin_sensibilidad else sensibilidad_tau(a.informe, fecha)
    exportar(modelo, sens)
