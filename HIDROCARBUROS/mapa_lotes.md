# Mapa de lotes de PERUPETRO · Contexto técnico

Notebook: `HIDROCARBUROS/PP_Mapa_Lotes.ipynb`
Abrir en Colab: https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Mapa_Lotes.ipynb
Última actualización: **11/10/2026**.

## Para qué sirve

Da a cada lote su **departamento real** y sus **variables geográficas**, para cruzarlas con la producción por lote (`PP_Produccion_Lotes.ipynb`). Reemplaza la regla provisional "Selva Norte = Loreto".

## Fuentes

| Tema | Fuente | Cómo se obtiene |
|---|---|---|
| Polígonos de lotes, cuencas y lo que traiga el visor | Visor de PERUPETRO en ArcGIS Online: https://perupetro.maps.arcgis.com/apps/webappviewer/index.html?id=cc883917c55a4264a01debfa02585e2e | API REST pública de ArcGIS: aplicación → mapa web → capas → `query` |
| Departamentos | geoBoundaries PER ADM1 (basado en límites INEI) | API de geoBoundaries |
| Ríos grandes (distancia) | HydroRIVERS v1.0 Sudamérica (caudal medio `DIS_AV_CMS`, umbral elegible, 300 m³/s por defecto) | Descarga del shapefile (~centenas de MB, solo la primera vez por sesión) |
| Nombre del río cercano | Natural Earth 10m | Descarga directa |
| Oleoducto Norperuano | Capa del visor de PERUPETRO si existe; si no, un servicio público hallado en ArcGIS Online; si no, OpenStreetMap (Overpass, `man_made=pipeline` + `substance=oil`) | Selector del Bloque 2 |
| Áreas Naturales Protegidas | Servicio de SERNANP u otro hallado en ArcGIS Online; respaldo OpenStreetMap (`boundary=protected_area`) | Selector del Bloque 2 |
| Comunidades nativas | Servicio público hallado en ArcGIS Online (BDPI del Ministerio de Cultura u otro) | Selector del Bloque 2; si no hay ninguno, se omite |

Las capas de ArcGIS se consultan con su API pública, sin iniciar sesión. Si una capa pide credenciales, el notebook la marca "requiere inicio de sesión" y sigue con las demás.

## Aviso: el visor de PERUPETRO tiene una capa rota (11/10/2026)

Al abrir el visor en el navegador aparece el mensaje *"La capa, MapaBase_Set2019, , no se puede agregar al mapa"* y el mapa queda sin lotes. Esa capa es la de los polígonos de lotes, así que el servicio detrás está caído o ya no es público.

Qué hace el notebook en ese caso:
- el Bloque 2 lista las capas que no responden y el error del servidor;
- también busca polígonos de lotes en otros servicios públicos de ArcGIS Online ("lotes hidrocarburos Peru", "lotes de contrato PERUPETRO");
- si el visor no da lotes, propone la mejor candidata, con preferencia por servicios de PERUPETRO, MINEM, OSINERGMIN o INGEMMET;
- también se puede pegar una URL conocida en `URLS_EXTRA`.

Otras vías si nada sirve:
- el enlace "Banco de Datos" del mismo visor (cuenta del usuario);
- el shapefile de lotes que PERUPETRO entrega a pedido, por ejemplo a promocion@perupetro.com.pe, el contacto que figura en el visor.

**Primera corrida real (11/10/2026):**
- El visor apunta al mapa web «MAPA BASE 2024», cuya capa `MapaBase_Set2019` está en `gismaptemp.perupetro.com.pe` y da error de conexión.
- La búsqueda en ArcGIS Online devolvió 1.023 capas porque se tomaban todas las capas de cada servicio hallado. Además, los selectores no se dibujaron.

Correcciones:
- **Certificado HTTPS:** si un servidor no envía su certificado intermedio, el notebook lo completa solo, igual que en el notebook de producción.
- **Mensajes de error claros:** p. ej. "el servidor X no responde (caído o bloqueado)".
- **Servidor de PERUPETRO:** si la capa del visor falla, se listan los demás servicios del mismo servidor y se prueban los de lotes o hidrocarburos.
- **Candidatas filtradas por tema:** solo pasan las capas cuyo nombre corresponde al tema.
- **Selección visible:** se activa el gestor de selectores de Colab y la propuesta se imprime también en texto.
- **Elección manual:** al inicio del Bloque 3 se pueden escribir los números N (`N_LOTES`, `N_OLEODUCTO`, etc.) sin depender de los selectores.

