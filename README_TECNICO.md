# Guía técnica — MFT Investments (Talleres 1 y 2, Inversiones EAFIT)

> Para la guía de uso orientada al profesor, ver el [README principal](README.md).
> Este documento explica cómo levantar el proyecto, su estructura y las tecnologías.

Proto robo-advisor: registro, cuestionario de aversión al riesgo, portafolio óptimo (Markowitz) con CAL, seguimiento y recomendaciones por reglas fijas.
Datos de Yahoo Finance cargados por un pipeline diario en Supabase; app en Streamlit. **Ejercicio académico; no constituye asesoría de inversión.**

## Tecnologías
| Capa | Herramientas |
|---|---|
| Motor financiero | Python 3.11+, numpy, pandas, scipy (SLSQP), covarianza muestral |
| App | Streamlit (multipágina), plotly |
| Datos | Supabase (Postgres + Auth + RLS), `supabase-py`, `yfinance` |
| Automatización | GitHub Actions (cron 22:23 UTC ≈ 5:23 pm Bogotá, con respaldo) |
| Calidad | pytest, ruff, CI en GitHub Actions |

## Quickstart (jugar con la app en 5 minutos, sin Supabase)

Requiere Python ≥ 3.11.

```bash
git clone <url-del-repo>
cd robo-advisor
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

MOCK_DATA=true streamlit run app/Inicio.py
```

