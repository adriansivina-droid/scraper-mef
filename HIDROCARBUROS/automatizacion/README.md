# Actualización automática (GitHub Actions)

Corre los notebooks del proyecto **sin abrir Colab**, todos los días, y guarda los resultados en las mismas carpetas de Drive (DATA y CONTROL).

| Cuándo | Modo | Qué corre |
|---|---|---|
| Todos los días, 06:17 (hora de Lima) | `diario` | `PP_Produccion_Lotes.ipynb` (producción mensual y diaria, pozos, regalías, canon de PERUPETRO) → `PP_Mapa_Lotes_Plus.ipynb` (mapa simple y Plus) |
| El día 5 de cada mes | `mensual` | lo anterior + `PP_MEF_Canon_Municipal.ipynb` (año anterior y actual, «LOS 6 PETROLEROS», anual) |
| Cuando quieras | el que elijas | GitHub → **Actions → «Hidrocarburos · actualización» → Run workflow** |

Los notebooks corren con sus **valores por defecto**, como «Ejecutar todo» en Colab. Solo el del MEF se fija en el año anterior y el actual, para no consultar 20 años cada mes y no provocar el bloqueo (HTTP 403).

## Configuración (una sola vez)

1. **Credencial de Drive.** Abre `PP_Credencial_Drive.ipynb` en Colab y sigue los pasos. Descarga `credencial_drive.json`.
   - https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/HIDROCARBUROS/automatizacion/PP_Credencial_Drive.ipynb
2. **Secreto en GitHub.**
   - Ve al repositorio → **Settings → Secrets and variables → Actions → New repository secret**.
   - Nombre: `GOOGLE_DRIVE_CREDENCIAL`. Valor: todo el contenido de `credencial_drive.json`.
   - Después borra el archivo de tu computadora.
3. **Primera prueba.** Ve a **Actions → «Hidrocarburos · actualización» → Run workflow** y elige `diario`.

## Dónde ver los resultados

- **Drive:** DATA, CONTROL y DATA/MAPA, igual que con Colab.
- **GitHub, en cada ejecución:**
  - el **resumen** con cada paso y su estado (✅/❌) y los minutos que tomó;
  - el archivo **«mapas-y-resumen»**, con los HTML de los mapas, descargable por 14 días.
- Si algo falla, GitHub te envía un correo (lo hace por defecto con las ejecuciones fallidas).

## Archivos

- `ejecutar_notebooks.py`: ejecuta los notebooks en orden fuera de Colab.
  - Sustituye `google.colab` (la autenticación usa la credencial del secreto).
  - Quita las líneas `!pip`.
  - Cambia `/content/` por una carpeta de trabajo.
- `requirements.txt`: librerías.
- `PP_Credencial_Drive.ipynb`: genera la credencial de Drive.
- `../../.github/workflows/hidrocarburos_actualizar.yml`: el horario y los pasos.

## A tener en cuenta

- **La credencial es tuya**, con acceso a tu Drive. Vive solo en los secretos de GitHub, que nadie puede leer, ni siquiera en los registros.
  - Si la revocas (cuenta de Google → Seguridad → Acceso de terceros) o cambias tu contraseña, hay que generarla de nuevo.
- **PERUPETRO o el MEF podrían bloquear las direcciones de GitHub**, como el MEF hizo con Colab.
  - Si pasa, el paso sale ❌ con el mensaje del bloqueo.
  - Los demás pasos siguen, y el mapa se arma con lo que ya hay en Drive.
- **Uso:** si el repositorio es privado, GitHub Actions tiene minutos gratis limitados al mes; si es público, no hay límite. Revisa en Settings → Billing cuánto toma cada corrida y, si hace falta, cambia el horario diario a días hábiles.
- **Condiciones de uso:** antes de dejarlo corriendo a diario, revisa las del portal de PERUPETRO (descarga automática de sus estadísticas).

## Primera ejecución (22/10/2026)

- **Producción:** ✅ OK (44 min). Desde GitHub se conectó bien a PERUPETRO y a Drive.
- **Mapas:** ❌ El visor ArcGIS de PERUPETRO (perupetro.maps.arcgis.com) respondió «Invalid URL» desde GitHub. Desde Colab sí responde.
  - El notebook del mapa ya no se detiene por eso: sigue con el geoportal de PERUPETRO (WFS).
  - Si hoy ninguna fuente de lotes responde, usa los polígonos de la corrida anterior guardados en `DATA/MAPA/PP_lotes_indicadores.geojson` y lo avisa en el registro.
