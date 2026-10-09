# Scrapers MEF – Consulta Amigable · Contexto del proyecto

Documento de traspaso para retomar el proyecto sin perder contexto, sea una persona o una sesión nueva de un asistente. Última actualización: **09/10/2026**.

---

## 1. Qué es

Son notebooks de **Google Colab** que extraen datos de ejecución presupuestal del portal **Consulta Amigable (Mensual)** del MEF:
`https://apps5.mineco.gob.pe/transparencia/mensual/`

- Siempre se filtra la **Genérica 6-26: Adquisición de activos no financieros** (inversión).
- Se extrae el **Devengado** (por mes) o el **PIM** (anual), por **Función**, para distintos niveles de gobierno y regiones.
- Los resultados son CSV que alimentan un BI. Se suben a carpetas de **Google Drive** o se descargan en un zip.
- Cada scraper genera además un **archivo de CONTROL** que valida los datos contra el propio MEF.

**Repositorio:** `adriansivina-droid/scraper-mef` (rama principal: `main`).

---

## 2. Inventario de scrapers

| Notebook | Dato | Nivel de gobierno | Regiones | Ruta de consulta |
|---|---|---|---|---|
| `MEF_DEV_Funcion_GobiernoRegional_LOR_SMN_UCA_(1).ipynb` | Devengado mensual | R: Gobiernos Regionales | Loreto, San Martín, Ucayali | Depto (Meta) → Función |
| `DEV_Funcion_GobiernoNacional_LOR_SMN_UCA.ipynb` | Devengado mensual | E: Gobierno Nacional | LOR, SMN, UCA | Depto (Meta) → Función |
| `DEV_Funcion_Municipalidad.ipynb` | Devengado mensual | M: Municipalidades | las 25 | Depto → Función → Municipalidad |
| `DEV_Funcion_Municipalidad_LOR_SMN_UCA.ipynb` | Devengado mensual | M: Municipalidades | LOR, SMN, UCA | Depto → Función → Municipalidad |
| `PIM_Funcion_LOR_SMN_UCA.ipynb` | PIM anual | E, M y R (los tres) | LOR, SMN, UCA | Depto (Meta) → Función, por nivel |
| `PIM_Funcion_Municipalidad_LOR_SMN_UCA.ipynb` | PIM anual | M: Municipalidades | LOR, SMN, UCA | Depto → Función → Municipalidad |

Para abrir cualquiera en Colab:
`https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/<NOMBRE>.ipynb`
En el caso del Regional, los paréntesis del nombre van codificados como `%28` y `%29`.

**Estado de las pruebas:**
- Se probaron contra el MEF real: Gobierno Regional y Municipalidad LOR-SMN-UCA. El usuario confirmó que funcionan.
- Los demás comparten el mismo código base y se probaron con un simulador. La primera ejecución real conviene revisarla.

---

## 3. Carpetas de Google Drive

| Scraper | Datos (`DRIVE_FOLDER_ID`) | Control (`DRIVE_FOLDER_CONTROL_ID`) |
|---|---|---|
| DEV Gobierno Regional | `18Ohcjmg6FojhNwbCHUHX3MEOxhokZA9b` | `1v2fa0FKJFi_0l1uGECJjYw8TvHPCDTbo` |
| DEV Gobierno Nacional | `1B7Z4_4Bop8WK33YvFZ8pX-xCQBmaTHnk` | `1v2fa0FKJFi_0l1uGECJjYw8TvHPCDTbo` |
| DEV Municipalidad (25 regiones) | `1lBfLL3Uwpk9adiB8uKHBfu0guazFiqJR` | `1v2fa0FKJFi_0l1uGECJjYw8TvHPCDTbo` |
| DEV Municipalidad LOR-SMN-UCA | `1T3_NF_Uk5-uEbUSqey0LTszBkfwVwfwi` | `1JbX5Of3fkGvN2rLuHgt5hVtsUDMlPB2s` |
| PIM Función (E/M/R) | `1Vu6zpHljX_178x0ZDTbtE9BL2b0pS0uh` | `1lHTsdrjZgCmJDOh_kbHhhG1-eJDQg2jz` |
| PIM Municipalidad | `1gnXMhMyfiKz_Hy-LIrR3lhPXqXgcysxx` | `1vIywq5uTfzu5Uw9xo9CIisg3aF7hfZ6m` |

