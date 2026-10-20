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
| Pantalla completa y medición | `plugins.Fullscreen` y `plugins.MeasureControl` (km y ha). El minimapa se quitó el 14/10/2026 a pedido del usuario. |
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

## Panel «Pozos, regalías y canon» (14/10/2026)

- **Ficha del lote:**
  - Se agrega un tercer bloque: **canon y sobrecanon del departamento del lote**, en millones de S/ desde 1993. Lee `PP_canon_departamento_anio.csv` y lleva la aclaración de que es del departamento entero, no solo del lote.
  - Los tres bloques (pozos, regalías y canon) y el botón «📊 Ver pozos, regalías y canon» abren un **panel interactivo** centrado (`act_panel.html`). Se cierra con ×, Esc o clic fuera.
- **Panel:**
  - Pestañas: Pozos perforados, Regalías y Canon y sobrecanon. Las que no tienen datos quedan desactivadas.
  - Barras anuales con eje y líneas guía. Pozos van apilados por tipo; regalías, por hidrocarburo (petróleo, LGN, gas natural, condensado).
  - Al pasar el cursor por una barra se ven los valores del año. El área sensible de cada barra es toda la columna del año.
  - Al hacer clic en un año aparece su detalle:
    - pozos y regalías: **por lote del campo** (p. ej. 192 y 1-AB);
    - canon: con la variación respecto del año anterior.
  - Arriba hay un resumen con el total del período, el año máximo y el último año con dato.
- **Datos:** un solo JSON `ACT` en el HTML: `p[campo][lote][d|e][año]`, `r[campo][lote][hidrocarburo][año]` en MM US$, `c[departamento][año]` en MM S/ y `rango` con los años de cada tabla. Los departamentos se comparan sin tildes y en mayúsculas.
- **Prueba:** corrida simulada y Chromium en escritorio (1300 px) y móvil (390 px). Se verificaron:
  - la ficha muestra los 3 bloques;
  - el panel abre con el título del campo y sus lotes;
  - la ayuda al pasar el cursor y el detalle por lote al hacer clic;
  - el cambio de pestañas y el cierre con Esc;
  - sin errores de JavaScript.

## Ficha del lote reordenada (14/10/2026)

Revisión a pedido del usuario: se quita lo que repite información y se aclara lo que puede confundir. La ficha queda en 4 secciones con título: **Producción**, **Contrato**, **Geografía y sociedad** y **Pozos, regalías y canon**.

| Ítem | Regla |
|---|---|
| Estado por producto | Solo los productos que el lote produjo alguna vez (en producción o paralizado). Si no produjo nada: «Sin producción fiscalizada registrada (1994–hoy)». |
| Campo | Solo si suma varios contratos (p. ej. 1-AB/192), con la etiqueta «Campo (contratos sumados)». |
| Fase del contrato | Se oculta si es EXPLOTACIÓN y el lote tiene producción; se muestra en lotes en exploración o sin producción. |
| Departamento | Sin «100 %» cuando el lote está en un solo departamento; con porcentajes cuando cruza límites (define el canon). |
| Tipo de contrato | Se mantiene: licencia frente a servicios cambia la lectura de las regalías. |
| Ríos | Las dos distancias por caudal se reemplazan por una línea: «Río grande más cercano: nombre · km». |
| Ríos e Iquitos | Solo para lotes de la selva (no zócalo ni costa). |
| Pico y acumulado | Si la primera producción es «≤01/1994», las etiquetas dicen «(desde 1994)» / «(1994–hoy)» y una nota avisa que el pico y el acumulado reales pueden ser mayores. |
| Acumulados | No se muestran si son 0. |

- **Se mantienen:** estado y volumen, operador vigente e historial, última producción, paralización más larga, oleoducto, áreas protegidas, comunidades nativas e Iquitos (para la selva).
- **Prueba:** corrida simulada y navegador, con fichas de 192, 8, 95 y Z-1 revisadas; sin errores de JavaScript.

## Vista de tabla y descarga en el panel de pozos, regalías y canon (15/10/2026)

