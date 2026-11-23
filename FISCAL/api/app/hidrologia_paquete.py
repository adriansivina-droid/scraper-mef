"""Paquete para compartir de «Ríos del Perú» (SENAMHI): un zip con los datos en Excel con nombres claros, un LEEME.txt que explica
qué trae cada archivo y un DICCIONARIO_DE_VARIABLES.txt con el significado de cada columna.

Se arma a partir de los CSV que ya arma hidrologia.armar(): cada CSV pasa a Excel (fechas y números como tales, encabezado fijo y
filtros), escrito por filas sin cargar todo en memoria (la serie diaria llega a cientos de miles de filas). Cada Excel trae además una
hoja «Descripción» con lo mismo que el diccionario, para que se entienda aunque se mande solo.
"""
import csv
import os
import zipfile
from datetime import date, datetime

import xlsxwriter

MAX_FILAS_EXCEL = 1_048_575                      # una hoja de Excel admite 1 048 576 filas, una es el encabezado

# columnas por tipo: lo demás va como texto (los códigos de estación, por ejemplo, deben leerse como texto)
DECIMALES = {"VALOR", "MINIMO", "MAXIMO", "PROM_HISTORICO", "UMBRAL_ROJO", "UMBRAL_NARANJA", "UMBRAL_AMARILLO", "ANOMALIA", "VALOR_MES",
             "VALOR_MES_ANTERIOR", "LATITUD", "LONGITUD", "CRUCE_MENSUAL_DIF_MAX_%"}
ENTEROS = {"AÑO", "MES", "DIA", "AÑO_HIDROLOGICO", "DIAS_CON_DATO", "DIAS_FALTANTES", "SALTOS_RAROS", "DATOS_DUDOSOS", "ESTACIONES", "CON_DATO",
           "FILAS", "ID_ESTACION"}
FECHAS = {"FECHA", "FECHA_EXTRACCION", "PRIMERA_FECHA", "ULTIMA_FECHA", "INICIO_SERIE"}

# ── diccionario ──────────────────────────────────────────────────────────────
# (variable, tipo, descripción, ejemplo)
_ESTACION = ("COD_ESTACION", "texto", "Código de la estación en SENAMHI. Es la llave para unir los archivos entre sí. Puede tener letras: léelo como texto.", "240001 · 47E0D438")
_FILA_DIARIO = [
    _ESTACION,
    ("ESTACION", "texto", "Nombre de la estación hidrométrica.", "TAMSHIYACU"),
    ("RIO", "texto", "Río o cuerpo de agua, como lo rotula el hidrograma de SENAMHI.", "RÍO AMAZONAS"),
    ("VARIABLE", "texto", "Qué se mide: NIVEL o CAUDAL.", "NIVEL"),
    ("UNIDAD", "texto", "Unidad del valor: m.s.n.m (metros sobre el nivel del mar) o m para el nivel; m3/s (metros cúbicos por segundo) para el caudal.", "m.s.n.m"),
    ("FECHA", "fecha", "Día del dato.", "10/11/2026"),
    ("AÑO", "entero", "Año de la fecha (para filtrar y agrupar).", "2026"),
    ("MES", "entero", "Mes de la fecha, de 1 a 12.", "11"),
    ("DIA", "entero", "Día del mes.", "10"),
    ("AÑO_HIDROLOGICO", "entero", "Año hidrológico al que pertenece el día. Va de setiembre a agosto y se nombra por el año en que empieza: 2026 = del 01/09/2026 al 31/08/2027.", "2026"),
    ("VALOR", "decimal", "Valor del día que dibuja el hidrograma de SENAMHI. En lo revisado es el promedio del mínimo y el máximo del día. Está en la UNIDAD de la fila. Vacío = sin dato.", "112.56"),
    ("MINIMO", "decimal", "Valor mínimo del día. Solo viene en las filas de SERIE = ACTUAL.", "112.50"),
    ("MAXIMO", "decimal", "Valor máximo del día. Solo viene en las filas de SERIE = ACTUAL.", "112.62"),
    ("PROM_HISTORICO", "decimal", "«Promedio histórico» que publica SENAMHI para ese día del año: una curva fija, igual todos los años. SENAMHI no dice de qué años la calcula. Solo en SERIE = ACTUAL.", "111.90"),
    ("UMBRAL_ROJO", "decimal", "Umbral de alerta roja de la estación, en la unidad del valor. Solo en SERIE = ACTUAL.", "110.05"),
    ("UMBRAL_NARANJA", "decimal", "Umbral de alerta naranja. Solo en SERIE = ACTUAL.", "110.94"),
    ("UMBRAL_AMARILLO", "decimal", "Umbral de alerta amarilla. Solo en SERIE = ACTUAL.", "111.68"),
    ("SERIE", "texto", "De qué serie del hidrograma salió la fila. ACTUAL: del año hidrológico pedido (trae mínimo, máximo, promedio histórico y umbrales). ANTERIOR: leído como «año anterior» desde el hidrograma del año siguiente (solo trae VALOR). Si un día está en las dos, se guarda ACTUAL.", "ACTUAL"),
    ("FECHA_EXTRACCION", "fecha", "Día en que se descargó el dato de SENAMHI.", "10/11/2026"),
    ("DATO_DUDOSO", "texto", "«SI» si el nivel de ese día es un pico aislado de 1 o 2 días que sube y vuelve al valor de antes, algo imposible en un río (por ejemplo, 12 m en un día). El valor NO se borra: queda en el archivo y se marca para que se revise. Solo se revisa el NIVEL (en caudal, las crecidas repentinas de los ríos de montaña son reales). Vacío = sin sospecha.", "SI"),
]

