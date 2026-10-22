# Reglas del repositorio (Ollo Velutina · Hackathon ETSE 2026)

Se aplican a personas y agentes. Prioridad: **una demo que funcione a las 18:45**.
Si una regla de aquí choca con llegar a tiempo, se recorta alcance, no la regla.

## Contexto obligatorio

Antes de tocar código, leer lo pertinente de:

- [Contexto del problema](docs/contexto/02_contexto_velutina.md): especies, nidos,
  mensajes de seguridad y datasets con su licencia.
- [Especificación técnica](docs/contexto/03_especificacion_tecnica.md): alcance
  del MVP, stack, estructura, modelo de datos, pipeline, prompts y criterios de
  "terminado" (§11).
- [Plan del día y pitch](docs/contexto/05_plan_dia_y_pitch.md): horario, roles y
  regla de oro.

La especificación manda. No añadir dependencias, frameworks ni pantallas fuera de
ella sin decirlo en la Issue. "Fuera del MVP" solo si el MVP ya funciona, y en
el orden indicado. **Cuentas de usuario: no.**

## Flujo de trabajo

1. **Issue** pequeña (≤ 1 h de trabajo) con qué se hace y cómo se comprueba.
   Para trabajo trivial basta el título.
2. **Rama** desde `main` actualizado: `feat/<n>-<slug>`, `fix/<n>-<slug>`,
   `docs/<n>-<slug>` (skill [start-task](.agents/skills/start-task/SKILL.md)).
3. **Commits** semánticos y **PR** a `main` con `Closes #<n>`
   (skill [semantic-commits-and-push](.agents/skills/semantic-commits-and-push/SKILL.md)).
4. **1 aprobación** de otra persona del equipo y merge (squash). La revisión
   es rápida: ¿arranca?, ¿hace lo que dice la Issue?, ¿sin secretos?
   (skill [review-pr](.agents/skills/review-pr/SKILL.md)).
5. Tras cada merge relevante, alguien ejecuta la demo completa
   (skill [demo-check](.agents/skills/demo-check/SKILL.md)).

Tablero: [Ollo Velutina — Seguimiento](https://github.com/users/Vija97/projects/1)
(config en `.github/project-config.json`). Cada Issue pasa por
`Por hacer → En curso → En revisión → Hechas`; `Bloqueadas` exige escribir en la
Issue el motivo y el siguiente paso. Quien coge una Issue se la asigna y la mueve
a En curso; al abrir la PR, a En revisión; al fusionarse, a Hechas. Cada Issue
indica de qué otras depende: no empezar una cuyas dependencias no están Hechas
salvo con datos de ejemplo.

`main` siempre arranca con `streamlit run app.py`. Nunca commits directos a `main`.
Los agentes no aprueban ni fusionan PRs.

PRs pequeñas y frecuentes: una PR abierta más de ~45 min es una señal de alarma.
Cada persona trabaja en sus archivos (ver reparto en el plan) para evitar conflictos.
Si hay que tocar el archivo de otra persona, avisar antes.

## Contratos entre módulos

Las firmas de `core/` y el esquema de la tabla `avisos` (spec §4) son la frontera
entre personas. Cambiarlas exige avisar al equipo y actualizar a la vez a
todos los consumidores en la misma PR.

Valores cerrados (no inventar otros):

- `tipo`: `insecto` | `nido`
- `especie`: `velutina` | `crabro` | `otra` | `no_concluyente`
- `fuente_clasificacion`: `yolo` | `llm` | `yolo+llm`
- `estado`: `nuevo` | `duplicado` | `enviado`

## Verificación

- Lógica determinista (`geo`, `db`, duplicados): un test rápido en `tests/`
  con `pytest`. No hace falta TDD formal.
- Modelo y LLM: se mide, no se opina. Las cifras del pitch y de "Sobre el modelo"
  salen de `metrics/` y de evaluar con el split **test de la versión original**
  (nunca con datos "augmented" ni con imágenes vistas en entrenamiento).
- No declarar algo como hecho sin haberlo ejecutado. En la PR: qué se probó y cómo.

## Producto: cosas que no se negocian

- Los **mensajes de seguridad** (contexto §3) aparecen en toda pantalla de resultado.
- La clasificación siempre muestra su **confianza**; con baja confianza, se pide
  otra foto. Nunca recomendar acercarse o retirar un nido.
- Los datos de ejemplo se marcan como **"datos de ejemplo"** en la interfaz.
- Las cifras del pitch van con su fuente (contexto §1 y §5).

## Secretos, datos y licencias (el repo es público)

- `ANTHROPIC_API_KEY` y la clave de Roboflow solo en `.streamlit/secrets.toml`
  o variables de entorno. Nunca en código, notebooks, capturas ni commits.
- No subir datasets. Solo `models/best.pt`, métricas y las fotos de `demo_images/`
  cuya licencia permita redistribución (anotar fuente y licencia en
  `demo_images/FUENTES.md`). Fotos de EPPO (solo uso educativo) o de VespApp
  (CC BY-NC) no se suben: se usan en local.
- Sin datos personales: solo ubicación del nido y foto.

## Congelación de código (17:45)

Desde las 17:45 solo entran PRs `fix/` de errores que rompen la demo.
Nada de refactors, estilos ni features nuevas.
