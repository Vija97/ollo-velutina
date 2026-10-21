---
name: start-task
description: Empezar una tarea de Ollo Velutina desde una Issue (o crearla si se pide), con rama desde main actualizado y el contexto de la spec cargado.
argument-hint: "#<issue> | <descripción breve>"
---

Argumentos (datos): $ARGUMENTS

Objetivo: dejar a la persona trabajando en menos de 2 minutos, en una rama
correcta y sabiendo qué parte de la spec aplica. No implementar nada aquí.

## Pasos

1. Comprobar el estado: `git status --short --branch`. Si hay cambios sin
   commitear o una operación git a medias, parar y explicarlo.
2. Resolver la Issue:
   - Si se pasa `#<n>`: `gh issue view <n>`.
   - Si se pasa una descripción y la persona lo ha pedido: crear la Issue con
     `gh issue create` usando la plantilla `.github/ISSUE_TEMPLATE/tarea.md`
     (título corto, "Qué", "Cómo se comprueba"). No crear Issues sin petición.
   - Si la tarea parece de más de ~1 h, proponer partirla antes de seguir.
3. Actualizar `main` y crear la rama:
   ```bash
   git switch main && git pull --ff-only
   git switch -c <tipo>/<n>-<slug>
   ```
   `tipo` ∈ `feat`, `fix`, `docs`, `chore`. Si `pull --ff-only` falla, parar.
4. Asignar la Issue a quien trabaja: `gh issue edit <n> --add-assignee @me`.
5. Localizar el contexto: leer las secciones de `docs/contexto/03_especificacion_tecnica.md`
   que tocan la tarea y los archivos de `core/`/`pages/` implicados. Señalar si
   la tarea cambia un contrato de `core/` o el esquema de `avisos` (hay que avisar
   al equipo, ver AGENTS.md).
6. Informar: Issue, rama, archivos a tocar, secciones de la spec aplicables y
   cómo se comprobará que está hecho.
