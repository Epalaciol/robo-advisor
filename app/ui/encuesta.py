"""Helpers de la encuesta: construcción del payload.

`construir_payload_encuesta` es puro (sin red) para poder probarlo con
`pytest`; el cálculo de puntaje/perfil/A sigue viviendo solo en `core/`.
El gráfico ilustrativo de utilidad vive en `ui/graficos.py` (reutilizable).
"""

from roboadvisor.core.cuestionario import ResultadoEncuesta

VERSION_CUESTIONARIO = "v1"


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
