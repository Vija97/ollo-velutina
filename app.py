"""Pantalla principal de la issue #8. Sin llamadas a IA ni al pipeline real."""

import hashlib
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

from ui.demo import (
    ESCENARIOS,
    buscar_registro,
    cargar_registros,
    crear_resultado_demo,
    crear_resultado_registro,
    leer_fotografia,
)


MENSAJES_SEGURIDAD = [
    "No te acerques al nido ni intentes retirarlo. Mantén al menos 5 metros de distancia y no hagas ruidos ni vibraciones cerca.",
    "Avisa al **012** o usa los canales oficiales de la Xunta.",
    "Si te pica y tienes dificultad para respirar, hinchazón generalizada o mareo, llama al **112**.",
]
ESPECIES = {
    "velutina": ("Posible avispa velutina", "Vespa velutina", "🔴"),
    "crabro": ("Avispón europeo", "Vespa crabro · especie autóctona", "🟢"),
    "otra": ("Otra especie", "No corresponde a una velutina en este ejemplo", "⚪"),
    "no_concluyente": ("Necesitamos otra fotografía", "Identificación no concluyente", "🟠"),
}
NOMBRES_NIDO = {
    "velutina": "Posible nido de velutina",
    "crabro": "Nido de avispón europeo",
    "otra": "Nido de otra especie",
}
ETSE = (42.8782, -8.5448)


def nombre_resultado(resultado: dict) -> str:
    nombre = ESPECIES[resultado["especie"]][0]
    if resultado.get("tipo") == "nido":
        return NOMBRES_NIDO.get(resultado["especie"], nombre)
    return nombre


def seguridad():
    with st.container(border=True):
        st.markdown("#### Tu seguridad, primero")
        for mensaje in MENSAJES_SEGURIDAD:
            st.markdown(f"- {mensaje}")


