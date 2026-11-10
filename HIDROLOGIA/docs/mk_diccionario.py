"""Genera HIDROLOGIA/docs/Diccionario_SENAMHI_rios.pdf: el diccionario de variables de los archivos que produce
HIDROLOGIA/SENAMHI_Rios.ipynb (carpetas DATA, CONTROL y CRUDO de SENAMHI_HIDROLOGIA en Drive).

Uso:  pip install reportlab  ·  python HIDROLOGIA/docs/mk_diccionario.py
Si cambian las columnas del notebook, se actualizan aquí las listas y se vuelve a generar.
"""
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, MID, HAIR, PANEL, TEAL = (colors.HexColor(c) for c in ("#111149", "#5A5A9E", "#CCD3DF", "#F6F8FB", "#2A9DA1"))
SALIDA = Path(__file__).with_name("Diccionario_SENAMHI_rios.pdf")
HOY = date.today().strftime("%d/%m/%Y")

E = {
    "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=4),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=11, leading=14, textColor=MID, spaceAfter=10),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=6, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=12, alignment=TA_LEFT, spaceAfter=4),
    "c": ParagraphStyle("c", fontName="Helvetica", fontSize=8, leading=10),
    "cb": ParagraphStyle("cb", fontName="Courier-Bold", fontSize=7.5, leading=10, textColor=NAVY),
    "ch": ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=8.5, leading=10, textColor=colors.white),
}


def tabla(filas, anchos, cabecera):
    datos = [[Paragraph(t, E["ch"]) for t in cabecera]]
    for f in filas:
        datos.append([Paragraph(f[0], E["cb"])] + [Paragraph(str(x), E["c"]) for x in f[1:]])
    t = Table(datos, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, HAIR), ("BOX", (0, 0), (-1, -1), 0.6, HAIR),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


CAB = ["Variable", "Tipo", "Descripción", "Ejemplo"]
ANCHOS = [4.6 * cm, 2.2 * cm, 15.4 * cm, 4.5 * cm]

