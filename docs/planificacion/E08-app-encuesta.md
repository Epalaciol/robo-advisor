# E08 · App: encuesta y guardado

**Depende de:** E03, E07 · **Rama:** `e08-app-encuesta` · **Commit:** `feat(app): E08 encuesta de aversión al riesgo y guardado`

## Objetivo
Que el usuario responda el cuestionario una sola vez, vea su perfil y A, y quede guardado junto con los factores personales que explican su aversión al riesgo (para el análisis de los 5 voluntarios).

## Alcance
- `pages/1_Encuesta.py`
  - Si ya existe encuesta → mostrar resultado (puntaje, perfil, A, fecha) en modo lectura con explicación de qué significa `U = E(r) − ½Aσ²` y un mini gráfico de utilidad vs σ para su A (curva simple, ver E09 para estilo). No permitir repetirla.
  - Si no existe → formulario con las 9 preguntas (de `core.cuestionario.PREGUNTAS`, radio buttons, sin respuesta preseleccionada) **más** los factores opcionales de `FACTORES_SUGERIDOS` (guardados en `perfiles.factores`).
  - Botón "Calcular mi perfil": valida que estén las 9, llama `puntuar`, muestra el resultado y pide **confirmar y guardar**. Guardar = insert en `encuestas` (y update de `perfiles.factores`).
  - Tras guardar, botón para ir al Constructor.
- `data/repositorio_usuario.py`: `guardar_encuesta(resultado, respuestas)`, `actualizar_factores(factores)`. Manejar el caso de doble envío (violación de `unique`) con mensaje claro.
- Texto de apoyo: qué es la aversión al riesgo y cómo se usa en el portafolio completo (breve).
- Accesibilidad básica: preguntas numeradas, opciones con texto completo.

## Fuera de alcance
Repetir la encuesta, editar respuestas, loterías.

## Pruebas
- Pytest: construcción del payload a insertar a partir de respuestas (sin red); validación de "faltan respuestas".
- Prueba de integración opcional (`-m integration`): insertar y leer la encuesta con un usuario de prueba y comprobar que un segundo insert falla.

## Verificación local (manual)
- [ ] Un usuario nuevo contesta todo en "b" → puntaje 18, Moderado, A=4; queda en `encuestas`.
- [ ] Recargar y volver a entrar muestra el resultado, sin formulario.
- [ ] Intentar contestar con una pregunta vacía muestra error y no guarda.
- [ ] Los factores aparecen en `perfiles.factores`.
- [ ] Un segundo usuario no puede ver el resultado del primero (probar con dos sesiones).

## Criterios de aceptación
- [ ] Flujo completo sin errores; datos correctos en Supabase. **Pendiente**: requiere Supabase real (E01) para el checklist manual; el payload y la lógica de validación ya están probados con pytest.
- [x] La encuesta es inmutable desde la app (solo insert; sin update/delete en la UI ni en `repositorio_usuario.py`).
- [x] Sin cálculos de puntaje fuera de `core/` (la página solo llama a `puntuar()`).
