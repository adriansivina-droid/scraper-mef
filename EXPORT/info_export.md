# info_export — Exportaciones: ESTAD, SERIES y Cuadro de la síntesis

BCRP Sucursal Iquitos · Loreto, San Martín y Ucayali · Actualizado: 28-10-2026

Este archivo reúne todo lo relativo a las exportaciones: fuentes, archivos, hojas, celdas, fórmulas, reglas de cálculo, errores encontrados y cómo se corrigieron.

---

## 1. Flujo de datos

```
SUNAT / BCRP Oficina Principal
            │
            ▼
ESTAD (fuente única)  H:\eecono\WEBS\ESTAD PARA WEB\
  ESTADLO.xlsx  → hojas 15.Export y 16.Import
  ESTADSMN.xlsx → hoja 14.XLS
  ESTADUCA.xlsx → hoja 15.XLS
            │
            ├──► SERIES [DEPARTAMENTO].xlsx
            │       hoja ENLACE ESTAD → hojas XS (gráficos) y XS CUADROS (cuadros)
            │
            └──► Cuadro_LOR.xlsx (cuadro de la síntesis de Loreto)
                    hoja X_Base → hoja Exportaciones → Síntesis / PPT
```

**Regla de oro:** el ESTAD es la única fuente. Ningún cuadro debe tener cifras pegadas o digitadas.

---

## 2. Archivos

| Archivo | Rol | Hoja de exportaciones | Observación |
|---|---|---|---|
| ESTADLO.xlsx | Fuente Loreto | `15.Export` (export.), `16.Import` (import.) | Miles de USD |
| ESTADSMN.xlsx | Fuente San Martín | `14.XLS` | Miles de USD |
| ESTADUCA.xlsx | Fuente Ucayali | `15.XLS` | Miles de USD |
| SERIES LORETO (OFICIAL).xlsx | Gráficos y cuadros Loreto | `XS LOR AGOS-2026`, `XS LOR AGO-2026`, `XS CUADROS`, `ENLACE ESTAD` | Vinculado a ESTADLO |
| SERIES SMN 04-2026.xlsx | Gráficos y cuadros San Martín | `XS SMN ABR-2026`, `XS SMN ABR2-2026`, `XS SMN EMPRESAS`, `XS CUADROS (2)`, `ENLACE ESTAD` | Vinculado a ESTADSMN |
| SERIES UCAYALI.xlsx | Gráficos Ucayali | `XS UCA`, `ENLACE ESTAD` | Vinculado a ESTADUCA |
| Cuadro_LOR.xlsx | Cuadro de la síntesis de Loreto | `Exportaciones` (lee de `X_Base`) | X_Base ahora vinculado a ESTADLO |

Versiones corregidas entregadas (con nombre "- ENLACE ESTAD" en las SERIES). Reemplazan a las anteriores.

---

## 3. Estructura de las hojas ESTAD de exportaciones

Igual en los tres departamentos:

| Elemento | Ubicación |
|---|---|
| Fila 4 | Año en el primer mes de cada bloque; "Total" en la columna anual; textos como "Var.% 2026/2025" en columnas resumen |
| Fila 5 | Fecha del mes (1er día) en columnas mensuales; año (número) en columnas "Total"; textos "Ene.-Jul." en resumen |
| Columna A | Etiqueta del producto/grupo |
| Datos | Desde columna B (enero 2009) en bloques de 12 meses + 1 columna Total por año |
| Columnas resumen | Al final (Loreto: IC = Var.%, IE/IF = acumulados Ene-mes, IH-IJ diferencias) |

**Trampa:** la columna de "Var.%" (Loreto IC) tiene en la fila 5 una **fecha** (ej. 2026-07-01). Una fórmula que solo filtre por fecha la sumaría como si fuera un mes. Por eso las fórmulas excluyen columnas cuyo encabezado de fila 4 tiene 5 o más caracteres: `--(LEN(fila4)<5)`.

**Trampa 2:** las columnas resumen "Ene.-Mes" se actualizan con retraso (en octubre la de Loreto decía Ene.-Jul.). Nunca tomar totales de esas columnas; calcular por fechas.

### 3.1 Filas de ESTADLO – 15.Export

