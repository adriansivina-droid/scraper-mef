"""Genera HIDROCARBUROS/docs/Diccionario_datos_Proyecto_Petroleo.pdf (python3 mk_diccionario.py)."""
import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether)

FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FD + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

AZUL = colors.HexColor("#1F3A5F")
GRIS = colors.HexColor("#F2F4F7")
LINEA = colors.HexColor("#C9D1DB")
st = {
    "tit": ParagraphStyle("tit", fontName="DVB", fontSize=20, leading=25, textColor=AZUL, spaceAfter=6),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=11, leading=15, textColor=colors.HexColor("#4A5568")),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=14, leading=18, textColor=AZUL, spaceBefore=14, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=11, leading=14, textColor=AZUL, spaceBefore=10, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="DV", fontSize=9.2, leading=13, spaceAfter=5, alignment=TA_LEFT),
    "li": ParagraphStyle("li", fontName="DV", fontSize=9.2, leading=13, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "c": ParagraphStyle("c", fontName="DV", fontSize=8.2, leading=10.8),
    "cv": ParagraphStyle("cv", fontName="DVM", fontSize=8, leading=10.8, textColor=AZUL),
    "ch": ParagraphStyle("ch", fontName="DVB", fontSize=8.4, leading=10.8, textColor=colors.white),
}

def P(t, s="p"):
    return Paragraph(t, st[s])

def lista(items):
    return [Paragraph(i, st["li"], bulletText="•") for i in items]

