import pytest

from roboadvisor.core.utilidad import utilidad


def test_utilidad_valor_de_referencia():
    assert utilidad(0.10, 0.20, 4) == pytest.approx(0.02)


def test_utilidad_decrece_con_a_creciente():
    u_bajo = utilidad(0.10, 0.20, 1)
    u_alto = utilidad(0.10, 0.20, 8)
    assert u_alto < u_bajo


def test_utilidad_error_si_sigma_negativo():
    with pytest.raises(ValueError):
        utilidad(0.10, -0.01, 4)


def test_utilidad_error_si_a_no_positivo():
    with pytest.raises(ValueError):
        utilidad(0.10, 0.20, 0)
