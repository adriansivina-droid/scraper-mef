# Departamento de estudios BCRP-IQT · API

API interna para descargar las bases que bajan los scrapers del MEF (Consulta Amigable) y las de **pesca** (DIREPRO de
Loreto, San Martín y Ucayali). Una página permite marcar **bases, departamentos, nivel de gobierno y periodo** y
descargar un Excel con una hoja por base, con el formato de `PIM_Funcion.xlsx`.

## Estado del proyecto

| Fase | Qué incluye | Estado |
|---|---|---|
| 1 | Página, descarga de las 7 bases del MEF (Excel, CSV o JSON), estado de la base de datos y carga de los archivos que genera el scraper de Colab | **lista** |
| Pesca | Las 3 bases de pesca, cargadas con los Excel mensuales de las DIREPRO (o los LONG de los notebooks de `PESCA/`) | **lista** |
| 2 | El scraper del MEF corre solo (GitHub Actions, días 2 y 21) o con el botón «Actualizar desde el MEF», y carga directo en la base de datos | **lista** |
| Empleo | Base de empleo del MTPE (scraper en GitHub Actions, días 2 y 21, o botón «Actualizar empleo»), con el cuadro, el gráfico y el anexo de la síntesis por región | **lista** |
| Hidrocarburos | Producción por lote y canon de PERUPETRO, que guarda en la página el flujo diario de `HIDROCARBUROS/`, con el cuadro, el gráfico, el anexo por lote y el canon de la síntesis | **lista** |
| 3 | Ejecución del presupuesto: cuadros de gasto corriente e inversión (var. % real con el IPC de Lima, avance del PIM, comparación entre años), variaciones alarmantes y proyectos (GitHub Actions tras el scraper) | **lista** |

## Hoja de ruta: el informe completo

Objetivo a largo plazo: que el API arme la **Síntesis de Actividad Económica** mensual de Loreto, San Martín y Ucayali
(estructura tomada de los informes de junio de 2026). Cada sección sería un módulo con el mismo esquema que Fiscal:
scraper (o carga de una plantilla) → base de datos → descargas en Excel → cuadros y anexos.

| Sección | Cuadros y anexos | Fuente (según los informes) | Cómo entra al API | Estado |
|---|---|---|---|---|
| Resumen · otros indicadores | Cuadro 1 | SBS, MEF, DIREPRO y empresas | se arma con los demás módulos | al final |
| Agropecuario | producción (t), superficie sembrada (ha) · Anexo 1 | MIDAGRI y direcciones regionales | **archivo mensual** que recibe el equipo | falta |
| Pesca | producción pesquera y VBP · Anexo 2 | DIREPRO Loreto, San Martín y Ucayali | **archivo mensual**: el Excel de cada DIREPRO se sube en la página (o el LONG de los notebooks de `PESCA/`) | **en el API** |
| Hidrocarburos (Loreto, Ucayali) | producción y precio · Anexo de petróleo crudo | PERUPETRO; precio, Reuters | scraper en `HIDROCARBUROS/` (diario en GitHub Actions) → almacén de la página → API | **en el API** (producción y canon; falta el precio) |
| Manufactura | índice de volumen físico · Anexos | DIREPRO y encuesta BCRP a empresas industriales | **archivo mensual** | falta |
| Empleo | trabajadores asalariados privados formales, por sector · Anexo | MTPE (PLAME y T-Registro) | scraper de `EMPLEO/` en GitHub Actions (o su Excel subido en la página) | **en el API**, con cuadro, gráfico y anexo |
| Exportaciones | por grupo de productos · Anexo | SUNAT | **archivo mensual** | falta |
| Importaciones (Loreto) | FOB por uso o destino, aduana de Iquitos · Anexo | SUNAT | **archivo mensual** | falta |
| Crédito, depósitos y morosidad | saldos, crédito por tipo sin BN ni Agrobanco · Anexos | SBS y AFP | scraper (web de la SBS) | falta |
| Gasto corriente no financiero | por nivel, mes y acumulado, var. % real · Anexos de ejecución por nivel | MEF, Consulta Amigable | `Fiscal_Scraper` + API | **en el API** (fase 1) |
| Inversión pública | por nivel, var. % real y avance del PIM · Anexos de inversión por nivel | MEF, Consulta Amigable | `Fiscal_Scraper` + API | **en el API** (fase 1) |

Seis secciones llegan **en archivos mensuales** que el equipo ya recibe (exportaciones, empleo, importaciones,
agropecuario, manufactura y pesca): entran por la página, en «Actualizar base de datos», igual que hoy los CSV del
scraper. Solo quedan como scrapers el MEF (hecho), PERUPETRO (hecho) y la SBS.

**Arquitectura:** Render sirve la página y las descargas; Neon guarda los datos; los scrapers (MEF, SBS, PERUPETRO)
corren en **GitHub Actions** y escriben directo en Neon; los archivos mensuales se suben en la página.

