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
| `PRODUCTO` | `PETROLEO` o `LGN` (líquidos de gas natural) |
| `BARRILES`, `BPD` | Producción fiscalizada del mes y promedio diario |
| `ESTADO_FILA`, `FUENTE` | `OK` / `IMPUTADO <MES>` / `REVISAR`, y PDF de origen |

**`CONTROL PP produccion_lote_mes_<ini>-<fin>.csv`** (CONTROL): una fila por PDF usado.
- `LOTES`, `FILAS_IMPUTADAS`, `FILAS_REVISAR`.
- `BARRILES_PETROLEO` / `BARRILES_LGN`.
- `DIF_MAX_PETROLEO` / `DIF_MAX_LGN`: la mayor diferencia mensual entre la suma de lotes y el SUB-TOTAL/TOTAL que imprime el PDF (debe ser 0).
- `ESTADO`: `OK`, `REVISAR`, `SIN TABLA`, `ERROR DE DESCARGA` o `NO ES ESTADÍSTICA…`.

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

1. **Primera corrida real en Colab** (1994–2026). Los PDF antiguos (antes de 2012, aprox.) pueden tener otro formato. Si el control los marca `SIN TABLA` o `REVISAR`, se ajusta el extractor con esos PDF.
2. **Mapa de lotes** (ArcGIS público) para los polígonos y el departamento de cada lote.
3. Otras tablas del anual: producción por **yacimiento**, **estado de pozos**, **regalías por lote**, canasta de precios.
4. Cruce con Infotrade (exportación de crudo de Loreto) y canon (MEF / tabla de canon del PDF).
5. Banco de Datos de PERUPETRO (cuenta del usuario, credenciales en Colab → Secretos): pozos y sísmica. Requiere capturas F12.

## 8. Flujo de trabajo con GitHub

El mismo de los demás proyectos (ver `FISCAL/CONTEXTO_PROYECTO.md` §9): rama `claude/scraper-gobiernos-regionales-kk6ecm`, PR y merge a `main`, notebooks sin salidas.
