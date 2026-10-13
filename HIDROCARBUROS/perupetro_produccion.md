# Producción petrolera por lote · PERUPETRO · Contexto del proyecto

Documento de traspaso para retomar el proyecto sin perder contexto. Última actualización: **10/10/2026**.

---

## 1. Objetivo

Analizar la **producción petrolera de Loreto**: qué lote produce o ha producido más, qué empresas los operan y cómo influyen las condiciones geográficas. Se combinará con:
- las exportaciones de crudo de Infotrade (`EXPORT/`, partida 2709);
- el canon petrolero;
- el mapa de lotes.

**Notebook:** `HIDROCARBUROS/PP_Produccion_Lotes.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Produccion_Lotes.ipynb

## 2. Carpetas de Google Drive

| Uso | ID |
|---|---|
| DATA (CSV + subcarpeta `PDF` con los PDF descargados) | `1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq` |
| CONTROL (control y catálogo de PDF) | `1TKjS2Wjpnf26oladjhqstmN5c9Irq-Aj` |

## 3. Fuente

Página **Estadísticas → Estadística Petrolera** de perupetro.com.pe (la URL está en el Bloque 3, `PAGINA_EST`):
- Estadística **anual** de hidrocarburos de 1994 a 2025.
- Estadística **mensual** del año en curso.
- Todo en PDF, sin necesidad de usuario.

Tablas de interés:

| Tabla | Anual | Mensual |
|---|---|---|
| Producción fiscalizada mensual de hidrocarburos líquidos por **operador y lote** (petróleo y LGN) | 12 meses del año | acumulado del año |
| Producción por **yacimiento**, estado de pozos, regalías por lote, canasta de precios, contratos | sí | parcial |
| Canon y sobrecanon por departamento | sí | sí |
| Mapa de lotes (ArcGIS público) | — | enlace en el índice |

El mapa está en https://perupetro.maps.arcgis.com/apps/webappviewer/index.html?id=cc883917c55a4264a01debfa02585e2e. Es la fuente prevista para los polígonos de los lotes y el departamento de cada uno.

**Zona vs departamento:** los PDF usan zonas (Selva Norte, Selva Central, Selva Sur, Noroeste, Zócalo). Por ahora solo se asigna `DEPARTAMENTO = LORETO` a Selva Norte (lotes 1-AB/192, 8, 67, 95, 102, 64, 39). El resto queda vacío hasta cruzarlo con el mapa de lotes.

**Certificado HTTPS.** perupetro.com.pe no envía su certificado intermedio. Los navegadores lo completan solos, pero Python falla con `CERTIFICATE_VERIFY_FAILED` (visto en Colab el 10/10/2026). El Bloque 3 resuelve esto sin desactivar la verificación:
- lee el certificado del servidor;
- descarga los intermedios desde la dirección AIA del propio certificado (hasta 3 niveles);
- arma `ca_perupetro.pem` (certifi + intermedios) y verifica con la cadena completa.

`VERIFICAR_SSL = False` existe solo como último recurso. La otra alternativa es subir los PDF a mano a `DATA/PDF`.

## 4. Notebook (3 bloques)

1. **Instalación y extractor.** `pdfplumber` lee la tabla "PRODUCCIÓN FISCALIZADA MENSUAL DE HIDROCARBUROS LÍQUIDOS" **por coordenadas**: ubica cada número en la columna del mes más cercana. Así no se mezclan columnas con gráficos o notas al pie.
   - **Nombres de lote:** se homologan, por ejemplo `8.`→`8`, `IX,`→`IX`, `192 (1)`→`192`, `1AB`→`1-AB`. `LOTE_ORIGINAL` conserva el texto del PDF.
   - **Operadores:** `PETROMONT` se homologa a `PETROLERA MONTERRICO`. Los rótulos de gráficos (`DPB`, `BPD`, `MBBL`…) ya no se toman como operador; antes aparecía `DPB` en los lotes 56 y 88 en 2021.
   - **Operador:** si en la tabla mensual sale ilegible por una nota superpuesta, se toma de la tabla resumen del mismo PDF.
   - **Mes vacío:** si a una fila le falta un mes y el total lo permite, se imputa (`IMPUTADO <MES>`), por ejemplo el Lote 56 en setiembre de 2021.
2. **Selectores:**
   - año inicio y año fin;
   - usar la última mensual para el año en curso;
   - guardar los PDF en Drive.
3. **Descarga, extracción, control y Drive.**
   - Lee los enlaces de la página.
   - Descarga cada PDF o lo reutiliza si ya está en `DATA/PDF`. `PP_CATALOGO_PDF.csv` (en CONTROL) guarda la relación URL → archivo.
   - Procesa también los PDF que se suban **a mano** a `DATA/PDF` (por si la web cambia).
   - Para cada año usa el **anual**; si no hay anual, la **mensual más reciente**.

## 5. Archivos

**`PP_produccion_lote_mes_<ini>-<fin>.csv`** (DATA): una fila por año × mes × lote × producto.

| Columna | Qué es |
|---|---|
| `AÑO`, `MES`, `FECHA` (dd/mm/aaaa, día 01) | Período |
| `ZONA`, `DEPARTAMENTO` | Zona de PERUPETRO; departamento (por ahora solo Loreto) |
| `OPERADOR`, `LOTE`, `LOTE_ORIGINAL` | Empresa operadora y lote |
| `LOTE_HISTORICO` | Une contratos sucesivos del mismo campo para series largas y rankings: `1-AB/192` (el 1-AB terminó el 29/08/2015 y desde el 30/08/2015 es el 192), `Z-2B/Z-69` (Z-2B pasó a Z-69 en 2023, a confirmar), y quita los sufijos de contratos temporales (`I(T)`/`I(TT)` → `I`, `VI(T)` → `VI`) |
| `PRODUCTO` | `PETROLEO`, `LGN` (líquidos de gas natural) o `CONDENSADO` (años antiguos, Lote 31-C) |
| `BARRILES`, `BPD` | Producción fiscalizada del mes y promedio diario |
| `ESTADO_FILA`, `FUENTE` | `OK` / `IMPUTADO <MES>` / `REVISAR`, y PDF de origen |

**`PP_produccion_gas_lote_mes_<ini>-<fin>.csv`** (DATA), añadido el 12/10/2026: gas natural fiscalizado por lote y mes, 1994–hoy (2001+ del PDF; 1994–2000 transcrito).
- **Origen:** la tabla «Producción fiscalizada mensual de gas natural (MPC)» de los mismos PDF, leída en la misma pasada (`extraer(path, "GAS")`).
- **Columnas:** las mismas de identificación que el CSV de líquidos, más `PRODUCTO` = `GAS NATURAL`, `MPC` (miles de pies cúbicos) y `MMPCD` (millones de pies cúbicos por día).
- **Variantes de título que se reconocen:**
  - «… FISCALIZADA MENSUAL DE GAS NATURAL 2021 (MPC)»;
  - «… MENSUAL FISCALIZADA DE GAS NATURAL - 2001»;
  - «… FISCALIZADA DE GAS NATURAL MENSUAL (MPC) - 2012», en página girada 90°;
  - «… FISCALIZADA MENSUAL (Mscf) - 2008», sin la palabra gas; se reconoce por la unidad.
- **Tablas descartadas:** la versión en MMBTU, la producción «de campo» y los balances.
- **Prueba con los PDF reales:** 2001, 2008, 2010, 2016, 2020, 2021, 02/2024 y 01/2026. La suma de lotes cuadra con el TOTAL del PDF con ≤ 2 MPC de diferencia, por redondeo de decimales. En 2021 el total es 401.690.512 MPC, frente a 401.690.513 en el PDF.
- **Tolerancia por fila:** 6 MPC.
- **Control:** columnas `LOTES_GAS`, `GAS_MPC`, `DIF_MAX_GAS` y `ESTADO_GAS`.
- **1994–2000:** transcritos a mano desde los escaneos (`transcripciones/PP_gas_mensual_<año>_transcrito.csv`, 12/10/2026). Cuadran exacto filas, meses y total general.
  - Lotes con gas fiscalizado en esos años: I (Cavelcas/GMP), VI (Petroperú/Sapet), VII (1994), VII/VI (2000), X (Petroperú/Pérez Companc), Z-2B (Petrotech) y 31-C (Aguaytía, desde marzo de 1998).
  - Totales anuales en MPC: 1994 9.536.727; 1995 9.425.074; 1996 8.768.216; 1997 8.530.880; 1998 14.431.906; 1999 14.644.530; 2000 12.183.917.
  - Nota del PDF de 1995: el gas fiscalizado del lote VI se reinyectó mientras lo operó Petroperú, hasta el 10/10/1995.

**`CONTROL PP produccion_lote_mes_<ini>-<fin>.csv`** (CONTROL): una fila por PDF usado.
- `LOTES`, `FILAS_IMPUTADAS`, `FILAS_REVISAR`.
- `BARRILES_PETROLEO` / `BARRILES_LGN`.
- `DIF_MAX_TOTAL` (todos los productos contra el TOTAL general), `DIF_MAX_PETROLEO` / `DIF_MAX_LGN` / `DIF_MAX_CONDENSADO`: la mayor diferencia mensual entre la suma de lotes y el SUB-TOTAL/TOTAL que imprime el PDF (debe ser 0).
- `ESTADO`: `OK`, `REVISAR`, `SIN TABLA`, `ESCANEADO (sin texto)`, `FORMATO ANTIGUO (texto OCR)`, `ERROR DE DESCARGA` o `NO ES ESTADÍSTICA…`.

## 6. Pruebas

Probado (simulación de la web y de Drive) con los anuales 2020 y 2021 y los mensuales de febrero 2024 y enero 2026:
- 4/4 en OK con diferencia 0 contra los totales del PDF;
- la segunda corrida reutiliza los PDF de Drive.

Loreto (petróleo, millones de bbl):

| Lote | 2020 | 2021 | 2024 (ene–feb) | 2026 (ene) |
|---|---|---|---|---|
| 95 | 2.07 | 3.23 | 1.11 | 0.46 |
| 67 | 0.25 | 0.52 | 0 | 0 |
| 8 | 0.59 | 0 | — | 0.13 |
| 192 | 0.48 | 0 | 0 | 0 |

## 7. Pendientes

1. **Primera corrida real (10/10/2026).** Resultado por año:
   - 2019–2025 y 2026 (mensual de junio): OK.
   - 2017 y 2018: REVISAR, por unos 3–4 mil bbl. **Corregido:** el Lote 31-B/D de Maple aparece como `31B/31D` en 2012–2018 y quedaba fuera.
   - 2012, 2016 y 2017 ahora cuadran con diferencia 0 (probado con los PDF reales).
     - 2016 titula la tabla sin "FISCALIZADA" ("PRODUCCIÓN DE HIDROCARBUROS LIQUIDOS MENSUAL 2016").
     - 2016 tiene "Pág. 24" pegado al rótulo de LGN.
   - **Velocidad:** con `pypdf` se ubican primero las pocas páginas con la tabla (lectura rápida) y solo esas se analizan con pdfplumber. 8 anuales en menos de 2 min.
   - 1994–2016: no reconocidos por la portada. Se corrigió: 2001 y 2008 son **digitales** y ahora se leen con diferencia 0.
     - Se aceptan los títulos "PRODUCCIÓN FISCALIZADA MENSUAL 2008" y "PRODUCCION MENSUAL FISCALIZADA DE HIDROCARBUROS LIQUIDOS - 2001".
     - Se aceptan las columnas CONTRATISTA, los meses abreviados (ENE…DIC) y el punto como separador de miles.
     - Se aceptan los lotes `Z - 2B`, `1 - AB`, `31B/D` (→ `31-B/D`) y `31-C ( LGN )` / `31-C ( COND.)` (producto CONDENSADO).
     - Se leen las páginas con texto girado 90° (anual 2008).
     - Control contra un solo TOTAL general cuando no hay subtotal por producto.
   - Se excluyen los documentos legales enlazados en la misma página, como un reglamento de participación ciudadana.
   - **Corrida del 11/10/2026:** 25 años OK (2001–2009, 2011–2025 y 2026 ene–jun), todos con diferencia 0 contra el total del PDF (6.540 filas).
   - **Corrida completa 1994–2026 (11/10/2026):** 33 años con datos y 8.076 filas: 26 años OK por extracción y 7 OK (transcrito). En 2001–2006 la columna `DIF_MAX_LGN` mostraba millones de barriles, pero era un falso aviso: el TOTAL general del PDF, que va después de la sección LGN, se comparaba como si fuera el subtotal de LGN. Ahora el control por producto ignora el total general; el total sigue controlado en `DIF_MAX_TOTAL` (0 en todos los años).
   - **Ranking de Loreto:**
     - pone 0, y no NaN, en los años en que el lote ya existía pero no figura en el PDF; queda vacío solo antes de su primer año;
     - el año en curso se rotula con los meses que trae, p. ej. "2026 (ene–jun)";
     - `LOTE_HISTORICO` une 31-B y 31-D en `31-B/D`.
   - 2010: su título es "PRODUCCIÓN FISCALIZADA MENSUAL - 2010", con guion. Corregido; ahora OK.
   - **1994–2000 (escaneados): transcripción validada.** El OCR automático no es confiable en estos escaneos. Por eso la tabla mensual de cada año se transcribe desde la imagen ampliada de la página y se valida en tres niveles:
     - cada lote suma su total anual;
     - cada mes suma el TOTAL del mes;
     - el gran total coincide con la tabla resumen del PDF.

     Las celdas que no cuadran se releen con más zoom. Por ejemplo, en 1998 hubo 9 celdas mal leídas en la primera pasada, como 691.465 → 891.465 en el Lote 8 de enero.
   - Los archivos están en `HIDROCARBUROS/transcripciones/PP_mensual_<año>_transcrito.csv`, con las columnas `LOTE_ORIGINAL`, `LOTE` homologado y `FUENTE` (PDF y página).
   - El notebook los lee desde GitHub para los años sin extracción OK: `ESTADO = OK (transcrito)`, `ESTADO_FILA = TRANSCRITO`.
   - **Serie completa 1994–2000.** Todos los años transcritos y validados con diferencia 0.
   - **1995** (p.18, escaneo sin texto): 11 celdas dudosas (el 6 y el 8 se confunden en el escaneo) se resolvieron con la validación y con el "Cuadro de producción acumulada de petróleo crudo 1995" de la p.17, que trae las mismas cifras en otra tipografía (VI+VII y 31-B+31-D vienen sumados ahí y también cuadran). Total 44.443.276 bbl. Nota manuscrita: Cavelcas operó el Lote I hasta el 24/08/1995 (155.936 bbl).
   - **1996** (p.16): transcrito desde la imagen; cuadra a la primera. Total 43.909.188 bbl. Incluye el lote LOB/EA/LO (OXY/Bridas) hasta julio: desde el 24/07/1996 pasó al Lote X (salvo Folche y Cruz, que pasaron al VI).
   - Los PDF de 1995 y 1996 están en `HIDROCARBUROS/pdf_escaneados/` (subidos por el usuario porque pesan más de lo que admite el chat).
   - **1997** (p.10) trae una capa OCR legible: se tomó como base y se validó contra la imagen. Solo una celda estaba mal (Lote I, abril: 19.662 → 19.862). Total 43.157.111 bbl, igual a la tabla "por contratista". En 1997 no hay LGN ni condensado (Aguaytía empieza en 1998).
   - **1999** (p.10, "Producción mensual de hidrocarburos líquidos") también trae OCR, pero con 10 celdas mal leídas y sin las filas de LGN/condensado: se corrigió y completó desde la imagen (por ejemplo Mercantile abril 27.665 → 27.685, Lote 8 total 9.786.945 → 9.788.945). Total 38.663.371 bbl, igual a la tabla "por contratista" (p.8).
2. **PDF antiguos.** Revisados 1994 y 1998:
   - **1998** es un escaneo sin texto.
   - **1994** es un escaneo con texto OCR de mala calidad y otro diseño: "PRODUCCION MENSUAL DE PETROLEO CRUDO", punto como separador de miles, por contratista y lote.

   El notebook los marca `ESCANEADO (sin texto)` o `FORMATO ANTIGUO (texto OCR)` y **los guarda igual** en `DATA/PDF` como `PP_ANUAL_<año>.pdf`.

   Opciones para esos años:
   - OCR con Tesseract en Colab, solo de la tabla resumen anual por contratista y lote (unas 15 filas por año), validando que la suma dé el TOTAL;
   - las tablas de 10 años de los anuales digitales (cada anual trae la serie anual por lote de la década anterior);
   - transcripción manual de las pocas tablas que el OCR no lea bien.

   Dato del anual 1994: Lote 1-AB (Occidental) 20,04 MM bbl; Lote 8 (Petroperú) 10,62 MM bbl; total país 46,47 MM bbl.
3. **Mapa de lotes** (ArcGIS público) para los polígonos y el departamento de cada lote.
4. Otras tablas del anual: producción por **yacimiento**, **estado de pozos**, **regalías por lote**, canasta de precios.
5. Cruce con Infotrade (exportación de crudo de Loreto) y canon (MEF / tabla de canon del PDF).
6. Banco de Datos de PERUPETRO (cuenta del usuario, credenciales en Colab → Secretos): pozos y sísmica. Requiere capturas F12.

## 8. Flujo de trabajo con GitHub

El mismo de los demás proyectos (ver `FISCAL/CONTEXTO_PROYECTO.md` §9): rama `claude/scraper-gobiernos-regionales-kk6ecm`, PR y merge a `main`, notebooks sin salidas.


## Producción diaria (sección 8 del Bloque 3 de `PP_Produccion_Lotes.ipynb`, 12/10/2026)

Primero fue un notebook aparte; ahora corre en el mismo notebook de producción si está marcada la casilla «Producción diaria» del Bloque 2, que viene marcada por defecto. No depende del período elegido. Usa la conexión a Drive y el certificado del Bloque 3.

**Fuente.** perupetro.com.pe → Estadísticas → Producción Hidrocarburos → **Producción Diaria**. Hay un PDF por mes (cierre de mes) y uno del mes en curso:
- «Líquidos en b/d»: *Reporte de producción fiscalizada de hidrocarburos líquidos a nivel nacional (barriles)*, con una columna por lote para petróleo y condensado, una por lote de LGN, los SUB TOTAL y el TOTAL.
- «Gas en Mcfd»: *Reporte de producción fiscalizada de gas natural (Mcf)*. Trae una segunda hoja en MMBtu.
- «Gas en m3/d»: se usa desde el 13/10/2026 (`UNIDAD` = M3).
  - Sus rótulos de UNNA («Lote III.» y «Lote IV.», en negrita) se montan sobre los números del día 1; el lector separa las palabras por tipo de letra.
  - Los nombres de operador vienen cortados («N EXPORT»); se toman del reporte en Mcf del mismo mes.
  - Control: m3 ÷ Mcf = 28,317 en todos los lotes (1 Mcf = 28,3168 m3).

**Lector (`pd_parser`).**
- **Cabecera:** lee la tabla por coordenadas. Toma la primera fila con 5 o más códigos de lote; en gas vienen como «Lote : 31-C».
- **Operadores:** salen del encabezado, aunque un operador abarque varios lotes. Por ejemplo, MONTERRICO cubre II y XX, y UNNA ENERGIA cubre III y IV.
- **Valores:** van alineados a la derecha de su celda.
- **Control por día:** la suma de los lotes de cada producto se compara con su SUB TOTAL y la de todos con el TOTAL. La tolerancia es 1 bbl en líquidos y 0,05 en gas.
- **Lotes:** `X.` → `X` y `192_LIC` → `192`. El lote 8 aparece dos veces en líquidos, con PLUSPETROL NORTE y con UPLAND OIL; se conserva el operador de cada columna.

**Salidas.**
- `DATA/PP_produccion_diaria.csv`, una fila por día × lote × producto × unidad.
  - Columnas: `FECHA` (dd/mm/aaaa), `AÑO`, `MES`, `DIA`, `FLUIDO`, `PRODUCTO` (PETROLEO Y CONDENSADO / LGN / GAS NATURAL), `UNIDAD` (BBL / MCF / MMBTU / M3), `OPERADOR`, `LOTE_ORIGINAL`, `LOTE`, `VALOR`, `FUENTE` y `DEPARTAMENTO` (del mapa).
  - Se **acumula**: cada corrida reemplaza los meses que vuelve a leer y conserva los anteriores.
- `CONTROL/CONTROL PP produccion_diaria.csv`, una fila por mes y unidad: `REPORTE_AL`, `DIAS`, `DIAS_OK`, `DIF_MAX`, `LOTES` y `ESTADO`.
- Los PDF se guardan en `DATA/PDF_DIARIA/PP_DIARIA_<LIQUIDOS|GAS>_<año>_<mes>.pdf`. Un PDF subido a mano a esa carpeta también se lee.

**Prueba (setiembre 2026, PDF reales).**
- Líquidos, gas en Mcf y gas en MMBtu: 30/30 días OK, con diferencia 0.
- Los promedios del mes coinciden con los «PROMEDIOS» que imprime el PDF: gas del lote 88 1.034,88 MMPCD; LGN del 88 42.020 bpd; lote 95 11.612 bpd; X 9.084 bpd.
- **No probado contra la página real:** desde la nube de Claude no se accede a perupetro.com.pe. Los enlaces se reconocen por el texto («Líquidos», «Gas en Mcfd») o por el nombre del archivo.

**Ajuste del 13/10/2026: solo encontraba el mes en curso.**
- **Síntoma:** en la primera corrida real solo halló los 2 enlaces del mes en curso (octubre, días 1–11, con los 11 días OK). No vio la tabla de enero–setiembre.
- **Cambios en la búsqueda de enlaces:**
  - acepta `href` con comillas simples, dobles o sin comillas, y enlaces con `.pdf` o `AJPERES` en cualquier parte;
  - también lee las páginas de los `iframe`.
- **Diagnóstico nuevo:**
  - guarda la página en `CONTROL/PP_pagina_produccion_diaria.html`;
  - si encuentra menos de 4 reportes, imprime los enlaces a PDF que vio («🔎 Diagnóstico»).
- **Ajuste 2 (13/10/2026):** también se toman los enlaces cuyo **texto** es «Líquidos en b/d» o «Gas en Mcfd», aunque la dirección no termine en `.pdf`. Al descargar solo se acepta lo que de verdad es un PDF.
- **Enlace real de la tabla** (13/10/2026, enero 2026): `https://www.perupetro.com.pe/wps/wcm/connect/corporativo/a48b83b1-…/Reporte+de+Producci%C3%B3n+de+L%C3%ADquidos+31.1.2026.pdf?MOD=AJPERES&Liquidos%20-%20enero%202025`.
  - Es una dirección normal a un PDF; la falla anterior se debía, con toda probabilidad, al formato del `href` (comillas).
  - El texto del enlace dice «enero 2025», pero el PDF es de enero de 2026. El año y el mes se toman siempre del contenido del PDF.
