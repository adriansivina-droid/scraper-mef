---
name: nota-metodologica
description: Redactar, revisar o corregir notas metodológicas del Departamento de Estudios Económicos (BCRP, Sucursal Iquitos) — p. ej. «Nota metodológica · Ejecución del presupuesto», en LaTeX o Word. Usar al escribir o editar cualquier sección de una nota metodológica, sus cuadros, gráficos, fórmulas o títulos, y al revisar la redacción de documentos técnicos del departamento. Reúne las reglas de redacción académica (Sánchez Upegui 2011; Ríos Ramírez 2017a, 2017b) y las convenciones que el usuario fijó en sus correcciones.
---

# Nota metodológica · guía de redacción

Una nota metodológica explica **cómo se obtiene** cada producto (origen de los datos → carga → cálculo → presentación),
para que otra persona pueda **repetir el proceso y llegar al mismo resultado**. Es un texto técnico-institucional: el
lector es un economista del BCRP que conoce el tema pero no el código. Detalle de las fuentes y citas: `referencias.md`.

## 0. Antes de tocar el texto

1. **No reescribir lo que el usuario ya redactó.** Las correcciones que haga el usuario se aprenden y se conservan
   (párrafos, giros, orden). Solo se cambia lo que pide, lo que deja de ser cierto o un error objetivo (ortografía,
   dato, referencia rota). Si algo de su redacción parece mejorable, se propone aparte; no se aplica.
2. Comparar contra la versión anterior (PDF compilado o archivo previo) para detectar qué cambió el usuario y seguir
   ese criterio en el resto del documento.
3. No mencionar dónde están los archivos internos (carpetas de la automatización, rutas de red, carpeta AUTOMATIZACION)
   ni datos internos que no deban circular.

## 1. Principios de estilo (Sánchez Upegui, cap. 1; Ríos 2017a, §1.2)

- **Claridad**: escribir para el lector que no conoce el sistema. «Escribe claro quien piensa claro». Explicar cada
  término técnico la primera vez (devengado, PIM, meta, IPC, panel, JSON…), sin caer en didactismo.
- **Precisión**: la palabra exacta, no el comodín. Ordenar las ideas con un criterio explícito (cronológico: el
  recorrido del dato; causal; de lo general a lo particular).
  - hacer → calcular, elaborar, ejecutar, construir · poner → incluir, ubicar · dar → presentar, entregar, arrojar ·
    tener → contener, registrar · ver → revisar, verificar · cosa/tema/aspecto → nombrar lo que es.
- **Concisión**: cada palabra con función. Sin muletillas («cabe mencionar», «es importante señalar», «a nivel de»,
  «en lo que respecta a»), sin repetir lo dicho en otra sección, sin verbos copulativos vacíos cuando hay un verbo
  pleno («es la encargada de calcular» → «calcula»). Concisión ≠ estilo telegráfico.
- **Simplicidad**: tras cada párrafo, preguntarse si puede decirse de forma más simple (Ríos 2017a, citando a Day).
- **Interpretar con datos, no opinar**: toda afirmación valorativa se apoya en una cifra, una fuente o un ejemplo.
- **Persona**: impersonal con «se» (se calcula, se compara, se toma) o sujeto institucional/técnico («la página
  calcula», «Render lee de Neon»). Nunca «yo»; «nosotros» solo si el usuario lo usa.
- **Registro**: formal y culto, sin coloquialismos. Anglicismos técnicos en cursiva la primera vez (*scraper*, *canvas*)
  con su equivalente: «programa de recolección (*scraper*)».

## 2. Coherencia y cohesión (Sánchez Upegui, cap. 2: normas de textualidad)

- **Coherencia**: cada sección responde a su título y todo el documento al objetivo de la presentación. Si una sección
  se borra o se fusiona, revisar las referencias a ella en el resto del texto («descrito en el apartado de Cálculos»).
- **Cohesión**: conectores que expliciten la relación lógica: adición (además, asimismo), contraste (sin embargo,
  en cambio), causa (porque, ya que), consecuencia (por ello, por lo tanto, así), orden (primero, luego, finalmente),
  ejemplificación (por ejemplo). Un hilo argumental, no una colección de ideas sueltas.
- **Reiteración controlada**: el mismo término para el mismo concepto en todo el documento (no alternar «inversión»,
  «inversión pública» y «gasto de capital» para lo mismo). Definirlo una vez y mantenerlo.
- **Informatividad**: cada párrafo aporta algo nuevo; lo ya explicado se remite («ecuación (2)», «Cuadro N° 3»).

## 3. Estructura de la nota (adaptación de IMRyD; Ríos 2017a, §2)

| Sección de la nota | Equivale a | Qué contiene |
|---|---|---|
| Presentación | Introducción | Objetivo (qué explica la nota y para qué), alcance y cómo se organiza el documento |
| I. Origen de los datos | Materiales | Fuentes, conceptos que se toman, cobertura (lugar, periodo), bases |
| II. Carga de los datos | Métodos: procedimientos e instrumentos | Arquitectura, herramientas y lenguajes, recolección, almacenamiento, controles de calidad |
| III. Metodología de cálculo de los indicadores | Métodos: estadígrafos | Cada indicador: fórmula, «Donde,», reglas especiales |
| IV. Producto final | Resultados | Lo que muestra la página, con su imagen y la explicación de cómo se genera |

- Los métodos deben permitir **repetir** el procedimiento (Ríos 2017a, §2.4.1): fuentes exactas (nombre del archivo,
  hoja, filtro), periodicidad, reglas de agrupación, tolerancias de control, software usado.
