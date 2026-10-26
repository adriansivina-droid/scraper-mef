# EMPLEO · Trabajadores formales por región y actividad (MTPE)

Scraper del tablero de Power BI del MTPE con el empleo formal privado (Planilla Electrónica: PLAME y T-Registro), por
región y actividad económica. Alimenta la sección **II. Aspectos laborales · Empleo** de las síntesis regionales
(cuadro de trabajadores asalariados privados formales y su anexo por sectores). Es independiente de los scrapers del MEF
(`FISCAL/`).

**Notebook:** `EMPLEO/Scraping_MTPE_Empleo_x_Region_Actividad.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/EMPLEO/Scraping_MTPE_Empleo_x_Region_Actividad.ipynb

## Cómo funciona

1. **Instalación:** Playwright con Chromium, y Tesseract (OCR), que se instala aunque hoy el código no lo usa.
2. **Selector de región:** pide por teclado una o varias regiones de una lista de 27 (Perú, los departamentos, y Lima
   Metropolitana y Lima Provincias por separado): un número (`18`), varios (`18,24,27`), un rango (`3-10`) o `all`.
3. **Extracción:** abre el tablero (`EMBED_URL`), entra a «EVOLUCIÓN» y, por cada región y cada actividad, marca los
   filtros, activa todos los años, pasa el gráfico a tabla («Mostrar como tabla») y la recorre con scroll.
   - Actividades: Agrícola, Minería, Manufactura, Construcción, Comercio, Servicios y No precisa.
4. **Salida:** un Excel con columnas `AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO`, ordenado por región, actividad,
   año y mes. El nombre depende de la selección: `Ucayali_empleo.xlsx`, `Loreto_San_Martín_Ucayali_empleo.xlsx` o
   `N_regiones_empleo.xlsx`. Antes de descargar revisa que no falten meses por región y actividad.

## Cuidados

- La navegación depende de la posición de los elementos del tablero (coordenadas fijas y textos de los botones). Si el
  MTPE cambia el diseño del Power BI, hay que ajustar esos clics.
- La descarga final usa `files.download()` de Colab, que a veces falla sin aviso (ver `FISCAL/CONTEXTO_PROYECTO.md`
  §8). Si no baja, el archivo queda en el panel de archivos de Colab.
- En el API, el Excel que genera este notebook se cargará como archivo mensual de empleo (hoja de ruta en
  `FISCAL/api/README.md`).