- **Ajuste 3 (13/10/2026), causa real:** sin cabecera de idioma, el portal de PERUPETRO responde la página en **inglés** («Liquid Production b/d»), y esa versión no trae la tabla de meses. Ahora todas las descargas envían `Accept-Language: es-PE,es`; la página diaria se pide con sesión y, si sigue en inglés, se reintenta una vez y se avisa.
- **Ajuste 4 (13/10/2026), m3 de mayo «REVISAR»:** el operador LATIN AMERICAN ENERGY ocupa tres renglones en la cabecera y su columna no trae el rótulo «Lote …». Solo produjo el 30 y 31/05 (14.548 y 39.931 m3), por eso solo esos días no cuadraban. Ahora, si un operador de la cabecera no tiene columna de lote debajo, se crea su columna. El lote sale de `LOTE_DE_OPERADOR` (LATIN AMERICAN ENERGY / LAET → VI); si el operador no está ahí, el lote queda «SIN ROTULO». Mayo pasa a 31/31 días OK.

**Gas mensual: 7 años corregidos (13/10/2026)**, con los PDF reales. En la corrida del 13/10 salían 3 en REVISAR y 4 SIN TABLA.

| Año | Problema | Corrección |
|---|---|---|
| 2005, 2006 | Además de la tabla en MPC se leía la de «PODER CALORÍFICO» (energía) y se sumaba: 21 y 14 lotes | Se descartan los títulos con CALOR, MMBTU, CAMPO o BALANCE |
| 2007 | El PDF imprime «-3616», «3-3402» y «4-3034» (SAPET VII/VI, may–jul) por 3.616, 33.402 y 43.034 | En gas se quita el guion intercalado; la fila cuadra con su TOTAL |
| 2011 | El rótulo del lote va 3 pt más arriba que sus valores (página girada) | En gas, las filas se agrupan con 3,6 pt de tolerancia |
| 2013 | Título «PRODUCCIÓN MENSUAL (MPC) - 2013», sin «fiscalizada» ni «gas» | Se acepta «MENSUAL» con unidad MPC/MSCF/MCF |
| 2024, 2025 | La tabla mensual en MPC se titula «RESUMEN DE PRODUCCIÓN FISCALIZADA DE GAS NATURAL» | Se acepta ese título (con columnas de meses) |

