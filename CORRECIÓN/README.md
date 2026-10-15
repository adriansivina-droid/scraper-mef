# Corrección · Servicio de la deuda

Versiones corregidas de `Fiscal_Scraper.ipynb` y `Fiscal_Procesamiento.ipynb`. Rutas, nombres de archivo y columnas son los mismos que antes.

## Por qué no funcionaba

1. **Scraper: la cadena Sub-Genérica no se validaba.** `calibrar()` probaba las claves `25-28` y aceptaba la primera que devolviera *cualquier* tabla, aunque listara otra dimensión. Además bajaba solo por la primera fila. Si la clave no era Sub-Genérica o Sub-Genérica Detalle, los rubros nunca contenían "amortización" ni "intereses". Entonces todas las filas salían como `CLASIFICACION = OTRO` o con error. Con una calibración fallida, también se usaba la lista `25-28` "por defecto, sin verificar".
2. **Procesamiento: el subtotal dependía solo del desglose.** `SERVICIO DE LA DEUDA = Intereses + Amortización`. Las filas `OTRO` se descartaban. Si `DEV Deuda` faltaba (como `GobNacional`) o venía incompleto (`GobRegional`: 18 filas desde 2025-06), el subtotal quedaba en 0 y los rubros en blanco. Eso es lo que muestra la captura.

## Qué cambió

**Scraper**
- `calibrar_deuda()` acepta una clave solo si todas sus filas son rubros de deuda. Prueba los 3 departamentos, los niveles R/M/E, el año y el anterior, y más claves candidatas. Si no encuentra la cadena, lo avisa y no guarda datos sin verificar. Para evitar el bloqueo de Incapsula, solo consulta donde la 2.8 tiene monto y descarta las claves que fallan (como máximo unas 45 consultas).
- `extraer_deuda()` guarda siempre una fila `CLASIFICACION = TOTAL` con el total de la genérica 2.8, aunque falle el desglose. También avisa las filas que quedan como `OTRO`.

**Procesamiento**
- El subtotal `SERVICIO DE LA DEUDA` sale de la genérica 2.8 de `DEV Generica`, que siempre se raspa. Si falta, usa la fila `TOTAL` de `DEV Deuda`.
- Las filas `OTRO` de los CSV ya existentes se reclasifican por el texto de `RUTA`.
- Los meses sin deuda se escriben como 0.
- Hay una nueva fila de control: `Deuda sin desglosar = total - (intereses + amortización)`.
- Ignora los archivos de prueba, los que terminan en ` - PRUEBA.csv` y salen de `PRUEBA_RAPIDA = True`, tanto en los datos como en los controles. La versión original ya lo hacía; se había perdido en la corrección.

## Rango de años
En el Bloque 2 del scraper:
```python
AÑO_INICIO = 2025; MES_INICIO = 1
AÑO_FIN = 2026;    MES_FIN = None   # None = último mes cerrado
```
Raspa de Enero 2025 hasta el último mes cerrado de 2026 (Setiembre, si se corre en octubre). Los años intermedios van completos. Los archivos, los controles y el PIM se siguen generando por año.

## Versión en uso
`Fiscal_Scraper.ipynb` es la versión con la que se trabaja (el archivo "Fiscal_Scraper (2)"):
- Procesa **mes por mes** y **guarda cada mes en Drive al terminarlo**. Si Colab se corta, lo hecho no se pierde.
- Cada corrida vuelve a descargar todos los meses del rango. Así recoge las revisiones que el MEF hace mes a mes, tanto de 2025 como de 2026.
- Tarda unos 4 minutos por mes de información.

Las pruebas de eficiencia (memoria de consultas, año completo en paralelo, reutilizar años cerrados) se descartaron. Una de ellas, reutilizar años cerrados, dejaba 2025 desactualizado. Quedan en el historial de git (commit `d172c90`) por si se retoman.

## Cómo usar
1. Corre `Fiscal_Scraper.ipynb` (conviene primero con `PRUEBA_RAPIDA = True`). Revisa la salida de "Calibrando sub-niveles…": debe terminar en `✅ cadena Sub-genérica = ['25']`. La clave 25 está verificada en el MEF real el 14/10/2026.
   Si dice que no la encontró: en Consulta Amigable entra a Genérica 2-8 y luego a Sub-Genérica. Copia la clave numérica nueva de la URL (F12 > Network) y ponla primera en `CANDIDATOS_SUBGENERICA`.
2. Para la corrida mensual usa `AÑO_INICIO = 2025`, `MES_INICIO = 1`, `AÑO_FIN = 2026` y `MES_FIN = None`, porque el MEF revisa ambos años. Vuelve a raspar los meses (`MES_INICIO = 1`) para regenerar `DEV Deuda.*`. Después corre `Fiscal_Procesamiento.ipynb`.
