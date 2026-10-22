# Probar la pantalla principal · issue #8

La pantalla principal funciona con **fotografías de demo ya clasificadas**. La
especie y la confianza que se muestran salen de ejecutar `models/best.pt` sobre
cada foto y guardar el resultado en `demo_images/clasificaciones.csv`; la app no
vuelve a analizar la imagen. No implementa la página del mapa (#9), los botones
del 012 (#11) ni la conexión al pipeline (#12). `core/` y sus contratos no se
modifican.

## Qué se puede probar

1. Arranca la aplicación desde la raíz del repositorio:

   ```bash
   source .venv/bin/activate     # en Windows: .\.venv\Scripts\Activate.ps1
   streamlit run app.py
   ```

2. Abre la dirección que aparece en la terminal (`http://localhost:8501`).
3. En **01 · Tu fotografía**, elige una **Fotografía de ejemplo**: velutina,
   velutina duplicada, avispón europeo o no concluyente. También puedes subir
   una de las cuatro fotos de `demo_images/`; se reconocen por su contenido.
   Si subes otra foto, la app avisa de que no está clasificada y ofrece las de
   ejemplo.
4. Elige **Insecto**, **Nido** o **No lo sé**. En esta fase el tipo y la especie
   se toman de la clasificación guardada.
5. Pulsa en el mapa para situar el encuentro. También puedes abrir **Elegir
   coordenadas o usar una ubicación de ejemplo** y elegir la ETSE.
6. Pulsa **Analizar fotografía**.

Los cuatro casos cubren la comprobación de #8: nido de velutina, nido de avispón
europeo, duplicado (18 m, con fecha) y no concluyente (con consejo para otra foto). Los
mensajes de seguridad aparecen siempre. Al cambiar la foto, el tipo o el lugar,
el resultado anterior se retira hasta volver a analizar.

La ubicación se elige manualmente: todavía no se extrae el GPS de los metadatos.
Las fotos se validan y normalizan en memoria para mostrarlas, sin escribir nada
en disco ni llamar a ninguna API.

El mapa necesita acceso a `cdn.jsdelivr.net` y `tile.openstreetmap.org`. Si no
carga, la entrada manual de coordenadas permite continuar.

## Procedencia de las fotos

Las cuatro son fotogramas del split `test` del dataset de Roboflow
«[Original] Vespa crabro and Vespa Velutina» v2 (**CC BY 4.0**). Fuente y licencia
de cada archivo, en `demo_images/FUENTES.md`. El dataset completo no se
redistribuye: vive en `datasets/` y `.gitignore` lo excluye.

Las clasificaciones del manifiesto se generaron con:

```python
from ultralytics import YOLO
modelo = YOLO("models/best.pt")
modelo.predict(source="demo_images/velutina_1.jpg", imgsz=640, device="cpu")
```

## Comprobaciones

Desde la raíz:

```bash
python -m pytest -q
```

**16 pruebas superadas en esta rama** (22 al fusionar también el mapa de #9): inicio, validación de imágenes, manifiesto, un
resultado por cada foto (velutina, crabro, duplicado y no concluyente), confianza,
rasgos, consejos, seguridad, retirada de resultados antiguos, subida por huella,
foto no clasificada, cámara simulada y el mapa de #9.

Además se ha probado en Chromium con la app real: selección de las cuatro fotos,
subida por el control de archivos, clic en el mapa, popup y casos de duplicado y
no concluyente. La cámara física del portátil debe probarse antes de la demo.

## Seguimiento en GitHub

La issue #8 está asignada a `IagoVarelaR`. Con esta entrega se cumplen sus tres
comprobaciones, así que la PR puede usar `Closes #8`. La conexión al modelo en
vivo sigue siendo #12.
