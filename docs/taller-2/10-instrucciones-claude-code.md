# Taller 2 · Instrucciones para Claude Code (validación con datos reales de IRC)

Contexto: repo `robo-advisor`, rama `taller2`, cambios sin commit. El código del Taller 2 ya está
implementado y probado con la tabla del enunciado (2-oct-2026). Falta correrlo con los informes
reales de www.irc.gov.co, cargar Supabase y verificar la app. Lee primero `CLAUDE.md`,
`docs/taller-2/README.md` y `docs/taller-2/09-validacion.md`.

**Reglas:** no hagas commit ni push sin mi confirmación. No modifiques `docs/taller-2/referencias/`.
No toques tablas del Taller 1. Si algo falla, detente y repórtame el error exacto antes de cambiar código.

## Paso 0 · Preparar
```bash
git branch --show-current            # debe decir taller2
source .venv/bin/activate
pip install -e ".[dev]"              # dependencias nuevas: pdfplumber, openpyxl, httpx
pytest -q -m "not integration"       # esperado: 158 passed
ruff check .
```

## Paso 1 · Fase 1 (hasta el 2-oct), sin tocar Supabase
```bash
python -m roboadvisor.taller2.pipeline.validacion fase1
```
- Descarga a `data_local/tes/` los informes del 21-sep al 2-oct y escribe
  `exports/taller2/validacion/fase1.html` y `fase1.md`.
- **Esperado:** C1, C2, C3a, C3b, C4a, C5 en **PASA**; C3c en **AVISO** (error conocido del Excel del
  grupo: la columna L compara contra `$O$3`); C4b PASA o AVISO (el lector del `.py` del grupo
  puede perder papeles); C6 PASA o AVISO.
- Si **C2 falla** (la tabla del PDF no coincide con el enunciado) o el lector no encuentra filas:
  ```bash
  python -m roboadvisor.taller2.datos.informe data_local/tes/informe_2026-10-02.pdf
  ```
  Revisa el texto guardado en `exports/taller2/diagnostico/` y ajusta `PATRON_FILA`, `PATRON_TOTAL`
  o `PATRON_FECHA` en `src/roboadvisor/taller2/datos/informe.py` al formato real. Agrega a
  `tests/taller2/test_datos.py` una prueba con un fragmento de ese texto real. Repite hasta que C2 PASE.
- Si IRC responde **403/429** (bloqueo): avísame. Bajaré los PDF a mano a `data_local/tes/` y
  correremos con `--sin-descarga`.
- Si la URL directa no sirve, el código busca en el listado `https://www.irc.gov.co/440`. Si tampoco
  encuentra un informe, revisa el HTML del listado y ajusta `informes_en_listado` /
  `pagina_siguiente` en `src/roboadvisor/taller2/datos/irc.py`.

Muéstrame la tabla de chequeos de `fase1.md` antes de seguir.

## Paso 2 · Supabase: migración del Taller 2
Hay que ejecutar una sola vez `supabase/migrations/0003_taller2_tes.sql` (crea `t2_informes`,
`t2_cotizaciones`, `t2_curvas`, `t2_resultados` y `t2_corridas` con lectura pública).
- Si `.env` tiene `SUPABASE_DB_URL`: `psql "$SUPABASE_DB_URL" -f supabase/migrations/0003_taller2_tes.sql`.
- Si no, dime y la pego yo en el SQL Editor de Supabase. Espera mi confirmación.

## Paso 3 · Cargar la fase 1 y correr la fase 2
```bash
python -m roboadvisor.taller2.pipeline.validacion fase1 --cargar
python -m roboadvisor.taller2.pipeline.validacion fase2 --cargar     # 5-oct → hoy
```
- La fase 2 encadena con los betas del 2-oct y genera `exports/taller2/validacion/fase2.html`
  (betas en el tiempo, tasas a 1/5/10 años, curvas superpuestas, mapa de decisiones).
- Al final debe imprimir `Supabase (anon): N/N días visibles`.
- IRC publica con ~1 semana de retraso: es normal que los últimos días salgan "no publicado".
- Revisa los AVISO de C6 (saltos > 50 pb o RMSE > 1,5) y dime en qué fechas aparecen.

## Paso 4 · Verificar la app
```bash
streamlit run app/Inicio.py
```
- Abre "T2 Curva TES" **sin iniciar sesión**. Debe listar todas las fechas cargadas; el 2-oct debe
  mostrar β0 13,54 %, β1 −1,20 %, β2 0,78 %, umbral ±23,5 pb y 0 Comprar / 6 Vender / 23 Mantener.
- La pestaña "Historia" debe coincidir con las gráficas de `fase2.html`.
- Confirma que las páginas T1 siguen pidiendo login.
- `pytest -m integration -q` (pruebas contra Supabase real del Taller 1) debe seguir pasando.

## Paso 5 · Excel del 2-oct para el reporte
```bash
python - <<'PY'
from roboadvisor.taller2.datos.informe import leer_csv
from roboadvisor.taller2.core.analisis import analizar, sensibilidad
from roboadvisor.taller2.reportes.excel import generar_excel
inf = leer_csv("tests/taller2/fixtures/tes_2026-10-02.csv")
r = analizar(inf.papeles(), inf.fecha)
print(generar_excel(r, "exports/taller2/Taller2_2026-10-02.xlsx", sensibilidad(inf.papeles(), inf.fecha)))
PY
```
Ábrelo y confirma que las fórmulas calculan (XIRR, decisión, DV01) y que la celda SSE (Parametros!B9) vale ≈ 6,8271.

## Paso 6 · Proponer commits (no ejecutar sin mi OK)
1. `refactor: separar el repo en comun/taller1/taller2 (código, páginas, pruebas, docs)`
2. `feat(taller2): curva Nelson-Siegel de TES, pipeline IRC, validación en dos fases y página pública`
3. (si hubo) `fix(taller2): ajustar lector al formato real del PDF de IRC`

Después del push: en GitHub Actions correr una vez a mano `pipeline-taller2.yml` (workflow_dispatch)
para ver si los runners de GitHub pueden descargar de IRC, y en Streamlit Cloud hacer
**Manage app → Reboot app** (cambiaron rutas de módulos).

## Reporte final que necesito
- Tabla de chequeos de la fase 1 y de la fase 2.
- Fechas cargadas (primera y última) y días sin informe.
- Cualquier cambio que hayas hecho al código y por qué.
