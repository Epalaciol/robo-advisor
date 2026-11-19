"""Administración (solo lectura): portafolios y cálculos de cualquier usuario.

Solo para cuentas marcadas en `public.administradores` (migración 0004). La seguridad la da RLS: un
usuario normal que abra esta página solo vería sus propias filas y además se le niega el acceso
aquí. Se muestran alias y rango de edad, nunca correos. No se modifica nada.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.comun.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.comun.estilos import AVISO_ACADEMICO, configurar_pagina, pie_de_pagina  # noqa: E402
from ui.taller1.graficos import MODO_BASE_100, figura_comportamiento, figura_composicion  # noqa: E402
from ui.taller1.resultado import calcular_resultado, mostrar_resultado  # noqa: E402

from roboadvisor.taller1.config import RF_NOMBRE, ParametrosFinancieros  # noqa: E402
from roboadvisor.taller1.core.cuestionario import PREGUNTAS, puntuar  # noqa: E402
from roboadvisor.taller1.data.repositorio_mercado import RepositorioMercado  # noqa: E402
from roboadvisor.taller1.data.repositorio_usuario import RepositorioUsuario  # noqa: E402
from roboadvisor.taller1.data.servicio_portafolio import ResumenPortafolio, construir_resumen  # noqa: E402

PARAMS = ParametrosFinancieros()
ETIQUETA_PREGUNTA = {
    "q1": "1", "q2a": "2A", "q2b": "2B", "q2c": "2C", "q3": "3", "q4": "4", "q5": "5", "q6": "6",
    "q7": "7",
}  # fmt: skip

configurar_pagina("Administración")
requerir_sesion()

cliente = cliente_sesion_actual()
mi_id = st.session_state.get("user_id")
if not RepositorioUsuario(cliente, mi_id).es_admin():
    st.title("Administración")
    st.warning("Esta sección es solo para administradores.")
    st.stop()

repo_mercado = RepositorioMercado(cliente)
st.title("Administración · portafolios de los usuarios")
st.caption(
    "Vista de solo lectura para revisar la encuesta, el portafolio y los cálculos de cada persona. "
    "Se muestran alias y rango de edad (no correos). " + AVISO_ACADEMICO
)


@st.cache_data(ttl=300, show_spinner="Cargando usuarios...")
def _usuarios(_repo: RepositorioUsuario, mi_id: str) -> list[dict]:
    # Sin la propia cuenta ni las de prueba (marcadas con scripts/taller1/marcar_usuarios_prueba.py)
    return [
        u
        for u in _repo.listar_usuarios()
        if u["user_id"] != mi_id and not (u.get("factores") or {}).get("_prueba")
    ]


def _origen(portafolio: dict | None) -> str:
    if not portafolio:
        return "—"
    return "asignado" if (portafolio.get("parametros") or {}).get("origen") else "propio"


usuarios = _usuarios(RepositorioUsuario(cliente, mi_id), mi_id)
filas = []
for u in usuarios:
    e, p = u["encuesta"], u["portafolio"]
    filas.append(
        {
            "Alias": u["alias"],
            "Edad": u["edad_rango"],
            "Puntaje": e["puntaje"] if e else None,
            "Perfil": e["perfil"] if e else "sin encuesta",
            "A": float(e["a"]) if e else None,
            "Portafolio": _origen(p),
            "y*": float(p["y_star"]) if p else None,
            "Fecha base": p["fecha_base"] if p else "—",
        }
    )
tabla = pd.DataFrame(filas)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Registrados", len(usuarios))
c2.metric("Con encuesta", sum(1 for u in usuarios if u["encuesta"]))
c3.metric("Con portafolio", sum(1 for u in usuarios if u["portafolio"]))
c4.metric("Portafolio propio", sum(1 for u in usuarios if _origen(u["portafolio"]) == "propio"))

st.subheader("Todos los usuarios")
if tabla.empty:
    st.info("Aún no hay usuarios registrados.")
    pie_de_pagina()
    st.stop()
st.dataframe(
    tabla.sort_values(["Edad", "Alias"]).style.format({"y*": "{:.1%}", "A": "{:g}"}, na_rep="—"),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Detalle de una persona")
con_encuesta = [u for u in usuarios if u["encuesta"]]
etiquetas = {
    f"{u['alias']} · {u['edad_rango']} · {u['encuesta']['perfil']}": u
    for u in sorted(con_encuesta, key=lambda x: (x["edad_rango"], x["alias"]))
}
if not etiquetas:
    st.info("Nadie ha respondido la encuesta todavía.")
    pie_de_pagina()
    st.stop()
u = etiquetas[st.selectbox("Persona", list(etiquetas))]
encuesta, portafolio = u["encuesta"], u["portafolio"]
a = float(encuesta["a"])

tab_encuesta, tab_calculo, tab_construccion, tab_seguimiento = st.tabs(
    ["Encuesta y A", "Portafolio registrado y y*", "Construcción (lo que vio)", "Seguimiento"]
)

with tab_encuesta:
    respuestas = encuesta["respuestas"]
    resultado = puntuar(respuestas)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Pregunta": ETIQUETA_PREGUNTA[p.id],
                    "Respuesta": respuestas[p.id],
                    "Opción escogida": p.opciones[respuestas[p.id]],
                    "Puntos": {"a": 1, "b": 2, "c": 3}[respuestas[p.id]],
                }
                for p in PREGUNTAS
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    n = resultado.conteo
    st.markdown(
        f"**Puntaje** = 1·{n['a']} + 2·{n['b']} + 3·{n['c']} = **{resultado.puntaje}** → "
        f"perfil **{resultado.etiqueta}** → **A = {resultado.a}**"
    )
    st.latex(rf"U = E(r) - \tfrac{{1}}{{2}}\cdot {a:g}\cdot \sigma^2")
    factores = {
        k: v
        for k, v in (u.get("factores") or {}).items()
        if str(v).strip() and not k.startswith("_")
    }
    if factores:
        st.markdown("**Información personal**")
        st.dataframe(
            pd.DataFrame({"Factor": list(factores), "Respuesta": list(factores.values())}),
            hide_index=True,
        )

with tab_calculo:
    if not portafolio:
        st.info("Esta persona aún no tiene portafolio.")
    else:
        par = portafolio.get("parametros") or {}
        met = portafolio.get("metricas") or {}
        st.caption(
            f"Portafolio **{_origen(portafolio)}** · datos al {portafolio['fecha_base']} · "
            f"{par.get('n_obs_usadas', '—')} días · pesos entre {par.get('w_min', 0):.0%} y "
            f"{par.get('w_max', 0):.0%} · tasa libre de riesgo {par.get('rf', 0):.2%} ({RF_NOMBRE})"
        )
        pesos = pd.Series(portafolio["pesos_riesgo"], dtype=float).sort_values(ascending=False)
        col1, col2 = st.columns(2)
        col1.plotly_chart(
            figura_composicion(pesos, "Portafolio de riesgo óptimo"), use_container_width=True
        )
        completo = pd.Series(portafolio["pesos_completo"], dtype=float)
        completo["Libre de riesgo"] = float(portafolio["peso_rf"])
        col2.plotly_chart(
            figura_composicion(completo.sort_values(ascending=False), "Portafolio completo"),
            use_container_width=True,
        )
        e_p, s_p = met.get("retorno_riesgo"), met.get("sigma_riesgo")
        rf = par.get("rf")
        if None not in (e_p, s_p, rf):
            y_formula = (e_p - rf) / (a * s_p**2)
            st.markdown("**Cálculo de y\\***")
            st.latex(
                rf"y^* = \frac{{E(R_P) - r_f}}{{A\,\sigma_P^2}} = "
                rf"\frac{{{e_p:.4f} - {rf:.4f}}}{{{a:g}\times {s_p:.4f}^2}} = {y_formula:.3f}"
            )
            if y_formula > 1:
                st.warning(
                    f"La fórmula da **{y_formula:.1%}**: esta persona querría endeudarse a la tasa "
                    f"libre de riesgo para invertir más que su capital. Sin apalancamiento se "
                    f"limita a **100 %**."
                )
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("E(Rp) · σp", f"{e_p:.1%} · {s_p:.1%}")
            m2.metric("Sharpe de P", f"{met.get('sharpe_riesgo', float('nan')):.2f}")
            m3.metric("y* aplicado", f"{float(portafolio['y_star']):.1%}")
            m4.metric("Utilidad U", f"{met.get('utilidad', float('nan')):.4f}")
            st.caption(
                f"Portafolio completo: E(Rc) = {met.get('retorno_completo', float('nan')):.2%} · "
                f"σc = {met.get('sigma_completo', float('nan')):.2%}"
            )
        st.markdown("**Composición del portafolio completo**")
        st.dataframe(
            pd.DataFrame(
                {
                    "Peso en P": pesos,
                    "Peso en el portafolio completo": completo.drop("Libre de riesgo"),
                }
            )
            .reindex([*pesos.index])
            .style.format("{:.1%}"),
            use_container_width=True,
        )


with tab_construccion:
    if not portafolio:
        st.info("Esta persona aún no tiene portafolio.")
    else:
        par = portafolio.get("parametros") or {}
        universo = par.get("universo") or list(portafolio["tickers"])
        st.caption(
            "Reconstrucción con **los mismos datos y parámetros** con que esta persona armó su "
            f"portafolio: {len(universo)} activos ({', '.join(sorted(universo))}), precios hasta "
            f"{portafolio['fecha_base']}, pesos entre {par.get('w_min', 0):.0%} y "
            f"{par.get('w_max', PARAMS.w_max):.0%} y tasa libre de riesgo "
            f"{par.get('rf', 0):.2%}. Es la misma vista del Constructor."
        )
        catalogo_por_ticker = {x["ticker"]: x for x in repo_mercado.listar_catalogo()}
        try:
            res = calcular_resultado(
                repo_mercado,
                catalogo_por_ticker,
                tuple(sorted(universo)),
                portafolio["fecha_base"],
                float(par.get("rf", repo_mercado.rf_ultima())),
                float(par.get("w_max", PARAMS.w_max)),
                float(par.get("w_min", 0.0)),
                int(par.get("ventana_dias", PARAMS.ventana_dias)),
                int(par.get("min_dias", PARAMS.min_dias)),
                PARAMS.benchmark,
                hasta=portafolio["fecha_base"],
            )
        except Exception:
            st.error("No fue posible reconstruir la optimización de este portafolio.")
        else:
            guardado = pd.Series(portafolio["pesos_riesgo"], dtype=float)
            dif = (res["port_tangente"].w.reindex(guardado.index).fillna(0) - guardado).abs().max()
            if dif > 0.01:
                st.caption(
                    f"Nota: los pesos recalculados difieren hasta {dif:.1%} de los registrados "
                    "(los precios históricos pueden haberse ajustado después)."
                )
            mostrar_resultado(res, a, PARAMS, clave=f"admin_{u['user_id']}")


@st.cache_data(ttl=600, show_spinner="Calculando seguimiento...")
def _seguimiento(user_id: str, ultima_fecha: str | None) -> ResumenPortafolio:
    return construir_resumen(RepositorioUsuario(cliente, user_id), repo_mercado, PARAMS)


with tab_seguimiento:
    if not portafolio:
        st.info("Esta persona aún no tiene portafolio.")
    else:
        try:
            r = _seguimiento(u["user_id"], repo_mercado.ultima_fecha_precios())
        except Exception:
            st.error("No fue posible calcular el seguimiento de este portafolio.")
        else:
            if not r.seguimiento.suficiente:
                st.info("Aún no hay suficientes días desde que se armó el portafolio.")
            else:
                s = r.seguimiento
                m1, m2, m3 = st.columns(3)
                m1.metric("Retorno acumulado", f"{s.retorno_acum:.1%}")
                vol = s.vol_realizada
                m2.metric("Volatilidad realizada", "—" if vol != vol else f"{vol:.1%}")
                m3.metric("Máxima caída", f"{s.max_drawdown:.1%}")
                st.plotly_chart(
                    figura_comportamiento(
                        s.valor,
                        r.seguimiento_benchmark.valor if r.seguimiento_benchmark else None,
                        r.benchmark,
                        None,
                        MODO_BASE_100,
                    ),
                    use_container_width=True,
                )
            st.markdown("**Recomendaciones (reglas fijas)**")
            for rec in r.recomendaciones:
                st.markdown(
                    f"- **{rec.titulo}**{' — ' + rec.ticker if rec.ticker else ''}: {rec.detalle}"
                )

pie_de_pagina()