| Fila | Etiqueta |
|---|---|
| 7 | TOTAL EXPORTACIONES |
| 9 | PRODUCTOS TRADICIONALES |
| 10 | Petróleo crudo y derivados |
| 11 | PRODUCTOS NO TRADICIONALES |
| 12 | Forestales |
| 13–16 | Madera aserrada, Madera laminada, Triplay, Otros acabados |
| 17 | Pesqueros |
| 18–19 | Pescado congelado (paiche), Peces ornamentales |
| 20 | Agropecuarios |
| 21–22 | Cacao en grano, Conservas de palmito |
| 23 | Animales vivos |
| 24 | Resto2/ |
| 25 | OTRAS EXPORTACIONES3/ |

En X_Base (Cuadro_LOR) las filas son las mismas pero con otras etiquetas: fila 12 "Maderas y sus manufacturas", fila 24 "Resto", fila 25 "OTRAS EXPORTACIONES2/".

### 3.2 Filas de ESTADLO – 16.Import

7 TOTAL IMPORTACIONES · 9 BIENES DE CONSUMO (10 no duraderos 100, 11 duraderos 200, 12 diversos 010) · 13 MATERIAS PRIMAS E INSUMOS (14 combustibles 300, 15 agricultura 400, 16 industria 500) · 17 BIENES DE CAPITAL (18 construcción 600, 19 agricultura 700, 20 industria 800, 21 transporte 900).

### 3.3 Filas de ESTADSMN – 14.XLS

7 TOTAL · 9 TRADICIONALES · 10 Pesqueros (2) · 11 Agrícolas (café) · 12 NO TRADICIONALES · 13 Maderas y sus manufacturas (14–17 madera aserrada, tablillas, machihembrado, otros acabados) · 18 Pesqueros (19 paiche salado) · 20 Agropecuarios (21 aceite crudo de palma, 22 aceite crudo de palmiste, 23 aceite refinado de palma, 24 aceite refinado de palmiste, 25 aceite vegetal, 26 cacao derivados, 27 cacao en grano, 28 chocolates, 29 conservas de palmito, 30 estearina de palma, 31 manteca vegetal de palma, 32 manteca vegetal de palmiste, 33 puros y cigarros, 34 tabaco negro y rubio) · 35 Resto2/ · 36 OTRAS EXPORTACIONES3/.

### 3.4 Filas de ESTADUCA – 15.XLS

7 TOTAL · 9 NO TRADICIONALES · 10 Maderas y sus manufacturas (11 decking, 12 machihembrado, 13 madera aserrada, 14 laminada, 15 moldurada, 16 tableros, 17 tablillas y frisos, 18 triplay, 19 otros acabados) · 20 Pesqueros (21 pescado congelado, 22 peces ornamentales, 23 pescado seco salado) · 24 Agropecuarios (25 aceite crudo de palma, 26 aceite crudo de palmiste, 27 aceite refinado de palma, 28 cacao en grano, 29 café en grano, 30 chocolates, 31 estearina de palma, 32 manteca vegetal) · 33 Resto2/ · 34 OTRAS EXPORTACIONES3/.

Ucayali no tiene productos tradicionales en el ESTAD.

---

## 4. Fórmula base (lectura del ESTAD)

Suma de un producto entre dos meses, con el libro ESTAD cerrado:

```
=SUMAPRODUCTO(--(LARGO('[ESTADLO.xlsx]15.Export'!$B$4:$ZZ$4)<5);
              --('[ESTADLO.xlsx]15.Export'!$B$5:$ZZ$5>=FECHA(año;mes_ini;1));
              --('[ESTADLO.xlsx]15.Export'!$B$5:$ZZ$5<=FECHA(año;mes_fin;1));
              INDICE('[ESTADLO.xlsx]15.Export'!$B$1:$ZZ$60;
                     COINCIDIR("Etiqueta";'[ESTADLO.xlsx]15.Export'!$A$1:$A$60;0);0))
```

- Se usa SUMAPRODUCTO + INDICE/COINCIDIR porque funcionan con el ESTAD **cerrado** (SUMAR.SI.CONJUNTO y BUSCARX no).
- Busca por **fecha** y por **etiqueta**: si el ESTAD agrega meses o años, se toman solos.
- Si cambia el texto de una etiqueta en el ESTAD, la fórmula devuelve error: revisar etiquetas.

