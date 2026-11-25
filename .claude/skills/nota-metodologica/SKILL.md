---
name: nota-metodologica
description: Redactar, revisar o corregir notas metodológicas del Departamento de Estudios Económicos (BCRP, Sucursal Iquitos) — p. ej. «Nota metodológica · Ejecución del presupuesto», en LaTeX o Word. Usar al escribir o editar cualquier sección de una nota metodológica, sus cuadros, gráficos, fórmulas o títulos, y al revisar la redacción de documentos técnicos del departamento. Reúne las reglas de redacción académica (Sánchez Upegui 2011; Ríos Ramírez 2017a, 2017b) y las convenciones que el usuario fijó en sus correcciones.
---

# Nota metodológica · guía de redacción

Una nota metodológica explica **cómo se obtiene** cada producto (origen de los datos → carga → cálculo → presentación)
para que otra persona pueda **evaluar su confiabilidad y repetir el proceso** hasta llegar al mismo resultado. Es un
texto técnico-institucional cuyo lector es un economista del BCRP que conoce el tema, pero no el código. Su género es
el del **artículo metodológico** (Sánchez Upegui, cap. 6): presenta un método, sus características, su rango de
aplicación y su comportamiento. El detalle de las fuentes y las citas está en `referencias.md`.

## 0. Antes de tocar el texto

1. **No reescribir lo que el usuario ya redactó.** Las correcciones que hace el usuario se aprenden y se conservan
   (párrafos, giros, orden). Solo se cambia lo que pide, lo que deja de ser cierto o un error objetivo (ortografía,
   dato, referencia rota). Si algo de su redacción parece mejorable, se propone aparte; no se aplica.
2. Comparar contra la versión anterior (el PDF compilado o el archivo previo) para detectar qué cambió el usuario y
   seguir ese criterio en el resto del documento.
3. No mencionar dónde están los archivos internos (carpetas de la automatización, rutas de red, carpeta AUTOMATIZACION)
   ni datos internos que no deban circular.
4. **Pre-redacción** (Sánchez, cap. 1). Antes de escribir una sección nueva, responder:
   - ¿Para qué se escribe? Para explicar y para que el proceso pueda reproducirse.
   - ¿Quién la lee?
   - ¿Qué idea central debe quedar?
   - ¿Qué va en la introducción, qué en el desarrollo y qué al cierre?

   Luego, hacer un esquema de ideas principales y secundarias antes de redactar.

## 1. Principios de estilo (Sánchez, cap. 1; Ríos 2017a, §1.2)

- **Claridad.** Escribir para el lector que no conoce el sistema («Escribe claro quien piensa claro»). Explicar cada
  término técnico la primera vez (devengado, PIM, meta, IPC, panel, JSON…), sin caer en didactismo. Usar frases cortas,
  lenguaje concreto, ejemplos, títulos enunciativos y conectores.
- **Precisión.** Usar la palabra exacta y no el comodín. Ordenar las ideas con un criterio explícito: el cronológico
  (el recorrido del dato), el causal, o de lo general a lo particular.
  - hacer → calcular, elaborar, ejecutar, construir
  - poner → incluir, ubicar
  - dar → presentar, entregar, arrojar
  - tener → contener, registrar
  - ver → revisar, verificar
  - cosa, tema, aspecto → nombrar lo que es
- **Concisión.** Cada palabra cumple una función.
  - Sin muletillas: «cabe mencionar», «es importante señalar», «a nivel de», «en lo que respecta a».
  - Sin repetir lo dicho en otra sección.
  - Sin copulativos vacíos cuando hay un verbo pleno: «es la encargada de calcular» → «calcula».
  - Concisión no es estilo telegráfico.
- **Simplicidad.** Después de cada párrafo, preguntarse si puede decirse de forma más simple (Ríos 2017a, citando a
  Day). Un texto técnico no lleva adornos literarios.
- **Interpretar con datos, no opinar.** Toda afirmación valorativa se apoya en una cifra, una fuente o un ejemplo.
- **Persona.** Usar el impersonal con «se» (se calcula, se compara, se toma) o un sujeto institucional o técnico («la
  página calcula», «Render lee de Neon»). Nunca «yo»; «nosotros» solo si el usuario lo usa.
