# Proyecto Petróleo · Loreto · Resumen para continuar en otro chat

Resumen ejecutivo del proyecto de producción petrolera. Sirve para retomarlo en una sesión nueva sin perder el contexto. El detalle técnico del extractor está en `HIDROCARBUROS/perupetro_produccion.md`. Última actualización: **20/10/2026**.

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
 Producción        Mapa de lotes          Infotrade              Canon
 lote × mes        polígonos, distritos,  exportación 2709       por lote, beneficiario
 (HECHO)           indicadores (HECHO);   (scraper listo,        y municipalidad
                   Banco de Datos         cruce pendiente)       (HECHO, Excel de
                   (PENDIENTE)                                    PERUPETRO)
```

## 2. Dónde está todo

| Qué | Dónde |
|---|---|
| Repositorio | `adriansivina-droid/scraper-mef` (público), carpeta `HIDROCARBUROS/` |
| Notebook de producción | `HIDROCARBUROS/PP_Produccion_Lotes.ipynb` |
| Notebook del mapa de lotes | `HIDROCARBUROS/PP_Mapa_Lotes.ipynb` → [Colab](https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Mapa_Lotes.ipynb) · detalle en `HIDROCARBUROS/mapa_lotes.md` |
| Mapa con plugins (fondos CARTO, nombres, buscador, pantalla completa, minimapa, medición, línea de tiempo animada) | `HIDROCARBUROS/PP_Mapa_Lotes_Plus.ipynb` → [Colab](https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Mapa_Lotes_Plus.ipynb) · `DATA/MAPA/PP_mapa_lotes_plus.html` |
| Abrir en Colab | https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/PP_Produccion_Lotes.ipynb |
| Producción **diaria** (líquidos y gas, por lote) | Sección 8 del Bloque 3 del notebook de producción (casilla «Producción diaria») → `DATA/PP_produccion_diaria.csv` |
| Gas natural fiscalizado por lote y mes (1994–hoy) | `DATA/PP_produccion_gas_lote_mes_<ini>-<fin>.csv` (notebook de producción) |
| Pozos perforados por lote (1995–hoy), regalías por lote (2001–hoy), canon por departamento (1993–hoy), precio de canasta por lote y mes (2001–hoy) y valor de la producción | `DATA/PP_pozos_perforados_lote_anio.csv`, `PP_regalias_lote_anio.csv`, `PP_canon_departamento_anio.csv`, `PP_precio_canasta_lote_mes.csv`, `PP_valor_produccion_lote_mes.csv` (notebook de producción, sección 6.1; detalle en `perupetro_produccion.md`) |
| Contexto técnico | `HIDROCARBUROS/perupetro_produccion.md` |
| Canon (Excel de PERUPETRO: Determinación, Distribución y Municipalidades) | Sección 9 del notebook de producción → `DATA/CANON_EXCEL/` y `DATA/PP_canon_lote_mes.csv`, `PP_canon_distribucion_mes.csv`, `PP_canon_municipal_mes.csv`; serie oficial `PP_canon_departamento_mes.csv` y `_anio.csv` (los `_pdf.csv` son control) |
| Textos y evidencia (Loreto y Ucayali 2025) | `HIDROCARBUROS/analisis/` (.md, .docx y .xlsx) |
| Indicadores por lote (estado, pico, declinación, paralizaciones, operadores) | `DATA/PP_LOTES_INDICADORES.csv` (notebook del mapa) |
| Diccionario de datos (PDF) | `HIDROCARBUROS/docs/Diccionario_datos_Proyecto_Petroleo.pdf` (se regenera con `python3 HIDROCARBUROS/docs/mk_diccionario.py`) |
| Diccionarios Word (APA 7) de la carpeta DATA | `HIDROCARBUROS/docs/diccionarios/`: `00_Diccionario_general_DATA.docx` (para qué sirve cada archivo y si es útil, control o redundante) y un `.docx` por archivo con sus variables; se regeneran con `node HIDROCARBUROS/docs/diccionarios/mk_diccionarios_docx.js` |
| Transcripciones 1994–2000 | `HIDROCARBUROS/transcripciones/PP_mensual_<año>_transcrito.csv` (líquidos) y `PP_gas_mensual_<año>_transcrito.csv` (gas) |
| PDF escaneados pesados | `HIDROCARBUROS/pdf_escaneados/` (1995 y 1996, demasiado grandes para el chat) |
| Drive · DATA | `1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq` (CSV de producción + subcarpeta `PDF` con todos los PDF descargados) |
| Drive · CONTROL | `1TKjS2Wjpnf26oladjhqstmN5c9Irq-Aj` (control por año y `PP_CATALOGO_PDF.csv`) |
| Geoportal PERUPETRO (mapas oficiales, WFS) | https://geoportal.perupetro.com.pe — servicio `https://geoportal.perupetro.com.pe/geoserver/wfs` (capa de lotes `cartografia_pp:lote_contrato`) |
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
- **`LOTE_HISTORICO`** une contratos del mismo campo: `1-AB/192` (el 1-AB terminó el 29/08/2015 y desde el 30/08/2015 es el 192) y `Z-2B/Z-69` (a confirmar) y `31-B/D` (Maple: hasta 2000 el PDF separa 31-B Maquía y 31-D Agua Caliente). También quita sufijos de contratos temporales como `(T)`.
- **`DEPARTAMENTO`**: sale del mapa de lotes (`PP_LOTES_GEO.csv`, polígonos INGEMMET de enero 2019). Si el lote no tiene polígono, se usa la zona (Selva Norte → Loreto). `DEPARTAMENTO_FUENTE` indica cuál de las dos se usó.

