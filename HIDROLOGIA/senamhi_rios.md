# Nivel y caudal de los ríos · SENAMHI · Contexto del proyecto

Documento de traspaso para retomar el proyecto sin perder contexto. Última actualización: **09/11/2026**.

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
| DATA | *(pendiente: primera corrida)* |
| CONTROL | *(pendiente: primera corrida)* |

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

**Acceso.** SENAMHI corta la conexión desde servidores en la nube (el entorno de Claude Code); responde desde el navegador. La primera corrida es en **Colab**. Si Colab también es bloqueado, se verá en el primer paso: falla la lista de estaciones.

## 4. Notebook (3 bloques)

1. **Instalación y funciones.** Lectura de cada endpoint y conversión del hidrograma a filas diarias. `-999` se toma como sin dato.
2. **Selectores:**
   - año inicial (2023 por defecto);
   - nivel y/o caudal;
   - Información Mensual;
   - lista opcional de códigos para una prueba rápida, por ejemplo `240001, 240111, 240103`.
3. **Descarga, control y Drive.**
   - Por estación, primero pide la ficha, que da la última `fecha_hora` y el `variable_opcion`. Después pide el «Diario» del año hidrológico actual, que también trae el anterior.
   - Para llegar a 2023 pide `fecha_hora = 31/08` de años anteriores: un año Y trae Y y Y-1, el siguiente pedido Y-2, y así.
   - **Si SENAMHI ignora la fecha pasada** y devuelve otra vez el año actual en las 3 primeras pruebas, deja de intentarlo y avisa. En ese caso el hidrograma solo llega al 01/09 del año hidrológico anterior, y la historia más antigua queda solo en la Información Mensual. **Esto se confirma en la primera corrida.**
   - Si un día aparece como `ACTUAL` (año pedido) y como `ANTERIOR` (visto desde el año siguiente), se queda el `ACTUAL`.
   - **Información Diaria** (punto 9, al final porque es lo más largo):
     - 4 consultas por día desde el año elegido, unas 5.600 desde 2023, es decir ~1,5–2 h la primera vez;
     - guarda en Drive cada 200 consultas;
     - al volver a ejecutar salta las fechas y horas ya `OK` del control, y siempre vuelve a pedir hoy y ayer;
     - en la prueba rápida, con códigos en el Bloque 2, solo pide los 2 primeros días.

## 5. Archivos

**DATA**

| Archivo | Contenido |
|---|---|
| `SENAMHI_rios_diario.csv` | Una fila por estación, variable y día. Columnas: `COD_ESTACION, ESTACION, RIO, VARIABLE, UNIDAD, FECHA (dd/mm/aaaa), AÑO, MES, DIA, AÑO_HIDROLOGICO, VALOR, MINIMO, MAXIMO, PROM_HISTORICO, UMBRAL_ROJO/NARANJA/AMARILLO, SERIE (ACTUAL/ANTERIOR), FECHA_EXTRACCION`. Se acumula: cada corrida reemplaza los días que vuelve a leer |
| `SENAMHI_rios_info_diaria.csv` | Una fila por estación, día y hora con dato (sin `-999`): `COD_ESTACION, ESTACION, CUERPO_AGUA, CUENCA, DEPARTAMENTO, ZONA, REGION_HIDROGRAFICA, COD_ZONAL, FECHA, AÑO, MES, DIA, HORA, UNIDAD, VALOR, ANOMALIA, UNIDAD_ANOMALIA, TENDENCIA, UMBRAL_ROJO, FECHA_EXTRACCION` |
| `SENAMHI_rios_mensual.csv` | Una fila por estación y mes: valor del mes, mes anterior, anomalía, tendencia, umbral rojo, departamento, cuerpo de agua y región hidrográfica |
| `SENAMHI_ESTACIONES.csv` | Las 143 estaciones, con la última fecha y hora, `variable_opcion`, río, departamento cuando lo hay, y coordenadas si el WFS del GeoServer responde |

**CONTROL**

| Archivo | Contenido |
|---|---|
| `CONTROL SENAMHI rios_diario.csv` | Por estación y variable: primera y última fecha, días con dato, días faltantes y saltos raros (20 veces mayores que lo usual). Incluye el cruce con la Información Mensual: diferencia máxima entre el promedio de los días del mes y el valor mensual publicado, cuando la unidad es la misma. Estado: `OK`, `OK desde …`, `SIN DATOS` o `REVISAR` |
| `CONTROL SENAMHI rios_mensual.csv` | Por mes pedido: mes servido, número de estaciones y estado |
| `CONTROL SENAMHI rios_info_diaria.csv` | Por fecha y hora consultada: estaciones, cuántas con dato y estado (`OK` o `SIN RESPUESTA`). Sirve también para reanudar |
| `LOG SENAMHI consultas.csv` | Cada consulta al hidrograma: fecha pedida, inicio de la serie devuelta, filas y estado |
| `SENAMHI_respuesta_vacia.html` | Primera respuesta sin datos, tal cual, para diagnóstico |

## 6. Pendiente

- [ ] Primera corrida en Colab, con prueba rápida de 3 estaciones y luego todas. Confirmar si `fecha_hora` pasada devuelve años anteriores.
- [ ] Confirmar `variable_opcion` en una estación con caudal.
- [ ] Anotar los IDs de DATA y CONTROL (sección 2).
- [ ] Si Colab llega a SENAMHI, ver si GitHub Actions también llega, para la actualización diaria automática en la página, como en HIDROCARBUROS.
