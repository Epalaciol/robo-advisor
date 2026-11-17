# Taller 2 · Validación en dos fases

Objetivo: demostrar que el pipeline y el modelo funcionan **antes** de llenar la app con datos.
El 2-oct-2026 es el día de referencia: lo tenemos en la tabla del enunciado, en el Excel del grupo
(`referencias/Libro-taller2.xlsx`) y en el script del grupo (`referencias/taller2_nelson_siegel.py`).

## Fase 1 · hasta el 2-oct-2026
Trae los informes del **21-sep al 2-oct** (descarga de IRC o PDF en `data_local/tes/`), los valida,
calibra cada día encadenando los betas y compara el 2-oct contra todas las referencias.

```bash
python -m roboadvisor.taller2.pipeline.validacion fase1            # solo valida (no toca Supabase)
python -m roboadvisor.taller2.pipeline.validacion fase1 --cargar   # si todo PASA, carga a Supabase
```

| Código | Qué verifica | Tolerancia |
|---|---|---|
| C1 | Cada día hábil del rango: leído, validado (V1–V6) y calibrado; festivos/no publicados se listan | sin errores |
| C2 | La tabla del 2-oct leída del PDF = tabla del enunciado (29 papeles, campo por campo) | exacta |
| C3a | Betas = Excel del grupo (B35:D35) | 1e-6 |
| C3b | Precio estimado, TIR observada y estimada (XIRR), diferencia en pb y DV01 = Excel del grupo | 1e-6 / 0,01 pb |
| C3c | Decisión vs. Excel. **El Excel compara contra `$O$3` (vacía) y no contra `N3`**: queda umbral 0 (10 Comprar / 19 Vender / 0 Mantener). Con `N3` coincide con Python | AVISO documentado |
| C4a | Motor = `.py` del grupo con los mismos datos (betas, TIR, DV01, decisiones) | 1e-5 |
| C4b | El lector de PDF del `.py` lee los mismos 29 papeles (en el texto del PDF la fecha de los papeles 2050 y 2058 queda separada de su fila) | AVISO si le faltan |
| C5 | Precio = Excel del profesor (17-mar, 24 papeles sanos + 2 con cupón corregido) | 1e-8 |
| C6 | Continuidad: la tasa spot a 1/5/10 años no salta más de 50 pb de un día a otro; RMSE < 1,5 | AVISO |

Si no hay PDF del 2-oct, la fase 1 usa la tabla del enunciado para ese día (C2 se compara contra sí misma
y C4b queda OMITIDO). **Resultado con la tabla del enunciado (16-nov):** C1–C6 PASA, C3c AVISO.

## Fase 2 · del 5-oct en adelante
```bash
python -m roboadvisor.taller2.pipeline.validacion fase2            # 5-oct → hoy
python -m roboadvisor.taller2.pipeline.validacion fase2 --cargar
```
Encadena con los betas del 2-oct de la fase 1, procesa cada día y genera las gráficas:
betas en el tiempo, tasas spot a 1/5/10 años, curvas superpuestas, mapa de decisiones por papel y
día, y la curva del último día. Chequeos C1, C6 y C7 (gráficas generadas). Con `--cargar`, después
de cargar relee Supabase **con la clave pública** (como la página) y confirma que se ven todos los días.

Por último, abrir la página **Taller 2 · Curva TES** de la app y revisar que las fechas, la curva y la
historia coincidan con `exports/taller2/validacion/fase2.html`.

## Salidas
- `exports/taller2/validacion/fase1.html|md`, `fase2.html|md`: tabla de chequeos, gráficas y resumen por día.
- `exports/taller2/<fecha>/`: `resultado.csv`, `flujos.csv`, `curva.csv`, `parametros.csv` de cada día.
- `data_local/tes/`: PDF descargados (caché; no se vuelven a bajar).

## Si IRC bloquea la descarga
El comando falla con un mensaje claro (HTTP 403/429). Bajar los PDF a mano desde https://www.irc.gov.co/440
a `data_local/tes/` (cualquier nombre: la fecha se lee del contenido) y repetir con `--sin-descarga`.

## Hallazgos en los datos de IRC
- **Total publicado vs suma de filas.** Del 21 al 25-sep el total de "Tasa Fija en Pesos" que publica IRC
  difiere en 3 (millones) de la suma de las filas (561.499.244 vs 561.499.241; 559.614.871 vs
  559.614.868). No falta ninguna fila: es redondeo/arrastre de la fuente. V1 tolera
  |Δ| ≤ 0,5 × n.º de filas (`ParametrosTES.tol_total_por_fila_mm`) como **advertencia**; más que eso es error.
- **Papel que vence el día del informe.** El 22-sep IRC publica el `TCO364220926` el mismo día que vence.
  No es error del informe: V2 lo marca como advertencia, cuenta en la suma V1 y se excluye de la curva
  (`InformeTES.papeles()` solo devuelve papeles con vencimiento posterior a la fecha).
