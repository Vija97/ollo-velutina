"""Pantalla principal: foto → resultado real → aviso guardado (#8 y #12)."""

import hashlib
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

from core import geo, llm, pipeline
from ui.demo import fotos_demo, leer_fotografia


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
    st.info("**Demostración · modelo real.** La foto se analiza con YOLO y el LLM, y el aviso se guarda en la base de datos local. Es una identificación orientativa.", icon="🧪")
    st.markdown("## Una mirada más cerca de la solución")
    st.write("Añade una fotografía tomada desde una distancia segura y señala dónde has visto el insecto o el nido.")
    photo_col, location_col = st.columns([1.05, 1], gap="large")
    imagen = None
    original = None
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
            if archivo is not None:
                try:
                    original = archivo.getvalue()
                    imagen = leer_fotografia(original)
                    st.image(imagen, caption="Tu fotografía", width="stretch")
                except ValueError as error:
                    original = None
                    st.error(str(error))
            if original is None:
                opciones = {foto.name: foto for foto in fotos_demo()}
                if opciones:
                    elegida = st.selectbox("O usa una fotografía de ejemplo", list(opciones), key="foto_ejemplo")
                    if elegida:
                        original = opciones[elegida].read_bytes()
                        imagen = leer_fotografia(original)
                        st.image(imagen, caption=f"Fotografía de ejemplo · {elegida}", width="stretch")
            tipo_texto = st.radio("¿Qué has encontrado?", ["No lo sé", "Insecto", "Nido"], horizontal=True, key="tipo")
            tipo = {"No lo sé": "no_se", "Insecto": "insecto", "Nido": "nido"}[tipo_texto]
            if original is not None:
                gps = geo.get_exif_gps(original)
                if gps:
                    st.caption(f"GPS de la foto: {gps[0]:.5f}, {gps[1]:.5f}")
                    if st.session_state.get("gps_foto") != gps:
                        st.session_state.gps_foto = gps
                        st.session_state.ubicacion = gps
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
        st.markdown("### 03 · Analiza la fotografía")
        st.write("YOLO y el LLM analizan la imagen. Si ya hay un aviso compatible cerca, te lo decimos. El aviso se guarda en la base de datos local.")
        firma = (hashlib.sha256(original).hexdigest() if original else None, tipo, ubicacion)
        listo = original is not None and ubicacion is not None
        if not listo:
            st.caption("Para continuar, elige una fotografía válida y selecciona una ubicación.")
        if st.session_state.get("firma_resultado") != firma:
            st.session_state.pop("resultado", None)
        if st.button("Analizar fotografía", type="primary", width="stretch", disabled=not listo):
            with st.spinner("Analizando la fotografía… puede tardar unos segundos."):
                try:
                    st.session_state.resultado = pipeline.procesar(original, tipo, *ubicacion)
                    st.session_state.firma_resultado = firma
                    st.session_state.pop("texto_012", None)
                except Exception as error:
                    st.session_state.pop("resultado", None)
                    st.error(f"No se pudo analizar la fotografía: {error}")
    resultado = st.session_state.get("resultado")
    if resultado:
        st.markdown("## Tu resultado, de un vistazo")
        st.warning("**Identificación automática y orientativa.** El aviso se ha guardado en la base de datos local. Los canales oficiales verifican cada aviso; no lo uses para decidir por tu cuenta.", icon="🧪")
        with st.container(border=True, key=f"resultado_{resultado['especie']}"):
            foto, detalle = st.columns([1, 1.15], gap="large")
            with foto:
                st.image(imagen, caption="Fotografía analizada", width="stretch")
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
                    fecha = (resultado["duplicado_fecha"] or "")[:10]
                    st.warning(f"Posible duplicado: Ya hay un aviso a {resultado['duplicado_distancia_m']:.0f} m del {fecha}. No hace falta volver a llamar por el mismo aviso.", icon="📍")
                fuente = {"yolo": "YOLO", "llm": "LLM", "yolo+llm": "YOLO + LLM"}.get(resultado["fuente_clasificacion"], resultado["fuente_clasificacion"])
                st.caption(f"Ubicación: {resultado['lat']:.5f}, {resultado['lon']:.5f} · Fuente: {fuente} · Aviso #{resultado['id']} ({resultado['estado']})")

                # §5.6: solo velutina y no duplicado.
                if resultado["especie"] == "velutina" and resultado["duplicado_de"] is None:
                    st.divider()
                    if st.button(
                        "Generar aviso para el 012",
                        width="stretch",
                        key=f"generar_012_{resultado['id']}",
                    ):
                        with st.spinner("Redactando el aviso para el 012…"):
                            try:
                                st.session_state.texto_012 = llm.generar_aviso_012(resultado)
                            except Exception as error:
                                st.session_state.pop("texto_012", None)
                                st.error(f"No se pudo generar el aviso: {error}")
                    if st.session_state.get("texto_012"):
                        st.markdown("**Texto listo para copiar**")
                        st.code(st.session_state.texto_012, language=None)
                        st.caption("Usa el icono de copiar de la esquina del bloque.")
    seguridad()
    st.html('<footer class="footer"><strong>ollo velutina</strong><span>Cuidamos lo que nos rodea.</span><span>Identificación orientativa · Los canales oficiales verifican cada aviso.</span></footer>')


if __name__ == "__main__":
    main()