## 4. Estado de la serie (al 11/10/2026)

| Años | Cómo se obtuvo | Estado |
|---|---|---|
| 2001–2025 | Extracción automática de los PDF anuales digitales | ✅ **OK, diferencia 0 contra los totales del PDF** |
| 2026 (ene–jun) | Mensual de junio 2026 (acumulado del año) | ✅ OK |
| 1994–2000 | **Transcritos a mano** desde la imagen (escaneos) y validados con los totales del PDF | ✅ OK (transcrito) |
| Gas natural 2001–2026 | Extracción automática de la tabla «Producción fiscalizada mensual de gas natural (MPC)» | ✅ OK (≤ 2 MPC de diferencia por redondeo) |
| Gas natural 1994–2000 | **Transcrito a mano** (12/10/2026) y validado: filas, meses y total general cuadran exacto | ✅ OK (transcrito) |
| Producción diaria | Reportes diarios de la página «Producción Diaria» (líquidos en bbl, gas en Mcf y MMBtu), desde el año en curso; se acumula en Drive | ✅ Probado con setiembre 2026: 30/30 días cuadran con el TOTAL del PDF |

**Cómo se transcribieron los años escaneados** (método por si aparece otra tabla escaneada):
1. Ubicar la página "PRODUCCION MENSUAL DE HIDROCARBUROS LIQUIDOS, <año>": 1994 → p.16, 1995 → p.18 (y cuadro de control en p.17), 1996 → p.16, 1997 → p.10, 1998 → p.10, 1999 → p.10, 2000 → p.10.
   Gas («PRODUCCION FISCALIZADA MENSUAL DE GAS NATURAL», en KPC = MPC): 1994 → p.53, 1995 → p.82, 1996 → p.71, 1997 → p.38, 1998 → p.38, 1999 → p.39, 2000 → p.38. Si el PDF trae capa OCR (1997, 1999), sirve de borrador, pero se valida igual contra la imagen.
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

**Serie nacional 1994–2026** (archivo CONTROL de la corrida completa del 11/10/2026):

- **Validación cruzada:** el promedio diario calculado coincide con el que imprime el PDF (1995: 121.762 bpd; 1997: 118.239 bpd).
- **Petróleo:** pasa de 46,5 MM bbl (127 mil bpd) en 1994 a 14–16 MM bbl (unos 40 mil bpd) desde 2020, una caída del 68 %.
- **Caídas bruscas:**
  - 2016: −30 %, por la paralización del Oleoducto Norperuano tras sus roturas, que dejó sin salida al 192 y al 8;
  - 2020: −25 %, por el COVID y el cierre del 192.
- **2026 (enero–junio):** unos 36 mil bpd, 18 % menos que el promedio de 2025, sobre todo por menor producción del Lote 95.
- **LGN:** salta en 2004–2005 con Camisea y desde 2009 supera al petróleo; hoy es cerca de dos tercios de los líquidos del país.
- **Peso de Loreto** en el petróleo nacional, sumando 1-AB/192, 8, 95, 67 y 102:
  - 66 % en 1994;
  - 65 % en 2000;
  - 23–28 % en 2018–2021;
  - 49 % en 2025, por el crecimiento del 95.

  Es provisional: el departamento de cada lote se confirmará con el mapa.

