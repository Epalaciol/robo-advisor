# Taller 2 · Metodología (según "Modelo Nelson Siegel.xlsx" del profesor)

Fuente de verdad: el enunciado y el Excel del profesor (hojas `Instrucciones`, `CalculoCurva`, `DatosCurvaSpot`). Entrega: **19-nov-2026**. Prueba obligatoria: tabla del **2-oct-2026** que trae el enunciado.
Etiquetas: **[Enunciado]** lo pide el taller · **[Excel]** sale del modelo del profesor · **[Datos]** verificado con la tabla del 2-oct · **[Supuesto]** decisión nuestra, a confirmar con el profesor (§6).

## 1. Pasos del modelo

1. **Entrada [Enunciado][Excel].** Tabla "Tasa Fija en Pesos" del *Informe diario de deuda pública* (irc.gov.co → Deuda Pública → Deuda Interna GNC → Mercado Secundario → Informe diario TES). Columnas: fecha de vencimiento, nemotécnico, valor nominal*, cupón, precio limpio, precio sucio, duración, tasa del día con origen (VAL/SEN), tasa del día anterior con origen, variación en pb. Fila final: "Total Tasa Fija en Pesos" (Σ nominal) y "Promedio" (de la variación). Fecha de cálculo = fecha del informe. Solo esta tabla; los TES UVR quedan fuera.
2. **Observado = precio sucio [Excel]**, por cada $100 de facial. En los TCO (cero cupón) limpio = sucio.
3. **Flujos [Excel][Datos].** Fechas = aniversarios anuales del vencimiento **estrictamente posteriores** a la fecha de cálculo (`EDATE(venc, −12·k)`; un 29-feb pasa a 28-feb). Monto = cupón en cada fecha y `100 + cupón` al vencimiento; TCO: solo `100`.
   *Verificación con los datos:* sucio − limpio = cupón × (días desde el último aniversario)/365 en 16 de 17 bonos del 2-oct (error ≤ 0,004). El TFIT 2050 difiere en 0,02 (≈ 1 día de cupón). Liquidación: misma fecha del informe.
4. **Tiempo [Excel]:** `t = días(fecha_flujo − fecha_cálculo) / 365`.
5. **Tasa spot Nelson-Siegel [Excel]**, efectiva anual:
   `S(t) = β0 + (β1 + β2)·(1 − e^(−t/τ))/(t/τ) − β2·e^(−t/τ)`.  Límites: `S(0⁺) = β0 + β1`, `S(∞) = β0`. β2 da la "joroba".
6. **Descuento y precio estimado [Excel]:** `DF(t) = (1 + S(t))^(−t)`;  `P_est = Σ flujo·DF`.
7. **Calibración [Excel]:** minimizar `SSE = Σ (P_sucio − P_est)²` (sin ponderar) sobre β0, β1, β2, **libres de signo**, con **τ fijo = 3,7** (así lo deja el Solver del profesor). Arranque: β del día anterior; si no hay, los del Excel (0,1279; −0,0313; 0,0437).
8. **Curva cero cupón [Excel]:** `S(d/365)` para d = 1…10.950 días (30 años) → hoja `DatosCurvaSpot`.
9. **TIR teórica, comparación y señal [Enunciado]:** §2.
10. **DV01 por $1.000 millones de nominal [Enunciado]:** §2.

## 2. Definiciones propias (todas configurables)

| Concepto | Definición | Origen |
|---|---|---|
| Papeles usados | Los 29 de la tabla (igual que el Excel, que usa toda la tabla del día). Sensibilidad: solo los marcados **SEN** (`usar_origen`) | [Supuesto] |
| TIR observada | TIR efectiva anual (`brentq`) que iguala el **precio sucio** con los flujos del paso 3 y base días/365. La `tasa_pub` del informe se muestra al lado como referencia | [Supuesto] |
| TIR teórica | La misma TIR, pero del **precio estimado** con la curva cero ("calcular su TIR usando la cero cupón") | [Enunciado] |
| Spread | `TIR_obs − TIR_teo` en pb | [Supuesto] |
| Señal | spread > +u → **COMPRAR**; spread < −u → **VENDER**; si no, **MANTENER**. `u = 10 pb` por defecto. Sensibilidad 5/10/20 pb | [Supuesto] |
| Duración | Macaulay `D = Σ t·PV/P` (la columna del informe es Macaulay [Datos]); modificada `D* = D/(1+y)` | estándar |
| Convexidad | `C = Σ t(t+1)·PV / (P·(1+y)²)` | estándar |
| **DV01** | Nominal **N = $1.000.000.000 COP (10⁹)**. `DV01 = N/100 · [P(y−1pb) − P(y+1pb)]/2` con `y = TIR_obs`. Control: `≈ N·(P/100)·D*·1e-4` | [Enunciado] + [Supuesto] en la tasa base |
| DV01 de curva (complemento) | `N/100 · [P_est(β0−1pb) − P_est(β0+1pb)]/2`. Mover β0 desplaza **toda** la curva spot 1 pb en paralelo | [Supuesto] |
| Aproximación de precio | `ΔP/P ≈ −D*·Δy + ½·C·Δy²`, comparada con la revaluación exacta para Δy = ±50 y ±100 pb | objetivo del taller |

