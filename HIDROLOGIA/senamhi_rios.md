# Nivel y caudal de los ríos · SENAMHI · Contexto del proyecto

Documento de traspaso para retomar el proyecto sin perder contexto. Última actualización: **12/11/2026**.

---

## 1. Objetivo

Reunir la serie **diaria** del nivel (m.s.n.m) y el caudal (m³/s) de los ríos del Perú, **al menos desde 2023**. Incluye todas las estaciones de la red de monitoreo hidrológico de SENAMHI, con énfasis en Loreto (Nanay, Napo, Amazonas…).

**Notebook:** `HIDROLOGIA/SENAMHI_Rios.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROLOGIA/SENAMHI_Rios.ipynb

## 2. Carpetas de Google Drive

Si `DRIVE_FOLDER_ID` y `DRIVE_FOLDER_CONTROL_ID` están vacíos (Bloque 3, punto 1), el notebook usa o crea `SENAMHI_HIDROLOGIA/DATA` y `SENAMHI_HIDROLOGIA/CONTROL` en Mi unidad. Al final imprime sus IDs. Cópialos aquí y en el Bloque 3 cuando estén fijos.

| Uso | ID |
|---|---|
| DATA | `10JyiTexl7Ip7FneQNFDXJFNGxaf3epqQ` |
| CONTROL | `1Lg28Y32pca7nDZy5ru5Pzbd-butalEfb` |

## 3. Fuente

La página es https://www.senamhi.gob.pe/?p=monitoreo-hidrologico. El mapa es un `iframe`: `https://www.senamhi.gob.pe/mapas/mapa-monitoreohidro/mapa-monitoreo.php`. Todas las consultas son públicas y no piden usuario.

Los endpoints salen de la HAR del navegador del 09/11/2026:

| Endpoint | Método y campos | Devuelve |
|---|---|---|
| `/mapas/mapa-monitoreohidro/include/ajaxEstaciones.php` | POST multipart `cod_zonal=-1` (todas las direcciones zonales) | JSON con **143 estaciones**: `idEstacion`, `codEstacion`, `nomEstacion`, `subEstacion`, `estado` |
| `/mapas/mapa-monitoreohidro/include/ajaxIdesep.php` | POST multipart `url=<WMS GetFeatureInfo del GeoServer>` | Es un intermediario hacia `idesep.senamhi.gob.pe/geoserver/g_dbphisis/wms`, capa `estaciones_monitoreo`. Por estación devuelve `{"id","fecha_hora","variable","variable_opcion"}`; si el clic no cae sobre una estación, devuelve `null` |
| `/mapas/mapa-monitoreohidro/include/mnt-grafica-new.php` | POST `rbtVariable=NIVEL\|CAUDAL`, `fecha_hora=AAAA-MM-DD hh:mm:ss`, `btnTipo=D\|H`, `variable_opcion`, `id=<codEstacion>` | HTML del hidrograma. Los datos vienen en `var data = {...}` (Highcharts) |
| `/include/ajax-informacion-diaria.php` | POST multipart `fecha=AAAA-MM-DD`, `hora=00:00\|06:00\|12:00\|18:00` | JSON de la pestaña «Información Diaria»: **~72 estaciones** (las principales, casi todas en caudal), con el dato a esa hora, la anomalía respecto a la normal, la tendencia, el umbral rojo, la cuenca y el departamento. Hay datos **desde 2023** (probado con 01/01/2023) |
| `/include/ajax-informacion-mensual.php` | POST multipart `fecha=AAAA-MM` | JSON de la pestaña «Información Mensual»: **57 estaciones**, con valor del mes, mes anterior, anomalía, tendencia y umbral rojo |

**Hidrograma «Diario» (`btnTipo=D`).** Trae un **año hidrológico**, de setiembre a agosto. `fechaHora` es la lista de días, en ms UTC, y cada serie es una lista de pares `[ms, valor]`:
- `datoActual`: año hidrológico de la fecha pedida. Es el valor del día, el promedio de mínimo y máximo.
- `minimo`, `maximo`: del día.
- `datoAnterior`: el año hidrológico anterior, en la misma fecha del año.
- `promHistorico`: promedio histórico del día.
- `rojo`, `naranja`, `amarillo`: umbrales de alerta.
- `var dataCSV` repite lo mismo, por fila.

