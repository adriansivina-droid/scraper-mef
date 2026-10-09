# Scraper de Exportaciones · Infotrade (PROMPERÚ) · Contexto del proyecto

Documento de traspaso de este proyecto, para retomarlo sin perder contexto, sea una persona o una sesión nueva de un asistente. Es **independiente** de los scrapers del MEF, que se describen en `FISCAL/CONTEXTO_PROYECTO.md`. Última actualización: **09/10/2026**.

---

## 1. Objetivo

Descargar el detalle de **exportaciones del Perú** (datos de SUNAT) desde Infotrade de PROMPERÚ, por región, sector y subsector, desde **2005** como mínimo, y dejarlo en CSV en Google Drive para alimentar un BI.

- **Página:** https://infotrade.promperu.gob.pe/reporte-exportaciones ("Descarga de información de exportaciones").
- Requiere cuenta de usuario para entrar a la web.
- La tabla que muestra la web es **incompleta** (paginada); la información completa se obtiene con **"Exportar a Excel"**.
- **Restricción de la web:** cada consulta abarca **6 meses como máximo**.

**Repositorio:** `adriansivina-droid/scraper-mef` · **Notebooks:** `EXPORT/EXP_Infotrade_Exportaciones.ipynb` (descarga) y `EXPORT/EXP_Selector_Partidas.ipynb` (diccionario de partidas, §7)

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/EXPORT/EXP_Infotrade_Exportaciones.ipynb

**Estado:** primera prueba real el 09/10/2026 (Loreto, No Tradicional / MADERAS Y PAPELES, partida 4412310000, ene–jul 2026). Funcionó sin contraseña y con los filtros aplicados. Se detectó y corrigió la fila de TOTAL (ver §3.1); con la corrección, filas y totales cuadran al centavo con la web. Falta probar con varias regiones y con "Todos".

---

## 2. Carpetas de Google Drive

| Uso | ID | URL |
|---|---|---|
| Datos (CSV por región y semestre) | `1JJqcvUomccL-dCCNm5yovl-9TN5laKYi` | https://drive.google.com/drive/folders/1JJqcvUomccL-dCCNm5yovl-9TN5laKYi |
| Control y LOG | `1gAO8-UjTV2bmBwMPgONBAYeVfpwXSWCY` | https://drive.google.com/drive/folders/1gAO8-UjTV2bmBwMPgONBAYeVfpwXSWCY |

- Se configuran en el **Bloque 3**, sección `# ── 1. CONFIGURACIÓN FIJA` (`DRIVE_FOLDER_ID` y `DRIVE_FOLDER_CONTROL_ID`).
- La cuenta que se autoriza en Colab necesita permiso de **Editor** en ambas carpetas. El notebook lo verifica al inicio.

---

## 3. La API de Infotrade (descubierta con F12 → Network)

La web es una aplicación React (`<div id="root">`) que consulta una API JSON. Todas las llamadas son **`POST`** con `Content-Type: application/json` a:

```
https://infotrade.promperu.gob.pe/wss/api/<ruta>
```

**Autenticación:** las llamadas **no envían token ni sesión de usuario**, solo cookies del sitio (`TS01…`, del firewall, y las de Google Analytics). El notebook no necesita la contraseña. Se usa con la cuenta del usuario y respetando los términos de uso: con pausas, de a una descarga y con auditoría.

### 3.1 Secuencia que hace la web al pulsar "Exportar a Excel"

| Orden | Ruta | Cuerpo (payload) | Respuesta |
|---|---|---|---|
| 1 | `Comunes/ObtenerParametroConcurrenciaReporteActual` | `{"headers":{"Accept":"application/json"}}` | `{"vResult":{"PARAMETROID":63,"CODIGO":"CantidadActualDescarga","VALOR":"0",…}}` |
| 2 | `Reportes/ExportacionesExcel` | filtros (sin `NumeroPagina`) | `{"RptData":[…todas las filas…],"TotalRegistros":0,"Totales":null,"TotalesPagina":null}` |
| 3 | `Comunes/ActualizarConcurrenciaDescarga` | `{"Tipo":1,"PerfilUsuario":"PERFIL_USUARIO_EXTERNO"}` | `{"vResult":1}` |
| 4 | `Comunes/ActualizarConcurrenciaDescarga` | `{"Tipo":2,"PerfilUsuario":"PERFIL_USUARIO_EXTERNO"}` | `{"vResult":1}` |
| 5 | `user/RegistrarAuditoria` | ver 3.4 | — |