- **Aporte estimado al canon:** se probó una estimación del aporte de cada campo al canon del departamento y se **retiró a pedido del usuario**. PERUPETRO publica el canon solo por departamento, así que se muestra tal cual, con la aclaración «del departamento, no solo de este lote».
- **Tabla:** las tres pestañas tienen el botón «📋 Tabla», que cambia a una tabla completa por año (la más reciente arriba); «📈 Gráfico» vuelve al gráfico. La tabla del canon incluye la variación respecto del año anterior.
- **Descarga:** «⬇ Descargar CSV» baja los datos de la pestaña. Usa separador `;`, coma decimal y BOM, como el panel de producción. Archivos:
  - `pozos_perforados_campo_<c>.csv`: AÑO, CAMPO, LOTE, DESARROLLO, EXPLORATORIOS_Y_CONFIRMATORIOS;
  - `regalias_campo_<c>.csv`: AÑO, CAMPO, LOTE, HIDROCARBURO, REGALIA_MM_US$;
  - `canon_sobrecanon_<DEPARTAMENTO>.csv`: AÑO, DEPARTAMENTO, CANON_SOBRECANON_MM_S/.
- **Prueba:** corrida simulada y Chromium en escritorio y móvil, con la tabla de 33 años y la descarga de los 3 CSV con contenido correcto; sin errores de JavaScript.

## Empresas: ficha y pestaña «Empresas» (18/10/2026)

- **Historial de operadores:** el Bloque 4 arma `DATA/PP_operadores_lote.csv` desde la producción fiscalizada (líquidos y gas, 1994–hoy): DEPARTAMENTO, CAMPO, LOTE, OPERADOR, AÑO_INICIO, AÑO_FIN, AÑOS_CON_PRODUCCION, LIQUIDOS_BBL, GAS_MPC. Un año sin producción corta el periodo.
- **Ficha del lote:** la sección «Contrato» pasa a **«Empresa y contrato»**: operador, empresas del contrato con su % y vigencia (de `PP_contratos.csv`, edición más reciente), y «Operadores con producción». Si hay vigencia, no se repite la fecha de suscripción del visor. Botón «🏢 Ver empresas y operadores».
- **Pestaña «Empresas»** del panel (`act_panel.html`):
  - línea de tiempo con una barra por lote y operador (cursor: años y producción);
  - tabla del contrato vigente (empresa, %, suscripción, término, fase) y de los contratos terminados;
  - «📋 Tabla» y «⬇ Descargar CSV» (`empresas_campo_<campo>.csv`, con TIPO = OPERADOR CON PRODUCCION / SOCIO DEL CONTRATO VIGENTE / CONTRATO TERMINADO).
- **Prueba:** Chromium con contratos reales (ediciones 2021, 2024 y 2025), escritorio y móvil, lotes 95 y 192; sin errores de JavaScript.
- **Regalías por empresa (18/10/2026):** `PP_operadores_lote.csv` suma REGALIAS_US$ por operador y periodo (con la columna OPERADOR de `PP_regalias_lote_anio.csv`). En la pestaña «Empresas» aparecen en el cursor, la tabla y el CSV; las que el PDF no permite atribuir van en una nota («REGALIAS SIN OPERADOR IDENTIFICADO» en el CSV). La pestaña «Regalías» sigue sumando por lote.

## Ficha sin gráficos: un solo botón «📊 Ver estadísticas» (18/10/2026)

- **Ficha del lote:** se quitaron todos los gráficos (línea de producción anual, barras de pozos, regalías y canon) y sus botones. Quedan el estado por producto, las secciones de texto y una línea **«Resumen <año>»**: pozos perforados, regalías del campo y canon del departamento del último año (por ejemplo, «1 pozo perforado · regalías US$ 24,4 MM · canon y sobrecanon de Loreto S/ 213,9 MM (todo el departamento)»).
- **Botón «📊 Ver estadísticas»:** abre la pestaña **Producción** del campo (vistas anual, mensual y diaria) si tiene serie; si no, la primera pestaña con datos.
- **Pestañas compartidas:** Producción · Pozos perforados · Regalías · Canon y sobrecanon · Empresas. Son dos paneles (`panel_prod.html` y `act_panel.html`) con la misma barra de pestañas, el mismo ancho (900 px) y en el mismo lugar: al cambiar de pestaña se cierra uno y se abre el otro con el mismo lote.
- **Las pestañas siguen al selector «Serie»:** si en Producción se elige otro campo o lote, las pestañas pasan a ese campo (pozos, regalías, empresas y el canon de su departamento); si se elige un departamento, queda activo solo su canon; con «Perú (total)» se ocultan y vuelven al elegir otra serie. Cada serie del panel lleva su campo (`cp`) y departamento (`dp`). El botón de abajo a la izquierda abre Producción sin pestañas, como antes.
- **Prueba:** Chromium, escritorio y móvil: ficha sin gráficos, Producción → Regalías → Empresas → Producción; sin errores de JavaScript.