- Carpeta de Drive donde el usuario guarda copias de los notebooks: `1Jeodj7iSXlr6qBAyrBtdc9VrhY2AsKUG`. Esas copias **no se sincronizan con GitHub**: hay que volver a guardarlas tras cada cambio.
- La URL de una carpeta es `https://drive.google.com/drive/folders/<ID>`.
- La cuenta que se autoriza en Colab necesita permiso de **Editor** en las carpetas. El notebook lo verifica al inicio.
- Las variables `DRIVE_FOLDER_ID` y `DRIVE_FOLDER_CONTROL_ID` están en el **Bloque 2**, sección `# ── 1. CONFIGURACIÓN`, alrededor de las líneas 10-12.

---

## 4. Cómo funciona Consulta Amigable (lo aprendido)

### 4.1 La URL codifica la ruta de navegación
```
Navegar_6.aspx?_tgt=frame&_uhc=yes&0=&24=6-2-6&23=1&1=R&21=16&8=&y=2025&ap=ActProy
```
- Cada **clave numérica** es una dimensión. El **valor** es el filtro elegido.
- **La PRIMERA clave con valor vacío es la columna que se lista** en la tabla de detalle. Todo lo que viene después se **ignora**.
  - Ejemplo: con `…&1=R&37=&5=16…`, la página se queda en "Nivel de gobierno" y **no** filtra el departamento. Ese fue el primer bug que se encontró.
- **El orden importa:** es el orden del breadcrumb.
- Hay que enviar `ap=ActProy`, porque así lo hace el navegador. El formato `_tgt=frame&_uhc=yes` + `ap=ActProy` es el que funciona hoy.
- **Mes:** clave `23`. Para la vista **anual** (PIM, control), la clave `23` se **omite**. Enviarla vacía cortaría la ruta.

### 4.2 Claves conocidas
| Clave | Dimensión | Ejemplo de valor |
|---|---|---|
| `0` | TOTAL | (siempre vacío, al inicio) |
| `24` | Genérica | `6-2-6` (= 6-26) |
| `23` | Mes | `1` … `12` |
| `1` | Nivel de gobierno | `E` Nacional · `R` Regionales · `M` Locales |
| `37` | Gob.Loc./Mancom. | `M` = Municipalidades (solo nivel M) |
| `2` | Sector | `99` = Gobiernos Regionales |
| `3` | Pliego | `453` = GR Loreto |
| `4` | Unidad ejecutora | `861` (la etiqueta dice `001-861`; la URL acepta el código corto) |
| `5` | Departamento (ubicación de la entidad) | `16` |
| `21` | Departamento (Meta: dónde se ejecuta el gasto) | `16` |
| `8` | Función | `03`, `15`, … |
| `7` | Municipalidad | listada como `160101-301263: MUNICIPALIDAD …` |

Departamentos: `16` Loreto · `22` San Martín · `25` Ucayali (los 25 están en `DEV_Funcion_Municipalidad.ipynb`).

### 4.3 Estructura del HTML
- **Breadcrumb** (`table.History`): filas sin radio, con la etiqueta del filtro ("Departamento (Meta) 16: LORETO") y sus montos.
- **Detalle** (`table.Data`): filas con `<input type="radio" name="grp1" value="99///…">`.
  - El valor del radio **no** es un código limpio. Se usa el código de la etiqueta (`99`, `453`, `861`).
  - `kCod` en el `onclick` del `<tr>` también trae el código.
