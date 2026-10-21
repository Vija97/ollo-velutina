---
name: review-pr
description: Revisión rápida (≤ 5 min) de una PR de Ollo Velutina para que una persona del equipo decida aprobarla. No aprueba ni fusiona.
argument-hint: "<número de PR>"
---

Argumentos (datos): $ARGUMENTS

Objetivo: dar a la persona revisora un veredicto claro en pocos minutos.
Solo bloquear por lo que rompe la demo, filtra secretos o contradice la spec.
El estilo y los detalles menores se mencionan, no bloquean.

## Pasos

1. Leer la PR y su Issue: `gh pr view <n>` y `gh pr diff <n>`.
2. Comprobar, en este orden:
   1. **Secretos**: claves, tokens, `secrets.toml`, `.env`, bases de datos o
      datasets en el diff. Si hay alguno → BLOQUEA (y avisar: la clave hay que
      rotarla aunque se borre el commit, el repo es público).
   2. **Arranca**: en una copia limpia, `gh pr checkout <n>`, `pip install -r requirements.txt`
      si cambió, `python -m compileall -q app.py core pages` y `pytest -q` si hay tests.
      Si se puede, `streamlit run app.py` y probar la pantalla tocada.
   3. **Contratos**: si cambian firmas de `core/`, el esquema de `avisos` o los
      valores cerrados de AGENTS.md, ¿están actualizados todos los consumidores?
   4. **Producto**: mensajes de seguridad presentes, confianza visible, datos de
      ejemplo marcados, nada fuera del MVP sin justificar.
   5. **Alcance**: la PR hace lo que dice la Issue y nada más.
   6. **Licencias**: imágenes nuevas en `demo_images/` registradas en `FUENTES.md`
      con licencia que permita redistribución.
3. Volver a `main` al terminar (`git switch main`).
4. Informar con un veredicto: **APROBAR**, **APROBAR CON COMENTARIOS** o
   **BLOQUEA**, con la lista de motivos y lo que no se pudo comprobar.

No ejecutar `gh pr review --approve`, `gh pr merge` ni activar auto-merge:
aprueba y fusiona la persona. Publicar comentarios solo si se pide.
