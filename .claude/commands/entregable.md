---
description: Implementa un entregable (E00–E12) del robo-advisor siguiendo su especificación
argument-hint: E03
---

Vas a implementar el entregable **$ARGUMENTS** del proyecto.

1. Lee `CLAUDE.md` y `docs/05-plan-entregables.md`. Localiza `docs/planificacion/$ARGUMENTS-*.md` y léelo completo.
2. Revisa con `git log --oneline` y el árbol de archivos que las dependencias del entregable ya están hechas. Si falta alguna, detente y dilo.
3. Antes de escribir código, resume en 5 líneas qué vas a construir y qué queda fuera de alcance. Si algo del entregable es ambiguo o contradice los docs 00–04, pregunta; no improvises.
4. Implementa en pasos pequeños. Crea primero las pruebas indicadas cuando el entregable sea de lógica (`core/`, pipeline).
5. Ejecuta `pytest -q` y `ruff check .`. Luego ejecuta la sección "Verificación local" del entregable y muestra el resultado real (no lo supongas).
6. Marca con `[x]` los criterios de aceptación cumplidos en el propio archivo del entregable y deja explícito cuáles no.
7. Propón el mensaje de commit sugerido y espera confirmación. No hagas `git push`.
