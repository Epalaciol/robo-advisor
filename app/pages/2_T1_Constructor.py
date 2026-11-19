"""Constructor de portafolio: selección de activos, cálculo y guardado (E09)."""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.comun.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.comun.estilos import configurar_pagina, pie_de_pagina  # noqa: E402
from ui.taller1.constructor import armar_registro_portafolio  # noqa: E402
from ui.taller1.resultado import calcular_resultado, mostrar_resultado  # noqa: E402

from roboadvisor.taller1.config import (  # noqa: E402
    UNIVERSO_REFERENCIA,
    ParametrosFinancieros,
)
from roboadvisor.taller1.core.portafolio_completo import componer  # noqa: E402
from roboadvisor.taller1.core.retornos import ventana_comun  # noqa: E402
from roboadvisor.taller1.data.repositorio_mercado import RepositorioMercado  # noqa: E402
from roboadvisor.taller1.data.repositorio_usuario import RepositorioUsuario  # noqa: E402

PARAMS = ParametrosFinancieros()

configurar_pagina("Constructor")
requerir_sesion()

cliente = cliente_sesion_actual()
repo_usuario = RepositorioUsuario(cliente, st.session_state.get("user_id"))
repo_mercado = RepositorioMercado(cliente)

st.title("Construcción de portafolio")

encuesta = repo_usuario.obtener_encuesta()
if encuesta is None:
    st.info(
        "Antes de construir tu portafolio necesitamos conocer tu perfil de riesgo: "
        "son nueve preguntas breves y nos permiten ajustar la propuesta a tu forma "
        "de invertir."
    )
    if st.button("Conocer mi perfil de riesgo", type="primary"):
        st.switch_page("pages/1_T1_Encuesta.py")
    st.stop()

if repo_usuario.obtener_portafolio() is not None:
    st.info(
        "Tu portafolio ya está registrado. Puedes seguir su evolución en la sección de seguimiento."
    )
    if st.button("Ver el seguimiento de mi portafolio", type="primary"):
        st.switch_page("pages/3_T1_Mi_portafolio.py")
    st.stop()

a_usuario = float(encuesta["a"])
perfil_usuario = encuesta["perfil"]
st.caption(f"Perfil: **{perfil_usuario}** · coeficiente de aversión al riesgo A = {a_usuario}.")


@st.cache_data(show_spinner=False, ttl=3600)
def _primeras_fechas(_repo_mercado: RepositorioMercado, tickers: tuple[str, ...]) -> dict:
    return _repo_mercado.primera_fecha_por_ticker(list(tickers))


def _etiqueta_activo(a: dict, primera: pd.Timestamp | None, ultima: pd.Timestamp | None) -> str:
    extra = f", duration {a['duration']}" if a.get("duration") else ""
    base = f"{a['ticker']} — {a['nombre']} ({a['clase']}, {a['moneda']}{extra})"
    if primera is not None and ultima is not None:
        # ETF joven: se avisa en el propio selector cuánta historia tiene
        _, _, dias = ventana_comun({a["ticker"]: primera}, ultima)
        if dias < PARAMS.ventana_dias:
            base += f" · datos desde {primera:%Y-%m}"
    return base


catalogo = repo_mercado.listar_catalogo()
catalogo_por_ticker = {a["ticker"]: a for a in catalogo}
_ultima_dato = repo_mercado.ultima_fecha_precios()
_ultima_ts = pd.Timestamp(_ultima_dato) if _ultima_dato else None
primeras_fechas = _primeras_fechas(repo_mercado, tuple(sorted(catalogo_por_ticker)))
etiquetas_por_ticker = {
    a["ticker"]: _etiqueta_activo(a, primeras_fechas.get(a["ticker"]), _ultima_ts) for a in catalogo
}
tickers_por_etiqueta = {v: k for k, v in etiquetas_por_ticker.items()}

st.subheader("1. Universo de inversión (3 a 11 activos)")