Abre `http://localhost:8501`. Inicia sesión con el usuario ya creado por el modo mock:
**correo `prueba@local.test`, clave `Prueba1234!`**. Todo corre en memoria (nada de Supabase,
nada de claves) — ver [Modo mock](#modo-mock-correr-la-app-sin-supabase) más abajo.

## Estado del proyecto
Motor financiero y app completos, con Supabase real conectado, datos de Yahoo cargados y el
pipeline diario activo en GitHub Actions. Pendiente: verificación de tickers con el profesor,
pruebas finales en producción y reporte.

## Qué hay en este paquete
| Ruta | Contenido |
|---|---|
| `docs/taller-1/00…06` | Taller 1: requisitos, arquitectura, datos, motor, pipeline, plan, despliegue |
| `docs/taller-2/` | Taller 2: metodología Nelson-Siegel, pipeline TES, validación, referencias del grupo |
| `src/roboadvisor/comun/` | Común: credenciales (`config.py`), clientes de Supabase, cliente mock, paginación |
| `src/roboadvisor/taller1/core/` | T1 · motor puro (cuestionario, Markowitz, riesgo, recomendaciones) |
| `src/roboadvisor/taller1/data/`, `taller1/pipeline/` | T1 · Supabase, Yahoo Finance; carga diaria de precios/fundamentales |
| `src/roboadvisor/taller2/core/` | T2 · motor puro (flujos, Nelson-Siegel, calibración, TIR, duración, DV01, decisión) |
| `src/roboadvisor/taller2/datos/` | T2 · lector del informe (PDF/Excel/CSV), descarga de IRC, repositorio `t2_*` |
| `src/roboadvisor/taller2/pipeline/` | T2 · `update_tes` (diario / un día / un archivo) y `validacion` (fase 1 y 2) |
| `src/roboadvisor/taller2/reportes/` | T2 · gráficas (Plotly), Excel con fórmulas (listo para Solver) e informe PDF |
| `src/roboadvisor/taller1/reportes/` | T1 · caso de referencia, Excel e informe PDF |
| `entregas/` | Lo que se entrega: PDF, Excel y README de cada taller (se regeneran con `python -m roboadvisor.taller1.reportes` y `python -m roboadvisor.taller2.reportes`; requieren `pip install -e ".[reportes]"` y `pandoc` + `xelatex`) |
| `app/` | App Streamlit: `Inicio.py`, `pages/` (`T1_*` con login, `4_T2_Curva_TES.py` pública), `ui/{comun,taller1,taller2}` |
| `.streamlit/config.toml` | Tema de la app (colores de la marca) |
| `tests/{taller1,taller2,comun}/` | `pytest -q` (unitarias) y `pytest -m integration -q` (requieren Supabase real) |
| `supabase/migrations/` | T1: `0001_init.sql`, `0002_*`; T2: `0003_taller2_tes.sql` (tablas `t2_*`). Ver `supabase/README.md` |
| `supabase/seed/activos.csv` | Catálogo inicial (23 filas, sin GXG; los tickers los valida el profesor) |
| `.env.example`, `.gitignore` | Variables y exclusiones (nunca se commitea `.env`) |

## Correr las pruebas
```bash
pytest -q && ruff check .
```
100+ pruebas unitarias, sin red ni Supabase. Las de integración (`-m integration`, RLS real)
se saltan automáticamente si no hay `.env`.

## Modo mock (correr la app sin Supabase)
Para desarrollo/demo sin un proyecto Supabase real:
```bash
MOCK_DATA=true streamlit run app/Inicio.py
```
Usa un cliente Supabase falso en memoria (`roboadvisor/comun/cliente_mock.py`): se siembra con
el catálogo (`supabase/seed/activos.csv`) y, si existen, los precios reales de `data_local/`
(la instantánea versionada en `data_local/taller1/`, que se actualiza con
`python scripts/taller1/exportar_instantanea.py`). Entra con `prueba@local.test` / `Prueba1234!`, o con `a3@local.test` / `Prueba1234!` (encuesta ya hecha, A = 3, sin portafolio: listo para armarlo).

Los datos viven solo en la memoria del proceso del servidor y **se pierden al reiniciarlo**;
`data_local/taller1/` se versiona (instantánea de precios para el mock y los informes); `data_local/tes/` no. Los scripts sueltos
(`cargar_catalogo.py`) no ven los datos del mock porque corren en
otro proceso — son para el flujo con Supabase real. **El modo mock no reemplaza** las pruebas
de RLS de `tests/taller1/db/test_rls.py`, que siguen corriendo solo contra un Supabase real.

## Conectar un Supabase real (para el entregable final)
1. Crear el proyecto Supabase gratuito (acción humana).
2. Copiar `.env.example` a `.env` y completar `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY` (nunca se commitea).
3. En el SQL Editor del proyecto, ejecutar en orden `supabase/migrations/0001_init.sql` y `0002_rangos_edad.sql` (una sola vez cada una).
4. Cargar el catálogo: `python scripts/taller1/cargar_catalogo.py` (idempotente, usa `service_role`).
5. Verificar la seguridad: `pytest -m integration -q` (crea y borra usuarios de prueba).

7. Cargar precios reales: `python -m roboadvisor.taller1.pipeline.update_prices` (ver `docs/taller-1/04-pipeline-datos.md`).

## Desplegar en Streamlit Community Cloud
1. share.streamlit.io → New app → repo, rama `master`, archivo `app/Inicio.py`.
2. Secrets (Settings → Secrets), solo la clave pública:
   ```toml
   SUPABASE_URL = "https://<proyecto>.supabase.co"
   SUPABASE_ANON_KEY = "sb_publishable_..."
   ```
   Para una demo sin base de datos usar solo `MOCK_DATA = "true"`. **Nunca** poner la clave `service_role`.
3. Tras cambios en módulos de `app/ui/` o `src/`, usar **Manage app → Reboot app** (Streamlit conserva módulos viejos en memoria).
4. Pipeline: en GitHub → Settings → Secrets → Actions crear `SUPABASE_URL`, `SUPABASE_ANON_KEY` y `SUPABASE_SERVICE_ROLE_KEY`; el workflow `pipeline.yml` corre de lunes a viernes.

## Taller 2 · comandos
```bash
# Un día determinado (requisito del enunciado): betas, curva, TIR, decisión y DV01
python -m roboadvisor.taller2.pipeline.update_tes --fecha 2026-10-02 --sin-supabase
python -m roboadvisor.taller2.pipeline.update_tes --archivo tests/taller2/fixtures/tes_2026-10-02.csv --sin-supabase
# Validación (ver docs/taller-2/09-validacion.md)
python -m roboadvisor.taller2.pipeline.validacion fase1 [--cargar]
python -m roboadvisor.taller2.pipeline.validacion fase2 [--cargar]
```
Opciones del modelo: `--umbral sigma|sigma_robusta|<pb>`, `--solo-sen`, `--ponderar-duracion`, `--tau`.
Supabase: ejecutar una vez `supabase/migrations/0003_taller2_tes.sql`. En modo mock la página del
Taller 2 muestra solo el 2-oct de la tabla del enunciado.

## Fechas
Taller 1: **19-nov-2026** · Taller 2: **26-nov-2026**.
