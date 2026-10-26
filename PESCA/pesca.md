# PESCA · Producción pesquera de Loreto, San Martín y Ucayali

Alimenta la sección de **pesca** de las síntesis regionales (producción pesquera y su anexo). Los datos no se scrapean:
cada DIREPRO manda un Excel mensual que se lleva a una tabla larga (LONG) con el mismo esquema y, de ahí, al VBP.

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
| LONG | `LOR_PESCA_LONG.xlsx`, hoja `LOR_PESCA` (este notebook) | `SMN_PESCA_LONG`, hoja `SMN_PESCA` | `UCA_PESCA_LONG`, hoja `UCA_PESCA` |
| Especies principales (`*_OK`) | Las del Cuadro Nº 07 (Indicadores del sector pesquero); los demás zúngaros, Zúngaro; el resto, Otros | Boquichico, Camarón gigante, Gamitana, Paco, Paiche, Tilapia; el resto, Otras | Bagre, Boquichico, Chiu Chiu, Palometa, Ractacara, Sardina; el resto, Otros |
| Estados con VBP | fresco, salpreso, seco salado y ornamentales | fresco (salpreso y seco salado van en 0) | fresco y seco salado (ornamentales en 0) |

## Loreto: `Pesca_Loreto_Long.ipynb`

Abrir en Colab:
https://colab.research.google.com/github/adriansivina-droid/scraper-mef/blob/main/PESCA/Pesca_Loreto_Long.ipynb

1. **Bloque 1 · Parámetros.** `CARPETA_CRUDOS` (los Excel de DIREPRO en Drive), `RUTA_LONG` (el histórico, que se crea
   si no existe), `FUENTE`, `PRECIOS`, `ESPECIES_07`, `ESPECIES_CUADRO` y `CORRECCIONES`. Con `SUBIR_A_MANO = True` pide los archivos con
   un botón.
2. **Bloque 2 · Funciones.** Para cada crudo:
   - lee el mes del rótulo `PERIODO : FEBRERO - 2026`;
   - ubica las hojas por nombre (`Desemb_Fres`, `Desemb_salpr`, `Desemb_secosalad`, o las `Extrac_*`);
   - toma la columna Total de cada especie hasta la fila NOTA o FUENTE, y avisa si la suma no cuadra con la fila Total;
   - normaliza el nombre (`ESPECIE_CORREGIDA`; por ejemplo, «Manitoa» pasa a «Zúngaro Manitoa»);
   - asigna `ESPECIE_OK`: la especie si figura en el Cuadro Nº 07; «Zúngaro» para los zúngaros sin fila propia
     (Achacubo, Alianza, Tabla Barba, Toa, Torre); «Otros» para el resto;
   - asigna `ESPECIE_CUADRO`, el grupo del cuadro de producción pesquera: Boquichico, Llambina/Palometa u Otros;
   - calcula el VBP.
   - si el crudo es de ornamentales (tiene la hoja `POR ESPECIES`), toma de la tabla por especie las unidades por
     destino: exportación → «Mercado externo», nacional → «Mercado interno» y stock remanente y/o mortandad, en miles
     de unidades (la suma es el ingreso). Se detiene en la fila TOTAL, así que no lee la tabla de principales especies
     que viene debajo.
3. **Bloque 3 · Generar.** Monta Drive, procesa todos los crudos de la carpeta (consumo y ornamentales juntos) y
   reemplaza en el histórico los meses que traen, cada tipo por separado (el resto se conserva, y recargar no duplica). Guarda dos hojas: `LOR_PESCA` y `CUADRO`, con las filas del
   cuadro «Loreto: producción pesquera» y un mes por columna: Valor Bruto Pesquero, toneladas en estado fresco, seco
   salado y salpreso (con su precio de 2007), Boquichico y Llambina/Palometa.

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

Por especie: Boquichico 34,146 t y Llambina/Palometa 19,948 t (15,534 + 4,414).

Ornamentales de setiembre de 2025: 396,249 miles de unidades (322,727 al mercado externo y 73,522 al interno, sin
stock), con un VBP de 409,286 miles de S/ de 2007.

## Cuidados

- Si DIREPRO cambia el nombre de las hojas o el rótulo PERIODO, el notebook se detiene con un mensaje que dice qué no
  encontró.
- Una especie nueva entra sola como «Otros» (o como «Zúngaro»). Si el crudo la escribe distinto que el Cuadro Nº 07, se
  agrega a `CORRECCIONES`.
- En el API, los tres LONG entrarán como archivo mensual de pesca (hoja de ruta en `FISCAL/api/README.md`).