- **Resultado:** los 7 años cuadran con el TOTAL del PDF, con ≤ 2 MPC de diferencia por redondeo. Los otros años probados siguen igual, y los líquidos no cambian.
- **PDF de prueba:** 2005, 2006, 2007, 2011, 2013 y 2024 están en `HIDROCARBUROS/pdf_fuente/` (son digitales). 2025 no se sube porque pesa 28 MB.

## Pozos, regalías, canon y precio de canasta (sección 6.1 del Bloque 3, 13/10/2026)

Se leen de las mismas **Estadísticas Anuales** si está marcada la casilla «Pozos, regalías, canon y precio de canasta» del Bloque 2 (viene marcada). Solo se leen los anuales del período elegido: para la serie completa, correr desde 2001. Lector: `px_parser` (embebido en el Bloque 1), que reutiliza `palabras` y `lineas` de `pp_parser`.

**Inversión en US$ por lote: no está en los anuales.** El resumen ejecutivo solo trae la inversión total del país. El indicador de actividad por lote disponible son los **pozos perforados**.

| Tabla del PDF | Archivo (DATA) | Cobertura | Control |
|---|---|---|---|
| «Pozos exploratorios / confirmatorios / de desarrollo perforados por contrato aaaa–aaaa» (series de 10–11 años) | `PP_pozos_perforados_lote_anio.csv` | 1995–hoy (la edición 2005 llega a 1995) | suma de lotes = fila TOTAL, por año y tipo |
| «Ingresos al fisco» / «Ingreso por regalías por contrato» (2007+, US$) e «Ingresos por contratos» (2001–2006, miles de US$) | `PP_regalias_lote_anio.csv` | 2001–hoy | suma de lotes = TOTAL (0,1 % en 2001–2006, que vienen redondeados a miles) |
| «Distribución del canon / sobrecanon aaaa–aaaa» (millones de soles) | `PP_canon_departamento_anio.csv` | 1993–hoy (la edición 2001 llega a 1993) | suma de departamentos = TOTAL |
| «Valor mensual del precio de canasta de hidrocarburos líquidos» (US$/bbl) | `PP_precio_canasta_lote_mes.csv` | 2001–hoy | promedio de los 12 meses = PROMEDIO del PDF (2012+); en 2007–2011, que no lo imprimen, se exigen 12 meses |
| producción de líquidos × precio de canasta | `PP_valor_produccion_lote_mes.csv` | años con canasta | ESTADO_PRECIO: OK / SIN PRECIO / SIN PRODUCCION |

