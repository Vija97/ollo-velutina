"""Métricas del modelo y datasets con licencia (spec §6, contexto §4)."""

import json
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
METRICAS = RAIZ / "metrics" / "results.json"

st.set_page_config(
    page_title="Sobre el modelo · Ollo Velutina", page_icon="📊", layout="wide"
)

st.title("Sobre el modelo")
st.caption(
    "YOLO11n entrenado por el equipo para detectar avispas y un LLM para nidos y "
    "casos dudosos. La identificación es automática y orientativa."
)

if not METRICAS.is_file():
    st.warning(
        "Todavía no hay métricas del modelo. Ejecuta la evaluación y vuelve a esta página."
    )
    st.stop()

datos = json.loads(METRICAS.read_text(encoding="utf-8"))
modelo = datos.get("modelo", {})
test = datos.get("test", {})
dataset = datos.get("dataset", {})


def numero(valor, decimales=3):
    try:
        return f"{float(valor):.{decimales}f}"
    except (TypeError, ValueError):
        return "—"


def porcentaje(valor, decimales=1):
    try:
        return f"{float(valor):.{decimales}%}"
    except (TypeError, ValueError):
        return "—"


st.markdown("## Resultados en test")
columnas = st.columns(4)
columnas[0].metric("Precisión", numero(test.get("precision")))
columnas[1].metric("Recall", numero(test.get("recall")))
columnas[2].metric("mAP50", numero(test.get("mAP50")))
columnas[3].metric("mAP50-95", numero(test.get("mAP50_95")))

if test.get("imagenes"):
    st.caption(
        f"{test.get('imagenes')} imágenes y {test.get('instancias', '—')} instancias "
        "del split de test, separado por secuencia de vídeo."
    )

por_clase = test.get("por_clase") or {}
if por_clase:
    st.markdown("### Por clase")
    filas = [
        {
            "Clase": clase,
            "Precisión": numero(valores.get("precision")),
            "Recall": numero(valores.get("recall")),
            "mAP50": numero(valores.get("mAP50")),
            "mAP50-95": numero(valores.get("mAP50_95")),
            "Instancias": valores.get("instancias", "—"),
        }
        for clase, valores in por_clase.items()
    ]
    st.dataframe(filas, hide_index=True, width="stretch")

umbral = datos.get("umbral_demo_0_70") or {}
if umbral:
    st.markdown("### Umbral de la demo (0,70)")
    st.write(
        f"Con ese umbral se aceptan **{porcentaje(umbral.get('cobertura'))}** de las "
        f"imágenes y acierta el **{porcentaje(umbral.get('acierto_entre_aceptadas'))}** "
        "de las aceptadas. Por debajo del umbral decide el LLM."
    )

st.markdown("## Matriz de confusión")
matrices = [
    ("confusion_matrix.png", "Test"),
    ("confusion_matrix_normalized.png", "Test normalizada"),
    ("confusion_matrix_llm.png", "LLM en test"),
]
columnas = st.columns(3)
mostrada = False
for columna, (archivo, titulo) in zip(columnas, matrices):
    ruta = RAIZ / "metrics" / archivo
    if ruta.is_file():
        columna.image(str(ruta), caption=titulo, width="stretch")
        mostrada = True
if not mostrada:
    st.info("Las matrices de confusión se generan al evaluar el modelo.")

st.markdown("## Datos y licencia")
if dataset:
    fuente = dataset.get("fuente", "Dataset")
    url = dataset.get("url")
    enlace = f"[{fuente}]({url})" if url else fuente
    st.markdown(
        f"**Fuente:** {enlace} · **Licencia:** {dataset.get('licencia', '—')}"
    )
    clases = ", ".join(dataset.get("clases") or [])
    st.write(
        f"{dataset.get('imagenes', '—')} imágenes · "
        f"{dataset.get('secuencias_de_video', '—')} secuencias de vídeo · "
        f"clases: {clases or '—'}"
    )

split = datos.get("split") or {}
if split.get("protocolo"):
    st.caption(f"Split: {split['protocolo']}")
    train, valid, prueba = split.get("train", {}), split.get("valid", {}), split.get("test", {})
    st.caption(
        f"Train: {train.get('imagenes', '—')} imágenes · "
        f"Valid: {valid.get('imagenes', '—')} · Test: {prueba.get('imagenes', '—')}. "
        "El dataset completo no se redistribuye: vive en `datasets/` (ignorado por git)."
    )

limitacion = datos.get("limitacion_conocida")
if limitacion:
    st.warning(limitacion, icon="⚠️")

fugas = datos.get("fugas_de_datos") or {}
if fugas.get("nota"):
    st.caption(f"Fugas de datos: {fugas['nota']}")

latencia = datos.get("latencia_cpu") or {}
if latencia:
    st.caption(
        f"Latencia en CPU: {latencia.get('inferencia_yolo_ms', '—')} ms por inferencia "
        f"YOLO · fin a fin máximo {latencia.get('fin_a_fin_max_ms', '—')} ms."
    )