## Fuente de cada mes y mes incompleto en el panel de producción (18/10/2026)

Lo publicado por PERUPETRO al 18/10/2026: estadística mensual de enero a junio de 2026; reportes diarios de cierre de mes de enero a setiembre; reporte diario en curso de octubre.

- **Vista mensual:**
  - meses de la estadística mensual, con línea continua;
  - meses posteriores, con la suma de los reportes diarios de cierre de mes, con línea punteada;
  - mes en curso (días 1–N), con punto hueco y «*» en el eje («oct*»).
  - El cursor indica la fuente: «suma de los reportes diarios» o «reporte diario en curso, días 1–N: mes incompleto».
- **Vista anual:** el año que la estadística mensual cubre a medias va con «*» («2026*») y barra clara. Suma solo los meses de la estadística mensual (ene–jun); los meses de los reportes diarios se ven en la vista mensual, para no mezclar fuentes en una barra.
- **Nota del gráfico:** se arma con los datos: «Estadística mensual de PERUPETRO hasta jun 2026. jul–set 2026: suma de los reportes diarios de cierre de mes (línea punteada). oct* 2026: reporte diario en curso, días 1–17 (mes incompleto…)».
- En «barriles por día» el mes incompleto no se ve más bajo, porque se divide entre los días con reporte. El «Estado por producto» de la ficha ya usaba esa cuenta.

## Producción por empresa operadora (18/10/2026)

- **Vista anual de Producción** (una sola serie de campo o lote): las barras se apilan por empresa operadora, con leyenda «Operador: …». El cursor da la producción de cada empresa en el año. Los datos van en cada serie del panel (`ob`: operador → p / l / g por año, solo de la estadística mensual).
- **Mismos colores** en Producción y en la línea de tiempo de «Empresas» (`window.ppColOp`): la paleta sigue el orden del primer año con producción de cada empresa en el campo, también cuando se ve un solo lote.
- **Clic en una barra de la línea de tiempo** («Empresas»): abre Producción de ese lote (o del campo, si tiene un solo lote) en los años de esa empresa, con las pestañas del campo.
- Con «Comparar con», o para Perú y los departamentos, las barras siguen siendo de un solo color.


## Canon: serie del Excel de Distribución (19/10/2026)

La pestaña «Canon» lee `PP_canon_departamento_anio.csv`, que ahora sale de los Excel de Distribución (1993–hoy; ver `perupetro_produccion.md`). Si el archivo trae AÑO_COMPLETO, se muestran solo los años completos, para que el año en curso no parezca una caída. Hay que volver a correr el notebook del mapa después del de producción.

## Punto 4: pestaña «Canon» por lote, beneficiario y municipalidades (20/10/2026)

**Provincias y distritos de cada lote.** La sección 2 baja de geoBoundaries los límites de provincias (ADM2) y distritos (ADM3), la misma fuente que ya se usa para los departamentos. Cada distrito toma su departamento y su provincia por su punto interior. La sección 3 calcula, igual que con los departamentos, el % del área del lote en cada provincia y distrito: columnas `PROVINCIA_DETALLE` y `DISTRITO_DETALLE` de `PP_LOTES_GEO.csv`, con el formato «DEP|PROV|DIST 85.0%; …». Desde el 20/10/2026, si la API de geoBoundaries no devuelve JSON (en la primera corrida real falló con «Expecting value»), se reintenta 3 veces, luego se baja el mismo archivo de geoBoundaries desde GitHub y, como último respaldo, GADM 4.1 (`gadm41_PER_2/3.json.zip`, columnas NAME_2 y NAME_3); el mensaje dice qué respondió cada fuente. Si todas fallan, el mapa sigue funcionando sin esas columnas (queda anotado en el control de capas). La ficha del lote muestra «Provincia» y «Distrito» con su %; si es el 100 %, sin porcentaje.

