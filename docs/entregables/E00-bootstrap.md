# E00 · Bootstrap del repo, tooling y CI

**Depende de:** nada · **Rama:** `e00-bootstrap` · **Commit:** `chore: E00 bootstrap del proyecto`

## Objetivo
Dejar un repo Python instalable, con lint, pruebas y CI mínimos, listo para recibir el resto.

## Alcance
- `pyproject.toml` con paquete `roboadvisor` (layout `src/`), Python ≥ 3.11 y dependencias:
  - runtime: `numpy`, `pandas`, `scipy`, `scikit-learn`, `plotly`, `streamlit`, `supabase`, `yfinance`, `pydantic-settings`
  - dev (`[project.optional-dependencies].dev`): `pytest`, `pytest-cov`, `ruff`, `pglast` (opcional, para validar SQL)
- Árbol vacío con `__init__.py`: `src/roboadvisor/{core,data,pipeline}/`, `app/` (sin código aún), `tests/{core,data,pipeline}/`.
- `src/roboadvisor/config.py`: `Settings` (pydantic-settings, lee `.env`: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` opcional) y `ParametrosFinancieros` (dataclass congelada) con los valores de `docs/00` §4 y `docs/03`: `ventana_meses=60`, `min_meses=36`, `w_max=0.40`, `n_min_activos=3`, `n_max_activos=11`, `umbral_desvio=0.05`, `min_peso_alerta=0.05`, `tol_vol=0.25`, `dias_stale=5`, `tilt_multiplos=0.025`, `benchmark="ACWI"`.
- `requirements.txt` en la raíz con `-e .` (lo usará Streamlit Cloud).
- `ruff` configurado en `pyproject.toml` (line-length 100, reglas E,F,I,B,UP).
- `.github/workflows/ci.yml`: en push y PR → instalar `.[dev]`, `ruff check .`, `pytest -q`.
- `README.md` con arranque rápido (ya existe un borrador: ajustarlo a lo real).
- Un test de humo `tests/test_config.py` (parámetros por defecto y que `Settings` falle con mensaje claro si falta `SUPABASE_URL` cuando se pide).

## Fuera de alcance
Cualquier lógica financiera, acceso a Supabase, páginas de Streamlit.

## Pruebas
`pytest -q` pasa (≥ 2 tests). `ruff check .` limpio.

## Verificación local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check . && python -c "import roboadvisor; print('ok')"
```

## Criterios de aceptación
- [x] `pip install -e ".[dev]"` funciona en limpio.
- [x] `pytest` y `ruff` verdes localmente.
- [x] El workflow de CI existe y su YAML es válido.
- [x] `config.py` contiene todos los parámetros listados, sin duplicarlos en otros archivos.
- [x] `.env` no está versionado.