## 6. Pendientes, en orden sugerido

0. **Hecho al 20/10/2026** (detalle en la sección 9 y en `mapa_lotes.md`): canon por lote, beneficiario y municipalidad (puntos 1–5); mapa de lotes con corrida real (geoportal de PERUPETRO, provincias de geoBoundaries y distritos de GADM 4.1 como respaldo), pestañas de pozos, regalías, canon y empresas, selector de año, unidades en «millones»; diccionarios Word de DATA; texto de Loreto en Word.
1. **Mapa de lotes**: ✅ corrida real hecha (20/10/2026). Pendiente menor: la dirección de respaldo de geoBoundaries en GitHub da 404 (no afecta: entra GADM); los distritos de GADM son límites de 2022 y no los oficiales del INEI.
2. **Otras tablas de los anuales.**
   - HECHO (13/10/2026):
     - **pozos perforados** por lote y tipo;
     - **regalías** por lote;
     - **canon y sobrecanon** por departamento;
     - **precio de canasta** por lote y mes, y con él el **valor de la producción**.
   - Falta la primera corrida real desde 2001 en Colab.
   - Hecho después: **contratos** (fechas, socios, área; `PP_contratos.csv`) e historial de operadores (`PP_operadores_lote.csv`).
   - Pendientes:
     - producción por **yacimiento**;
     - **estado de pozos** por lote.
   - La **inversión en US$ por lote no está en los anuales**; habría que buscarla en otra fuente (memorias de PERUPETRO, MINEM).
   - **Regalías 1994–2000: no existen en los anuales.** Revisé los índices de los 7 escaneados: pasan de «Canasta» a «Canon» y «Contratos»; el cuadro «Ingresos por contratos» aparece recién en la edición 2001. Alternativas: memorias anuales de PERUPETRO de esos años, o transcribir la canasta 1994–2000 (sí está, sección 6) para tener el valor de la producción.
3. **Cruce con Infotrade.** Exportación de crudo (partida 2709) de Loreto vs producción; operador ↔ exportador.
4. **Banco de Datos de PERUPETRO.** El usuario tiene cuenta, para pozos y sísmica:
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

## 7b. Análisis Loreto 2025 (estilo BCRP)

- `analisis/Loreto_petroleo_2025_texto.md`: texto «3. Extracción de petróleo, gas, minerales y servicios conexos» para Loreto 2025, con la estructura del informe del BCRP (1. tendencia de diez años, VAB INEI e historia 2015–2020; 2. lotes en operación; 3. Lote 95, precios, regalías, canon, reservas y riesgos), más «Empresas que operan en Loreto» (PetroTal, Upland, Petroperú y Perenco). Al final, un anexo con la versión ampliada por tema.
- `analisis/Loreto_petroleo_2025_evidencia.xlsx`: datos de respaldo con fórmulas; hoja `VAB_INEI` transcrita de los cuadros 1 y 2 del INEI (información a junio del 2026; 2024P, 2025E), con control contra el total publicado; hoja `VAB_INEI_2014_2025` (serie del INEI), hoja `Empresas_Loreto` (contratos vigentes y producción por operador 2006–2025) y hoja `Serie_Loreto_2006_2025` con la producción de Loreto y del país y las reservas probadas de la zona Selva.
- Desde el 20/10/2026 el texto de Loreto incluye el subtítulo **«Canon y sobrecanon petrolero en Loreto»** (canon por lote: Lote 95 = 83,7 % y Lote 8 = 16,4 % de lo que recibió Loreto en US$; reparto por beneficiario con la Ley N° 31934; municipalidades ene–set 2025: Requena 47 %, Puinahua 16,2 %) y está también en Word: `analisis/Loreto_petroleo_2025_texto.docx` (generador `analisis/mk_docx_loreto.js`). Evidencia en la hoja `Canon_lotes_2025` (generador `analisis/mk_evid_canon_loreto.py`).
- `analisis/Ucayali_petroleo_2025_texto.md` (19/10/2026): la misma sección para Ucayali, en texto continuo sin subtítulos (pedido del usuario): VAB del INEI (cuadro 1 de Ucayali 2015–2025: −12,2 % promedio anual, 8,2 % → 1,9 % de la economía regional, −18,2 % en 2025, −0,4 p.p. al crecimiento de 2,5 %), lotes 31-C (Aguaytía) y 131 (Ucawa Energy), sus contratos, regalías y canon por lote de origen y por beneficiario.
- `analisis/Ucayali_petroleo_2025_evidencia.xlsx`: respaldo con fórmulas (producción 31-C y 131 2016–2025, regalías 2024–2025, canon 2016–2026 por mes y beneficiario, canon 2025 por lote de origen desde la Determinación, VAB INEI 2015–2025 y participación nacional, contratos). Generador: `mk_evid_ucayali.py` (scratchpad). Hallazgo: el 80,9 % del canon de Ucayali 2025 viene del Lote 95 (Loreto), porque la Determinación da a Ucayali el 20 % del canon de los lotes de Loreto; el canon del Lote 131 va a Puerto Inca (Huánuco) aunque el 57,5 % de su área está en Ucayali.