**Datos del panel** (Plus, Bloque 4), leídos de los CSV que deja la sección 9 del notebook de producción:
- `ACT.cl[campo][lote][departamento] = {año: MM US$}`: canon generado por el lote y la parte de cada departamento (`PP_canon_lote_mes.csv`, sin los ajustes de meses anteriores). Los lotes de la Determinación se asignan al campo con los mismos nombres de la producción; se prueban «(T)» y «(TT)».
- `ACT.cb[departamento][beneficiario] = {año: MM S/}`: canon del departamento por beneficiario, solo años completos (`PP_canon_distribucion_mes.csv`).
- `ACT.cm[campo]`: municipalidades de los distritos del lote, más la provincial de cada provincia, con su serie anual en MM S/ (`PP_canon_municipal_mes.csv`). El nombre del distrito de geoBoundaries se busca entre las municipalidades del departamento: primero exacto y, si no aparece, el más parecido (`difflib`, similitud ≥ 0,82). Igual se hace con la provincia.
- `ACT.cln[año]` y `ACT.cmn[departamento][año]`: meses con dato, para marcar los años incompletos.

**Pestaña «Canon y sobrecanon»:** tiene tres vistas, cada una con su gráfico, detalle por año, tabla y CSV:
1. **Generado por el lote** (MM US$), con barras apiladas por el departamento que recibe la parte (Loreto 80 % y Ucayali 20 % en los lotes de Loreto). Es la vista inicial cuando el lote tiene datos.
2. **Departamento por beneficiario** (MM S/): gobierno regional, municipalidades, universidades, institutos, IIAP y Ley 29289. Es lo que recibe el departamento entero.
3. **Municipalidades del lote** (MM S/): distritos donde está el lote (con el % de su área) y la municipalidad provincial. Solo hay datos de 1993–2002 (Distribución) y del año que publica «Canon Municipalidades», que se acumula desde 2025. Los años incompletos se marcan con ⚠️ y los meses con dato.

**Prueba** con el mapa simulado (`mock_plus4.py`, `pw_canon.py`), con los Excel reales de canon y distritos de prueba sobre el Lote 95:
- 2025: Puinahua S/ 19,96 MM, Saquena S/ 1,31 MM y municipalidad provincial de Requena S/ 17,92 MM (9 meses).
- Generado por el Lote 95 en 2026: US$ 15,16 MM para Loreto y US$ 3,79 MM para Ucayali (4 meses).
- Loreto 2025 por beneficiario: 213,84 MM.
- Sin errores en escritorio ni en móvil; las demás pestañas siguen igual.

**Selector de año y detalle por beneficiario (20/10/2026).** En las pestañas con gráfico anual (pozos, regalías, canon) hay un selector «Año de la tabla» debajo del gráfico: cambia la tabla de detalle (y marca la barra), sin filtrar el gráfico; equivale a hacer clic en una barra. En la vista «Generado por el lote», los encabezados «Para Loreto ▾» / «Para Ucayali ▾» son botones: despliegan cómo repartió ese departamento su canon de ese año por beneficiario (gobierno regional, municipalidades, universidades, institutos, IIAP, Ley 29289), en MM S/ y con su participación, del Excel de Distribución. Es lo que recibió el departamento entero por todos sus lotes, no la parte del lote. En años incompletos se muestra con el aviso de meses con dato (datos `cbi`/`cbn` del panel; la vista «Departamento por beneficiario» sigue mostrando solo años completos).

**Ficha más corta y títulos (20/10/2026).** La ficha del lote tiene un alto máximo (58 % de la pantalla) con desplazamiento interno, y provincias y distritos muestran los 3 de mayor % («y N más»). Los nombres de GADM sin espacios («EmilioSanMartin») se separan («Emilio San Martin»). Cada vista del panel lleva un título con el lote, el departamento y la unidad (p. ej. «Loreto · Canon y sobrecanon recibido por las municipalidades de los distritos del Lote 95 (provincia de Requena) (MM S/)»). Primera corrida real: provincias de geoBoundaries (196) y distritos de GADM (1815), porque la API de geoBoundaries cortó la conexión.

**Unidades con palabras (20/10/2026).** En el mapa ya no se usa «MM»: «millones de S/», «millones de US$», «millones de bbl», «millones de pies³» (antes MMPC), «millones de pies³/día» (antes MMPCD) y «miles de millones de pies³» (antes BCF). El beneficiario «LEY 29289» de Loreto (2009–2023) se muestra como «Descuento: pago de deuda (Ley 29289)», en gris: en el Excel de Distribución son dos líneas, «Contrapartida nacional» y «Servicio de deuda», que se descuentan del canon antes del reparto; se mantiene en el gráfico porque es parte del canon del departamento (sin ella el total no cuadra con la serie oficial).

