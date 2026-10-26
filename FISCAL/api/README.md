# Departamento de estudios BCRP-IQT · API

API interna para descargar las bases que bajan los scrapers del MEF (Consulta Amigable). Una página permite marcar
**bases, departamentos, nivel de gobierno y periodo** y descargar un Excel con una hoja por base, con el formato de
`PIM_Funcion.xlsx`.

## Estado del proyecto

| Fase | Qué incluye | Estado |
|---|---|---|
| 1 | Página, descarga de las 7 bases (Excel, CSV o JSON), estado de la base de datos y carga de los archivos que genera el scraper de Colab | **lista** |
| 2 | El scraper corre en el servidor (Render), cada mes y a pedido, y escribe directo en la base de datos | pendiente |
| 3 | Reportes procesados (cuadros, variaciones, proyectos) generados en el servidor | pendiente |

## Hoja de ruta: el informe completo

El objetivo a largo plazo es que el API cubra la síntesis de actividad económica de la región, con el orden de su índice.
Cada sección sería un módulo con el mismo esquema que Fiscal: scraper → base de datos → descargas en Excel → cuadros.

| Sección del informe | Fuente probable | Estado |
|---|---|---|
| I. Actividad productiva · 1.1 Agropecuario | MIDAGRI | falta |
| I. Actividad productiva · 1.2 Hidrocarburos | PERUPETRO | scraper en `HIDROCARBUROS/` (diario con GitHub Actions) |
| I. Actividad productiva · 2.1 Manufactura | PRODUCE | falta |
| II. Aspectos laborales · Empleo | MTPE | falta |
| III. Sector externo · Exportaciones | Infotrade / PROMPERÚ (SUNAT) | scraper en `EXPORT/` |
| III. Sector externo · Importaciones | SUNAT | falta |
| IV. Crédito y depósitos | SBS | falta |
| V. Presupuesto · Gasto corriente no financiero e Inversión pública | MEF, Consulta Amigable | en el API (fase 1) |
| Anexos | cuadros de cada sección | al final |

Orden propuesto: (1) terminar Fiscal (despliegue, fases 2 y 3); (2) sumar al API hidrocarburos y exportaciones, que ya
tienen scraper; (3) fuentes nuevas: SBS, MTPE, MIDAGRI, PRODUCE e importaciones; (4) un botón que genere los cuadros y
anexos del mes. Las fuentes de las secciones que faltan están por confirmar con el equipo.

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
| POST | `/v1/cargas` | Sube CSV del scraper, el `.zip` de `Scrapeo/output` o `PIM_Funcion.xlsx` |
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
