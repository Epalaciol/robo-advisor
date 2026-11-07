# E16 · TIR teórica vs. observada, duración, convexidad, DV01 y señales (2-oct sin base de datos)

**Depende de:** E15 (y `leer_csv` de E13; si no está, leer el CSV con pandas) · **Rama:** `e16-senales-dv01` · **Commit:** `feat(tes): E16 TIR teórica vs observada, DV01 y señales`
**Lee antes:** `docs/taller-2/07-taller2-metodologia.md` §2 y §5.
**Cubre:** T4, T5, T7, T8, T9. Con E15, es el **núcleo calificable** del taller.

## Objetivo
Para una fecha y sus papeles: calibrar, calcular la TIR teórica y observada, la señal, la duración, la convexidad y el DV01 por $1.000 millones. Dejar el resultado del 2-oct listo para el reporte, sin depender de Supabase ni de IRC.

## Alcance
- `core/tes/rendimientos.py`:
  - `tir(t, monto, precio) -> float`: efectiva anual con `brentq` en [−0,5; 2]; error claro si no hay raíz.
  - `duracion_macaulay`, `duracion_modificada`, `convexidad` (fórmulas de `07` §2).
  - `dv01(t, monto, y, nominal) = nominal/100 · [P(y−1pb) − P(y+1pb)]/2` y `dv01_analitico = nominal·(P/100)·D*·1e-4`.
  - `dv01_curva(papel, betas, tau, nominal)`: β0 ± 1 pb.
  - `aproximacion_precio(t, monto, y, dys=(−0.01, −0.005, 0.005, 0.01))` → exacto, solo D*, D* + C.
- `core/tes/senales.py`: `senal(spread_pb, umbral_pb) -> Literal["COMPRAR","VENDER","MANTENER"]` (estricto: |spread| = umbral → MANTENER).
- `core/tes/analisis.py`: `analizar(papeles, fecha, params, betas_previos=None) -> ResultadoTES(calibracion, tabla: DataFrame)`. Columnas de la tabla: `nemotecnico, tipo, vencimiento, cupon, origen_tasa, precio_sucio, precio_estimado, tir_obs, tir_teo, tasa_pub, spread_pb, senal, dur_macaulay, dur_informe, dur_modificada, convexidad, dv01_cop, dv01_curva_cop`.
  `sensibilidad(papeles, fecha, params) -> DataFrame`: β y conteo de señales para {Excel, ponderada, solo SEN} × umbral {5, 10, 20}.
- `config.ParametrosTES`: `nominal_dv01: int = 1_000_000_000  # $1.000 millones = 10**9 COP; NO 10**12`, `umbral_pb = 10`.
- **CLI del taller** (en `pipeline/`, porque lee y escribe archivos) `python -m roboadvisor.pipeline.taller2 --csv tests/fixtures/tes_2026-10-02.csv` (o `--fecha AAAA-MM-DD` contra la base cuando exista E14):
  imprime β, SSE, RMSE y la tabla, y escribe `exports/taller2_AAAA-MM-DD/{resultado.csv, sensibilidad.csv, curva.csv}` (`exports/` está en `.gitignore`). Es la evidencia de T1 ("betas para un día determinado").

## Fuera de alcance
Escritura en Supabase (E14), UI (E17), Excel y PDF (E18).

## Pruebas (`tests/core/tes/`)
1. **TIR:** flujos construidos a mano con t = 1, 2, 3 y cupón c, precio 100 → TIR = c (tol 1e-10); TCO a 365 días con precio 90 → 11,111 %; ida y vuelta `tir(precio(y)) = y`.
2. **Duración y convexidad de un TCO:** D = t; D* = t/(1+y); C = t(t+1)/(1+y)².
3. **DV01:** numérico vs. analítico, diferencia relativa < 1e-3 en los 29 papeles del 2-oct.
4. **Escala, sin topes fijos:** `dv01 / ((P/100)·nominal·1e-4) = D*` (tol 1e-4) en los 29 papeles. Con nominal 10¹² la prueba falla. Referencia del 2-oct: TCO 20-oct-26 ≈ $4.367 y TFIT 2058 ≈ $653.824 (±1 %).
5. **Señal:** ±10 exactos → MANTENER; 10,01 → COMPRAR; −10,01 → VENDER; el umbral sale de la configuración.
6. **Regresión 2-oct** (contra `07` §5): conteos 5/12/12; TFIT 3-nov-27 con spread −102,8 ± 0,5 pb; tabla de sensibilidad con los conteos de `07` §5.
7. **Consistencia:** `dur_macaulay` vs. `dur_informe`: |Δ| ≤ 0,02 en los 29.
8. **Aproximación (TFIT 2058):** con ±100 pb, el error de D* + C es < 0,05 puntos porcentuales y menor que el de D* sola.

## Verificación local
```bash
pytest tests/core/tes -q
python -m roboadvisor.pipeline.taller2 --csv tests/fixtures/tes_2026-10-02.csv
```
Revisar a mano 3 filas (un TCO, un TFIT corto, el TFIT 2058) contra `07` §5.

## Criterios de aceptación
- [ ] Tabla del 2-oct completa (29 filas) y sensibilidad exportadas.
- [ ] Prueba de escala del DV01 en verde.
- [ ] `core/tes` sigue puro; parámetros en `ParametrosTES`.