**Hidrograma «Horario» (`btnTipo=H`).** Trae los últimos ~3 días en `dato`. No se usa, porque se eligió la serie diaria.

**Caudal.** En Santa María de Nanay (240001) y Bellavista (240111), el botón «Caudal» sale deshabilitado (`variable_opcion = "N"`, solo nivel). Falta ver una estación que tenga caudal en el hidrograma, para confirmar qué `variable_opcion` usa.

**Información Mensual.** Si se pide un mes aún no publicado, devuelve el último publicado: con `2026-11` devolvió `OCT-26`. El notebook compara el mes servido (`primDescripcion`, por ejemplo `JAN-23`) con el pedido y descarta el que no coincide. Viene en m³/s en 54 estaciones; las demás, en m o m.s.n.m.

**Información Diaria.** A una hora dada, varias estaciones salen `-999` (sin dato). Por ejemplo, el 01/01/2023 a las 00:00 salen así Requena, Contamana, Tamshiyacu y Borja. Por eso se piden las 4 horas del desplegable. Es la fuente principal de **historia diaria desde 2023** para las estaciones principales. El hidrograma cubre las 143 estaciones, pero quizá solo los 2 últimos años hidrológicos.

**Acceso: SENAMHI no responde a servidores en la nube.** Solo responde al navegador, desde una conexión normal. Comprobado el 10/11/2026 desde tres orígenes distintos:

| Origen | Resultado |
|---|---|
| Colab (Google) | `Max retries exceeded` en la lista de estaciones |
| GitHub Actions (workflow «Hidrología · prueba de conexión a SENAMHI») | las 6 consultas agotaron los 45 s de espera, incluido el GeoServer `idesep` |
| Entorno de Claude Code | conexión cortada (`connection reset`) en `www.senamhi.gob.pe`, `senamhi.gob.pe` e `idesep.senamhi.gob.pe` |

No es un fallo del código: es un bloqueo de red de SENAMHI. Por eso **la descarga la hace el navegador** y Colab solo procesa (sección 4). La actualización automática diaria con GitHub Actions, como en HIDROCARBUROS, **no es posible** mientras dure ese bloqueo.

## 4. Cómo se ejecuta (dos pasos)

**Rutina diaria (desde el 12/11/2026): consola + página.** En la página del departamento, sección **Hidrología → Actualizar**, el botón «Copiar el código» copia una línea para la consola. Cada día: abrir Monitoreo Hidrológico de SENAMHI, F12 → Console, Ctrl+V y Enter (aparece el panel; se revisan las fechas y se pulsa «Iniciar»: no empieza solo; la actualización diaria tarda ~5 minutos), y arrastrar el `SENAMHI_crudo_….json` descargado al recuadro de esa misma pestaña. La página compara con lo que ya tiene y sube solo las piezas nuevas o cambiadas. El favorito «Recolector SENAMHI» (en Preguntas frecuentes) hace lo mismo, pero en el primer uso real (12/11/2026) no funcionó en Chrome sobre la página de SENAMHI; la consola sí. El notebook de Colab (Paso B) queda como opción para tener además la copia en Drive.

No hay que cambiar las fechas del panel: con «Desde 01/01/2023» el recolector solo pide lo nuevo (el año hidrológico en curso de todas las estaciones, los 3 últimos meses de la Información Mensual, y la Información Diaria de hoy, de ayer y de los días que falten).

### Paso A · Recolector en el navegador (`HIDROLOGIA/senamhi_navegador.js`)

1. Abrir https://www.senamhi.gob.pe/?p=monitoreo-hidrologico
2. **F12 → Console**, pegar esta línea y Enter. Si Chrome pide permiso para pegar, escribir `allow pasting`, Enter, y volver a pegar:

   ```js
   fetch('https://raw.githubusercontent.com/adriansivina-droid/scraper-mef/main/HIDROLOGIA/senamhi_navegador.js').then(r=>r.text()).then(eval)
   ```

   Si la consola responde con un error en rojo y no aparece el panel, abrir `HIDROLOGIA/senamhi_navegador.js` en GitHub, copiar todo su contenido (botón «Copy raw file») y pegarlo en la consola.