---

## 5. Hoja ENLACE ESTAD (en cada SERIES)

Hoja nueva, pestaña azul marino. No se escribe en ella.

| Celda | Contenido |
|---|---|
| C4 | Año (toma el control de la hoja XS) |
| C5 | Último mes con datos en el ESTAD |
| C6 | Mes usado (toma el control de la hoja XS) |
| C7 | Nombre del mes |
| C8 | Control: "OK" o "OJO: ESTAD solo tiene datos hasta el mes N" |
| B12:G23 | Variación % anual de exportaciones (12 años): etiqueta, año, meses, valor, valor año anterior, var. % |
| B26:C34 | No tradicionales año anterior completo: título, total, top 6 + Otros |
| B37:C45 | No tradicionales enero-mes año actual: título, total, top 6 + Otros |
| B48:C54 | Top 5 productos (total exportado) enero-mes |
| B99:C105 | Top 5 productos (total exportado) solo el mes |
| B61 en adelante | Ayudante: cada producto con su valor ene-mes, año anterior, mes y claves de orden |

El ranking usa `K.ESIMO.MAYOR` sobre una clave (valor − FILA()/10^7) para desempatar.

### Controles de año y mes

| SERIES | Hoja | Año | Mes |
|---|---|---|---|
| Loreto | XS LOR AGOS-2026 | C30 | C31 |
| Loreto | XS CUADROS | B1 | B2 |
| San Martín | XS SMN ABR-2026 | C30 | C31 |
| San Martín | XS CUADROS (2) | B1 | B2 |
| Ucayali | XS UCA | B29 (agregada) | B30 |
| Cuadro_LOR | Exportaciones | B1 | B2 |

---

## 6. Qué quedó conectado en cada SERIES

| SERIES | Hoja | Rango | Contenido |
|---|---|---|---|
| Loreto | XS LOR AGOS-2026 | B8:C19 | Variación % exportaciones (gráfico de barras Loreto vs Perú) |
| Loreto | XS LOR AGOS-2026 | B102:D113 | Circular no tradicionales, año anterior completo |
| Loreto | XS LOR AGOS-2026 | K102:M113 | Circular no tradicionales, enero-mes año actual |
| Loreto | XS CUADROS | D9:S24 | Exportaciones por grupo (mes, enero-mes, enero) |
| Loreto | XS CUADROS | U34:AG53 | Importaciones por grupo |
| San Martín | XS SMN ABR-2026 | B8:C19 | Variación % |
| San Martín | XS SMN ABR-2026 | B68, B71:C76 | Top 5 productos enero-mes |
| San Martín | XS SMN ABR-2026 | T68, T71:U76 | Top 5 productos del mes |
| San Martín | XS CUADROS (2) | D9:S22 | Exportaciones por grupo |
| Ucayali | XS UCA | A7:B17 | Variación % (11 años) |
| Ucayali | XS UCA | A32, A35:B40 | Top 5 productos enero-mes (en USD = ESTAD × 1000) |
| Ucayali | XS UCA | S67, S70:T75 | Top 5 productos del mes |

**Siguen manuales** (no están en el ESTAD): mercados de destino, aduanas, empresas exportadoras y la serie de Perú. Algunos de sus títulos usan `FECHA(2025;…)` con el año fijo: cambiar `2025` por la celda de año.

### Particularidades

- **Loreto:** el gráfico de variación recorta barras >250 % a 230 (columna "LORETO GRÁFICO", `=SI(C>250;230;C)`) y muestra el valor real con "Valor de las celdas" + un arco blanco sobre la barra.
- **San Martín:** la tabla derecha de XS CUADROS (2) copia la izquierda fila por fila.
- **Ucayali:** la variación compara **enero-mes en todos los años** (no año completo), igual que la serie original. Valores en USD, no miles.

---

## 7. Regla de cálculo de los cuadros (vigente)

Aplica a **Cuadro_LOR (síntesis)** y **SERIES Loreto – XS CUADROS**. Ambos dan cifras idénticas.