Control: `CONTROL/CONTROL PP tablas_adicionales.csv` (TABLA, EDICION, AÑO, SUMA, TOTAL_PDF, PAGINA, USADO, ESTADO).

**Cómo se leen** (todas por coordenadas):
- **Series por lote (pozos, canon):** el encabezado es la primera línea con 4 o más años; cada número va a la columna más cercana. Así funciona aunque el PDF deje celdas vacías sin «-». Para cada año manda la **edición más reciente**: PERUPETRO corrige cifras, por ejemplo desarrollo 2013 = 83 en la edición 2016 y 84 en la 2020.
- **Celdas combinadas:** cuando un lote tuvo varios operadores, el rótulo del lote va centrado verticalmente en su bloque de filas. Por ejemplo, el lote III cubre MERCANTILE, INTEROIL y GMP, y el IV cubre RIO BRAVO, INTEROIL y GMP. Las filas se reparten entre los rótulos con una partición óptima (`asignar_lotes`), de modo que el centro de cada bloque quede junto a su rótulo. Lo mismo se hace con la modalidad (licencia / servicios) y el hidrocarburo en regalías, y con el operador escrito en otra línea («REPSOL» para los lotes 39 y 57).
- **Formatos especiales:**
  - Edición 2005 de pozos: traspuesta, con lotes en columnas, años en filas y 3 páginas giradas. Las columnas salen de los bordes de las celdas (`rects_lectura`) y el operador de la celda combinada de arriba.
  - Canasta 2001–2006: también traspuesta, con meses en filas. Se asigna por orden de columnas y se descartan las de gas natural.
  - Regalías 2001–2006: dos columnas de página (petróleo/LGN a la izquierda, gas/condensado a la derecha).
  - Regalías 2001 usa punto de miles.