if st.button("Cargar portafolio de referencia (11 ETF)"):
    st.session_state["constructor_seleccion"] = [
        etiquetas_por_ticker[t] for t in UNIVERSO_REFERENCIA if t in etiquetas_por_ticker
    ]
st.caption(
    "Son los mismos **11 ETF para todos los perfiles** (acciones de EE.UU., Colombia, "
    "Latinoamérica, desarrollados y emergentes; renta fija de grado de inversión, de alto "
    "rendimiento y emergente; REIT y oro), escogidos por maximizar el Sharpe sin "
    "apalancamiento. El portafolio de riesgo óptimo depende solo del universo y de los datos; "
    "**tu A define cuánto inviertes en él (y*)**. Tras optimizar verás una tabla con el y* de "
    "cada perfil. Puedes modificar la selección antes de optimizar."
)

seleccion_etiquetas = st.multiselect(
    "Universo de activos (por clase)",
    options=sorted(etiquetas_por_ticker.values()),
    max_selections=PARAMS.n_max_activos,
    select_all=False,  # "Select all" chocaría con el máximo de activos
    key="constructor_seleccion",
)
tickers_elegidos = [tickers_por_etiqueta[e] for e in seleccion_etiquetas]
st.caption(
    f"{len(tickers_elegidos)}/{PARAMS.n_max_activos} activos (mínimo {PARAMS.n_min_activos})"
)

ventana_ok = True
if tickers_elegidos and _ultima_ts is not None:
    elegidas = {t: primeras_fechas[t] for t in tickers_elegidos if t in primeras_fechas}
    if elegidas:
        inicio_comun, limitante, dias_comunes = ventana_comun(elegidas, _ultima_ts)
        if dias_comunes < PARAMS.min_dias:
            ventana_ok = False
            st.error(
                f"**Historia común insuficiente:** {limitante} tiene datos desde "
                f"{inicio_comun:%Y-%m-%d}, así que solo habría ≈{dias_comunes} días en común "
                f"(mínimo {PARAMS.min_dias}). Quita {limitante} o elige activos con más historia."
            )
        elif dias_comunes < PARAMS.ventana_dias:
            st.warning(
                f"**Ojo con {limitante}:** solo tiene datos desde {inicio_comun:%Y-%m-%d}. "
                "La estimación usa el periodo que tienen en común **todos** los activos "
                f"elegidos: ≈{dias_comunes} días (≈{dias_comunes / 252:.1f} años) en lugar de "
                f"{PARAMS.ventana_dias} (≈{PARAMS.ventana_dias / 252:.0f} años). Eso acorta la "
                "historia de los demás activos y hace el resultado más sensible a lo que pasó "
                "en ese tramo reciente."
            )