| Elemento | Regla |
|---|---|
| Unidad | Millones de USD (ESTAD / 1000) |
| Productos y subtotales | `REDONDEAR(valor;2)` — **2 decimales** desde oct-2026 |
| Total | Suma de tradicionales + no tradicionales + otras exportaciones (ya redondeados) |
| Variación % | `SI.ERROR(REDONDEAR((actual/anterior-1)*100;1);"-")`, 1 decimal |
| Estructura % | Mes del año anterior / total del mismo mes × 100 |
| Contribución | (actual − anterior) / total anterior × 100 |
| Orden de filas | Tradicionales, Petróleo, No tradicionales, Agropecuarios, Animales vivos, Maderas, Pesqueros, Resto, Otras, Total |

San Martín y Ucayali siguen a 1 decimal (pendiente decidir si se pasan a 2).

**Ojo:** con redondeo previo, las variaciones de rubros pequeños se distorsionan. Para redactar textos ("creció X %"), calcular con los miles de USD del ESTAD.

---

## 8. Cuadro_LOR.xlsx (síntesis de Loreto)

- Hoja **Exportaciones**: lee de **X_Base** con `REDONDEAR(SUMAPRODUCTO((X_Base!$B$5:$IN$5=fecha)*(X_Base!$A$7:$A$25=etiqueta)*(X_Base!$B$7:$IN$25))/1000;2)`.
- **X_Base** (corregida): fila 6 = columna del ESTAD con la misma fecha (`SI.ERROR(COINCIDIR(B$5;'[1]15.Export'!$A$5:$ZZ$5;0);0)`); filas 7–25 = `SI(B$6=0;0;N(INDICE('[1]15.Export'!$A$1:$ZZ$60;fila;B$6)))`.
- X_Base tiene columnas hasta 2027 (IB:IM meses 2027, IN total 2027); el ESTAD hoy llega a 2026, así que esas devuelven 0.
- Filas 29–30 de X_Base: control de totales (valores pegados). No usadas por el cuadro.
- Las importaciones (filas 42–64) están "En proyecto (No finalizado)" y son manuales.

---

## 9. Errores encontrados y corrección

| # | Documento | Hoja / celda | Error | Efecto | Estado |
|---|---|---|---|---|---|
| 1 | Cuadro_LOR | X_Base | Datos pegados, sin vínculo al ESTADLO | No se actualizaba | Corregido: vinculado |
| 2 | Cuadro_LOR | X_Base HQ23 | Animales vivos mar-2026 vacío (ESTAD: 58 mil USD) | 0,4 en vez de 0,5; NT 4,6; total 189,6; var. −1,5 | Corregido |
| 3 | Cuadro_LOR | X_Base HV7 | Total ago-2026 sumaba Resto en vez de Otras | 17 541 vs 17 479 (no llegó al cuadro) | Corregido |
| 4 | Cuadro_LOR | Exportaciones M30 | +0,1 sumado a mano | Ajuste forzado | Corregido |
| 5 | Cuadro_LOR | Exportaciones H, M | #VALUE! en contribuciones; faltaba Animales vivos | Incompleto | Corregido |
| 6 | Cuadro_LOR | Exportaciones B3 | FECHA = 18 | Sin efecto | Corregido: `FECHA(B1;B2;1)` |
| 7 | SERIES Loreto | XS CUADROS | Cifras digitadas; solo el encabezado cambiaba con el mes | Decía ene-jul con datos ene-jun; importaciones 71,6 era total anual 2025 | Corregido: fórmulas |
| 8 | SERIES Loreto | XS LOR AGOS-2026 L106 | NT tomado de la columna Ene.-Jul. con título ene-ago | 4 251 vs 4 697 | Corregido |
| 9 | SERIES Loreto | XS LOR AGOS-2026 D107 | Peces ornamentales 84,5 % fijo (de otra tabla) | % errado | Corregido |
| 10 | Ambos | Regla | Síntesis redondeaba antes; SERIES calculaba exacto | Diferencias de 0,1 | Unificado: 2 decimales |
| 11 | PPT síntesis | Lámina 24 | "Enero-agosto … contracción de 28,5 %" | 28,5 % es agosto; ene-ago es −1,4 % | Pendiente de corregir en la lámina |
| 12 | SERIES SMN | XS CUADROS (2) | Cifras manuales (ej. Resto 40,0) | Errores puntuales | Corregido |
| 13 | SERIES UCA | XS UCA B30 | MES = 10 con ESTAD hasta agosto | Periodo inexistente | Corregido: 8 |

