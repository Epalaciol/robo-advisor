"""TALLER 2 · Curva cero cupón de TES (Nelson-Siegel), TIR, decisión y DV01.

Página **pública**: no pide inicio de sesión (no llama a `requerir_sesion`). Solo lee las
tablas `t2_*` con el cliente `anon` (RLS: SELECT público). Funciona igual con `MOCK_DATA=true`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime as dt  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.comun.estilos import AVISO_ACADEMICO, configurar_pagina, pie_de_pagina  # noqa: E402
from ui.taller2.tes import conteo, pesos, tabla_presentacion  # noqa: E402

from roboadvisor.comun.cliente import cliente_anon  # noqa: E402
from roboadvisor.taller2.core.modelos import Betas  # noqa: E402
from roboadvisor.taller2.core.nelson_siegel import spot  # noqa: E402
from roboadvisor.taller2.datos.repositorio import RepositorioTES  # noqa: E402
from roboadvisor.taller2.reportes import graficas  # noqa: E402

configurar_pagina("Curva TES · Taller 2")
st.title("Taller 2 · Curva cero cupón de TES tasa fija en pesos")
st.caption(
    "Modelo Nelson-Siegel sobre el Informe Diario de Deuda Pública (www.irc.gov.co). "
    "Sección pública: no requiere iniciar sesión. " + AVISO_ACADEMICO
)


@st.cache_data(ttl=3600, show_spinner=False)
def _curvas() -> pd.DataFrame:
    return RepositorioTES(cliente_anon()).curvas()


@st.cache_data(ttl=3600, show_spinner=False)
def _tabla(fecha: dt.date) -> pd.DataFrame:
    return RepositorioTES(cliente_anon()).tabla_dia(fecha)


@st.cache_data(ttl=3600, show_spinner=False)
def _informe(fecha: dt.date) -> dict | None:
    return RepositorioTES(cliente_anon()).informe(fecha)


try:
    curvas = _curvas()
except Exception as error:  # noqa: BLE001 — sin conexión o sin migración 0003
    st.error(f"No se pudieron leer los datos del Taller 2: {error}")
    st.stop()

if curvas.empty:
    st.info("Aún no hay curvas calculadas. Corre el pipeline del Taller 2 (ver README).")
    st.stop()

fechas = sorted(curvas["fecha"], reverse=True)
col_f, col_t = st.columns([3, 1])
with col_f:
    fecha = st.selectbox(
        "Fecha del informe", fechas, index=0, format_func=lambda f: f.strftime("%d-%m-%Y")
    )
with col_t:
    claro = st.toggle("Gráficas con fondo claro", value=True)
tema = "claro" if claro else "oscuro"
TEMA_ST = None if claro else "streamlit"  # None: Streamlit no impone su tema oscuro

hoy = dt.date.today()
habiles = sum(
    1 for d in range((hoy - fechas[0]).days) if (fechas[0] + dt.timedelta(d + 1)).weekday() < 5
)
if habiles > 5:
    st.warning(
        f"El último informe cargado es del {fechas[0]:%d-%m-%Y} ({habiles} días hábiles atrás). "
        "IRC suele publicar con unos días de retraso."
    )

c = curvas[curvas["fecha"] == fecha].iloc[0]
betas = Betas(float(c["b0"]), float(c["b1"]), float(c["b2"]))
tabla = _tabla(fecha)
cuenta = conteo(tabla) if not tabla.empty else {"Comprar": 0, "Vender": 0, "Mantener": 0}

m = st.columns(6)
m[0].metric("β0 (nivel)", f"{betas.b0:.2%}")
m[1].metric("β1 (pendiente)", f"{betas.b1:.2%}")
m[2].metric("β2 (curvatura)", f"{betas.b2:.2%}")
m[3].metric("τ", f"{c['tau']:.2f}")
m[4].metric("RMSE de precio", f"{c['rmse']:.3f}")
m[5].metric("Umbral", f"±{c['umbral_pb']:.1f} pb", help=f"Regla: {c['regla_umbral']}")
st.caption(
    f"{int(c['n_papeles'])} papeles en la curva · Comprar {cuenta['Comprar']} · "
    f"Vender {cuenta['Vender']} · Mantener {cuenta['Mantener']} · "
    f"Tasa spot a 1, 5 y 10 años: "
    + " · ".join(f"{spot(float(p), betas, float(c['tau'])):.3%}" for p in (1, 5, 10))
)

pest = st.tabs(["Curva y decisiones", "Tabla por papel", "Historia", "Cómo leer esto"])
with pest[0]:
    st.plotly_chart(
        graficas.figura_curva_desde(betas, float(c["tau"]), tabla, tema=tema),
        use_container_width=True,
        theme=TEMA_ST,
    )
    if not tabla.empty:
        res = SimpleNamespace(tabla=tabla, umbral_pb=float(c["umbral_pb"]))
        st.plotly_chart(
            graficas.figura_spreads(res, tema=tema), use_container_width=True, theme=TEMA_ST
        )
with pest[1]:
    if tabla.empty:
        st.info("Sin resultados por papel para esta fecha.")
    else:
        st.dataframe(tabla_presentacion(tabla), hide_index=True, use_container_width=True)
        st.caption(
            "DV01: lo que gana (o pierde), en COP, una posición de "
            "**1.000'000.000 COP (mil millones de pesos) de valor nominal**"
            f" si la TIR baja (sube) 1 pb. Mayor DV01 del día: "
            f"{pesos(float(tabla['dv01_cop'].max()))}."
        )
        st.download_button(
            "Descargar CSV",
            tabla.to_csv(index=False).encode("utf-8"),
            file_name=f"tes_{fecha.isoformat()}.csv",
            mime="text/csv",
        )
    inf = _informe(fecha)
    if inf and inf.get("hallazgos"):
        with st.expander(f"Validaciones del informe ({len(inf['hallazgos'])} avisos)"):
            st.dataframe(pd.DataFrame(inf["hallazgos"]), hide_index=True)
with pest[2]:
    if len(curvas) < 2:
        st.info("Se necesitan al menos dos fechas para ver la historia.")
    else:
        st.plotly_chart(
            graficas.figura_betas_tiempo(curvas, tema=tema), use_container_width=True, theme=TEMA_ST
        )
        st.plotly_chart(
            graficas.figura_spot_plazos(curvas, tema=tema), use_container_width=True, theme=TEMA_ST
        )
        st.plotly_chart(
            graficas.figura_curvas_superpuestas(curvas, tema=tema), use_container_width=True
        )
with pest[3]:
    st.markdown(
        """
