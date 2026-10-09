# Scraper de Exportaciones · Infotrade (PROMPERÚ) · Contexto del proyecto

Documento de traspaso de este proyecto, para retomarlo sin perder contexto, sea una persona o una sesión nueva de un asistente. Es **independiente** de los scrapers del MEF, que se describen en `FISCAL/CONTEXTO_PROYECTO.md`. Última actualización: **09/10/2026**.

---

## 1. Objetivo

Descargar el detalle de **exportaciones del Perú** (datos de SUNAT) desde Infotrade de PROMPERÚ, por región, sector y subsector, desde **2005** como mínimo, y dejarlo en CSV en Google Drive para alimentar un BI.

- **Página:** https://infotrade.promperu.gob.pe/reporte-exportaciones ("Descarga de información de exportaciones").
- Requiere cuenta de usuario para entrar a la web.
- La tabla que muestra la web es **incompleta** (paginada); la información completa se obtiene con **"Exportar a Excel"**.
- **Restricción de la web:** cada consulta abarca **6 meses como máximo**.

**Repositorio:** `adriansivina-droid/scraper-mef` · **Notebook:** `EXPORT/EXP_Infotrade_Exportaciones.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/EXPORT/EXP_Infotrade_Exportaciones.ipynb

**Estado:** probado solo con un simulador (API y Drive falsos). **Falta la primera prueba con el sitio real.** Conviene empezar con una región y un rango corto.

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

`ExportacionesExcel` responde **JSON** con todas las filas; la web arma el Excel en el navegador. Un subsector durante 6 meses pesó unos 12 MB, con 24 714 filas.

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
| `Tipo` | **Sector** de la web | `No Tradicional`, `Tradicional`, `Sin clasificación`; `""` = Todos (supuesto, ver §7) |
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
| Partida, Empresa | Texto | Vacío (todas) |
| Usuario (auditoría) | Texto | Vacío (no registra auditoría) |

**Bloque 3 · Descarga, control y Drive.**
1. Lee los selectores y arma los **cortes semestrales** (Ene–Jun y Jul–Dic), recortados al período elegido. Un semestre recortado se marca `CORTE_COMPLETO = NO`.
2. Se conecta a Drive y verifica las dos carpetas.
3. Lee el **control previo** desde Drive, si existe, para reanudar.
4. Por cada **corte × región pendiente**, repite la secuencia de la web: concurrencia → `Exportaciones` (referencia) → `ExportacionesExcel` (si hay registros) → concurrencia `Tipo 1` y `Tipo 2` → auditoría (opcional).
5. Guarda **un CSV por región y semestre**, lo sube a Drive y borra la copia local para no llenar el disco de Colab.
6. Actualiza el control **después de cada corte**.
7. Muestra un resumen con los cortes OK, los que hay que revisar y los que tuvieron error, y genera un LOG de errores.

**Nombres de archivo:**
- Datos: `EXP <año>-S<1|2> - <Región> - Sector <…> - Subsector <…>[ - Partida …][ - Empresa …].csv`
- Control: `CONTROL Exportaciones - Sector <…> - Subsector <…>.csv` (uno por combinación de filtros; se acumula entre corridas).
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
| `REGION`, `SECTOR`, `SUBSECTOR`, `PARTIDA`, `EMPRESA` | Filtros usados |
| `FILAS_DESCARGADAS` / `FILAS_REF` / `DIF_FILAS` | Filas descargadas, `TotalRegistros` de la web y su diferencia |
| `FOB_USD_DESCARGADO` / `FOB_USD_REF` / `DIF_FOB_USD` | Suma del FOB descargado contra `Totales.Monto` de la web |
| `PESO_NETO_KG_*`, `PESO_BRUTO_KG_*`, `CANTIDAD_*` | Lo mismo para peso neto, peso bruto y cantidad |
| `REGIONES_EN_DATOS` | Regiones que vienen en las filas descargadas (debe ser la pedida) |
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

## 7. Supuestos y pendientes

1. **Primera prueba real pendiente.** Sugerencia: una región, por ejemplo Loreto, en 2025-2026, y comparar con lo que muestra la web.
2. **Supuesto:** "Todos" en Sector y Subsector se envía como `""`, igual que en Mercado y Región. Si con "Todos" el control da 0 filas donde debería haber datos, capturar el Payload de la web con Sector o Subsector en "Todos" y ajustar `filtros()`.
3. **Supuesto:** el formato de `Partida` y `Empresa` cuando se llenan. Se confirmó una partida de 10 dígitos; el formato de Empresa (RUC o razón social) no se ha confirmado.
4. **Concurrencia:** el notebook consulta `CantidadActualDescarga` pero no espera según su valor, porque se desconoce el máximo permitido. Si la web empieza a rechazar descargas, agregar una espera mientras `VALOR` esté por encima del límite.
5. **Idea:** unir los CSV por año o en un solo archivo para el BI. Power BI también puede leer la carpeta completa.

---

## 8. Flujo de trabajo con GitHub

Es el mismo que el de los scrapers del MEF (ver `FISCAL/CONTEXTO_PROYECTO.md` §9):
- se trabaja en la rama `claude/scraper-gobiernos-regionales-kk6ecm`;
- se abre un PR y se fusiona a `main`;
- antes de editar, siempre se parte de `origin/main`;
- los notebooks se guardan sin salidas.

Este proyecto entró en el PR adriansivina-droid/scraper-mef#22.