---

## 10. Cifras de referencia (ESTAD, octubre 2026)

### Loreto – agosto 2026 (millones USD, 2 decimales)

| Tipo | Est. % ago-25 | Ago-25 | Ago-26 | Var. % | Ene-ago 25 | Ene-ago 26 | Var. % |
|---|---|---|---|---|---|---|---|
| Tradicionales (petróleo) | 99,1 | 24,22 | 17,03 | −29,7 | 189,16 | 184,89 | −2,3 |
| No tradicionales | 0,9 | 0,23 | 0,45 | 95,7 | 2,89 | 4,70 | 62,6 |
| Agropecuarios | 0,0 | 0,00 | 0,29 | – | 0,00 | 2,60 | – |
| Animales vivos | 0,4 | 0,09 | 0,00 | −100,0 | 1,26 | 0,50 | −60,3 |
| Maderas | 0,2 | 0,05 | 0,00 | −100,0 | 0,59 | 0,49 | −16,9 |
| Pesqueros | 0,3 | 0,07 | 0,09 | 28,6 | 0,85 | 0,79 | −7,1 |
| Resto | 0,1 | 0,02 | 0,06 | 200,0 | 0,19 | 0,32 | 68,4 |
| Otras | 0,0 | 0,00 | 0,00 | – | 0,25 | 0,08 | −68,0 |
| **Total** | **100,0** | **24,45** | **17,48** | **−28,5** | **192,30** | **189,67** | **−1,4** |

Animales vivos 2026 por mes (miles USD): 134 · 110 · 58 · 69 · 38 · 65 · 24 · 0 = 498.

### Variación % anual de exportaciones Loreto (año completo; 2026 = ene-ago)

2015 −63,6 · 2016 −53,9 · 2017 48,6 · 2018 173,9 · 2019 69,3 · 2020 −70,6 · 2021 39,0 · 2022 409,7 · 2023 −10,0 · 2024 40,3 · 2025 −20,7 · 2026* −1,4

### Valor FOB anual (millones USD)

| Región / producto | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Ene-ago 25 | Ene-ago 26 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Loreto total | 27,0 | 73,9 | 125,0 | 36,7 | 51,1 | 260,4 | 234,5 | 329,1 | 261,1 | 192,3 | 189,7 |
| Loreto no tradicionales | 14,4 | 9,6 | 9,4 | 5,7 | 6,4 | 7,1 | 6,2 | 6,0 | 5,0 | 2,9 | 4,7 |
| San Martín total | 172,0 | 117,6 | 139,9 | 170,8 | 177,5 | 187,4 | 207,6 | 293,4 | 532,3 | 356,9 | 208,0 |
| San Martín cacao en grano | 52,1 | 18,5 | 20,5 | 22,7 | 33,8 | 54,5 | 92,6 | 166,0 | 395,3 | 278,2 | 144,7 |
| San Martín café | 62,0 | 15,0 | 25,3 | 29,1 | 36,8 | 43,8 | 22,3 | 25,2 | 46,2 | 19,8 | 11,4 |
| Ucayali total | 29,8 | 20,4 | 23,0 | 46,7 | 102,5 | 146,0 | 90,9 | 136,4 | 100,7 | 80,2 | 35,4 |
| Ucayali maderas | 24,6 | 16,1 | 17,7 | 18,3 | 29,3 | 36,4 | 29,6 | 28,9 | 23,2 | 14,9 | 14,5 |
| Ucayali cacao en grano | 3,2 | 3,4 | 4,7 | 5,2 | 8,1 | 12,7 | 9,2 | 89,0 | 52,3 | 43,3 | 7,8 |
| Ucayali aceite crudo de palma | 0,0 | 0,1 | 0,1 | 22,3 | 60,5 | 93,0 | 51,1 | 14,0 | 14,8 | 14,8 | 11,5 |

Último mes con datos: Loreto agosto 2026 · San Martín agosto 2026 (la SERIES usa abril) · Ucayali agosto 2026.

### Mensajes clave