def main():
    st.set_page_config(page_title="Ollo Velutina · Detecta. Localiza. Protege.", page_icon="🌿", layout="wide", initial_sidebar_state="collapsed")
    css = Path(__file__).with_name("ui").joinpath("main.css").read_text()
    st.html(f"<style>{css}</style>")
    st.html('''<div class="brand"><span class="brand-icon" aria-hidden="true">◉</span>
        <span>ollo<span class="brand-light">velutina</span></span>
        <span class="brand-tag">UNHA MIRADA QUE PROTEXE</span></div>
        <section class="hero"><div class="hero-eyebrow">TECNOLOGÍA AL SERVICIO DE LA NATURALEZA</div>
        <h1>Detecta. Localiza.<br><span>Protege.</span></h1>
        <p>Una fotografía puede marcar la diferencia.<br>Identifica posibles velutinas y ayuda a cuidar nuestro entorno.</p>
        <div class="hero-foot"><span>01 &nbsp; Fotografía</span><span>02 &nbsp; Ubica</span><span>03 &nbsp; Consulta</span></div>
        <div class="hero-orbit" aria-hidden="true"><div class="bee-mark">
        <span class="bee-wing left"></span><span class="bee-wing right"></span>
        <span class="bee-head"></span><span class="bee-body"></span>
        </div></div></section>''')
    st.info("**Modo demostración · datos de ejemplo.** Los resultados proceden de fotografías de ejemplo ya clasificadas. No se analiza tu fotografía ni se envían o guardan avisos.", icon="🧪")
    st.markdown("## Una mirada más cerca de la solución")
    st.write("Añade una fotografía tomada desde una distancia segura y señala dónde has visto el insecto o el nido.")
    photo_col, location_col = st.columns([1.05, 1], gap="large")
    imagen = None
    registro = None
    registros = cargar_registros()
    with photo_col:
        with st.container(border=True):
            st.markdown("### 01 · Tu fotografía")
            origen = st.radio("¿Cómo quieres añadirla?", ["Subir fotografía", "Usar cámara"], horizontal=True, key="origen")
            if origen == "Subir fotografía":
                archivo = st.file_uploader("Selecciona una fotografía", type=["jpg", "jpeg", "png", "webp"], max_upload_size=10, key="foto_archivo")
                st.caption("JPG, PNG o WEBP · hasta 10 MB. Evita imágenes con personas o datos personales.")
            else:
                st.caption("Permite el acceso a la cámara en tu navegador. Necesita HTTPS o una ejecución local.")
                archivo = st.camera_input("Haz una fotografía desde un lugar seguro", key="foto_camara")
            foto_invalida = False
            if archivo is not None:
                try:
                    imagen = leer_fotografia(archivo.getvalue())
                    registro = buscar_registro(registros, archivo.getvalue()) if registros else None
                    if registro is not None:
                        st.image(imagen, caption="Tu fotografía · clasificación guardada de la demostración", width="stretch")
                except ValueError as error:
                    foto_invalida = True
                    st.error(str(error))
            if registros and not foto_invalida and registro is None:
                if archivo is not None:
                    st.info("Esa foto no está entre las clasificadas de ejemplo. Elige una de las fotografías de demostración.", icon="ℹ️")
                opciones = {
                    f"{nombre_resultado(item)} · {Path(item['foto_path']).name}": item
                    for item in registros
                }
                elegida = st.selectbox("Fotografía de ejemplo", list(opciones), key="foto_ejemplo")
                registro = opciones[elegida]
                imagen = leer_fotografia(registro["foto_path"].read_bytes())
                st.image(imagen, caption=f"Fotografía de ejemplo · {nombre_resultado(registro)}", width="stretch")
            if archivo is None and not registros:
                st.html('<div class="photo-empty"><span aria-hidden="true">＋</span><strong>Todo empieza con una mirada</strong><p>Añade una foto del insecto o del nido.<br>Usa el zoom; mantén la distancia.</p></div>')
            tipo_texto = st.radio("¿Qué has encontrado?", ["No lo sé", "Insecto", "Nido"], horizontal=True, key="tipo")
            tipo = {"No lo sé": "no_se", "Insecto": "insecto", "Nido": "nido"}[tipo_texto]
            if registros:
                st.caption("En esta demostración, el tipo y la especie salen de la clasificación guardada de la foto.")
    with location_col:
        with st.container(border=True):
            st.markdown("### 02 · El lugar del encuentro")
            st.write("Pulsa en el mapa para señalar la ubicación aproximada.")
            st.caption("Solo la ubicación del insecto o nido. Nunca tu domicilio ni tu posición personal.")
            if "ubicacion" not in st.session_state:
                st.session_state.ubicacion = None
            ubicacion = st.session_state.ubicacion
            mapa = folium.Map(location=ubicacion or ETSE, zoom_start=13, control_scale=True, tiles="OpenStreetMap")
            # Este selector solo necesita Leaflet. Evita cargar bibliotecas de
            # iconos y estilos de terceros que no se utilizan en esta pantalla.
            mapa.default_js = [enlace for enlace in mapa.default_js if enlace[0] == "leaflet"]
            mapa.default_css = [enlace for enlace in mapa.default_css if enlace[0] == "leaflet_css"]
            if ubicacion:
                folium.CircleMarker(ubicacion, radius=9, color="#163D2C", fill=True, fill_color="#357A55", fill_opacity=.9, tooltip="Ubicación seleccionada").add_to(mapa)
            seleccion = st_folium(mapa, height=290, use_container_width=True, returned_objects=["last_clicked"], key="ubicacion_mapa")
            ultimo_clic = seleccion.get("last_clicked") if seleccion else None
            # Consumir cada clic una vez: uno antiguo no debe pisar la entrada manual.
            if ultimo_clic and ultimo_clic != st.session_state.get("ultimo_clic_mapa"):
                st.session_state.ultimo_clic_mapa = ultimo_clic
                st.session_state.ubicacion = (ultimo_clic["lat"], ultimo_clic["lng"])
                st.rerun()
            with st.expander("Elegir coordenadas o usar una ubicación de ejemplo"):
                st.caption("Si el mapa no carga, indica aquí el lugar. En esta demostración, la ubicación se elige manualmente.")
                lat = st.number_input("Latitud", min_value=-90.0, max_value=90.0, value=ETSE[0], format="%.5f")
                lon = st.number_input("Longitud", min_value=-180.0, max_value=180.0, value=ETSE[1], format="%.5f")
                if st.button("Usar estas coordenadas", width="stretch"):
                    st.session_state.ubicacion = (lat, lon)
                    st.rerun()
                if st.button("Usar ubicación de ejemplo · ETSE", width="stretch"):
                    st.session_state.ubicacion = ETSE
                    st.rerun()
            ubicacion = st.session_state.ubicacion
            if ubicacion:
                st.success(f"Ubicación seleccionada: {ubicacion[0]:.5f}, {ubicacion[1]:.5f}", icon="📍")
            else:
                st.caption("📍 Mapa centrado en la ETSE, Santiago. Todavía no has seleccionado un lugar.")
            st.caption("¿El mapa aparece en blanco? Abre la opción de coordenadas para continuar.")
    with st.container(border=True):
        st.markdown("### 03 · Consulta el resultado")
        if registros:
            st.write("El resultado se construye a partir de la clasificación guardada de la fotografía. No se vuelve a analizar.")
            firma = (registro["sha256"] if registro else None, tipo, ubicacion)
            generar = lambda: crear_resultado_registro(registro, *ubicacion)
        else:
            st.write("Elige el caso que quieres probar. Es independiente del contenido de tu fotografía.")
            escenario = st.selectbox("Resultado de ejemplo", ESCENARIOS, key="escenario")
            firma = (hashlib.sha256(imagen).hexdigest() if imagen else None, tipo, ubicacion, escenario)
            generar = lambda: crear_resultado_demo(escenario, tipo, *ubicacion)
        listo = imagen is not None and ubicacion is not None and (registro is not None or not registros)
        if not listo:
            st.caption("Para continuar, elige una fotografía válida y selecciona una ubicación.")
        if st.session_state.get("firma_resultado") != firma:
            st.session_state.pop("resultado", None)
        if st.button("Analizar fotografía", type="primary", width="stretch", disabled=not listo):
            with st.spinner("Preparando el resultado de demostración…"):
                st.session_state.resultado = generar()
                st.session_state.firma_resultado = firma
    resultado = st.session_state.get("resultado")
    if resultado:
        st.markdown("## Tu resultado, de un vistazo")
        if registros:
            st.warning("**Demostración · clasificación guardada.** Este resultado procede de la clasificación real de una fotografía de ejemplo. No se analiza una foto nueva ni se guarda ningún aviso.", icon="🧪")
        else:
            st.warning("**Resultado simulado · datos de ejemplo.** No identifica el contenido de tu foto. No lo uses para decidir sobre un avistamiento real.")
        with st.container(border=True, key=f"resultado_{resultado['especie']}"):
            foto, detalle = st.columns([1, 1.15], gap="large")
            with foto:
                st.image(imagen, caption="Fotografía de la demostración", width="stretch")
            with detalle:
                _, cientifico, icono = ESPECIES[resultado["especie"]]
                st.markdown(f"### {icono} {nombre_resultado(resultado)}")
                st.caption(cientifico)
                confianza = resultado["confianza"]
                st.progress(confianza, text=f"Confianza: {confianza:.0%}")
                st.write(resultado["explicacion"])
                st.markdown("**Rasgos observados**")
                for rasgo in resultado["rasgos_observados"]:
                    st.markdown(f"- {rasgo}")
                if resultado["consejo_foto"]:
                    st.warning(resultado["consejo_foto"], icon="📷")
                if resultado["duplicado_de"] is not None:
                    st.warning(f"Posible duplicado: Ya hay un aviso a {resultado['duplicado_distancia_m']:.0f} m del {resultado['duplicado_fecha'][:10]}. No hace falta volver a llamar por el mismo aviso.", icon="📍")
                st.caption(f"Ubicación elegida: {resultado['lat']:.5f}, {resultado['lon']:.5f} · No se ha guardado ningún aviso.")
    seguridad()
    st.html('<footer class="footer"><strong>ollo velutina</strong><span>Cuidamos lo que nos rodea.</span><span>Identificación orientativa · Los canales oficiales verifican cada aviso.</span></footer>')


if __name__ == "__main__":
    main()
