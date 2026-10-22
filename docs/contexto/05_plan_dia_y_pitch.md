# Plan del día y pitch: Ollo Velutina

## Esta noche (miércoles), en este orden
1. **Crear el proyecto en OpenCode** con las instrucciones y los archivos 02, 03 y 05 como conocimiento (el 04 se pega como primer mensaje mañana).
2. **Entrenar el YOLO en Colab** (sección 6 de la especificación). Guardar `best.pt`, `confusion_matrix.png` y las métricas. Si falla, no pasa nada: plan B solo LLM.
3. **Claves**: API de OpenCode y de Roboflow funcionando y probadas con una llamada.
4. **Fotos de demo** en `demo_images/` (ver especificación §9). Para el duplicado, dos fotos del mismo nido con GPS cercano, o asignar coordenadas a mano.
5. **Fase 0 hecha en casa**: repo creado, entorno instalado en los 4 portátiles, `streamlit run` funcionando.
6. Nombre definitivo y logo sencillo.

## Roles
| Persona | Responsabilidad principal | Fases |
|---|---|---|
| A · Backend | Base de datos, geolocalización, duplicados, pipeline | 1, 3, 6 (pipeline) |
| B · IA | YOLO, LLM, prompts, métricas | 4, 5, 7 |
| C · Frontend | Pantalla principal, mapa, estilo | 2, 6 (UI), 8 |
| D · Pitch y QA | Diapositivas, guion, pruebas de la demo, vídeo de respaldo | Prueba cada checkpoint |

Un solo repo en GitHub; cada uno en su archivo para evitar conflictos (la estructura lo permite).

## Mañana (jueves)
| Hora | Qué |
|---|---|
| 11:45 | Llegada y acreditación. Portátiles cargados y regleta. |
| 12:00–14:30 | Formación de vibe coding (aprovechad huecos para fases 1 y 2). |
| 14:30 | Comida (rápida). |
| 15:00–15:45 | Fases 1–3 en paralelo (A), 4–5 (B), 2 (C). |
| 15:45–16:45 | Fase 5–6. **16:45: primer recorrido completo de la demo, aunque sea feo.** |
| 16:45–17:45 | Fase 6–7 y pulido. D graba el vídeo de respaldo a las 17:30. |
| 17:45–18:15 | **Congelar código.** Solo arreglos de errores. Ensayar el pitch 2 veces cronometrado. |
| 18:15–18:45 | Margen y último ensayo. |
| 18:45 | Exposición. |

Regla de oro: si a las 16:45 algo no funciona, se recorta, no se arregla.

## Pitch (3 minutos)
**1. Gancho (20 s)**
"El año pasado se retiraron en Galicia más de 24.500 nidos de velutina. Pero más de 3.100 avisos acabaron en nidos inactivos, de otras especies o duplicados. Cada uno, un operario desplazado para nada."

**2. Solución (20 s)**
"Ollo Velutina filtra antes de avisar: haces una foto, la IA te dice si es velutina, comprueba si ya está avisado y te prepara el aviso para el 012."

**3. Demo en directo (80 s)**
Velutina → resultado con confianza → aparece en el mapa → segunda foto del mismo nido → "duplicado a 20 m" → foto de un avispón europeo → "autóctono, no hace falta avisar".

**4. La IA por dentro (25 s)**
"Modelo YOLO propio entrenado con imágenes etiquetadas de velutina y avispón europeo, con X % de precisión en test, y un modelo multimodal para nidos y casos dudosos. La clasificación siempre muestra su confianza."

**5. Impacto y negocio (25 s)**
"Clientes: concellos, la Xunta y asociaciones de apicultores. Ahorro en desplazamientos inútiles, menos nidos autóctonos retirados por error y un mapa en tiempo real de la invasión. Siguiente paso: integrarlo con el canal del 012."

**6. Cierre (10 s)**
"No sustituimos al 012: hacemos que cada llamada cuente."

## Preguntas probables del jurado
- **"¿Y si se equivoca?"** → Muestra confianza, pide otra foto si es baja, y el operario sigue verificando. Reducimos falsas alarmas, no decidimos solas.
- **"¿Por qué no usar solo ChatGPT/Claude?"** → El modelo propio es más rápido, barato y medible; el LLM entra solo donde aporta (nidos, explicación).
- **"¿Cómo lo financiáis?"** → Licencia a concellos/Xunta (B2G) y a asociaciones apícolas; datos agregados de la invasión.
- **"¿Ya existe algo así?"** → La Xunta tiene 012, chatbot y agente virtual para recoger avisos; en Reino Unido existe VespAI para detección automática. Nadie filtra y deduplica los avisos ciudadanos antes de que lleguen al 012 en Galicia.
- **"¿Privacidad?"** → Solo se guarda la ubicación del nido y la foto, sin datos personales.
