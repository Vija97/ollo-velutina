# Probar la pantalla principal · issues #8 y #12

La pantalla principal analiza la fotografía en vivo con `core.pipeline.procesar`
(YOLO + LLM), guarda el aviso en SQLite y lo deja disponible para el mapa. Ya no
usa clasificaciones guardadas ni resultados inventados.

Reparto de la clasificación:

- **Nido con YOLO ≥ 0,70**: manda YOLO (es estable y rápido); no se llama al LLM.
- **Nido sin detección** o confianza baja: decide el LLM.
- **Insecto**: YOLO con confianza ≥ 0,70 y el LLM redacta la explicación; si
  discrepan, `no_concluyente`.
- **Foto borrosa**: `no_concluyente` con consejo para otra foto.

## Qué se puede probar

1. Arranca la aplicación desde la raíz del repositorio:

   ```bash
   source .venv/bin/activate     # en Windows: .\.venv\Scripts\Activate.ps1
   streamlit run app.py
   ```

2. Elige una **fotografía de ejemplo** o sube una tuya (JPG, PNG o WEBP, ≤10 MB).
   Si la foto tiene GPS en el EXIF, la ubicación se rellena sola.
3. Elige **Nido** para `velutina_1.jpg`/`velutina_2.jpg`/`crabro_1.jpg`, o
   **No lo sé** para la borrosa. Pulsa en el mapa si la foto no trae GPS.
4. Pulsa **Analizar fotografía**. Tarda ~5 s en los nidos con detección.

Resultados esperados con las fotos de demo:

| Foto | Tipo elegido | Resultado |
|---|---|---|
| `velutina_1.jpg` | Nido | Posible nido de velutina · 87 % |
| `velutina_2.jpg` | Nido | Posible nido de velutina · 83 % |
| `crabro_1.jpg` | Nido | Nido de avispón europeo · 87 % |
| `no_concluyente_1.jpg` | No lo sé | No concluyente · consejo |

El aviso se guarda en `data/avisos.db` y aparece en la página **Mapa**. Para
probar el duplicado, analiza dos fotos con coordenadas a menos de 50 m (el seed
ya tiene avisos cerca de la ETSE: elige un punto limpio para la primera foto).

Las fotos de `demo_images/` son fotogramas del dataset CC BY 4.0; fuente y
licencia en `demo_images/FUENTES.md`. El dataset completo vive en `datasets/` y
está excluido por `.gitignore`.

## Limitación conocida

El LLM de la cuenta (DeepSeek V4.1 Flash vía OpenRouter) es **inestable** al
clasificar nidos y puede tardar hasta 20 s. Por eso los nidos con detección YOLO
no dependen de él. Si se fuerza el camino LLM en un nido, la especie puede variar
entre llamadas; es una limitación del proveedor, no del pipeline.

## Comprobaciones

Desde la raíz:

```bash
python -m pytest -q
```

**54 pruebas superadas**: imágenes, pipeline (YOLO, LLM, nido, discrepancia,
duplicado), base de datos, geo, mapa, pantalla, cámara simulada y errores.

Probado en Chromium: las cuatro fotos, subida real, GPS EXIF, resultado, aviso
guardado y aparición en el mapa. La cámara física del portátil debe probarse
antes de la demo.