# (archivo, carpeta, qué es, una fila es…, [(variable, tipo, descripción, ejemplo)])
ARCHIVOS = [
    ("SENAMHI_rios_diario.csv", "DATA",
     "Serie diaria del <b>hidrograma</b> («Diario») de las estaciones del mapa de Monitoreo Hidrológico: nivel y, donde "
     "la estación lo tiene, caudal. Se acumula: cada corrida reemplaza los días que vuelve a leer.",
     "Una fila por estación, variable y día.",
     [("COD_ESTACION", "texto", "Código de la estación en SENAMHI. Es la llave para unir con los demás archivos. Puede tener letras.", "240103 · 47E0D438"),
      ("ESTACION", "texto", "Nombre de la estación hidrométrica.", "TAMSHIYACU"),
      ("RIO", "texto", "Río o cuerpo de agua, como lo rotula el hidrograma.", "RÍO AMAZONAS"),
      ("VARIABLE", "texto", "Qué se mide: <b>NIVEL</b> o <b>CAUDAL</b>.", "NIVEL"),
      ("UNIDAD", "texto", "Unidad del valor: m.s.n.m (metros sobre el nivel del mar) o m para el nivel; m3/s para el caudal.", "m.s.n.m"),
      ("FECHA", "fecha", "Día del dato, en formato dd/mm/aaaa.", "10/11/2026"),
      ("AÑO, MES, DIA", "entero", "La misma fecha separada en tres columnas, para filtrar y agrupar.", "2026 · 11 · 10"),
      ("AÑO_HIDROLOGICO", "entero", "Año hidrológico al que pertenece el día. Va de setiembre a agosto y se nombra por el año en que empieza: 2026 = 01/09/2026 a 31/08/2027.", "2026"),
      ("VALOR", "decimal", "Valor del día que dibuja el hidrograma (serie «datoActual» o «datoAnterior»). En lo revisado es el promedio del mínimo y el máximo del día.", "112.56"),
      ("MINIMO", "decimal", "Valor mínimo del día. Solo viene en las filas de SERIE = ACTUAL.", "112.50"),
      ("MAXIMO", "decimal", "Valor máximo del día. Solo viene en las filas de SERIE = ACTUAL.", "112.62"),
      ("PROM_HISTORICO", "decimal", "Promedio histórico de SENAMHI para ese día del año (línea «Prom. Histórico»). Solo en SERIE = ACTUAL.", "111.90"),
      ("UMBRAL_ROJO", "decimal", "Umbral de alerta roja de la estación, en la misma unidad. Solo en SERIE = ACTUAL.", "110.05"),
      ("UMBRAL_NARANJA", "decimal", "Umbral de alerta naranja. Solo en SERIE = ACTUAL.", "110.94"),
      ("UMBRAL_AMARILLO", "decimal", "Umbral de alerta amarilla. Solo en SERIE = ACTUAL.", "111.68"),
      ("SERIE", "texto", "De qué serie del hidrograma salió la fila. <b>ACTUAL</b>: del año hidrológico pedido (trae mínimo, máximo, promedio histórico y umbrales). <b>ANTERIOR</b>: leído como «año anterior» desde el hidrograma del año siguiente (solo trae VALOR). Si un día está en las dos, se guarda ACTUAL.", "ACTUAL"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se recolectó el dato de SENAMHI (dd/mm/aaaa).", "10/11/2026")]),

    ("SENAMHI_rios_info_diaria.csv", "DATA",
     "Pestaña <b>«Información Diaria»</b>: el dato de unas 70 estaciones principales a una hora dada (00:00, 06:00, 12:00 "
     "y 18:00), con su anomalía y tendencia. Casi todas reportan caudal. Solo se guardan las filas con dato.",
     "Una fila por estación, día y hora.",
     [("COD_ESTACION", "texto", "Código de la estación en SENAMHI.", "240103"),
      ("ESTACION", "texto", "Nombre de la estación hidrométrica.", "TAMSHIYACU"),
      ("CUERPO_AGUA", "texto", "Río, lago o canal donde está la estación.", "RÍO AMAZONAS"),
      ("CUENCA", "texto", "Cuenca o intercuenca, según SENAMHI.", "Intercuenca 49797"),
      ("DEPARTAMENTO", "texto", "Departamento de la estación.", "LORETO"),
      ("ZONA", "texto", "Sector del país: NORTE, CENTRO o SUR.", "NORTE"),
      ("REGION_HIDROGRAFICA", "texto", "Región hidrográfica: del Pacífico, del Amazonas o del Titicaca.", "Región Hidrográfica del Amazonas"),
      ("COD_ZONAL", "texto", "Código de la dirección zonal de SENAMHI a cargo de la estación (01 a 13; 08 es la de Loreto).", "08"),
      ("FECHA", "fecha", "Día del dato (dd/mm/aaaa).", "01/01/2023"),
      ("AÑO, MES, DIA", "entero", "La misma fecha separada en tres columnas.", "2023 · 1 · 1"),
      ("HORA", "texto", "Hora consultada: 00:00, 06:00, 12:00 o 18:00. No todas las estaciones reportan a todas las horas.", "06:00"),
      ("UNIDAD", "texto", "Unidad del valor: m3/s (caudal), m o m.s.n.m (nivel).", "m3/s"),
      ("VALOR", "decimal", "Dato de la estación a esa fecha y hora (columna «Hoy» de la página).", "23865.79"),
      ("ANOMALIA", "decimal", "Anomalía hídrica respecto a la normal histórica: en % si el dato es caudal; en metros si es nivel.", "-27.03"),
      ("UNIDAD_ANOMALIA", "texto", "Unidad de la anomalía: % , m o m.s.n.m.", "%"),
      ("TENDENCIA", "texto", "Tendencia respecto al día anterior, con el código de SENAMHI (la página lo muestra como flecha). Códigos vistos: A = ascenso, LA = ligero ascenso, E = estable, LD = ligero descenso, D = descenso. Vacío si no hay.", "LA"),
      ("UMBRAL_ROJO", "decimal", "Umbral de alerta roja de la estación, en la unidad del valor.", "53835.1"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se recolectó de SENAMHI.", "10/11/2026")]),

    ("SENAMHI_rios_mensual.csv", "DATA",
     "Pestaña <b>«Información Mensual»</b>: valor del mes de 57 estaciones principales, con su anomalía y tendencia.",
     "Una fila por estación y mes.",
     [("AÑO, MES", "entero", "Mes del dato.", "2023 · 1"),
      ("FECHA", "fecha", "Primer día del mes (dd/mm/aaaa), para ordenar como serie.", "01/01/2023"),
      ("COD_ESTACION", "texto", "Código de la estación en SENAMHI.", "240103"),
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
      ("FECHA_EXTRACCION", "fecha", "Día en que se recolectó de SENAMHI.", "10/11/2026")]),

    ("SENAMHI_ESTACIONES.csv", "DATA",
     "Catálogo de las estaciones del mapa de Monitoreo Hidrológico (143 en noviembre de 2026).",
     "Una fila por estación.",
     [("ID_ESTACION", "entero", "Identificador interno de SENAMHI (no es el código).", "151"),
      ("COD_ESTACION", "texto", "Código de la estación. Llave para unir con los demás archivos.", "240111"),
      ("ESTACION", "texto", "Nombre de la estación.", "BELLAVISTA"),
      ("SUB_ESTACION", "texto", "Subestación, si SENAMHI la indica. Suele venir vacía.", ""),
      ("ESTADO", "entero", "Estado en SENAMHI: 1 = activa.", "1"),
      ("COD_ZONAL", "texto", "Dirección zonal de SENAMHI que tiene la estación (filtro «Dirección Zonal» del mapa), de 01 a 13. Vacío si no se pudo leer.", "08"),
      ("DIRECCION_ZONAL", "texto", "Nombre de la dirección zonal, por su sede. La 08 es la de Loreto.", "DZ 8 · Loreto"),
      ("LAT, LON", "decimal", "Coordenadas (grados decimales, WGS84). Solo si el servidor de mapas de SENAMHI entrega la capa; si no, no aparecen.", "-3.48 · -73.07"),
      ("GEO_…", "varios", "Otros atributos de la capa de estaciones del servidor de mapas, con el prefijo GEO_. Solo si esa capa se pudo leer.", ""),
      ("FECHA_HORA_ULTIMA", "texto", "Fecha y hora del último dato de la estación, según su ficha en el mapa (aaaa-mm-dd hh:mm:ss).", "2026-11-09 11:00:00"),
      ("VARIABLE_OPCION", "texto", "Código de SENAMHI que indica qué variables ofrece el hidrograma de la estación (N = solo nivel).", "N"),
      ("RIO", "texto", "Río, tomado del hidrograma.", "RÍO NAPO"),
      ("VARIABLES_CON_DATOS", "texto", "Variables de la estación que tienen datos en SENAMHI_rios_diario.csv.", "CAUDAL / NIVEL"),
      ("DEPARTAMENTO", "texto", "Departamento. Solo se conoce para las estaciones que salen en la Información Diaria o Mensual; en las demás queda vacío (usar DIRECCION_ZONAL).", "LORETO"),
      ("FECHA_EXTRACCION", "fecha", "Día en que se recolectó de SENAMHI.", "10/11/2026")]),

    ("CONTROL SENAMHI rios_diario.csv", "CONTROL",
     "Control de calidad de la serie diaria del hidrograma.",
     "Una fila por estación y variable consultada.",
     [("COD_ESTACION, ESTACION", "texto", "Estación controlada.", "240103 · TAMSHIYACU"),
      ("VARIABLE", "texto", "NIVEL o CAUDAL.", "CAUDAL"),
      ("ESTADO", "texto", "<b>OK</b>: tiene datos desde el inicio del período. <b>OK desde dd/mm/aaaa</b>: SENAMHI no trae datos más atrás. <b>SIN DATOS</b>: la estación no tiene esa variable. <b>SIN RESPUESTA</b>: la consulta falló (volver a recolectar). <b>REVISAR (saltos)</b>: hay cambios bruscos entre días seguidos.", "OK"),
      ("PRIMERA_FECHA, ULTIMA_FECHA", "fecha", "Primer y último día con dato.", "01/01/2023 · 10/11/2026"),
      ("DIAS_CON_DATO", "entero", "Número de días con dato.", "1410"),
      ("DIAS_FALTANTES", "entero", "Días sin dato entre la primera y la última fecha (huecos de la serie).", "3"),
      ("SALTOS_RAROS", "entero", "Número de cambios de un día al siguiente que son más de 20 veces el cambio habitual de la estación (percentil 90). Sirve para ubicar posibles errores del dato.", "0"),
      ("LLEGA_AL_INICIO", "lógico", "True si la serie empieza dentro del primer mes del período pedido.", "True"),
      ("CRUCE_MENSUAL_DIF_MAX_%", "decimal", "Mayor diferencia, en %, entre el promedio de los días de un mes y el valor mensual publicado (Información Mensual), en los meses con 25 días o más y la misma unidad. Vacío si la estación no está en la mensual.", "1.8"),
      ("FECHA_EXTRACCION", "fecha", "Día de la recolección.", "10/11/2026")]),

    ("CONTROL SENAMHI rios_info_diaria.csv", "CONTROL",
     "Registro de cada consulta de la Información Diaria. También sirve para no repetir las que ya están hechas.",
     "Una fila por fecha y hora consultada.",
     [("FECHA", "fecha", "Día consultado (dd/mm/aaaa).", "01/01/2023"),
      ("HORA", "texto", "Hora consultada.", "06:00"),
      ("ESTACIONES", "entero", "Estaciones que devolvió SENAMHI en esa consulta, con o sin dato.", "72"),
      ("CON_DATO", "entero", "Cuántas de ellas traían dato (las demás venían con -999 = sin dato).", "64"),
      ("ESTADO", "texto", "OK o SIN RESPUESTA (se reintenta en la siguiente corrida).", "OK"),
      ("FECHA_EXTRACCION", "fecha", "Día de la recolección.", "10/11/2026")]),

    ("CONTROL SENAMHI rios_mensual.csv", "CONTROL",
     "Registro de cada mes pedido a la Información Mensual.",
     "Una fila por mes consultado.",
     [("AÑO, MES", "entero", "Mes pedido.", "2026 · 11"),
      ("SERVIDO", "texto", "Mes que realmente devolvió SENAMHI (mm/aaaa). Si el mes pedido aún no está publicado, devuelve el último que tiene.", "10/2026"),
      ("ESTACIONES", "entero", "Estaciones en la respuesta.", "57"),
      ("ESTADO", "texto", "OK · SIN DATOS · AÚN NO PUBLICADO (devuelve otro mes; no se guarda).", "OK"),
      ("FECHA_EXTRACCION", "fecha", "Día de la recolección.", "10/11/2026")]),

    ("LOG SENAMHI consultas.csv", "CONTROL",
     "Bitácora de las consultas al hidrograma de la última corrida.",
     "Una fila por consulta (estación, variable y año hidrológico pedido).",
     [("COD_ESTACION, ESTACION", "texto", "Estación consultada.", "240001 · SANTA MARÍA DE NANAY"),
      ("VARIABLE", "texto", "NIVEL o CAUDAL.", "NIVEL"),
      ("VARIABLE_OPCION", "texto", "Código de variables de la estación que se envió a SENAMHI.", "N"),
      ("FECHA_HORA_PEDIDA", "texto", "Fecha y hora enviada. La actual, o el 31/08 del año siguiente para pedir un año hidrológico pasado.", "2025-08-31 06:00:00"),
      ("INICIO_SERIE", "fecha", "Primer día de la serie que devolvió SENAMHI (debe ser un 01/09).", "01/09/2024"),
      ("FILAS", "entero", "Filas diarias obtenidas de esa respuesta.", "729"),
      ("ESTADO", "texto", "OK · SIN DATOS · SIN RESPUESTA · DEVOLVIO OTRO AÑO (dd/mm/aaaa).", "OK"),
      ("FECHA_EXTRACCION", "fecha", "Día de la recolección.", "10/11/2026")]),
]

CRUDO = [
    ("meta", "objeto", "Datos de la recolección: fecha (hoy), rango pedido (desdeFecha, hastaFecha), si fue prueba rápida, variables y horas.", ""),
    ("estaciones", "lista", "Lista de estaciones, tal como la devuelve SENAMHI.", ""),
    ("zonales", "objeto", "Dirección zonal de cada estación: {código de estación: código zonal}.", '{"240103": "08"}'),
    ("fichas", "objeto", "Ficha de cada estación: última fecha y hora, variable y variable_opcion.", ""),
    ("graficas", "lista", "Un elemento por consulta al hidrograma: estación, variable, año hidrológico, estado y las series del año (valores sin repetir las fechas).", ""),
    ("mensual", "objeto", "Respuesta de la Información Mensual por mes («aaaa-mm»).", ""),
    ("infoDiaria", "objeto", "Por «aaaa-mm-dd hh:mm»: número de estaciones de la respuesta y las filas con dato.", ""),
    ("infoMeta", "objeto", "Nombre, río, cuenca, departamento y zona de las estaciones de la Información Diaria.", ""),
    ("wfs", "objeto", "Capa de estaciones del servidor de mapas (coordenadas), si respondió; si no, null.", ""),
    ("historiaOk", "lógico", "true si SENAMHI devolvió años hidrológicos pasados al pedirlos.", "true"),
]


def pie(c, doc):
    c.saveState()
    c.setFont("Helvetica", 7.5); c.setFillColor(MID)
    c.drawString(1.5 * cm, 1.0 * cm, "Diccionario de variables · Nivel y caudal de los ríos (SENAMHI) · Departamento de estudios BCRP-IQT")
    c.drawRightString(landscape(A4)[0] - 1.5 * cm, 1.0 * cm, f"Página {doc.page}")
    c.setStrokeColor(TEAL); c.setLineWidth(1.2)
    c.line(1.5 * cm, landscape(A4)[1] - 1.2 * cm, landscape(A4)[0] - 1.5 * cm, landscape(A4)[1] - 1.2 * cm)
    c.restoreState()


def construir():
    doc = SimpleDocTemplate(str(SALIDA), pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title="Diccionario de variables · Nivel y caudal de los ríos (SENAMHI)",
                            author="Departamento de estudios BCRP-IQT")
    h = [Paragraph("Diccionario de variables", E["titulo"]),
         Paragraph(f"Nivel y caudal de los ríos · SENAMHI, Monitoreo Hidrológico · Versión del {HOY}", E["sub"]),
         Paragraph("<b>Fuente.</b> Página «Monitoreo Hidrológico» de SENAMHI (www.senamhi.gob.pe/?p=monitoreo-hidrologico): el "
                   "hidrograma diario de cada estación del mapa y las pestañas «Información Diaria» e «Información Mensual». "
                   "Los datos son en tiempo casi real y SENAMHI los publica sujetos a revisión y validación.", E["p"]),
         Paragraph("<b>Cómo se generan.</b> El recolector <font face='Courier'>HIDROLOGIA/senamhi_navegador.js</font> hace las consultas "
                   "desde el navegador y descarga un archivo crudo; el notebook <font face='Courier'>HIDROLOGIA/SENAMHI_Rios.ipynb</font> "
                   "lo convierte en los CSV de este diccionario y los guarda en Google Drive, carpeta "
                   "<font face='Courier'>SENAMHI_HIDROLOGIA</font> (subcarpetas DATA, CONTROL y CRUDO).", E["p"]),
         Paragraph("<b>Convenciones.</b> CSV en UTF-8 con BOM, separados por coma y con punto decimal. Fechas en dd/mm/aaaa. "
                   "Una celda vacía significa «sin dato» (SENAMHI lo marca con -999; aquí se deja vacío). "
                   "Año hidrológico: de setiembre a agosto, nombrado por el año en que empieza. "
                   "COD_ESTACION une todos los archivos y debe leerse como texto.", E["p"]),
         Spacer(1, 4),
         Paragraph("Archivos", E["h1"]),
         tabla([(a, c, r, u) for a, c, r, u, _ in ARCHIVOS] +
               [("SENAMHI_crudo_AAAA-MM-DD.json", "CRUDO", "Archivo que descarga el navegador, con las respuestas de SENAMHI en forma compacta. Es la entrada del notebook.", "Un archivo por recolección.")],
               [6.2 * cm, 2.0 * cm, 13.0 * cm, 5.5 * cm], ["Archivo", "Carpeta", "Contenido", "Una fila es…"]),
         PageBreak()]
    for nombre, carpeta, que, fila, cols in ARCHIVOS:
        h += [Paragraph(f"{carpeta} / {nombre}", E["h1"]), Paragraph(f"{que} <b>{fila}</b>", E["p"]),
              tabla(cols, ANCHOS, CAB), Spacer(1, 10)]
    h += [Paragraph("CRUDO / SENAMHI_crudo_AAAA-MM-DD.json", E["h1"]),
          Paragraph("Archivo JSON que genera el recolector del navegador. No se usa para análisis: es la entrada del notebook y "
                    "queda como respaldo de lo que respondió SENAMHI. <b>Sus claves principales:</b>", E["p"]),
          tabla(CRUDO, ANCHOS, ["Clave", "Tipo", "Descripción", "Ejemplo"])]
    doc.build(h, onFirstPage=pie, onLaterPages=pie)
    print("PDF:", SALIDA)


if __name__ == "__main__":
    construir()