`ExportacionesExcel` responde **JSON** con todas las filas; la web arma el Excel en el navegador. **Atención:** `RptData` trae al final **una fila de TOTAL**, con fecha, RUC, empresa y partida vacías y las sumas en Monto, pesos y cantidad. El notebook la descarta; si no, duplica los montos y cuenta una fila de más. Un subsector durante 6 meses pesó unos 12 MB, con 24 714 filas.

### 3.2 Consulta paginada (botón "Consultar")

`Reportes/Exportaciones` lleva los mismos filtros más `"NumeroPagina": 1` y responde:

```
{ "RptData": [ …filas de la página… ],
  "TotalRegistros": 24714,
  "Totales": { "Monto": 140264437.72, "PesoNeto": 84737289.037, "PesoBruto": 86348753.617, "Cantidad": 245364449, … },
  "TotalesPagina": { … } }
```

El notebook la usa como **referencia para el control**: `TotalRegistros` y `Totales`.

### 3.3 Cuerpo de filtros

```json
{
  "FechaInicio": "01-01-2026", "FechaFin": "30-06-2026",
  "Departamento": "Loreto",
  "Tipo": "No Tradicional",
  "Sector": "MADERAS Y PAPELES",
  "Mercado": "", "Partida": "", "Empresa": "",
  "DescripcionComercial": "", "DescripcionProducto1": "", "Condicion2": "",
  "DescripcionProducto2": "", "Condicion3": "", "DescripcionProducto3": "",
  "DescripcionProducto1E": "", "Condicion2E": "", "DescripcionProducto2E": "",
  "Condicion3E": "", "DescripcionProducto3E": ""
}
```

| Campo | Significado | Valores |
|---|---|---|
| `FechaInicio`, `FechaFin` | Rango (máximo 6 meses) | `dd-mm-aaaa`; el fin es el último día del mes |
| `Departamento` | **Región** | Nombre con tildes, tal cual en la web ("Áncash", "Apurímac", "San Martín"…). `""` = Todas |
| `Tipo` | **Sector** de la web | `No Tradicional`, `Tradicional`, `Sin clasificación`; `""` = Todos (supuesto, ver §8) |
| `Sector` | **Subsector** de la web | ver §3.5; `""` = Todos (supuesto) |
| `Mercado` | País de destino | `""` = Todos |
| `Partida` | Partida arancelaria (texto libre) | p. ej. `4418990000`; `""` = todas |
| `Empresa` | Empresa (texto libre) | `""` = todas |

En la API los nombres están **cruzados** respecto a la web: `Tipo` corresponde al Sector y `Sector` al Subsector.

### 3.4 Auditoría (`user/RegistrarAuditoria`)

```json
{ "UsuarioAuditoria": "<usuario>", "CodigoOpcionAuditoria": "Reportes",
  "CodigoPaginaAuditoria": "Exportaciones", "CodigoSubPaginaAuditoria": "",
  "Evento": "EXPORTAR EXCEL",
  "Json": "{\"FechaInicio\":…,\"Boton\":\"EXPORTAR A EXCEL\",\"Navegador\":\"Chrome\",\"Dispositivo\":\"Windows\",\"Ip\":\"\"}",
  "Pais": "Todos", "Partida": "", "Ruc": "" }
```

- Para "Consultar", el evento es `"CONSULTAR"`.
- En el notebook es **opcional**: solo se envía si se llena el campo "Usuario".

### 3.5 Catálogos (desplegables de la web)

- **Años:** 1994 a 2026.
- **Regiones (25):** Amazonas, Áncash, Apurímac, Arequipa, Ayacucho, Cajamarca, Callao, Cusco, Huancavelica, Huánuco, Ica, Junín, La Libertad, Lambayeque, Lima Metropolitana, Loreto, Madre de Dios, Moquegua, Pasco, Piura, Puno, San Martín, Tacna, Tumbes, Ucayali.
  - "Lima Metropolitana" aparece **dos veces** en la web, pero ambas envían el mismo valor: es un duplicado.
