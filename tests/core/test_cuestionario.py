import pytest

from roboadvisor.core.cuestionario import IDS_PREGUNTAS, puntuar


def _respuestas(valor: str) -> dict[str, str]:
    return dict.fromkeys(IDS_PREGUNTAS, valor)


def test_todas_a_da_conservador():
    r = puntuar(_respuestas("a"))
    assert r.puntaje == 9
    assert r.perfil == "conservador"
    assert r.a == 8


def test_todas_c_da_agresivo():
    r = puntuar(_respuestas("c"))
    assert r.puntaje == 27
    assert r.perfil == "agresivo"
    assert r.a == 1


@pytest.mark.parametrize(
    "puntaje,num_b,num_c,perfil_esperado,a_esperado",
    [
        (12, 3, 0, "conservador", 8),
        (13, 4, 0, "conservador_moderado", 6),
        (16, 7, 0, "conservador_moderado", 6),
        (17, 8, 0, "moderado", 4),
        (20, 7, 2, "moderado", 4),
        (21, 6, 3, "moderado_agresivo", 3),
        (24, 3, 6, "moderado_agresivo", 3),
        (25, 0, 8, "agresivo", 1),
        (27, 0, 9, "agresivo", 1),
    ],
)
def test_bordes_de_perfil(puntaje, num_b, num_c, perfil_esperado, a_esperado):
    """Verifica los 8 puntajes borde (12/13, 16/17, 20/21, 24/25)."""
    num_a = len(IDS_PREGUNTAS) - num_b - num_c
    respuestas = {}
    ids = iter(IDS_PREGUNTAS)
    for _ in range(num_a):
        respuestas[next(ids)] = "a"
    for _ in range(num_b):
        respuestas[next(ids)] = "b"
    for _ in range(num_c):
        respuestas[next(ids)] = "c"

    r = puntuar(respuestas)
    assert r.puntaje == puntaje
    assert r.perfil == perfil_esperado
    assert r.a == a_esperado


def test_combinacion_mixta_calculada_a_mano():
    # 3 a, 4 b, 2 c = 3 + 8 + 6 = 17 -> Moderado A=4
    respuestas = dict(
        zip(
            IDS_PREGUNTAS,
            ["a", "a", "a", "b", "b", "b", "b", "c", "c"],
            strict=True,
        )
    )
    r = puntuar(respuestas)
    assert r.puntaje == 17
    assert r.perfil == "moderado"
    assert r.a == 4


def test_error_si_falta_una_pregunta():
    respuestas = _respuestas("a")
    del respuestas["q7"]
    with pytest.raises(ValueError, match="q7"):
        puntuar(respuestas)


def test_error_si_sobra_un_id():
    respuestas = _respuestas("a")
    respuestas["q8"] = "a"
    with pytest.raises(ValueError, match="q8"):
        puntuar(respuestas)


def test_error_si_valor_invalido():
    respuestas = _respuestas("a")
    respuestas["q1"] = "d"
    with pytest.raises(ValueError, match="inválidos"):
        puntuar(respuestas)
