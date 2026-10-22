"""Orquesta el flujo completo foto → resultado → aviso guardado (spec §5). Responsable: Backend."""

from __future__ import annotations

from datetime import datetime

from core import db
from core.classifier import UMBRAL_CONFIANZA, clasificar_yolo
from core.geo import buscar_duplicado
from core.llm import analizar_imagen

DB_PATH = db.DB_PATH

EXPLICACION_YOLO = {
    "velutina": "Cuerpo oscuro con banda naranja ancha en el abdomen y patas con extremos amarillos.",
    "crabro": "Tórax rojizo y abdomen mayoritariamente amarillo; avispón europeo autóctono.",
}
RASGOS_YOLO = {
    "velutina": [
        "Cuerpo mayoritariamente oscuro",
        "Banda anaranjada en el abdomen",
        "Extremos de las patas amarillos",
    ],
    "crabro": [
        "Tórax de tono rojizo",
        "Abdomen mayoritariamente amarillo",
        "Patas marrones",
    ],
}
CONSEJO_OTRA_FOTO = (
    "Haz otra foto más cerca y con buena luz, enfocando al insecto o al nido "
    "sin acercarte a él."
)


def _no_concluyente(tipo: str, explicacion: str = "La imagen no permite una identificación segura.") -> dict:
    return {
        "tipo": tipo,
        "especie": "no_concluyente",
        "confianza": 0.0,
        "rasgos_observados": [],
        "explicacion": explicacion,
        "consejo_foto": CONSEJO_OTRA_FOTO,
    }


def _clasificar(imagen_bytes: bytes, tipo: str) -> tuple[dict, str]:
    """Devuelve (resultado de clasificación, fuente_clasificacion)."""
    # YOLO también en nidos: detecta las avispas sobre el nido y es estable.
    yolo = clasificar_yolo(imagen_bytes)
    resumen = f"{yolo['especie']} {yolo['confianza']:.2f}" if yolo else ""

    if yolo and yolo["confianza"] >= UMBRAL_CONFIANZA:
        # Nido con YOLO fiable: el detector manda y no dependemos del LLM.
        if tipo == "nido":
            return {
                "tipo": "nido",
                "especie": yolo["especie"],
                "confianza": yolo["confianza"],
                "rasgos_observados": RASGOS_YOLO.get(yolo["especie"], []),
                "explicacion": EXPLICACION_YOLO.get(yolo["especie"], ""),
                "consejo_foto": "",
            }, "yolo"

        # Insecto, o nido con crabro: segunda opinión del LLM.
        # No se le dice que YOLO ve un crabro: se lo cree y es justo donde falla.
        resumen_llm = "" if yolo["especie"] == "crabro" else resumen
        try:
            llm = analizar_imagen(imagen_bytes, tipo, resumen_llm)
        except Exception:
            llm = None

        tipo_final = "nido" if tipo == "nido" else "insecto"
        especie_llm = (llm or {}).get("especie", "no_concluyente")
        if "velutina" in (yolo["especie"], especie_llm):
            # Ante la duda gana la velutina: un falso "crabro" deja pasar una invasora.
            especie = "velutina"
            if especie_llm == "velutina":
                confianza = float(llm["confianza"])
                if yolo["especie"] == "velutina":
                    confianza = max(confianza, yolo["confianza"])
            else:
                confianza = yolo["confianza"]
        elif yolo["especie"] == "crabro" and especie_llm == "crabro":
            especie, confianza = "crabro", min(yolo["confianza"], float(llm["confianza"]))
        elif tipo != "nido" and yolo["especie"] == "crabro":
            # En insectos, un crabro de YOLO es fiable: el LLM solo no lo confirma.
            especie, confianza = "crabro", yolo["confianza"]
        else:
            return _no_concluyente(
                tipo_final, "El modelo de imagen y el análisis visual no coinciden."
            ), "yolo+llm"

        return {
            "tipo": tipo_final,
            "especie": especie,
            "confianza": confianza,
            "rasgos_observados": (llm or {}).get("rasgos_observados") or RASGOS_YOLO.get(especie, []),
            "explicacion": (llm or {}).get("explicacion") or EXPLICACION_YOLO.get(especie, ""),
            # Con confianza baja se pide otra foto, también si la especie es velutina (AGENTS.md).
            "consejo_foto": CONSEJO_OTRA_FOTO if confianza < UMBRAL_CONFIANZA else "",
        }, "yolo+llm" if llm else "yolo"

    # Sin detección, confianza baja o nido sin avispas claras: decide el LLM.
    llm = analizar_imagen(imagen_bytes, tipo, resumen)
    tipo_final = "nido" if tipo == "nido" else llm["tipo"]
    return {
        "tipo": tipo_final,
        "especie": llm["especie"],
        "confianza": llm["confianza"],
        "rasgos_observados": llm["rasgos_observados"],
        "explicacion": llm["explicacion"],
        "consejo_foto": llm["consejo_foto"],
    }, "llm"


def procesar(imagen_bytes: bytes, tipo: str, lat: float, lon: float) -> dict:
    """Clasifica, busca duplicados y guarda el aviso.

    Devuelve el aviso guardado (campos de §4) más estos campos, que no se guardan en la tabla:
    - `rasgos_observados`: list[str] (puede ir vacía)
    - `consejo_foto`: str, vacío salvo si es `no_concluyente`
    - `duplicado_distancia_m`: float | None
    - `duplicado_fecha`: str ISO | None, `created_at` del aviso original
    `tipo` es "insecto", "nido" o "no_se".
    """
    tipo_entrada = tipo if tipo in ("insecto", "nido") else "no_se"
    clasificacion, fuente = _clasificar(imagen_bytes, tipo_entrada)

    db.init_db(DB_PATH)
    original = buscar_duplicado(
        lat, lon, clasificacion["tipo"], clasificacion["especie"], db.listar_avisos(DB_PATH)
    )

    aviso = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "lat": float(lat),
        "lon": float(lon),
        "tipo": clasificacion["tipo"],
        "especie": clasificacion["especie"],
        "confianza": float(clasificacion["confianza"]),
        "fuente_clasificacion": fuente,
        "explicacion": clasificacion["explicacion"],
        "foto_path": "",
        "duplicado_de": original[0]["id"] if original else None,
        "estado": "duplicado" if original else "nuevo",
    }
    aviso["id"] = db.insertar_aviso(aviso, DB_PATH)

    aviso["rasgos_observados"] = list(clasificacion["rasgos_observados"])
    aviso["consejo_foto"] = clasificacion["consejo_foto"]
    aviso["duplicado_distancia_m"] = round(original[1], 1) if original else None
    aviso["duplicado_fecha"] = original[0]["created_at"] if original else None
    return aviso