# (clave de hidrologia.ARCHIVOS, carpeta, archivo, título, qué es, una fila es…, columnas)
PAQUETE = [
    ("estaciones", "1_DATOS", "1_Estaciones_hidrometricas.xlsx", "Estaciones hidrométricas",
     "El catálogo de estaciones del mapa de Monitoreo Hidrológico de SENAMHI, con su dirección zonal, departamento, río, variables con datos y coordenadas. "
     "Es el archivo para ubicar cada COD_ESTACION.", "Una fila por estación.",
     [("ID_ESTACION", "entero", "Identificador interno de SENAMHI (no es el código).", "151"),
      _ESTACION,
      ("ESTACION", "texto", "Nombre de la estación.", "BELLAVISTA"),
      ("SUB_ESTACION", "texto", "Subestación, si SENAMHI la indica. Suele venir vacía.", ""),
      ("ESTADO", "entero", "Estado en SENAMHI: 1 = activa.", "1"),
      ("COD_ZONAL", "texto", "Dirección zonal de SENAMHI que tiene la estación (filtro «Dirección Zonal» del mapa), de 01 a 13. Vacío si no se pudo leer.", "08"),
      ("DIRECCION_ZONAL", "texto", "Nombre de la dirección zonal, por su sede. La 08 es la de Loreto, la 09 la de San Martín y la 10 la de Huánuco-Ucayali.", "DZ 8 · Loreto"),
      ("DEPARTAMENTO", "texto", "Departamento de la estación. SENAMHI lo da solo para las estaciones principales (las de la Información Diaria o Mensual); en las demás queda vacío: usa DIRECCION_ZONAL.", "LORETO"),
      ("FECHA_HORA_ULTIMA", "texto", "Fecha y hora del último dato de la estación, según su ficha en el mapa de SENAMHI (aaaa-mm-dd hh:mm:ss).", "2026-11-09 11:00:00"),
      ("VARIABLE_OPCION", "texto", "Código con que SENAMHI indica qué variables ofrece el hidrograma de la estación (N = solo nivel).", "N"),
      ("RIO", "texto", "Río, tomado del hidrograma.", "RÍO NAPO"),
      ("VARIABLES_CON_DATOS", "texto", "Variables de la estación que tienen datos en el archivo «Nivel y caudal diario».", "CAUDAL / NIVEL"),
      ("LATITUD", "decimal", "Latitud en grados decimales (WGS84; negativa = sur). Vacía si no se conoce la ubicación.", "-3.48"),
      ("LONGITUD", "decimal", "Longitud en grados decimales (WGS84; negativa = oeste).", "-73.07"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó de SENAMHI.", "10/11/2026")]),

    ("diario", "1_DATOS", "2_Nivel_y_caudal_diario.xlsx", "Nivel y caudal diario (hidrograma de SENAMHI)",
     "La serie principal: el hidrograma diario de todas las estaciones del mapa de SENAMHI, con el nivel (m) y, donde la estación lo publica, el caudal (m3/s). "
     "Trae el mínimo y máximo del día, el promedio histórico y los umbrales de alerta. Es el archivo para análisis y gráficos.",
     "Una fila por estación, variable y día. Si pasa de 1 048 575 filas se continúa en otra hoja del mismo archivo.", _FILA_DIARIO),

    ("info-diaria", "1_DATOS", "3_Informacion_diaria_4_horas.xlsx", "Información Diaria (4 lecturas por día)",
     "La pestaña «Información Diaria» de SENAMHI: el dato de las estaciones principales (unas 70, casi todas en caudal) a las 00:00, 06:00, 12:00 y 18:00, "
     "con su anomalía respecto a la normal y su tendencia. Solo se guardan las filas con dato.", "Una fila por estación, día y hora.",
     [_ESTACION,
      ("ESTACION", "texto", "Nombre de la estación.", "TAMSHIYACU"),
      ("CUERPO_AGUA", "texto", "Río, lago o canal donde está la estación.", "RÍO AMAZONAS"),
      ("CUENCA", "texto", "Cuenca o intercuenca, según SENAMHI.", "Intercuenca 49797"),
      ("DEPARTAMENTO", "texto", "Departamento de la estación.", "LORETO"),
      ("ZONA", "texto", "Sector del país: NORTE, CENTRO o SUR.", "NORTE"),
      ("REGION_HIDROGRAFICA", "texto", "Región hidrográfica: del Pacífico, del Amazonas o del Titicaca.", "Región Hidrográfica del Amazonas"),
      ("COD_ZONAL", "texto", "Código de la dirección zonal de SENAMHI a cargo de la estación (01 a 13).", "08"),
      ("FECHA", "fecha", "Día del dato.", "01/01/2023"),
      ("AÑO", "entero", "Año de la fecha.", "2023"), ("MES", "entero", "Mes de la fecha.", "1"), ("DIA", "entero", "Día del mes.", "1"),
      ("HORA", "texto", "Hora consultada: 00:00, 06:00, 12:00 o 18:00. No todas las estaciones reportan a todas las horas.", "06:00"),
      ("UNIDAD", "texto", "Unidad del valor: m3/s (caudal), m o m.s.n.m (nivel).", "m3/s"),
      ("VALOR", "decimal", "Dato de la estación a esa fecha y hora (la columna «Hoy» de la página de SENAMHI).", "23865.79"),
      ("ANOMALIA", "decimal", "Anomalía respecto a la normal histórica: en % si el dato es caudal; en metros si es nivel.", "-27.03"),
      ("UNIDAD_ANOMALIA", "texto", "Unidad de la anomalía: %, m o m.s.n.m.", "%"),
      ("TENDENCIA", "texto", "Tendencia respecto al día anterior, con el código de SENAMHI: A = ascenso, LA = ligero ascenso, E = estable, LD = ligero descenso, D = descenso. Vacío si no hay.", "LA"),
      ("UMBRAL_ROJO", "decimal", "Umbral de alerta roja de la estación, en la unidad del valor.", "53835.1"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó de SENAMHI.", "10/11/2026")]),

    ("mensual", "1_DATOS", "4_Informacion_mensual.xlsx", "Información Mensual",
     "La pestaña «Información Mensual» de SENAMHI: el valor del mes de unas 57 estaciones principales, con su anomalía y tendencia.", "Una fila por estación y mes.",
     [("AÑO", "entero", "Año del mes.", "2023"), ("MES", "entero", "Mes, de 1 a 12.", "1"),
      ("FECHA", "fecha", "Primer día del mes, para ordenar como serie.", "01/01/2023"),
      _ESTACION,
      ("ESTACION", "texto", "Nombre de la estación.", "TAMSHIYACU"),
      ("CUERPO_AGUA", "texto", "Río, lago o canal.", "RÍO AMAZONAS"),
      ("DEPARTAMENTO", "texto", "Departamento de la estación.", "LORETO"),
      ("ZONA", "texto", "Sector del país: NORTE, CENTRO o SUR.", "NORTE"),
      ("REGION_HIDROGRAFICA", "texto", "Región hidrográfica.", "Región Hidrográfica del Amazonas"),
      ("COD_ZONAL", "texto", "Código de la dirección zonal de SENAMHI (01 a 13).", "08"),
      ("UNIDAD", "texto", "Unidad del valor: m3/s, m o m.s.n.m.", "m3/s"),
      ("VALOR_MES", "decimal", "Valor del mes publicado por SENAMHI (caudal o nivel).", "23865.79"),
      ("VALOR_MES_ANTERIOR", "decimal", "Valor del mes anterior, como lo muestra la misma tabla.", "17616.73"),
      ("ANOMALIA", "decimal", "Anomalía mensual respecto a la normal: en % para caudal; en metros para nivel.", "-27.03"),
      ("UNIDAD_ANOMALIA", "texto", "Unidad de la anomalía.", "%"),
      ("TENDENCIA", "texto", "Tendencia entre el mes y el anterior, con el código de SENAMHI (A, LA, E, LD, D). Vacío si no hay.", "A"),
      ("UMBRAL_ROJO", "decimal", "Umbral de alerta roja de la estación.", "53835.1"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó de SENAMHI.", "10/11/2026")]),

    ("no-publicado", "1_DATOS", "5_Series_no_publicadas_por_SENAMHI.xlsx", "Series que SENAMHI no publica",
     "Lo que SENAMHI devuelve de una variable que NO publica en esa estación (en su página el botón «Nivel» o «Caudal» está deshabilitado): por ejemplo, el «nivel» "
     "de las estaciones que solo publican caudal. Probablemente son lecturas internas sin validar. Se guardan aparte y NO se usan en el mapa, las alertas ni los gráficos. "
     "Conviene no usarlas para análisis sin contrastarlas.", "Una fila por estación, variable y día (mismas columnas que «Nivel y caudal diario»).", _FILA_DIARIO),

    ("control", "2_CONTROL_DE_CALIDAD", "Control_de_la_serie_diaria.xlsx", "Control de la serie diaria",
     "Control de calidad de «Nivel y caudal diario»: hasta qué fechas llega cada estación, cuántos días le faltan y si tiene saltos raros o datos dudosos. "
     "Sirve para decidir qué estaciones usar.", "Una fila por estación y variable.",
     [("COD_ESTACION", "texto", "Código de la estación.", "240001"),
      ("ESTACION", "texto", "Nombre de la estación.", "SANTA MARÍA DE NANAY"),
      ("VARIABLE", "texto", "NIVEL o CAUDAL.", "NIVEL"),
      ("ESTADO", "texto", "OK: tiene datos desde el inicio del período. OK desde dd/mm/aaaa: SENAMHI no trae datos más atrás. SIN DATOS: la estación no tiene esa variable. SIN RESPUESTA: la consulta falló (hay que volver a descargar). REVISAR (saltos): hay cambios bruscos entre días seguidos. NO PUBLICADA POR SENAMHI: ver el archivo 5.", "OK"),
      ("PRIMERA_FECHA", "fecha", "Primer día con dato.", "01/01/2020"),
      ("ULTIMA_FECHA", "fecha", "Último día con dato.", "10/11/2026"),
      ("DIAS_CON_DATO", "entero", "Número de días con dato.", "1410"),
      ("DIAS_FALTANTES", "entero", "Días sin dato entre la primera y la última fecha (huecos de la serie).", "3"),
      ("SALTOS_RAROS", "entero", "Número de cambios de un día al siguiente que superan 20 veces el cambio habitual de la estación (percentil 90). Sirve para ubicar posibles errores.", "0"),
      ("DATOS_DUDOSOS", "entero", "Número de días marcados como DATO_DUDOSO (picos aislados imposibles en un río). Solo se revisa el nivel.", "1"),
      ("LLEGA_AL_INICIO", "lógico", "VERDADERO si la serie empieza dentro del primer mes del período pedido.", "True"),
      ("CRUCE_MENSUAL_DIF_MAX_%", "decimal", "Mayor diferencia, en %, entre el promedio de los días de un mes y el valor mensual publicado por SENAMHI (Información Mensual), en los meses con 25 días o más. Vacío si la estación no está en la mensual.", "1.8"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó.", "10/11/2026")]),

    ("control-info", "2_CONTROL_DE_CALIDAD", "Control_de_la_informacion_diaria.xlsx", "Control de la Información Diaria",
     "Registro de cada consulta a la Información Diaria: cuántas estaciones respondió SENAMHI y cuántas traían dato.", "Una fila por fecha y hora consultada.",
     [("FECHA", "fecha", "Día consultado.", "01/01/2023"), ("HORA", "texto", "Hora consultada.", "06:00"),
      ("ESTACIONES", "entero", "Estaciones que devolvió SENAMHI en esa consulta, con o sin dato.", "72"),
      ("CON_DATO", "entero", "Cuántas de ellas traían dato (las demás venían con -999 = sin dato).", "64"),
      ("ESTADO", "texto", "OK o SIN RESPUESTA (se reintenta en la siguiente descarga).", "OK"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó.", "10/11/2026")]),

    ("control-mensual", "2_CONTROL_DE_CALIDAD", "Control_de_la_informacion_mensual.xlsx", "Control de la Información Mensual",
     "Registro de cada mes pedido a la Información Mensual.", "Una fila por mes consultado.",
     [("AÑO", "entero", "Año pedido.", "2026"), ("MES", "entero", "Mes pedido.", "11"),
      ("SERVIDO", "texto", "Mes que realmente devolvió SENAMHI (mm/aaaa). Si el mes pedido aún no está publicado, devuelve el último que tiene.", "10/2026"),
      ("ESTACIONES", "entero", "Estaciones en la respuesta.", "57"),
      ("ESTADO", "texto", "OK · SIN DATOS · AÚN NO PUBLICADO (devuelve otro mes; no se guarda).", "OK"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó.", "10/11/2026")]),

    ("log", "2_CONTROL_DE_CALIDAD", "Registro_de_consultas_al_hidrograma.xlsx", "Registro de consultas al hidrograma",
     "Bitácora de las consultas al hidrograma de SENAMHI de la última descarga: qué se pidió y qué respondió.", "Una fila por consulta (estación, variable y año hidrológico pedido).",
     [("COD_ESTACION", "texto", "Código de la estación consultada.", "240001"),
      ("ESTACION", "texto", "Nombre de la estación.", "SANTA MARÍA DE NANAY"),
      ("VARIABLE", "texto", "NIVEL o CAUDAL.", "NIVEL"),
      ("VARIABLE_OPCION", "texto", "Código de variables de la estación que se envió a SENAMHI.", "N"),
      ("FECHA_HORA_PEDIDA", "texto", "Fecha y hora enviada. La actual, o el 31/08 del año siguiente para pedir un año hidrológico pasado.", "2025-08-31 06:00:00"),
      ("INICIO_SERIE", "fecha", "Primer día de la serie que devolvió SENAMHI (debe ser un 01/09).", "01/09/2024"),
      ("FILAS", "entero", "Filas diarias obtenidas de esa respuesta.", "729"),
      ("ESTADO", "texto", "OK · SIN DATOS · SIN RESPUESTA · DEVOLVIO OTRO AÑO.", "OK"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se descargó.", "10/11/2026")]),
]


def _dmy(texto):
    try:
        return datetime.strptime(texto, "%d/%m/%Y")
    except (TypeError, ValueError):
        return None


def _celda(col, v):
    """El valor de una celda de CSV como número, fecha o texto, según la columna."""
    if v == "":
        return None
    if col in DECIMALES:
        try:
            return float(v)
        except ValueError:
            return v
    if col in ENTEROS:
        try:
            return int(float(v))
        except ValueError:
            return v
    if col in FECHAS:
        return _dmy(v) or v
    return v


def _excel(csv_ruta, destino, titulo, que, fila, columnas, pie):
    """Un CSV → un .xlsx con la hoja «Descripción» y la hoja «Datos» (o «Datos 2», … si pasa del máximo de filas). Devuelve las filas escritas."""
    libro = xlsxwriter.Workbook(destino, {"constant_memory": True, "default_date_format": "dd/mm/yyyy", "strings_to_numbers": False,
                                          "strings_to_formulas": False, "strings_to_urls": False})
    cab = libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#111149", "valign": "top", "text_wrap": True, "border": 1, "border_color": "#CCD3DF"})
    negrita = libro.add_format({"bold": True}); ajuste = libro.add_format({"text_wrap": True, "valign": "top"})
    mono = libro.add_format({"bold": True, "font_color": "#111149", "valign": "top"})
    fecha = libro.add_format({"num_format": "dd/mm/yyyy"})
    # hoja de descripción: para qué sirve el archivo y qué es cada columna
    d = libro.add_worksheet("Descripción")
    d.set_column(0, 0, 26); d.set_column(1, 1, 10); d.set_column(2, 2, 100); d.set_column(3, 3, 26)
    d.write(0, 0, titulo, libro.add_format({"bold": True, "font_size": 14, "font_color": "#111149"}))
    d.merge_range(1, 0, 1, 3, que, ajuste); d.set_row(1, 15 * (1 + len(que) // 130))
    d.merge_range(2, 0, 2, 3, fila, ajuste)
    d.merge_range(3, 0, 3, 3, pie, ajuste); d.set_row(3, 15 * (1 + len(pie) // 130))
    for j, t in enumerate(("Variable", "Tipo", "Descripción", "Ejemplo")):
        d.write(5, j, t, cab)
    for i, (v, t, desc, ej) in enumerate(columnas):
        d.write(6 + i, 0, v, mono); d.write(6 + i, 1, t, ajuste); d.write(6 + i, 2, desc, ajuste); d.write(6 + i, 3, ej, ajuste)
        d.set_row(6 + i, 15 * (1 + len(desc) // 105))
    # hojas de datos, escritas por filas
    escritas, hoja, fila_h, anchos = 0, None, 0, []
    with open(csv_ruta, encoding="utf-8-sig", newline="") as f:
        lector = csv.reader(f)
        encabezado = next(lector)
        anchos = [max(10, min(len(c) + 3, 36)) for c in encabezado]
        for fila_csv in lector:
            if hoja is None or fila_h > MAX_FILAS_EXCEL:
                if hoja is not None:
                    hoja.autofilter(0, 0, fila_h - 1, len(encabezado) - 1)
                hoja = libro.add_worksheet("Datos" if escritas == 0 else f"Datos {escritas // MAX_FILAS_EXCEL + 1}")
                for j, c in enumerate(encabezado):
                    hoja.write(0, j, c, cab); hoja.set_column(j, j, anchos[j], fecha if c in FECHAS else None)
                hoja.freeze_panes(1, 0); hoja.set_row(0, 30)
                fila_h = 1
            for j, (c, v) in enumerate(zip(encabezado, fila_csv)):
                x = _celda(c, v)
                if x is None:
                    continue
                if isinstance(x, datetime):
                    hoja.write_datetime(fila_h, j, x, fecha)
                else:
                    hoja.write(fila_h, j, x)
            fila_h += 1
            escritas += 1
    if hoja is None:                                         # sin filas: solo el encabezado
        hoja = libro.add_worksheet("Datos")
        for j, c in enumerate(encabezado):
            hoja.write(0, j, c, cab); hoja.set_column(j, j, anchos[j])
        fila_h = 1
    hoja.autofilter(0, 0, max(fila_h - 1, 1), len(encabezado) - 1)
    libro.close()
    return escritas


def _tabla_texto(columnas):
    out = []
    for v, t, desc, ej in columnas:
        out.append(f"  {v}  [{t}]")
        out.append(_sangrar(desc, 6))
        if ej:
            out.append(f"      Ejemplo: {ej}")
        out.append("")
    return "\n".join(out)


def _sangrar(texto, n, ancho=100):
    """Parte un texto en líneas de hasta «ancho» caracteres, con n espacios de sangría."""
    lineas, actual = [], ""
    for p in texto.split():
        if len(actual) + len(p) + 1 > ancho and actual:
            lineas.append(actual); actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        lineas.append(actual)
    return "\n".join(" " * n + l for l in lineas)


def diccionario(hoy_txt):
    t = ["DICCIONARIO DE VARIABLES", "Nivel y caudal de los ríos del Perú · SENAMHI, Monitoreo Hidrológico", f"Versión del {hoy_txt}", "=" * 78, "",
         "CONVENCIONES", "",
         _sangrar("Los datos vienen de la página «Monitoreo Hidrológico» de SENAMHI (www.senamhi.gob.pe/?p=monitoreo-hidrologico): el hidrograma diario de cada "
                  "estación del mapa y las pestañas «Información Diaria» e «Información Mensual». Son datos en tiempo casi real, que SENAMHI publica sujetos a "
                  "revisión y validación.", 2), "",
         _sangrar("Una celda vacía significa «sin dato» (SENAMHI lo marca con -999; aquí se deja vacío).", 2),
         _sangrar("Las fechas están como fecha de Excel (se muestran dd/mm/aaaa). Los números usan punto decimal en los CSV y el formato de tu Excel en los .xlsx.", 2),
         _sangrar("Año hidrológico: va de setiembre a agosto y se nombra por el año en que empieza (2026 = 01/09/2026 al 31/08/2027).", 2),
         _sangrar("COD_ESTACION une todos los archivos. Es texto (puede tener letras): no lo conviertas a número.", 2),
         _sangrar("Unidades: el nivel está en metros sobre el nivel del mar (m.s.n.m) o en metros (m); el caudal, en metros cúbicos por segundo (m3/s).", 2),
         _sangrar("Cada Excel trae en su primera hoja («Descripción») este mismo diccionario, y los datos en la hoja «Datos».", 2), "",
         "=" * 78, ""]
    for clave, carpeta, archivo, titulo, que, fila, cols in PAQUETE:
        t += [f"{carpeta}/{archivo}", titulo.upper(), "-" * 78, _sangrar(que, 0), "", fila, "", _tabla_texto(cols), "=" * 78, ""]
    return "\n".join(t)


def leeme(hoy_txt, resumen, filas, desde_txt=""):
    """El LEEME.txt: qué es el paquete, qué trae cada archivo y cómo usarlo."""
    r = resumen or {}
    num = lambda n: f"{int(n):,}".replace(",", " ")           # noqa: E731
    t = ["NIVEL Y CAUDAL DE LOS RÍOS DEL PERÚ (SENAMHI)",
         "Departamento de Estudios Económicos · BCRP Sucursal Iquitos",
         f"Paquete generado el {hoy_txt}", "=" * 78, "",
         "QUÉ ES ESTO", "",
         _sangrar("Los datos de nivel y caudal de los ríos que publica el Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI) en su página de "
                  "Monitoreo Hidrológico, descargados y ordenados para que se puedan usar en Excel, R, Python, EViews u otro programa. Cubre las estaciones "
                  "hidrométricas de todo el país, con énfasis en la Amazonía (Loreto, San Martín y Ucayali).", 2), "",
         "RESUMEN DE LO QUE TRAE", ""]
    t += [f"  - Estaciones en el catálogo: {num(r.get('estaciones', 0))} (con datos de nivel o caudal: {num(r.get('estaciones_con_datos', 0))}).",
          f"  - Filas de la serie diaria: {num(r.get('filas_diario', 0))}" + (f", {desde_txt}" if desde_txt else "") +
          (f", hasta el {r['ultima_fecha'][8:10]}/{r['ultima_fecha'][5:7]}/{r['ultima_fecha'][:4]}." if r.get("ultima_fecha") else "."),
          f"  - Filas de Información Diaria (4 lecturas por día): {num(r.get('filas_info_diaria', 0))}.",
          f"  - Filas de Información Mensual: {num(r.get('filas_mensual', 0))}.",
          f"  - Series que SENAMHI no publica (guardadas aparte): {num(r.get('filas_no_publicadas', 0))} filas.",
          f"  - Descarga de SENAMHI del día: {r.get('recolectado', '') or 'sin fecha'}.", "",
          "CONTENIDO DEL ZIP", "",
          "  LEEME.txt                         Este archivo.",
          "  DICCIONARIO_DE_VARIABLES.txt      Qué significa cada columna de cada Excel.", "",
          "  1_DATOS/  (los datos para analizar)"]
    for clave, carpeta, archivo, titulo, que, fila, cols in PAQUETE:
        if carpeta != "1_DATOS":
            continue
        t += ["", f"    {archivo}", f"      {titulo} · {num(filas.get(clave, 0))} {'fila' if filas.get(clave, 0) == 1 else 'filas'}.", _sangrar(que, 6), f"      {fila}"]
    t += ["", "  2_CONTROL_DE_CALIDAD/  (para juzgar qué tan confiable es cada serie)"]
    for clave, carpeta, archivo, titulo, que, fila, cols in PAQUETE:
        if carpeta != "2_CONTROL_DE_CALIDAD":
            continue
        t += ["", f"    {archivo}", f"      {titulo} · {num(filas.get(clave, 0))} {'fila' if filas.get(clave, 0) == 1 else 'filas'}.", _sangrar(que, 6), f"      {fila}"]
    t += ["", "=" * 78, "", "CÓMO USARLO", "",
          _sangrar("1. Empieza por 1_Estaciones_hidrometricas.xlsx para ubicar la estación que te interesa (por río, departamento o dirección zonal) y anota su COD_ESTACION.", 2),
          _sangrar("2. Filtra 2_Nivel_y_caudal_diario.xlsx por ese COD_ESTACION y por VARIABLE (NIVEL o CAUDAL). La hoja trae filtros en el encabezado.", 2),
          _sangrar("3. Quédate con SERIE = ACTUAL cuando necesites el mínimo, máximo, promedio histórico y umbrales; las filas ANTERIOR solo traen VALOR y sirven para completar días.", 2),
          _sangrar("4. Mira Control_de_la_serie_diaria.xlsx: ahí dice desde cuándo y hasta cuándo hay datos, cuántos días faltan y si la serie tiene saltos raros o datos dudosos.", 2),
          _sangrar("5. Para unir archivos usa COD_ESTACION (como texto). Para series de tiempo usa FECHA; para comparar años hidrológicos, AÑO_HIDROLOGICO.", 2), "",
          "ADVERTENCIAS", "",
          _sangrar("- Son datos en tiempo casi real, sujetos a revisión y validación de SENAMHI: los valores recientes pueden cambiar.", 2),
          _sangrar("- DATO_DUDOSO = SI marca un pico aislado de 1 o 2 días que sube y vuelve al nivel de antes (imposible en un río). El valor NO se borró: decide tú si lo "
                   "excluyes. Solo se revisa el nivel; en caudal las crecidas repentinas de los ríos de montaña son reales.", 2),
          _sangrar("- El «promedio histórico» (PROM_HISTORICO) es una curva fija que publica SENAMHI para cada día del año. SENAMHI no dice de qué años la calcula.", 2),
          _sangrar("- Los umbrales rojo, naranja y amarillo los fija SENAMHI para cada estación. En unas son de nivel bajo (vaciante) y en otras de crecida.", 2),
          _sangrar("- Algunas estaciones no publican una de las dos variables. Lo que SENAMHI devuelve igual está en el archivo 5 y no debería usarse sin contrastarlo.", 2),
          _sangrar("- Los saltos entre días y los huecos son tal como los publica SENAMHI: no se rellenó ni se corrigió nada.", 2), "",
          "FUENTE Y CONTACTO", "",
          "  Fuente: SENAMHI, Monitoreo Hidrológico (www.senamhi.gob.pe/?p=monitoreo-hidrologico).",
          "  Elaboración: Departamento de Estudios Económicos, BCRP Sucursal Iquitos.", ""]
    return "\n".join(t)


def armar_paquete(carpeta_csv, destino, resumen, hoy_txt, archivos, desde_txt=""):
    """Escribe en «destino» (.zip) el paquete. «archivos»: {clave: nombre del CSV}. Devuelve {clave: filas}."""
    base = f"SENAMHI_Rios_del_Peru_{datetime.strptime(hoy_txt, '%d/%m/%Y'):%Y-%m-%d}"
    tmp = destino + ".d"
    os.makedirs(tmp, exist_ok=True)
    filas = {}
    try:
        for clave, carpeta, archivo, titulo, que, fila, cols in PAQUETE:
            ruta = os.path.join(carpeta_csv, archivos[clave])
            if not os.path.exists(ruta):
                continue
            salida = os.path.join(tmp, archivo)
            pie = f"Datos de SENAMHI (Monitoreo Hidrológico), descargados el {hoy_txt}. Departamento de Estudios Económicos, BCRP Sucursal Iquitos."
            filas[clave] = _excel(ruta, salida, titulo, que, fila, cols, pie)
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.writestr(f"{base}/LEEME.txt", "﻿" + leeme(hoy_txt, resumen, filas, desde_txt))
            z.writestr(f"{base}/DICCIONARIO_DE_VARIABLES.txt", "﻿" + diccionario(hoy_txt))
            for clave, carpeta, archivo, *_ in PAQUETE:
                salida = os.path.join(tmp, archivo)
                if os.path.exists(salida):
                    z.write(salida, f"{base}/{carpeta}/{archivo}")
    finally:
        for n in os.listdir(tmp):
            os.remove(os.path.join(tmp, n))
        os.rmdir(tmp)
    return filas