- **Registro.** Formal y culto, sin coloquialismos. Los anglicismos técnicos van en cursiva la primera vez y con su
  equivalente: «programa de recolección (*scraper*)».
- **Microrredacción** (Sánchez, cap. 5, guía de evaluación). Revisar:
  - tildes, concordancia de género y número, queísmo y dequeísmo;
  - preposiciones y conjunciones;
  - el **gerundio**: solo para una acción simultánea o anterior; nunca de posterioridad ni como adjetivo;
  - la escritura de cifras;
  - el uso uniforme de negrita, cursiva, comillas y siglas.

## 2. Coherencia y cohesión (Sánchez, cap. 2: normas de textualidad)

- **Coherencia.** Cada sección responde a su título, y todo el documento responde al objetivo de la presentación. Si
  una sección se borra o se fusiona, hay que revisar las remisiones a ella en el resto del texto («descrito en el
  apartado de Cálculos»).
- **Cohesión.** Los conectores explicitan la relación lógica:

  | Relación | Conectores |
  |---|---|
  | Adición | además, asimismo |
  | Contraste | sin embargo, en cambio |
  | Causa | porque, ya que |
  | Consecuencia | por ello, por lo tanto, así |
  | Orden | primero, luego, finalmente |
  | Ejemplificación | por ejemplo |

  El texto debe tener un hilo argumental, no ser una colección de ideas sueltas.
- **Reiteración controlada.** Usar el mismo término para el mismo concepto en todo el documento. No alternar
  «inversión», «inversión pública» y «gasto de capital» para referirse a lo mismo. Se define una vez y se mantiene.
- **Deixis clara.** Nada de «este», «ahí», «actualmente» o «el mes pasado» sin referente. Escribir la fecha, el mes
  del informe o el nombre de la sección.
- **Informatividad.** Cada párrafo aporta algo nuevo. Lo ya explicado se remite: «ecuación (2)», «Cuadro N° 3».

## 3. Estructura de la nota

### 3.1 Presentación (introducción; modelo CARS de Swales, en Sánchez, cap. 6)

Va en tres movimientos, en este orden:
1. **Situar el tema.** Qué es el apartado de la síntesis y por qué importa (qué productos genera y para quién).
2. **Señalar el problema que resuelve.** Por ejemplo, el tiempo de elaboración manual, el riesgo de errores o la
   consistencia entre regiones.
3. **Presentar el trabajo.** El objetivo de la nota, con un verbo en infinitivo y un objetivo único, y la estructura
   del documento: qué contiene cada sección.

La situación se describe en presente. No se hace una enciclopedia del tema.

### 3.2 Cuerpo (movimientos de los métodos de Kanoksilapatham, en Sánchez, cap. 6)

| Sección de la nota | Movimiento | Qué debe decir |
|---|---|---|
| I. Origen de los datos | 1 · Materiales | Enumerar las fuentes, su procedencia (institución, módulo, archivo, hoja, filtros), sus antecedentes y la cobertura (lugar, periodo, unidades) |
| II. Carga de los datos | 2 · Procedimientos, y 3 · Equipos | Los pasos en orden cronológico, con detalle suficiente para repetirlos. La fecha, el momento y la duración de la recolección (Ríos 2017b, cap. 11). Las herramientas y los lenguajes. Los controles de calidad y las tolerancias |
| III. Metodología de cálculo de los indicadores | 4 · Procedimientos estadísticos | Para cada indicador: definición conceptual (qué mide), definición operacional (la fórmula), «Donde,», la unidad y las reglas especiales (Ríos 2017b, cap. 8) |
| IV. Producto final | Resultados | Por cada elemento: qué muestra, cómo se genera (remitiendo a las ecuaciones), cómo se lee y cuáles son sus límites |

- **Técnica de recolección.** Es un **análisis documental**: registros administrativos del MEF y del INEI. Se nombra
  así cuando haga falta clasificarla.
- **Tiempo verbal.** En un artículo los métodos van en pasado. En una nota que describe un proceso vigente se usa el
  **presente** («el programa consulta», «se calcula»). El pasado queda solo para hechos puntuales («en 2026 se
  incorporó…»).
