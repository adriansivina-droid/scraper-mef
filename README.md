# Departamento de Estudios Económicos · BCRP, Sucursal Iquitos

Recolección, carga y presentación de los datos de la Síntesis de Actividad Económica de Loreto, San Martín y Ucayali.

```
scraper-mef/
├── PAGINA/                 página web «Departamento de estudios BCRP-IQT» (FastAPI, en Render; base en Neon)
│   ├── app/                    servidor: núcleo (main, db, catalogo, carga…) y un subpaquete por sector
│   │   ├── fiscal/                 ejecución del presupuesto, contraste con el MEF, ESTAD fiscal e IPC
│   │   ├── pesca/                  pesca (DIREPRO)
│   │   ├── exportaciones/          exportaciones e importaciones (SUNAT, Infotrade)
│   │   ├── empleo/                 empleo formal (MTPE)
│   │   ├── hidrologia/             ríos (SENAMHI) y reporte de situación hídrica
│   │   ├── hidrocarburos/          producción, canon y exportaciones de crudo (PERUPETRO)
│   │   ├── manufactura/            índice de volumen físico manufacturero
│   │   ├── drae/                   gráficos de las SERIES de cada departamento
│   │   └── static/                 lo que descarga el navegador (HTML, CSS y JavaScript)
│   ├── tests/                  pruebas (pytest)
│   └── README.md               despliegue, endpoints y flujos
│
├── FISCAL/                 notebooks y automatización del MEF (Consulta Amigable)
├── PESCA/                  notebooks de pesca y sus scripts
├── EXPORT/                 notebooks de exportaciones, arancel y padrón RUC
├── EMPLEO/                 scraper del empleo formal (MTPE)
├── HIDROLOGIA/             notebook del SENAMHI y herramienta de Power BI
├── HIDROCARBUROS/          Proyecto Petróleo: notebooks, fuentes, análisis y Power BI
│
├── .github/workflows/      tareas programadas y manuales de GitHub Actions
└── render.yaml             configuración del servicio en Render (carpeta PAGINA)
```

Cada carpeta de sector guarda lo propio de ese sector; el código del sector que corre en la página está en
`PAGINA/app/<sector>/`.
