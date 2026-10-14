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
- **Mapa pesado (4,9 MB):** 3,6 MB eran la línea del oleoducto sin simplificar. Ahora todas las capas se simplifican y se redondean a 5 decimales; el mapa queda en ~1 MB.
- La capa de INGEMMET no trae operador ni cuenca, así que `OPERADOR_MAPA` y `CUENCA` quedan vacíos.
- **El notebook de producción ahora toma `DEPARTAMENTO` de `PP_LOTES_GEO.csv`.** Agrega la columna `DEPARTAMENTO_FUENTE` (MAPA o ZONA). Con esto, 31-B, 31-E, 39 y 64 pasan a Loreto.

**Versión 2 del mapa (11/10/2026), a partir de la revisión de la segunda corrida:**
- **Indicadores de producción** por lote y por campo, en el nuevo archivo `DATA/PP_LOTES_INDICADORES.csv`:
  - estado: en producción, paralizado, sucedido por otro lote o sin producción;
  - primera y última producción;
  - producción actual (bpd de los últimos 12 meses);
  - pico (año y bpd);
  - declinación a 5 años;
  - meses sin producción y paralización más larga;
  - historia de operadores.
- **Campo = componente conexa de polígonos compartidos.** Corrige el acumulado de Maple, que era distinto en 31-B, 31-D y 31-B/D. Un contrato que terminó y siguió con otro lote figura como "SUCEDIDO POR": 1-AB → 192, Z-2B → Z-69, LOB/EA/LO → X (nota del anual 1996).
- **Ríos:**
  - se recortan al contorno de Perú; antes se dibujaba el rectángulo de descarga, con ríos de Ecuador, Colombia y Brasil;
  - se dibujan solo los de ≥ 1.000 m³/s, en tres clases: afluente, río troncal y Amazonas/tramo bajo;
  - la distancia se mide desde el punto interior del lote (desde el borde casi todos daban 0) con umbrales de 1.000, 5.000 y 20.000 m³/s; "río grande" = 5.000 m³/s por defecto.
- **Overpass (nombres de ríos):** daba error 406. Ahora la consulta se identifica como pide su política de uso y prueba tres servidores.
- **Mapa:**
  - una capa por estado (verde en producción, naranja paralizado, gris sin producción) y círculos ∝ bpd actual;
  - leyenda;
  - ficha al hacer clic, con etiquetas en español, unidades, operadores y mini gráfico de la producción anual 1994–2026;
  - comunidades nativas agrupadas;
  - nombre al pasar el cursor por ANP, ríos y oleoducto (antes el oleoducto no mostraba nada);
  - topográfico por defecto.
- **Diagnóstico del HTML anterior (10,9 MB):** los ríos pesaban 6 MB (17.640 tramos ≥ 100 m³/s) y el oleoducto 3,6 MB. Las líneas verticales de una captura no están en la geometría de ninguna capa; probablemente eran un artefacto de dibujo. Si reaparecen, revisar con la capa de departamentos apagada.

**Revisión de la tercera corrida (12/10/2026): 9 correcciones**
1. **Operadores:** los nombres se homologan en el notebook de producción (`norm_operador`). Se agrega `OPERADOR_ORIGINAL`.
2. **Pico:** se busca en años completos con producción. Antes, el 102 y el XIV daban "pico 0 bpd".
3. **Declinación a 5 años:** se calcula entre años "normales" (≤ 2 meses sin producción). Se agrega `DECLINACION_PERIODO`. Antes daba +13,8 % en el 8 y +49 % en el Z-1 al comparar con 2020.
4. **Paralizaciones por lote:** los meses en que el campo produjo con otro contrato no cuentan. Antes VI y VII daban 317 y 285 meses por el periodo reportado como VII/VI.
5. **Departamento** de los lotes sin polígono (102, XIV, LOB/EA/LO), tomado de la base de producción.
6. **Formato del CSV:** enteros sin decimales.
7. **Overpass:** se piden solo los ríos principales como relaciones; la consulta anterior de todos los tramos daba 504/500.
8. **Ficha:** muestra la distancia a un afluente (≥ 1.000 m³/s) además de la distancia a un río troncal.
9. **Los círculos de producción actual también abren la ficha** del lote.

