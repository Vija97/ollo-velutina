"""Datos y construcción del mapa de avisos (#9). Sin clasificación ni escritura."""

from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path

import folium

RAIZ = Path(__file__).resolve().parents[1]
SEED = RAIZ / "data" / "seed_avisos.csv"
CENTRO = (42.8782, -8.5448)  # ETSE, Santiago

# Spec §10: velutina rojo, crabro verde, otra gris, no_concluyente naranja.
COLORES = {
    "velutina": "#C94B4B",
    "crabro": "#357A55",
    "otra": "#6B7280",
    "no_concluyente": "#E6A23C",
}
ETIQUETAS = {
    "velutina": "Posible velutina",
    "crabro": "Avispón europeo",
    "otra": "Otra especie",
    "no_concluyente": "No concluyente",
}
ESTADOS = {"nuevo": "Nuevo", "duplicado": "Duplicado", "enviado": "Enviado al 012"}


def color(aviso: dict) -> str:
    return COLORES.get(aviso.get("especie"), COLORES["otra"])


def etiqueta(aviso: dict) -> str:
    return ETIQUETAS.get(aviso.get("especie"), "Otra especie")


def normalizar(fila: dict) -> dict:
    """Convierte los campos numéricos del seed/BD; no falla con filas incompletas."""
    aviso = dict(fila)
    for campo in ("lat", "lon"):
        try:
            aviso[campo] = float(aviso[campo])
        except (KeyError, TypeError, ValueError):
            aviso[campo] = None
    try:
        aviso["confianza"] = float(aviso["confianza"])
    except (KeyError, TypeError, ValueError):
        aviso["confianza"] = 0.0
    for campo in ("id", "duplicado_de"):
        valor = aviso.get(campo)
        try:
            aviso[campo] = int(valor) if valor not in (None, "") else None
        except (TypeError, ValueError):
            aviso[campo] = None
    return aviso


def leer_seed(ruta: Path | str = SEED) -> list[dict]:
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    with ruta.open(newline="", encoding="utf-8-sig") as archivo:
        return [normalizar(fila) for fila in csv.DictReader(archivo)]


def cargar_avisos() -> tuple[list[dict], str]:
    """Devuelve (avisos, origen). Usa la BD si ya está implementada; si no, el seed."""
    try:
        from core.db import listar_avisos

        avisos = listar_avisos()
        if avisos:
            return [normalizar(dict(aviso)) for aviso in avisos], "base de datos"
    except (NotImplementedError, FileNotFoundError, OSError):
        pass
    return leer_seed(), "datos de ejemplo"


def fecha_legible(valor) -> str:
    if not valor:
        return "Fecha desconocida"
    try:
        return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(valor)


def popup_html(aviso: dict) -> str:
    partes = [
        f"<strong>{html.escape(etiqueta(aviso))}</strong>",
        f"<span style='color:#52634F'>{html.escape(str(aviso.get('tipo', '')))}</span>",
        f"Fecha: {html.escape(fecha_legible(aviso.get('created_at')))}",
        f"Confianza: {round(float(aviso.get('confianza') or 0) * 100)} %",
        f"Estado: {html.escape(ESTADOS.get(aviso.get('estado'), str(aviso.get('estado', ''))))}",
    ]
    if aviso.get("duplicado_de"):
        partes.append(
            f"<span style='color:#8A6D1F'>Duplicado del aviso #{html.escape(str(aviso['duplicado_de']))}</span>"
        )
    return "<br>".join(partes)


def construir_mapa(avisos: list[dict], centro: tuple[float, float] = CENTRO) -> folium.Map:
    mapa = folium.Map(
        location=centro, zoom_start=12, control_scale=True, tiles="OpenStreetMap"
    )
    por_id = {aviso.get("id"): aviso for aviso in avisos}
    for aviso in avisos:
        lat, lon = aviso.get("lat"), aviso.get("lon")
        if lat is None or lon is None:
            continue
        original = por_id.get(aviso.get("duplicado_de"))
        if original and original.get("lat") is not None and original.get("lon") is not None:
            folium.PolyLine(
                [(original["lat"], original["lon"]), (lat, lon)],
                color="#8A9A8A",
                weight=1.5,
                dash_array="4",
                opacity=0.7,
                tooltip=f"Duplicado del aviso #{aviso['duplicado_de']}",
            ).add_to(mapa)
        folium.CircleMarker(
            location=(lat, lon),
            radius=5 if aviso.get("duplicado_de") else 8,
            color=color(aviso),
            weight=1 if aviso.get("duplicado_de") else 2,
            fill=True,
            fill_color=color(aviso),
            fill_opacity=0.6 if aviso.get("duplicado_de") else 0.85,
            tooltip=etiqueta(aviso),
            popup=folium.Popup(popup_html(aviso), max_width=300),
        ).add_to(mapa)
    return mapa


def resumen(avisos: list[dict]) -> str:
    total = len(avisos)
    cuentas = {clave: 0 for clave in COLORES}
    for aviso in avisos:
        especie = aviso.get("especie")
        if especie in cuentas:
            cuentas[especie] += 1
    detalle = " · ".join(
        f"{ETIQUETAS[especie]}: {cantidad}" for especie, cantidad in cuentas.items()
    )
    return f"{total} avisos · {detalle}"


def leyenda_html() -> str:
    elementos = "".join(
        "<span style='display:inline-flex;align-items:center;gap:6px;margin-right:18px'>"
        f"<span style='width:12px;height:12px;border-radius:50%;background:{COLORES[clave]};display:inline-block'></span>"
        f"{ETIQUETAS[clave]}</span>"
        for clave in COLORES
    )
    return (
        "<div style='font-size:.85rem;color:#26332D;margin:.4rem 0 1rem'>"
        f"{elementos}"
        "<span style='display:inline-flex;align-items:center;gap:6px'>"
        "<span style='width:8px;height:8px;border-radius:50%;background:#8A9A8A;display:inline-block'></span>"
        "Duplicado (más pequeño, unido al original)</span>"
        "</div>"
    )
