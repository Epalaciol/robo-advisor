# E14 · Pipeline de TES: migración, descarga de IRC, carga y curvas diarias

**Depende de:** E01 (Supabase real), E13, E16 · **Rama:** `e14-pipeline-tes` · **Commit:** `feat(tes): E14 migración, scraper IRC, carga y workflow`
**Lee antes:** `docs/taller-2/08-pipeline-tes.md`.
**Cubre:** T2 automatizado (el enunciado pide que el código se base en irc.gov.co). Si el sitio bloquea, queda la carga manual de PDF o CSV.

## Objetivo
Cada día hábil, bajar los informes que falten, validarlos, guardarlos y calcular su curva y sus señales. Mismo flujo para una fecha puntual (`--fecha`).

## Acciones manuales
1. **Migración:** copiar `docs/taller-2/anexos/0002_tes.sql` a `supabase/migrations/` con el **siguiente número libre** (si ya hay un `0002_*`, usar `0003_tes.sql`). Aplicarla en Supabase (SQL Editor o `psql "$SUPABASE_DB_URL" -f …`). Copiar `anexos/0002_tes_rls.sql` a `supabase/tests/`.
2. **Prueba de acceso** (antes de escribir el scraper): `python scripts/probar_irc.py` en local y en un workflow manual de GitHub. Anotar en `08-pipeline-tes.md` §1 qué pasó:
   - Ambos OK → cron automático.
   - Solo local → el cron solo hace `--solo-curvas`; los PDF se cargan a mano con `--pdf`.
   - Ninguno → carga manual con `--pdf` o `--csv`.

## Alcance
- `scripts/probar_irc.py`: GET del listado del año y de un PDF; imprime código HTTP, `content-type`, tamaño y si el PDF trae texto. No guarda nada.
- `src/roboadvisor/pipeline/tes_scraper.py`:
  - `listar_informes(anio) -> list[(date, url)]`: parsea los títulos "Informe Diario TES DD de Mes de AAAA", con meses en español.
  - `descargar(url) -> bytes`: timeout 30 s, 3 reintentos con espera; ante 403/429 se detiene sin insistir.
  - Pruebas con HTML y PDF guardados (`responses` o `respx`), sin red.
- `src/roboadvisor/data/repositorio_tes.py` (cliente `service_role`): `fechas_cargadas()`, `guardar_informe(informe, sha256, url, via, fuente)` (upsert de las tres tablas en una transacción vía RPC, o borrar y reinsertar la fecha), `cotizaciones(fecha)`, `fechas_sin_curva()`, `betas_previos(fecha)`, `guardar_resultado(fecha, ResultadoTES)` (`curvas_ns` + `tes_senales`).
- `src/roboadvisor/pipeline/update_tes.py` (CLI):
  - `--fecha AAAA-MM-DD`: una fecha (la busca en el listado de su año).
  - `--desde AAAA-MM-DD`: todas las faltantes desde esa fecha.
  - `--pdf RUTA` / `--csv RUTA [--fecha]`: carga manual (`via='texto'|'ocr'|'csv'`).
  - `--solo-curvas`: recalcula las fechas sin curva usando `core/tes/analisis.analizar` (E16).
  - `--dry-run`: valida y muestra sin escribir.
  - Registra en `pipeline_runs` con `tipo='tes'`. Código ≠ 0 si hay errores de validación, si la curva no converge o si hay ≥ 5 días hábiles sin cargar.
- `.github/workflows/pipeline-tes.yml`: cron `17 13 * * 1-5` y `41 23 * * 1-5` (nunca minuto 0) + `workflow_dispatch` con entrada `fecha`; secretos `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; instala `tesseract-ocr` solo si E13 concluyó que hace falta.
- `cliente_mock`: agregar las tablas `tes_*` y `curvas_ns`, precargadas con el 2-oct calculado desde el fixture (para `MOCK_DATA=true`).

## Fuera de alcance
UI (E17), Excel y PDF (E18).

## Pruebas
- Unitarias (sin red ni DB): parseo del listado con 3 títulos de ejemplo; cálculo de fechas faltantes con feriados (lista simple de festivos de Colombia 2026 en config); `update_tes --dry-run --csv` sobre el fixture.
- Integración (`@pytest.mark.integration`, Supabase de pruebas):
  1. Cargar el 2-oct dos veces → 29 cotizaciones, 1 curva, 29 señales (idempotente).
  2. Un informe que falla V1 no escribe nada.
  3. La RLS de `0002_tes_rls.sql` se cumple en Supabase real: anon lee `tes_*` y `curvas_ns`; no lee `perfiles`, `encuestas`, `portafolios`, `precios`, `activos`; ni anon ni authenticated pueden escribir `tes_*`.

## Verificación local
```bash
python scripts/probar_irc.py
python -m roboadvisor.pipeline.update_tes --csv tests/fixtures/tes_2026-10-02.csv --fecha 2026-10-02 --dry-run
python -m roboadvisor.pipeline.update_tes --csv tests/fixtures/tes_2026-10-02.csv --fecha 2026-10-02
python -m roboadvisor.pipeline.update_tes --fecha 2026-10-02        # desde IRC, si probar_irc dio OK
python -m roboadvisor.pipeline.update_tes --solo-curvas
```
En Supabase: `select count(*) from tes_cotizaciones where fecha='2026-10-02'` → 29; `curvas_ns` con β iguales a E16.

## Criterios de aceptación
- [ ] Migración aplicada y RLS probada en Supabase real.
- [ ] 2-oct cargado (por IRC o por CSV) e idempotente; resultados iguales a E16.
- [ ] Resultado de `probar_irc.py` documentado y modo de operación elegido.
- [ ] Workflow corrido al menos una vez con `workflow_dispatch`.
- [ ] `service_role` solo en secretos y `.env`.
