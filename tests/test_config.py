import pytest
from pydantic import ValidationError

from roboadvisor.config import ParametrosFinancieros, Settings


def test_parametros_financieros_valores_por_defecto():
    p = ParametrosFinancieros()
    assert p.ventana_meses == 60
    assert p.min_meses == 36
    assert p.w_max == 0.40
    assert p.n_min_activos == 3
    assert p.n_max_activos == 11
    assert p.umbral_desvio == 0.05
    assert p.min_peso_alerta == 0.05
    assert p.tol_vol == 0.25
    assert p.dias_stale == 5
    assert p.tilt_multiplos == 0.025
    assert p.benchmark == "ACWI"


def test_settings_falla_con_mensaje_claro_si_falta_supabase_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "SUPABASE_URL" in str(exc_info.value)