- **Curva cero cupón**: tasa a la que se descuenta un peso que se recibe en *t* años.
  Nelson-Siegel: `S(t) = β0 + β1·(1−e^(−t/τ))/(t/τ) + β2·[(1−e^(−t/τ))/(t/τ) − e^(−t/τ)]`,
  con τ = 3,7 fijo. β0 es el nivel de largo plazo, β0 + β1 la tasa de muy corto plazo.
- **Calibración**: β0, β1 y β2 minimizan la suma de (precio sucio observado − precio con la curva)²,
  igual que el Solver del Excel del profesor.
- **TIR observada vs. estimada**: TIR del precio sucio del mercado vs. TIR del precio que da
  la curva. Plazos en días / 365 **sin contar los 29 de febrero** (convención del mercado de TES,
  NL/365): con ella la TIR del precio publicado coincide con la tasa SEN de IRC.
- **Decisión**: si la TIR observada supera la estimada en más del umbral, el papel está
  barato frente a la curva → *Comprar*; si es menor por más del umbral → *Vender*.
  El umbral por defecto es 1 desviación estándar de las diferencias del día.
- **DV01** por 1.000'000.000 COP (mil millones de pesos) de nominal, por revaluación
  con ±½ pb en la TIR.
- Las decisiones cambian bastante con el método de calibración y el umbral: son salidas
  de un modelo, **no recomendaciones de inversión**.
"""
    )

pie_de_pagina()
