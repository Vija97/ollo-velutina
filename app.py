"""Ollo Velutina: foto → resultado → aviso (spec §5). Responsable: Frontend."""

import streamlit as st

MENSAJES_SEGURIDAD = [
    "No te acerques al nido ni intentes retirarlo. Mantén al menos 5 metros de distancia y no hagas ruidos ni vibraciones cerca.",
    "Avisa al **012** o usa los canales oficiales de la Xunta.",
    "Si te pica y tienes dificultad para respirar, hinchazón generalizada o mareo, llama al **112**.",
]

st.set_page_config(page_title="Ollo Velutina", page_icon="🐝")
st.title("Ollo Velutina")
st.caption("Haz una foto: te decimos si es velutina, si ya está avisado y te preparamos el aviso para el 012.")

st.info("En construcción.")

with st.expander("Seguridad", expanded=True):
    for mensaje in MENSAJES_SEGURIDAD:
        st.markdown(f"- {mensaje}")
