# Contexto del proyecto: Ollo Velutina

## 1. El problema

La avispa velutina (Vespa velutina, "avispa asiática" o "de patas amarillas") es una especie invasora asentada en Galicia. Depreda abejas (daño a la apicultura y la polinización), afecta a frutales y es peligrosa para personas alérgicas.

### Datos oficiales y de prensa (usar en el pitch, con fuente)
- El plan centralizado de retirada de nidos permitió retirar **más de 24.500 nidos en 2025** (Pontevedra >9.100, A Coruña 8.800, Lugo ≈4.200, Ourense 2.400). — El Debate, 25/04/2026.
- Además de los nidos retirados, los operarios se encuentran **nidos inactivos, nidos de otras especies y avisos duplicados**: en 2025 se gestionaron **más de 3.100 avisos de ese tipo**. — El Debate, 25/04/2026.
- La campaña 2026 de retirada de nidos tiene un presupuesto de **1,7 millones de euros**. — El Debate, 25/04/2026.
- Desde 2020 el plan centralizado ha retirado **más de 131.000 nidos**; están adheridos los **313 concellos** gallegos y la gestión la hace la empresa pública **Seaga**. — Xunta, nota de prensa 07/11/2025.
- En 2025 se capturaron **más de 230.000 reinas** con más de 18.500 trampas. — Xunta, nota de prensa 30/09/2025.
- Interesa no retirar por error nidos de avispas autóctonas, que compiten con la velutina. — Consellería do Medio Rural (vía Agronews Castilla y León).

### Canales existentes (nuestra "competencia")
- Teléfono **012** (Atención á Cidadanía), reforzado en verano.
- Un **chatbot** y un **agente virtual** de la Xunta como vías complementarias para comunicar nidos. — Ecoticias, 25/03/2025.

**Nuestro diferencial:** esos canales recogen avisos; nosotros los **filtramos antes**:
1. Clasificación por foto (velutina / avispón europeo / otra especie / no concluyente).
2. Detección de duplicados por geolocalización ("ya hay un aviso a 30 m").
3. Aviso estructurado (especie probable, confianza, coordenadas, foto, descripción) listo para el 012.
4. Mapa de calor para concellos y apicultores.

### Respaldo científico
- Universidad de Salamanca (2024), *Deep Learning for Vespa Velutina Detection*: demuestra la viabilidad de reconocer la velutina con IA.
- VespAI (Reino Unido): sistema que distingue Vespa velutina de Vespa crabro y pide confirmación humana antes de alertar.

## 2. Guía de identificación (para prompts y para la pantalla de resultados)

| Especie | Rasgos clave |
|---|---|
| **Vespa velutina** (invasora) | 2–3 cm. Cuerpo mayoritariamente **negro/marrón oscuro**. Una **banda naranja-amarilla** ancha en el 4.º segmento del abdomen. **Extremos de las patas amarillos** ("patas amarillas"). Cara anaranjada. |
| **Vespa crabro** (avispón europeo, autóctono) | Más grande (hasta 3,5 cm). Tórax **rojizo-marrón**, abdomen **mayoritariamente amarillo** con marcas negras. Patas marrones/rojizas. |
| **Vespula / Polistes** (avispas comunes) | Pequeñas (1–1,5 cm), patrón **amarillo y negro** muy contrastado. |
| **Abeja (Apis mellifera)** | Peluda, marrón-dorada, sin cintura marcada. Es la víctima, no la amenaza. |

### Nidos
- **Velutina, nido primario** (primavera): pequeño, del tamaño de una naranja, en lugares resguardados (aleros, cobertizos).
- **Velutina, nido secundario** (verano–otoño): grande (puede superar el medio metro), con forma de pera o esfera, a menudo en **copas de árboles altos**, con una **pequeña entrada lateral**.
- **Avispón europeo**: suele anidar en **huecos** (troncos, paredes, desvanes); el nido queda abierto por abajo.

## 3. Mensajes de seguridad (obligatorios en la app)
- No te acerques al nido ni intentes retirarlo. Mantén al menos 5 metros de distancia y no hagas ruidos ni vibraciones cerca.
- Avisa al **012** o usa los canales oficiales de la Xunta.
- Si te pica y tienes dificultad para respirar, hinchazón generalizada o mareo, llama al **112**.

## 4. Datasets disponibles

| Dataset | Contenido | Licencia | Uso recomendado |
|---|---|---|---|
| Roboflow Universe · *hornet-behavior* · "[Original] Vespa crabro and Vespa Velutina" | 364 imágenes, detección, clases crabro/velutina | Ver página | **Entrenamiento y test** (usar la versión original para el test) |
| Roboflow · *hornet-behavior* · "[New original] Crabro and Velutina" | 546 imágenes | Ver página | Entrenamiento |
| Roboflow · "HornetDetect" | Detección crabro/velutina | CC BY 4.0 | Ampliar entrenamiento |
| Roboflow · *student-insects* · "Vespa velutina" | ≈1.460 imágenes solo velutina | Ver página | Ampliar clase velutina |
| Roboflow · "U-See" | Abeja y avispa asiática | CC BY 4.0 | Clase abeja |
| VespApp (Universitat de les Illes Balears) | 571 registros de insectos que NO eran velutina, validados por expertos | CC BY-NC 4.0 | Clase "falsa alarma" / test (no comercial) |
| iNaturalist / GBIF | Observaciones con foto de velutina, crabro, Vespula, nidos | Varias CC | Ampliar y fotos de nidos |
| EPPO Global Database | Fotos tomadas en Galicia (incl. Santiago) | Solo uso educativo | Solo demo |

**Cuidados:** no evaluar con versiones "augmented" si se entrenó con la original (fuga de datos). Apenas hay datasets etiquetados de nidos: para nidos se usa el LLM multimodal. Anotar fuente y licencia de cada dataset en una diapositiva.

## 5. Fuentes
- El Debate (25/04/2026): https://www.eldebate.com/espana/galicia/20260425/xunta-destina-17-millones-euros-campana-retirada-nidos-velutina_409825.html
- Xunta (07/11/2025): https://www.xunta.gal/notas-de-prensa/-/nova/018491/plan-centralizado-xunta-acordado-cos-concellos-permitiu-retirada-mais-131-000
- Xunta (30/09/2025): https://www.xunta.gal/es/notas-de-prensa/-/nova/017148/xunta-casi-duplica-numero-reinas-avispa-velutina-capturadas-hasta-superar-las
- Ecoticias (25/03/2025): https://www.ecoticias.com/naturaleza/galicia-campana-avispa-velutina
- Universidad de Salamanca (2024): https://produccioncientifica.usal.es/documentos/67f8f7378ec97269559f64db
- VespAI (MRCVS): https://www.mrcvs.co.uk/en/news-story.php?id=23430
- Roboflow hornet-behavior: https://universe.roboflow.com/hornet-behavior
- Roboflow HornetDetect: https://universe.roboflow.com/hornetdetection/hornetdetect-ardf0
- Roboflow student-insects: https://universe.roboflow.com/student-insects
- Roboflow U-See: https://universe.roboflow.com/rubns-workspace-rtcgh/u-see
- VespApp (UIB): https://portalinvestigacio.uib.cat/documentos/6a4bc6ed56f5d753c437a9e2
- EPPO: https://gd.eppo.int/taxon/VESPVE/photos