- Las filas tienen 10 celdas: `radio | nombre | PIA | PIM | Certificación | Compromiso anual | Atención compromiso mensual | Devengado | Girado | Avance %`.
  - **Devengado = `celdas[-3]`**
  - **PIM = `celdas[-7]`**
- No hay `<th>`: los encabezados son `<td>` en `table.MapTable`.
- Los botones de dimensión (Función, Pliego, …) solo aparecen si esa dimensión **no** es la que se está listando. "Pliego" solo aparece después de elegir "Sector".
- El sitio usa **Incapsula** (anti-bots). Conviene pocos hilos, con pausas y reintentos.
- Página de 400 filas como máximo (`psize=400`), suficiente para cualquier departamento.

---

## 5. Arquitectura común de los notebooks

Todos tienen **dos bloques**. No hay celda de diagnóstico: el usuario pidió eliminarla y que no se descarguen HTML.

- **Bloque 1 · Instalación:** `pip install` + imports.
- **Bloque 2 · Configuración, extracción y cierre**, con estas secciones:
  1. `CONFIGURACIÓN`: año(s)/meses, carpetas de Drive, catálogo de departamentos, claves de URL, pausas e hilos.
  2. `GOOGLE DRIVE`:
     - `conectar_drive([ids])` autentica y verifica permiso de Editor.
     - `subir_a_drive()` crea o actualiza el archivo por nombre, con reintentos.
  3. `NAVEGACIÓN`:
     - `Pagina`: parsea breadcrumb (`filtros`) y detalle (`filas`).
     - `armar_params`: arma la URL.
     - `consultar`: reintentos con backoff. "SIN_TABLA" se trata como **error**, no como "sin datos".
     - `calibrar`: prueba formatos de URL y elige el primero que trae la tabla.
     - `validar_departamento` y `cuadre`: la suma del detalle debe coincidir con el total del breadcrumb.
     - `abrir_nivel`: prueba códigos candidatos hasta que el breadcrumb confirma el filtro.
     - `recorrer`: baja nivel por nivel.
     - `extraer`: arma los registros.
  4. `CONTROL`: ver sección 6.
  5. `CONEXIONES` + bucle principal (por mes o por año), resumen, LOG y subida/descarga.

**Reglas que se mantienen en todos:**
- Se guardan las filas en **0** que lista el MEF. `recorrer` baja también por las filas en 0.
  - Si el MEF no muestra una función, no se inventa una fila en 0.
- Montos **numéricos**, sin comas.
- Errores visibles: tabla de errores en pantalla y archivo `LOG … .csv`.
- Un CSV por **mes** (Devengado) o por **año** (PIM). Nunca un archivo único que se sobrescriba.
- Sufijo `- LOR - SMN - UCA` en los nombres de archivo de los scrapers acotados a esas regiones.
- Meses: `MES_INICIO` / `MES_FIN` (`None` = último mes **cerrado**; `INCLUIR_MES_EN_CURSO = False`).
- PIM: `AÑO_INICIO` / `AÑO_FIN`, **sin filtro de mes**, y **sin** fecha de corte (el usuario la consideró irrelevante).

### Opción de detalle en Regional y Nacional (`NIVEL_DETALLE`)
- `"DEPARTAMENTO"` (**por defecto**): Depto → Función. Una consulta por región y mes; la corrida tarda 1-2 minutos.
- `"PLIEGO"`: Depto → Sector → Pliego → Función.
- `"EJECUTORA"`: Depto → Sector → Pliego → Unidad ejecutora → Función.
  - Es mucho más lento: 20-40 minutos en Regional y horas en Nacional.
  - El usuario decidió no usarlo por defecto.

---

## 6. Archivos de CONTROL

Diccionario de columnas listo para Drive/Sheets: `docs/Diccionario_Controles_MEF.xlsx`. Tiene una hoja por control: DEV LOR-SMN-UCA, PIM Función y PIM Municipalidad.