**Resultados de la primera corrida completa (11/10/2026)**

Fuentes elegidas:
- lotes: `Lote_Petroleros_Enero_2019_PERUPETRO` (INGEMMET), 75 entidades y 49 lotes;
- oleoducto: Oleoducto Norperuano (WWF Perú);
- ANP: capa pública de 97 áreas;
- comunidades nativas: "Comunidades Nativas/Reservas Territoriales" (Loreto Verde), 668 polígonos. **Solo cubre Loreto.**

Resultados:
- Lotes por departamento: Piura 22, Loreto 9, Cusco 4, Tumbes 3, La Libertad 3, Ucayali 2, Huánuco 2, y Amazonas, Junín, Pasco y San Martín con 1 cada uno.
- Loreto: 1-AB/192, 8, 95, 67, 31-B, 31-E, 39, 64 y 192. **31-B (Maquía) y 31-E quedan en Loreto**, no en "Selva Central" como suponía la tabla de zonas del notebook de producción.

Problemas y correcciones:
- **HydroRIVERS no se leyó** ("not recognized as being in a supported file format"): el .shp está dentro de una carpeta del ZIP. Ahora se busca el .shp dentro del ZIP; si la descarga no es un ZIP, se borra y se avisa.
- **`RIO_CERCANO` venía de Natural Earth**, que es demasiado gruesa: para el 192 daba "Santiago". Ahora usa ríos con nombre de OpenStreetMap, solo los que coinciden con un tramo grande de HydroRIVERS.
- **Sensibilidad:** la distancia al río se calcula con umbrales de 100, 300 y 1.000 m³/s.
- **Mapa de fondo:** los mosaicos de OpenStreetMap respondían "403 Access blocked" dentro de Colab. Ahora el fondo es de Esri, topográfico y satelital.
- **14 lotes con producción sin polígono:** 102, 31-B/D, I(T), I(TT), III(T), IV(T), LOB/EA/LO, VI(T), VII/VI, XIII, XIV, Z-2B, Z-69 y Z-69(T). Ahora se ubican solos los temporales (quitando (T)/(TT)), los compuestos (VII/VI → VII+VI) y los alias (31-B/D → 31-B+31-D, Z-69 ↔ Z-2B, 1-AB → 192). Se imprimen los lotes del mapa sin producción para encontrar el resto de nombres.

**Revisión del mapa (`PP_mapa_lotes.html`, 48 lotes dibujados):**
- El mapa divide algunos lotes en sectores: Z-2B → Z-2B A/B/C/D y XIII → XIII-A/B/C. Ahora se unen solos al lote de producción.
- Z-1, Z-6 y los sectores de Z-2B tocan una franja de costa (1–11 % en tierra) y salían como ZOCALO = NO. Ahora es SI cuando menos del 50 % del lote está en tierra.
- La capa de INGEMMET no trae operador ni cuenca, así que `OPERADOR_MAPA` y `CUENCA` quedan vacíos.
- **El notebook de producción ahora toma `DEPARTAMENTO` de `PP_LOTES_GEO.csv`.** Agrega la columna `DEPARTAMENTO_FUENTE` (MAPA o ZONA). Con esto, 31-B, 31-E, 39 y 64 pasan a Loreto.

## Bloques

1. **Instalación, Drive y funciones.**
   - Lector REST de ArcGIS con reintentos.
   - Descarga paginada: por `resultOffset` si el servidor lo admite; si no, por bloques de `objectIds`.
   - Conversión de geometría Esri a shapely, incluidos huecos y colecciones incrustadas en el mapa web.
   - Funciones de indicadores.
2. **Descubrimiento.**
   - Lista todas las capas del visor y busca en ArcGIS Online candidatas para ANP, comunidades nativas y oleoducto.
   - Propone una selección automática por palabras clave, con preferencia por servicios del Estado: SERNANP, Cultura, MINEM, OSINERGMIN.
   - Guarda el catálogo en `CONTROL/CONTROL PP mapa capas.csv`.
