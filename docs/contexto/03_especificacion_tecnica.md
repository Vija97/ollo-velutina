# Especificación técnica: Ollo Velutina

## 1. Alcance del MVP (lo que SÍ entra mañana)
1. Subir o hacer una foto de un insecto o nido.
2. Clasificación: modelo YOLO propio para insectos + LLM multimodal (Claude) para nidos, casos de baja confianza y explicación.
3. Ubicación: GPS de los metadatos EXIF de la foto o, si no hay, clic en el mapa.
4. Detección de duplicados (radio 50 m, últimos 30 días, misma categoría).
5. Mapa compartido con todos los avisos (colores por especie).
6. Aviso generado listo para copiar/enviar al 012.
7. Página "Sobre el modelo" con métricas (precisión, recall, matriz de confusión).

**Fuera del MVP** (solo si sobra tiempo, en este orden): mapa de calor para concellos → idioma gallego en la interfaz → panel de estadísticas → cuentas de usuario (NO hacerlo).

## 2. Stack
| Pieza | Elección | Motivo |
|---|---|---|
| App | **Streamlit** (Python 3.11) | El equipo domina Python; UI en minutos; `st.camera_input` y `st.file_uploader` |
| Mapa | **folium + streamlit-folium** | Marcadores, clic para ubicar, heatmap |
| Clasificador | **ultralytics YOLO11n** (detección) entrenado en Colab | Rápido de entrenar (20–40 min en GPU T4), se ejecuta en CPU |
| LLM | **API de Claude** con visión, modelo `claude-sonnet-5-5`, SDK `anthropic` | Nidos, casos dudosos, explicación y texto del aviso |
| Datos | **SQLite** (`data/avisos.db`) | Cero configuración |
| EXIF | **Pillow** | Extraer GPS de la foto |
| Despliegue | Local en el portátil para la demo; opcional Streamlit Community Cloud | Menos riesgo |

`requirements.txt`:
```
streamlit
streamlit-folium
folium
ultralytics
anthropic
pillow
pandas
```

## 3. Estructura de archivos
```
ollo-velutina/
├── app.py                  # Página principal: foto → resultado → aviso
├── pages/
│   ├── 1_Mapa.py           # Mapa de todos los avisos (+ heatmap)
│   └── 2_Sobre_el_modelo.py# Métricas y datasets/licencias
├── core/
│   ├── classifier.py       # Carga YOLO y clasifica
│   ├── llm.py              # Llamadas a Claude (análisis y aviso)
│   ├── geo.py              # EXIF GPS + haversine + duplicados
│   ├── db.py               # SQLite: crear tabla, insertar, listar
│   └── pipeline.py         # Orquesta todo el flujo
├── models/best.pt          # Pesos YOLO entrenados (esta noche)
├── data/avisos.db
├── data/seed_avisos.csv    # Avisos de ejemplo para que el mapa no salga vacío
├── demo_images/            # Fotos de prueba para la demo (plan B sin cámara)
├── metrics/                # confusion_matrix.png, results.json
└── .streamlit/secrets.toml # ANTHROPIC_API_KEY (no subir a git)
```

## 4. Modelo de datos (SQLite)
Tabla `avisos`:
| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK | |
| created_at | TEXT (ISO) | |
| lat, lon | REAL | |
| tipo | TEXT | `insecto` / `nido` |
| especie | TEXT | `velutina`, `crabro`, `otra`, `no_concluyente` |
| confianza | REAL | 0–1 |
| fuente_clasificacion | TEXT | `yolo`, `llm`, `yolo+llm` |
| explicacion | TEXT | Rasgos observados |
| foto_path | TEXT | |
| duplicado_de | INTEGER NULL | id del aviso original si es duplicado |
| estado | TEXT | `nuevo`, `duplicado`, `enviado` |

## 5. Flujo (pipeline)
1. **Entrada**: imagen (cámara o archivo) + tipo opcional (insecto/nido; por defecto "no sé").
2. **Ubicación**: `geo.get_exif_gps(img)`; si devuelve None → pedir clic en el mapa (`st_folium(...)["last_clicked"]`). Por defecto centrar el mapa en la ETSE (42.8782, -8.5448).
3. **Clasificación**:
   - Si es insecto o "no sé": ejecutar YOLO. Si hay detección con confianza ≥ 0,70 → resultado YOLO; además se llama al LLM solo para la explicación breve.
   - Si confianza < 0,70, no hay detección o es nido → llamar al LLM con la imagen (salida JSON, ver §7).
   - Si ambos discrepan → `no_concluyente` y pedir otra foto.
4. **Duplicados**: buscar avisos con misma especie en radio ≤ 50 m y últimos 30 días (haversine). Si existe → marcar `duplicado_de` y mostrar "Ya hay un aviso a X m del {fecha}. No hace falta volver a llamar."
5. **Guardar** en SQLite.
6. **Resultado en pantalla**: especie, confianza (barra), explicación, mensajes de seguridad, y si es velutina y no duplicado → botón "Generar aviso para el 012" (texto generado por LLM, ver §7) + botón copiar.

