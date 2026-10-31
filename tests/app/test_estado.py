from ui.estado import estado_usuario


class RepositorioFalso:
    def __init__(self, encuesta=None, portafolio=None):
        self._encuesta = encuesta
        self._portafolio = portafolio

    def obtener_encuesta(self):
        return self._encuesta

    def obtener_portafolio(self):
        return self._portafolio


def test_sin_encuesta():
    assert estado_usuario(RepositorioFalso()) == "sin_encuesta"


def test_con_encuesta_sin_portafolio():
    repo = RepositorioFalso(encuesta={"puntaje": 18})
    assert estado_usuario(repo) == "sin_portafolio"


def test_completo():
    repo = RepositorioFalso(encuesta={"puntaje": 18}, portafolio={"y_star": 0.5})
    assert estado_usuario(repo) == "completo"