3. **Descarga y variables.**
   - Guarda cada capa en `DATA/MAPA/*.geojson`.
   - Arma la tabla de lotes y calcula las variables.
   - Cruza con el último `PP_produccion_lote_mes_*.csv` de DATA.
   - Guarda `DATA/PP_LOTES_GEO.csv` y `CONTROL/CONTROL PP mapa descarga.csv`.
4. **Mapa interactivo.**
   - Mapa folium con lotes coloreados por petróleo acumulado del campo, departamentos, ríos, oleoducto, ANP y comunidades nativas.
   - Guarda `DATA/MAPA/PP_mapa_lotes.html`.

## Columnas de `PP_LOTES_GEO.csv`

**Identificación del lote:**
- `FECHA_EXTRACCION` (dd/mm/aaaa);
- `LOTE`: clave homologada, la misma que en producción (`LOTE 192` → `192`, `Z - 2B` → `Z-2B`);
- `GEOMETRIA_DE`: polígono usado; para `1-AB` es el del `192`;
- `LOTE_MAPA`, `OPERADOR_MAPA`, `ESTADO_MAPA`, `CAPA`.

**Ubicación:**
- `DEPARTAMENTO`: el de mayor área;
- `DEPARTAMENTO_PCT`, `DEPARTAMENTO_DETALLE` (p. ej. "LORETO 67.7%; UCAYALI 32.3%"), `DEPARTAMENTO_N`;
- `ZOCALO`: SI para los lotes en el mar, asignados a la región costera más cercana;
- `CUENCA`, `CUENCA_PCT`;
- `AREA_KM2` (Albers equivalente de Sudamérica);
- `LAT`, `LON`: punto interior del lote.

**Distancias** (en km, UTM 18S; 0 si toca):
- `DIST_OLEODUCTO_KM`;
- `DIST_IQUITOS_KM`;
- `DIST_RIO_GRANDE_KM`, `RIO_CERCANO`.

**Áreas protegidas y comunidades nativas:**
- `ANP_PCT`: % del lote dentro de ANP;
- `ANP_DETALLE`;
- `CCNN_DENTRO_N`, `CCNN_5KM_N`, `CCNN_DENTRO`.

**Producción:**
- `PETROLEO_ACUM_MMBBL`: acumulado 1994–hoy del lote;
- `PETROLEO_ACUM_CAMPO_MMBBL`: suma de los contratos que comparten polígono, p. ej. 1-AB + 192.

## Lotes históricos sin polígono

- El Bloque 3 imprime y guarda en CONTROL los lotes con producción que no tienen polígono en el mapa actual. Son lotes que ya no existen o que se renombraron, como LOB/EA/LO o 31-B/D.
- Se resuelven agregando el equivalente en `LOTES_ALIAS_GEOMETRIA` (Bloque 3). Por ahora solo está `{"1-AB": "192"}`.

## Pruebas

- **Lo que no se pudo probar:** desde el entorno de Claude, arcgis.com y perupetro.com.pe están bloqueados (403 del proxy). La primera corrida real se hace en Colab.
- **Pruebas simuladas** con un servidor ArcGIS falso, un Drive falso y geometrías sintéticas. Todo resultó correcto:
  - descubrimiento app → mapa web → grupos → MapServer → subcapas, más colecciones incrustadas;
  - 2.500 entidades descargadas con paginación por offset y por IDs;
  - polígono con hueco;
  - reparto 75/25 entre departamentos;
  - lote en el mar asignado como ZÓCALO;
  - distancias, ANP y comunidades;
  - alias 1-AB → 192;
  - cruce con la producción y detección de lotes sin polígono;
  - mapa HTML.
- **Respaldo de OpenStreetMap:** probada la conversión de vías y relaciones a líneas y polígonos.

## Pendiente

1. Primera corrida real: revisar en el Bloque 2 qué capas trae el visor (nombres, campos) y ajustar la detección de campos si hiciera falta.
2. Completar `LOTES_ALIAS_GEOMETRIA` con los lotes históricos.
3. Llevar `DEPARTAMENTO` de `PP_LOTES_GEO.csv` al notebook de producción.