## 8. Cómo continuar en un chat nuevo

Pegar algo como:

> Continúa el **Proyecto Petróleo** del repositorio `adriansivina-droid/scraper-mef`. Lee `HIDROCARBUROS/proyecto_petroleo.md` y `HIDROCARBUROS/perupetro_produccion.md`. Trabaja en la rama `claude/scraper-gobiernos-regionales-kk6ecm`, haz PR y merge a `main`. La sección 9 (canon) está terminada; siguientes tareas posibles en la sección 6 (cruce con Infotrade, Banco de Datos, yacimientos) o las que pida el usuario. Te subo los PDF o Excel que necesites (si no se pueden adjuntar, los subo a GitHub en una rama aparte).

Otros proyectos del mismo repositorio:
- `FISCAL/`: scrapers MEF Consulta Amigable (ver `FISCAL/CONTEXTO_PROYECTO.md`).
- `EXPORT/`: scraper Infotrade y diccionario de partidas arancelarias (ver `EXPORT/exportaciones_scraper_infotrade.md`).

## 9. Siguiente tarea: canon por lote, por beneficiario y por municipalidad (pendiente, 18/10/2026)

**Estado:** punto 1 (descarga) implementado y verificado en Colab (19/10/2026); punto 2 (lectores) implementado y verificado con la corrida real del 19/10/2026 (tres correcciones del lector; ver `perupetro_produccion.md`); punto 3 (serie oficial desde la Distribución) implementado el 19/10/2026; punto 4 (pestaña «Canon» del mapa) implementado el 20/10/2026 y verificado en la corrida real (distritos de GADM); punto 5 (texto y evidencia) hecho el 20/10/2026.

**Forma de los Excel de Municipalidades (revisados el 19/10/2026; sirven para el lector del punto 2):**
- Todos son hojas «de reporte», no tablas. La hoja con datos se llama como el año («2025»). Piura trae además «Indices» y «Hoja1»; Tumbes, «Indices Anuales», «Graficos» e «Indices Institutos».
- Bloque 1 (filas ~1–13), «DISTRIBUCION DE LA PARTICIPACION»: gobierno regional, institutos, universidades y MUNICIPALIDADES con su %, más el TOTAL PARTICIPACION. Columnas: PERIODO DE PAGO (Ene.2025…) y FECHA DE PAGO.
- Bloque 2 (desde la fila ~18), «… A GOBIERNOS REGIONALES, LOCALES Y COMUNIDADES (Validado con la PCM)»: gobierno regional (con el 10 % para comunidades), universidades e institutos, y «CANON Y SOBRECANON – GOBIERNOS LOCALES» por municipalidad provincial y distrital.
- Las cabeceras no son uniformes: «DEPARTAMENTO DE LORETO: D.LEY 21678», «DEPARTAMENTO CUSCO», «PROVINCIA PUERTO INCA HUANUCO : LEY 24977» (el de Huánuco es solo la provincia de Puerto Inca). En el de Tumbes, el bloque 2 dice por error «DEPARTAMENTO DE PIURA : LEY 23630»: el lector debe tomar el departamento del nombre del archivo o de la primera cabecera, no de la segunda.
- **Ucayali no tiene Excel municipal propio.** «Canon por Año Ucayali» (`…/f8441c1d-287a-4817-a2fe-34c3013f6c4d/CANON+POR+A%C3%91O+UCAYALI.xlsx`) es un Excel de Distribución. Si la página de Municipalidades también lo lista, es el mismo archivo: el cuaderno no repite direcciones, por eso contó 5. Confirmado en la corrida del 19/10/2026: la página de Municipalidades no enlaza Ucayali. Su «Canon por Año Ucayali» (copia en `fuentes_canon/Canon_por_anio_Ucayali.xlsx`, 154 336 bytes, el mismo tamaño que `PP_CANON_DISTRIBUCION_UCAYALI.xlsx` en Drive) es de Distribución. Trae 34 hojas (1993–2026) con el bloque «DISTRIBUCION DEL SOBRE CANON (LEY 23350) Y CANON (D.U. 027-98) — DEPARTAMENTO UCAYALI»: Región Ucayali, institutos, universidades, IIAP y «CONCEJOS MUNICIPALES (*)». Igual que Loreto, **1993–2002 trae el detalle por concejo** («DISTRIBUCION POR CONCEJOS»: Coronel Portillo 48,47 %, Callería…); de 2003 en adelante, solo el monto municipal total. Para Ucayali no hay detalle municipal del año en curso. La columna de % trae rangos de texto («52% - 20%», «40% - 70%»).