**Orden propuesto:** (1) desplegar Fiscal y sus fases 2 y 3 (scraper en GitHub Actions y reportes); (2) carga de los
seis archivos mensuales, con el formato en que llegan; (3) hidrocarburos (scraper listo) y SBS; (4) un botón que genere
los cuadros y anexos del mes por región.

## Bases

| Grupo | Base (`base=`) | Hoja del Excel | Viene de |
|---|---|---|---|
| Inversión (2.6) | `inv-dev-funcion` | INV Funciones | `DEV Funcion.GobNacional/GobRegional` y, en locales, la suma de `DEV Funcion.Municipalidad` |
| | `inv-dev-municipalidad` | INV Municipalidades | `DEV Funcion.Municipalidad` |
| | `inv-dev-fuente` | INV Fuentes | `DEV InvFuente.*` |
| | `inv-pim-funcion` | PIM Funciones | `PIM Funcion AAAA - ….csv` o `PIM_Funcion.xlsx` |
| | `inv-pim-municipalidad` | PIM Municipalidades | `PIM Funcion.Municipalidad AAAA - ….csv` |
| Gasto total | `gasto-dev-generica` | GASTO Genéricas | `DEV Generica.*`, con la 2.8 reemplazada por su desglose de `DEV Deuda.*` |
| | `gasto-dev-fuente` | GASTO Fuentes | `DEV Fuente.*` |
| Pesca | `pesca-loreto` | PESCA Loreto | Excel de DIREPRO Loreto (consumo: hojas `Desemb_*`; ornamentales: hoja `POR ESPECIES`) o `LOR_PESCA_LONG.xlsx` |
| | `pesca-san-martin` | PESCA San Martín | `SMN_PESCA_AAAA-MM.xlsx` (el mes sale del nombre) o `SMN_PESCA_LONG.xlsx` |
| | `pesca-ucayali` | PESCA Ucayali | `ESTADISTICA_PESQUERA_DIREPRO_UCA_….xlsx` (acumulado del año) o `UCA_PESCA_LONG.xlsx` |

**Pesca** (detalle en `PESCA/pesca.md`; `app/pesca.py` repite la lógica de los notebooks de `PESCA/`):
- Cada base tiene las columnas del LONG de su región, con el VBP en miles de soles de 2007 (`#,##0.000` en el Excel).
  No usan el nivel de gobierno y solo tienen datos de su departamento.
- Los Excel se reconocen por sus hojas. Un crudo se convierte al LONG al subirlo; si en la misma carga viene también el
  LONG con ese periodo, gana el crudo.
- San Martín y Ucayali clasifican las especies con lo que ya está en la base de datos (o con el LONG que se sube junto).
  Por eso, **la primera vez hay que subir sus LONG históricos**; una especie que no estaba se avisa.
- Loreto reemplaza el consumo y los ornamentales por separado: subir uno no borra el otro.
- Ucayali llega con los 12 meses del año: los meses en cero después del último con datos no se guardan.

## Desplegar en Render + Neon (una sola vez)

Render corre el API (plan Starter, unos US$7 al mes) y Neon guarda la base Postgres (plan gratuito, que alcanza para
este volumen). Railway quedó descartado porque tiene cerrado el registro de cuentas nuevas.

**1. Base de datos en Neon**
1. Entra a <https://neon.com>, crea una cuenta (con GitHub o correo) y un proyecto llamado `estudios-bcrp-iqt`,
   región **AWS US East (N. Virginia)**.
2. En **Connection details** copia la cadena de conexión (empieza con `postgresql://` y termina en `?sslmode=require`).

**2. API en Render**
1. Entra a <https://render.com>, crea una cuenta con GitHub y autoriza el acceso **solo** a `adriansivina-droid/scraper-mef`.
2. **New → Blueprint →** elige `scraper-mef`. Render lee `render.yaml` (en la raíz del repositorio) y propone el servicio
   `estudios-bcrp-iqt` con la carpeta `FISCAL/api`.
3. Cuando pida `DATABASE_URL`, pega la cadena de Neon. `APP_USUARIO` queda en `estudios` y `APP_CLAVE` se genera sola
   (la ves en **Environment** del servicio).
4. **Apply.** Al terminar, la dirección aparece arriba del servicio (`https://estudios-bcrp-iqt.onrender.com` o parecida).
5. Entra con el usuario y la contraseña, ve a **Actualizar base de datos** y sube el `.zip` de `Fiscal/Scrapeo/output`
   y `PIM_Funcion.xlsx`.

Si Render no reconoce el Blueprint, se crea a mano: **New → Web Service → scraper-mef**, Root Directory `FISCAL/api`,
runtime Docker, plan Starter, Health Check Path `/salud` y las tres variables de arriba.

Cada cambio fusionado a `main` se vuelve a desplegar solo. `railway.json` queda por si Railway vuelve a abrir registros;
el `Dockerfile` sirve en cualquier servicio que corra contenedores.

