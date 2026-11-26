# Taller 2 · Curva cero cupón de TES (Nelson-Siegel)

**Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026**  
Profesor: Juan Carlos Botero Ramírez  
Integrantes: Sebastian Duarte Uran, Paulina Jaramillo Restrepo, Juan David Londoño Grajales, Juan Luis Orrego Henao y Esteban Palacio Londoño  
Entrega: **26 de noviembre de 2026**

El taller pide un código que, con el *Informe Diario de Deuda Pública* de [www.irc.gov.co](https://www.irc.gov.co/440),
(1) calcule la **curva cero cupón** (Nelson-Siegel), (2) calcule la **TIR** de cada TES que se transó ese día
y la compare con la TIR que implica la curva para decidir **comprar, vender o mantener**, y (3) calcule el
**DV01** por cada $1.000 millones. Debía probarse con el **2 de octubre de 2026**.

## ¿Qué hay en esta carpeta?

| Archivo | Qué es | Para quién |
|---|---|---|
| [**Taller2_Informe.pdf**](Taller2_Informe.pdf) | El informe: método paso a paso, curva, TIR de cada papel, decisiones, duración, convexidad y DV01 | **Empiece por aquí** |
| [Taller2_2026-10-02.xlsx](Taller2_2026-10-02.xlsx) | El modelo en Excel (siguiendo el "Modelo Nelson Siegel.xlsx"), con fórmulas vivas y la celda de la suma de errores² lista para Solver | Para revisar un cálculo |
| [figuras/](figuras/) | Gráficos del informe | Opcional |

## Cómo leer el informe

- **Resumen ejecutivo:** la respuesta en una página.
- **1 – Metodología:** datos de IRC, flujos de cada papel (con un ejemplo), la curva Nelson-Siegel, la
  calibración (el Solver), TIR observada vs. estimada y la regla de decisión, y las fórmulas de duración,
  convexidad y DV01.
- **2 – Resultados del 2-oct:** curva y tasas cero cupón, TIR y decisión por papel, duración/convexidad/DV01
  por $1.000 millones y qué tan buena es la aproximación de precio con duración y con convexidad.
- **3 – Sensibilidad** de la decisión al método de calibración, al umbral y a τ.
- **4 – Cómo correrlo para un día determinado** (`--fecha`) y **cómo ver en la página las curvas de otros días**.
- **5 – Validación, 6 – Conclusiones, 7 – Limitaciones.**

## Resultado del 2 de octubre de 2026 (en una mirada)

β0 = 13,55 % · β1 = −1,20 % · β2 = 0,80 % · τ = 3,7 → **0 comprar · 7 vender · 22 mantener**
(umbral: ±23,7 puntos básicos, una desviación estándar de las diferencias). El DV01 por $1.000 millones va de
$4.367 pesos (TCO a 18 días) a $653.204 pesos (TFIT 2058).

Los plazos se cuentan con la **convención del mercado de TES** (días / 365 sin contar los 29 de febrero): con ella
la TIR del precio publicado coincide con la tasa SEN de IRC (por ejemplo, 13,500 % en el TFIT 2058). El Excel del
profesor usa días calendario; la sección 3.4 del informe compara ambas (con días calendario sale 6 vender · 23 mantener).

Para otro día: `python -m roboadvisor.taller2.pipeline.update_tes --fecha AAAA-MM-DD --sin-supabase`.

## Más allá del taller: la página web, siempre al día

El código no solo se probó con el 2-oct: alimenta una **página pública** —**sin registro**— con la curva de
cada día publicado por IRC (desde el 21-sep-2026), la decisión por papel, la duración/DV01 y la historia de la curva:

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