### Fuentes (PERUPETRO, web «Estadísticas»; no están en los PDF anuales)

| Página | Archivo | Contenido | Revisión |
|---|---|---|---|
| Canon y Sobre Canon → **Determinación** | «Canon Petrolero 2007…2026» (un Excel por año; copias de 2025 y 2026 en `HIDROCARBUROS/fuentes_canon/Determinacion_canon_2025.xlsx` y `_2026.xlsx`) | **Canon por lote y mes**: una hoja por mes (Ene…Dic, TOTAL; hay hojas extra como «Abr (2)», «Ene-2», «Recuperado_Hoja1», «cuadre», «Nov-original» que se deben ignorar). Por zona (Piura/Tumbes, Puerto Inca-Huánuco, Loreto/Ucayali, Cusco): lote, modalidad, período (Quincena/Mes), fórmula (F1–F4), unidades (Bls / MM BTU), volumen 1.ª y 2.ª quincena, canasta, deducciones (flete, comercialización, oleoducto, fiscalización), **valor de la producción (US$)**, **canon y sobrecanon total (US$)** y la parte de cada departamento («Localidad 1» = Loreto); subtotal en US$ y en S/ (tipo de cambio en la fila 5). | Ene-2025: Loreto/Ucayali, Lote 95 = valor US$ 40,40 MM, canon US$ 7,58 MM, parte de Loreto US$ 6,06 MM (80 %); **subtotal Loreto S/ 23.157.055 = canon mensual de Loreto ene-2025 (23,16 MM) ✔**. |
| Canon y Sobre Canon → **Distribución** | «Canon por Año <Dep.>» (Ucayali, Piura, Huánuco, Tumbes, Loreto, Cusco); copia de Loreto en `fuentes_canon/Canon_por_anio_Loreto.xlsx` | Una hoja por año, **1993–2026**: canon de cada mes, fecha de pago y reparto por beneficiario (gobierno regional, instituto tecnológico, universidades, IIAP, concejos municipales, Ley 29289) con su %. **1993–2002 trae además el detalle por municipalidad**; 2003+ solo el total municipal. % por norma: 52/5/3/40 hasta 2023; 20/2/2,5/2,5/3/70 desde la Ley 31934 (30/01/2024). | Loreto: total anual = canon de los PDF anuales en **1995–2024 (diferencia 0)**; 2025 = 213,84 MM (confirma la corrección por suma mensual); agrega 1993–1994 y 2026 ene–jul (125,37 MM). |
| **Canon Municipalidades** | «Canon por Año <Dep.>» (Cusco, Huánuco, Loreto, Tumbes, Piura); copia de Loreto en `fuentes_canon/Canon_municipalidades_Loreto_2025.xlsx` | Año en curso (el de Loreto trae solo 2025): gobierno regional, universidades, IIAP y **las 53 municipalidades provinciales y distritales** de Loreto, + 5 % comunidades (D.U. 026-2010). | Ene–ago 2025 = serie mensual al centavo; set (Ucayali en 0) y oct (municipios en 0) incompletos. Puinahua (distrito del Lote 95) S/ 20,0 MM ene–set 2025 = 16 % de lo municipal; provincia de Requena 47 %. |

Dirección de la página «Canon y Sobre Canon» (Determinación y Distribución), dada por el usuario:
`https://www.perupetro.com.pe/wps/portal/corporativo/PerupetroSite/estadisticas/canon%20sobre%20canon/!ut/p/z1/pZJNDoIwEEbP4gmmrW1hS6PyEypgMMBsDCvTRNGF8fxSdOOCwcRZtcl7mZmvBYQWcOif7tw_3G3oL-O9Q33ai61MEsmzuLQhq2S9yerxYIyGZgLYTEUMkPAT9fFngEpoyue5pH0PEP6BC9r3ADW_XfA98OUXcblj2lijyjRkYb6wvw8If8mfaPBP_r4B0s_bAC4hSM2gC0UD0x8ggNgEggYCsYb79fiulrnURasX6dHDBQ!!/dz/d5/L2dBISEvZ0FBIS9nQSEh/`. La de «Canon Municipalidades» está en el mismo menú (Estadísticas → Canon Municipalidades).

