# Hidrología en Power BI (en la PC)

SENAMHI no responde a servidores, así que la recolección sigue en el navegador. Lo que antes se subía a la página ahora lo procesa `actualizar_hidrologia.py` en la PC, y deja los CSV en una carpeta que lee Power BI.

## Una sola vez

1. **Python con SQLAlchemy:** `pip install sqlalchemy` (el mismo Python de AUTOMATIZACION).
2. **Carpeta:** en `configuracion.txt`, línea `CARPETA = …`. Si se deja vacía, se usa `Documentos\Power BI\Hidrologia`.
3. **Historial de la página:**
   1. GitHub → Actions → **«Hidrología · respaldo para Power BI»** → Run workflow.
   2. Al terminar, en la corrida, Artifacts → «Hidrologia - historial para Power BI».
   3. Descomprímelo y copia `hidrologia.sqlite` a la CARPETA.

## Cada día

1. Recolector en la consola de SENAMHI (como antes, ver `../senamhi_rios.md`): deja `SENAMHI_crudo_AAAA-MM-DD.json` en Descargas.
2. Doble clic en **`Actualizar hidrologia.bat`**.
3. Power BI → Inicio → **Actualizar**.

## Qué queda en la CARPETA

| Carpeta | Archivos |
|---|---|
| `DATA` | `SENAMHI_rios_diario.csv` (nivel y caudal diario por estación, con mínimo, máximo, promedio histórico y umbrales), `SENAMHI_rios_mensual.csv`, `SENAMHI_rios_info_diaria.csv`, `SENAMHI_ESTACIONES.csv` (con departamento y coordenadas), `SENAMHI_rios_diario_no_publicado.csv` |
| `CONTROL` | Controles de la recolección (la columna ESTADO debe decir OK) |
| `ENTRADA\procesados` | Los JSON ya leídos |
| — | `hidrologia.sqlite` (historial; no borrar) y `LEEME.txt` (fecha de la última actualización) |

`motor/` (en el paquete para la PC) trae una copia de `hidrologia.py` de la página; en el repositorio se usa `FISCAL/api/app/hidrologia.py`.