- **Lotes:** se aceptan variantes como `VII-VI` y `VII_VI` → VII/VI; `31B-31D` → 31-B/D; `31C` → 31-C; `I (TT)`, `VI (T)` → I, VI (el original queda en `LOTE_PDF`). La canasta separa los lotes agrupados («VII y V», «31B-31D / 31C») y las variantes de producto (`Z-69-L`, `Z-69-P`, `Z-2B (LGN)` → columna VARIANTE). En 2001 hay un solo precio para la zona NOROESTE, que se usa para sus lotes.
- **Restos de gráficos:** en la canasta se lee hasta donde empieza el eje del gráfico. Solo se aceptan precios con decimales, porque hay textos superpuestos como «6677866778».
- **Pozos antiguos:** hasta 2001 (ediciones 2005 y 2008) los confirmatorios van dentro de los exploratorios. Desde 2013 no se cuentan pozos inyectores (nota del PDF).

**Prueba** con 15 anuales reales (2001, 2005–2008, 2010, 2012, 2013, 2016, 2017, 2020, 2021, 2024, 2025):
- **Pozos:** las 7 ediciones con series cuadran exacto con su TOTAL. Además coinciden entre sí en los años que comparten: 1998–2012 idénticos en todas, con solo 2013 y 2014 corregidos en +1.
- **Regalías:** cuadran exacto en 2001, 2007, 2008, 2010, 2012, 2013, 2016, 2020, 2024 y 2025. En 2005 y 2006 la diferencia es de 2 a 2,4 mil US$, por el redondeo a miles.
- **Canon:** todas las ediciones cuadran, con diferencias de 0,01 por redondeo; en la edición 2001, de 1.
- **Canasta:** el promedio calculado coincide con el impreso (≤ 0,01 US$/bbl). Hay 2 casos reales en 2008, que quedan en REVISAR: el lote 56 empezó en setiembre (4 meses) y a XIII le falta un mes en el PDF. En 2010, a V le falta enero por un texto superpuesto en el PDF.
- **Corrida simulada del notebook (2001–2026)** con Drive falso: sin errores. Genera los 5 CSV y el control; solo 1 fila de producción queda sin precio (XIII, 2008).
- **Tiempo:** unos 10 s más por anual.
