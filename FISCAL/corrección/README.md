# Corrección · Servicio de la deuda

Versiones corregidas de `Fiscal_Scraper.ipynb` y `Fiscal_Procesamiento.ipynb`. Rutas, nombres de archivo y columnas son los mismos que antes.

## Por qué no funcionaba

1. **Scraper: la cadena Sub-Genérica no se validaba.** `calibrar()` probaba las claves `25-28` y aceptaba la primera que devolviera *cualquier* tabla, aunque listara otra dimensión. Además bajaba solo por la primera fila. Si la clave no era Sub-Genérica o Sub-Genérica Detalle, los rubros nunca contenían "amortización" ni "intereses". Entonces todas las filas salían como `CLASIFICACION = OTRO` o con error. Con una calibración fallida, también se usaba la lista `25-28` "por defecto, sin verificar".
2. **Procesamiento: el subtotal dependía solo del desglose.** `SERVICIO DE LA DEUDA = Intereses + Amortización`. Las filas `OTRO` se descartaban. Si `DEV Deuda` faltaba (como `GobNacional`) o venía incompleto (`GobRegional`: 18 filas desde 2025-06), el subtotal quedaba en 0 y los rubros en blanco. Eso es lo que muestra la captura.

## Qué cambió

**Scraper**
- `calibrar_deuda()` acepta una clave solo si todas sus filas son rubros de deuda. Prueba los 3 departamentos, los niveles R/M/E, el año y el anterior, y más claves candidatas. Si no encuentra la cadena, lo avisa y no guarda datos sin verificar.
- `extraer_deuda()` guarda siempre una fila `CLASIFICACION = TOTAL` con el total de la genérica 2.8, aunque falle el desglose. También avisa las filas que quedan como `OTRO`.

**Procesamiento**
- El subtotal `SERVICIO DE LA DEUDA` sale de la genérica 2.8 de `DEV Generica`, que siempre se raspa. Si falta, usa la fila `TOTAL` de `DEV Deuda`.
- Las filas `OTRO` de los CSV ya existentes se reclasifican por el texto de `RUTA`.
- Los meses sin deuda se escriben como 0.
- Hay una nueva fila de control: `Deuda sin desglosar = total - (intereses + amortización)`.

## Cómo usar
1. Corre `Fiscal_Scraper.ipynb` (conviene primero con `PRUEBA_RAPIDA = True`). Revisa la salida de "Calibrando sub-niveles…": debe terminar en `✅ cadena Sub-genérica = [...]`.
   Si dice que no la encontró: en Consulta Amigable entra a Genérica 2-8 y luego a Sub-Genérica. Copia la clave numérica nueva de la URL (F12 > Network) y ponla primera en `CANDIDATOS_SUBGENERICA`.
2. Vuelve a raspar los meses (`MES_INICIO = 1`) para regenerar `DEV Deuda.*`. Después corre `Fiscal_Procesamiento.ipynb`.