- **Sector (`Tipo`):** Todos, No Tradicional, Tradicional, Sin clasificación.
- **Subsector (`Sector`):** Todos, AGROPECUARIO, ARTESANÍAS, MADERAS Y PAPELES, METAL-MECÁNICO, MINERÍA NO METÁLICA, MINEROS, PESQUERO, PETRÓLEO Y GAS NATURAL, PIELES Y CUEROS, QUÍMICO, SIDERO-METALÚRGICO, SIN CLASIFICACIÓN, TEXTIL, VARIOS (inc. joyería).
- **Mercados:** todos los países del mundo. La web los carga desde `Comunes?TIPOCONSULTA=EjecutarPais`; las regiones vienen de `Comunes?TIPOCONSULTA=EjecutarDepartamento`. El notebook no los necesita mientras se usen con "Todos".

### 3.6 Campos de cada fila (`RptData`)

| API | CSV del notebook | Columna en la web |
|---|---|---|
| `FechaEmbarque` | `FECHA_EMBARQUE` | Fecha de embarque (dd/mm/aaaa) |
| `Ruc` | `RUC` (texto) | RUC |
| `RazonSocial` | `RAZON_SOCIAL` | Razón social |
| `Departamento` | `REGION` | Región |
| `CodigoPartida` | `PARTIDA` (texto, 10 dígitos) | Partida |
| `Partida` | `DESCRIPCION_ARANCELARIA` | Descripción arancelaria |
| `DescripcionComercial` | `DESCRIPCION_COMERCIAL` | Descripción comercial |
| `PaisDestino` | `MERCADO_DESTINO` | Mercado destino |
| `Monto` | `MONTO_FOB_USD` | Monto FOB (USD) |
| `PesoNeto` | `PESO_NETO_KG` | Peso neto (kg) |
| `PesoBruto` | `PESO_BRUTO_KG` | Peso bruto (kg) |
| `Cantidad` | `CANTIDAD` | Cantidad |
| `TipoSector` | `SECTOR` | Sector |
| `Sector` | `SUBSECTOR` | Subsector |

---

## 4. El notebook `EXP_Infotrade_Exportaciones.ipynb`

**Bloque 1 · Instalación.** Instala `requests`, `pandas`, `numpy`, `ipywidgets` y `google-api-python-client`, y hace los imports.

**Bloque 2 · Selectores (ipywidgets).**

| Selector | Tipo | Valor por defecto |
|---|---|---|
| Año / Mes inicio | Lista desplegable | Enero 2005 |
| Disponible hasta (año / mes) | Lista desplegable | Hoy menos 3 meses; **se ajusta** al mes que dice la web en "Datos disponibles hasta…" |
| Regiones | **Selección múltiple** (Ctrl/Cmd + clic) y botones "Marcar todas" / "Desmarcar todas" | Las 25 |
| Sector | Lista desplegable (una opción) | Todos |
| Subsector | Lista desplegable (una opción) | Todos |
| Capítulos | **Selección múltiple** (97 capítulos del Sistema Armonizado) y botón "Quitar capítulos" | Ninguno (todas las partidas) |
| Partida, Empresa | Texto | Vacío (todas). No se puede combinar Partida con Capítulos |
| Usuario (auditoría) | Texto | Vacío (no registra auditoría) |

**Bloque 3 · Descarga, control y Drive.**
1. Lee los selectores y arma los **cortes semestrales** (Ene–Jun y Jul–Dic), recortados al período elegido. Un semestre recortado se marca `CORTE_COMPLETO = NO`.
2. Se conecta a Drive y verifica las dos carpetas.
3. Lee el **control previo** desde Drive, si existe, para reanudar.
4. Por cada **corte × región pendiente**, repite la secuencia de la web: concurrencia → `Exportaciones` (referencia) → `ExportacionesExcel` (si hay registros) → concurrencia `Tipo 1` y `Tipo 2` → auditoría (opcional).
5. **Capítulos:** la web solo acepta en `Partida` códigos completos de 10 dígitos (lo confirmó el usuario: un código corto como `44` o `4412` no funciona). Por eso, cuando hay capítulos elegidos, se descarga el corte completo, el control lo compara con la web y luego se guardan **solo las filas cuya partida empieza por esos capítulos**. Antes, `PARTIDA` se normaliza a 10 dígitos (por si llega sin el 0 inicial).
6. Guarda **un CSV por región y semestre**, lo sube a Drive y borra la copia local para no llenar el disco de Colab.
7. Actualiza el control **después de cada corte**.
8. Muestra un resumen con los cortes OK, los que hay que revisar y los que tuvieron error, y genera un LOG de errores.

