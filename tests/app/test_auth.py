from ui.auth import MIN_LARGO_CONTRASENA, validar_registro


def test_registro_valido_sin_errores():
    errores = validar_registro("a@b.com", "x" * MIN_LARGO_CONTRASENA, "Pepe", "25-34", True)
    assert errores == []


def test_correo_invalido():
    errores = validar_registro("no-es-correo", "x" * MIN_LARGO_CONTRASENA, "Pepe", "25-34", True)
    assert any("Correo" in e for e in errores)


def test_contrasena_corta():
    errores = validar_registro("a@b.com", "corta", "Pepe", "25-34", True)
    assert any("contraseña" in e for e in errores)


def test_alias_vacio():
    errores = validar_registro("a@b.com", "x" * MIN_LARGO_CONTRASENA, "   ", "25-34", True)
    assert any("alias" in e for e in errores)


def test_rango_edad_invalido():
    errores = validar_registro("a@b.com", "x" * MIN_LARGO_CONTRASENA, "Pepe", "10-20", True)
    assert any("edad" in e for e in errores)


def test_sin_consentimiento():
    errores = validar_registro("a@b.com", "x" * MIN_LARGO_CONTRASENA, "Pepe", "25-34", False)
    assert any("consentimiento" in e for e in errores)
