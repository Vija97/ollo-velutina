"""Pruebas rápidas del split y de la detección de duplicados (Issue #13)."""

from pathlib import Path

from PIL import Image, ImageDraw

from scripts.evaluar_modelo import (
    UMBRAL_HAMMING,
    comprobar_duplicados,
    dhash,
    hamming,
    nombre_original,
    phash,
    secuencia_de,
)


def _imagen(ruta: Path, color: tuple[int, int, int], desplazamiento: int = 0) -> Path:
    imagen = Image.new("RGB", (320, 240), color)
    dibujo = ImageDraw.Draw(imagen)
    for y in range(0, 240, 40 + desplazamiento):
        dibujo.rectangle([0, y, 320, y + 20], fill=(250, 230, 190))
    dibujo.ellipse([80, 50, 240, 190], fill=(250, 180, 20))
    imagen.save(ruta, format="JPEG", quality=90)
    return ruta


def test_nombre_y_secuencia_de_roboflow():
    ruta = Path("MAH00002_000004_jpg.rf.6c7c2ccf745a92252963857da3eccf2c.jpg")
    assert nombre_original(ruta) == "mah00002-000004"
    assert secuencia_de(ruta) == "mah00002"

    ruta = Path("Vespa-crabro-Pete-Stable-2_000014_jpg.rf.abc.jpg")
    assert nombre_original(ruta) == "vespa-crabro-pete-stable-2-000014"
    assert secuencia_de(ruta) == "vespa-crabro-pete-stable-2"

    ruta = Path("Vespa crabro Germany 1_000010.jpg")
    assert secuencia_de(ruta) == "vespa-crabro-germany-1"


def test_hash_perceptual_detecta_recodificacion(tmp_path):
    original = _imagen(tmp_path / "original.jpg", (40, 80, 40))
    recodificada = tmp_path / "recodificada.jpg"
    with Image.open(original) as imagen:
        imagen.resize((300, 225)).save(recodificada, format="JPEG", quality=70)

    assert dhash(original) == dhash(original)
    assert hamming(dhash(original), dhash(recodificada)) <= UMBRAL_HAMMING
    assert hamming(phash(original), phash(recodificada)) <= UMBRAL_HAMMING


def test_comprobar_duplicados_tres_criterios(tmp_path):
    test = tmp_path / "test"
    ref = tmp_path / "ref"
    test.mkdir()
    ref.mkdir()

    # Misma imagen, distinto nombre y recodificada: no es hash exacto, sí pHash.
    _imagen(test / "MAH00002_000004_jpg.rf.aaa.jpg", (40, 80, 40))
    with Image.open(test / "MAH00002_000004_jpg.rf.aaa.jpg") as imagen:
        imagen.resize((300, 225)).save(
            ref / "MAH00002_000004.jpg", format="JPEG", quality=70
        )
    # Imagen claramente distinta: no debe aparecer.
    Image.new("RGB", (320, 240), (220, 30, 30)).save(
        ref / "MAH06732_000007_jpg.rf.bbb.jpg", format="JPEG", quality=90
    )

    resumen, pares = comprobar_duplicados(
        sorted(test.glob("*.jpg")), sorted(ref.glob("*.jpg")), "prueba"
    )

    assert resumen["pares_hash_exacto"] == 0
    assert resumen["pares_mismo_nombre_original"] == 1
    assert resumen["pares_casi_duplicados"] >= 1
    assert any(p["referencia"] == "MAH00002_000004.jpg" for p in pares)
