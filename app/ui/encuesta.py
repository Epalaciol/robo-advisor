"""Helpers de la encuesta: construcción del payload y gráfico ilustrativo.

`construir_payload_encuesta` es puro (sin red) para poder probarlo con
`pytest`; el cálculo de puntaje/perfil/A sigue viviendo solo en `core/`.
"""

import numpy as np
import plotly.graph_objects as go

from roboadvisor.core.cuestionario import ResultadoEncuesta
from roboadvisor.core.utilidad import utilidad

VERSION_CUESTIONARIO = "v1"
ER_ILUSTRATIVO = 0.08  # solo para el gráfico explicativo de U vs σ, no es un cálculo real


def construir_payload_encuesta(
    user_id: str,
    resultado: ResultadoEncuesta,
    respuestas: dict[str, str],
    version_cuestionario: str = VERSION_CUESTIONARIO,
) -> dict:
    """Fila lista para `encuestas.insert(...)` a partir de un `ResultadoEncuesta`."""
    return {
        "user_id": user_id,
        "respuestas": respuestas,
        "puntaje": resultado.puntaje,
        "perfil": resultado.perfil,
        "a": resultado.a,
        "version_cuestionario": version_cuestionario,
    }


def figura_utilidad_vs_sigma(a: float, er: float = ER_ILUSTRATIVO) -> go.Figure:
    """Curva ilustrativa `U = er − ½·A·σ²` para el `A` del usuario, a un `er` fijo."""
    sigmas = np.linspace(0.01, 0.40, 50)
    utilidades = [utilidad(er, float(s), a) for s in sigmas]

    fig = go.Figure(go.Scatter(x=sigmas, y=utilidades, mode="lines"))
    fig.update_layout(
        title=f"Utilidad vs σ (ilustrativo, A={a}, E(r)={er:.0%})",
        xaxis_title="σ (desviación estándar)",
        yaxis_title="Utilidad U",
        xaxis_tickformat=".0%",
    )
    return fig