### 6.1 Devengado (Regional, Nacional, Municipalidad)
`CONTROL <nivel> <AÑO>[ - Meses XX-YY][ - LOR - SMN - UCA].csv`

Compara la suma de los meses descargados con la **vista anual** del MEF (sin filtro de mes), por departamento y función.

| Columna | Significado |
|---|---|
| `DEV_REF_ANUAL` | Devengado del año según el MEF (incluye todo lo registrado a la fecha) |
| `DEV_SUMA_MESES` | Suma de los CSV mensuales descargados |
| `DEV_ULTIMO_MES` | Devengado del último mes procesado |
| `DIF_SUMA` / `DIF_ULTIMO` | `DEV_SUMA_MESES` o `DEV_ULTIMO_MES` menos `DEV_REF_ANUAL` |
| `ESTADO` | `OK` / `REVISAR` (año completo) · `PARCIAL` (año incompleto: la diferencia es el gasto de meses no descargados) |
| `TOLERANCIA_S/` | 5 × número de meses (mínimo 5), por redondeo |
| `FECHA_EXTRACCION` | Fecha de la corrida |

- **Conclusión verificada:** el devengado de cada CSV mensual es **solo de ese mes**. En el control de GR 2025, `DIF_SUMA` dio entre 0 y 3 soles. Por eso los meses **se pueden sumar**.
- El control solo **valida** con un año cerrado y completo. Con un año en curso sirve para ver el gasto de los meses no descargados.

### 6.2 PIM Función (E/M/R)
`CONTROL PIM Funcion <años> - LOR - SMN - UCA.csv`

Por año, departamento y función: `PIM_GOBIERNO_NACIONAL + PIM_GOBIERNOS_LOCALES + PIM_GOBIERNOS_REGIONALES = PIM_SUMA_NIVELES` contra `PIM_REF_TOTAL` (el departamento consultado sin filtro de nivel). Incluye `DIF`, `ESTADO` (OK/REVISAR) y una tolerancia de S/ 3.

### 6.3 PIM Municipalidad
`CONTROL PIM Funcion.Municipalidad <años> - LOR - SMN - UCA.csv`

Por año, departamento y función: `PIM_SUMA_MUNICIPALIDADES` contra `PIM_REF_FUNCION`. Incluye `DIF`, `N_MUNICIPALIDADES`, `ESTADO` y una tolerancia de max(3, 0.5 × número de municipalidades).

---

## 7. Columnas de los CSV de datos

| Scraper | Columnas |
|---|---|
| DEV Regional / Nacional (DEPARTAMENTO) | `AÑO, MES, NIVEL_GOBIERNO, DEPARTAMENTO, ENTIDAD, FUNCION, DEVENGADO` |
| DEV Regional / Nacional (EJECUTORA) | `AÑO, MES, NIVEL_GOBIERNO, DEPARTAMENTO, PLIEGO, UNIDAD_EJECUTORA, FUNCION, DEVENGADO` |
| DEV Municipalidad (ambos) | `AÑO, MES, DEPARTAMENTO, FUNCION, MUNICIPALIDAD, DEVENGADO` |
| PIM Función | `AÑO, DEPARTAMENTO, NIVEL DE GOBIERNO, FUNCION, PIM` |
| PIM Municipalidad | `AÑO, DEPARTAMENTO, FUNCION, MUNICIPALIDAD, PIM` |

---

## 8. Cómo hacer cambios frecuentes