**Nota «canon mayor que regalías» (20/10/2026).** Bajo la tabla de «Regalías» y en la nota de «Generado por el lote» se explica por qué el canon de un lote puede superar a sus regalías (Lote 95, 2025: canon US$ 62,9 millones, regalías US$ 24,4 millones). El canon petrolero no es una parte de las regalías: es un porcentaje fijo del valor de la producción (18,75 % en la zona Loreto/Ucayali). La regalía depende del contrato; en el Lote 95 es una escala por volumen y en 2025 fue el 5,7 % del valor. El canon gasífero de Cusco, en cambio, sí es el 50 % de las regalías y del impuesto a la renta.

**Nota canon vs. regalía (20/10/2026).** En las pestañas Regalías y Canon («Generado por el lote») el detalle del año trae una nota: la regalía es lo que la empresa paga según su contrato; el canon y sobrecanon petrolero no es una parte de ella, sino un porcentaje del valor de la producción (barriles × canasta menos deducciones); en la zona Loreto / Ucayali, 18,75 % (15 % Loreto, 3,75 % Ucayali, según la Determinación). Por eso el canon de un lote puede superar a sus regalías. (A pedido del usuario, la nota no muestra los montos del año ni la advertencia sobre las bases.)

**Botón arriba (20/10/2026).** «📊 Ver estadísticas» está ahora en la parte superior de la ficha, debajo del nombre del lote, para no tener que bajar hasta el final.

**Fuente por periodo en «Municipalidades del lote» (20/10/2026).** PERUPETRO publica el detalle por municipalidad solo en 1993–2002 (Excel de Distribución, «Distribución por concejos») y el año en curso (Excel de Canon Municipalidades); 2003–2024 no tiene detalle (sí el total municipal del departamento). El gráfico pinta esos años con una franja gris «Sin detalle por municipalidad · la fuente no lo publica», muestra debajo la línea «Fuente por periodo», la fuente en el cuadro del cursor y en la nota del detalle, y el CSV trae la columna FUENTE (datos `cmf` del panel, desde FUENTE_EXCEL). Para completar 2003–2024 se busca la fuente del MEF (transferencias de canon y sobrecanon petrolero a gobiernos locales) con `PP_MEF_Canon_Explorar.ipynb`; cuando se integre, sus años saldrán con la fuente «MEF, transferencias a gobiernos locales».

**Canon municipal 2007–2024 desde el MEF (20/10/2026).** «Municipalidades del lote» completa los años sin detalle de PERUPETRO con `DATA/PP_canon_municipal_mef_anio.csv` (notebook `PP_MEF_Canon_Municipal.ipynb`: MEF, Consulta Amigable de Ingresos, canon y sobrecanon petrolero *recaudado* por cada municipalidad, tipos de recurso 5 y K del rubro 18). Se usa solo en los años y departamentos que PERUPETRO no cubre; la línea «Fuente por periodo» lo rotula. 2005–2006 vienen del tipo «0: NORMAL» (todos los canones, no solo el petrolero) y la fuente lo dice así. 2003–2004 siguen en gris: PERUPETRO entregaba el total municipal al Consejo Nacional de Descentralización y el MEF registra el ingreso a nombre del CND, sin reparto.

**Paleta del proyecto en el panel de estadísticas (20/10/2026, a prueba).** Azul noche #111149, turquesa #72D2D5, naranja #DD6140, amarillo #FFC41D, gris azulado #CCD3DF, negro #181818 y blanco #FEFEFE, con tonos intermedios (#2A9DA1, #5A5A9E, #A8452B, #8C96AD) cuando hacen falta más series. Beneficiarios: gobierno regional azul noche, municipalidades turquesa, universidades naranja, institutos amarillo, IIAP turquesa oscuro, descuento Ley 29289 gris. Botones activos en azul noche. Los colores anteriores quedan en el historial de `act_panel.html` por si se descarta.

**Tipo de letra Barlow (20/10/2026).** Todo el mapa (fichas, panel de producción, panel de estadísticas, leyenda y controles) usa Barlow de Google Fonts; los íconos no se tocan y, sin conexión a internet, cae en la letra del sistema.

**Pendiente de la corrida real:** confirmar qué fuente entregó ADM2 y ADM3 (geoBoundaries o GADM), y revisar los nombres de distrito que no se emparejen.