- **Producto final.** Sigue el orden de los métodos. El texto interpreta y no repite las cifras de la imagen. No se
  vuelve a explicar el método: se remite a él.

### 3.3 Cierre (si la nota lo lleva: «Alcance y limitaciones» o «Consideraciones finales»)

- **Rango de aplicación y comportamiento del método.** Qué cubre y qué no (regiones, años, meses faltantes,
  revisiones del MEF). Qué pasa cuando falta un dato (por ejemplo, el IPC del mes: la variación sale nominal).
- **Conclusiones.** Se derivan de lo expuesto. No repiten el resumen ni agregan información nueva. Responden al
  objetivo de la presentación y pueden ser parciales.
- **Recomendaciones o trabajo futuro.** Se presentan en el orden de las conclusiones.

### 3.4 Resumen (solo si se pide)

Un párrafo de 150 a 250 palabras con objetivo, método, resultado principal y conclusión. Va en prosa y sin citas,
cuadros ni fórmulas.

## 4. Títulos (Ríos 2017b, cap. 2; Ríos 2017a, §2.1; Sánchez, cap. 6)

- **Forma.** Claros, precisos y breves, de hasta dos líneas. Sin «Estudio de…» ni «Análisis de…» vacíos. Sin siglas,
  salvo las universales (MEF, INEI, PIM, IPC). Cuidar el orden de las palabras: la mayoría de los fallos de un título
  vienen de la sintaxis o de la ambigüedad.
- **Numeración.**
  - Secciones en MAYÚSCULAS, con número romano (I., II.…).
  - Subsecciones con número arábigo (1., 2.…).
  - Los títulos internos deben guiar al lector.
- **Títulos «ejecutivos»** que digan qué hay. Por ejemplo: «Metodología de cálculo de los indicadores», «Criterio de
  presentación de resultados», «Principales variaciones», «Avance condicional del presupuesto».

## 5. Cuadros, gráficos e imágenes (Ríos 2017a, §2.5.2; Ríos 2017b, cap. 12)

- **Numeración.** Correlativa e independiente por tipo: **Cuadro N° k**, **Gráfico N° k**, **Imagen N° k**, con un
  espacio después de «N°». Siempre se citan en el texto antes de que aparezcan («El Cuadro N° 2 resume…»).
- **Título.** Debe decir qué, dónde, cómo y cuándo: «Loreto: inversión pública por nivel de gobierno». **Las fechas van
  debajo del título, en una línea aparte y entre paréntesis**: «Loreto: principales variaciones de la Inversión
  Pública\\ (Oct. 2026 / Oct. 2025)».
- **Pie.** Debajo, en letra menor:
  - «Fuente: …»;
  - «Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos.»;
  - en las capturas: «Captura de la página. Elaboración: …»;
  - en los esquemas: «Nota. …».
- **Formato.**
  - Deben entenderse solos y leerse en vertical.
  - Las palabras van a la izquierda y los números a la derecha, alineados por la coma.
  - Un cuadro no se corta entre páginas.
  - No quedan celdas vacías sin explicación.
- **Elección del recurso** (valoración de Rosenfeld). Texto si hay pocos datos; cuadro cuando importa la precisión;
  gráfico para mostrar tendencias y diferencias. Sin material gráfico irrelevante.
- **No incluir imágenes ni listados de código.** Lo que hace el código se explica en prosa: qué recibe, qué calcula y
  qué entrega. Se puede nombrar la función o el módulo (`ejecucion.py`, función `cuadros`) sin reproducirlo.

## 6. Fórmulas, variables e indicadores (Ríos 2017b, cap. 8)

- **Numeración.** Cada ecuación se numera y se cita por su número automático (`\eqref{}`), nunca escribiendo
  «ecuación (4)» a mano.
- **Antes de la fórmula, la definición conceptual.** Qué mide el indicador, en una o dos frases. La fórmula es su
  definición operacional.
- **Inmediatamente después, «Donde,»** (con coma y sin dos puntos), con una línea por variable: «símbolo :
  definición», incluida la unidad y el periodo. Se definen todas las variables y cada una solo una vez.
- **Ejemplos numéricos.** Con datos reales y el redondeo explícito, en un recuadro «Ejemplo». Pueden quedar fuera de la
  versión de presentación: el documento tiene dos versiones, con y sin ejemplos, que se cambian con un solo
  interruptor.