- **Cambiar una carpeta de Drive:** reemplazar el ID en `DRIVE_FOLDER_ID` o `DRIVE_FOLDER_CONTROL_ID`, en el Bloque 2.
- **Descargar un zip en lugar de subir a Drive:** `SUBIR_A_DRIVE = False`, IDs en `""`, `DESCARGA_FINAL = "zip"`. **No es confiable:** `files.download()` de Colab puede fallar sin aviso (descarga bloqueada por el navegador o por cookies de terceros). Se probó en Municipalidad LOR-SMN-UCA, no descargaba y se volvió a Drive.
- **Agregar o quitar regiones:** editar la lista `departamentos` (y `SUFIJO_REGIONES` si existe).
- **Crear un scraper para otro nivel:** copiar el notebook más parecido y cambiar `NIVEL_GOBIERNO`, `NIVEL_ETIQUETA`, `NIVEL_CORTO` y `PARAMS_NIVEL` (`{"37": "M"}` solo para municipalidades).
- **Cambiar el monto extraído:** en los municipales, `COLUMNA_VALOR` (`-3` Devengado, `-7` PIM). En los demás está fijo en `Pagina`.
- **Si el MEF cambia la URL o las claves:** revisar `FORMATOS`, `CLAVE`, `CLAVES_DEPTO` y `PARAMS_EXTRA`. La validación del breadcrumb avisa cuando un filtro no se aplicó.

---

## 9. Flujo de trabajo con GitHub

- Rama de desarrollo usada por el asistente: `claude/scraper-gobiernos-regionales-kk6ecm`.
- Por cada cambio: se recrea la rama desde `origin/main`, se hace commit y push, se abre un PR y se **fusiona a `main`**. Hasta ahora van del #1 al #18.
- Los notebooks se guardan **sin salidas**: `outputs` y `execution_count` vacíos.
- El usuario a veces guarda desde Colab a `main` con commits "Se creó con Colab". Antes de editar, siempre hay que hacer `git fetch` y partir de `origin/main`, para no pisar esos cambios.
- Desde el entorno del asistente, el sitio del MEF está **bloqueado** por la red. Las pruebas se hicieron con simuladores que imitan el HTML y la lógica de la URL (más un Drive falso), y los HTML reales que subió el usuario confirmaron el parser.

---

## 10. Historial de decisiones (resumen)

1. El scraper municipal original se adaptó a Gobiernos Regionales. Se corrigieron el `37` vacío, la cabecera `<th>` inexistente y la navegación (que es por URL, no por botones).
2. Se agregó el detalle por Pliego y Unidad ejecutora. Luego se decidió **DEPARTAMENTO por defecto**, por eficiencia.
3. El notebook quedó en **dos bloques**, sin celda de diagnóstico ni descarga de HTML.
4. Nuevo scraper de **Gobierno Nacional** (nivel E).
5. El **control anual** se genera siempre (estado PARCIAL si el año está incompleto) y va a su propia carpeta.
6. Se integró y corrigió el scraper **Municipalidad** (25 regiones):
   - DEVENGADO pasó de texto a número;
   - los errores ya no se ocultan;
   - se eliminaron las 625 consultas fijas;
   - hay un CSV por mes.
7. **Municipalidad LOR-SMN-UCA**: se probó la salida en zip, pero el zip no se descargaba y se volvió a Drive (carpetas propias).
8. En todos se conservan las **filas en 0** que lista el MEF.
9. Nuevos **PIM Función** y **PIM Municipalidad** (LOR-SMN-UCA), anuales, con control. Se quitó la fecha de corte.

---

## 11. Pendientes / ideas

- Confirmar en el MEF real los notebooks que solo se probaron con el simulador: Nacional, Municipalidad (25 regiones) y los dos de PIM.
- Si se necesita el PIM municipal de las 25 regiones, se puede crear la variante copiando el catálogo de `DEV_Funcion_Municipalidad.ipynb`.
- La opción de meses sueltos ("1, 3, 5") se eliminó al unificar con `MES_INICIO`/`MES_FIN`. Se puede volver a agregar.

---

## 12. Proyecto Exportaciones (Infotrade · PROMPERÚ)

Es un proyecto aparte, con su propio documento de contexto: **`exportaciones_scraper_infotrade.md`**. Allí están la API descubierta, el notebook `EXP_Infotrade_Exportaciones.ipynb`, las carpetas de Drive, el control y los pendientes.
