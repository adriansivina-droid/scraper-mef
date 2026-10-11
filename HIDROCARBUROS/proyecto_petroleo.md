# Proyecto Petróleo · Loreto · Resumen para continuar en otro chat

Resumen ejecutivo del proyecto de producción petrolera. Sirve para retomarlo en una sesión nueva sin perder el contexto. El detalle técnico del extractor está en `HIDROCARBUROS/perupetro_produccion.md`. Última actualización: **11/10/2026**.

---

## 1. Qué buscamos

Hacer un **análisis económico de la producción petrolera de Loreto**:
- qué lote produce o ha producido más;
- qué empresas los operan y operaron;
- cómo influyen las condiciones geográficas (Loreto es una región muy extensa);
- cómo se relaciona la producción con las exportaciones de crudo y con el canon que recibe la región.

El plan es combinar varias fuentes que se unen por **lote**, **operador** y **año-mes**:

```
                 LOTE (1-AB/192, 8, 95, 67…)
                   │
 ┌─────────────────┼──────────────────────┬──────────────────────┐
 Producción        Mapa / Banco de Datos  Infotrade              Canon
 lote × mes        polígonos, pozos       exportación 2709       Loreto × mes
 (HECHO)           (PENDIENTE)            (scraper listo,        (PENDIENTE)
                                           cruce pendiente)
```

## 2. Dónde está todo

| Qué | Dónde |
|---|---|
| Repositorio | `adriansivina-droid/scraper-mef` (público), carpeta `HIDROCARBUROS/` |
| Notebook | `HIDROCARBUROS/PP_Produccion_Lotes.ipynb` |
| Abrir en Colab | https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Produccion_Lotes.ipynb |
| Contexto técnico | `HIDROCARBUROS/perupetro_produccion.md` |
| Transcripciones 1994–2000 | `HIDROCARBUROS/transcripciones/PP_mensual_<año>_transcrito.csv` |
| Drive · DATA | `1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq` (CSV de producción + subcarpeta `PDF` con todos los PDF descargados) |
| Drive · CONTROL | `1TKjS2Wjpnf26oladjhqstmN5c9Irq-Aj` (control por año y `PP_CATALOGO_PDF.csv`) |
| Fuente de los PDF | perupetro.com.pe → Estadísticas → **Estadística Petrolera**: anuales 1994–2025 y mensuales del año en curso. La URL completa está en el Bloque 3 (`PAGINA_EST`) |

**Abrir siempre desde el enlace de Colab.** Una copia guardada en Drive no recibe las correcciones nuevas.

## 3. Qué hace el notebook (3 bloques)

1. **Instalación y extractor.** Usa `pdfplumber` + `pypdf`. Lee la tabla "Producción fiscalizada mensual de hidrocarburos líquidos" **por coordenadas**.
2. **Selectores.** Año inicio y fin; para el año en curso usa la última mensual; opción de guardar los PDF en Drive.
3. **Descarga y control.**
   - Lee los enlaces de la página de PERUPETRO.
   - Completa el certificado HTTPS de PERUPETRO, que viene incompleto: descarga el intermedio desde la dirección AIA del certificado.
   - Descarga los PDF o los reutiliza desde `DATA/PDF`.
   - Extrae, homologa, controla y sube a Drive:
     - `PP_produccion_lote_mes_<ini>-<fin>.csv` (DATA);
     - `CONTROL PP produccion_lote_mes_<ini>-<fin>.csv` (CONTROL).
   - Al final muestra el ranking de Loreto por lote histórico.

**Columnas de los datos:**
- `AÑO`, `MES`, `FECHA` (dd/mm/aaaa)
- `ZONA`, `DEPARTAMENTO`
- `OPERADOR`, `LOTE`, `LOTE_HISTORICO`, `LOTE_ORIGINAL`
- `PRODUCTO` (PETROLEO / LGN / CONDENSADO)
- `BARRILES`, `BPD`
- `ESTADO_FILA`, `FUENTE`

Notas sobre algunas columnas:
- **`LOTE_HISTORICO`** une contratos del mismo campo: `1-AB/192` (el 1-AB terminó el 29/08/2015 y desde el 30/08/2015 es el 192) y `Z-2B/Z-69` (a confirmar). También quita sufijos de contratos temporales como `(T)`.
- **`DEPARTAMENTO`**: por ahora solo `LORETO`, asignado a la zona Selva Norte. El resto se completará con el mapa de lotes.

## 4. Estado de la serie (al 11/10/2026)

| Años | Cómo se obtuvo | Estado |
|---|---|---|
| 2001–2025 | Extracción automática de los PDF anuales digitales | ✅ **OK, diferencia 0 contra los totales del PDF** |
| 2026 (ene–jun) | Mensual de junio 2026 (acumulado del año) | ✅ OK |
| 1994, 1998, 2000 | **Transcritos a mano** desde la imagen (escaneos) y validados con los totales del PDF | ✅ OK (transcrito) |
| **1995, 1996, 1997, 1999** | Escaneos | ⏳ **Pendiente de transcribir**: el usuario debe subir `PP_ANUAL_1995/1996/1997/1999.pdf` desde DATA/PDF |