## Scraper del MEF en el servidor (fase 2)

`.github/workflows/fiscal_scraper.yml` corre **el mismo `Fiscal_Scraper.ipynb` de Colab** sin Colab
(`FISCAL/automatizacion/scraper_servidor.py`: lee sus celdas, reemplaza Drive por una carpeta de trabajo y fija el
periodo) y carga `Scrapeo/output` en la base de datos con la misma lógica que subir el `.zip`. Si cambias el scraper
en el notebook, el servidor usa el cambio.

- **Solo:** los días 2 y 21 de cada mes a las 6:00 a. m.: año en curso hasta el último mes cerrado (el MEF sigue
  ajustando los meses anteriores, por eso se vuelve a bajar todo el año).
- **A mano:** botón «Actualizar desde el MEF» en «Actualizar base de datos» (eliges el periodo; vacío = año en curso),
  o en GitHub: Actions → «Fiscal · scraper del MEF» → Run workflow. La prueba rápida (un mes, solo Loreto) no carga
  nada en la base.
- **Departamentos:** el detalle municipal (`DEV Funcion.Municipalidad`, base «Inversión por municipalidad»), el PIM por
  función y el PIM por función y municipalidad se bajan para **los 25 departamentos** (`DEPARTAMENTOS_NACIONAL` en el
  BLOQUE 2 del notebook); el resto de bloques, para Loreto, San Martín y Ucayali. Todo se descarga con el formato de
  `PIM_Funcion.xlsx`.
- **Consultas simultáneas: 3** (entrada «consultas» del flujo; `FISCAL_WORKERS`). Con 6, la corrida de 2026 recibió del
  MEF páginas de otro filtro desde marzo («la URL no aplicó el filtro»); con 3 salió limpia, pero más lenta: unos 30
  minutos por mes con 25 departamentos. Por eso, sin periodo elegido (corrida automática o botón con el periodo vacío),
  el año se baja en **dos tramos seguidos**, enero-junio y julio-último mes cerrado, cada uno en su job (GitHub da 6
  horas por job). Con un periodo elegido a mano va en un solo job: hasta unos 10 meses por corrida.
- Los CSV de cada corrida quedan como artefacto en GitHub por 30 días (incluidos los CONTROL y LOG).
- Requiere el secreto `DATABASE_URL` en GitHub (la misma cadena de Neon). `FISCAL/automatizacion/prueba_mef.py`
  (flujo «Fiscal · prueba de conexión al MEF») comprueba que el MEF responde desde GitHub.

**El botón** no raspa en Render: le pide a GitHub que lance la corrida y muestra sus últimas corridas. Necesita un token:
1. GitHub → tu foto → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. **Token name:** `estudios-bcrp-iqt`; **Expiration:** la más larga que permita (o sin vencimiento); **Repository
   access:** *Only select repositories* → `scraper-mef`; **Permissions → Repository permissions → Actions:** *Read and
   write* (Metadata queda en *Read-only* sola). **Generate token** y cópialo.
3. Render → servicio → **Environment** → **Add Environment Variable** → `GITHUB_ACCIONES_TOKEN` = el token → guardar.
   Nunca lo pegues en un chat. Cuando venza, el botón avisará «el token no es válido o venció»: se genera otro igual.

## Todo en la página (sin Drive)

La página guarda todo en su base de datos y usa GitHub Actions solo para lo que necesita un servidor aparte (los
scrapers del MEF, de empleo y de PERUPETRO, los notebooks fiscales). Drive ya no hace falta:

- **Pesca:** el Excel que manda cada DIREPRO (o el LONG / la base histórica) se sube en la página: pestaña
  «Actualizar» del sector pesca de cada región, o «Las tres regiones → Subir archivos». Queda guardado en la base.
- **IPC de Lima:** se trae solo del BCRP (al abrir los cuadros de ejecución si le falta el mes anterior, a lo más una
  vez al día, y antes de cada procesamiento fiscal). Si el BCRP no responde, se sube `IPC.xlsx` en la página.
- **Notebooks fiscales:** sus Excel quedan en la pestaña «Archivos» (ver Ejecución del presupuesto).
- **Hidrocarburos:** el flujo `hidrocarburos_actualizar.yml` (07:00 en Lima, o el botón «Actualizar desde PERUPETRO»)
  corre los notebooks de `HIDROCARBUROS/` y guarda todo (CSV acumulados, PDF de PERUPETRO, Excel de canon, capas y
  mapa) en el **almacén de la página** (`app/almacen.py`, tabla `almacen`, con las mismas carpetas DATA y CONTROL e IDs
  que tenía en Drive: los notebooks no cambian). Al terminar carga la producción, el canon y el mapa. Lo que había en
  Drive se copia una sola vez con «Hidrocarburos · migrar desde Drive» (`hidrocarburos_migrar.yml`: primero `listar`,
  luego `copiar`); hasta entonces el flujo diario no corre, para no perder los históricos. Los archivos guardados se
  ven y se descargan en la pestaña «Actualizar» del sector hidrocarburos. Excepción: los PDF anuales de PERUPETRO
  (DATA/PDF, ~450 MB, públicos) no van a la base para no llenarla: quedan en la caché de GitHub del flujo y, si se
  pierden, el notebook los vuelve a bajar de PERUPETRO.
