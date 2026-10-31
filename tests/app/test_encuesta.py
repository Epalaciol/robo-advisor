import pytest
from ui.encuesta import VERSION_CUESTIONARIO, construir_payload_encuesta

from roboadvisor.core.cuestionario import IDS_PREGUNTAS, puntuar


def test_construir_payload_a_partir_de_respuestas():
    respuestas = dict.fromkeys(IDS_PREGUNTAS, "b")
    resultado = puntuar(respuestas)

    payload = construir_payload_encuesta("user-123", resultado, respuestas)

    assert payload == {
        "user_id": "user-123",
        "respuestas": respuestas,
        "puntaje": 18,
        "perfil": "moderado",
        "a": 4,
        "version_cuestionario": VERSION_CUESTIONARIO,
    }


def test_faltan_respuestas_no_calcula_payload():
    respuestas = dict.fromkeys(IDS_PREGUNTAS, "a")
    del respuestas["q5"]

    with pytest.raises(ValueError, match="q5"):
        puntuar(respuestas)