**Por qué comparar en TIR y no en precio.** Con los mismos flujos, la TIR baja cuando el precio sube, así que el signo del spread es el de `P_est − P_obs`: spread > 0 ⇔ el papel está **más barato** que la curva ⇔ COMPRAR. En magnitud, `spread_pb ≈ 10⁴ · (P_est − P_obs) / (P_obs · D*)`. La misma diferencia de precio pesa mucho más en un papel corto: 0,05 de precio en el TCO de 18 días son ~100 pb; en el TFIT 2058, menos de 1 pb.

**Consecuencia para la calibración.** El SSE en precios (método del Excel) casi no "ve" los TCO cortos, porque sus errores de precio son pequeños aunque en tasa sean grandes. Por eso en el tramo corto pueden salir señales fuertes que son del ajuste, no del mercado. Se reporta como sensibilidad una calibración ponderada por `1/D*` (aproxima minimizar errores en tasa), sin cambiar el método principal.

### Unidades del DV01
**$1.000 millones = 1.000.000.000 COP = 10⁹.** 10¹² es **un billón** y daría un DV01 1.000 veces mayor. `DV01 ≈ $100.000 × D* × P/100`, sin tope fijo. Hoy (tasas ≈ 13 %) la D* más alta es ≈ 7, así que el máximo ronda $650.000. Si las tasas bajan, un papel largo puede superar $1.000.000.
Valor Nominal* del informe: **millones de COP**, saldo en circulación (el TCO 20-oct-26 muestra 5.351.599 el 17-mar y el 2-oct), no monto transado. No interviene en el DV01 pedido, que es por $1.000 millones.

## 3. Hallazgos en el Excel del profesor (se corrigen en el Excel que entregamos)
1. **Dos bloques con cupón roto.** En los papeles que vencen el 3-nov-2027 (filas 112–122) y el 18-sep-2030 (filas 173–188), la columna B no está enlazada al cupón de la tabla y los cupones quedan en 0. El Excel estima 84,36 y 59,48; lo correcto con los mismos β es 94,61 y 89,22. En los otros 24 papeles, Python reproduce el Excel a ~1e-12.
2. **Los β guardados no son óptimos**: son valores de arranque (SSE 1.313,6; con los cupones corregidos y los mismos β, 720,4).
3. **Probable errata:** el TFIT 25-jul-2046 tiene cupón 13,5 en el ejemplo y 11,5 en el 2-oct (el cupón de un bono no cambia).
4. El ejemplo es del 17-mar-2026 (26 papeles). La hoja "Gráfica Curva Spot" que citan las instrucciones no existe en el archivo.
5. Las instrucciones advierten fechas en los 1900 al pegar desde el PDF: el parser interpreta años de 2 dígitos como 20xx y meses en español (`20-oct-26`).

## 4. Datos de prueba (`anexos/fixtures/`, van a `tests/fixtures/`)
- **`tes_2026-10-02.csv`** — tabla del enunciado. 29 papeles: 12 TCO y 17 con cupón (16 TFIT y 1 TFVT). Por origen de tasa: 18 SEN y 11 VAL. **Validado** campo por campo contra la imagen del enunciado; Σ nominal 562.515.499 y promedio de variación 9,96 (10,0 en la tabla). Tasas en decimal (11,607 % → 0.11607).
- **`modelo_excel_2026-03-17.json`** — β y τ del Excel; 26 papeles con `precio_estimado_excel`, `precio_estimado_correcto` y la marca `excel_roto`. Prueba dorada en E15.

