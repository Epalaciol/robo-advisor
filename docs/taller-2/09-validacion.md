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
