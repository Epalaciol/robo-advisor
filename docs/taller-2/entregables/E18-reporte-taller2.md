# E18 · Excel y reporte del Taller 2 (2-oct-2026)

**Depende de:** E16 (obligatorio); E17 (opcional, para capturas y botón de descarga) · **Rama:** `e18-reporte-taller2` · **Commit:** `feat(reportes): E18 Excel Nelson-Siegel y reporte del Taller 2`
**Entrega:** jueves 19-nov-2026. **Cubre:** T6, T7, T11 y la presentación de T1–T9.

## Objetivo
Entregables formales: Excel con el modelo (siguiendo el del profesor, ya corregido), PDF autoexplicativo y código, todos con las mismas cifras.

## Alcance
1. **`reportes/excel_tes.py`** → `generar_excel(resultado: ResultadoTES, papeles, ruta)`. Un solo generador, que usan el reporte y la app. Hojas:
   - `Instrucciones`: qué es cada hoja, la fuente (tabla del enunciado) y los supuestos (τ = 3,7, precio sucio, días/365, flujos en aniversarios, N = 10⁹).
   - `Datos`: la tabla del 2-oct tal como viene.
   - `CalculoCurva`: con la misma lógica que la hoja del profesor. Celdas de β0, β1, β2 y τ; por papel, sus flujos (fecha, t, monto, spot, DF, VP) **con fórmulas vivas** y el **cupón enlazado a la tabla** (sin los dos bloques rotos del modelo de ejemplo); precio estimado, error² y una celda SSE. Lista para correr **Solver** (minimizar SSE cambiando β0:β2, sin restringir el signo).
   - `DatosCurvaSpot`: días 1…10.950, t, tasa spot y DF, con fórmulas referidas a las celdas de β.
   - `TIR y señales`: TIR observada y TIR teórica con `TIR.NO.PER` (`XIRR`): flujo −precio en la fecha del informe y los flujos del papel. XIRR descuenta con días/365, la misma convención del modelo, así que debe coincidir con Python (tol 1e-6, por la precisión iterativa de XIRR), spread, señal con fórmula `SI` y umbral en una celda.
   - `DV01`: N en una celda (1.000.000.000), DV01 por bump con fórmulas, D*, convexidad y la tabla de aproximación ±50/±100 pb.
   - `Sensibilidad`: tabla de `07` §5 (valores).
   - En la app (si existe E17): botón "Descargar Excel" para la fecha elegida.
2. **`reportes/generar_pdf_taller2.py`** (o notebook/Quarto → PDF). Secciones:
   1. Objetivo y enunciado. 2. Datos: la tabla del 2-oct, su fuente y las validaciones (Σ nominal, nemotécnicos, cupón corrido). 3. Metodología: Nelson-Siegel, flujos, calibración, supuestos y diferencias con el Excel de ejemplo (`07` §3). 4. Betas del 2-oct y calidad del ajuste (residuos por papel). 5. Curva cero cupón (gráfico, tasas a 1, 5, 10 y 30 años). 6. TIR observada vs. teórica y señal por papel (tabla y gráfico de spreads). 7. Sensibilidad: umbral 5/10/20 y calibración Excel/ponderada/SEN, con la conclusión de que la señal depende del método. 8. Casos a comentar: TFIT 3-nov-27 (−103 pb), TCO VAL, TFVT vs. TFIT 2031. 9. Duración, convexidad y DV01 por $1.000 millones (10⁹ COP), con un papel desarrollado paso a paso y la tabla de aproximación. 10. Implementación: pipeline desde irc.gov.co y página pública (capturas). 11. Limitaciones (τ fijo, ajuste en precios, tramo corto, datos de un solo día). 12. Respuestas del profesor a las preguntas de `07` §6 y cómo se aplicaron.
3. **Validación externa (opcional):** comparar la curva con la cero cupón de TES del Banco de la República para la misma fecha y reportar la diferencia.

## Fuera de alcance
Cambios funcionales, salvo correcciones.

## Pruebas
1. El Excel abre con `openpyxl`; `DatosCurvaSpot` tiene 10.950 filas; las fórmulas existen en `CalculoCurva` y `DV01`.
2. **Recalcular con LibreOffice** (si `soffice` está instalado; si no, `skip`): `soffice --headless --convert-to xlsx` y releer con `data_only=True` → precios estimados, SSE y DV01 iguales a Python (tol 1e-6).
3. Prueba manual en Excel: correr Solver desde los β del modelo de ejemplo → llega a los β de E16 (±1e-4). Anotar el resultado en el PR.
4. Cada cifra del PDF sale de `exports/taller2_2026-10-02/` o del Excel (script de verificación que compara los dos).

## Verificación
- [ ] PDF, Excel y código consistentes (mismos β, conteos y DV01).
- [ ] La unidad del DV01 está declarada: por $1.000.000.000 COP.
- [ ] Preguntas al profesor respondidas o con el supuesto declarado.
- [ ] Revisión cruzada por otro integrante del grupo que no escribió el código.

## Criterios de aceptación
- [ ] Entregado antes del jueves 19-nov.
