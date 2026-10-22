# Probar la pantalla principal · issue #8

Esta rama implementa únicamente la pantalla principal. No implementa la página
del mapa de avisos (#9), los botones del 012 (#11) ni la conexión al pipeline (#12).
`core/` y sus contratos no se modifican. La salida de demostración contiene los
campos de resultado adicionales de la PR #1, todavía pendiente de fusionar.

## Qué se puede probar

1. Arranca la aplicación desde la raíz del repositorio:

   ```bash
   source .venv/bin/activate
   streamlit run app.py
   ```

   En Windows, activa el entorno con `.venv\Scripts\activate`.
   Si aún no tienes entorno local, sigue la instalación de `README.md`.
   El entorno en la nube ya tiene las dependencias instaladas.
2. Si la ejecutas en tu ordenador, abre en el navegador la dirección que aparece
   en la terminal. Un servidor dentro del entorno de Codex no publica por sí solo
   una web accesible desde tu ordenador.
3. Sube una foto JPG, PNG o WEBP de hasta 10 MB, o selecciona **Usar cámara**.
   Para la cámara debes permitir el acceso en el navegador y usar HTTPS o una
   ejecución local. En la demostración se admite cualquier foto válida:
   **su contenido no se analiza**.
4. Elige **Insecto**, **Nido** o **No lo sé**.
5. Pulsa en el mapa para situar el encuentro. También puedes abrir **Elegir
   coordenadas o usar una ubicación de ejemplo** y elegir la ETSE.
6. Selecciona un **Resultado de ejemplo** y pulsa **Analizar fotografía**.
   Prueba velutina, avispón europeo, otra especie, duplicado y no concluyente.

Los resultados y su confianza son **simulados**, no predicciones. No se llama a
ninguna API de IA, no se guardan fotos ni avisos y no se usa ninguna clave.
Los avisos de seguridad aparecen siempre. Al cambiar la fotografía, el tipo,
el lugar o el escenario, el resultado anterior se retira hasta volver a analizar.
Las fotos se validan y normalizan en memoria, se eliminan sus metadatos y se
reduce su tamaño para visualizarlas. La ubicación se elige manualmente: todavía
no se extrae el GPS de los metadatos.

El mapa necesita acceso a `cdn.jsdelivr.net` y `tile.openstreetmap.org`.
Si no carga, la entrada manual de coordenadas permite continuar. Se han guardado
los dominios necesarios en el borrador de configuración del entorno; ese borrador
no equivale a haber publicado una nueva versión del entorno.

## Pendiente para cerrar #8

En el entorno solo había `.gitkeep` en `data/`, `models/` y `metrics/`, y ninguna
fotografía en `demo_images/`. Faltan las **fotos reales clasificadas de la base de
datos del equipo**. Cuando estén disponibles hay que construir el resultado a
partir de esos registros y probar una foto de cada especie. Los ejemplos actuales
no satisfacen ese criterio; la PR debe usar `Refs #8` y la issue seguir abierta.
No se han descargado fotos ajenas ni añadido datasets al repositorio.

## Comprobaciones

Desde la raíz:

```bash
.venv/bin/python -m pytest -q
```

Las pruebas cubren inicio, validación de imágenes, botón de análisis, todos los
resultados, confianza, rasgos, consejos, seguridad, retirada de resultados antiguos
y la ruta de entrada de cámara mediante una captura simulada.

Además se ha probado en Chromium: subida por el control real del navegador,
clic en el mapa, cinco escenarios, archivo dañado, captura con cámara virtual
y anchura móvil de 390 px sin desbordamiento horizontal. La cámara física de
tu portátil debe probarse antes de presentar la demo. Las comprobaciones visuales
no validan la precisión de IA ni el funcionamiento de módulos todavía pendientes.

## Seguimiento en GitHub

La issue #8 ya está asignada a `IagoVarelaR`. Si la integración no puede editar
el tablero, abre https://github.com/users/Vija97/projects/1, busca la tarjeta #8
y cambia **Status** a **En revisión** cuando exista la PR.

Para revisar la PR, pulsa **Files changed** y lee los cambios. Pide a otra persona
del equipo que haga la revisión y apruebe. Esta PR no cierra #8 automáticamente:
tras fusionar esta primera entrega, la issue sigue pendiente de las fotos reales.
No marques **Hechas** hasta completar y comprobar ese requisito. El siguiente
trabajo, #9, depende de que estén disponibles los avisos de #2.
