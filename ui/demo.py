"""Ejemplos SIMULADOS, sin clasificación ni llamadas al backend.

La salida sigue el contrato de la PR #1. No sustituye las fotos clasificadas
de la base de datos que requiere la issue #8.
"""

from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

ESCENARIOS = ("Posible velutina", "Avispón europeo", "Otra especie", "Posible duplicado", "No concluyente")


def leer_fotografia(contenido: bytes) -> bytes:
    """Valida y normaliza la foto en memoria; no escribe archivos."""
    if len(contenido) > 10 * 1024 * 1024:
        raise ValueError("La fotografía supera los 10 MB. Elige una imagen más pequeña.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(contenido)) as imagen:
                if imagen.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("Usa una fotografía JPG, PNG o WEBP.")
                if imagen.width * imagen.height > 25_000_000:
                    raise ValueError("La imagen es demasiado grande. Redúcela a menos de 25 megapíxeles.")
                imagen = ImageOps.exif_transpose(imagen).convert("RGB")
                imagen.thumbnail((1600, 1600))
                salida = BytesIO()
                imagen.save(salida, format="JPEG", quality=90)
                return salida.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("No podemos abrir esa fotografía. Prueba con otro archivo JPG, PNG o WEBP.") from error


def crear_resultado_demo(escenario: str, tipo: str, lat: float, lon: float) -> dict:
    """Devuelve el caso elegido, sin inferir nada del contenido de una foto."""
    if escenario not in ESCENARIOS:
        raise ValueError("Escenario de demostración desconocido")
    especie, confianza, explicacion, rasgos = {
        "Posible velutina": ("velutina", .93, "En este ejemplo, la combinación de cuerpo oscuro y patas amarillas es compatible con una velutina. La identificación real debe ser verificada.", ["Cuerpo mayoritariamente oscuro", "Banda anaranjada en el abdomen", "Extremos de las patas amarillos"]),
        "Avispón europeo": ("crabro", .89, "Este ejemplo representa un avispón europeo, una especie autóctona. Su abdomen más amarillo y su tórax rojizo ayudan a distinguirlo.", ["Tórax de tono rojizo", "Abdomen mayoritariamente amarillo", "Patas marrones"]),
        "Otra especie": ("otra", .84, "Este ejemplo representa una avispa común. Su aspecto no corresponde a una velutina.", ["Franjas amarillas y negras contrastadas", "Ausencia del patrón oscuro típico de la velutina"]),
        "Posible duplicado": ("velutina", .91, "Este ejemplo representa un avistamiento compatible con un aviso anterior cercano del mismo tipo.", ["Rasgos compatibles con velutina en el ejemplo"]),
        "No concluyente": ("no_concluyente", .38, "En este ejemplo no se distinguen suficientes detalles para identificar la especie con seguridad.", ["Detalles insuficientes para una identificación fiable"]),
    }[escenario]
    if tipo == "nido" and especie != "no_concluyente":
        explicacion, rasgos = {
            "velutina": ("Este ejemplo representa un posible nido secundario de velutina. Su identificación requiere verificación por los canales oficiales.", ["Forma redondeada o de pera", "Posible entrada lateral pequeña", "Ubicación en la copa de un árbol"]),
            "crabro": ("Este ejemplo representa un nido de avispón europeo, una especie autóctona.", ["Situado en un hueco protegido", "Abertura inferior visible en el ejemplo"]),
            "otra": ("Este ejemplo representa un nido de otra especie de avispa.", ["Estructura diferente del nido secundario típico de velutina"]),
        }[especie]
    duplicado = escenario == "Posible duplicado"
    return {
        "id": 1001, "created_at": "2026-10-22T10:00:00+00:00",
        "lat": lat, "lon": lon, "tipo": "insecto" if tipo == "no_se" else tipo,
        "especie": especie, "confianza": confianza, "fuente_clasificacion": "llm",
        "explicacion": explicacion, "foto_path": "", "duplicado_de": 1000 if duplicado else None,
        "estado": "duplicado" if duplicado else "nuevo", "rasgos_observados": rasgos,
        "consejo_foto": "Prueba con otra fotografía más nítida y buena luz. Usa el zoom y mantén al menos 5 metros de distancia; no te acerques al nido." if confianza < .70 else "",
        "duplicado_distancia_m": 20.0 if duplicado else None,
        "duplicado_fecha": "2026-10-21T10:00:00+00:00" if duplicado else None,
    }