## 7. Fuentes y citas (Sánchez, cap. 3)

- **Fuentes de datos.** Se citan con la institución, el nombre exacto del producto (Consulta Amigable, archivo del IPC
  y su hoja), la dirección web completa y la fecha de consulta.
- **Citas textuales.** Siempre entre comillas, cerradas y con su fuente. Si pasan de 40 palabras, van en bloque.
- **Paráfrasis.** También llevan su fuente.
- **Un solo sistema de citación**, el que use el departamento. Todo lo citado aparece en las referencias y solo lo
  citado. Copiar la estructura de otro documento sin dar el crédito también es plagio.

## 8. Convenciones fijadas por el usuario (no cambiarlas)

- **Nombres propios con mayúscula**, en el texto y en los títulos: Gobierno Nacional, Gobiernos Regionales, Gobiernos
  Locales, Gobierno Regional de Loreto, Inversión Pública, Gasto Corriente No Financiero, Presupuesto Institucional
  Modificado, Consulta Amigable, Loreto, San Martín y Ucayali. «Nivel de gobierno» y «niveles de gobierno» van en
  minúscula.
- **Categoría del gasto** (5 gastos corrientes, 6 gastos de capital, 7 servicio de la deuda), no «tipo de
  transacción». Es el primer dígito del código de la genérica: la 5-24 es corriente y la 6-24 es de capital.
- **Números.** Miles con espacio y decimales con coma: 1 886 347 223; 64,7 %. En LaTeX: `1\,886\,347\,223` y
  `64{,}7`.
- **Meses abreviados:** Ene., Feb., Mar., Abr., May., Jun., Jul., Ago., Set., Oct., Nov., Dic.
- **Excel** con mayúscula. Las siglas se desarrollan la primera vez: Ministerio de Economía y Finanzas (MEF).
- **Fuente de las cifras fiscales:** «Fuente: MEF», o «MEF e INEI» si interviene el IPC.

## 9. Plantilla LaTeX del departamento

- **Macros.** Usar las que ya trae la nota, sin inventar otras: `\cuadrotit`, `\graficotit`, `\imagentit`,
  `\bloquefig` (con `\\` en el título para bajar la fecha), `\fuente{}`, `\elab`, `\notatabla{}`, `\donde` (la fila
  «Donde,») y el entorno `ejemplo`, envuelto en `\ifconejemplos … \fi`.
- **Compilación.** Compilar dos veces con pdflatex y dejar **0 avisos** (Overfull, referencias indefinidas,
  `\headheight`). Antes de entregar, compilar las dos versiones.

## 10. Lista de control antes de entregar (adaptada de la guía de evaluación de Sánchez, cap. 5)

**Fondo**
- [ ] ¿Se conservó la redacción del usuario y solo se cambió lo pedido o lo que era un error?
- [ ] ¿La presentación sitúa el tema, señala el problema y anuncia el objetivo y la estructura?
- [ ] ¿Cada fuente dice su procedencia exacta y su cobertura? ¿Los procedimientos permiten repetir el proceso?
- [ ] ¿Cada indicador tiene su definición conceptual, su fórmula y «Donde,» con todas las variables?
- [ ] ¿El producto final remite a las ecuaciones y no repite el método? ¿Se dicen los límites?

**Forma**
- [ ] ¿Cada sección cumple lo que dice su título? ¿Se actualizaron las remisiones a secciones renombradas o borradas?
- [ ] ¿Todos los cuadros, gráficos, imágenes y ecuaciones están numerados, citados en el texto y con su fuente o
      elaboración?
- [ ] ¿Las fechas de los títulos van en una segunda línea, entre paréntesis?
- [ ] ¿Los nombres propios van con mayúscula, se dice «categoría del gasto» y los números usan espacio y coma?
- [ ] ¿No hay imágenes de código ni rutas internas?
- [ ] ¿No hay comodines, muletillas, repeticiones, gerundios mal usados ni deixis sin referente? ¿Hay conectores entre
      los párrafos?
- [ ] ¿Las citas están entre comillas, con su fuente y con un solo sistema de citación?
- [ ] ¿Compila sin errores ni avisos, en las dos versiones?
