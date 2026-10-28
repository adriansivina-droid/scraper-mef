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
| 3 | Reportes procesados (cuadros, variaciones, proyectos) generados en el servidor | pendiente |

## Hoja de ruta: el informe completo

Objetivo a largo plazo: que el API arme la **Síntesis de Actividad Económica** mensual de Loreto, San Martín y Ucayali
(estructura tomada de los informes de junio de 2026). Cada sección sería un módulo con el mismo esquema que Fiscal:
scraper (o carga de una plantilla) → base de datos → descargas en Excel → cuadros y anexos.

| Sección | Cuadros y anexos | Fuente (según los informes) | Cómo entra al API | Estado |
|---|---|---|---|---|
| Resumen · otros indicadores | Cuadro 1 | SBS, MEF, DIREPRO y empresas | se arma con los demás módulos | al final |
| Agropecuario | producción (t), superficie sembrada (ha) · Anexo 1 | MIDAGRI y direcciones regionales | **archivo mensual** que recibe el equipo | falta |
| Pesca | producción pesquera y VBP · Anexo 2 | DIREPRO Loreto, San Martín y Ucayali | **archivo mensual**: el Excel de cada DIREPRO se sube en la página (o el LONG de los notebooks de `PESCA/`) | **en el API** |
| Hidrocarburos (Loreto, Ucayali) | producción y precio · Anexo de petróleo crudo | PERUPETRO; precio, Reuters | scraper en `HIDROCARBUROS/` (diario en GitHub Actions); precio por archivo | scraper listo |
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
  `PIM_Funcion.xlsx`. Con 25 departamentos una corrida de un año completo toma unas 2 a 3 horas: para periodos largos,
  conviene un año por corrida (el límite de GitHub es de 6 horas por corrida).
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

## Pesca desde Drive (automático)

Basta con dejar los Excel que manda cada DIREPRO en su carpeta de crudos de Drive: el API los carga solo **cada día a
las 7:30 a. m.** (GitHub Actions, `.github/workflows/pesca_drive.yml`) o **al instante** con el botón «Sincronizar
ahora» de «Actualizar base de datos». Solo procesa los archivos nuevos o modificados (con «Volver a procesar todos»,
todos). Solo lee: nunca escribe ni borra en Drive.

| Base | Carpeta de crudos |
|---|---|
| Pesca Loreto | `1FRKRjpHi_KX5twCCafYiHedPuQPscWqj` |
| Pesca San Martín | `1Kkwys70cT3Z4ia5T7tO6CmNuQX-mSKWT` |
| Pesca Ucayali | `1AEEvAfbtJwbkW773mKg-BIsDwjigjCg9` |

**Configurar (una vez, después de desplegar en Render):**
1. **Credencial de Drive en Render.** Es la misma que usa el flujo de hidrocarburos (secreto `GOOGLE_DRIVE_CREDENCIAL`
   de GitHub). GitHub no deja volver a ver un secreto, así que si ya no tienes el archivo, genera otra con
   `HIDROCARBUROS/automatizacion/PP_Credencial_Drive.ipynb` (la anterior sigue sirviendo). En Render → servicio →
   **Environment** → variable `GOOGLE_DRIVE_CREDENCIAL` → pega todo el contenido de `credencial_drive.json` → guardar.
   La cuenta con la que se generó debe poder ver las tres carpetas de crudos. Nunca pegues la credencial en un chat.
2. **Secretos en GitHub** (repositorio → Settings → Secrets and variables → Actions → New repository secret):
   - `ESTUDIOS_API_URL`: la dirección del servicio (`https://estudios-bcrp-iqt.onrender.com` o la que te dio Render);
   - `ESTUDIOS_API_USUARIO` y `ESTUDIOS_API_CLAVE`: los valores de `APP_USUARIO` y `APP_CLAVE` (Render → Environment).
   Mientras falten, el flujo diario solo deja un aviso y no falla.
3. **Primera carga:** deja también en las carpetas de San Martín y Ucayali sus LONG históricos (`SMN_PESCA_LONG.xlsx`,
   `UCA_PESCA_LONG.xlsx`), o súbelos una vez en la página: de ahí sale la clasificación de especies. Los notebooks de
   `PESCA/` ignoran esos LONG en las carpetas de crudos.
4. Prueba con «Sincronizar ahora», o en GitHub: Actions → «Pesca · sincronizar desde Drive» → Run workflow.

Las carpetas se pueden cambiar sin tocar el código con las variables `DRIVE_CRUDOS_LORETO`, `DRIVE_CRUDOS_SAN_MARTIN` y
`DRIVE_CRUDOS_UCAYALI`.

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
gráfico de 25 meses de var. % interanual del total y el anexo por sectores de 13 meses, y los descarga en Excel.
Las cifras se comprobaron con el Cuadro N° 6 publicado de Loreto (`tests/test_empleo.py`).

**Descarga en formato LONG** (Las tres regiones → Datos → «Empleo · LONG por región»): el mismo Excel que genera el
scraper (una hoja `AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO`, ordenada por región, actividad, año y mes, con su
mismo nombre de archivo), de una región, de varias o de las 26. Botones de grupo: Sucursal Iquitos, Oriente, Norte,
Centro, Sur y Lima y Callao (`GRUPOS_REGIONES` en `app/empleo.py`); solo marcan casillas, así que se puede combinar
cualquier región. Para tener las 26, el scraper debe correr con «Todas las regiones».

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
| GET | `/v1/drive` | Si Drive está conectado, sus carpetas y la última sincronización |
| POST | `/v1/drive/sincronizar` | Carga los Excel nuevos o modificados de las carpetas de crudos (`todo=true`: todos) |
| GET | `/v1/mef` | Si el botón del MEF está configurado y las últimas corridas del scraper en GitHub |
| POST | `/v1/mef/actualizar` | Lanza el scraper del MEF en GitHub Actions (`desde`, `hasta` AAAA-MM opcionales; `prueba=true`) |
| GET | `/v1/empleo` | Si el botón de empleo está configurado y las últimas corridas de su scraper |
| POST | `/v1/empleo/actualizar` | Lanza el scraper de empleo (`regiones=LOR,SMN,UCA` o `TODAS`) |
| GET | `/v1/descargas/empleo` | Empleo en el formato LONG del scraper, una hoja (`regiones=Loreto,San Martín` o `todas`; `desde`, `hasta` opcionales; `formato=xlsx`, `csv` o `json`) |
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