- **Cargar archivos sin abrir la página:** `.github/workflows/cargar_archivos.yml` sube a la página los archivos de la
  carpeta `cargas/` de una rama aparte.

## Empleo (MTPE)

Base `empleo` (hoja EMPLEO): `AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO`, tal como sale de
`EMPLEO/Scraping_MTPE_Empleo_x_Region_Actividad.ipynb`. Entra de tres formas:

- **Solo:** `.github/workflows/empleo_scraper.yml` corre los días 2 y 21 (12:30 UTC) para Loreto, San Martín y Ucayali.
- **Con el botón** «Actualizar empleo» (Las tres regiones → Actualización → Empleo), que usa el mismo
  `GITHUB_ACCIONES_TOKEN` que el botón del MEF; ahí se puede pedir `TODAS` las regiones.
- **Subiendo el Excel** `*_empleo.xlsx` en «Archivos».

El total «Perú» no se guarda (la síntesis no lo usa). Lima Metropolitana y Lima Provincias van en el departamento 15
sin pisarse. En cada región, la pestaña **Cuadros** de Empleo arma el cuadro de la síntesis (Loreto N° 6, San Martín
N° 4, Ucayali N° 7: mes del año anterior, mes, var. %, diciembre anterior, mes, var. %; «Otros» es «No precisa»), el
gráfico del número de trabajadores (desde enero de tres años antes, como el portal del MTPE), el gráfico de 25 meses
de var. % interanual del total y el anexo por sectores de 13 meses, y los descarga en Excel. En todos los gráficos de
la página, el año va debajo de los meses.
Las cifras se comprobaron con el Cuadro N° 6 publicado de Loreto (`tests/test_empleo.py`).

**Descarga en formato LONG** (pestaña Datos de Empleo en cada región, o Las tres regiones → Datos → «Empleo · LONG por
región»), con todos los meses que publica el MTPE (desde enero 2016): el mismo Excel que genera el
scraper (una hoja `AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO`, ordenada por región, actividad, año y mes, con su
mismo nombre de archivo), de una región, de varias o de las 26. Botones de grupo: Sucursal Iquitos, Oriente, Norte,
Centro, Sur y Lima y Callao (`GRUPOS_REGIONES` en `app/empleo.py`); solo marcan casillas, así que se puede combinar
cualquier región. Para tener las 26, el scraper debe correr con «Todas las regiones».

## Hidrocarburos (PERUPETRO)

El flujo diario de `HIDROCARBUROS/` (07:00 en Lima) guarda en la carpeta **DATA** del almacén de la página los CSV de
PERUPETRO y, al terminar, carga el más reciente de cada uno (también con «Volver a cargar en las bases» en la página):

| Archivo de DATA | Base | Hoja |
|---|---|---|
| `PP_produccion_lote_mes_<ini>-<fin>.csv` (petróleo, LGN, condensado; barriles) | `hidro-produccion` | HIDROCARBUROS |
| `PP_produccion_gas_lote_mes_<ini>-<fin>.csv` (gas natural; MPC) | `hidro-produccion` | HIDROCARBUROS |
| `PP_canon_departamento_mes.csv` (canon y sobrecanon transferido; MM S/) | `hidro-canon` | CANON PETROLERO |
| `PP_produccion_diaria.csv` (producción diaria por lote) | `hidro-produccion` (FUENTE «PRODUCCIÓN DIARIA · n de N días») | HIDROCARBUROS |
| `MAPA/PP_mapa_lotes_plus.html` (o `PP_mapa_lotes.html`) | el mapa de la pestaña «Mapa» (tabla `documentos`) | — |

La estadística mensual de PERUPETRO va con dos o tres meses de rezago; los meses que aún no trae se completan con la
suma de la producción diaria (columna FUENTE). El mes en curso es parcial: no entra en el cuadro ni en el anexo, y en el
gráfico va como promedio de los días reportados, marcado con «*».

Los CSV traen la serie completa: cada carga reemplaza los meses que trae en todos los departamentos. El departamento
sale de la columna `DEPARTAMENTO` (la que asigna el mapa de lotes; «UCAYALI / HUANUCO» va a Ucayali); si falta, de
`LOTES_DEPTO` en `app/hidrocarburos.py` (1-AB/192, 8, 95, 67, 39, 64, 102 → Loreto; 31-C, 131 → Ucayali); los demás
quedan como «SIN DEPARTAMENTO». También se pueden subir los CSV en la página.

