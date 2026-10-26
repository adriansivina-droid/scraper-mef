# PESCA · Producción pesquera de Loreto, San Martín y Ucayali

Alimenta la sección de **pesca** de las síntesis regionales (producción pesquera y su anexo). Los datos no se scrapean:
cada DIREPRO manda un Excel mensual que se lleva a una tabla larga (LONG) y, de ahí, al VBP. Dos notebooks:
`Pesca_Loreto_Long.ipynb` (Loreto) y `Pesca_SMN_UCA_Long.ipynb` (San Martín y Ucayali).

**VBP = VOLUMEN (t) × precio base 2007** (miles de soles por tonelada), en miles de soles de 2007:

| Estado | Precio base 2007 (S/ por t) | En el LONG (miles de S/ por t) |
|---|---|---|
| Fresco | 3 275,04 | 3.27504 |
| Salpreso | 3 015,89 | 3.01589 |
| Seco salado | 2 987,78 | 2.98778 |
| Peces ornamentales | 1 032,90 por mil unidades | 1.0329 (miles de S/ por mil unidades) |

## Cómo llega y cómo se transforma cada región

| | Loreto | San Martín | Ucayali |
|---|---|---|---|
| Archivo | `CONSUMO_<MES>_-_<AÑO>-OPP.xlsx` y `P._ORNAMENTALES_<MES>_-_OPP_<AÑO>.xlsx` (DIREPRO Loreto, OPP), **un mes** por archivo | `SMN_PESCA_<AÑO>-<MES>.xlsx`, un mes | `ESTADISTICA_PESQUERA_DIREPRO_UCA_<AÑOMES>-<AÑOMES>.xlsx`, **acumulado del año**, un mes por columna |
| Forma | Un cuadro por estado: N° · Especie · 8 localidades · Total, con la fila Total arriba | Una hoja: procedencia (acuicultura / continental), especie y una columna por estado, **en kg** | Hojas `TOTAL FRESCO` y `TOTAL SECOSALADO` (especie × mes, en t) y ornamentales (unidades) |
| Qué se toma | **Desembarque**: hojas `Desemb_Fres`, `Desemb_salpr` y `Desemb_secosalad` (Cuadros 06–08); ornamentales: hoja `POR ESPECIES` | Volumen por estado | Desembarque (Cuadro 01) |
| LONG | `LOR_PESCA_LONG.xlsx`, hoja `LOR_PESCA` (`Pesca_Loreto_Long.ipynb`) | `SMN_PESCA_LONG.xlsx`, hoja `SMN_PESCA` (`Pesca_SMN_UCA_Long.ipynb`) | `UCA_PESCA_LONG.xlsx`, hoja `UCA_PESCA` (`Pesca_SMN_UCA_Long.ipynb`) |
| Especies principales (`*_OK`) | Las 35 del Cuadro Nº 07 (Indicadores del sector pesquero); el resto, Otros | Boquichico, Camarón gigante, Gamitana, Paco, Paiche, Tilapia; el resto, Otras | Bagre, Boquichico, Chiu Chiu, Palometa, Ractacara, Sardina; el resto, Otros |
| Estados con VBP | fresco, salpreso, seco salado y ornamentales | fresco (salpreso y seco salado van en 0) | fresco y seco salado (ornamentales en 0) |

## Carpeta en Drive

Todo vive en la carpeta **PESCA** de Drive (`PESCA_FOLDER_ID = 1wJP-N4A6AjHto__hJmWx-EE21nKiNB5i`). Los notebooks la
leen y escriben por su ID (API de Drive, como `subir_xlsx_a_drive` de Fiscal; piden autorizar la cuenta la primera vez)
y crean solos lo que falte:

```
PESCA/
├── LORETO/       CRUDOS/ · RESPALDOS/ · LOR_PESCA_LONG.xlsx
├── SAN MARTÍN/   CRUDOS/ · RESPALDOS/ · SMN_PESCA_LONG.xlsx
└── UCAYALI/      CRUDOS/ · RESPALDOS/ · UCA_PESCA_LONG.xlsx
```

- **CRUDOS:** aquí se dejan los Excel que manda cada DIREPRO. Pueden quedarse: volver a procesarlos no duplica nada.
  En Ucayali, si hay varias versiones del acumulado del año, gana la última por nombre (`…_202601-202609` sobre
  `…_202601-202608`).
- **RESPALDOS:** antes de reemplazar un LONG, el notebook copia aquí el anterior como
  `<nombre>_respaldo_<fecha_hora>.xlsx`.
- La primera corrida con la carpeta vacía solo crea las subcarpetas y avisa que faltan los crudos.