La línea negra vertical que se vio en algunas capturas no está en ninguna capa vectorial; al dibujar el HTML real sin mapa de fondo no aparece. Viene del fondo topográfico de Esri.

**Geoportal oficial de PERUPETRO como fuente principal (12/10/2026)**
- `https://geoportal.perupetro.com.pe/geoserver` es un GeoServer con WFS abierto, sin iniciar sesión. Lo encontró el usuario: el visor ArcGIS anterior estaba caído.
- La capa `cartografia_pp:lote_contrato` trae 32 lotes vigentes con estos campos: `lote` (p. ej. LOTE_Z62; en el mapa algunos en romanos, XCV = 95), `cia_oper`, `contrato` (EXPLORACIÓN/EXPLOTACIÓN), `tipo_contr`, `f_suscripc`, `decreto_su`, `ubicacion` y `Area_Ha`.
- El Bloque 2 lista todas las capas del WFS y describe las útiles: lotes, cuencas sedimentarias, ANP, comunidades, ductos, yacimientos, áreas promocionales, convenios y arcos. La propuesta automática las prefiere a las de terceros.
- **Lotes:**
  - primero los del geoportal (vigentes);
  - después la capa INGEMMET 2019 para lotes antiguos sin contrato vigente (1-AB, 31-B/D, etc.);
  - si un lote está en ambas, manda el del geoportal (`FUENTE_POLIGONO`).
- **Nombres de lote:** `lote_clave` acepta guion bajo y convierte los romanos de la selva (≥ 30 y VIII) a arábigos. Los del noroeste (I a XXIX) siguen en romanos, como en la producción.
- **Nuevas columnas:** `TIPO_CONTRATO`, `F_SUSCRIPCION`, `FUENTE_POLIGONO`; la ficha muestra operador, fase, tipo y fecha del contrato vigente.
- La descarga "Interoperabilidad" (ZIP/RAR) del geoportal da "archivo no disponible": es un enlace roto de PERUPETRO. El WFS la reemplaza.

**Primera corrida con el geoportal (12/10/2026):** el WFS publica 165 capas.

Problemas encontrados:
- El Bloque 2 tardó unos 11 minutos.
- La propuesta incluía "Cuencas Sedimentarias" y "lote_contrato_pash" como si fueran lotes.
- Para comunidades eligió "Pueblos Indígenas".

Correcciones:
- **Servidores caídos:** 2 intentos y no se vuelve a esperar en la misma sesión (el visor viejo `gismaptemp` hacía perder minutos).
- **Una sola petición DescribeFeatureType** para todas las capas útiles, en vez de 31.
- **Capas útiles con lista explícita:** se excluyen las auxiliares (`_inicio`, `_fin`, `_nw`, `_pash`, acueducto, gasoducto, poliducto).
- **ArcGIS Online solo se consulta para lo que el geoportal no trae** (hoy, el complemento de lotes antiguos).
- **Lotes:** solo `lote_contrato` y después `lotes_contrato` del geoportal, más INGEMMET 2019 para los antiguos.
- **Comunidades:** se prefiere "Comunidades Amazónicas" a "Pueblos Indígenas".
- El mensaje "Runtime no longer has a reference to this dataframe" es de la tabla interactiva de Colab al recargar; no afecta.

**Segunda corrida con el geoportal (12/10/2026)**
- Polígonos por fuente: 32 lotes del geoportal y 18 de INGEMMET 2019.

Problemas encontrados:
- La leyenda tapaba el mapa.
- Los operadores seguían sin homologar: el CSV de producción de Drive era anterior a la corrección.
- Los sectores de INGEMMET (XIII-A/B/C, Z-2B A..D) se dibujaban encima de XIII y Z-69 del geoportal.

Correcciones:
- Leyenda plegable en la esquina inferior derecha.
- El notebook del mapa también aplica `norm_operador` al leer la producción.
- Un polígono de una fuente secundaria cubierto en más del 50 % por la fuente principal se descarta, salvo que tenga producción propia.

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

## Correcciones del 12/10/2026 (revisión del mapa final)

