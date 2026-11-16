"""Cuestionario de aversión al riesgo del Taller 1, su puntaje y mapeo a perfil.

Las 9 preguntas están transcritas literalmente del PDF "Formato para medición
de aversión al riesgo". Cada respuesta vale: a=1, b=2, c=3.
Puntaje total 9–27 → perfil → coeficiente de aversión A (ver docs/02).
"""

from dataclasses import dataclass, field

IDS_PREGUNTAS: list[str] = ["q1", "q2a", "q2b", "q2c", "q3", "q4", "q5", "q6", "q7"]

OPCIONES_VALIDAS = {"a", "b", "c"}


@dataclass(frozen=True)
class Pregunta:
    """Un ítem del cuestionario con sus 3 opciones (a/b/c)."""

    id: str
    texto: str
    opciones: dict[str, str]


PREGUNTAS: list[Pregunta] = [
    Pregunta(
        id="q1",
        texto=(
            "Justo 60 días después de usted haber hecho una inversión, el precio de "
            "ésta cae el 20%. Asumiendo que ninguno de los factores fundamentales de "
            "la economía ha cambiado, ¿usted qué haría?"
        ),
        opciones={
            "a": "Vender para evitar mayores pérdidas e intentar con otra inversión",
            "b": "No hace nada y espera que la inversión se recupere",
            "c": (
                "Compra más. Si antes de que el precio cayera era una buena "
                "inversión, ahora es todavía más atractiva"
            ),
        },
    ),
    Pregunta(
        id="q2a",
        texto=(
            "De una mirada otra vez a la pregunta anterior, pero desde otro punto de "
            "vista. Su inversión cayó el 20%, pero ésta es parte de un portafolio que "
            "está siendo usado para cumplir con objetivos de inversión con tres "
            "horizontes de tiempo distintos. ¿Qué haría usted si el objetivo estuviera "
            "cinco años más adelante?"
        ),
        opciones={"a": "Vender", "b": "No hace nada", "c": "Compra más"},
    ),
    Pregunta(
        id="q2b",
        texto="¿Qué haría usted si el objetivo estuviera quince años más adelante?",
        opciones={"a": "Vender", "b": "No hace nada", "c": "Compra más"},
    ),
    Pregunta(
        id="q2c",
        texto="¿Qué haría usted si el objetivo estuviera treinta años más adelante?",
        opciones={"a": "Vender", "b": "No hace nada", "c": "Compra más"},
    ),
    Pregunta(
        id="q3",
        texto=(
            "El valor de su inversión en el fondo de pensiones voluntarias se dispara "
            "el 25% al poco tiempo de usted haber hecho un depósito inicial importante. "
            "De nuevo los fundamentales no han cambiado. ¿Qué haría usted?"
        ),
        opciones={
            "a": "Retiraría el dinero del fondo asegurando la ganancia",
            "b": "Se quedaría quieto, esperando valorizaciones adicionales",
            "c": (
                "Haría depósitos adicionales esperando que éstos tengan la misma "
                "suerte del depósito inicial"
            ),
        },
    ),
    Pregunta(
        id="q4",
        texto=(
            "Usted espera retirarse dentro de quince años y está ahorrando para cuando "
            "llegue ese día. ¿Qué opción tomaría usted?"
        ),
        opciones={
            "a": (
                "Invierte en un fondo a la vista muy seguro, sacrificando ganancias "
                "importantes, pero asegurando el principal invertido"
            ),
            "b": (
                "Invierte en un fondo que invierte el 50% en bonos y el otro 50% en "
                "acciones. Esto con el fin de obtener algún crecimiento en su capital, "
                "pero con la protección que otorga la inversión en bonos"
            ),
            "c": (
                "Invierte en un fondo de crecimiento agresivo. En un fondo como estos "
                "las perspectivas de crecimiento en un horizonte de 10 años son "
                "impresionantes, pero por su alto riesgo es posible que durante el año "
                "se presenten fuertes fluctuaciones"
            ),
        },
    ),
    Pregunta(
        id="q5",
        texto=(
            "Usted acaba de ganarse un tremendo premio. Pero ¿cuál? Esto depende del "
            "que usted escoja"
        ),
        opciones={
            "a": "$2.000.000 en efectivo",
            "b": "Una ganancia de $5.000.000 con una probabilidad del 50%",
            "c": "Una ganancia de $15.000.000 con una probabilidad del 20%",
        },
    ),
    Pregunta(
        id="q6",
        texto=(
            "Se le acaba de presentar una excelente oportunidad de inversión, pero "
            "usted no tiene en este momento dinero para participar de ésta. Por lo "
            "tanto, usted tiene que ir al banco a pedir dinero prestado si quiere hacer "
            "la inversión. Sobre la perspectiva de tomar este préstamo, usted:"
        ),
        opciones={
            "a": "Definitivamente no lo tomaría",
            "b": "Quizás sí lo tomaría",
            "c": "Definitivamente sí lo tomaría",
        },
    ),
    Pregunta(
        id="q7",
        texto=(
            "La compañía donde usted trabaja está vendiéndole acciones a los "
            "empleados. En tres años la gerencia de la empresa espera haber crecido "
            "tanto que la compañía podrá ser inscrita en la Bolsa de Valores. Durante "
            "esos tres años usted no puede vender las acciones que compre ahora y no "
            "recibirá ningún dividendo. Sin embargo, si la compañía es efectivamente "
            "inscrita en la Bolsa, su inversión en ese momento se podría multiplicar "
            "por 10. ¿Cuánto dinero invertiría usted?"
        ),
        opciones={
            "a": "Nada",
            "b": "El equivalente a dos meses de su salario",
            "c": "El equivalente a cuatro meses de su salario",
        },
    ),
]

