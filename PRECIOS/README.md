# Precios al consumidor por ciudad · INEI (SIRTOD)

Datos de precios para la tesis «Nivel de los ríos navegables y precios de los alimentos en la ciudad de Iquitos 2012-2025». Descargados el 20/11/2026.

## Archivos en `data/`

| Archivo | Contenido |
|---|---|
| `sirtod_ipc_precios_departamentos.csv` | Todo lo descargado del SIRTOD, en formato largo: `SERIE, UBIGEO, DEPARTAMENTO, INDICADOR, AÑO, MES, VALOR`. 24 departamentos, frecuencia mensual. |
| `ipc_alimentos_empalmado_dic2021_100.csv` | Índice de alimentos por departamento, dic-2021 = 100, de 2009 a oct-2026. |
| `ipc_general_empalmado_dic2021_100.csv` | Índice general por departamento, empalmado del mismo modo. |
| `precios_promedio_productos_loreto_lima_ucayali_sanmartin.csv` | Precio promedio mensual (soles) por producto, con los nombres armonizados entre las dos bases. |
| `INEI_IPC_CCIF_base_dic2021_ciudades_2021-2026.xlsx` | Archivo enviado por el INEI: IPC por división, grupo y clase (CCIF) de Iquitos, Lima, Pucallpa y Tarapoto, dic-2021 a oct-2026. |

Valores de `SERIE`:

| SERIE | Periodo | Contenido |
|---|---|---|
| `b2009_indices` | 2009-2021 | Índice general, alimentos y bebidas (dentro y fuera del hogar) y 14 subgrupos de alimentos, base 2009 = 100 |
| `b2021_indices` | 2022-2026 | Índice general, alimentos y bebidas no alcohólicas y sus 13 clases, base dic-2021 = 100 |
| `b2009_precios` | 2009-2021 | Precio promedio de 41 productos |
| `b2021_precios` | 2022-2026 | Precio promedio de 43 productos |

## Empalme del índice de alimentos

- Hasta dic-2021: base 2009, «Alimentos y bebidas dentro del hogar», reescalado para que dic-2021 = 100. Se excluyen las comidas fuera del hogar, que en la base 2021 pasan a otra división.
- Desde ene-2022: base dic-2021, «Alimentos y bebidas no alcohólicas».

## Control de calidad

- El índice general del SIRTOD coincide con el compilado de los 178 informes técnicos mensuales para Loreto, Lima y Ucayali: la diferencia máxima en la variación mensual es de 0,011 puntos porcentuales.
- Los valores de 2022 en adelante son idénticos a los del archivo enviado por el INEI.
- En el SIRTOD, el departamento San Martín corresponde a **Moyobamba**, no a Tarapoto. Para Tarapoto solo se tiene el archivo del INEI, desde 2022.
- Hay 21 productos con serie continua de 2009 (o 2010) a 2026 en Loreto. Los demás solo existen en una de las dos bases.

## Cómo obtener los mismos datos en la página del SIRTOD

1. Entrar a https://sirtod.inei.gob.pe/app/consulta.
2. En «Seleccione el lugar», elegir **Departamentos** y marcar Loreto, Lima, Ucayali y San Martín.
3. En el árbol: Económico › Índice de Precios al Consumidor › Base 2009 (o Base Diciembre 2021) › Índices de Precios al Consumidor, y marcar el **indicador final**, no la carpeta.
4. Cambiar la frecuencia de **Anual a Mensual** en el selector superior. Los datos se descargaron con frecuencia mensual; con «Anual» la página muestra «No se dispone de información a este nivel».
5. Pulsar **Ejecutar** y descargar con el ícono de Excel.