**Nombres de archivo:**
- Datos: `<prefijo> - <AAAAMM>-<AAAAMM> - <Región>.csv`. Ejemplos: `4412310000 - 202601-202606 - Loreto.csv`.
  - El prefijo es la partida; si se eligieron capítulos, `CAP44` o `CAP09+44`; si no hay ninguno de los dos, `TODAS`.
  - Con más de 6 capítulos el prefijo es `CAP<n>caps-<código>`, donde el código identifica la selección exacta. Los capítulos elegidos quedan en la columna `CAPITULOS` del control.
  - El nombre **no incluye Sector ni Subsector**: dos corridas con la misma partida (o `TODAS`), el mismo período y la misma región, pero con otros filtros, se reemplazan entre sí en la carpeta. Para filtros distintos conviene usar otra carpeta.
  - Un semestre incompleto (p. ej. `202607-202607`) se **reemplaza** al volver a descargarse con más meses (`202607-202608`): el notebook borra la versión parcial anterior.
- Control: `CONTROL Exportaciones - Sector <…> - Subsector <…>[ - Capitulos 09+44].csv` (uno por combinación de filtros; se acumula entre corridas).
- LOG: `LOG Exportaciones <fecha> - Sector <…> - Subsector <…>.csv`

**Reanudación:**
- Se **saltan** los cortes con `ESTADO = OK`, `CORTE_COMPLETO = SI` y archivo presente en Drive.
- Se **vuelven a descargar** los cortes con error, los que quedaron en REVISAR y los semestres incompletos.
- Si Colab se desconecta, basta con **ejecutar de nuevo el Bloque 3**.

**Cortesía con el servidor:**
- Una descarga a la vez.
- Pausa aleatoria de 2 a 4 s entre cortes.
- Reintentos con backoff.
- `TIMEOUT_EXCEL` de 600 s para cortes grandes.

**Volumen estimado:** desde 2005 con las 25 regiones son unos 43 semestres × 25 ≈ **1 075 descargas**. Pueden hacer falta varias corridas.

---

## 5. Archivo de CONTROL

Una fila por **año × semestre × región**:

| Columna | Qué es |
|---|---|
| `AÑO`, `SEMESTRE`, `DESDE`, `HASTA` | Corte consultado |
| `CORTE_COMPLETO` | `SI` si cubre el semestre entero; `NO` si quedó recortado por la fecha de inicio o por "Disponible hasta" |
| `REGION`, `SECTOR`, `SUBSECTOR`, `PARTIDA`, `CAPITULOS`, `EMPRESA` | Filtros usados |
| `FILAS_DESCARGADAS` / `FILAS_REF` / `DIF_FILAS` | Filas descargadas, `TotalRegistros` de la web y su diferencia |
| `FOB_USD_DESCARGADO` / `FOB_USD_REF` / `DIF_FOB_USD` | Suma del FOB descargado contra `Totales.Monto` de la web |
| `PESO_NETO_KG_*`, `PESO_BRUTO_KG_*`, `CANTIDAD_*` | Lo mismo para peso neto, peso bruto y cantidad |
| `REGIONES_EN_DATOS` | Regiones que vienen en las filas descargadas (debe ser la pedida) |
| `FILAS_GUARDADAS` / `FOB_USD_GUARDADO` | Filas y FOB que quedan en el CSV. Con capítulos, son solo las de esos capítulos; sin capítulos, coinciden con lo descargado. Las columnas `_DESCARGADO` / `_REF` se refieren siempre al corte completo |
| `ESTADO` | `OK` si filas y totales cuadran (tolerancia de 1 unidad) y la región coincide; si no, `REVISAR` |
| `ARCHIVO` | Nombre del CSV en Drive |
| `FECHA_EXTRACCION` | Fecha de la corrida |