# (puntaje_min, puntaje_max, clave_perfil, etiqueta, A) — ver docs/02 §Mapeo del puntaje al perfil
PERFILES: list[tuple[int, int, str, str, int]] = [
    (9, 12, "conservador", "Conservador", 8),
    (13, 16, "conservador_moderado", "Conservador a Moderado", 6),
    (17, 20, "moderado", "Moderado", 4),
    (21, 24, "moderado_agresivo", "Moderado a Agresivo", 3),
    (25, 27, "agresivo", "Agresivo", 1),
]

FACTORES_SUGERIDOS: list[str] = [
    "ocupacion",
    "rango_ingresos",
    "dependientes_economicos",
    "nivel_educativo",
    "experiencia_invirtiendo_anios",
    "horizonte_principal_inversion",
    "colchon_emergencia",
]

# Opciones de cada factor para un desplegable (dropdown) en la UI: listas
# cerradas, más fáciles de llenar y más fáciles de analizar entre los 5
# voluntarios que texto libre. Solo metadatos para la UI; no afectan el cálculo.
OPCIONES_FACTORES: dict[str, list[str]] = {
    "ocupacion": [
        "Empleado/a",
        "Independiente / freelance",
        "Empresario/a",
        "Estudiante",
        "Jubilado/a",
        "Desempleado/a",
        "Otro",
    ],
    "rango_ingresos": [
        "Menos de $2.000.000",
        "$2.000.000 - $4.000.000",
        "$4.000.000 - $8.000.000",
        "$8.000.000 - $15.000.000",
        "Más de $15.000.000",
        "Prefiero no decir",
    ],
    "dependientes_economicos": ["0", "1", "2", "3", "4 o más"],
    "nivel_educativo": [
        "Bachillerato",
        "Técnico/tecnólogo",
        "Pregrado",
        "Especialización",
        "Maestría",
        "Doctorado",
    ],
    "experiencia_invirtiendo_anios": [
        "Sin experiencia",
        "Menos de 1 año",
        "1 a 3 años",
        "3 a 5 años",
        "5 a 10 años",
        "Más de 10 años",
    ],
    "horizonte_principal_inversion": [
        "Menos de 1 año",
        "1 a 3 años",
        "3 a 5 años",
        "5 a 10 años",
        "10 a 20 años",
        "Más de 20 años",
    ],
    "colchon_emergencia": ["Sí", "No"],
}


@dataclass(frozen=True)
class ResultadoEncuesta:
    """Resultado de puntuar una encuesta de aversión al riesgo."""

    puntaje: int
    perfil: str
    etiqueta: str
    a: int
    conteo: dict[str, int] = field(default_factory=dict)


def _perfil_desde_puntaje(puntaje: int) -> tuple[str, str, int]:
    for minimo, maximo, clave, etiqueta, a in PERFILES:
        if minimo <= puntaje <= maximo:
            return clave, etiqueta, a
    raise ValueError(f"Puntaje fuera de rango 9-27: {puntaje}")


def puntuar(respuestas: dict[str, str]) -> ResultadoEncuesta:
    """Calcula puntaje, perfil y A a partir de las respuestas del cuestionario.

    `puntaje = 1·#a + 2·#b + 3·#c`. Lanza `ValueError` si faltan ids, sobran ids
    o algún valor no es "a"/"b"/"c".
    """
    ids_esperados = set(IDS_PREGUNTAS)
    ids_recibidos = set(respuestas.keys())

    faltantes = ids_esperados - ids_recibidos
    if faltantes:
        raise ValueError(f"Faltan respuestas para: {sorted(faltantes)}")

    sobrantes = ids_recibidos - ids_esperados
    if sobrantes:
        raise ValueError(f"Ids de pregunta desconocidos: {sorted(sobrantes)}")

    invalidas = {k: v for k, v in respuestas.items() if v not in OPCIONES_VALIDAS}
    if invalidas:
        raise ValueError(f"Valores inválidos (deben ser a/b/c): {invalidas}")

    conteo = {"a": 0, "b": 0, "c": 0}
    for valor in respuestas.values():
        conteo[valor] += 1

    puntaje = conteo["a"] * 1 + conteo["b"] * 2 + conteo["c"] * 3
    clave, etiqueta, a = _perfil_desde_puntaje(puntaje)

    return ResultadoEncuesta(puntaje=puntaje, perfil=clave, etiqueta=etiqueta, a=a, conteo=conteo)
