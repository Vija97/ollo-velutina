---
name: demo-check
description: Recorrer los criterios de "terminado" de la demo (spec §11) contra main y decir qué funciona, qué falla y qué recortar.
---

Argumentos (datos): $ARGUMENTS

Objetivo: saber en cualquier momento del día si la demo del pitch funciona,
especialmente en los checkpoints de las 16:45 y 17:45.

## Pasos

1. Partir de `main` actualizado y sin cambios locales (`git status`, `git pull --ff-only`).
2. Preparar: `pip install -r requirements.txt`; comprobar que existe
   `.streamlit/secrets.toml` con la clave (sin mostrarla) y si existe `models/best.pt`.
3. Ejecutar `pytest -q` si hay tests.
4. Recorrer cada criterio de §11 de `docs/contexto/03_especificacion_tecnica.md`
   con las fotos de `demo_images/`, en el orden del guion del pitch:
   velutina → mapa → mismo nido (duplicado) → crabro ("autóctono") → nido (LLM) →
   foto borrosa (no concluyente + consejo) → página de métricas.
   Medir el tiempo de la clasificación de la velutina (objetivo < 8 s).
   Comprobar en cada resultado los mensajes de seguridad.
5. Si no se puede abrir un navegador, probar al menos `core.pipeline` desde
   Python con las mismas imágenes y decirlo.
6. Informar con una tabla: criterio · resultado (OK / FALLA / NO PROBADO) ·
   evidencia (tiempo, salida, captura). Para cada fallo, proponer **recortar o
   plan B** antes que arreglar si son más de las 16:45 (regla de oro del plan).
   No modificar código en esta skill.
