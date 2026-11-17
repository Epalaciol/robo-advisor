# Taller 2 · Curva cero cupón de TES (Nelson-Siegel)

**Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026**  
Profesor: Juan Carlos Botero Ramírez  
Entrega: **26 de noviembre de 2026**

El taller pide un código que, con el *Informe Diario de Deuda Pública* de [www.irc.gov.co](https://www.irc.gov.co/440),
(1) calcule la **curva cero cupón** (Nelson-Siegel), (2) calcule la **TIR** de cada TES que se transó ese día
y la compare con la TIR que implica la curva para decidir **comprar, vender o mantener**, y (3) calcule el
**DV01** por cada $1.000 millones. Debía probarse con el **2 de octubre de 2026**.

## ¿Qué hay en esta carpeta?

| Archivo | Qué es | Para quién |
|---|---|---|
| [**Taller2_Informe.pdf**](Taller2_Informe.pdf) | El informe: método paso a paso, curva, TIR de cada papel, decisiones, duración, convexidad y DV01 | **Empiece por aquí** |
| [Taller2_2026-10-02.xlsx](Taller2_2026-10-02.xlsx) | El modelo en Excel (siguiendo el "Modelo Nelson Siegel.xlsx"), con fórmulas vivas | Para revisar un cálculo |
| [figuras/](figuras/) | Gráficos del informe | Opcional |

## Resultado del 2 de octubre de 2026 (en una mirada)

β0 = 13,54 % · β1 = −1,20 % · β2 = 0,78 % · τ = 3,7 → **0 comprar · 6 vender · 23 mantener**
(umbral: ±23,5 puntos básicos, una desviación estándar de las diferencias).

## Más allá del taller: la página web, siempre al día

El código no solo se probó con el 2-oct: alimenta una **página pública** —**sin registro**— con la curva de
cada día, la decisión por papel, la duración/DV01 y la historia de la curva:

**🔗 <https://mft-investements.streamlit.app/> → página "T2 Curva TES"**

Así se mantiene actualizada (no es tiempo real, es **diaria**):

```
  www.irc.gov.co                 1. Descarga el informe de cada día hábil (PDF)
        │
        ▼
  Lector + validaciones          2. Lee la tabla y revisa que cuadre (totales, fechas, cupones)
        │
        ▼
  Motor Nelson-Siegel            3. Calibra los betas, calcula la curva, TIR, decisión y DV01
        │
        ▼
  Base de datos (Supabase)       4. Guarda el resultado de cada día
        │
        ▼
  Página "T2 Curva TES"          5. Muestra siempre el último día y su historia
```

Un proceso automático (GitHub Actions, [`pipeline-taller2.yml`](../../.github/workflows/pipeline-taller2.yml))
ejecuta los pasos 1 a 4 cada día hábil y se puede **encender o apagar** a voluntad. IRC publica con unos días
de retraso, por eso el proceso revisa una ventana de días y no solo "ayer". Si repite el proceso, el resultado es el
mismo (no duplica datos).

## ¿Cómo sabemos que está bien?

El motor se comparó contra el Excel del profesor y contra el Excel y el script del grupo, con diferencias
menores a una millonésima, y el lector se probó con 31 informes reales de IRC. Los chequeos y las
anomalías que se encontraron en los datos reales (y cómo se tratan) están en
[`docs/taller-2/09-validacion.md`](../../docs/taller-2/09-validacion.md).

## ¿Dónde está el código?

[**`src/roboadvisor/taller2/`**](../../src/roboadvisor/taller2/README.md) — con una guía que explica cada
archivo en lenguaje sencillo, incluidos los fragmentos de código más importantes. Las pruebas automáticas
están en [`tests/taller2/`](../../tests/taller2/).

## Regenerar el informe y el Excel

```
pip install -e ".[reportes]"
python -m roboadvisor.taller2.reportes
```

> Ejercicio académico; no es asesoría de inversión.