- **Loreto:** el petróleo es ~97 % del total; la caída de agosto (−28,5 %) es petróleo. Las no tradicionales crecen por el cacao (0,0 → 2,6 en ene-ago).
- **San Martín:** la caída ene-ago (−42 %) es casi toda cacao (278,2 → 144,7). 2025 fue atípico (532 millones).
- **Ucayali:** caída ene-ago −56 % por cacao (43,3 → 7,8); la madera se mantiene estable.

---

## 11. Formato de gráficos y cuadros

### Paleta BCRP

| Color | Hex | Uso |
|---|---|---|
| Azul marino | `#111149` | Serie principal, línea Perú, títulos |
| Turquesa | `#72D2D5` | Barras de la región, segunda serie |
| Gris azulado | `#CCD3DF` | "Otros", líneas guía, ejes |
| Naranja | `#DD6140` | Tercera categoría |
| Amarillo | `#FFC41D` | Cuarta categoría |
| Negro | `#181818` | Texto, etiquetas externas |
| Blanco | `#FEFEFE` | Fondo, bordes de tajadas |

### Fuente

**Barlow** en todo (celdas, tema, 177 gráficos, cuadros de texto) en las tres SERIES. Debe estar instalada en cada PC (fonts.google.com/specimen/Barlow).

### Gráfico de variación (barras + línea)

Columna agrupada (región) + línea con marcadores (Perú) en el mismo eje · marcadores círculo 25–30, relleno blanco, borde azul marino · etiquetas de Perú al centro del círculo · etiquetas de región en extremo externo con "Valor de las celdas" · sin eje vertical ni cuadrícula.

### Gráfico circular (no tradicionales)

Etiquetas: nombre de categoría + porcentaje, separador nueva línea, 1 decimal, líneas guía · sin leyenda · bordes blancos 1,5 pt · "Otros" en gris · tajadas grandes con etiqueta dentro, pequeñas fuera.

**Al cambiar datos sin perder formato:** editar el rango en la barra de fórmulas `=SERIES(...)` en lugar de "Seleccionar datos". Guardar como plantilla ("Circular BCRP").

### Gráfico recomendado pendiente

Barras apiladas de valor FOB por producto principal (2017–2026, mismo periodo ene-mes), con los 2–3 productos principales + Resto. Muestra qué producto explica la caída o el alza.

### Títulos de láminas (síntesis)

El título dice la conclusión y debe usar el **mismo periodo y la misma cifra** que el cuadro. Ejemplo correcto:
"En agosto de 2026, las exportaciones se contrajeron 28,5 % interanual, por las menores ventas de petróleo crudo."

---

## 12. Rutina mensual

1. Actualizar el ESTAD en `H:\eecono\WEBS\ESTAD PARA WEB\`.
2. Abrir la SERIES y Cuadro_LOR → **Actualizar vínculos**.
3. Cambiar AÑO y MES en las celdas de control (sección 5).
4. Revisar `ENLACE ESTAD!C8` = "OK".
5. Comparar el total del cuadro con el total del ESTAD para el mismo periodo.
6. Reacomodar etiquetas pequeñas de los circulares si cambió el orden de productos.
7. Actualizar a mano mercados, aduanas y empresas.
8. Verificar que los títulos de las láminas coincidan con el cuadro.

**Nunca:** pegar valores en X_Base, ENLACE ESTAD o los cuadros XS; tomar totales de las columnas resumen "Ene.-Mes" del ESTAD.

---

## 13. Pendientes

- [ ] Confirmar con SUNAT / responsable del ESTADLO que Animales vivos de marzo 2026 = 58 mil USD.
- [ ] Corregir el título de la lámina 24 de la síntesis (enero-agosto vs agosto).
- [ ] Decidir si San Martín y Ucayali pasan a 2 decimales.
- [ ] Revisar títulos con `FECHA(2025;…)` fijo en tablas de mercados, aduanas y empresas.
- [ ] Opcional: columna auxiliar con variación exacta junto a cada cuadro.
- [ ] Opcional: gráfico de barras apiladas por producto en las tres SERIES.
- [ ] Opcional: precio vs volumen del cacao (requiere toneladas de SUNAT; el ESTAD solo trae valor FOB).
- [ ] Documento para jefatura: "Diferencias en exportaciones de Loreto: causas y corrección" (compartir desde el menú Compartir).
