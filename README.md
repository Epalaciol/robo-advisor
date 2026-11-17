# MFT Investments · Robo-advisor y curva de TES

**Talleres 1 y 2 de Inversiones — Maestría en Finanzas, Universidad EAFIT (2026-II)**
Profesor: Juan Carlos Botero Ramírez

Este repositorio reúne **los dos talleres** en una sola plataforma web: ayuda a una persona a armar su
portafolio de inversión según cuánto riesgo está dispuesta a asumir (Taller 1) y calcula cada día la
curva de tasas de los TES colombianos para decir qué papeles parecen caros o baratos (Taller 2).
**Es un ejercicio académico: no constituye asesoría de inversión.**

---

## 1. Pruébela (2 minutos, sin instalar nada)

**🔗 Aplicación: <https://mft-investements.streamlit.app/>**

*Si dice que la app "se fue a dormir", pulse el botón para despertarla; tarda unos segundos.*

| Quiere ver… | Qué hacer |
|---|---|
| **Taller 2** (curva de TES) | Abra la página **"T2 Curva TES"** en el menú de la izquierda. **No pide registro.** |
| **Taller 1** (robo-advisor) | Cree su cuenta en la pestaña **"Crear cuenta"** (solo pide correo, un alias y un rango de edad; no pedimos cédula, teléfono ni nombre). Luego: encuesta → armar portafolio → ver su portafolio. |
| Recorrido rápido del Taller 1 | Entre con el usuario de demostración `a3@local.test` / `Prueba1234!` (perfil ya definido). Con `prueba@local.test` / `Prueba1234!` empieza desde la encuesta. |

## 2. Las entregas

| | Taller 1 · Aversión al riesgo y Markowitz | Taller 2 · Curva cero cupón de TES |
|---|---|---|
| **Entrega** | 19 de noviembre de 2026 | 26 de noviembre de 2026 |
| **Empiece por** | [**`entregas/taller-1/`**](entregas/taller-1/README.md) | [**`entregas/taller-2/`**](entregas/taller-2/README.md) |
| Informe (PDF) | [Taller1_Informe.pdf](entregas/taller-1/Taller1_Informe.pdf) | [Taller2_Informe.pdf](entregas/taller-2/Taller2_Informe.pdf) |
| Excel | [Taller1.xlsx](entregas/taller-1/Taller1.xlsx) | [Taller2_2026-10-02.xlsx](entregas/taller-2/Taller2_2026-10-02.xlsx) |
| Código | [`src/roboadvisor/taller1/`](src/roboadvisor/taller1/README.md) | [`src/roboadvisor/taller2/`](src/roboadvisor/taller2/README.md) |

Cada carpeta de entrega tiene su propio README (también como PDF) pensado para adjuntarse a un correo:
explica qué contiene cada archivo y en qué orden leerlo.

## 3. Cómo está organizado el repositorio

```
entregas/            ← LO QUE SE ENTREGA: informes PDF, Excel y el README de cada taller
  taller-1/
  taller-2/
app/                 ← La aplicación web (lo que ve el usuario)
src/roboadvisor/     ← El código que hace los cálculos
  taller1/           ←   Markowitz, aversión al riesgo, portafolios      (con README guía)
  taller2/           ←   curva Nelson-Siegel, TIR, DV01, lector de IRC   (con README guía)
  comun/             ←   conexión a la base de datos, compartido
tests/               ← Pruebas automáticas que comprueban que los cálculos son correctos
docs/                ← Documentos de apoyo: metodología, fórmulas, validación
data_local/          ← Copia de los precios usados, para repetir los cálculos sin internet
supabase/            ← Estructura de la base de datos
.github/workflows/   ← Procesos automáticos que traen datos nuevos cada día
```

## 4. Cómo se mantiene al día

Dos procesos automáticos (GitHub Actions) traen datos nuevos y los guardan en la base de datos
(Supabase), de donde los lee la aplicación:

- **Taller 1:** cada día hábil a las 5:00 pm (hora de Bogotá) se descargan los precios de los activos de
  Yahoo Finance; en cada ingreso, el usuario ve cómo ha rendido su portafolio con los precios nuevos.
- **Taller 2:** descarga el *Informe Diario de Deuda Pública* de [www.irc.gov.co](https://www.irc.gov.co/440),
  lo valida, recalcula la curva y la publica en la página "T2 Curva TES".

No es información en tiempo real: la actualización es **diaria**.

## 5. Más información

- Cómo instalar y correr todo en un computador, pruebas y despliegue: [README_TECNICO.md](README_TECNICO.md).
- Metodología, fórmulas y validación: [`docs/`](docs/README.md).
- Privacidad: solo se guardan correo, alias, rango de edad y las respuestas de la encuesta; cada usuario
  ve únicamente sus propios datos.
