# E02 · Pipeline de datos

**Depende de:** E01 · **Rama:** `e02-pipeline` · **Commit:** `feat(pipeline): E02 carga diaria de precios, rf y fundamentales`

## Objetivo
Cargar y mantener `precios`, `tasa_libre_riesgo` y `fundamentales` desde Yahoo, con validaciones, idempotencia y workflow programado. Ver `docs/04-pipeline-datos.md`.

## Alcance
1. **`data/yahoo.py`**
   - `descargar_precios(tickers, desde) -> DataFrame` columnas `ticker, fecha, close, adj_close, volumen` (usar `yfinance.download(..., auto_adjust=False)` para tener ambos; manejar el formato multi-índice).
   - `descargar_rf(desde) -> DataFrame fecha, tasa_anual` desde `^IRX` (`close/100`).
   - `descargar_fundamentales(ticker) -> dict | None` con `pe, pb, ev_ebitda, div_yield` (None si falta).
   - Reintentos con espera creciente (3 intentos) y errores claros; sin imprimir claves.
2. **`pipeline/validators.py`**: funciones puras (`validar_precios(df, ...) -> ReporteValidacion`) para las reglas de `docs/04`. Con pruebas.
3. **`data/repositorio.py`**: `listar_activos(activos_only=True)`, `ultima_fecha_por_ticker()`, `upsert_precios(df)` (lotes de 500), `upsert_rf(df)`, `upsert_fundamentales(rows)`, `registrar_corrida(...)`.
4. **`pipeline/update_prices.py`** (CLI `python -m roboadvisor.pipeline.update_prices [--dry-run] [--desde] [--tickers]`) siguiendo el algoritmo de `docs/04`. `--dry-run` descarga y valida pero no escribe.
5. **`pipeline/update_fundamentals.py`** análogo.
6. **`pipeline/verificar_catalogo.py`**: descarga ~1 mes por ticker activo y reporta: sin datos, historia < 60 meses, última fecha vieja. Con `--aplicar` marca `activo=false` los fallidos (con confirmación interactiva).
7. **Workflows** `.github/workflows/pipeline.yml` (cron `0 22 * * 1-5` + `workflow_dispatch`) y `pipeline-fundamentales.yml` (`30 22 * * 5`). Usan `secrets.SUPABASE_URL` y `secrets.SUPABASE_SERVICE_ROLE_KEY`; `pip install -e .`; falla el job si estado `error`.

## Fuera de alcance
Conversión de monedas, TES, tiempo real, UI.

## Pruebas (`tests/pipeline/`, sin red)
- Validadores: precio ≤ 0, nulo, fecha futura, duplicada, salto extremo, dato viejo.
- `update_prices` con un cliente Yahoo **falso** (inyección de dependencias) y repositorio en memoria: idempotencia (2 corridas = mismas filas), solapamiento de 5 días, ticker fallido → estado `parcial` sin romper los demás.
- Parseo del formato multi-índice de yfinance con un DataFrame fabricado.

## Verificación local (con red y `.env`)
```bash
python -m roboadvisor.pipeline.verificar_catalogo        # revisar y decidir qué se desactiva
python -m roboadvisor.pipeline.update_prices --dry-run
python -m roboadvisor.pipeline.update_prices             # primera carga histórica (~6 años)
python -m roboadvisor.pipeline.update_prices             # segunda corrida: ~0 filas nuevas
python -m roboadvisor.pipeline.update_fundamentals
```
En Supabase: `select ticker, count(*), min(fecha), max(fecha) from precios group by 1 order by 1;` y una fila reciente en `pipeline_runs`.

## Criterios de aceptación
- [ ] Todos los tickers `activo=true` tienen ≥ 60 meses de historia o fueron desactivados con motivo en `notas`.
- [ ] Segunda corrida no duplica filas.
- [ ] `tasa_libre_riesgo` tiene la última fecha hábil.
- [ ] Workflow ejecutado con éxito al menos una vez con `workflow_dispatch` en GitHub y **activado el cron** (esto inicia el conteo de 3 días para E11).
- [ ] Documentar en `docs/04` los tickers desactivados o cambiados.
