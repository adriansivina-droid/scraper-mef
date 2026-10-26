# Departamento de estudios BCRP-IQT · API

API interna para descargar las bases que bajan los scrapers del MEF (Consulta Amigable) y las de **pesca** (DIREPRO de
Loreto, San Martín y Ucayali). Una página permite marcar **bases, departamentos, nivel de gobierno y periodo** y
descargar un Excel con una hoja por base, con el formato de `PIM_Funcion.xlsx`.

## Estado del proyecto

| Fase | Qué incluye | Estado |
|---|---|---|
| 1 | Página, descarga de las 7 bases del MEF (Excel, CSV o JSON), estado de la base de datos y carga de los archivos que genera el scraper de Colab | **lista** |
| Pesca | Las 3 bases de pesca, cargadas con los Excel mensuales de las DIREPRO (o los LONG de los notebooks de `PESCA/`) | **lista** |
| 2 | El scraper corre en el servidor (Render), cada mes y a pedido, y escribe directo en la base de datos | pendiente |
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
| Empleo | trabajadores asalariados privados formales, por sector · Anexo | MTPE (PLAME y T-Registro) | **archivo mensual**, que genera el scraper de `EMPLEO/` (Power BI del MTPE) | falta |
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

## Endpoints

Todos piden el usuario y la contraseña (autenticación básica), salvo `/salud`.

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/` | La página |
| GET | `/v1/catalogo` | Bases, grupos, departamentos y niveles |
| GET | `/v1/estado` | Por base: filas, departamentos y periodo cargado; última carga |
| GET | `/v1/descargas/vista-previa` | Primeras filas y conteo de lo que se descargaría |
| GET | `/v1/descargas` | El archivo: `formato=xlsx` (una hoja por base), `csv` (un `.zip` si son varias) o `json` (paginado) |
| POST | `/v1/cargas` | Sube CSV del scraper, el `.zip` de `Scrapeo/output`, `PIM_Funcion.xlsx` o los Excel de pesca |
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