**Cómo descargarlos (acordado):** sección nueva del notebook de producción que lee la página desde Colab (Colab sí accede), toma los enlaces a Excel (`/wps/wcm/connect/…?MOD=AJPERES`), los clasifica por el texto («Canon Petrolero <año>» → Determinación; «Canon por Año <Dep.>» → Distribución o Municipalidades), descarga con pausas y guarda en Drive (`PP_CANON_DETERMINACION_<año>.xlsx`, `PP_CANON_DISTRIBUCION_<DEP>.xlsx`, `PP_CANON_MUNICIPAL_<DEP>.xlsx`); en corridas siguientes solo baja el año en curso. Imprime un control con los enlaces encontrados y su clasificación. Respaldo: carpeta de Drive `DATA/CANON_EXCEL` con los archivos puestos a mano.

Desde la sesión de Claude Code **no se puede abrir perupetro.com.pe** (el proxy da 403): los archivos se suben al repositorio (GitHub → Add file → Upload files, en una rama aparte) o se descargan desde Colab. La rama `fuentes-canon` del usuario ya se copió a `HIDROCARBUROS/fuentes_canon/` y se puede borrar.

### Propuesta (5 puntos)
1. ✅ **Implementado (19/10/2026, sección 9 del notebook de producción; ver `perupetro_produccion.md`). Verificado en Colab el 19/10/2026: 34 de Determinación (1993–2026), 6 de Distribución (Cusco, Huánuco, Loreto, Piura, Tumbes, Ucayali) y 5 de Municipalidades (Cusco, Huánuco, Loreto, Piura, Tumbes: el de Ucayali es el mismo archivo de Distribución. Ucayali sí está en Distribución, con detalle por concejo solo en 1993–2002), sin pendientes en el control. Los enlaces de Municipalidades no tienen texto y se clasifican por la cabecera del Excel (PR 113–114).** **Descarga** en el notebook de producción (sección nueva) de los Excel de Determinación (2007–hoy), Distribución (6 dep.) y Canon Municipalidades (5 dep.), guardados en Drive con fecha; respaldo: carpeta de Drive con los archivos puestos a mano.
2. ✅ **Implementado (19/10/2026; detalle y prueba en `perupetro_produccion.md`, «Lectura de los Excel de canon»). Verificado con los 45 Excel reales (19/10/2026): todos los controles internos OK salvo Loreto set‑2025 (error del Excel); quedan 10 meses y 4 años con diferencias entre fuentes de PERUPETRO, documentadas.** **Lectores**: `PP_canon_lote_mes.csv` (año, mes, departamento, lote, producto, volumen, canasta, deducciones, valor US$, canon US$, parte por departamento, tipo de cambio), `PP_canon_distribucion_mes.csv` (1993–hoy, por beneficiario) y `PP_canon_municipal_mes.csv` (1993–2002 + año en curso, acumulado en Drive). Control: lotes = subtotal de zona; S/ = serie mensual; total anual = PDF anual.
3. ✅ **Implementado (19/10/2026; ver «Serie oficial de canon por departamento» en `perupetro_produccion.md`).** La serie de canon por departamento (`PP_canon_departamento_mes/anio.csv`) usa los totales mensuales de la Distribución (1993–hoy); lo de los PDF queda en `*_pdf.csv` como control. El mapa muestra solo años completos.
4. ✅ **Implementado y verificado en la corrida real (20/10/2026; ver `mapa_lotes.md`, «Punto 4»): 196 provincias (geoBoundaries) y 1815 distritos (GADM 4.1, porque la API de geoBoundaries cortó la conexión); el Lote 95 cruza con Tapiche, Soplín, Emilio San Martín, Puinahua, Capelo, Alto Tapiche y la provincial de Requena. En el gráfico por beneficiario, la «Ley 29289» se muestra en gris como «Descuento: pago de deuda (Ley 29289)» (contrapartida nacional y servicio de deuda, Loreto 2009–2023).** **Mapa**: pestaña «Canon» con el canon **del lote** (de Determinación), el del departamento por beneficiario y el de provincia/distrito del lote (requiere la capa de distritos INEI).
5. ✅ **Hecho (20/10/2026): subtítulo «Canon y sobrecanon petrolero en Loreto» en `analisis/Loreto_petroleo_2025_texto.md` (y hoja Texto_2025) y hoja `Canon_lotes_2025` del libro de evidencia (generada con `analisis/mk_evid_canon_loreto.py` desde los Excel reales). El Excel de Determinación 2024 rotula el Lote 8 como «MM BTU» aunque es petróleo (error de la fuente).** **Texto y evidencia** Loreto 2025: canon generado por el Lote 95 y el Lote 8, reparto por beneficiario, Puinahua y Requena; hoja nueva en el libro de evidencia.