3. Aparece un panel abajo a la derecha. Elegir las fechas **Desde** y **hasta** y pulsar **Iniciar**. Dejar la pestaña abierta.
4. Al terminar se descarga `SENAMHI_crudo_AAAA-MM-DD.json`.

Detalles:
- **Prueba rápida:** 3 estaciones (240001, 240111, 240103) y 2 días de Información Diaria. Tarda ~1 minuto y descarga `…_prueba.json`.
- **Corrida completa desde 01/01/2023:** unas 6.400 consultas, con 0,3 s de pausa entre una y otra. En la primera corrida real (10/11/2026) el panel estimó unas 4 horas.
- **Actualización:** poner «Desde» unos días atrás. Con una semana son unas 480 consultas (pocos minutos): el hidrograma del año hidrológico actual de todas las estaciones y la Información Diaria de esos días. Se puede desmarcar «Hidrograma diario» para pedir solo la Información Diaria y la Mensual.
- **Dirección zonal:** una sola vez pide la lista de estaciones de cada dirección zonal (01 a 13), para saber cuáles son de la DZ 8 (Loreto).
- **Se puede cortar.** El avance queda en el navegador (IndexedDB). Al volver a cargar el script en el mismo navegador, «Iniciar» sigue donde quedó. Las corridas siguientes solo piden lo nuevo: el año hidrológico actual, los 3 últimos meses y los 2 últimos días.
- «Descargar archivo» baja lo reunido hasta ese momento. «Empezar de cero» borra el avance guardado.
- Hace las mismas consultas que la página y con las mismas reglas que el notebook: el orden de estaciones, el retroceso de 2 en 2 años hidrológicos y el corte si SENAMHI ignora la fecha en las 3 primeras pruebas.
- El archivo es compacto. Del hidrograma guarda las series sin repetir fechas. De la Información Diaria guarda solo las estaciones con dato.
- No envía nada a ningún otro sitio.

**Corrida larga desde 2020 (mensual desde antes).** En el panel: «Desde» 01/01/2020 y, junto a «Información Mensual», «desde» el mes más antiguo (por ejemplo 2000-01). El recolector pide el hidrograma hacia atrás de 2 en 2 años hidrológicos hasta 2019-2020, la Información Diaria de cada día desde 2020 (unas 4 400 consultas más que desde 2023, ~2,5 horas adicionales) y la Mensual desde el mes elegido (12 consultas por año). Si SENAMHI no tiene datos tan antiguos, el recolector lo detecta (la consulta devuelve otro año o el mes servido no coincide) y no guarda nada falso. Conviene probar antes con «Prueba rápida» y «Desde» 01/01/2020 (~1 minuto): muestra si hay hidrograma e Información Diaria de esas fechas. La página toma como inicio de los CSV la fecha «Desde» más antigua con que se recolectó (la actualización diaria no la mueve); el notebook procesa la Mensual desde el primer mes que traiga el archivo.

### Paso B · Notebook de Colab (`HIDROLOGIA/SENAMHI_Rios.ipynb`, 3 bloques)

1. **Instalación y funciones.** Lectura de cada endpoint y conversión del hidrograma a filas diarias. `-999` se toma como sin dato. `usar_crudo()` hace que esas funciones lean del archivo del navegador en vez de consultar a SENAMHI.
2. **Selectores:**
   - origen de los datos: **archivo del navegador** (por defecto) o consulta directa, que solo sirve desde una red a la que SENAMHI responda;
   - subir el archivo desde la PC, o usar el más reciente de la carpeta `SENAMHI_HIDROLOGIA/CRUDO` de Drive;
   - año inicial (2023 por defecto), nivel y/o caudal, Información Mensual, Información Diaria y sus horas;
   - lista opcional de códigos de estación.
