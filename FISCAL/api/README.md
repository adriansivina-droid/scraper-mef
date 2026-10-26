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

Objetivo a largo plazo: que el API arme la **Síntesis de Actividad Económica** mensual de Loreto, San Martín y Ucayali
(estructura tomada de los informes de junio de 2026). Cada sección sería un módulo con el mismo esquema que Fiscal:
scraper (o carga de una plantilla) → base de datos → descargas en Excel → cuadros y anexos.

| Sección | Cuadros y anexos | Fuente (según los informes) | Cómo se obtiene | Estado |
|---|---|---|---|---|
| Resumen · otros indicadores | Cuadro 1 | SBS, MEF, DIREPRO y empresas | se arma con los demás módulos | al final |
| Agropecuario | producción (t), superficie sembrada (ha) · Anexo 1 | MIDAGRI; GERDAGRI Loreto, DRAU Ucayali, DRA San Martín | MIDAGRI por web; las direcciones regionales, por plantilla | falta |
| Pesca (Ucayali) | producción pesquera · Anexo 2 | DIREPRO Ucayali | plantilla | falta |
| Hidrocarburos (Loreto, Ucayali) | producción y precio · Anexo de petróleo crudo | PERUPETRO; precio, Reuters | scraper en `HIDROCARBUROS/` (diario en GitHub Actions); precio por plantilla | scraper listo |
| Manufactura | índice de volumen físico · Anexos | DIREPRO y encuesta BCRP a empresas industriales | plantilla (no es pública) | falta |
| Empleo | trabajadores asalariados privados formales, por sector · Anexo | MTPE, Planilla Electrónica (PLAME y T-Registro) | web del MTPE | falta |
| Exportaciones | por grupo de productos · Anexo | SUNAT | scraper en `EXPORT/` (Infotrade) | scraper listo |
| Importaciones (Loreto) | FOB por uso o destino, aduana de Iquitos · Anexo | SUNAT | web de SUNAT | falta |
| Crédito, depósitos y morosidad | saldos, crédito por tipo sin BN ni Agrobanco · Anexos | SBS y AFP (Carpeta de Información del Sistema Financiero) | web de la SBS | falta |
| Gasto corriente no financiero | por nivel, mes y acumulado, var. % real · Anexos de ejecución por nivel | MEF, Consulta Amigable | `Fiscal_Scraper` + API | **en el API** (fase 1) |
| Inversión pública | por nivel, var. % real y avance del PIM · Anexos de inversión por nivel | MEF, Consulta Amigable | `Fiscal_Scraper` + API | **en el API** (fase 1) |

Lo que no es público (DIREPRO, encuesta BCRP a empresas, direcciones regionales de agricultura, precio Reuters) entra por
**plantillas de Excel** que el equipo sube en la página; el resto se baja solo.

**Arquitectura:** Render sirve la página y las descargas; Neon guarda los datos; los scrapers corren en **GitHub Actions**
(como hoy los de hidrocarburos) y escriben directo en Neon. Así el servidor web sigue siendo el más barato.

**Orden propuesto:** (1) desplegar Fiscal y sus fases 2 y 3 (scraper en GitHub Actions y reportes); (2) sumar
hidrocarburos y exportaciones, que ya tienen scraper; (3) SBS (crédito, depósitos y morosidad), MTPE (empleo), MIDAGRI e
importaciones; (4) plantillas para lo no público; (5) un botón que genere los cuadros y anexos del mes por región.

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