---

## 6. Cómo hacer cambios frecuentes

- **Otras carpetas de Drive:** cambiar `DRIVE_FOLDER_ID` y `DRIVE_FOLDER_CONTROL_ID` en el Bloque 3.
- **Más o menos pausa:** `PAUSA` en el Bloque 3.
- **Agregar una región o un subsector a los selectores:** editar las listas `REGIONES`, `SECTORES` y `SUBSECTORES` en el Bloque 2, con el texto exacto que envía la web.
- **Filtrar por país:** agregar un selector `Mercado` y enviar en `filtros()` el valor que use la web. Antes hay que confirmar ese valor en el Payload.
- **Si la API cambia:** volver a capturar con F12 → Network → Fetch/XHR la secuencia de §3.1 y revisar rutas, campos y la estructura de `RptData` y `Totales`.

---

## 7. Diccionario de partidas arancelarias (`EXPORT/arancel/`)

Las subpartidas nacionales de SUNAT cambian con cada nueva versión del Arancel de Aduanas (aprox. cada 5 años, al ritmo de la enmienda del Sistema Armonizado). El diccionario dice qué partidas se pueden usar en un periodo y cuáles forman una serie comparable.

**Formato del código:** 10 dígitos sin puntos (`4412310000`). `CODIGO_SUNAT` guarda la forma con puntos (`4412.31.00.00`).

| Versión | Norma | Rige desde | Subpartidas |
|---|---|---|---|
| 2002 | D.S. 239-2001-EF | 01/01/2002 | 7 002 |
| 2007 | D.S. 017-2007-EF | 01/04/2007 (ene–mar 2007 rige el 2002) | 7 397 |
| 2012 | D.S. 238-2011-EF | 01/01/2012 | 7 566 |
| 2017 | D.S. 342-2016-EF | 01/01/2017 | 7 805 |
| 2022 | D.S. 404-2021-EF | 01/01/2022 (vigente) | 8 021 |

El conteo incluye códigos creados por modificaciones dentro de una misma versión (p. ej. `2608000010/90` en 2017).