# Límites dinámicos según el número de activos n: el mínimo por activo no puede
# superar 1/n y el máximo no puede ser menor que 1/n (si no, no suman 100 %).
n_ref = max(len(tickers_elegidos), PARAMS.n_min_activos)
tope_min_pct = 100 // n_ref  # piso de 1/n
piso_max_pct = -(-100 // n_ref)  # techo de 1/n
st.session_state["constructor_w_min"] = min(
    max(st.session_state.get("constructor_w_min", int(PARAMS.w_min * 100)), 0), tope_min_pct
)
st.session_state["constructor_w_max"] = min(
    max(st.session_state.get("constructor_w_max", int(PARAMS.w_max * 100)), piso_max_pct), 100
)

col_min, col_max = st.columns(2)
w_min_pct = col_min.slider(
    "Peso mínimo por activo (w_min)",
    min_value=0,
    max_value=max(tope_min_pct, 1),
    step=1,
    format="%d%%",
    key="constructor_w_min",
    help=(
        "Cada activo elegido tendrá al menos este peso en el portafolio de riesgo: obliga a "
        "incluirlos a todos. 0% deja que el optimizador descarte activos. "
        f"Con {n_ref} activos el máximo posible es {tope_min_pct}% (= 1/{n_ref})."
    ),
)
w_max_pct = col_max.slider(
    "Peso máximo por activo (w_max)",
    min_value=piso_max_pct,
    max_value=100,
    step=1,
    format="%d%%",
    key="constructor_w_max",
    help=(
        "Concentración máxima por activo en la optimización de Markowitz. Un tope menor "
        "impone mayor diversificación; 100% elimina la restricción. "
        f"Con {n_ref} activos el mínimo posible es {piso_max_pct}% (= 1/{n_ref}). "
        f"Valor de referencia: {PARAMS.w_max:.0%}."
    ),
)
w_min_usuario = w_min_pct / 100
w_max_usuario = w_max_pct / 100
st.caption(
    f"Los límites se ajustan solos al número de activos ({n_ref}): el mínimo va de 0% a "
    f"{tope_min_pct}% y el máximo de {piso_max_pct}% a 100%."
)

puede_calcular = (
    PARAMS.n_min_activos <= len(tickers_elegidos) <= PARAMS.n_max_activos and ventana_ok
)
if st.button("Optimizar portafolio", disabled=not puede_calcular, type="primary"):
    ultima_fecha = repo_mercado.ultima_fecha_precios()
    rf = repo_mercado.rf_ultima()
    try:
        resultado = calcular_resultado(
            repo_mercado,
            catalogo_por_ticker,
            tuple(sorted(tickers_elegidos)),
            ultima_fecha,
            rf,
            w_max_usuario,
            w_min_usuario,
            PARAMS.ventana_dias,
            PARAMS.min_dias,
            PARAMS.benchmark,
        )
    except ValueError as error:
        st.error(f"No fue posible optimizar el portafolio: {error}")
    except Exception:
        st.error(
            "No fue posible optimizar el portafolio con esta combinación de activos. "
            "Modifique la selección o intente nuevamente en unos segundos."
        )
    else:
        st.session_state["constructor_resultado"] = resultado

resultado = st.session_state.get("constructor_resultado")
if resultado:
    st.subheader("2. Resultados de la optimización")
    mostrar_resultado(resultado, a_usuario, PARAMS)
    est = resultado["est"]
    port_tangente = resultado["port_tangente"]
    port_completo = componer(port_tangente, est.rf, a_usuario)

    st.subheader("3. Registro del portafolio")
    guardados = [t for t, w in port_tangente.w.items() if w > PARAMS.peso_min_guardado]
    descartados = [t for t in port_tangente.w.index if t not in guardados]
    st.write(
        f"Se guardarán los **{len(guardados)} activos con peso**: {', '.join(sorted(guardados))}."
        + (
            f" Quedan fuera {', '.join(sorted(descartados))} (el optimizador les asignó 0 %); "
            "el universo que elegiste se conserva como referencia."
            if descartados
            else ""
        )
    )
    confirmar = st.checkbox(
        "Entiendo que el portafolio se registra una única vez y no podrá modificarse."
    )
    if st.button("Confirmar y registrar", type="primary", disabled=not confirmar):
        params_usados = replace(
            PARAMS, w_max=resultado["w_max_usado"], w_min=resultado["w_min_usado"]
        )
        payload = armar_registro_portafolio(
            user_id=st.session_state["user_id"],
            encuesta_id=encuesta["id"],
            a_usado=a_usuario,
            perfil_usado=perfil_usuario,
            est=est,
            port_riesgo=port_tangente,
            port_completo=port_completo,
            params=params_usados,
            fecha_base=resultado["fecha_base"],
        )
        try:
            repo_usuario.guardar_portafolio(payload)
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("No fue posible registrar el portafolio. Intente nuevamente en unos segundos.")
        else:
            del st.session_state["constructor_resultado"]
            st.success("Portafolio registrado.")
            if st.button("Ver seguimiento del portafolio", type="primary"):
                st.switch_page("pages/3_T1_Mi_portafolio.py")

pie_de_pagina()