En Loreto y Ucayali, la pestaña **Cuadros** del sector hidrocarburos arma: la producción por producto (petróleo y LGN
en miles de barriles, gas natural en millones de pies cúbicos) y lote, del mes y acumulada, contra el mismo periodo del
año anterior; el gráfico de producción diaria promedio (25 meses); el anexo mensual por lote (13 meses) y el canon
transferido al departamento; todo se descarga en Excel. Comprobado con el texto de Loreto 2025
(`HIDROCARBUROS/analisis`): 7,9 millones de barriles (+22,9 %), Lote 95 +5,9 % (`tests/test_hidrocarburos.py`).
Falta el precio del crudo (Reuters), que no está en DATA. La pestaña **Mapa** muestra el mapa de lotes del flujo de
hidrocarburos (`/v1/hidrocarburos/mapa`, aislado en un iframe), con botones de pantalla completa y descarga.

## Cuadros de pesca

En cada región, Sector pesca → Cuadros:
- indicadores del VBP y del volumen del mes y del acumulado;
- producción pesquera: VBP (miles de soles de 2007) y volúmenes por estado, especie y origen, del mes y del Ene.-Mes
  contra el año que se elija;
- gráficos: VBP mes a mes de los dos años y su variación interanual;
- con los formatos de la sucursal («Formato Cuadros …» de cada región):
  - «Producción pesquera» de la síntesis (mes y Ene.-Mes, y la fila SECTOR PESCA con la variación del VBP);
  - el Cuadro Nº 07 mes a mes con el total de cada año (en la página, los dos años comparados; en el Excel, toda la
    historia);
- las bases históricas de la sucursal (hojas `PESCA_SMN`, 2006-2022, y `PESCA_UCA`, 2010-2025) se suben en «Subir
  archivos»: se llevan al formato del LONG (mes a número, VBP a precios de 2007, nombres del crudo);
- descarga en Excel (`app/pesca_cuadros.py`).

## Exportaciones e importaciones (ESTAD)

El ESTAD de cada región es la única fuente (EXPORT/info_export.md). Se sube en «Exportaciones → Actualizar» (o en «Subir
archivos»): ESTADLO.xlsx (15.Export y 16.Import), ESTADSMN.xlsx (14.XLS) o ESTADUCA.xlsx (15.XLS). La página reconoce las
hojas por su título, lee solo las columnas de cada mes (fecha en la fila 5 y menos de 5 caracteres en la fila 4: nunca la
«Var.%» ni los «Ene.-Mes» del final) y guarda cada fila del cuadro (total, tipo, grupo, producto) en las bases
`expo-estad` e `impo-estad` (miles de US$). Las notas al pie del ESTAD («Resto», «Otras») pasan al anexo.

Cuadros (`/v1/cuadros/exportaciones?departamento=16&periodo=AAAA-MM[&flujo=impo][&formato=xlsx]`):
- **Síntesis** (Cuadro N° 7 Loreto, N° 5 San Martín, N° 8 Ucayali): regla del Cuadro_LOR — millones de US$ con
  REDONDEAR (Loreto 2 decimales; San Martín y Ucayali 1), total = suma de los tipos redondeados, variaciones con las
  cifras redondeadas, estructura % del mes del año anterior y contribución; la página muestra además las variaciones
  exactas (miles de US$) para redactar.
- **Anexo** (Loreto 6 y 7, San Martín 4, Ucayali 6): 13 meses + total Ene.-Dic. del año anterior, todas las filas del ESTAD.
- **Gráficos** (ENLACE ESTAD de las SERIES): variación % anual de 12 años (Ucayali: enero-mes en todos los años; Loreto
  corta las barras de más de 250 %), circulares de no tradicionales (6 principales + Otros, año anterior y enero-mes) y
  los 5 principales productos de enero-mes y del mes.

### Base mensual (pestañas «Base mensual» y «Resumen Export» de Exportaciones)

El flujo de ANUAL_PRO (hoja ORIGEN y tablas dinámicas) en la página (`sunat_expo.py`, base `expo-sunat`):
1. Subir un **ANUAL_PRO_AAAA.xlsx** una vez: carga los diccionarios (UNICOS: PROD_UNICOS, PAISES, EMPRESAS, ADUANA; y
   PARTIDA) y su hoja ORIGEN como base de ese año.
2. Cada mes, subir la base de SUNAT tal como llega (**X_AAAAMM.xlsx**). Cada fila toma producto, categoría, país,
   aduana, empresa y BORRAR PARA, y un estado: **ok** (BORRAR PARA = OK; solo estas entran), **verificar** (empresa nueva
   o BORRAR PARA vacío), **borrar** (BORRAR PARA con otra cosa, o una regla de limpieza obligatoria: hoy, café y tara en
   polvo en Loreto; se editan en la página) o **clasificar** (partida sin tipo ni producto).