- `F_SUSCRIPCION` llegaba del WFS como epoch en milisegundos (`1092009600000.0` en el lote 103). Ahora `fecha_dmy()` la convierte a dd/mm/aaaa; también acepta fechas ISO y dd/mm/aaaa.
- `OPERADORES` ya no muestra `NAN`. Los meses sin operador en el PDF (III(T), IV(T) e IV entre 2014 y 2016) se excluyen de la secuencia.
- `PETROMONT` es el nombre corto de Petrolera Monterrico desde 2010. Se homologa a `PETROLERA MONTERRICO` en los lotes II, XV y XX.
- `DPB` en los lotes 56 y 88 (2021) era el rótulo del eje de un gráfico del PDF, no un operador. El parser ignora esos rótulos (`ETIQUETA_GRAFICO`): DPB, BPD, MBBL, MMBBL, LBB, MM y "Página…".

## Panel de producción anual y mensual (12/10/2026)

- **Cómo se abre:**
  - en la ficha de un lote, clic en la línea de tiempo roja o en el botón «📊 Ver producción anual y mensual»;
  - o con el botón «📊 Producción anual y mensual» de la esquina inferior izquierda.
- **Selectores:**
  - **Serie:** Perú (total), un departamento, un campo (lotes sucesivos sumados, p. ej. 1-AB/192) o un lote.
  - **Comparar con:** una segunda serie.
  - **Producto:** líquidos totales, petróleo o LGN y condensado.
  - **Vista:** anual o mensual, con años **Desde** y **Hasta**.
  - **Unidad:** barriles o barriles por día. Los bpd usan los días reales de cada mes; el año en curso solo cuenta los meses publicados.
- **Gráfico:**
  - barras por año y líneas por mes;
  - al pasar el cursor se ven el valor y el operador de ese año;
  - **clic en una barra anual** abre los 12 meses de ese año, y «↩ Serie anual» vuelve.
- **Resumen:** total del periodo, promedio diario, máximo y meses sin producción.
- **Tabla y CSV:** botón «Tabla» con los datos, y descarga en CSV (separador `;` y coma decimal).
- **Funcionamiento:** los datos mensuales van dentro del HTML (función `series_panel` del Bloque 4) y el gráfico es SVG propio, sin librerías externas.
- **Al abrir el panel** se cierra la ficha del lote, para que no tape el gráfico. El panel se puede minimizar (–) o cerrar (×).
- **Leyenda:** ahora tiene un botón visible **+ / –** para abrirla y minimizarla. Antes era un `<details>` sin marcador visible.
- **Técnico:** `folium.Element` lee el texto como plantilla Jinja. Por eso el panel va entre `{% raw %}` … `{% endraw %}`; sin eso, el `{#` del CSS rompe el render.

## Gas natural y «producción fiscalizada» en el mapa (12/10/2026)

- **Lectura en el Bloque 3:** lee `PP_produccion_gas_lote_mes_*.csv` si existe; si no, el mapa funciona igual, sin gas.
- **Panel:** el selector **Producto** incluye «Gas natural» (1994–hoy desde el 12/10/2026, con las transcripciones 1994–2000).
  - Unidades: millones de pies cúbicos (MMPC) o MMPC por día (MMPCD). Los totales grandes se muestran en BCF.
- **Ficha:** muestra «Gas natural acumulado del campo» en BCF, solo si el campo tiene gas. Columna nueva `GAS_ACUM_CAMPO_BCF` en `PP_LOTES_GEO.csv`.
- **Textos:** el panel y la ficha dicen «producción fiscalizada». La nota del gráfico explica la fuente y que un mes en 0 puede ser paralización.

## Panel centrado (13/10/2026)

- **Al abrirse:** el panel de producción aparece **centrado en la pantalla**, con el mapa atenuado detrás, para concentrar la atención en el gráfico.
- **Para cerrarlo:** botón **×**, clic fuera del panel o tecla **Esc**.
- **Al minimizarlo (–):** queda como una barra abajo al centro y el mapa vuelve a estar libre. Con **+** se expande de nuevo.

## Vista «Diaria» del panel (13/10/2026)

