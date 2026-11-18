# Actualización automática (GitHub Actions)

Corre los notebooks del proyecto **sin abrir Colab**, todos los días, y publica los resultados en la **Release «hidrocarburos-datos»** del repositorio: el almacén de los notebooks (`almacen.sqlite`, con las mismas carpetas DATA y CONTROL que antes estaban en Drive y luego en la página) y los **CSV que lee Power BI**. Ya no usa Neon ni Drive.

| Cuándo | Modo | Qué corre |
|---|---|---|
| Todos los días, 07:00 (hora de Lima) | `diario` | `PP_Produccion_Lotes.ipynb` (producción mensual y diaria, pozos, regalías, canon de PERUPETRO) → `PP_Mapa_Lotes_Plus.ipynb` (mapa simple y Plus) |
| El día 5 de cada mes | `mensual` | lo anterior + `PP_MEF_Canon_Municipal.ipynb` (año anterior y actual, «LOS 6 PETROLEROS», anual) |
| Cuando quieras | el que elijas | GitHub → **Actions → «Hidrocarburos · actualización» → Run workflow** |

Los notebooks corren con sus **valores por defecto**, como «Ejecutar todo» en Colab. Solo el del MEF se fija en el año anterior y el actual, para no consultar 20 años cada mes y no provocar el bloqueo (HTTP 403).

## Archivos para Power BI (enlace fijo)

`https://github.com/adriansivina-droid/scraper-mef/releases/download/hidrocarburos-datos/<archivo>`

| Archivo | Qué trae |
|---|---|
| `hidro_produccion.csv` | Producción fiscalizada por mes, departamento, lote, operador (y empresa homologada) y producto. Los meses que la estadística mensual aún no publica salen de la producción diaria (columna FUENTE). |
| `hidro_canon.csv` | Canon y sobrecanon petrolero transferido por mes y departamento (millones de soles). |
| `hidro_lotes_operador.csv` | Qué lotes operó cada empresa cada año (para cruzar con las exportaciones por empresa). |
| `PP_mapa_lotes_plus.html` | El mapa de lotes (se abre con doble clic). |
| `LEEME.txt` | Fecha de la última actualización y filas de cada archivo. |

Son datos públicos de PERUPETRO y quedan públicos en el repositorio.

## Configuración (una sola vez)

1. **Pasar lo que había en Neon:** Actions → **«Hidrocarburos · pasar a GitHub»** → Run workflow. Copia el almacén de la página a la Release y publica los CSV. Solo lee Neon. Mientras la Release no tenga `almacen.sqlite`, el flujo diario no corre (para no perder los históricos).
2. **Prueba:** Actions → «Hidrocarburos · actualización» → Run workflow (`diario`).

## Dónde ver los resultados

- **La Release «hidrocarburos-datos»** (GitHub → Releases): los CSV y el mapa, con la fecha de la última corrida.
- **GitHub, en cada ejecución:**
  - el **resumen** con cada paso y su estado (✅/❌) y los minutos que tomó;
  - el archivo **«Mapa de Hidrocarburos - Perú»**: el mapa Plus en un solo HTML, descargable por 14 días. GitHub lo entrega dentro de un .zip; se descomprime y se abre con doble clic.
- Si algo falla, GitHub te envía un correo (lo hace por defecto con las ejecuciones fallidas).

## Archivos

- `ejecutar_notebooks.py`: ejecuta los notebooks en orden fuera de Colab.
  - Sustituye `google.colab` (la autenticación usa la credencial del secreto).
  - Quita las líneas `!pip`.
  - Cambia `/content/` por una carpeta de trabajo.
- `requirements.txt`: librerías.
- `publicar_powerbi.py`: arma los CSV para Power BI desde el almacén.
- `pasar_a_github.py`: copia una sola vez el almacén de Neon a la Release.
- `PP_Credencial_Drive.ipynb` y `migrar_drive.py`: de cuando los notebooks usaban Drive (ya no se usan en GitHub).
- `../../.github/workflows/hidrocarburos_actualizar.yml`: el horario y los pasos.

## A tener en cuenta

- **PERUPETRO o el MEF podrían bloquear las direcciones de GitHub**, como el MEF hizo con Colab.
  - Si pasa, el paso sale ❌ con el mensaje del bloqueo.
  - Los demás pasos siguen, y el mapa se arma con lo que ya hay en el almacén.
- **Uso:** si el repositorio es privado, GitHub Actions tiene minutos gratis limitados al mes; si es público, no hay límite. Revisa en Settings → Billing cuánto toma cada corrida y, si hace falta, cambia el horario diario a días hábiles.
- **Condiciones de uso:** antes de dejarlo corriendo a diario, revisa las del portal de PERUPETRO (descarga automática de sus estadísticas).

## Primera ejecución (22/10/2026)

- **Producción:** ✅ OK (44 min). Desde GitHub se conectó bien a PERUPETRO y a Drive.
- **Mapas:** ❌ El visor ArcGIS de PERUPETRO (perupetro.maps.arcgis.com) respondió «Invalid URL» desde GitHub. Desde Colab sí responde.
  - El notebook del mapa ya no se detiene por eso: sigue con el geoportal de PERUPETRO (WFS).
  - Si hoy ninguna fuente de lotes responde, usa los polígonos de la corrida anterior guardados en `DATA/MAPA/PP_lotes_indicadores.geojson` y lo avisa en el registro.