3. **Descarga, control y Drive.**
   - En modo archivo pide el `SENAMHI_crudo_….json`, guarda una copia en `CRUDO` y toma como fecha de extracción el día en que se recolectó.
   - Hidrograma: por estación usa la ficha (última `fecha_hora` y `variable_opcion`) y el «Diario» del año hidrológico actual, que también trae el anterior. Para llegar a 2023 usa los pedidos con `fecha_hora = 31/08` de años anteriores: un año Y trae Y y Y-1, el siguiente pedido Y-2, y así.
   - **Si SENAMHI ignora la fecha pasada** y devuelve otra vez el año actual en las 3 primeras pruebas, deja de intentarlo y avisa. En ese caso el hidrograma solo llega al 01/09 del año hidrológico anterior, y la historia más antigua queda en la Información Diaria y la Mensual. **Esto se confirma en la primera corrida real.**
   - Si una estación no tiene datos recientes y la consulta «actual» devuelve su último año hidrológico, se acepta ese año.
   - Si un día aparece como `ACTUAL` (año pedido) y como `ANTERIOR` (visto desde el año siguiente), se queda el `ACTUAL`.
   - **Información Diaria** (punto 9): 4 horas por día desde el año elegido. Salta las fechas y horas ya `OK` del control y siempre vuelve a leer hoy y ayer.

## 5. Archivos

**DATA**

| Archivo | Contenido |
|---|---|
| `SENAMHI_rios_diario.csv` | Una fila por estación, variable y día. Columnas: `COD_ESTACION, ESTACION, RIO, VARIABLE, UNIDAD, FECHA (dd/mm/aaaa), AÑO, MES, DIA, AÑO_HIDROLOGICO, VALOR, MINIMO, MAXIMO, PROM_HISTORICO, UMBRAL_ROJO/NARANJA/AMARILLO, SERIE (ACTUAL/ANTERIOR), FECHA_EXTRACCION`. Se acumula: cada corrida reemplaza los días que vuelve a leer |
| `SENAMHI_rios_info_diaria.csv` | Una fila por estación, día y hora con dato (sin `-999`): `COD_ESTACION, ESTACION, CUERPO_AGUA, CUENCA, DEPARTAMENTO, ZONA, REGION_HIDROGRAFICA, COD_ZONAL, FECHA, AÑO, MES, DIA, HORA, UNIDAD, VALOR, ANOMALIA, UNIDAD_ANOMALIA, TENDENCIA, UMBRAL_ROJO, FECHA_EXTRACCION` |
| `SENAMHI_rios_mensual.csv` | Una fila por estación y mes: valor del mes, mes anterior, anomalía, tendencia, umbral rojo, departamento, cuerpo de agua y región hidrográfica |
| `SENAMHI_ESTACIONES.csv` | Las 143 estaciones, con la dirección zonal (`COD_ZONAL`, `DIRECCION_ZONAL`), la última fecha y hora, `variable_opcion`, río, departamento cuando lo hay, y coordenadas si el WFS del GeoServer responde |

**CONTROL**

| Archivo | Contenido |
|---|---|
| `CONTROL SENAMHI rios_diario.csv` | Por estación y variable: primera y última fecha, días con dato, días faltantes y saltos raros (20 veces mayores que lo usual). Incluye el cruce con la Información Mensual: diferencia máxima entre el promedio de los días del mes y el valor mensual publicado, cuando la unidad es la misma. Estado: `OK`, `OK desde …`, `SIN DATOS` o `REVISAR` |
| `CONTROL SENAMHI rios_mensual.csv` | Por mes pedido: mes servido, número de estaciones y estado |
| `CONTROL SENAMHI rios_info_diaria.csv` | Por fecha y hora consultada: estaciones, cuántas con dato y estado (`OK` o `SIN RESPUESTA`). Sirve también para reanudar |
| `LOG SENAMHI consultas.csv` | Cada consulta al hidrograma: fecha pedida, inicio de la serie devuelta, filas y estado |
| `SENAMHI_respuesta_vacia.html` | Primera respuesta sin datos, tal cual, para diagnóstico |

El detalle de cada columna está en **`HIDROLOGIA/docs/Diccionario_SENAMHI_rios.pdf`**. Se genera con `python HIDROLOGIA/docs/mk_diccionario.py`; si cambian las columnas, se actualiza ese script y se vuelve a generar.

**Departamento de las estaciones.** SENAMHI solo da el departamento en la Información Diaria y la Mensual (~72 estaciones). Para las demás se usa la dirección zonal. En la primera prueba real el GeoServer no entregó la capa de estaciones, así que no hay coordenadas.

## 6. Pendiente

