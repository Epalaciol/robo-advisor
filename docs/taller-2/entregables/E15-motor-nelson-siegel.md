# E15 · Motor Nelson-Siegel: flujos, precio, calibración y curva

**Depende de:** E00 · **Rama:** `e15-nelson-siegel` · **Commit:** `feat(core): E15 motor Nelson-Siegel con prueba dorada del Excel`
**Lee antes:** `docs/taller-2/07-taller2-metodologia.md` §1–§3.
**Cubre:** T1 (betas de un día), T3 (curva cero cupón), T6 (fiel al Excel).

## Objetivo
Núcleo puro que reproduce el modelo del profesor y lo calibra.

## Alcance — `src/roboadvisor/core/tes/`
- `modelos.py`: `Papel(nemotecnico, vencimiento, cupon, precio_sucio, origen_tasa, …)`, `Betas(b0, b1, b2)`, `Calibracion(betas, tau, sse, rmse, n, convergio, iteraciones, arranque_usado)`.
- `flujos.py`: `flujos(vencimiento, cupon, fecha) -> tuple[np.ndarray t, np.ndarray monto]`.
  - Aniversarios hacia atrás desde el vencimiento (equivalente a `EDATE`; 29-feb → 28-feb), **solo fechas > fecha**; `t = días/365`.
  - TCO (cupón 0): un flujo de 100.
- `nelson_siegel.py`:
  - `spot(t, betas, tau)`: vectorizado. Para `t < 1e-8` usa el límite `β0 + β1`, sin división por cero.
  - `descuento(t, betas, tau) = (1 + spot)^(−t)`.
  - `precio(papel | (t, monto), betas, tau)`.
  - `curva(betas, tau, dias=np.arange(1, 10951)) -> DataFrame[dias, t, spot, descuento]`.
- `calibracion.py`: `calibrar(papeles, fecha, tau=3.7, arranques=None, ponderacion="ninguna"|"duracion", usar_origen="todos"|"SEN") -> Calibracion`.
  - `scipy.optimize.least_squares` sobre los residuos `P_sucio − P_est` (con `"duracion"`: residuo / (P·D*), que aproxima el error en tasa). Betas sin cotas.
  - **Varios arranques:** β del día anterior (si se pasan), β del Excel `(0.12790, −0.03133, 0.04366)` y `(0.13, −0.02, 0.0)`. Se queda con el menor SSE y registra cuál fue.
  - `convergio = False` si ningún arranque converge o si `S(t) ≤ −0.99` en algún plazo de 0 a 30 años (curva absurda).
- Parámetros (`tau`, `arranques`, `ponderacion`, `usar_origen`) en `config.py` → `ParametrosTES`, junto a `umbral_pb` y `nominal_dv01`, que usa E16.

## Fuera de alcance
TIR, duración, DV01, señales (E16). Lectura de CSV o PDF (E13).

## Pruebas (`tests/core/tes/`)
1. **Dorada (Excel):** con β y τ de `modelo_excel_2026-03-17.json`, `precio` reproduce `precio_estimado_excel` en los 24 papeles sanos (tol 1e-8) y `precio_estimado_correcto` en los 2 con `excel_roto` (tol 1e-8).
2. **Flujos:** bono que vence el 3-nov-2027 con cupón 5,75 al 2-oct-2026 → 2 flujos (3-nov-26: 5,75; 3-nov-27: 105,75), t = 32/365 y 397/365. Aniversario igual a la fecha → excluido. Vencimiento el 29-feb → aniversarios el 28-feb. TCO → 1 flujo.
3. **Spot:** `spot(1e-12) == β0+β1`; `spot(1e6) ≈ β0` (tol 1e-6); vectorizado = escalar; sin `RuntimeWarning`.
4. **Recuperación sintética:** precios generados con β conocidos sobre los 29 vencimientos del 2-oct → `calibrar` desde cada arranque recupera β (tol 1e-7).
5. **2-oct (regresión):** con el CSV, `convergio`, β dentro de ±5e-4 de (0,13544; −0,01199; 0,00780) y RMSE 0,49 ± 0,02. **Si no coincide, investigar antes de tocar la prueba.**
6. El SSE final es ≤ el SSE de cada arranque. `usar_origen="SEN"` usa 18 papeles.
7. `curva` tiene 10.950 filas, `descuento` decreciente y en (0, 1].

## Verificación local
```bash
pytest tests/core/tes -q
python - <<'PY'
from roboadvisor.pipeline.tes_parser import leer_csv          # si E13 aún no está: leer el CSV con pandas
from roboadvisor.core.tes.calibracion import calibrar
inf = leer_csv("tests/fixtures/tes_2026-10-02.csv")
print(calibrar(inf.papeles(), inf.fecha_informe))
PY
```

## Criterios de aceptación
- [ ] Prueba dorada del Excel y regresión del 2-oct en verde.
- [ ] `core/tes` no importa `data`, `pipeline` ni `app`.
- [ ] Sin constantes sueltas: τ, arranques y ponderación salen de `ParametrosTES`.
