# E13 · Parser del informe diario de TES (PDF → filas validadas)

**Depende de:** E00 · **Rama:** `e13-parser-tes` · **Commit:** `feat(tes): E13 parser del informe diario con validaciones`
**Lee antes:** `docs/taller-2/README.md`, `07-taller2-metodologia.md` §1, `08-pipeline-tes.md` §3.
**Cubre:** T2 (información de irc.gov.co).

## Objetivo
Convertir el PDF del Informe Diario TES en filas tipadas y validadas de la tabla "Tasa Fija en Pesos". Sin red ni base de datos.

## Acción manual previa
Bajar con el navegador el informe del **2-oct-2026** desde `https://www.irc.gov.co/440` y guardarlo como `tests/fixtures/informe_tes_2026-10-02.pdf` (documento público, pocos KB). Copiar `docs/taller-2/anexos/fixtures/*` a `tests/fixtures/`. Si no se consigue el PDF, la prueba 2 queda marcada `skip` con el motivo, pero el resto del entregable sigue.

## Alcance
- `src/roboadvisor/pipeline/tes_parser.py`:
  - `parsear_pdf(ruta | bytes) -> InformeTES`: extrae el texto con `pdfplumber`. Si no hay texto, OCR con `pytesseract` (extra opcional `[ocr]`; si no está instalado, error claro).
  - `parsear_texto(texto: str, via: str) -> InformeTES`: **función pura**, la que se prueba. Toma solo la sección "Tasa Fija en Pesos" (ignora TES UVR y demás tablas).
  - `InformeTES`: `fecha_informe`, `filas: list[FilaTES]`, `total_nominal_mm`, `promedio_var_pb`, `via`.
  - `FilaTES` (dataclass congelada): `vencimiento, nemotecnico, tipo` (prefijo: TCO, TFIT, TFVT…), `valor_nominal_mm: int, cupon, precio_limpio, precio_sucio, duracion, tasa_pub` (decimal, 11,607 → 0.11607), `origen_tasa, tasa_prev, origen_prev, var_pb`.
  - Utilidades puras: `a_numero("5.351.599")`, `a_fecha("20-oct-26")` (meses en español, años de 2 dígitos → 20xx), `fecha_informe("viernes, 2 de octubre de 2026")`.
  - `validar(informe) -> list[Hallazgo]` con V1–V7 de `08` §3. `Hallazgo(codigo, nivel: "error"|"advertencia", fila, mensaje)`.
  - `leer_csv(ruta) -> InformeTES`: lee el formato de `tes_2026-10-02.csv` (`via='csv'`). Sirve para E14 y E16.
  - CLI: `python -m roboadvisor.pipeline.tes_parser ARCHIVO.pdf` imprime tabla y hallazgos; `--csv salida.csv` escribe el formato del fixture.
- `core/tes/` **no** importa nada de este módulo. La TIR que necesita V6 se importa de `core/tes/rendimientos.py` si ya existe (E16). Si no existe, V6 queda pendiente con `TODO(E16)` y se activa en E16.

## Fuera de alcance
Descarga, base de datos, calibración.

## Pruebas (`tests/pipeline/test_tes_parser.py`)
1. Utilidades: `"5.351.599"→5351599`; `"99,430"→99.43`; `"-2,2"→-2.2`; `"12,144"` como tasa → 0.12144; `"20-oct-26"→2026-10-20`; `"9-feb-33"→2033-02-09`; `"ene"`, `"abr"`, `"ago"`, `"dic"`; texto vacío o raro → `ValueError`.
2. PDF del 2-oct → 29 filas **idénticas** a `tes_2026-10-02.csv` (tasas con tolerancia 1e-9), Σ nominal 562.515.499, promedio 9,96, cero errores y una sola advertencia V5 (TFIT 2050).
3. `leer_csv` del fixture = mismo `InformeTES` que la prueba 2.
4. Validaciones negativas, cada una sobre una copia alterada del fixture → error con su código: total que no suma (V1); nemotécnico ≠ vencimiento (V3); vencimiento ≤ fecha (V2); sucio < limpio (V2); TCO con cupón (V2); promedio alterado (V4); fila sin precio → error de parseo con número de fila.
5. Texto con otra tabla (UVR) antes y después de "Tasa Fija en Pesos" → solo se leen las 29 filas correctas.

## Verificación local
```bash
pytest tests/pipeline/test_tes_parser.py -q
python -m roboadvisor.pipeline.tes_parser tests/fixtures/informe_tes_2026-10-02.pdf
```
Anotar en el PR si el PDF trae texto o fue necesario OCR (decide la dependencia de `tesseract` en E14).

## Criterios de aceptación
- [ ] El PDF del 2-oct produce exactamente el CSV del enunciado, o queda documentado que no se consiguió el PDF.
- [ ] Ninguna validación falla en silencio; cada error dice fila y motivo.
- [ ] `pytest`, `ruff` en verde.
