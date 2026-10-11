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
   - 2010: su título es "PRODUCCIÓN FISCALIZADA MENSUAL - 2010", con guion. Corregido; ahora OK.
   - **1994–2000 (escaneados): transcripción validada.** El OCR automático no es confiable en estos escaneos. Por eso la tabla mensual de cada año se transcribe desde la imagen ampliada de la página y se valida en tres niveles:
     - cada lote suma su total anual;
     - cada mes suma el TOTAL del mes;
     - el gran total coincide con la tabla resumen del PDF.

     Las celdas que no cuadran se releen con más zoom. Por ejemplo, en 1998 hubo 9 celdas mal leídas en la primera pasada, como 691.465 → 891.465 en el Lote 8 de enero.
   - Los archivos están en `HIDROCARBUROS/transcripciones/PP_mensual_<año>_transcrito.csv`, con las columnas `LOTE_ORIGINAL`, `LOTE` homologado y `FUENTE` (PDF y página).
   - El notebook los lee desde GitHub para los años sin extracción OK: `ESTADO = OK (transcrito)`, `ESTADO_FILA = TRANSCRITO`.
   - Hechos: 1994, 1998 y 2000. Faltan 1995, 1996, 1997 y 1999 (pedir los PDF de DATA/PDF).
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
