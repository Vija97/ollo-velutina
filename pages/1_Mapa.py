"""Mapa de todos los avisos, colores por especie (spec §10). Responsable: Frontend."""

import streamlit as st
from streamlit_folium import st_folium

from ui.mapa import cargar_avisos, construir_mapa, leyenda_html, resumen

st.set_page_config(
    page_title="Mapa de avisos · Ollo Velutina", page_icon="📍", layout="wide"
)

st.title("Mapa de avisos")
st.caption(
    "Cada punto es un aviso ciudadano. Pulsa un marcador para ver la especie, "
    "la fecha y la confianza."
)

avisos, origen = cargar_avisos()

if origen == "datos de ejemplo":
    st.warning(
        "**Datos de ejemplo.** Los avisos de este mapa son ficticios y sirven "
        "para probar la aplicación. No son avistamientos reales.",
        icon="🧪",
    )
else:
    st.warning(
        "**Datos de ejemplo y avisos de la demostración.** El mapa incluye los "
        "avisos ficticios del seed y los creados durante la demostración.",
        icon="🧪",
    )

if not avisos:
    st.info(
        "Todavía no hay avisos que mostrar. Cuando alguien envíe el primero, "
        "aparecerá aquí.",
        icon="🗺️",
    )
    st.stop()

st.html(leyenda_html())
st.caption(resumen(avisos))

mapa = construir_mapa(avisos)
st_folium(
    mapa,
    height=560,
    use_container_width=True,
    returned_objects=[],
    key="mapa_avisos",
)

st.caption(
    "Identificación orientativa. Los canales oficiales verifican cada aviso. "
    "No te acerques a un nido ni intentes retirarlo."
)