## 5. Resultados preliminares del prototipo (2-oct; recalculados el 7-nov; E16 los produce de nuevo)
- **Curva (método del Excel):** β0 = 0,13544; β1 = −0,01199; β2 = 0,00780 (τ = 3,7; 29 papeles; precio sucio). SSE 6,83; RMSE de precio 0,485. Curva creciente: 12,35 % en t→0, 12,58 % a 1 año, 13,11 % a 5, 13,35 % a 10 y 13,49 % a 30 (asíntota β0 = 13,54 %).
- **Señales (umbral 10 pb):** 5 COMPRAR, 12 VENDER, 12 MANTENER; 7 de los 12 TCO salen VENDER. Umbral 5 pb: 7/15/7; umbral 20 pb: 1/8/20.
- **Caso extremo:** TFIT 3-nov-2027, spread **−103 pb** (TIR 11,57 % vs. curva 12,60 %). Su TIR desde el precio coincide con la tasa SEN publicada, así que el dato es real: el papel está caro frente a la curva, o la curva no captura ese tramo. Comentarlo en el reporte.
- **Sensibilidad de la calibración** (mismo umbral de 10 pb):
  | Variante | β0 | β1 | β2 | COMPRAR / VENDER / MANTENER |
  |---|---|---|---|---|
  | Excel (29, sin ponderar) | 0,13544 | −0,01199 | 0,00780 | 5 / 12 / 12 |
  | Ponderada por 1/(P·D*) | 0,13274 | −0,01154 | 0,01652 | 10 / 4 / 15 |
  | Solo SEN (calibra con 18; señales para los 29) | 0,13932 | −0,01274 | −0,00532 | 3 / 17 / 9 |
  Las señales cambian mucho con el método. Los resultados se presentan con el método del Excel y esta tabla como advertencia; no se presentan como recomendación firme.
- **TIR desde el precio vs. tasa publicada:** < 3 pb en los SEN y en los TFIT. En 10 de 11 VAL (TCO) no cuadra: hasta 68 pb en el TCO de 18 días (12,29 % vs. 11,607 %). Sugiere otra convención en esas valoraciones; por eso la TIR observada se calcula desde el precio.
- **Duración:** la calculada difiere de la del informe en ≤ 0,01 años.
- **DV01 por $1.000 millones:** $4.367 (TCO 20-oct-26) a $653.824 (TFIT 2058). El DV01 de curva da casi lo mismo, salvo en papeles largos con cupón bajo (TFIT 2050: $454.457 vs. $430.411). Control: DV01/((P/100)·N·1e-4) = D* con error < 1e-5.
- **Duración y convexidad (TFIT 2058, D* = 6,84, C = 94,9):**
  | Δy | ΔP/P exacto | Solo duración | Duración + convexidad |
  |---|---|---|---|
  | −100 pb | +7,35 % | +6,84 % | +7,32 % |
  | −50 pb | +3,54 % | +3,42 % | +3,54 % |
  | +50 pb | −3,31 % | −3,42 % | −3,30 % |
  | +100 pb | −6,39 % | −6,84 % | −6,37 % |

## 6. Preguntas para el profesor (enviar el lunes 9-nov)
1. **"Cada papel que se transó":** ¿son los 29 de la tabla o solo los que tienen tasa **SEN** (transados en el sistema; VAL serían de valoración)? Por defecto, los 29, como en el Excel.
2. **TIR observada:** ¿la tasa publicada o la que se deduce del precio sucio? (No cuadran en los TCO VAL.)
3. **Umbral** para comprar/vender/mantener: ¿hay un criterio (p. ej. 10 pb, o según el error del ajuste)?
4. **τ:** ¿siempre 3,7 o también se calibra?
5. **DV01:** ¿con la TIR del papel (desplazar su tasa) o con la curva (desplazamiento paralelo)? ¿Por $1.000 millones = 10⁹ COP?
6. **Renta variable:** el título y el objetivo la mencionan, pero el enunciado no pide nada. ¿Hay una parte que falta?
7. **Formato de entrega:** ¿código + informe PDF + Excel? ¿Hay sustentación?
8. **TFVT vs. TFIT 26-mar-2031:** mismo vencimiento y cupón, distinto precio; ¿se tratan como papeles distintos? (Por defecto sí.)
