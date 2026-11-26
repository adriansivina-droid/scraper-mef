# FISCAL · ejecución del presupuesto (MEF) y página web del departamento

```
FISCAL/
├── README.md                     este índice
├── CONTEXTO_PROYECTO.md          documento de traspaso: fuentes, rutas de consulta, columnas y decisiones
│
├── notebooks/                    extracción y procesamiento (Google Colab)
│   ├── Fiscal_Scraper.ipynb          devengado mensual y PIM de la Consulta Amigable (E, R y M)
│   ├── Fiscal_Procesamiento.ipynb    cuadros Fiscal-<Depto>_AUTO.xlsx y Principales variaciones
│   └── Fiscal_Proyectos.ipynb        proyectos detrás de las variaciones de la inversión
│
├── automatizacion/               los notebooks sin Colab, en GitHub Actions (.github/workflows/fiscal_*.yml)
│   ├── scraper_servidor.py           corre Fiscal_Scraper y carga lo descargado en la base (Neon)
│   ├── procesamiento_servidor.py     corre Fiscal_Procesamiento y guarda sus Excel en la página
│   ├── proyectos_servidor.py         corre Fiscal_Proyectos y guarda los proyectos en la base
│   ├── ingresos_mef.py               ingresos de los Gobiernos Regionales y Locales (Consulta Amigable de Ingresos)
│   ├── gasto_funcion.py              devengado por función de un departamento y periodo (CSV, sin tocar la base)
│   └── prueba_mef.py                 prueba de conexión con la Consulta Amigable (no guarda nada)
│
├── mantenimiento/
│   └── neon_revisar_tabla.py         solo lectura: tamaño y reparto de filas de una tabla de Neon
│
└── docs/
    └── Diccionario_Controles_MEF.xlsx
```

La página web está en la carpeta `PAGINA/` de la raíz; su parte fiscal, en `PAGINA/app/fiscal/`.

Abrir un notebook en Colab:
`https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/FISCAL/notebooks/<NOMBRE>.ipynb`