## Loreto: `Pesca_Loreto_Long.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/PESCA/Pesca_Loreto_Long.ipynb

1. **Bloque 1 · Parámetros.** `PESCA_FOLDER_ID`, `FUENTE`, `PRECIOS`, `ESPECIES_07`, `ESPECIES_FRESCO`,
   `ESPECIES_CUADRO` y `CORRECCIONES`. Con `SUBIR_A_MANO = True` pide los archivos con un botón y los guarda en
   `PESCA/LORETO/CRUDOS`.
2. **Bloque 2 · Funciones.** Para cada crudo:
   - lee el mes del rótulo `PERIODO : FEBRERO - 2026`;
   - ubica las hojas por nombre (`Desemb_Fres`, `Desemb_salpr`, `Desemb_secosalad`, o las `Extrac_*`);
   - toma la columna Total de cada especie hasta la fila NOTA o FUENTE, y avisa si la suma no cuadra con la fila Total;
   - normaliza el nombre (`ESPECIE_CORREGIDA`; por ejemplo, «Manitoa» pasa a «Zúngaro Manitoa»);
   - asigna `ESPECIE_OK`: la especie, escrita como en el Cuadro Nº 07, si figura en él; «Otros» para el resto (por
     ejemplo Bagre, Bocón, Zúngaro Toa y Zúngaro Achacubo);
   - asigna `ESPECIE_CUADRO`, el grupo del cuadro de producción pesquera: Boquichico, Llambina/Palometa u Otros;
   - calcula el VBP.
   - si el crudo es de ornamentales (tiene la hoja `POR ESPECIES`), toma de la tabla por especie las unidades por
     destino: exportación → «Mercado externo», nacional → «Mercado interno» y stock remanente y/o mortandad, en miles
     de unidades (la suma es el ingreso). Se detiene en la fila TOTAL, así que no lee la tabla de principales especies
     que viene debajo.
3. **Bloque 3 · Generar.** Baja los crudos de `PESCA/LORETO/CRUDOS`, procesa todos (consumo y ornamentales juntos) y
   reemplaza en el histórico los meses que traen, cada tipo por separado (el resto se conserva, y recargar no duplica). Guarda tres hojas, con un mes por
   columna en los cuadros:
   - `LOR_PESCA`: el LONG;
   - `CUADRO`: «Loreto: producción pesquera»: Valor Bruto Pesquero, toneladas en estado fresco, seco salado y salpreso
     (con su precio de 2007), Boquichico, Llambina/Palometa y peces ornamentales;
   - `CUADRO_07`: «Loreto: indicadores del sector pesquero»: desembarque total por estado de conservación, por especie
     (las 35 del cuadro y Otros), peces ornamentales por destino y el bloque «Desembarque fresco» (19 especies y
     Otras especies). Avisa si el total por estado no coincide con el total por especie, o si el bloque fresco no suma
     el fresco.

Columnas de `LOR_PESCA`: `AÑO, MES, DEPARTAMENTO, FUENTE, ESTADO, DESTINO, ESPECIE, ESPECIE_CORREGIDA, ESPECIE_OK,
ESPECIE_CUADRO, UNIDAD, VOLUMEN, VBP`.

- **Pescado** (consumo humano directo): `UNIDAD = t`, `DESTINO` vacío.
- **Peces ornamentales:** `ESTADO = ORNAMENTAL`, `UNIDAD = miles de unidades`, `DESTINO` como en el Cuadro Nº 07
  (mercado externo, mercado interno, stock remanente y/o mortandad). `ESPECIE` es el nombre común,
  `ESPECIE_CORREGIDA` el nombre científico y `ESPECIE_OK` y `ESPECIE_CUADRO` dicen «Peces ornamentales».
  Hay nombres comunes repetidos con distinto nombre científico, por eso el nombre científico distingue cada fila.
  VBP = miles de unidades × 1.0329.

**¿Desembarque o extracción?** El crudo trae los dos. El desembarque (Cuadros 06–08) es el que DIREPRO Loreto usa en su
resumen (Cuadro 17) y el mismo concepto que el LONG de Ucayali. La extracción (Cuadros 02–04) es mayor: en el fresco,
el desembarque equivale a extracción ÷ 1,3. Para cambiar, se pone `FUENTE = 'EXTRACCION'`; la columna `FUENTE` del LONG
dice cuál se usó.

Febrero de 2026, como control:

| Estado | Desembarque (t) | VBP (miles de S/ de 2007) | Extracción (t) |
|---|---|---|---|
| Fresco | 162,467 | 532,086 | 211,207 |
| Salpreso | 0,787 | 2,374 | 1,842 |
| Seco salado | 17,501 | 52,289 | 56,878 |
| **Total** | **180,755** | **586,749** | 269,927 |