def tabla(filas, anchos=(4.0, 3.0, 10.0), cab=("Variable", "Tipo / unidad", "Descripción")):
    data = [[P(c, "ch") for c in cab]]
    for f in filas:
        data.append([P(f[0], "cv")] + [P(x, "c") for x in f[1:]])
    t = Table(data, colWidths=[a * cm for a in anchos], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t

def pie(c, d):
    c.saveState()
    c.setFont("DV", 7.5); c.setFillColor(colors.HexColor("#718096"))
    c.drawString(2 * cm, 1.2 * cm, "Proyecto Petróleo · Diccionario de datos · versión 11/10/2026")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {d.page}")
    c.restoreState()

h = []
# ── Portada / introducción ───────────────────────────────────────────────────
h += [P("Diccionario de datos", "tit"),
      P("Proyecto Petróleo · Producción de hidrocarburos líquidos por lote (PERUPETRO) y variables geográficas de los lotes", "sub"),
      Spacer(1, 10),
      P("Repositorio: <font name='DVM'>adriansivina-droid/scraper-mef</font>, carpeta <font name='DVM'>HIDROCARBUROS/</font>. "
        "Este documento describe cada archivo que generan los notebooks, el significado de cada columna, sus unidades, "
        "los códigos que puede tomar y cómo se controló la calidad de los datos."),
      P("1. Qué son estos datos", "h1"),
      P("La base principal es la <b>producción fiscalizada mensual de hidrocarburos líquidos por lote</b> que publica PERUPETRO S.A. "
        "en su <i>Estadística Petrolera</i> (anuales 1994–2025 y mensuales del año en curso). <b>Fiscalizada</b> significa medida en el "
        "punto de fiscalización del contrato: es el volumen sobre el que se calculan regalías, no la producción \"de campo\" estimada."),
      *lista([
          "<b>Cobertura:</b> enero 1994 – junio 2026 (33 años; 2026 con 6 meses). Un registro por lote, producto y mes.",
          "<b>Productos:</b> petróleo crudo, líquidos de gas natural (LGN) y condensado.",
          "<b>1994–2000</b> provienen de PDF escaneados y fueron <b>transcritos a mano</b> desde la imagen y validados contra los totales del PDF. "
          "<b>2001–2026</b> se extraen automáticamente del PDF digital.",
          "<b>Validación:</b> en los 33 años la suma de los lotes coincide con el total que imprime el PDF (diferencia 0). Además, el promedio "
          "diario calculado coincide con el publicado (p. ej. 1995: 121.762 bpd; 1997: 118.239 bpd).",
      ]),
      P("2. Convenciones", "h1"),
      tabla([
          ["bbl", "unidad", "Barril estadounidense = 42 galones = 158,987 litros. Todas las columnas BARRILES están en barriles."],
          ["BPD / bpd", "unidad", "Barriles por día calendario. Mensual: barriles del mes ÷ días del mes. Anual: barriles del año ÷ 365 (366 en bisiesto)."],
          ["MM bbl", "unidad", "Millones de barriles (usado en resúmenes y en el mapa)."],
          ["Fechas", "texto", "Formato <b>dd/mm/aaaa</b>. En los datos mensuales, FECHA es el día 01 del mes (01/03/2015 = marzo 2015)."],
          ["Codificación", "archivo", "CSV en UTF-8 con BOM (se abre directo en Excel con tildes correctas), separador coma, punto decimal."],
          ["Vacío / NaN", "—", "Sin dato. En el ranking, vacío = el lote aún no existía; 0 = existía y no produjo (o no figura en el PDF ese año)."],
      ], anchos=(3.0, 2.3, 11.7), cab=("Término", "Tipo", "Significado")),
      P("3. Archivos", "h1"),
      tabla([
          ["DATA/PP_produccion_lote_mes_&lt;ini&gt;-&lt;fin&gt;.csv", "Producción", "Base principal: lote × producto × mes (§4)."],
          ["CONTROL/CONTROL PP produccion_lote_mes_&lt;ini&gt;-&lt;fin&gt;.csv", "Control", "Una fila por año: de qué PDF salió y si cuadra con sus totales (§5)."],
          ["CONTROL/PP_CATALOGO_PDF.csv", "Control", "Qué URL de PERUPETRO corresponde a cada PDF guardado (§6)."],
          ["DATA/PDF/PP_ANUAL_&lt;año&gt;.pdf, PP_MENSUAL_&lt;año&gt;_&lt;mes&gt;.pdf", "Fuente", "Copia de los PDF originales de PERUPETRO."],
          ["HIDROCARBUROS/transcripciones/PP_mensual_&lt;año&gt;_transcrito.csv", "Fuente", "Tablas 1994–2000 transcritas desde los escaneos (§7)."],
          ["DATA/PP_LOTES_GEO.csv", "Geografía", "Una fila por lote con departamento, cuenca, distancias, ANP y comunidades (§8)."],
          ["DATA/MAPA/*.geojson, PP_mapa_lotes.html", "Geografía", "Polígonos y capas descargadas; mapa interactivo."],
          ["CONTROL/CONTROL PP mapa capas.csv / mapa descarga.csv", "Control", "Capas encontradas y descargadas para el mapa (§9)."],
      ], anchos=(7.3, 2.2, 7.5), cab=("Archivo", "Rol", "Contenido")),
      ]

# ── 4. Producción ────────────────────────────────────────────────────────────
h += [P("4. Producción por lote y mes", "h1"),
      P("Archivo <font name='DVM'>PP_produccion_lote_mes_&lt;ini&gt;-&lt;fin&gt;.csv</font> (notebook <font name='DVM'>PP_Produccion_Lotes.ipynb</font>). "
        "<b>Unidad de observación:</b> un lote, un producto, un mes. Clave única: AÑO + MES + LOTE + PRODUCTO."),
      tabla([
          ["AÑO", "entero", "Año calendario (1994–2026)."],
          ["MES", "entero 1–12", "Mes calendario (1 = enero)."],
          ["FECHA", "texto dd/mm/aaaa", "Primer día del mes; útil para ordenar y graficar series. Ej.: 01/06/2026."],
          ["ZONA", "texto (código)", "Zona geográfica de PERUPETRO: NOROESTE, ZOCALO (zócalo continental, en el mar), SELVA NORTE, SELVA CENTRAL, "
                                     "SELVA SUR. Se toma del encabezado de la tabla del PDF o, si no lo trae, de una tabla fija por lote."],
          ["DEPARTAMENTO", "texto", "Departamento (región) donde está el lote: el de mayor área según el mapa de lotes "
                                    "(<font name='DVM'>PP_LOTES_GEO.csv</font>). Si el lote no tiene polígono, se usa la zona (SELVA NORTE → LORETO) "
                                    "o queda vacío."],
          ["DEPARTAMENTO_FUENTE", "texto (código)", "MAPA (departamento por polígono del lote), ZONA (asignado por la zona) o vacío."],
          ["OPERADOR", "texto", "Empresa que opera el lote según el PDF de ese año (p. ej. OCCIDENTAL, PLUSPETROL, PETROTAL). Cambia en el tiempo: "
                                "es el operador de ese mes, no el actual."],
          ["LOTE", "texto (código)", "Código homologado del contrato: sin la palabra \"Lote\", con guion estándar. Ej.: 192, 1-AB, 8, 95, Z-2B, "
                                     "31-B/D, X, LOB/EA/LO. Los contratos temporales conservan el sufijo (T), p. ej. I(T)."],
          ["LOTE_HISTORICO", "texto (código)", "Agrupa contratos que son el <b>mismo campo</b> a lo largo del tiempo, para series largas y rankings "
                                               "(ver §10). Ej.: 1-AB y 192 → 1-AB/192. Quita el sufijo (T)."],
          ["LOTE_ORIGINAL", "texto", "Lote tal como aparece escrito en el PDF (p. ej. \"31-C ( LGN )\", \"Z - 2B\"). Sirve para auditar."],
          ["PRODUCTO", "texto (código)", "PETROLEO (crudo), LGN (líquidos de gas natural: propano, butano, gasolina natural; Camisea, Aguaytía) o "
                                         "CONDENSADO. No sumar sin criterio: el petróleo y el LGN son mercados distintos."],
          ["BARRILES", "número (bbl)", "Producción fiscalizada del mes, en barriles."],
          ["BPD", "número (bbl/día)", "BARRILES ÷ días del mes, redondeado a 1 decimal. Permite comparar meses de distinta duración."],
          ["ESTADO_FILA", "texto (código)", "Calidad del registro: OK (leído y cuadra con el total del lote); IMPUTADO &lt;MES&gt; (ese único mes estaba "
                                            "en blanco en el PDF y se calculó como total anual − resto de meses); REVISAR (el lote no cuadra; no se "
                                            "presentó en la corrida completa); TRANSCRITO (1994–2000, desde la imagen)."],
          ["FUENTE", "texto", "Archivo de origen: PP_ANUAL_&lt;año&gt;.pdf, PP_MENSUAL_&lt;año&gt;_&lt;mes&gt;.pdf o \"TRANSCRIPCION PP_ANUAL_&lt;año&gt;.pdf p.N\"."],
      ]),
      Spacer(1, 6),
      P("<b>Cómo se eligió la fuente de cada año.</b> Si existe el anual, se usa el anual (trae los 12 meses ya revisados). Para el año en curso, "
        "se usa la estadística mensual más reciente, que trae el acumulado del año. Por eso 2026 llega hasta junio y cambiará al volver a correr "
        "el notebook cuando PERUPETRO publique meses nuevos."),
      ]

# ── 5. Control de producción ─────────────────────────────────────────────────
h += [P("5. Control de la producción", "h1"),
      P("Archivo <font name='DVM'>CONTROL PP produccion_lote_mes_&lt;ini&gt;-&lt;fin&gt;.csv</font>. Una fila por año (por archivo fuente). "
        "Es la evidencia de que los datos cuadran con el documento oficial."),
      tabla([
          ["ARCHIVO", "texto", "PDF (o PDF y página, en los transcritos) del que salieron los datos del año."],
          ["TIPO", "texto (código)", "ANUAL, MENSUAL (acumulado del año en curso) o TRANSCRITO."],
          ["AÑO", "entero", "Año de los datos."],
          ["MESES", "entero", "Meses cubiertos (12, o menos en el año en curso)."],
          ["LOTES", "entero", "Filas lote-producto leídas en la tabla del PDF."],
          ["FILAS_IMPUTADAS", "entero", "Lotes con un mes completado por diferencia (ver ESTADO_FILA). En la corrida completa: 1 (año 2021)."],
          ["FILAS_REVISAR", "entero", "Lotes cuya suma de meses no coincide con su total. Debe ser 0."],
          ["DIF_MAX_TOTAL", "número (bbl)", "Máxima diferencia mensual entre la suma de los lotes y el TOTAL/SUB-TOTAL impreso en el PDF. "
                                            "<b>0 = cuadra exacto.</b> Es el control principal."],
          ["BARRILES_PETROLEO / _LGN / _CONDENSADO", "número (bbl)", "Total del año por producto (suma de lotes)."],
          ["DIF_MAX_PETROLEO / _LGN / _CONDENSADO", "número (bbl)", "Igual que DIF_MAX_TOTAL pero contra el subtotal de cada producto. "
                                                                   "Vacío cuando el PDF no imprime subtotal por producto (anuales antiguos, 2001–2006)."],
          ["ESTADO", "texto (código)", "OK; OK (transcrito); REVISAR (no cuadra); SIN TABLA; ESCANEADO / FORMATO ANTIGUO (PDF sin tabla legible, "
                                       "cubierto por transcripción); ERROR DE DESCARGA."],
          ["FECHA_EXTRACCION", "texto dd/mm/aaaa", "Día en que se corrió el notebook."],
      ], anchos=(5.0, 2.6, 9.4)),
      P("6. Catálogo de PDF", "h1"),
      tabla([
          ["URL", "texto", "Dirección del PDF en perupetro.com.pe."],
          ["ARCHIVO", "texto", "Nombre con que se guardó en DATA/PDF (PP_ANUAL_&lt;año&gt;.pdf o PP_MENSUAL_&lt;año&gt;_&lt;mes&gt;.pdf). "
                               "Permite no volver a descargar lo ya guardado."],
      ]),
      P("7. Transcripciones 1994–2000", "h1"),
      P("Archivos <font name='DVM'>PP_mensual_&lt;año&gt;_transcrito.csv</font>, en formato ancho (un lote por fila, un mes por columna), "
        "tal como la tabla del PDF. El notebook los convierte al formato de §4."),
      tabla([
          ["ANIO", "entero", "Año."],
          ["PRODUCTO, OPERADOR, LOTE_ORIGINAL, LOTE", "texto", "Igual que en §4. OPERADOR conserva el nombre del PDF de esa época "
                                                               "(p. ej. VEGSA, MPOG, PETROPERU / PLUSPETROL)."],
          ["ENE … DIC", "número (bbl)", "Producción de cada mes."],
          ["TOTAL", "número (bbl)", "Total anual del lote impreso en el PDF (se verifica que sea la suma de los meses)."],
          ["FUENTE", "texto", "PDF y página de la tabla (p. ej. PP_ANUAL_1995.pdf p.18)."],
          ["fila TOTAL", "—", "Última fila: totales del PDF por mes, usados para validar."],
      ], anchos=(5.0, 2.6, 9.4)),
      Spacer(1, 4),
      P("<b>Validación de cada año transcrito:</b> (1) cada lote suma su total; (2) cada mes suma el TOTAL impreso; (3) el gran total coincide "
        "con la tabla \"por contratista\" del mismo PDF. Las celdas que no cuadran se releen con más aumento; en 1995 se usó además un cuadro "
        "de control de la p.17 con las mismas cifras en otra tipografía."),
      ]

# ── 8. Geografía ─────────────────────────────────────────────────────────────
h += [P("8. Variables geográficas por lote", "h1"),
      P("Archivo <font name='DVM'>PP_LOTES_GEO.csv</font> (notebook <font name='DVM'>PP_Mapa_Lotes.ipynb</font>). Una fila por lote. "
        "<b>Estado:</b> notebook listo y probado con datos simulados; pendiente la primera corrida con el mapa real de PERUPETRO."),
      tabla([
          ["FECHA_EXTRACCION", "texto dd/mm/aaaa", "Día de la corrida."],
          ["LOTE", "texto (código)", "Mismo código que en §4, para unir ambas tablas."],
          ["GEOMETRIA_DE", "texto", "Lote(s) del mapa cuyo polígono se usó. Igual a LOTE, salvo equivalencias: lote histórico "
                                    "(1-AB → 192; Z-69 → Z-2B), contrato temporal sin sufijo (I(T) → I) o unión de partes "
                                    "(31-B/D → 31-B+31-D; VII/VI → VII+VI)."],
          ["LOTE_MAPA, OPERADOR_MAPA, ESTADO_MAPA, CAPA", "texto", "Nombre, operador y estado del lote según el mapa, y capa de origen."],
          ["DEPARTAMENTO", "texto", "Departamento con mayor parte del área del lote."],
          ["DEPARTAMENTO_PCT", "% (0–100)", "Porcentaje del área del lote en ese departamento."],
          ["DEPARTAMENTO_DETALLE", "texto", "Reparto completo, p. ej. \"LORETO 67,7%; UCAYALI 32,3%\"."],
          ["DEPARTAMENTO_N", "entero", "Número de departamentos que toca el lote."],
          ["ZOCALO", "SI / NO", "SI para lotes mayormente en el mar (menos del 50 % de su área en tierra); se asignan al departamento "
                               "costero más cercano o al de su parte en tierra."],
          ["CUENCA, CUENCA_PCT", "texto, %", "Cuenca sedimentaria (Marañón, Ucayali, Talara, …) y % del lote en ella."],
          ["AREA_KM2", "número (km²)", "Superficie del lote (proyección equivalente de Sudamérica, ESRI:102033)."],
          ["LAT, LON", "grados decimales", "Punto interior del lote (WGS84)."],
          ["DIST_OLEODUCTO_KM", "número (km)", "Distancia mínima del borde del lote al Oleoducto Norperuano; 0 si lo cruza."],
          ["DIST_IQUITOS_KM", "número (km)", "Distancia mínima del lote a Iquitos."],
          ["DIST_RIO_GRANDE_KM", "número (km)", "Distancia al río más cercano con caudal medio ≥ umbral elegido (300 m³/s por defecto; "
                                                "HydroRIVERS, caudal modelado). Aproxima el acceso fluvial; no es una medida oficial de navegabilidad."],
          ["DIST_RIO_100_KM / _300_KM / _1000_KM", "número (km)", "Misma distancia con umbrales de 100, 300 y 1.000 m³/s (análisis de sensibilidad)."],
          ["RIO_CERCANO", "texto", "Nombre del río grande más cercano (ríos con nombre de OpenStreetMap que coinciden con un tramo "
                                   "de HydroRIVERS ≥ umbral; respaldo Natural Earth)."],
          ["ANP_PCT, ANP_DETALLE", "%, texto", "Porcentaje del lote dentro de Áreas Naturales Protegidas y cuáles."],
          ["CCNN_DENTRO_N, CCNN_5KM_N, CCNN_DENTRO", "entero, texto", "Comunidades nativas dentro del lote, a menos de 5 km, y sus nombres."],
          ["PETROLEO_ACUM_MMBBL", "número (MM bbl)", "Petróleo acumulado del lote en la base de §4."],
          ["PETROLEO_ACUM_CAMPO_MMBBL", "número (MM bbl)", "Acumulado de todos los contratos que comparten el polígono (p. ej. 1-AB + 192)."],
      ], anchos=(5.0, 2.6, 9.4)),
      P("<b>Fuentes del mapa:</b> visor \"Mapa de Lotes de contrato\" de PERUPETRO (ArcGIS Online); límites departamentales geoBoundaries "
        "(basados en INEI); HydroRIVERS y Natural Earth (ríos); SERNANP u OpenStreetMap (ANP); servicios públicos de comunidades nativas; "
        "oleoducto desde PERUPETRO u OpenStreetMap. <b>Primera corrida (11/10/2026):</b> el servidor de PERUPETRO (gismaptemp) no responde; "
        "se usaron los lotes de enero 2019 publicados por INGEMMET, el Oleoducto Norperuano de WWF Perú, ANP y comunidades nativas de "
        "servicios públicos de ArcGIS Online (ver CONTROL PP mapa capas.csv)."),
      P("9. Control del mapa", "h1"),
      tabla([
          ["N, CAPA, GRUPO", "texto", "Número, nombre y grupo de la capa encontrada."],
          ["URL, TIPO, GEOMETRIA", "texto", "Servicio ArcGIS, tipo de capa y geometría (polígono, línea, punto)."],
          ["FUENTE, TEMA", "texto", "PERUPETRO u otro servicio; tema (LOTES, ANP, CCNN, OLEODUCTO)."],
          ["ERROR", "texto", "Motivo si la capa no respondió (p. ej. requiere inicio de sesión)."],
          ["ENTIDADES, ESTADO", "entero, texto", "En el control de descarga: cuántos elementos llegaron y si fue OK; "
                                                  "incluye la fila \"LOTES SIN POLIGONO\" con los lotes con producción sin ubicar."],
      ], anchos=(5.0, 2.6, 9.4)),
      ]

# ── 10. Códigos y equivalencias ──────────────────────────────────────────────
h += [P("10. Lotes históricos y equivalencias", "h1"),
      tabla([
          ["1-AB → 192", "1-AB/192", "Mismo campo (Loreto). El contrato 1-AB terminó el 29/08/2015; desde el 30/08/2015 es el Lote 192."],
          ["Z-2B → Z-69", "Z-2B/Z-69", "Zócalo (Piura/Tumbes). Pasó a PetroPerú como Z-69 (fecha a confirmar con el PDF de 2023)."],
          ["31-B, 31-D → 31-B/D", "31-B/D", "Maple: Maquía (31-B) y Agua Caliente (31-D). El PDF los separa hasta 2000 y los une desde 2001."],
          ["LOB/EA/LO", "LOB/EA/LO", "Lobitos, El Alto y Los Órganos (OXY/Bridas, Noroeste). Desde el 24/07/1996 se integró al Lote X, "
                                     "salvo los yacimientos Folche y Cruz, que pasaron al VI. Se mantiene separado."],
          ["Sufijo (T)", "sin sufijo", "Contrato temporal (p. ej. I(T), VI(T)): mismo lote, se agrupa con el lote base."],
      ], anchos=(3.8, 3.4, 9.8), cab=("Código en los datos", "LOTE_HISTORICO", "Explicación")),
      P("11. Cómo usar los datos (recomendaciones)", "h1"),
      *lista([
          "<b>Totales anuales:</b> sumar BARRILES por AÑO; para comparar años con distinto número de meses usar BPD promedio.",
          "<b>Series de un campo:</b> agrupar por LOTE_HISTORICO, no por LOTE.",
          "<b>Petróleo vs. LGN:</b> filtrar PRODUCTO; el LGN (Camisea desde 2004) supera al petróleo desde 2009 y distorsiona los totales de \"líquidos\".",
          "<b>Loreto:</b> filtrar DEPARTAMENTO = \"LORETO\" (incluye 31-B Maquía y 31-E, que el PDF ubica en Selva Central).",
          "<b>Año en curso:</b> es parcial; no comparar su total con años completos.",
          "<b>Operador:</b> es el del momento; para análisis por empresa usar OPERADOR del mes, no el actual.",
          "<b>Calidad:</b> antes de publicar, revisar que el CONTROL tenga ESTADO OK / OK (transcrito) en todos los años usados.",
      ]),
      P("12. Limitaciones conocidas", "h1"),
      *lista([
          "Los polígonos de lotes son de enero 2019 (INGEMMET): los lotes firmados después no tienen polígono y su DEPARTAMENTO sale de la zona.",
          "La fecha exacta del paso Z-2B → Z-69 está por confirmar.",
          "1994–2000 provienen de escaneos: transcritos y validados al barril, pero sin capa digital original.",
          "Si PERUPETRO cambia el formato de sus PDF o de su página, el CONTROL lo mostrará como SIN TABLA o REVISAR (no como datos erróneos).",
      ])]

os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Diccionario_datos_Proyecto_Petroleo.pdf")
doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                        title="Diccionario de datos · Proyecto Petróleo", author="Proyecto Petróleo (scraper-mef)")
doc.build(h, onFirstPage=pie, onLaterPages=pie)
print("ok", out)
