"""Evalúa YOLO y el LLM sobre el split test por secuencia (spec §6 y §7.1).

Uso habitual (con los datasets ya descargados en local):

    python scripts/evaluar_modelo.py

Hace, en este orden:
  1. Reconstruye el split por secuencia desde el dataset de Roboflow.
  2. Busca fotos repetidas test <-> train+valid (hash exacto, nombre original y
     hash perceptual de 64 bits).
  3. Ejecuta `model.val(split="test")` y copia la matriz de confusión.
  4. Evalúa `llm.analizar_imagen` y el flujo real `pipeline._clasificar`.
  5. Actualiza `metrics/results.json` sin borrar lo que ya había.

Los datasets, la caché del LLM y `runs/` van a `datasets/`/`runs/`, que están
en `.gitignore`. Ninguna clave se escribe en este archivo: se leen de variables
de entorno o de `.streamlit/secrets.toml`.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
# Permite `python scripts/evaluar_modelo.py` desde cualquier directorio.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Mismos valores que el contrato de AGENTS.md.
CLASES_REALES = ("crabro", "velutina")
CLASES_PREDICHAS = ("velutina", "crabro", "otra", "no_concluyente")
NOMBRES_YOLO = {0: "crabro", 1: "velutina"}

# Umbral de duplicado perceptual (dHash/pHash de 64 bits) que pide la Issue.
UMBRAL_HAMMING = 5

# Roboflow: proyecto y versión de cada dataset (la clave va en el entorno).
RF_WORKSPACE = "hornet-behavior"
RF_ORIGINAL = {"project": "-original-vespa-crabro-and-vespa-velutina", "version": 2}
RF_NEW = {"project": "-new-original-crabro-and-velutina", "version": 1}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Utilidades de ficheros y secretos
# ---------------------------------------------------------------------------


def _leer_secretos() -> dict:
    """Lee `.streamlit/secrets.toml` si existe; nunca imprime valores."""
    ruta = RAIZ / ".streamlit" / "secrets.toml"
    if not ruta.is_file():
        return {}
    try:
        import tomllib

        with ruta.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _clave_roboflow() -> str:
    for nombre in ("ROBOFLOW_API_KEY", "ROBOFLOW_KEY"):
        valor = (os.environ.get(nombre) or "").strip()
        if valor:
            return valor
    secretos = _leer_secretos()
    for nombre in ("ROBOFLOW_API_KEY", "ROBOFLOW_KEY"):
        valor = str(secretos.get(nombre) or "").strip()
        if valor:
            return valor
    return ""


def _preparar_clave_llm() -> None:
    """Deja `OPENCODE_API_KEY` en el entorno, sin escribirla en ningún sitio."""
    if (os.environ.get("OPENCODE_API_KEY") or "").strip():
        return
    if (os.environ.get("OPENROUTER_API_KEY") or "").strip():
        os.environ["OPENCODE_API_KEY"] = os.environ["OPENROUTER_API_KEY"].strip()
        return
    secretos = _leer_secretos()
    for nombre in ("OPENCODE_API_KEY", "LLM_API_KEY", "OPENROUTER_API_KEY"):
        valor = str(secretos.get(nombre) or "").strip()
        if valor:
            os.environ["OPENCODE_API_KEY"] = valor
            return
    raise SystemExit(
        "Falta OPENCODE_API_KEY (o LLM_API_KEY/OPENROUTER_API_KEY) en el "
        "entorno o en .streamlit/secrets.toml."
    )


def _sha256_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def _commit_main() -> str:
    """Commit de `main` sobre el que se ha medido (merge-base con origin/main)."""
    try:
        salida = subprocess.check_output(
            ["git", "merge-base", "HEAD", "origin/main"],
            cwd=RAIZ,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return salida.strip() or "desconocido"
    except Exception:
        return "desconocido"


# ---------------------------------------------------------------------------
# Descarga de Roboflow (sin el paquete `roboflow`, solo stdlib)
# ---------------------------------------------------------------------------


def descargar_roboflow(
    proyecto: str, version: int, destino: Path, formato: str = "yolov11"
) -> Path:
    """Descarga un export YOLO de Roboflow y lo deja en `destino`."""
    clave = _clave_roboflow()
    if not clave:
        raise SystemExit(
            "Falta ROBOFLOW_API_KEY en el entorno o en .streamlit/secrets.toml. "
            "No se escribe ninguna clave en el código."
        )
    consulta = urllib.parse.urlencode({"api_key": clave, "nocache": "true"})
    url = (
        f"https://api.roboflow.com/{RF_WORKSPACE}/{proyecto}/{version}/"
        f"{formato}?{consulta}"
    )
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # No incluir la URL: lleva la clave.
        raise SystemExit(
            f"Roboflow devolvió HTTP {exc.code} al pedir {proyecto} v{version}."
        ) from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"No se pudo conectar con Roboflow: {exc.reason}") from None

    enlace = datos.get("url")
    if not enlace:
        raise SystemExit(
            f"Roboflow no devolvió enlace de descarga para {proyecto} v{version}."
        )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(enlace, headers={"User-Agent": USER_AGENT}),
            timeout=300,
        ) as respuesta:
            contenido = respuesta.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Falló la descarga del ZIP de Roboflow (HTTP {exc.code}).") from None

    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            for nombre in z.namelist():
                ruta = (Path(tmp) / nombre).resolve()
                if not ruta.is_relative_to(Path(tmp).resolve()):
                    raise SystemExit("El ZIP de Roboflow contiene rutas inseguras.")
            z.extractall(tmp)
        yamls = list(Path(tmp).rglob("data.yaml"))
        raiz_zip = yamls[0].parent if yamls else Path(tmp)
        for elemento in raiz_zip.iterdir():
            shutil.move(str(elemento), str(destino / elemento.name))
    return destino


# ---------------------------------------------------------------------------
# Split por secuencia
# ---------------------------------------------------------------------------


def nombre_original(ruta: Path) -> str:
    """Nombre del archivo original, sin `.rf.<hash>` ni extensión.

    Roboflow renombra a `<original>_jpg.rf.<hash>.jpg`. Se normalizan espacios,
    guiones y guiones bajos para poder comparar entre datasets.
    """
    nombre = ruta.name.split(".rf.")[0]
    nombre = re.sub(r"\.(jpe?g|png)$", "", nombre, flags=re.I)
    if nombre.lower().endswith("_jpg"):
        nombre = nombre[:-4]
    nombre = re.sub(r"[\s_-]+", "-", nombre.strip().lower())
    return nombre.strip("-")


def secuencia_de(ruta: Path) -> str:
    """Secuencia de vídeo: nombre original sin el número de frame."""
    nombre = nombre_original(ruta)
    return re.sub(r"-(?:\d{6}|mov-\d{3,4})$", "", nombre)


def _leer_split_esperado(results_path: Path) -> dict:
    if results_path.is_file():
        with results_path.open(encoding="utf-8") as f:
            datos = json.load(f)
        split = datos.get("split") or {}
        test = (split.get("test") or {}).get("secuencias") or []
        valid = (split.get("valid") or {}).get("secuencias") or []
        return {
            "test": [re.sub(r"[\s_-]+", "-", s.lower()) for s in test],
            "valid": [re.sub(r"[\s_-]+", "-", s.lower()) for s in valid],
            "train_n": (split.get("train") or {}).get("imagenes"),
            "valid_n": (split.get("valid") or {}).get("imagenes"),
            "test_n": (split.get("test") or {}).get("imagenes"),
        }
    return {
        "test": [
            "mah00002",
            "mah06782",
            "vespa-crabro-germany-1",
            "vespa-crabro-pete-roof-3",
        ],
        "valid": [
            "mah06732",
            "mah06395",
            "vespa-crabro-germany-3",
            "vespa-crabro-pete-roof-2",
        ],
        "train_n": 234,
        "valid_n": 59,
        "test_n": 71,
    }


def construir_split(origen: Path, destino: Path, config: dict) -> dict:
    """Copia el dataset a train/valid/test por secuencia y escribe data.yaml."""
    if not origen.is_dir():
        raise SystemExit(f"No existe el dataset de origen: {origen}")
    if origen.resolve() == destino.resolve():
        raise SystemExit("El destino del split no puede ser el dataset de origen.")

    imagenes = sorted(
        p
        for sub in ("train", "valid", "test")
        for p in (origen / sub / "images").glob("*.jpg")
    )
    if not imagenes:
        raise SystemExit(f"No hay imágenes en {origen}/*/images")

    test_seq = set(config["test"])
    valid_seq = set(config["valid"])
    asignadas = {"train": [], "valid": [], "test": []}
    sin_label = []
    for imagen in imagenes:
        secuencia = secuencia_de(imagen)
        if secuencia in test_seq:
            grupo = "test"
        elif secuencia in valid_seq:
            grupo = "valid"
        else:
            grupo = "train"
        label = None
        for sub in ("train", "valid", "test"):
            candidato = origen / sub / "labels" / (imagen.stem + ".txt")
            if candidato.is_file():
                label = candidato
                break
        if label is None:
            sin_label.append(imagen.name)
            continue
        asignadas[grupo].append((imagen, label))
    if sin_label:
        raise SystemExit(f"{len(sin_label)} imágenes sin etiqueta; ejemplo: {sin_label[0]}")

    # Reconstrucción limpia: el split es derivado y vive en datasets/ (ignorado).
    for grupo in ("train", "valid", "test"):
        shutil.rmtree(destino / grupo, ignore_errors=True)
        (destino / grupo / "images").mkdir(parents=True, exist_ok=True)
        (destino / grupo / "labels").mkdir(parents=True, exist_ok=True)
        for imagen, label in asignadas[grupo]:
            shutil.copy2(imagen, destino / grupo / "images" / imagen.name)
            shutil.copy2(label, destino / grupo / "labels" / label.name)

    conteos = {grupo: len(items) for grupo, items in asignadas.items()}
    esperado = {
        "train": config.get("train_n"),
        "valid": config.get("valid_n"),
        "test": config.get("test_n"),
    }
    for grupo in ("train", "valid", "test"):
        if esperado[grupo] is not None and conteos[grupo] != esperado[grupo]:
            raise SystemExit(
                f"El split por secuencia no cuadra: {grupo} tiene "
                f"{conteos[grupo]} imágenes y results.json dice {esperado[grupo]}."
            )

    data_yaml = destino / "data.yaml"
    data_yaml.write_text(
        "path: "
        + destino.resolve().as_posix()
        + "\ntrain: train/images\nval: valid/images\ntest: test/images\n"
        + "nc: 2\nnames: ['Vespa-Crabro', 'Vespa-Velutina']\n",
        encoding="utf-8",
    )
    return {
        "conteos": conteos,
        "data_yaml": data_yaml,
        "imagenes": {grupo: [i for i, _ in items] for grupo, items in asignadas.items()},
    }


# ---------------------------------------------------------------------------
# Duplicados: hash exacto, nombre original y hash perceptual
# ---------------------------------------------------------------------------


def _a_gris(ruta: Path, tam: tuple[int, int]) -> np.ndarray:
    with Image.open(ruta) as imagen:
        return np.asarray(
            imagen.convert("L").resize(tam, Image.Resampling.LANCZOS), dtype=np.float64
        )


def dhash(ruta: Path, lado: int = 8) -> int:
    """dHash de 64 bits (8x8 diferencias horizontales)."""
    gris = _a_gris(ruta, (lado + 1, lado))
    bits = gris[:, 1:] > gris[:, :-1]
    valor = 0
    for i, bit in enumerate(bits.flatten()):
        if bit:
            valor |= 1 << i
    return valor


def phash(ruta: Path, lado: int = 8, factor: int = 4) -> int:
    """pHash de 64 bits (DCT-II 32x32, bloque 8x8 de baja frecuencia)."""
    n = lado * factor
    gris = _a_gris(ruta, (n, n))
    k = np.arange(n)
    # Matriz DCT-II: D[k, x] = alpha_k * cos(pi * (2x + 1) * k / (2n))
    dct = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    dct *= np.sqrt(2.0 / n)
    dct[0, :] = np.sqrt(1.0 / n)
    coeficientes = dct @ gris @ dct.T
    bloque = coeficientes[:lado, :lado].flatten()
    mediana = np.median(bloque[1:])  # sin la componente DC
    valor = 0
    for i, bit in enumerate(bloque > mediana):
        if bit:
            valor |= 1 << i
    return valor


def hamming(a: int, b: int) -> int:
    return int(a ^ b).bit_count()


def comprobar_duplicados(
    test: list[Path], referencia: list[Path], etiqueta_referencia: str
) -> tuple[dict, list[dict]]:
    """Compara test contra referencia con los tres criterios de la Issue."""
    hash_test = {p: _sha256_archivo(p) for p in test}
    hash_ref = {p: _sha256_archivo(p) for p in referencia}

    exactos = []
    por_hash = {}
    for p, h in hash_ref.items():
        por_hash.setdefault(h, []).append(p)
    for p, h in hash_test.items():
        for q in por_hash.get(h, []):
            exactos.append({"test": p.name, "referencia": q.name})

    nombre_ref = {}
    for p in referencia:
        nombre_ref.setdefault(nombre_original(p), []).append(p)
    mismo_nombre = []
    for p in test:
        for q in nombre_ref.get(nombre_original(p), []):
            mismo_nombre.append({"test": p.name, "referencia": q.name})

    dhash_test = {p: dhash(p) for p in test}
    dhash_ref = {p: dhash(p) for p in referencia}
    phash_test = {p: phash(p) for p in test}
    phash_ref = {p: phash(p) for p in referencia}

    pares = []
    for p in test:
        for q in referencia:
            d = hamming(dhash_test[p], dhash_ref[q])
            ph = hamming(phash_test[p], phash_ref[q])
            if d <= UMBRAL_HAMMING or ph <= UMBRAL_HAMMING:
                pares.append(
                    {
                        "test": p.name,
                        "referencia": q.name,
                        "dhash": d,
                        "phash": ph,
                        "misma_secuencia": secuencia_de(p) == secuencia_de(q),
                        "secuencia_test": secuencia_de(p),
                        "secuencia_referencia": secuencia_de(q),
                    }
                )
    pares.sort(key=lambda x: (min(x["dhash"], x["phash"]), x["test"], x["referencia"]))

    resumen = {
        "comparado_con": etiqueta_referencia,
        "imagenes_test": len(test),
        "imagenes_referencia": len(referencia),
        "criterios": {
            "hash_exacto": "SHA-256 del contenido del archivo",
            "nombre_original": "nombre antes de '.rf.' (normalizado)",
            "hash_perceptual": (
                "dHash y pHash de 64 bits; distancia de Hamming <= "
                f"{UMBRAL_HAMMING}"
            ),
        },
        "pares_hash_exacto": len(exactos),
        "pares_mismo_nombre_original": len(mismo_nombre),
        "pares_casi_duplicados": len(pares),
        "pares_casi_duplicados_misma_secuencia": sum(
            1 for x in pares if x["misma_secuencia"]
        ),
        "pares_casi_duplicados_distinta_secuencia": sum(
            1 for x in pares if not x["misma_secuencia"]
        ),
        "ejemplos_pares_casi_duplicados": pares[:20],
    }
    return resumen, pares


# ---------------------------------------------------------------------------
# YOLO: validación y matriz de confusión
# ---------------------------------------------------------------------------


def validar_yolo(
    pesos: Path, data_yaml: Path, runs_dir: Path, metrics_dir: Path, results: dict
) -> dict:
    from ultralytics import YOLO

    modelo = YOLO(str(pesos))
    metrica = modelo.val(
        data=str(data_yaml),
        split="test",
        imgsz=640,
        device="cpu",
        seed=42,
        project=str(runs_dir),
        name="val_split_secuencia",
        exist_ok=True,
        plots=True,
        verbose=False,
    )
    medido = {
        "precision": float(metrica.box.mp),
        "recall": float(metrica.box.mr),
        "mAP50": float(metrica.box.map50),
        "mAP50_95": float(metrica.box.map),
    }
    esperado = results.get("test") or {}
    comparacion = {}
    for clave in ("precision", "recall", "mAP50"):
        if clave in esperado:
            diferencia = abs(float(esperado[clave]) - medido[clave])
            comparacion[clave] = {
                "results_json": float(esperado[clave]),
                "medido": round(medido[clave], 4),
                "diferencia": round(diferencia, 4),
                "coincide_0_01": diferencia <= 0.01,
            }

    save_dir = Path(metrica.save_dir)
    try:
        save_dir_texto = save_dir.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        save_dir_texto = str(save_dir)
    copiadas = []
    for nombre in ("confusion_matrix.png", "confusion_matrix_normalized.png"):
        origen = save_dir / nombre
        if origen.is_file():
            shutil.copy2(origen, metrics_dir / nombre)
            copiadas.append(nombre)

    return {
        "medido": {k: round(v, 4) for k, v in medido.items()},
        "comparacion_con_results_json": comparacion,
        "coincide_0_01": all(x["coincide_0_01"] for x in comparacion.values()),
        "matrices_copiadas": copiadas,
        "save_dir": save_dir_texto,
    }


# ---------------------------------------------------------------------------
# LLM y pipeline
# ---------------------------------------------------------------------------


def _leer_clase_real(label: Path) -> tuple[str | None, int, int]:
    """Clase mayoritaria de las cajas; devuelve (clase, nº cajas, nº clases).

    Si hay empate, gana la clase de la caja de mayor área (y se anota la mezcla
    en `imagenes_con_mezcla_de_clases`).
    """
    conteo = Counter()
    areas: dict[int, float] = {}
    for linea in label.read_text(encoding="utf-8").splitlines():
        partes = linea.split()
        if len(partes) >= 5:
            clase = int(float(partes[0]))
            ancho, alto = float(partes[3]), float(partes[4])
            conteo[clase] += 1
            areas[clase] = max(areas.get(clase, 0.0), ancho * alto)
    if not conteo:
        return None, 0, 0
    maximo = max(conteo.values())
    empatadas = [c for c, n in conteo.items() if n == maximo]
    clase = max(empatadas, key=lambda c: areas.get(c, 0.0)) if len(empatadas) > 1 else empatadas[0]
    return NOMBRES_YOLO.get(clase), sum(conteo.values()), len(conteo)


def _cargar_cache(ruta: Path) -> dict:
    if ruta.is_file():
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _guardar_cache(ruta: Path, cache: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ruta)


_CACHE_LOCK = threading.Lock()
_YOLO_LOCK = threading.Lock()


def evaluar_llm(
    imagenes: list[Path],
    labels: list[Path],
    cache_path: Path,
    modelo_path: Path,
    limite: int | None = None,
    workers: int = 4,
) -> tuple[dict, dict, dict]:
    _preparar_clave_llm()
    from core import llm, pipeline

    modelo = llm.modelo()
    # La caché incluye el código: si cambia el prompt, el modelo o la lógica,
    # las respuestas antiguas no se reutilizan.
    hash_llm = _sha256_archivo(RAIZ / "core" / "llm.py")
    hash_pipeline = _sha256_archivo(RAIZ / "core" / "pipeline.py")
    cache = _cargar_cache(cache_path)
    resultados_llm = {}
    resultados_pipeline = {}
    reales = {}
    fuentes = Counter()
    mezclas = []

    # Ultralytics no es thread-safe: se serializa solo la inferencia YOLO y se
    # deja que las llamadas HTTP al LLM corran en paralelo.
    yolo_original = pipeline.clasificar_yolo

    def yolo_seguro(datos: bytes):
        with _YOLO_LOCK:
            return yolo_original(datos)

    pipeline.clasificar_yolo = yolo_seguro

    pares = list(zip(imagenes, labels))
    if limite:
        pares = pares[:limite]

    def _cache_get(clave: str):
        with _CACHE_LOCK:
            return cache.get(clave)

    def _cache_set(clave: str, valor) -> None:
        with _CACHE_LOCK:
            cache[clave] = valor
            _guardar_cache(cache_path, cache)

    def llamar_llm(datos: bytes) -> dict:
        resultado = llm.analizar_imagen(datos, "insecto")
        for intento in range(2):
            fallo = resultado.get("especie") == "no_concluyente" and resultado.get(
                "explicacion"
            ) == getattr(llm, "EXPLICACION_FALLO", None)
            if not fallo:
                break
            time.sleep(2 * (intento + 1))
            resultado = llm.analizar_imagen(datos, "insecto")
        return resultado

    def procesar(imagen: Path, label: Path) -> dict:
        datos = imagen.read_bytes()
        clave_imagen = _sha256_bytes(datos)
        real, n_cajas, n_clases = _leer_clase_real(label)

        clave_llm = f"{clave_imagen}|llm|{modelo}|{hash_llm}"
        resultado_llm = _cache_get(clave_llm)
        if resultado_llm is None:
            resultado_llm = llamar_llm(datos)
            _cache_set(clave_llm, resultado_llm)

        clave_pipe = (
            f"{clave_imagen}|pipeline|{modelo}|"
            f"{_sha256_archivo(modelo_path)}|{hash_pipeline}"
        )
        resultado_pipe = _cache_get(clave_pipe)
        if resultado_pipe is None:
            try:
                clasificacion, fuente = pipeline._clasificar(datos, "insecto")
                resultado_pipe = {"resultado": clasificacion, "fuente": fuente}
            except Exception as exc:  # no romper la evaluación por una imagen
                resultado_pipe = {
                    "resultado": {
                        "tipo": "insecto",
                        "especie": "no_concluyente",
                        "confianza": 0.0,
                        "rasgos_observados": [],
                        "explicacion": f"Error al clasificar: {exc}",
                        "consejo_foto": "",
                    },
                    "fuente": "error",
                }
            _cache_set(clave_pipe, resultado_pipe)

        return {
            "nombre": imagen.name,
            "real": real,
            "cajas": n_cajas,
            "clases_distintas": n_clases,
            "llm": resultado_llm,
            "pipeline": resultado_pipe,
        }

    try:
        if workers <= 1:
            procesados = (procesar(imagen, label) for imagen, label in pares)
            iterable = ((i, p) for i, p in enumerate(procesados, 1))
            for i, item in iterable:
                _acumular(item, reales, mezclas, resultados_llm, resultados_pipeline, fuentes, i, len(pares))
        else:
            with ThreadPoolExecutor(max_workers=workers) as ejecutor:
                futuros = {
                    ejecutor.submit(procesar, imagen, label): imagen.name
                    for imagen, label in pares
                }
                for i, futuro in enumerate(as_completed(futuros), 1):
                    item = futuro.result()
                    _acumular(item, reales, mezclas, resultados_llm, resultados_pipeline, fuentes, i, len(pares))
    finally:
        pipeline.clasificar_yolo = yolo_original

    fallo = getattr(llm, "EXPLICACION_FALLO", None)

    def _error_api(resultado: dict) -> bool:
        return (
            resultado.get("especie") == "no_concluyente"
            and resultado.get("explicacion") == fallo
        )

    errores_llm = {
        k for k, v in resultados_llm.items() if _error_api(v)
    }
    errores_pipeline = {
        k for k, v in resultados_pipeline.items() if _error_api(v["resultado"])
    }

    llm_metricas = _metricas(
        {k: v.get("especie") for k, v in resultados_llm.items()},
        {k: v["especie"] for k, v in reales.items()},
        modelo,
        errores_api=errores_llm,
        extra={"imagenes_con_mezcla_de_clases": mezclas},
    )
    pipeline_metricas = _metricas(
        {k: v["resultado"].get("especie") for k, v in resultados_pipeline.items()},
        {k: v["especie"] for k, v in reales.items()},
        modelo,
        componentes="YOLO models/best.pt + LLM",
        errores_api=errores_pipeline,
        extra={"fuentes_clasificacion": dict(fuentes)},
    )
    pipeline_metricas["imagenes_con_mezcla_de_clases"] = mezclas
    return llm_metricas, pipeline_metricas, reales


def _acumular(
    item: dict,
    reales: dict,
    mezclas: list,
    resultados_llm: dict,
    resultados_pipeline: dict,
    fuentes: Counter,
    i: int,
    total: int,
) -> None:
    nombre = item["nombre"]
    reales[nombre] = {
        "especie": item["real"],
        "cajas": item["cajas"],
        "clases_distintas": item["clases_distintas"],
    }
    if item["clases_distintas"] > 1:
        mezclas.append(nombre)
    resultados_llm[nombre] = item["llm"]
    resultados_pipeline[nombre] = item["pipeline"]
    fuentes[item["pipeline"].get("fuente", "?")] += 1
    print(
        f"  [{i:02d}/{total}] {nombre}: real={item['real']} "
        f"llm={item['llm'].get('especie')} "
        f"pipeline={item['pipeline']['resultado'].get('especie')} "
        f"({item['pipeline'].get('fuente')})"
    )


def _metricas(
    predicciones: dict[str, str | None],
    reales: dict[str, str | None],
    modelo: str,
    componentes: str = "LLM",
    errores_api: set[str] | None = None,
    extra: dict | None = None,
) -> dict:
    errores_api = set(errores_api or ())
    todas = [k for k in predicciones if k in reales and reales[k] in CLASES_REALES]
    claves = [k for k in todas if k not in errores_api]
    n_total = len(todas)
    n = len(claves)
    aciertos = 0
    por_clase = {c: {"aciertos": 0, "total": 0} for c in CLASES_REALES}
    matriz = {real: Counter() for real in CLASES_REALES}
    no_concluyente = 0
    otra = 0
    concluyentes = 0
    aciertos_concluyentes = 0
    for k in claves:
        real = reales[k]
        pred = predicciones[k] or "no_concluyente"
        if pred not in CLASES_PREDICHAS:
            pred = "no_concluyente"
        matriz[real][pred] += 1
        por_clase[real]["total"] += 1
        if pred == real:
            aciertos += 1
            por_clase[real]["aciertos"] += 1
            aciertos_concluyentes += 1
        if pred == "no_concluyente":
            no_concluyente += 1
        else:
            concluyentes += 1
            if pred == "otra":
                otra += 1

    resultado = {
        "n": n,
        "n_total": n_total,
        "errores_api": len(errores_api),
        "imagenes_error_api": sorted(errores_api),
        "modelo": modelo,
        "componentes": componentes,
        "fecha": date.today().isoformat(),
        "definicion_acierto": (
            "especie predicha igual a la clase mayoritaria real; 'otra' y "
            "'no_concluyente' cuentan como fallo. Las llamadas con error de API "
            "se excluyen del denominador y se cuentan aparte."
        ),
        "acierto_global": round(aciertos / n, 4) if n else 0.0,
        "aciertos": aciertos,
        "acierto_por_clase": {
            c: {
                "aciertos": por_clase[c]["aciertos"],
                "total": por_clase[c]["total"],
                "acierto": round(
                    por_clase[c]["aciertos"] / por_clase[c]["total"], 4
                )
                if por_clase[c]["total"]
                else 0.0,
            }
            for c in CLASES_REALES
        },
        "pct_no_concluyente": round(no_concluyente / n, 4) if n else 0.0,
        "pct_otra": round(otra / n, 4) if n else 0.0,
        "acierto_entre_concluyentes": (
            round(aciertos_concluyentes / concluyentes, 4) if concluyentes else 0.0
        ),
        "matriz_confusion": {
            real: {pred: matriz[real].get(pred, 0) for pred in CLASES_PREDICHAS}
            for real in CLASES_REALES
        },
    }
    if extra:
        resultado.update(extra)
    return resultado


def _dibujar_matrices(llm_metricas: dict, pipeline_metricas: dict, destino: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    paneles = [
        ("LLM (analizar_imagen)", llm_metricas),
        ("Pipeline de la demo (_clasificar)", pipeline_metricas),
    ]
    fig, ejes = plt.subplots(1, 2, figsize=(14, 5.2))
    for eje, (titulo, datos) in zip(ejes, paneles):
        matriz = np.array(
            [
                [datos["matriz_confusion"][real][pred] for pred in CLASES_PREDICHAS]
                for real in CLASES_REALES
            ]
        )
        imagen = eje.imshow(matriz, cmap="Blues", vmin=0)
        eje.set_xticks(range(len(CLASES_PREDICHAS)), CLASES_PREDICHAS, rotation=30, ha="right")
        eje.set_yticks(range(len(CLASES_REALES)), CLASES_REALES)
        eje.set_xlabel("Predicho")
        eje.set_ylabel("Real")
        eje.set_title(
            f"{titulo}\n"
            f"acierto {datos['aciertos']}/{datos['n']} "
            f"({datos['acierto_global'] * 100:.1f} %)"
        )
        maximo = matriz.max() if matriz.size else 1
        for i in range(matriz.shape[0]):
            for j in range(matriz.shape[1]):
                eje.text(
                    j,
                    i,
                    int(matriz[i, j]),
                    ha="center",
                    va="center",
                    color="white" if matriz[i, j] > maximo / 2 else "black",
                    fontweight="bold",
                )
        fig.colorbar(imagen, ax=eje, fraction=0.046, pad=0.04)
    fig.suptitle(
        f"Matriz de confusión sobre las {llm_metricas['n']} imágenes de test "
        "(split por secuencia)",
        fontsize=12,
    )
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# results.json
# ---------------------------------------------------------------------------


def _actualizar_results(
    results_path: Path,
    duplicados: dict,
    yolo: dict,
    llm_metricas: dict,
    pipeline_metricas: dict,
    new_original_info: dict,
    commit_main: str,
) -> dict:
    if results_path.is_file():
        with results_path.open(encoding="utf-8") as f:
            results = json.load(f)
    else:
        results = {}

    fugas = dict(results.get("fugas_de_datos") or {})
    fugas["duplicados_exactos_entre_splits"] = duplicados["pares_hash_exacto"]
    fugas["comprobacion_test_vs_train_valid"] = duplicados
    fugas["new_original"] = new_original_info
    results["fugas_de_datos"] = fugas

    if "aciertos" in llm_metricas:
        llm_metricas["commit_main"] = commit_main
        results["llm_test"] = llm_metricas
    if "aciertos" in pipeline_metricas:
        pipeline_metricas["commit_main"] = commit_main
        results["pipeline_test"] = pipeline_metricas
    if yolo.get("medido"):
        yolo["commit_main"] = commit_main
        results["verificacion_yolo"] = yolo

    results["evaluacion"] = {
        "commit_main": commit_main,
        "modelo_llm": (
            llm_metricas.get("modelo")
            or pipeline_metricas.get("modelo")
            or "no evaluado"
        ),
        "core_llm_sha256": _sha256_archivo(RAIZ / "core" / "llm.py"),
        "core_pipeline_sha256": _sha256_archivo(RAIZ / "core" / "pipeline.py"),
        "cache_llm": "datasets/cache_llm.json (ignorada por git)",
        "nota_cache": (
            "La caché se indexa por hash de imagen, modelo y hash de "
            "core/llm.py; si cambia el prompt, el modelo o la lógica, se "
            "vuelve a llamar a la API."
        ),
        "fecha": date.today().isoformat(),
    }

    aciertos_pipe = pipeline_metricas.get("aciertos")
    n_pipe = pipeline_metricas.get("n")
    aciertos_llm = llm_metricas.get("aciertos")
    n_llm = llm_metricas.get("n")
    if n_pipe and n_llm:
        frase = (
            f"En las {n_pipe} fotos de test, el flujo completo de la demo "
            f"(YOLO + LLM) acierta {aciertos_pipe} "
            f"({aciertos_pipe / n_pipe * 100:.0f} %); el LLM por separado "
            f"acierta {aciertos_llm} de {n_llm} "
            f"({aciertos_llm / n_llm * 100:.0f} %). "
            "Fuente: metrics/results.json."
        )
    else:
        frase = results.get(
            "cifra_pitch",
            "Sin evaluación del LLM; no hay cifra de acierto. Fuente: metrics/results.json.",
        )
    results["cifra_pitch"] = frase
    results["fecha_evaluacion"] = date.today().isoformat()

    results_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = results_path.with_suffix(results_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, results_path)
    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--original",
        type=Path,
        default=RAIZ / "datasets" / "velutina-original",
        help="Dataset [Original] ya descargado (train/valid/test de Roboflow).",
    )
    parser.add_argument(
        "--new-original",
        type=Path,
        default=RAIZ / "datasets" / "velutina-new-original",
        help="Dataset [New original] ya descargado, si existe.",
    )
    parser.add_argument(
        "--split",
        type=Path,
        default=RAIZ / "datasets" / "velutina-split-secuencia",
        help="Carpeta donde se reconstruye el split por secuencia.",
    )
    parser.add_argument("--modelo", type=Path, default=RAIZ / "models" / "best.pt")
    parser.add_argument(
        "--results", type=Path, default=RAIZ / "metrics" / "results.json"
    )
    parser.add_argument("--metrics-dir", type=Path, default=RAIZ / "metrics")
    parser.add_argument(
        "--cache", type=Path, default=RAIZ / "datasets" / "cache_llm.json"
    )
    parser.add_argument(
        "--runs", type=Path, default=RAIZ / "runs", help="Salida de ultralytics."
    )
    parser.add_argument(
        "--descargar",
        action="store_true",
        help="Descarga los dos datasets de Roboflow (requiere ROBOFLOW_API_KEY).",
    )
    parser.add_argument(
        "--saltar-yolo", action="store_true", help="No ejecutar model.val."
    )
    parser.add_argument(
        "--saltar-llm", action="store_true", help="No llamar al LLM."
    )
    parser.add_argument(
        "--limite-llm", type=int, default=None, help="Solo N imágenes (pruebas)."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Llamadas al LLM en paralelo (1 = secuencial).",
    )
    return parser.parse_args()


def main() -> int:
    args = _argumentos()
    args.metrics_dir.mkdir(parents=True, exist_ok=True)

    if args.descargar:
        print("[1/5] Descargando [Original] v2 de Roboflow...")
        descargar_roboflow(RF_ORIGINAL["project"], RF_ORIGINAL["version"], args.original)
        print("[1/5] Descargando [New original] v1 de Roboflow...")
        descargar_roboflow(RF_NEW["project"], RF_NEW["version"], args.new_original)

    print("[1/5] Reconstruyendo split por secuencia...")
    config = _leer_split_esperado(args.results)
    split = construir_split(args.original, args.split, config)
    print(
        "      train={train} valid={valid} test={test} (cuadra con results.json)".format(
            **split["conteos"]
        )
    )

    print("[2/5] Buscando fotos repetidas test <-> train+valid de [Original]...")
    test = split["imagenes"]["test"]
    referencia = split["imagenes"]["train"] + split["imagenes"]["valid"]
    duplicados, _ = comprobar_duplicados(test, referencia, "[Original] train+valid")
    print(
        "      exactos={pares_hash_exacto} mismo_nombre={pares_mismo_nombre_original} "
        "casi_duplicados={pares_casi_duplicados}".format(**duplicados)
    )

    new_original_info = {
        "comprobado": False,
        "metodo": "SHA-256 + nombre original + dHash/pHash de 64 bits",
        "umbral_hamming": UMBRAL_HAMMING,
        "pares": None,
        "motivo": "No se pudo descargar: falta la clave de Roboflow en el entorno.",
        "conclusion": (
            "[New original] NO se ha comprobado contra el test. Por tanto, NO se "
            "puede usar para entrenar sin repetir antes esta comprobación de "
            "duplicados (hash exacto, nombre original y hash perceptual)."
        ),
        "indicio_no_sustitutivo": {
            "fuente": (
                "https://universe.roboflow.com/hornet-behavior/"
                "-new-original-crabro-and-velutina"
            ),
            "observacion": (
                "La vista pública de Roboflow muestra, entre otras, "
                "MAH00002_000004.jpg y MAH06782_000018.jpg, ambas del test por "
                "secuencia. Es un indicio de solapamiento, no la comprobación "
                "completa que sigue pendiente."
            ),
        },
    }
    if args.new_original.is_dir():
        print("[2/5] Comparando test <-> [New original]...")
        nuevas = sorted(
            args.new_original.glob("*/images/*.jpg")
        ) or sorted(args.new_original.rglob("*.jpg"))
        dup_new, _ = comprobar_duplicados(test, nuevas, "[New original] (todo)")
        new_original_info = {
            "comprobado": True,
            "imagenes": len(nuevas),
            "resultado": dup_new,
            "conclusion": (
                "Si hay pares, [New original] contiene imágenes del test y NO se "
                "puede usar para entrenar sin quitarlas antes."
                if (
                    dup_new["pares_hash_exacto"]
                    or dup_new["pares_mismo_nombre_original"]
                    or dup_new["pares_casi_duplicados"]
                )
                else "[New original] no contiene duplicados del test."
            ),
        }
    else:
        print("[2/5] [New original] no está descargado: se deja constancia en results.json.")

    if args.saltar_yolo:
        yolo_info = {"ejecutado": False, "motivo": "--saltar-yolo"}
    else:
        print("[3/5] Validando YOLO en test (CPU)...")
        yolo_info = validar_yolo(
            args.modelo, split["data_yaml"], args.runs, args.metrics_dir, json.loads(
                args.results.read_text(encoding="utf-8")
            ) if args.results.is_file() else {}
        )
        print(
            "      medido: "
            + ", ".join(f"{k}={v}" for k, v in yolo_info["medido"].items())
        )
        if not yolo_info["coincide_0_01"]:
            print(
                "      AVISO: las cifras no coinciden con results.json (±0,01). "
                "No se sobrescriben las claves de 'test'."
            )

    if args.saltar_llm:
        llm_info = {"ejecutado": False, "motivo": "--saltar-llm"}
        pipeline_info = {"ejecutado": False, "motivo": "--saltar-llm"}
    else:
        print("[4/5] Evaluando LLM y pipeline sobre test...")
        labels = [
            next(
                args.split / grupo / "labels" / (p.stem + ".txt")
                for grupo in ("train", "valid", "test")
                if (args.split / grupo / "labels" / (p.stem + ".txt")).is_file()
            )
            for p in test
        ]
        llm_info, pipeline_info, _ = evaluar_llm(
            test, labels, args.cache, args.modelo, args.limite_llm, args.workers
        )
        _dibujar_matrices(
            llm_info, pipeline_info, args.metrics_dir / "confusion_matrix_llm.png"
        )
        print(
            f"      LLM: {llm_info['aciertos']}/{llm_info['n']} "
            f"({llm_info['acierto_global'] * 100:.1f} %)"
        )
        print(
            f"      pipeline: {pipeline_info['aciertos']}/{pipeline_info['n']} "
            f"({pipeline_info['acierto_global'] * 100:.1f} %)"
        )

    print("[5/5] Actualizando results.json...")
    resultados = _actualizar_results(
        args.results,
        duplicados,
        yolo_info,
        llm_info,
        pipeline_info,
        new_original_info,
        _commit_main(),
    )
    print(f"      {resultados['cifra_pitch']}")
    print("Hecho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