- **Datos:** el Bloque 3 lee `DATA/PP_produccion_diaria.csv`, generado por la sección 8 del notebook de producción. `series_diarias()` agrega a cada serie del panel (Perú, departamento, campo, lote) su producción por día: `dd.p` petróleo y condensado y `dd.l` LGN, en bbl, y `dd.g` gas, en Mcf.
- **Vista:** el selector **Vista** tiene «Diaria». Navegación:
  - clic en un año → sus meses;
  - clic en un mes con reporte diario → sus días;
  - «↩» vuelve un nivel.
- **Meses recientes:** en la vista mensual, los meses posteriores a la última estadística mensual (hoy, julio a octubre de 2026) se arman **sumando los reportes diarios** y se rotulan «(diario)». Si el mes está incompleto se indica, por ejemplo «días 1–11».
- **Unidades en la vista diaria:** bpd en líquidos y MMPCD en gas; el selector «Unidad» se desactiva. El resumen muestra «Días sin producción».
- **Advertencia en la nota:** en líquidos varios lotes se fiscalizan por entregas (días en 0 y días altos); para comparar conviene usar el promedio.
- **Prueba:** el gas de Perú en setiembre 2026 da 1.643,7 MMPCD de promedio, igual al «PROMEDIOS» del PDF diario.

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

## Elección del CSV de producción (13/10/2026)
- **Problema:** con `PP_produccion_lote_mes_1994-2026.csv` y `…_2026-2026.csv` en DATA (este último de una corrida rápida), el mapa tomaba el último por orden alfabético, el de **2026-2026**. Los indicadores salían solo de 2026 (pico 2026, 1-AB/192 «sin producción»).
- **Corrección:** ahora se elige el archivo que cubre más años, es decir, el de inicio más antiguo y, si empatan, el de fin más reciente. Vale también para el CSV de gas.


## Selector de productos y estado por producto (13/10/2026)
- **Selector de capas:** solo Departamentos, Áreas Naturales Protegidas, Ríos, Comunidades nativas y Oleoducto, más la sección **Productos** con casillas: Petróleo, LGN y condensado, Gas natural. Las capas «Lotes · En producción / Paralizado / Sin producción» y «Producción actual» dejaron de ser capas fijas.
- **Lotes:** van en una sola capa. Su color se calcula en el navegador según los productos marcados:
  - **en producción**, si alguno de los productos marcados produjo en los últimos 12 meses con datos;
  - **paralizado**, si alguno produjo antes;
  - **sin producción**, en otro caso.
  - Así un lote puede estar en producción de gas y paralizado en petróleo.
- **Círculos de producción actual:** representan el promedio diario de los últimos 12 meses de los productos marcados, en **bep/d** (gas: 6 mil pies³ = 1 bep). Un clic abre la ficha del lote.
- **Ficha:** muestra el «Estado por producto» con el promedio de 12 meses (bpd o MMPCD) o la última producción si está paralizado. Se quitó la fila «Producción actual de líquidos», que usaba solo las estadísticas mensuales.
- **Cálculo:** `estados_producto()` usa las series mensuales del panel. Los meses posteriores a la última estadística mensual salen de los reportes diarios.
  - Petróleo = PETROLEO.
  - LGN y condensado = LGN + CONDENSADO.
  - Gas en Mcf.
  - En los reportes diarios, PERUPETRO junta petróleo y condensado; esos días se cuentan como petróleo.
- **Nuevo archivo `DATA/PP_LOTES_ESTADO_PRODUCTO.csv`:** una fila por campo, con estado, última producción y promedio actual de cada producto.
- **Ajuste (13/10/2026), lotes que dejaban de responder:** al apagar y prender una capa del selector (Departamentos, Comunidades…), Leaflet la vuelve a dibujar encima de los lotes. Entonces el clic caía en el departamento: se veía un rectángulo negro sobre Loreto y solo su nombre. Con el HTML real, tras prender y apagar Departamentos, solo 6 de 24 lotes respondían.
  - Ahora, en cada `overlayadd` / `baselayerchange`, los lotes y los círculos vuelven al frente; con eso responden los 24.
  - Se quitó el contorno de foco (`path.leaflet-interactive:focus{outline:none}`).
  - Sin productos marcados, los lotes se ocultan del todo: sin sombra ni clic.

## Mapa con plugins: `PP_Mapa_Lotes_Plus.ipynb` (13/10/2026)