**Fuentes** (entregadas por el usuario; sunat.gob.pe está bloqueado desde el entorno de Claude):
- los Aranceles 2002, 2007, 2012, 2017 y 2022 convertidos a markdown (el de 2007 está dañado y no se usa);
- las correlaciones teóricas de SUNAT 2002-2007, 2007-2012, 2012-2017 y 2017-2022 (https://www.sunat.gob.pe/orientacionaduanera/aranceles/correlaciones.html). La de 2017-2022 incluye la hoja `REVISADO`, que añade 37 pares sobre todo de textiles y vidrio; esos pares se suman a la tabla.

**Archivos:**

| Archivo | Contenido |
|---|---|
| `diccionario_partidas.csv` | Una fila por código (10 060 en total) |
| `diccionario_partidas.xlsx` | Hojas `LEEME`, `VERSIONES` e `INDICE`, una hoja por capítulo (`Cap 01`…`Cap 98`) y `CORRELACIONES` |
| `correlaciones_sunat.csv` | Pares origen→destino con `TIPO`: SIN CAMBIO, RECODIFICADA 1:1, DIVIDIDA 1:N, FUSIONADA N:1 o N:M |
| `versiones_arancel.csv` | Normas y vigencias |
| `construir_diccionario.py`, `construir_excel.py`, `parse_arancel.py` | Scripts para regenerar los archivos. Necesitan `corr/` (correlaciones descomprimidas) y `arancel_src/` (los md) junto al script |

**Columnas clave del diccionario:**
- `V2002…V2022`: 1 si el código existe en esa versión.
- `C02_07…C17_22`: 1 si el código pasa a la versión siguiente **1 a 1 consigo mismo**, es decir, sin dividirse, fusionarse ni recodificarse. Queda vacío si el código no existe en ambas versiones.
- `SERIE_ESTABLE`: el tramo más largo en que la serie es comparable. `TRAMOS` lista todos los tramos, porque un código puede desaparecer y volver a usarse (p. ej. `8471300000`: `2002 | 2007-2022`).
- `ESTADO`: uno de estos valores:
  - `ESTABLE 2002-HOY` (4 812 códigos)
  - `ESTABLE DESDE AAAA`
  - `NUEVA 2022`
  - `DESCONTINUADA (ÚLTIMA AAAA)`
- `MISMA_DESCRIPCION`: SI o NO. NO significa que cambió la redacción (similitud menor a 85 %) aunque la correlación sea 1 a 1. Conviene revisar esos casos (158).
- `EQUIV_ANTERIORES` / `EQUIV_SIGUIENTES`: los códigos con los que hay que empalmar la serie cuando no hay continuidad. Ejemplo: `0101101000` (2002–2007) → `0101210000` (2012–hoy).
- Descripciones:
  - `DESCRIPCION`: el texto de la subpartida.
  - `DESCRIPCION_COMPLETA`: la jerarquía, del tipo "partida > nivel > subpartida".
  - `DESC_2002…DESC_2022`: el texto de cada versión.
  - Los textos de 2002 y 2017 vienen de PDF convertidos a texto y pueden traer errores de OCR. Los de 2007, 2012 y 2022 vienen de las tablas de correlación y son más limpios.

**Notebook `EXPORT/EXP_Selector_Partidas.ipynb`** (3 bloques):
1. Lee el CSV desde GitHub (raw); no hay que subir nada.
2. Ofrece estos selectores: año inicio, año fin, capítulos (varios), texto o código a buscar, incluir parciales, guardar en Drive.
3. Calcula las versiones del Arancel que rigen en el periodo y clasifica cada código:
   - **HABILITADA**: existe en todas esas versiones con continuidad 1 a 1, así que la serie es comparable en todo el periodo.
   - **PARCIAL**: existe solo en parte del periodo; hay que usar las columnas `EQUIV_*` para empalmar.
   - **Deshabilitada**: no existe en el periodo y no se muestra.

   Guarda `PARTIDAS - AAAA-AAAA - CAP ….csv` en la carpeta de CONTROL (`1gAO8…`).

Ejemplos (2005–2025 = las 5 versiones): hay 4 812 partidas habilitadas. `4412310000` aparece como PARCIAL en 2005–2025, porque no existe en 2002 (viene de `4412130000`), y como HABILITADA en 2012–2025.

---

## 8. Supuestos y pendientes

1. **Primera prueba real hecha** (09/10/2026, una región). **Siguiente:** probar con 2–3 regiones y Sector/Subsector "Todos", y medir cuánto tarda cada corte para planificar la descarga desde 2005.
2. **Confirmado** (prueba real): no hace falta iniciar sesión, y `Partida` acepta el código de 10 dígitos.
3. **Supuesto:** "Todos" en Sector y Subsector se envía como `""`, igual que en Mercado y Región. Si con "Todos" el control da 0 filas donde debería haber datos, capturar el Payload de la web con Sector o Subsector en "Todos" y ajustar `filtros()`.
4. **Supuesto:** el formato de `Empresa` (RUC o razón social) no se ha confirmado.
5. **Concurrencia:** el notebook consulta `CantidadActualDescarga` pero no espera según su valor, porque se desconoce el máximo permitido. Si la web empieza a rechazar descargas, agregar una espera mientras `VALOR` esté por encima del límite.
6. **Diccionario de partidas:** falta confirmar la fecha de vigencia del Arancel 2002 (se asume 01/01/2002). Cuando SUNAT publique un Arancel nuevo, agregar su correlación y volver a ejecutar `construir_diccionario.py`.
7. **Idea:** unir los CSV por año o en un solo archivo para el BI. Power BI también puede leer la carpeta completa.

---

## 9. Flujo de trabajo con GitHub

Es el mismo que el de los scrapers del MEF (ver `FISCAL/CONTEXTO_PROYECTO.md` §9):
- se trabaja en la rama `claude/scraper-gobiernos-regionales-kk6ecm`;
- se abre un PR y se fusiona a `main`;
- antes de editar, siempre se parte de `origin/main`;
- los notebooks se guardan sin salidas.

Este proyecto entró en el PR adriansivina-droid/scraper-mef#22.