### Otros pendientes menores
- ✅ Ejes de los gráficos de pozos/regalías/canon: años encimados, corregido.
- Archivos `PP_produccion_lote_mes_2026-2026.csv` y `PP_produccion_gas_lote_mes_2026-2026.csv` en DATA: redundantes (salen de correr solo 2026). Correr producción siempre con 1994-2026, que es el archivo que usa el mapa; propuesta pendiente: que una corrida parcial actualice también el archivo completo.
- Excel de Determinación 2024: el Lote 8 figura con unidad «MM BTU» aunque es petróleo (error de la fuente; no afecta 2025).
- Ley 29289: falta identificar qué deuda o proyecto se pagaba (el Excel no lo dice).
- **Canon por municipalidad 2005–2024 (20/10/2026):** fuente encontrada con el usuario: MEF, **Consulta Amigable de Ingresos** (`https://apps5.mineco.gob.pe/transparenciaingresos/mensual/`), ruta Fuente 5 → Rubro 18 → Tipo de recurso «5: Canon y sobrecanon petrolero» y «K: Sub cuenta – …» → Nivel M → Departamento 16 → Municipalidad. Detalle por municipalidad: **2003–2004 no** (el canon petrolero municipal figura a nombre del Consejo Nacional de Descentralización; con el tipo «0: NORMAL» solo aparecen gobiernos regionales: GR Loreto 2003 S/ 107,2 millones, todos los canones, frente a S/ 98,2 millones de canon petrolero según PERUPETRO); **2005–2006 sí**, pero con otra clasificación (fuente 01 → tipo «0: NORMAL», todos los canones: municipalidades de Loreto 2005 S/ 75,0 millones frente a S/ 98,8 millones de PERUPETRO); **desde 2007** homogéneo (fuente 5 → rubro 18 → tipos 5 y K). Esto coincide con la nota de los Excel de Distribución: «distribución a municipalidades a través del CND / Secretaría de Descentralización – PCM». Lector **con `requests`, sin navegador, navegando el formulario** (21/10/2026): los filtros puestos en la URL se ignoran, también en la de «Exportar» (`_tgt=xls`). Pruebas manuales del usuario con `Navegar_1` y `Navegar_6` (2026, `0=&10=5&11=`): la exportación devolvió el total del país (S/ 105 668 millones) con los 151 tipos de recurso de todas las fuentes. Por eso el lector hace lo mismo que el navegador: abre `default.aspx?y=AAAA`, toma el marco `Navegar_N.aspx` del año (2026 = 6) y en cada paso envía el formulario ASP.NET (`__VIEWSTATE`, `__EVENTVALIDATION`, `grp1` = valor del radio de la fila elegida y el botón de la dimensión siguiente). Cada página se guarda y se reenvía para ramificar (otro nivel u otro departamento), y cada paso se valida con el historial y la cabecera. Código en `mef/lector_mef.py`, simulador `mef/mock_mef.py`. Capturas del usuario (21/10/2026): **2003** no tiene botón «Nivel de Gobierno» ni PIA/PIM. Ruta: Fuente 01 → Tipo 4 → Sector 01 PCM → Pliego 013 CND → UE 001-1069, con S/ 166 368 386; el notebook registra ese reparto por sector y pliego. **2005** (fuente «01: CANON Y SOBRECANON») y **2006** (fuente «01: CANON, SOBRECANON, REGALIAS Y PARTICIPACIONES»): con tipo 0 NORMAL, la página de nivel ofrece «Departamento». **2008–2009**: el tipo 0 CANON sí ofrece Nivel M → Departamento (Provincia / Municipalidad), pero no sirve como respaldo: los gobiernos locales de Loreto reciben solo S/ 1 178 540 (2008) y S/ 193 427 (2009). El canon petrolero va por los tipos 5 y K, así que desde 2007 no se usa el tipo 0. **2024** (tipo 0 CANON): la ruta es Nivel M → «Gob.Loc./Mancom.» M: MUNICIPALIDADES → Departamento → Municipalidad, la misma que usa el lector en los años recientes. La página principal de 2003 (`default.aspx?y=2003`) usa `<frame src="Navegar.aspx?y=2003">`, sin número; los años recientes usan `<iframe>` hacia `Navegar_N`. En 2008, Tipo K → M → Departamento muestra a Loreto con S/ 97 371 376 (captura del usuario): el detalle de 2007–2011 existe, y el lector no lo veía porque no enviaba el año del formulario (`DrpYear`). **Serie anual completa (21/10/2026, Loreto):** todos los controles en OK.