Por especie: Boquichico 34,146 t y Llambina/Palometa 19,948 t (15,534 + 4,414). Las 58 especies del LONG coinciden
una por una con el Cuadro 05 de DIREPRO (volumen total de desembarque), y los totales por estado con el Cuadro 18. En
el Cuadro Nº 07, «Otros» suma 16,229 t.

Ornamentales de setiembre de 2025: 396,249 miles de unidades (322,727 al mercado externo y 73,522 al interno, sin
stock), con un VBP de 409,286 miles de S/ de 2007.

## San Martín y Ucayali: `Pesca_SMN_UCA_Long.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/PESCA/Pesca_SMN_UCA_Long.ipynb

Reproduce los LONG que ya se armaban a mano. Probado contra ellos:
- **San Martín, agosto de 2026:** las 57 filas salen idénticas al LONG existente, volumen y VBP incluidos.
- **Ucayali, 2026:** las 2 602 filas tienen las mismas especies y clasificaciones, y de enero a julio los mismos
  volúmenes. En agosto y setiembre el LONG anterior tenía los volúmenes redondeados a enteros; el notebook usa las
  cifras exactas del crudo (por ejemplo, fresco de agosto: 473,618 t en vez de 472).

1. **Bloque 1 · Parámetros.** `PESCA_FOLDER_ID` y los precios.
2. **Bloque 2 · Funciones.**
   - **San Martín** (un archivo por mes, en kg): el mes sale del nombre del archivo (`SMN_PESCA_2026-08.xlsx`,
     porque el crudo no lo trae adentro).
     - Especies de San Martín: una fila por especie y estado con volumen. `ORIGEN` es Acuicultura (acuicultura
       continental) o Extracción de ríos (continental), y `ESTADO_OK` junta fresco y fresco refrigerado.
     - Lo que llega de otros departamentos (Pucallpa, Loreto, Piura, Chiclayo, Lima, Trujillo…): una fila por
       procedencia y estado con su total, con `DEPARTAMENTO = Otros` y `ESPECIE` = CONTINENTAL o MARÍTIMO.
     - VBP: solo para lo de San Martín; lo de otros departamentos va en 0.
   - **Ucayali** (acumulado del año, en t): lee los cuadros `TOTAL FRESCO`, `TOTAL SECOSALADO`, `TOTAL DE PESCADO`
     (TIPO = AGREGADO) y `ORNAMENTALES` (unidades; solo las celdas con datos). Los meses salen de los encabezados
     (`2026-01-01`…). VBP: fresco y seco salado; agregado y ornamentales van en 0, como en el LONG anterior.
   - **Especies:** `ESPECIE_OK` (San Martín) y `ESPECIES_CORREGIDO` / `ESPECIES_OK` (Ucayali) se toman del propio
     LONG histórico, así que siguen exactamente tu criterio. Una especie que nunca apareció se avisa y recibe un
     valor por defecto: en San Martín, la principal de su origen o «Otras»; en Ucayali, el nombre en formato título
     y, en fresco y agregado, «Otros». Conviene revisarla y corregirla en el LONG; desde entonces queda aprendida.
3. **Bloques 3 y 4 · Generar.** Bajan los crudos de `PESCA/SAN MARTÍN/CRUDOS` y `PESCA/UCAYALI/CRUDOS`, los procesan
   todos y reemplazan los periodos que traen: el mes en San Martín, el año completo en Ucayali. El periodo reemplazado
   queda en el mismo lugar del archivo y el resto se conserva en su orden. El archivo nuevo solo trae la hoja de datos y
   una hoja `VBP` (por mes y estado o tipo): las tablas dinámicas que tuviera (Hoja1, Hoja2) quedan en el respaldo.

La primera vez, sube tus LONG actuales a `PESCA/SAN MARTÍN/SMN_PESCA_LONG.xlsx` y `PESCA/UCAYALI/UCA_PESCA_LONG.xlsx`
(con sus hojas `SMN_PESCA` y `UCA_PESCA`; corre antes el notebook una vez para que cree las carpetas). Si no están, el
notebook los crea solo con lo que traen los crudos, pero sin el histórico no sabe tu clasificación de especies.

## Cuidados

- Si DIREPRO cambia el nombre de las hojas o el rótulo PERIODO, el notebook se detiene con un mensaje que dice qué no
  encontró.
- Una especie nueva entra sola como «Otros» (o como «Zúngaro»). Si el crudo la escribe distinto que el Cuadro Nº 07, se
  agrega a `CORRECCIONES`.
- En el API, los tres LONG entrarán como archivo mensual de pesca (hoja de ruta en `FISCAL/api/README.md`).
