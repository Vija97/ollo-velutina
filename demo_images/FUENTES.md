# Fuentes de las imágenes de demo

Solo imágenes cuya licencia permite redistribución (el repo es público): CC0,
dominio público, CC BY o CC BY-SA. EPPO (solo uso educativo) y VespApp
(CC BY-NC) no se suben: se usan en local.

## En el repositorio

| Archivo | Qué muestra | Página de la foto | Autoría | Licencia | Cambios hechos |
|---|---|---|---|---|---|
| `velutina_1.jpg` | Nido secundario de velutina en una rama, con adultos en la entrada (fotograma A de la pareja del duplicado) | [Roboflow · hornet-behavior, dataset v2, split test](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | Dataset «[Original] Vespa crabro and Vespa Velutina» | CC BY 4.0 | Redimensionada a 1280 px; EXIF original eliminado; GPS añadido (42.87820, -8.54480) |
| `velutina_2.jpg` | El mismo nido que `velutina_1`, otro fotograma (fotograma B de la pareja) | [Roboflow · hornet-behavior, dataset v2, split test](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | Dataset «[Original] Vespa crabro and Vespa Velutina» | CC BY 4.0 | Redimensionada a 1280 px; EXIF original eliminado; GPS añadido (42.87835, -8.54470) |
| `velutina_3.jpg` | Avispa velutina adulta de perfil sobre flores (insecto en primer plano) | [Wikimedia Commons · Asian hornet (Vespa velutina)](https://commons.wikimedia.org/wiki/File:Asian_hornet_(Vespa_velutina).jpg) | Charles J. Sharp | CC BY-SA 4.0 | Recorte alrededor del ejemplar y reducción a 850×790; EXIF eliminado |
| `velutina_4.jpg` | Avispa velutina adulta, retrato frontal (cara naranja y patas amarillas) | [Wikimedia Commons · Vespa velutina front.JPG](https://commons.wikimedia.org/wiki/File:Vespa_velutina_front.JPG) | Siga | CC BY-SA 3.0 | Redimensionada a 1600 px; EXIF eliminado |
| `crabro_1.jpg` | Avispón europeo (Vespa crabro) adulto con una presa, sobre una flor | [Wikimedia Commons · Vespa crabro germana with prey Richard Bartz Crop.jpg](https://commons.wikimedia.org/wiki/File:Vespa_crabro_germana_with_prey_Richard_Bartz_Crop.jpg) | Richard Bartz | CC BY-SA 2.5 | Redimensionada a 1600 px; EXIF eliminado |
| `otra_1.jpg` | Avispa común (Vespula vulgaris) sobre moras: no es velutina | [Wikimedia Commons · Vespula vulgaris-pjt5.jpg](https://commons.wikimedia.org/wiki/File:Vespula_vulgaris-pjt5.jpg) | pjt56 | CC BY-SA 3.0 | Redimensionada a 1600 px; EXIF eliminado |
| `no_concluyente_1.jpg` | Primer plano desenfocado de la entrada de un nido | [Roboflow · hornet-behavior, dataset v2, split test](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | Dataset «[Original] Vespa crabro and Vespa Velutina» | CC BY 4.0 | Redimensionada a 1280 px; EXIF eliminado |

Las fotos de Roboflow son fotogramas del split `test` de la versión original del
dataset. El dataset completo no se redistribuye: vive en `datasets/` y está
excluido por `.gitignore`.

### Pareja del duplicado

`velutina_1.jpg` y `velutina_2.jpg` son dos fotogramas del **mismo** nido. Llevan
un GPS escrito con Pillow, en Santiago, a 18,6 m de distancia (por debajo de
`RADIO_DUPLICADO_M = 50 m`):

| Archivo | Latitud | Longitud |
|---|---|---|
| `velutina_1.jpg` | 42.87820 | -8.54480 |
| `velutina_2.jpg` | 42.87835 | -8.54470 |

Si la demo no leyera el EXIF, se pueden introducir a mano en el mapa. El resto
de fotos no tienen ningún metadato EXIF.

## Solo en local (no se redistribuye)

Ninguna por ahora: las siete fotos del set final tienen licencia que permite
redistribución, así que no se ha necesitado ningún material de EPPO o VespApp.
`demo_local/` queda creado y excluido por `.gitignore` para lo que se use solo en
el portátil de la demo (por ejemplo, acercamientos de VespApp o EPPO).

## Nota para la diapositiva de créditos

Imágenes de demonstración: dataset «[Original] Vespa crabro and Vespa Velutina»
(Roboflow, CC BY 4.0); Charles J. Sharp (CC BY-SA 4.0), Siga (CC BY-SA 3.0),
Richard Bartz (CC BY-SA 2.5) y pjt56 (CC BY-SA 3.0), vía Wikimedia Commons. Los
recortes y la eliminación de metadatos son obra del equipo. Las licencias
CC BY-SA exigen mantener la atribución y compartir las adaptaciones bajo la
misma licencia.

`clasificaciones.csv` es un manifiesto heredado de la primera pantalla: desde
#12 la app clasifica en vivo con `core.pipeline` y no lee ese archivo, así que
solo conserva las cuatro filas originales (con `velutina_1`, `velutina_2`,
`crabro_1` y `no_concluyente_1`). Las cifras de la demo salen del pipeline, no
de ese CSV.