## 6. Clasificador YOLO (entrenar ESTA NOCHE en Colab con GPU)
```python
!pip install ultralytics roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="TU_API_KEY_ROBOFLOW")
# Copiar el snippet exacto de descarga en formato "YOLOv11" desde la página del dataset
ds = rf.workspace("hornet-behavior").project("<slug-del-proyecto>").version(1).download("yolov11")

from ultralytics import YOLO
model = YOLO("yolo11n.pt")
model.train(data=f"{ds.location}/data.yaml", epochs=40, imgsz=640, batch=16, patience=10)
metrics = model.val(split="test")   # usar SOLO el split test de la versión ORIGINAL
print(metrics.box.map50, metrics.box.mp, metrics.box.mr)
# Descargar runs/detect/train/weights/best.pt y la confusion_matrix.png
```
- Clases: `Vespa_crabro`, `Vespa_velutina` (mapear a `crabro` / `velutina`).
- Guardar `metrics/results.json` con mAP50, precisión y recall para la página "Sobre el modelo".
- Plan B si no da tiempo a entrenar: todo por LLM, y evaluar el LLM sobre 50–100 imágenes del test para tener una cifra de acierto.

## 7. Prompts del LLM

### 7.1 Análisis de imagen (system prompt)
```
Eres un experto entomólogo en especies invasoras de Galicia. Analizas una foto enviada por un ciudadano para decidir si muestra una avispa velutina (Vespa velutina) o su nido.

Distingue entre:
- velutina: cuerpo oscuro, banda naranja en el 4.º segmento abdominal, extremos de las patas amarillos, cara naranja. Nido secundario grande en copa de árbol con entrada lateral pequeña.
- crabro (avispón europeo, autóctono): tórax rojizo, abdomen mayoritariamente amarillo, patas marrones. Nidos en huecos, abiertos por abajo.
- otra: avispas comunes (Vespula, Polistes), abejas u otros insectos.
- no_concluyente: foto borrosa, lejana o sin rasgos visibles.

Sé prudente: si no ves rasgos claros, usa no_concluyente. Nunca recomiendes acercarse ni retirar el nido.

Responde SOLO con un JSON válido con esta forma:
{
  "tipo": "insecto" | "nido",
  "especie": "velutina" | "crabro" | "otra" | "no_concluyente",
  "confianza": número entre 0 y 1,
  "rasgos_observados": ["...", "..."],
  "explicacion": "1-2 frases en castellano para el ciudadano",
  "consejo_foto": "si no es concluyente, cómo hacer una foto mejor; si no, cadena vacía"
}
```
Llamada (esquema):
```python
client.messages.create(
    model="claude-sonnet-5-5", max_tokens=600, system=SYSTEM_ANALISIS,
    messages=[{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
        {"type": "text", "text": f"Tipo indicado por el usuario: {tipo}. Resultado del modelo YOLO (puede ser vacío): {yolo_resumen}"}
    ]}])
```
Parsear con `json.loads`; si falla, reintentar una vez pidiendo "solo JSON"; si vuelve a fallar → `no_concluyente`.

### 7.2 Texto del aviso al 012
```
Redacta un aviso breve y claro (máx. 80 palabras) para el servicio 012 de la Xunta de Galicia sobre un posible nido o avistamiento de avispa velutina. Incluye: tipo (insecto/nido), especie probable y confianza, coordenadas (lat, lon) con enlace a OpenStreetMap, referencia de lugar si se conoce, fecha y hora, y que la identificación es automática y orientativa. Tono neutro, en castellano.
Datos: {json_del_aviso}
```

## 8. Detección de duplicados
```python
from math import radians, sin, cos, asin, sqrt
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))
```
Regla: misma `especie`, distancia ≤ 50 m, `created_at` ≥ ahora − 30 días, `duplicado_de IS NULL` en el candidato. Devolver el más cercano.

## 9. Datos de demo
- `data/seed_avisos.csv`: 25–40 avisos ficticios repartidos por Santiago y alrededores (Conxo, Sar, Vite, Milladoiro, Ames, Teo), marcados como "datos de ejemplo" en la interfaz.
- `demo_images/`: 2 velutinas claras, 1 crabro, 1 avispa común, 1 nido secundario, 1 foto borrosa, y 2 fotos del MISMO nido con GPS cercano para enseñar el duplicado.

## 10. Colores del mapa
velutina → rojo · crabro → verde · otra → gris · no_concluyente → naranja · duplicado → icono más pequeño enlazado al original.

## 11. Criterios de "terminado" para la demo
- [ ] Foto de velutina → resultado correcto con confianza y explicación en < 8 s.
- [ ] Segunda foto del mismo nido → "duplicado" con distancia.
- [ ] Nido → clasificado por el LLM.
- [ ] Foto borrosa → no concluyente + consejo.
- [ ] Mapa con datos de ejemplo + avisos nuevos.
- [ ] Página de métricas con matriz de confusión.
- [ ] Vídeo de respaldo de la demo grabado.