**Cómo se transcriben los años escaneados.** Es el método para continuar con los pendientes:
1. Ubicar la página "PRODUCCION MENSUAL DE HIDROCARBUROS LIQUIDOS, <año>": 1994 → p.16, 1998 → p.10, 2000 → p.10.
2. Renderizar la página con `pdftoppm -r 300…600` y recortar la tabla en mitad izquierda y mitad derecha para leerla ampliada.
3. Transcribir a un CSV con estas columnas:
   - `ANIO, PRODUCTO, OPERADOR, LOTE_ORIGINAL, LOTE, ENE…DIC, TOTAL, FUENTE`;
   - una fila `TOTAL` al final.
4. Validar con estas reglas, y releer con zoom las celdas que no cuadren:
   - cada lote suma su total;
   - cada mes suma el TOTAL;
   - el gran total coincide con la tabla "por contratista" del mismo PDF.
5. Guardar en `HIDROCARBUROS/transcripciones/`. El notebook las toma solo para los años sin extracción OK.

**Formatos de PDF ya resueltos** por el extractor:
- tablas giradas 90° (2008);
- columna CONTRATISTA y meses abreviados;
- miles con punto (2001);
- títulos variados ("…MENSUAL 2008", "…MENSUAL - 2010", sin "FISCALIZADA" en 2016);
- lotes `31B/31D` → `31-B/D`, `Z - 2B`, `31-C (LGN/COND.)`;
- "Pág. N" pegado a los rótulos.

## 5. Lo que ya muestran los datos (Loreto, petróleo)

- **1-AB/192 es el campo más productivo de la historia de Loreto.** 20,0 MM bbl en 1994, 13,4 en 2000, 8,2 en 2008 y 5,6 en 2012. Desde 2020 está casi paralizado:
  - medidas de fuerza de comunidades nativas (02/2020);
  - fin del contrato de Frontera (02/2021);
  - hoy lo tiene PetroPerú, con producción 0.
- **Lote 8**: 10,6 MM bbl en 1994 y 9,3 en 2000, en caída. Sin producción desde 04/2020 (COVID). Con Upland vuelve a producir en 2026: 0,13 MM bbl en enero.
- **Lote 95 (Petrotal)**: el único que crece. De 0,17 MM bbl en 2018 a 3,2 en 2021. Hoy es el principal de Loreto.
- **Lote 67 (Perenco)**: producción intermitente.
- **Peso de Loreto:** en 1994, Loreto (1-AB + 8) aportaba unos dos tercios del petróleo del país (30,7 de 46,5 MM bbl).

Para la región, la **zona Selva Norte = Loreto**. Infotrade asigna la región probablemente por ubigeo de producción; ver `EXPORT/exportaciones_scraper_infotrade.md`.

## 6. Pendientes, en orden sugerido

1. **Transcribir 1995, 1996, 1997 y 1999** con el método de §4. Pedir los PDF al usuario.
2. **Mapa de lotes.** PERUPETRO publica un mapa en ArcGIS Online (https://perupetro.maps.arcgis.com/apps/webappviewer/index.html?id=cc883917c55a4264a01debfa02585e2e). De ahí salen los polígonos de los lotes, el departamento de cada uno y las variables geográficas: cuenca, distancia al Oleoducto Norperuano, ríos, áreas protegidas.
3. **Otras tablas de los anuales**, ya identificadas en los PDF:
   - producción por **yacimiento**;
   - **estado de pozos** por lote;
   - **regalías por lote** ("Ingresos al fisco por contrato");
   - **precio de la canasta** por lote;
   - **canon y sobrecanon** por departamento;
   - **contratos** (fechas y área).
4. **Cruce con Infotrade.** Exportación de crudo (partida 2709) de Loreto vs producción; operador ↔ exportador.
5. **Banco de Datos de PERUPETRO.** El usuario tiene cuenta, para pozos y sísmica:
   - credenciales en **Colab → Secretos**, nunca en el código;
   - antes hay que revisar las condiciones de uso y capturar con F12 → Network las peticiones al abrir las capas Pozos/Lotes.

## 7. Cosas a tener en cuenta

- **Conexión:** perupetro.com.pe está **bloqueado** desde el entorno de Claude, pero funciona desde Colab. Por eso las pruebas de Claude se hacen con PDF subidos por el usuario y simulaciones.
- **Servidor lento:** PERUPETRO a veces da `ConnectTimeout`. El notebook reintenta 3 veces y, si falla, anota `ERROR DE DESCARGA`; basta con volver a ejecutar.
- **Página de estadísticas:** incluye un documento legal (reglamento de participación ciudadana) que se excluye.
- **Preferencias del usuario:**
  - español;
  - fechas en **dd/mm/aaaa**;
  - todo cambio va por **PR y merge a `main`**;
  - los `.md` de contexto se mantienen al día;
  - los resultados van a Drive, no se descargan con `files.download`.

## 8. Cómo continuar en un chat nuevo

Pegar algo como:

> Continúa el **Proyecto Petróleo** del repositorio `adriansivina-droid/scraper-mef`. Lee `HIDROCARBUROS/proyecto_petroleo.md` y `HIDROCARBUROS/perupetro_produccion.md`. Trabaja en la rama `claude/scraper-gobiernos-regionales-kk6ecm`, haz PR y merge a `main`. Siguiente tarea: [por ejemplo, transcribir 1995–1999 / mapa de lotes / regalías por lote]. Te subo los PDF que necesites.

Otros proyectos del mismo repositorio:
- `FISCAL/`: scrapers MEF Consulta Amigable (ver `FISCAL/CONTEXTO_PROYECTO.md`).
- `EXPORT/`: scraper Infotrade y diccionario de partidas arancelarias (ver `EXPORT/exportaciones_scraper_infotrade.md`).