- `parsear_texto` avisa (`fila no leída: <línea>`) si un nemotécnico del texto no se leyó.
- **TCO con cupón (9-oct a 3-nov).** IRC imprimió `TCO364051027` con cupón 1,00 y limpio = sucio. Es error
  de digitación: con cupón 0 el precio 88,780 implica TIR 12,79 % (a 4 pb de la tasa VAL); con cupón 1
  implicaría 13,93 % (118 pb). Desde el 5-nov IRC lo publica corregido. `FilaTES` lo corrige a 0
  (guarda `cupon_original`) y `validar` emite la advertencia V2c. Un TCO con limpio ≠ sucio sigue siendo error.
- **PDF sin texto (21-oct).** El informe es una imagen (la tabla no es extraíble). No es error del pipeline:
  el día queda en estado `sin_texto` ("día omitido"), C1 da AVISO (no FALLA) y los betas encadenan
  del 20-oct al 22-oct. Un PDF corrupto o con fecha distinta sigue siendo `error_lectura` (FALLA).
- **Cupón pagado en la fecha del informe (3-nov, `TFIT08031127`).** Ese día IRC deja el cupón dentro del
  precio sucio (sucio 101,562 − limpio 95,875 = 5,687 ≈ cupón 5,75; el día siguiente el sucio ya es ex-cupón).
  Con la regla "solo flujos estrictamente posteriores" la TIR observada salía 4,12 % (spread −769 pb) y
  la calibración se desplazaba. Ahora `flujos(..., incluir_cupon_hoy=True)` incluye ese cupón en t = 0
  (DF = 1) cuando `sucio − limpio ≈ cupón` (`ParametrosTES.tol_cupon_hoy = 0,10`; con 0,05 esta fila
  real no pasaba: el corrido de IRC difiere en 0,063 por el rezago de precios del 3-nov). Si el precio es
  ex-cupón (`sucio − limpio ≈ 0`) el flujo se excluye como antes. Decide `core.flujos.incluye_cupon_hoy`
  (el core sigue puro: lo llama `analizar`/`validar`). Con t = 0 la TIR sale 10,37 % (vs 10,25 % publicada).
  El spread de este papel frente a la curva (≈ −210 pb; −216 pb el 30-oct) es una característica del
  papel, no un artefacto: cotiza a ~10,3 % siempre. La prueba dorada del Excel del profesor y la fase 1
  no cambian (ningún papel del 2-oct ni del 17-mar tiene cupón en la fecha).
- **3-nov: precios de TCO cortos desactualizados.** En los 8 TCO de menos de 250 días el plazo implícito en
  el precio (ln(100/P)/ln(1+r)) excede en 4 días el plazo real (precios del 30-oct tras el festivo del
  2-nov). Es un dato de la fuente; se deja como está y el efecto sobre la curva es ahora pequeño.
- **Plazo implícito de +1 día en días normales.** En los demás días el plazo implícito de los TCO excede
  en 1 día el real: IRC calcula los precios con liquidación T+1. Eso explica la diferencia entre la TIR del
  precio y la tasa VAL publicada en los TCO cortos. Se mantiene la convención del Excel del profesor
  (valoración = fecha del informe).
- **Diagnóstico del AVISO de C6 (3-nov y 4-nov) y resultado tras la corrección.** Antes de incluir el cupón
  en t = 0 el 3-nov daba SSE 61,6 / RMSE 1,457 y la spot a 1 año caía 65 pb. Las tasas publicadas cortas casi
  no se movieron (`var_pb` entre −3 y +3 pb), así que no era mercado. Después:

  | Día | β0 | β1 | β2 | SSE | RMSE | spot 0,5a | 1a | 2a | 5a |
  |---|---|---|---|---|---|---|---|---|---|
  | 30-oct | 0,13853 | −0,01589 | 0,00063 | 12,6 | 0,660 | 12,370 | 12,468 | 12,637 | 12,999 |
  | 3-nov | 0,13842 | −0,01544 | −0,00162 | 11,1 | 0,620 | 12,388 | 12,471 | 12,619 | 12,949 |
  | 4-nov | 0,13698 | −0,01574 | −0,00045 | 8,6 | 0,545 | 12,223 | 12,313 | 12,473 | 12,821 |
  | 5-nov | 0,13702 | −0,01447 | −0,00382 | 9,0 | 0,547 | 12,325 | 12,391 | 12,512 | 12,798 |

  C6 pasa sin saltos. Con `--ponderar-duracion` (antes de la corrección) el salto no desaparecía, se
  desplazaba al tramo largo (spot 5a −41 pb, RMSE 1,658); se presenta solo como sensibilidad y el método
  por defecto no cambia.
