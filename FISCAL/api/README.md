# API Fiscal · Railway

API interna para descargar las bases que bajan los scrapers del MEF (Consulta Amigable). Una página permite marcar
**bases, departamentos, nivel de gobierno y periodo** y descargar un Excel con una hoja por base, con el formato de
`PIM_Funcion.xlsx`.

## Estado del proyecto

| Fase | Qué incluye | Estado |
|---|---|---|
| 1 | Página, descarga de las 7 bases (Excel, CSV o JSON), estado de la base de datos y carga de los archivos que genera el scraper de Colab | **lista** |
| 2 | El scraper corre en Railway, cada mes y a pedido, y escribe directo en la base de datos | pendiente |
| 3 | Reportes procesados (cuadros, variaciones, proyectos) generados en Railway | pendiente |

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

## Desplegar en Railway (una sola vez)

1. Entra a <https://railway.com>, crea una cuenta con GitHub y elige un plan (Hobby alcanza para empezar).
2. **New Project → Deploy from GitHub repo →** `adriansivina-droid/scraper-mef`.
3. En el servicio que se crea: **Settings → Source → Root Directory = `FISCAL/api`**. Railway detecta el `Dockerfile` y `railway.json`.
4. En el mismo proyecto: **New → Database → PostgreSQL**. Railway crea la base de datos.
5. En el servicio del API, pestaña **Variables**, agrega:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (referencia a la base del paso 4)
   - `APP_USUARIO` = el usuario del equipo (por ejemplo `fiscal`)
   - `APP_CLAVE` = una contraseña larga
6. **Settings → Networking → Generate Domain**. Esa es la dirección de la página (`https://….up.railway.app`).
7. Abre la dirección, entra con el usuario y la contraseña, ve a **Actualizar base de datos** y sube el `.zip` de
   `Fiscal/Scrapeo/output` (en Drive: clic derecho sobre la carpeta → Descargar) y, si quieres el histórico 2020-2026,
   `PIM_Funcion.xlsx`.

Cada vez que se fusiona un cambio a `main`, Railway vuelve a desplegar solo.

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