- [x] Prueba rápida real (10/11/2026): funcionó de punta a punta. **SENAMHI sí acepta fechas pasadas** (nivel desde 2023 en las 3 estaciones) y el caudal sale en 2 de las 3. Información Diaria: 64 estaciones con dato a las 06:00, 12:00 y 18:00, y 30 a las 00:00.
- [x] Corrida completa desde 01/01/2023 (12/11/2026): 316 753 filas diarias de 138 estaciones, 327 381 de Información Diaria (74 estaciones) y 2 622 mensuales. Control: nivel 124 OK y 14 a revisar; caudal 88 OK, 19 a revisar y 31 sin datos (estaciones sin caudal). Los «REVISAR (saltos)» son cambios bruscos de un día a otro; los datos se guardan como los publica SENAMHI.
- [x] Llevar los datos a la página (12/11/2026): sección **Hidrología** de cada región (sección 7).
- [x] IDs de DATA y CONTROL anotados (sección 2).
- [ ] Opcional: recolección sin intervención, con un script de Python y el Programador de tareas de Windows en una PC de la oficina (SENAMHI solo bloquea a los servidores en la nube). Hay que probar primero que SENAMHI responde a Python desde esa red.

## 7. En la página (FISCAL/api)

- **Dónde:** índice de cada región → «V. Hidrología» (Anexos pasa a ser VI). Pestañas: **Gráfico** (situación de los ríos de la región y el hidrograma como el de SENAMHI: año hidrológico, año anterior, promedio histórico, mínimo y máximo del día y umbrales), **Descargar datos** (los mismos CSV del notebook, de la región o de todo el país, en CSV o Excel) y **Actualizar**.
- **Qué guarda:** las piezas del archivo del navegador tal cual, comprimidas, en la tabla `senamhi_crudo` (una fila por hidrograma `graf:<estación>:<variable>:<año hidrológico>`, por consulta de Información Diaria `inf:<fecha>:<hora>` y por mes `men:<AAAA-MM>`). La corrida completa ocupa unos 11 MB; guardar las filas ocuparía unas 10 veces más.
- **Cómo arma los CSV:** `app/hidrologia.py` aplica las mismas reglas que el notebook (comprobado: con el mismo archivo salen los mismos CSV, fila por fila). Se arman al primer pedido tras cada actualización y quedan en disco hasta la siguiente.
- **Subida:** la página parte el JSON en el navegador, pide `GET /v1/hidrologia/crudo/indice` (pieza → huella) y manda por lotes a `POST /v1/hidrologia/crudo` solo lo que cambió. Una pieza no se reemplaza por otra recolectada en un día anterior.
- **Departamento de una estación:** el que da SENAMHI en la Información Diaria o Mensual; las estaciones sin departamento se muestran en la región de su dirección zonal (DZ 8 Loreto, DZ 9 San Martín, DZ 10 Ucayali) con un asterisco.
- **Umbrales:** si el rojo es menor que el amarillo son de nivel bajo (vaciante), como en el Nanay o el Amazonas; si es mayor, de crecida.
- **Todo el país:** grupo **Perú** (antes «Las tres regiones») → Hidrología → «Ríos del Perú (SENAMHI)». Mapa de las estaciones (Leaflet + OpenStreetMap), con filtro por dirección zonal y por estación, el color de alerta de SENAMHI, la tabla de todas las estaciones, el hidrograma y las descargas de todo el país.
- **Coordenadas:** vienen de la lista `listaMonitoreo` que la página `mapa-monitoreo.php` de SENAMHI trae dentro (coordenadas, dirección zonal y color de alerta del día). El recolector v4 la guarda como pieza `monitoreo`; mientras no llegue, la página usa la copia del 09/11/2026 en `FISCAL/api/app/senamhi_ubicacion.json`. `SENAMHI_ESTACIONES.csv` trae ahora `LATITUD` y `LONGITUD`.
- **Reporte de situación hídrica · Zona Oriente:** PowerPoint y Excel con el formato del reporte de la Sucursal Piura, armados con los datos del día (`FISCAL/api/app/reporte_hidrico.py`; botón en Perú → Ríos del Perú → Descargar datos). Mar, lluvias y embalses no van: SENAMHI no los entrega en esta fuente y en el Oriente no hay embalses; el reporte se centra en el nivel y el caudal de los ríos.
- Pruebas: `FISCAL/api/tests/test_hidrologia.py`.