| Años | Detalle municipal | MEF / PERUPETRO |
|---|---|---|
| 2003–2004 | sin detalle | — |
| 2005 | 53 filas, S/ 75,87 millones (tipo 4 S/ 0,91 + NORMAL S/ 74,96) | 0,77 |
| 2006 | 51 filas, S/ 168,56 millones | 1,48 |
| 2007 | 51 filas, S/ 72,25 millones | 0,61 |
| 2008 | 102 filas (K + 5), S/ 168,91 millones | 1,26 |
| 2009–2026 | — | entre 0,96 y 1,66 |

Pendiente: ver si en 2008 los tipos K (Loreto S/ 97,37 millones) y 5 son ingresos distintos o el mismo monto registrado dos veces. **Versión mensual**: `DETALLE = "Anual y mensual"` agrega `PP_canon_municipal_mef_mes.csv` (ruta Tipo → Nivel M → [Gob. local] → Mes → Departamento → Municipalidad) y `PP_canon_nivel_gobierno_mef_mes.csv` (Tipo → Mes → Nivel); control en `CONTROL PP canon_mef_mes.csv` (suma de meses = año). **Gobiernos regionales desde 2012 (21/10/2026).** En `Navegar_6`, bajo «Gobiernos Regionales» no hay botón «Departamento», solo «Sector» y «Gob.Loc./Mancom.». Por eso la primera corrida no tuvo el nivel R por departamento desde 2012. El lector ahora baja por Sector → Pliego y asigna cada pliego al departamento que nombra («Gobierno Regional del Departamento de Loreto»). Hay que volver a correr 2012–2026. El gobierno nacional (E) solo se desagrega por departamento en 2007–2011; el mapa no lo muestra en la vista por departamento. **Cusco (21/10/2026):** se mantiene entre los 6 departamentos, con su canon **gasífero** (Camisea). Para Cusco el lector toma también los tipos de canon gasífero del MEF, cada fila con su tipo; en el mapa aparecen con la fuente «MEF … canon gasífero». Para los demás departamentos sigue solo el canon petrolero. Antes del detalle municipal registra la **distribución por nivel de gobierno** (E, M, R; total país y por departamento) → `DATA/PP_canon_nivel_gobierno_mef_anio.csv`, control `CONTROL PP canon_nivel_gobierno_mef.csv` (suma de niveles = total del tipo). Código en `HIDROCARBUROS/mef/lector_mef.py` (simulador `mef/mock_mef.py`; generador del notebook `mef/mk_nb_mef.py`) → `DATA/PP_canon_municipal_mef_anio.csv` y `CONTROL/CONTROL PP canon_municipal_mef.csv` (vs. total de Loreto en el MEF y vs. total municipal de PERUPETRO). Pendiente: primera corrida real. Primer cotejo manual 2007: tipo 5, municipalidades de Loreto S/ 72,2 millones recaudados frente a S/ 118,0 millones transferidos por PERUPETRO (a explicar con la corrida: fechas, tipo K u otros registros).

## Actualización automática (22/10/2026)

GitHub Actions corre los notebooks sin Colab:
- **Diario (06:17, hora de Lima):** producción → mapas.
- **Mensual (día 5):** además, el canon municipal del MEF del año anterior y el actual.

Guarda en las mismas carpetas de Drive. Usa una credencial OAuth de Drive del usuario en el secreto `GOOGLE_DRIVE_CREDENCIAL`. No se usa una cuenta de servicio porque las cuentas de servicio no tienen espacio propio para crear archivos en un Drive personal. Detalle y pasos en `HIDROCARBUROS/automatizacion/README.md`.
