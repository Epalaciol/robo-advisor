# Taller 2 · Pipeline de TES (informe diario → base de datos → curva)

Complementa `docs/04-pipeline-datos.md` (precios de Yahoo). Objetivo: tener en Supabase la tabla "Tasa Fija en Pesos" de cada día hábil, más su curva y sus señales, para que la página pública (E17) solo lea.

## 1. Lo verificado y lo que no
- IRC publica **un PDF por día**, en una carpeta por año: 2026 en `https://www.irc.gov.co/440`; años anteriores en `https://www.irc.gov.co/deuda-publica/deuda-interna-gnc/informe-diario-tes/<AÑO>`. Cada enlace se titula **"Informe Diario TES DD de Mes de AAAA"**; el ID del archivo no sigue la fecha.
- Sin API ni descarga masiva documentada (IRC, datos.gov.co, SUAMECA). minhacienda.gov.co responde con verificación anti-bots (Radware).
- El PDF del 30-oct tenía fecha de creación del 6-nov: **la publicación puede atrasarse días**. El pipeline busca todo lo que falte, no "el de ayer".
- **Sin verificar:** si un script (local o GitHub Actions) puede bajar el listado y el PDF, y si el PDF tiene texto o es imagen. Se resuelve con `scripts/probar_irc.py` al inicio de E14.

## 2. Flujo
```
cron (GitHub Actions): 17 13 * * 1-5  y  41 23 * * 1-5   (8:17 am y 6:41 pm Bogotá; nunca minuto 0)
 1. Listar la carpeta del año (y la del año anterior en enero) → [(fecha, url)]
 2. Fechas del listado que no están en tes_informes (o --fecha AAAA-MM-DD) → descargar el PDF
 3. Extraer la tabla "Tasa Fija en Pesos": pdfplumber; sin texto → OCR (tesseract), via='ocr'
 4. Validar (§3). Errores → no se carga esa fecha y el job termina en error
 5. Upsert en tes_emisiones, tes_informes (sha256, url, via), tes_cotizaciones
 6. Para cada fecha sin curva: calibrar (E15) y calcular métricas y señales (E16) → curvas_ns, tes_senales
 7. pipeline_runs con tipo='tes'
```
Pasos 1–5: dependen del sitio. Paso 6: solo de la base (`--solo-curvas`). Ambos son idempotentes.

## 3. Validaciones (`pipeline/tes_parser.py`)
| # | Regla | Si falla |
|---|---|---|
| V1 | Σ valor nominal = fila "Total Tasa Fija en Pesos" | error |
| V2 | 20–40 filas; vencimiento > fecha; cupón ≥ 0; sucio ≥ limpio > 0; TCO ⇒ cupón 0 y limpio = sucio | error |
| V3 | El nemotécnico termina en `ddmmyy` = vencimiento | error |
| V4 | Promedio de `var_pb` = "Promedio" de la tabla (±0,05) | error |
| V5 | Cupón corrido: `sucio − limpio` vs. `cupón·días/365` desde el último aniversario | advertencia si > 0,01 (el 2-oct: TFIT 2050, 0,02) |
| V6 | Filas SEN: \|TIR(precio sucio) − tasa publicada\| ≤ 3 pb | advertencia (VAL: solo se registra) |
| V7 | `via = ocr` ⇒ `validado = true` solo si pasan V1–V4 | — |

## 4. Entradas alternativas (respaldo si IRC bloquea)
- `update_tes --pdf ruta.pdf`: PDF bajado a mano con el navegador.
- `update_tes --csv anexos/fixtures/tes_2026-10-02.csv --fecha 2026-10-02`: carga la tabla del enunciado (`via='csv'`, `fuente='Enunciado Taller 2'`). Es la forma de tener el 2-oct en la base sin depender de IRC.

## 5. Operación
- **Datos viejos:** si el listado tiene ≥ 5 días hábiles sin cargar, el job falla (llega el correo de GitHub).
- **Cortesía con el sitio:** máximo ~10 peticiones por corrida, sin paralelismo, User-Agent genérico del proyecto, respetar 403/429 sin reintentos agresivos.
- **Modo mock (`MOCK_DATA=true`):** `cliente_mock` sirve las tablas `tes_*` con el 2-oct precalculado desde el fixture, así la página pública funciona en el despliegue actual sin Supabase.
- **Almacenamiento:** no se guardan los 10.950 puntos de la curva (≈ 140 MB/año, demasiado para el plan gratuito de 500 MB). La curva queda determinada por β0, β1, β2 y τ, y se calcula al vuelo con `core/tes`. Por día: ~29 cotizaciones + 29 señales + 1 curva ≈ 15 KB.
