# Fuentes de las imágenes de demo

Solo imágenes cuya licencia permita redistribución (el repo es público).
EPPO (solo uso educativo) y VespApp (CC BY-NC) se usan en local, sin subirlas.

| Archivo | Qué muestra | Fuente (URL) | Licencia y autoría |
|---|---|---|---|
| `velutina_1.jpg` | Nido de velutina con avispas en la entrada | [Roboflow · hornet-behavior, dataset v2](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | CC BY 4.0 · dataset «[Original] Vespa crabro and Vespa Velutina» |
| `velutina_2.jpg` | El mismo nido que `velutina_1`, otro fotograma | [Roboflow · hornet-behavior, dataset v2](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | CC BY 4.0 · dataset «[Original] Vespa crabro and Vespa Velutina» |
| `crabro_1.jpg` | Nido de avispón europeo con un adulto | [Roboflow · hornet-behavior, dataset v2](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | CC BY 4.0 · dataset «[Original] Vespa crabro and Vespa Velutina» |
| `no_concluyente_1.jpg` | Primer plano desenfocado de una entrada de nido | [Roboflow · hornet-behavior, dataset v2](https://universe.roboflow.com/hornet-behavior/-original-vespa-crabro-and-vespa-velutina/dataset/2) | CC BY 4.0 · dataset «[Original] Vespa crabro and Vespa Velutina» |

Las cuatro son fotogramas del split `test` del dataset. La clasificación guardada
en `clasificaciones.csv` (especie y confianza) se obtuvo ejecutando
`models/best.pt` (YOLO11n entrenado por el equipo) sobre cada imagen; no son
etiquetas copiadas del dataset. El dataset completo no se redistribuye: vive en
`datasets/` y está excluido por `.gitignore`.