3. Revisión en la página: empresas por verificar (BORRAR PARA y nota; razón social con «Buscar en el padrón de SUNAT»,
   que corre `EXPORT/automatizacion/padron_ruc.py` en GitHub: workflow `expo_padron_ruc.yml`, con DATABASE_URL),
   partidas sin clasificar y productos que van a «Resto» (equivalencias producto → fila del ESTAD). Cada corrección
   vuelve a procesar toda la base.
4. **ESTAD propuesto**: la tabla dinámica de las filas ok, fila por fila del último ESTAD de la región (por categoría al
   grupo; dentro del grupo, al producto del mismo nombre o de la equivalencia; maderas sin fila propia a «Otros
   acabados»; lo demás a «Resto»; tipo 3 a «Otras exportaciones»), contra el ESTAD cargado. «Pasar al ESTAD» lo guarda
   como el ESTAD del mes y los cuadros lo usan. También destinos, aduanas y empresas del mes y del acumulado.

5. **Resumen Export**: datos destacados del mes (producto estrella, principal destino y continente, cuántos países,
   productos y empresas; con el año anterior en la base, nuevos mercados y el producto que más creció; récord mensual),
   el borrador de los párrafos de la síntesis (mercados de destino y aduanas, como «El primero adquirió…; el segundo…»)
   y las tablas de productos, destinos, continentes, aduanas y empresas del mes y de enero-mes
   (`/v1/exportaciones/resumen`). La página no muestra el nombre SUNAT salvo en la nota «Fuente: SUNAT.» de los
   cuadros de la síntesis.

Con SUNAT 2023 (X_202301-202312) la página llega a las mismas 24 696 filas ok que la hoja ORIGEN depurada a mano.

### Importaciones (aduana de Iquitos): «Base mensual» y «Resumen Import»

El flujo de ANUAL_PRO - IMPORTACIONES (proyecto) en la página (`sunat_impo.py`, base `impo-base`):
1. Subir una vez el **ANUAL_PRO - IMPORTACIONES** (.xlsm o .xlsx): diccionarios PARTIDAS (con la tabla CUODE), UNICOS
   (PAISES, EMPRESAS, PROD_UNICOS) y su hoja ORIGEN.
2. Cada mes, la base tal como llega (**M_AAAAMM.xlsx**: aduana, ruc, partida, fob, flete, seguro, kilos, pais_adqui,
   cuode, periodo…). **No hay limpieza**: entran todas las filas de la aduana de Iquitos (226); las de otra aduana se
   marcan y no entran.
3. Clasificación como la hoja ORIGEN: la partida manda si su FUENTE es MANUAL y tiene tipo; si no, el CUODE de la fila;
   si no hay CUODE, la partida; si nada, «clasificar». CIF = FOB + flete + seguro; producto de la partida corregido
   con PROD_UNICOS; empresa y país por código.
4. **ESTAD propuesto** (Cuadro N° 16): por categoría, FOB redondeado a miles fila por fila (como el CUADRO 16), contra
   el ESTAD cargado; «Pasar al ESTAD» lo guarda. Revisión: empresas sin razón social (padrón de RUC) y partidas sin
   clasificar o sin nombre común (la categoría elegida queda como MANUAL).
5. **Resumen Import**: datos destacados y el borrador de los párrafos de la síntesis («Las importaciones por la aduana
   de Iquitos fueron de USD … millones en … provenientes de …; las compras correspondieron principalmente a …»).

Con las bases 2024–2026 el total coincide con el ESTAD casi todos los meses; la clasificación por CUODE difiere del
ESTAD antiguo, que ponía azúcar o aceite de soya en «Bienes no duraderos» (el CUODE los pone en «Materias para industria»).