- **Tiempo verbal**: en un artículo los métodos van en pasado; en una nota metodológica que describe un proceso que
  sigue vigente se usa **presente** («el programa consulta», «se calcula»). Pasado solo para hechos puntuales
  («en 2026 se incorporó…»).
- Introducción: situación en presente; objetivo claro y único, con verbo en infinitivo si se enuncia
  («describir el proceso…»). No hacer una enciclopedia del tema.

## 4. Títulos (Ríos 2017b, cap. 2; Ríos 2017a, §2.1)

- Claros, precisos, breves; sin «Estudio de…», «Análisis de…» vacíos; sin siglas salvo las universales (MEF, INEI, PIM, IPC).
- Secciones en VERSALITAS/MAYÚSCULAS con número romano (I., II.…); subsecciones con arábigo (1., 2.…).
- Títulos «ejecutivos» que digan qué hay: «Metodología de cálculo de los indicadores», «Criterio de presentación de
  resultados», «Principales variaciones», «Avance condicional del presupuesto».

## 5. Cuadros, gráficos e imágenes (Ríos 2017a, §2.5.2)

- Numeración correlativa e independiente: **Cuadro N° k**, **Gráfico N° k**, **Imagen N° k** (con espacio tras «N°»).
  Siempre citados en el texto antes de aparecer («El Cuadro N° 2 resume…»).
- Título que diga **qué, dónde, cómo y cuándo**: «Loreto: inversión pública por nivel de gobierno».
  **Las fechas van debajo del título, en una línea aparte y entre paréntesis**: «Loreto: principales variaciones de la
  Inversión Pública\\ (Oct. 2026 / Oct. 2025)».
- Debajo, en letra menor: «Fuente: …» y «Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos.»
  (en capturas: «Captura de la página. Elaboración: …»; en esquemas: «Nota. …»).
- Deben entenderse solos; lectura vertical; palabras a la izquierda y números a la derecha (alineados por la coma);
  no cortar un cuadro entre páginas; sin celdas vacías sin explicar.
- Elegir el recurso: texto si hay pocos datos; cuadro para precisión; gráfico para tendencias y diferencias. El texto
  interpreta, no repite las cifras del cuadro.
- **No incluir imágenes ni listados de código.** Lo que hace el código se explica en prosa (qué recibe, qué calcula,
  qué entrega); se puede nombrar la función o el módulo (`ejecucion.py`, función `cuadros`) sin reproducirlo.

## 6. Fórmulas y variables

- Ecuación numerada y referida por su número automático (`\eqref{}`), nunca «ecuación (4)» escrito a mano.
- Inmediatamente después: **«Donde,»** (con coma, sin dos puntos) y una línea por variable: «símbolo : definición»
  con unidad y periodo. Definir todas las variables y solo una vez.
- Ejemplos numéricos con datos reales y redondeo explícito; van en recuadro «Ejemplo» y pueden quedar fuera de la
  versión de presentación (dos versiones del documento: con y sin ejemplos, conmutadas con un solo interruptor).

## 7. Convenciones fijadas por el usuario (no cambiarlas)

- **Nombres propios con mayúscula** en texto y títulos: Gobierno Nacional, Gobiernos Regionales, Gobiernos Locales,
  Gobierno Regional de Loreto, Inversión Pública, Gasto Corriente No Financiero, Presupuesto Institucional Modificado,
  Consulta Amigable, Loreto, San Martín, Ucayali. «Nivel de gobierno» y «niveles de gobierno» van en minúscula.
- **Categoría del gasto** (5 corrientes, 6 capital, 7 servicio de la deuda), no «tipo de transacción»; el primer dígito
  del código de la genérica (5-24 corriente, 6-24 capital).
- Números: miles con espacio y decimales con coma (1 886 347 223; 64,7 %). En LaTeX: `1\,886\,347\,223`, `64{,}7`.
- Mes abreviado: Ene., Feb., Mar., Abr., May., Jun., Jul., Ago., Set., Oct., Nov., Dic.
- Excel con mayúscula. Siglas desarrolladas la primera vez: Ministerio de Economía y Finanzas (MEF).
- Fuente de las cifras fiscales: «Fuente: MEF» (o «MEF e INEI» si hay IPC).

## 8. Plantilla LaTeX del departamento

Usar las macros que ya trae la nota (no inventar otras): `\cuadrotit`, `\graficotit`, `\imagentit`, `\bloquefig`
(con `\\` en el título para bajar la fecha), `\fuente{}`, `\elab`, `\notatabla{}`, `\donde` (fila «Donde,») y el
entorno `ejemplo` envuelto en `\ifconejemplos … \fi`. Compilar dos veces con pdflatex y dejar **0 avisos** (Overfull,
referencias indefinidas, `\headheight`). Antes de entregar, compilar las dos versiones.

## 9. Lista de control antes de entregar

- [ ] ¿Se conservó la redacción del usuario y solo se cambió lo pedido o lo que era un error?
- [ ] ¿Cada sección cumple lo que dice su título? ¿Las remisiones a secciones renombradas o borradas se actualizaron?
- [ ] ¿Todos los cuadros, gráficos, imágenes y ecuaciones están numerados, citados en el texto y con fuente/elaboración?
- [ ] ¿Las fechas de los títulos van en una segunda línea entre paréntesis?
- [ ] ¿Cada fórmula tiene «Donde,» y todas sus variables definidas?
- [ ] ¿Nombres propios con mayúscula, «categoría del gasto», números con espacio y coma?
- [ ] ¿Sin imágenes de código ni rutas internas?
- [ ] ¿Sin comodines (hacer, poner, dar, cosa), muletillas ni repeticiones? ¿Conectores entre párrafos?
- [ ] ¿Compila sin errores ni avisos, en las dos versiones?
