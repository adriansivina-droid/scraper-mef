# Hidrología en Power BI (sin instalar nada en la PC)

SENAMHI no responde a servidores, así que la recolección sigue en el navegador. El JSON que deja se sube a la Release
**«hidrologia-datos»** de GitHub y GitHub hace el resto: lo suma al historial (`hidrologia.sqlite`, en la misma Release),
rearma los CSV y los publica con enlace fijo para Power BI:

`https://github.com/adriansivina-droid/scraper-mef/releases/download/hidrologia-datos/<archivo>`

## Una sola vez

GitHub → Actions → **«Hidrología · pasar a GitHub»** → Run workflow. Copia el historial de la página (Neon, solo lectura)
y publica los CSV.

## Cada día

1. Recolector en la consola de SENAMHI (`../senamhi_rios.md`): deja `SENAMHI_crudo_AAAA-MM-DD.json` en Descargas.
2. GitHub → **Releases** → «Hidrología · datos para Power BI» → lápiz (**Edit**) → arrastra el JSON a «Attach binaries» →
   **Update release**.
3. En unos minutos corre «Hidrología · actualización» (también cada 2 horas, por si acaso): suma el JSON, rearma los CSV y
   borra el JSON de la Release.
4. Power BI → Inicio → **Actualizar**.

## Archivos de la Release

| Archivo | Qué trae |
|---|---|
| `SENAMHI_rios_diario.csv` | Nivel y caudal diario por estación, con mínimo, máximo, promedio histórico y umbrales |
| `SENAMHI_rios_mensual.csv` | Información Mensual (valor del mes, anomalía, tendencia) |
| `SENAMHI_rios_info_diaria.csv` | Información Diaria (cada 6 horas) |
| `SENAMHI_ESTACIONES.csv` | Estaciones con departamento y coordenadas |
| `SENAMHI_rios_diario_no_publicado.csv` | Días que SENAMHI no publica en el hidrograma |
| `CONTROL_*.csv`, `LOG_*.csv` | Controles de la recolección (ESTADO debe decir OK) |
| `hidrologia.sqlite` | El historial (no se usa en Power BI) |
| `LEEME.txt` | Fecha de la última actualización |

## Programas

- `actualizar_hidrologia.py`: suma los JSON al historial y arma los CSV. Lo corre GitHub; también sirve en una PC con Python (`Actualizar hidrologia.bat`, carpeta en `configuracion.txt`).
- `publicar_release.sh`: los pasos de GitHub (bajar, armar, publicar, borrar el JSON).
- `respaldo_desde_neon.py`: copia una vez el historial de la página.