El antiguo scraper de Infotrade (EXPORT/*.ipynb) ya no se usa.

## Ejecución del presupuesto (fase 3)

En Loreto, San Martín y Ucayali, sección **V. Ejecución del presupuesto**:

- **Gasto corriente no financiero** (genéricas de tipo 5: personal, pensiones, bienes y servicios, donaciones y
  transferencias y otros gastos corrientes; sin deuda ni capital) e **inversión pública** (genérica 2.6), pestaña
  Cuadros:
  - indicadores del mes y del acumulado;
  - cuadro por nivel de gobierno y por genérica o función: mes y Ene.-Mes de un año contra otro (se elige con qué
    año comparar), en millones de soles, con var. % real;
  - gráficos: mes a mes y acumulado de los dos años, variación real interanual y participación de cada nivel;
  - en inversión, además, PIM, avance del PIM contra el ritmo parejo (meses / 12) y la curva de avance de los dos
    años;
  - descarga en Excel (con las variaciones alarmantes, en inversión).
- **Variaciones alarmantes** (inversión): los 5 mayores aumentos y caídas en soles corrientes, del mes y del acumulado,
  por todos los niveles juntos, por nivel y función y por municipalidad. Es el criterio del Bloque 6 de
  `Fiscal_Procesamiento.ipynb`: siempre 5 aumentos (las 5 mayores diferencias), sin ítems en 0 y sin repetir.
- **Proyectos**: `.github/workflows/fiscal_proyectos.yml` corre `Fiscal_Proyectos.ipynb` sin Colab
  (`FISCAL/automatizacion/proyectos_servidor.py`) al terminar cada corrida del scraper del MEF, o con el botón de la
  pestaña. Sus CSV de entrada salen de la base, y el resultado va a la base `inv-proyectos`. El Excel de su bloque 6
  («Proyectos variaciones AAAA-MM.xlsx») queda en la pestaña **Archivos** en vez de subirse a Drive.
- **Archivos** (procesamiento): `.github/workflows/fiscal_procesamiento.yml` corre `Fiscal_Procesamiento.ipynb` completo
  sin Colab (`FISCAL/automatizacion/procesamiento_servidor.py`) al terminar cada corrida del scraper del MEF, o con el
  botón «Volver a procesar». Los CSV de `Scrapeo/output` se arman desde la base (con los mismos nombres y columnas que
  deja el scraper; la deuda desglosada vuelve a `DEV Deuda`) y el `IPC.xlsx`, con el IPC cargado en la página. Sus
  Excel (`Fiscal-<Depto>_AUTO.xlsx` y «Variaciones alarmantes AAAA-MM.xlsx») se guardan en la base y se descargan en la
  pestaña **Archivos** de Gasto corriente e Inversión pública.
- **IPC de Lima** (variación real): se trae solo de la API del BCRP (serie `IPC_SERIE_BCRP`, por defecto `PN38705PM`
  y, de respaldo, `PN01270PM`). Si no responde, se usa el `IPC.xlsx` que se suba en la página. Sin IPC, los
  cuadros muestran la variación nominal y lo avisan.

## Cuadros y gráficos BCRP

En cada sector con cuadros (pesca, hidrocarburos, empleo, gasto corriente e inversión pública) la pestaña **«Cuadros y
gráficos BCRP»** arma los cuadros, gráficos y anexos de la síntesis con su formato (tomado de las síntesis de junio
2026): Arial, filetes horizontales, miles con espacio y decimales con coma, notas de fuente y elaboración; los gráficos,
barras celestes con borde azul y el mismo mes de cada año en blanco («J.24 J A S … J.25»); los anexos, horizontales,
con la cabecera gris, los 13 meses y el total Ene.-Dic. del año anterior, y los rótulos repetidos a la derecha.
Cada uno se **copia** como imagen (para pegar en Word con Ctrl+V) o se descarga en **SVG** (vectorial) o **PNG**. La
numeración viene de la síntesis de junio 2026 y se puede cambiar en cada uno. Lo dibuja `app/static/bcrp.js`; los
anexos de ejecución salen de `/v1/cuadros/ejecucion?anexos=true` (13 meses por nivel de gobierno: gasto no financiero
por genérica, inversión por función).

## Anexos y contraste con la síntesis

- **Anexos** (último ítem del índice de cada región): todos los anexos de la síntesis en su orden y numeración (junio
  2026), con el formato BCRP y Copiar / SVG / PNG. Los de sectores que aún no entran a la página (agrícola,
  manufactura, exportaciones, importaciones, crédito, depósitos, morosidad) aparecen como pendientes.
- **Contraste** (pestaña de Gasto corriente e Inversión pública): lo que tiene la página contra lo **publicado por el
  MEF** en la vista anual de Consulta Amigable. El scraper la consulta en cada corrida y la deja en sus CSV de CONTROL;
  la página los guarda (`app/controles.py`, tabla `mef_controles`) y compara, por bloque (genérica, fuente, función,
  PIM), nivel y año, ese total con la suma de lo que tiene guardado: *coincide* (hasta S/ 5 por mes), *mes en curso*
  (del año actual, el MEF ya suma lo devengado en el mes abierto) o *revisar*. «API · revisar» también lo imprime, y
  «Fiscal · cargar controles» trae los CONTROL de corridas anteriores.

## Endpoints

Todos piden el usuario y la contraseña (autenticación básica), salvo `/salud`.

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/` | La página |
| GET | `/v1/catalogo` | Bases, grupos, departamentos y niveles |
| GET | `/v1/estado` | Por base: filas, departamentos y periodo cargado; última carga |
| GET | `/v1/descargas/vista-previa` | Primeras filas y conteo de lo que se descargaría |
| GET | `/v1/descargas` | El archivo: `formato=xlsx` (una hoja por base), `csv` (un `.zip` si son varias) o `json` (paginado) |
| POST | `/v1/cargas` | Sube CSV del scraper, el `.zip` de `Scrapeo/output`, `PIM_Funcion.xlsx`, los Excel de pesca o el de empleo |
| GET | `/v1/hidrocarburos/almacen` | Archivos y MB guardados por el flujo de hidrocarburos, última carga y corridas |
| POST | `/v1/hidrocarburos/cargar` | Carga en las bases los CSV nuevos o modificados del almacén y el mapa (`todo=true`: todos) |
| POST | `/v1/hidrocarburos/actualizar?modo=diario\|mensual` | Lanza el flujo de PERUPETRO en GitHub Actions |
| GET | `/v1/hidrocarburos/archivos` · `/v1/hidrocarburos/archivos/descargar?id=` | Lista y descarga los archivos del almacén |
| GET | `/v1/mef` | Si el botón del MEF está configurado y las últimas corridas del scraper en GitHub |
| POST | `/v1/mef/actualizar` | Lanza el scraper del MEF en GitHub Actions (`desde`, `hasta` AAAA-MM opcionales; `prueba=true`) |
| GET | `/v1/empleo` | Si el botón de empleo está configurado y las últimas corridas de su scraper |
| POST | `/v1/empleo/actualizar` | Lanza el scraper de empleo (`regiones=LOR,SMN,UCA` o `TODAS`) |
| GET | `/v1/descargas/empleo` | Empleo en el formato LONG del scraper, una hoja (`regiones=Loreto,San Martín` o `todas`; `desde`, `hasta` opcionales; `formato=xlsx`, `csv` o `json`) |
| GET | `/v1/cuadros/pesca` | Producción pesquera de Loreto, San Martín o Ucayali (`departamento=16/22/25`, `periodo`, `comparar`, `formato`); en Loreto, también el Cuadro Nº 07 |
| GET | `/v1/cuadros/ejecucion` | Gasto corriente (`sector=gasto`) o inversión (`sector=inversion`) de un departamento: `periodo`, `comparar` (año), `formato=json` o `xlsx` |
| GET | `/v1/variaciones` | Variaciones alarmantes de la inversión (`departamento`, `periodo`, `comparar`) |
| GET | `/v1/proyectos` | Proyectos detrás de las variaciones del último mes calculado |
| POST | `/v1/proyectos/actualizar` | Lanza la consulta de proyectos en GitHub Actions |
| GET | `/v1/contraste/ejecucion?departamento=&sector=` | Lo guardado en la página contra lo publicado por el MEF (vista anual, de los CONTROL del scraper) |
| POST | `/v1/bcrp/excel` | Excel de un cuadro de «Cuadros y gráficos BCRP» con el formato de la síntesis |
| GET | `/v1/fiscal/archivos` | Excel de los notebooks fiscales guardados (procesamiento, variaciones, proyectos) |
| GET | `/v1/fiscal/archivos/descargar?nombre=` | Descarga uno de esos Excel |
| POST | `/v1/fiscal/procesar` | Lanza `Fiscal_Procesamiento` en GitHub Actions |
| GET / POST | `/v1/ipc`, `/v1/ipc/actualizar` | IPC de Lima cargado / traerlo del BCRP |
| GET | `/v1/cuadros/hidrocarburos` | Producción, gráfico, anexo por lote y canon de un departamento (`departamento=16`, `periodo` opcional, `formato=json` o `xlsx`) |
| GET | `/v1/cuadros/empleo` | Cuadro, gráfico y anexo de empleo de un departamento (`departamento=16`, `periodo=2026-08` opcional, `formato=json` o `xlsx`) |
| GET | `/docs` | Documentación interactiva |

Parámetros de las descargas: `base=inv-dev-funcion,inv-pim-funcion`, `departamento=16,22,25`,
`nivel=nacional,regional,locales`, `desde=2025-01`, `hasta=2026-09`.

Ejemplo para el BI:

```
curl -u "$APP_USUARIO:$APP_CLAVE" -o bases.xlsx \
  "https://<tu-dominio>.up.railway.app/v1/descargas?base=inv-pim-funcion&departamento=16,22,25&nivel=nacional,regional,locales&desde=2025-01&hasta=2026-09&formato=xlsx"
```

## Cómo se guardan los datos

- Una tabla por base en Postgres, con columnas internas `_anio`, `_mes`, `_depto` y `_nivel` para filtrar.
- Cargar reemplaza los meses, departamentos y niveles que traen los archivos; lo demás se conserva. Recargar los mismos
  archivos no duplica filas. Si en una misma carga dos archivos traen el mismo periodo (por ejemplo el CSV del scraper
  y `PIM_Funcion.xlsx`), se usa el último y se avisa.
- Los archivos `CONTROL` y `LOG` se ignoran.

## Trabajar en local

```
pip install -r requirements-dev.txt
pytest                                             # pruebas con SQLite
PRUEBA_DATABASE_URL=postgresql://… pytest          # las mismas pruebas contra Postgres
uvicorn app.main:app --reload                      # http://localhost:8000 (sin APP_CLAVE no pide contraseña)
python -m app.carga <carpeta Scrapeo/output o .zip> # carga por comando
```