Notebook aparte, a pedido del usuario. Tiene los mismos bloques 1–4 que `PP_Mapa_Lotes.ipynb` y un **Bloque 5** que agrega plugins al mapa `m` y lo guarda como `DATA/MAPA/PP_mapa_lotes_plus.html`. El Bloque 4 sigue guardando el mapa base `PP_mapa_lotes.html`.
Colab: https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Mapa_Lotes_Plus.ipynb

| Plugin | Detalle |
|---|---|
| Fondos CARTO claro y oscuro | Capas base nuevas en el selector. Se cargan desde `basemaps.cartocdn.com` con URL explícita, para evitar el aviso de API key de xyzservices. |
| Nombres de lotes | Capa «Nombres de lotes»: rótulo en un punto interior de cada polígono, visible desde el zoom 7. |
| Comunidades discretas | `icon_create_function` del `MarkerCluster` de comunidades: círculos morados de 18–26 px. |
| Buscador de lotes | Control propio arriba a la izquierda, con lista desplegable. Encuadra el lote (zoom máximo 9) y abre su ficha; si el lote no existe, avisa. |
| Pantalla completa, minimapa, medición | `plugins.Fullscreen`, `plugins.MiniMap` (abajo a la izquierda, plegable; oculto en pantallas de menos de 700 px) y `plugins.MeasureControl` (km y ha). |
| Línea de tiempo animada | Botón «⏱ Evolución histórica de la producción». Colorea cada lote por el bep/d anual de su campo (gas: 6 mil pies³ = 1 bep) según los productos marcados. Usa una escala verde de 5 clases (1–1.000, 1.000–5.000, 5.000–20.000, 20.000–50.000 y ≥ 50.000) y gris para 0. Tiene ▶/⏸ y deslizador por año; ✕ vuelve al estado actual. Con la línea de tiempo abierta se ocultan los círculos de producción actual, y cambiar los productos repinta el año. |

**Detalles técnicos:**
- `productos.html` (compartido con el mapa base) expone `window.ppProductos`, y su `aplicar()` cede el pintado a `window.ppTL` cuando la línea de tiempo está activa. En el mapa base no cambia nada.
- **Control de capas al final:** el Bloque 5 saca el `LayerControl`, y también su script del HTML ya renderizado por el guardado del Bloque 4, y lo vuelve a agregar al final. Si no, el control se construye antes de las capas nuevas y falla (`setZIndex` de undefined).
- **Prueba:** corrida simulada del notebook y Chromium sin conexión con las librerías locales, en escritorio (1366 px) y móvil (390 px). Se verificaron:
  - las capas nuevas y los controles;
  - los nombres desde el zoom 7;
  - el buscador («95» abre la ficha);
  - la línea de tiempo: 1994, ▶ avanza, ✕ restaura los colores y los círculos;
  - la ficha con la línea de tiempo abierta;
  - sin errores de JavaScript.
- **No se pudo verificar desde la nube** que carguen los mosaicos de CARTO: la red de Claude los bloquea.

## Pozos perforados y regalías en la ficha del lote (14/10/2026)

En los dos notebooks del mapa (base y con plugins), el Bloque 4 lee de `DATA/` los archivos `PP_pozos_perforados_lote_anio.csv` y `PP_regalias_lote_anio.csv`, que genera el notebook de producción en su sección 6.1. Si no existen, la ficha queda igual que antes.

- **Agrupación por campo:** como la producción, se usa `CAMPO_DE` (o `LOTE_HISTORICO`). Por ejemplo, 1-AB y 192 suman juntos.
- **Pozos perforados:** total de desarrollo y total de exploratorios + confirmatorios, último año con perforación y barras apiladas por año (desarrollo azul `#1565c0`, exploratorios verde azulado `#00897b`), de 1995 a hoy.
- **Regalías pagadas al Estado:** total y monto del último año, en millones de US$, con barras por año (marrón `#6d4c41`), de 2001 a hoy.
- Al pasar el cursor por cada barra se ve el valor del año.
- **Prueba:** corrida simulada con pozos y regalías falsos para 1-AB, 192, 8, 95 y Z-2B. En la ficha del 192 aparecen los dos bloques, sin errores de JavaScript, en escritorio y en móvil.
