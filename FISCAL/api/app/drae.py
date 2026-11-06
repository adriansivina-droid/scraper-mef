"""Gráficos DRAE: los gráficos de las SERIES de cada departamento (SERIES LORETO / SMN / UCAYALI .xlsx), leídos del libro
tal como están (los valores que guarda cada gráfico, su tipo y sus series) y guardados en la base para dibujarlos en la
página con la paleta del Seminario de Periodistas.

Cada gráfico de Excel guarda en su XML una copia de sus datos (c:strCache / c:numCache): no hace falta recalcular el
libro ni abrir sus vínculos. El título y la fuente no están en el gráfico sino en las celdas de arriba y de abajo: se
toman de ahí.
"""
import io
import json
import posixpath
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from sqlalchemy import text

from . import db

NS = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
      "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
TIPOS = {"barChart": "barras", "bar3DChart": "barras", "lineChart": "lineas", "line3DChart": "lineas", "areaChart": "area",
         "pieChart": "circular", "pie3DChart": "circular", "doughnutChart": "anillo", "scatterChart": "dispersion", "radarChart": "radar"}
# departamento y fuente por el nombre del archivo: las SERIES («SERIES LORETO (OFICIAL).xlsx», «SERIES_SMN.xlsx») o el
# libro de gráficos del DRAE («DRAE_SMT_Nov-26.xlsx», «DRAE_Ucayali-Set26_Parte5.xlsx»)
_RE_SERIES = re.compile(r"^(SERIES|DRAE)[\s_\-]+(LORETO|LOR|SAN[\s_]*MART[IÍ]N|SMN|SMT|UCAYALI|UCA)(?![A-Za-z])", re.I)
DEPTO = {"LOR": "16", "LORETO": "16", "SMN": "22", "SMT": "22", "SANMARTIN": "22", "SANMARTÍN": "22", "UCA": "25", "UCAYALI": "25"}
NOMBRE = {"16": "Loreto", "22": "San Martín", "25": "Ucayali"}
BASE_DRAE = 1000            # los gráficos del libro del DRAE van con orden 1001, 1002… (los de las SERIES, 1, 2…)


def depto_de(nombre):
    """'16' / '22' / '25' si el nombre es el de unas SERIES o un libro del DRAE, si no None."""
    m = _RE_SERIES.match(posixpath.basename(nombre).strip())
    return DEPTO.get(re.sub(r"[\s_]", "", m.group(2)).upper()) if m else None


def fuente_de(nombre):
    """'SERIES' o 'DRAE' según el nombre del archivo."""
    m = _RE_SERIES.match(posixpath.basename(nombre).strip())
    return m.group(1).upper() if m else None


def _xml(z, ruta):
    try:
        return ET.fromstring(z.read(ruta))
    except KeyError:
        return None


def _rels(z, ruta):
    """{Id: ruta absoluta dentro del zip} de las relaciones de `ruta`."""
    base, nombre = posixpath.split(ruta)
    r = _xml(z, posixpath.join(base, "_rels", nombre + ".rels"))
    if r is None:
        return {}
    return {x.get("Id"): posixpath.normpath(posixpath.join(base, x.get("Target"))) for x in r.findall("pr:Relationship", NS)}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cache(nodo):
    """Valores de un c:cat / c:val / c:tx (strCache, numCache o multiLvlStrCache) -> lista."""
    if nodo is None:
        return []
    multi = nodo.find(".//c:multiLvlStrCache", NS)
    if multi is not None:                                   # categorías en dos niveles (mes y año): se juntan
        n = int(multi.find("c:ptCount", NS).get("val", 0))
        niveles = []
        for lvl in multi.findall("c:lvl", NS):
            v = [""] * n
            for p in lvl.findall("c:pt", NS):
                v[int(p.get("idx"))] = p.findtext("c:v", "", NS)
            niveles.append(v)
        salida, ultimo = [], [""] * len(niveles)
        for i in range(n):
            partes = [niv[i] for niv in niveles]
            salida.append(" ".join(x for x in partes if x).strip())
        return salida
    c = nodo.find(".//c:numCache", NS)
    numerico = c is not None
    if c is None:
        c = nodo.find(".//c:strCache", NS)
    if c is None:
        v = nodo.findtext(".//c:v", None, NS)
        return [v] if v is not None else []
    n = int((c.find("c:ptCount", NS).get("val") if c.find("c:ptCount", NS) is not None else 0) or 0)
    v = [None] * n
    for p in c.findall("c:pt", NS):
        i = int(p.get("idx"))
        if i >= n:
            v += [None] * (i + 1 - n); n = i + 1
        x = p.findtext("c:v", None, NS)
        v[i] = _num(x) if numerico else x
    return v


def _formato(nodo):
    f = nodo.find(".//c:numCache/c:formatCode", NS) if nodo is not None else None
    return f.text if f is not None else None


def _color_serie(ser):
    c = ser.find("c:spPr//a:solidFill/a:srgbClr", NS)
    return ("#" + c.get("val")) if c is not None else None


def leer_grafico(xml):
    """XML de un gráfico -> {tipo, apilado, horizontal, series: [{nombre, tipo, valores, eje, etiquetas}], categorias} o None."""
    plot = xml.find(".//c:plotArea", NS)
    if plot is None:
        return None
    ejes_sec = set()
    valax = plot.findall("c:valAx", NS)
    if len(valax) > 1:                                      # el segundo eje de valores es el secundario
        ejes_sec = {valax[1].find("c:axId", NS).get("val")}
    series, cat, tipo_base, apilado, horizontal = [], [], None, None, False
    for hijo in plot:
        nombre = hijo.tag.split("}")[1]
        if nombre not in TIPOS:
            continue
        tipo = TIPOS[nombre]
        g = hijo.find("c:grouping", NS)
        agrup = g.get("val") if g is not None else None
        if tipo == "barras" and hijo.find("c:barDir", NS) is not None and hijo.find("c:barDir", NS).get("val") == "bar":
            horizontal = True
        ids = {x.get("val") for x in hijo.findall("c:axId", NS)}
        secundario = bool(ids & ejes_sec)
        if tipo_base is None or tipo in ("barras", "circular", "anillo"):
            tipo_base = tipo_base if tipo_base in ("barras",) else tipo
            if agrup in ("stacked", "percentStacked"):
                apilado = agrup
        for ser in hijo.findall("c:ser", NS):
            nombre_s = " ".join(str(x) for x in _cache(ser.find("c:tx", NS)) if x is not None).strip()
            if tipo == "dispersion":
                c, v = _cache(ser.find("c:xVal", NS)), _cache(ser.find("c:yVal", NS))
            else:
                c, v = _cache(ser.find("c:cat", NS)), _cache(ser.find("c:val", NS))
            if len(c) > len(cat):
                cat = [str(x) if x is not None else "" for x in c]
            dl = ser.find("c:dLbls/c:showVal", NS)
            mk = ser.find("c:marker", NS)
            ln = ser.find("c:spPr/a:ln", NS)
            series.append({"nombre": nombre_s, "tipo": tipo, "valores": v, "eje": 2 if secundario else 1,
                           "etiquetas": dl is not None and dl.get("val") == "1", "formato": _formato(ser.find("c:val", NS)),
                           "color_original": _color_serie(ser),
                           "marcador": (None if mk is None or mk.find("c:symbol", NS) is None else
                                        {"simbolo": mk.find("c:symbol", NS).get("val"), "tam": _int(mk.find("c:size", NS))}),
                           "grosor": round(int(ln.get("w")) / 12700, 2) if ln is not None and ln.get("w") else None,
                           "etq": _fuente(ser.find("c:dLbls", NS))})
    series = [s for s in series if any(x is not None for x in s["valores"])]
    if not series:
        return None
    n = max(len(s["valores"]) for s in series)
    cat = (cat + [""] * n)[:n]
    if len({s["tipo"] for s in series}) > 1:
        tipo_base = "combinado"
    # estilo del gráfico en Excel (para dibujarlo igual): leyenda, separación de barras y tamaños de letra
    ley = xml.find(".//c:chart/c:legend", NS)
    bar = plot.find("c:barChart", NS)
    estilo = {"leyenda": (None if ley is None else (ley.find("c:legendPos", NS).get("val") if ley.find("c:legendPos", NS) is not None else "r")),
              "leyenda_borde": ley is not None and ley.find("c:spPr/a:ln/a:solidFill", NS) is not None,
              "leyenda_fuente": _fuente(ley), "base": _fuente(xml.find("c:txPr", NS)),
              "eje": _fuente(plot.find("c:catAx", NS)) or _fuente(plot.find("c:dateAx", NS)),
              "gap": _int(bar.find("c:gapWidth", NS)) if bar is not None else None,
              "overlap": _int(bar.find("c:overlap", NS)) if bar is not None else None}
    return {"tipo": tipo_base, "apilado": apilado, "horizontal": horizontal, "categorias": cat, "series": series, "estilo": estilo}


def _int(nodo):
    try:
        return int(nodo.get("val"))
    except (AttributeError, TypeError, ValueError):
        return None


def _fuente(nodo):
    """{tam (pt), negrita} del primer a:defRPr con tamaño de un nodo (txPr de etiquetas, leyenda, ejes) o None."""
    if nodo is None:
        return None
    for r in nodo.iter("{%s}defRPr" % NS["a"]):
        if r.get("sz"):
            return {"tam": int(r.get("sz")) / 100, "negrita": r.get("b") == "1"}
    return None


def _celdas(z, ruta_hoja, compartidas):
    """{(fila, col) 0-based: texto} de las celdas con texto (o número) de una hoja."""
    raiz = _xml(z, ruta_hoja)
    salida = {}
    if raiz is None:
        return salida
    for c in raiz.iter("{%s}c" % NS["m"]):
        ref, t = c.get("r"), c.get("t")
        m = re.match(r"([A-Z]+)(\d+)", ref or "")
        if not m:
            continue
        col = 0
        for ch in m.group(1):
            col = col * 26 + ord(ch) - 64
        if t == "s":
            v = c.findtext("m:v", None, NS)
            val = compartidas[int(v)] if v is not None and v.isdigit() and int(v) < len(compartidas) else None
        elif t == "inlineStr":
            val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
        elif t == "str":
            val = c.findtext("m:v", None, NS)
        else:
            continue                                      # números: no son títulos
        if val and val.strip():
            salida[(int(m.group(2)) - 1, col - 1)] = val.strip()
    return salida


EMU_PX = 9525


def _medidas(hoja):
    """Función ancla -> (ancho, alto) del gráfico en píxeles a 100 % de zoom, con los anchos de columna y altos de fila
    de la hoja (columnas: caracteres × 7 + 5 px; filas: puntos × 4/3)."""
    fmt = hoja.find("m:sheetFormatPr", NS)
    ancho_def = float(fmt.get("defaultColWidth") or (float(fmt.get("baseColWidth") or 8) + 0.71)) if fmt is not None else 8.71
    alto_def = float(fmt.get("defaultRowHeight") or 15) if fmt is not None else 15.0
    cols = {}
    for c in hoja.iter("{%s}col" % NS["m"]):
        for i in range(int(c.get("min")), min(int(c.get("max")), 400) + 1):
            cols[i - 1] = float(c.get("width") or ancho_def)
    filas = {int(r.get("r")) - 1: float(r.get("ht")) for r in hoja.iter("{%s}row" % NS["m"]) if r.get("ht") and r.get("r")}
    px_col = lambda i: round(cols.get(i, ancho_def) * 7 + 5)
    px_fila = lambda i: filas.get(i, alto_def) * 4 / 3

    def medir(a):
        if a.get("ext"):
            return round(a["ext"][0] / EMU_PX), round(a["ext"][1] / EMU_PX)
        r0, c0, r1, c1 = a["pos"]
        o = a["off"]
        ancho = sum(px_col(i) for i in range(c0, c1)) - o[0] / EMU_PX + o[2] / EMU_PX
        alto = sum(px_fila(i) for i in range(r0, r1)) - o[1] / EMU_PX + o[3] / EMU_PX
        return round(ancho), round(alto)
    return medir


def _textos_cajas(anclas):
    return [a for a in anclas if a["texto"]]


def _col(letras):
    n = 0
    for ch in letras:
        n = n * 26 + ord(ch) - 64
    return n - 1


_NO_TITULO = re.compile(r"^\(?\s*(fuente|nota|elaboraci|a\s+\w+\s+(de\s+)?\d{4}|dato|\d+/)", re.I)


def _partir(t):
    """«EVOLUCIÓN DE …, 2016 - 2025 (Var. real)» -> («Evolución de …, 2016 - 2025», «(Var. real)»)."""
    t = re.sub(r"\s+", " ", t).strip()
    m = re.match(r"^(.*?)\s*(\([^()]*\))\s*$", t)
    tit, sub = (m.group(1), m.group(2)) if m and len(m.group(1)) > 8 else (t, "")
    if tit.isupper():
        tit = tit[:1] + tit[1:].lower()
        tit = re.sub(r"\b(perú|loreto|ucayali|san martín|san martin|pbi|wti|pim|pea|incore|igpc|sbs|mef|inei|fob|ssff)\b",
                     lambda m: {"perú": "Perú", "loreto": "Loreto", "ucayali": "Ucayali", "san martín": "San Martín", "san martin": "San Martín"}.get(m.group(1), m.group(1).upper()), tit)
    return tit, sub


def _titulo(celdas, anclas, pos, refs, propios=frozenset()):
    """El título de un gráfico: el texto largo más cercano por encima (celdas o cuadros de texto), cerca de sus columnas
    o encima del rango de sus datos; si no hay, el primero de la parte de arriba de la hoja."""
    r0, c0, r1, c1 = pos
    largo = lambda t: (len(t) >= 14 and " " in t.strip() and not _NO_TITULO.match(t) and t.strip().lower() not in propios
                       and not re.match(r"^(\(en |gr[aá]fico|loreto gr|\(como)", t.strip(), re.I))
    cand = []
    for (r, c), t in celdas.items():
        if not largo(t):
            continue
        if r <= r0 + 1 and c0 - 3 <= c <= c1 + 1 and r >= r0 - 12:
            cand.append((0, r0 - r, t))
    for b in _textos_cajas(anclas):
        br, bc = b["pos"][0], b["pos"][1]
        if largo(b["texto"]) and r0 - 6 <= br <= r0 + 2 and c0 - 2 <= bc <= c1:
            cand.append((0, abs(r0 - br) - 0.5, b["texto"]))
    for letras, fila in refs[:2]:                         # encima del rango de los datos
        rr, cc = int(fila) - 1, _col(letras)
        for (r, c), t in celdas.items():
            if largo(t) and rr - 15 <= r < rr and cc - 3 <= c <= cc + 6:
                cand.append((1, rr - r, t))
    if not cand:
        cand = [(2, r, t) for (r, c), t in celdas.items() if r <= 3 and largo(t)]
    if not cand:
        return "", ""
    return _partir(sorted(cand)[0][2])


def leer_series(contenido):
    """Bytes de un libro SERIES -> lista de gráficos en orden de hoja y posición:
    [{hoja, orden, titulo, subtitulo, notas, tipo, apilado, horizontal, categorias, series}]."""
    z = zipfile.ZipFile(io.BytesIO(contenido))
    wb = _xml(z, "xl/workbook.xml")
    rel_wb = _rels(z, "xl/workbook.xml")
    ss = _xml(z, "xl/sharedStrings.xml")
    compartidas = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])) for si in ss.findall("m:si", NS)] if ss is not None else []
    graficos = []
    for nh, hoja in enumerate(wb.find("m:sheets", NS)):
        if hoja.get("state") in ("hidden", "veryHidden"):
            continue
        ruta = rel_wb.get(hoja.get("{%s}id" % NS["r"]))
        if not ruta:
            continue
        raiz = _xml(z, ruta)
        dib = raiz.find("m:drawing", NS) if raiz is not None else None
        if dib is None:
            continue
        ruta_dib = _rels(z, ruta).get(dib.get("{%s}id" % NS["r"]))
        d = _xml(z, ruta_dib) if ruta_dib else None
        if d is None:
            continue
        rel_dib = _rels(z, ruta_dib)
        anclas = []
        for anc in list(d):
            f, t = anc.find("xdr:from", NS), anc.find("xdr:to", NS)
            if f is None:
                continue
            pos = (int(f.findtext("xdr:row", "0", NS)), int(f.findtext("xdr:col", "0", NS)),
                   int(t.findtext("xdr:row", "0", NS)) if t is not None else int(f.findtext("xdr:row", "0", NS)) + 20,
                   int(t.findtext("xdr:col", "0", NS)) if t is not None else int(f.findtext("xdr:col", "0", NS)) + 8)
            off = (int(f.findtext("xdr:colOff", "0", NS)), int(f.findtext("xdr:rowOff", "0", NS)),
                   int(t.findtext("xdr:colOff", "0", NS)) if t is not None else 0, int(t.findtext("xdr:rowOff", "0", NS)) if t is not None else 0)
            ext = anc.find("xdr:ext", NS)
            ch = anc.find(".//c:chart", NS)
            texto = " ".join((x.text or "") for x in anc.iter("{%s}t" % NS["a"])).strip() if ch is None else ""
            anclas.append({"pos": pos, "off": off, "ext": (int(ext.get("cx")), int(ext.get("cy"))) if ext is not None else None,
                           "chart": rel_dib.get(ch.get("{%s}id" % NS["r"])) if ch is not None else None, "texto": texto})
        celdas = None
        medida = _medidas(raiz)
        for a in sorted((x for x in anclas if x["chart"]), key=lambda x: (x["pos"][0], x["pos"][1])):
            x = _xml(z, a["chart"])
            g = leer_grafico(x) if x is not None else None
            if g is None:
                continue
            if celdas is None:
                celdas = _celdas(z, ruta, compartidas)
            r0, c0, r1, c1 = a["pos"]
            refs = re.findall(r"!\$?([A-Z]+)\$?(\d+)", ET.tostring(x, encoding="unicode"))
            serie_titulo = next((x["nombre"] for x in g["series"] if len(x["nombre"]) >= 25 and ":" in x["nombre"]), None)
            propios = frozenset(str(v).strip().lower() for v in g["categorias"] + [x["nombre"] for x in g["series"]] if v)
            titulo, subtitulo = _partir(serie_titulo) if serie_titulo else _titulo(celdas, anclas, (r0, c0, r1, c1), refs, propios)
            if serie_titulo and len(g["series"]) == 1:
                g["series"][0]["nombre"] = ""
            debajo = [celdas[k] for k in sorted(k for k in celdas if r1 - 2 <= k[0] <= r1 + 5 and c0 - 2 <= k[1] <= c1 + 2)]
            notas = [s for s in debajo if re.match(r"^\s*(\*|\d/|fuente|nota|elaboraci|\(\*\))", s, re.I)]
            ancho, alto = medida(a)
            graficos.append({"hoja": hoja.get("name").strip(), "orden_hoja": nh, "titulo": titulo, "subtitulo": subtitulo,
                             "notas": notas[:4], "ancho_px": ancho, "alto_px": alto, **g})
    for i, g in enumerate(graficos):
        g["orden"] = i + 1
    return graficos


# ── base de datos ──
# ── Gráficos innecesarios: duplicados, contenidos en otro o de un mes ya reemplazado ──
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
_RE_MES = re.compile(r"\b(" + "|".join(_MESES) + r"|septiembre)\b")


def _sin_tilde(t):
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()


def _titulo_base(g):
    """El título sin meses, años ni «periodo»: dos gráficos con el mismo título base son el mismo gráfico de otra fecha."""
    t = _RE_MES.sub("", _sin_tilde(g.get("titulo")))
    t = re.sub(r"\b(periodo|perido)\b|\b(19|20)\d\d\b", "", t)
    return re.sub(r"[^a-z]+", " ", t).strip()


def _fecha_titulo(g):
    """(año, último mes, varios_meses) del título; el año sale de la hoja si el título no lo trae (p. ej. «XS LOR AGOS-2026»)."""
    t = _sin_tilde(g.get("titulo")).replace("septiembre", "setiembre")
    meses = [_MESES.index(m) + 1 for m in _RE_MES.findall(t)]
    if not meses:
        return None
    anios = re.findall(r"\b((?:19|20)\d\d)\b", t) or re.findall(r"((?:19|20)\d\d)", str(g.get("hoja") or ""))
    return (int(anios[-1]) if anios else None, meses[-1], len(meses) > 1)


def _firma(g):
    return json.dumps([[str(c) for c in g["categorias"]], [[None if v is None else round(v, 6) for v in x["valores"]] for x in g["series"]]])


def _contenido(a, b):
    """True si todo lo de «a» (cada serie en cada categoría) está en «b» con el mismo valor y «b» trae más categorías."""
    if len(a["categorias"]) >= len(b["categorias"]) or a.get("tipo") == "anillo" or a.get("tipo") == "circular":
        return False
    pos = {str(c): i for i, c in enumerate(b["categorias"])}
    series_b = {x["nombre"]: x["valores"] for x in b["series"]}
    if not a["series"] or any(str(c) not in pos for c in a["categorias"]):
        return False
    for x in a["series"]:
        if x["nombre"] not in series_b:
            return False
        for c, v in zip(a["categorias"], x["valores"]):
            w = series_b[x["nombre"]][pos[str(c)]] if pos[str(c)] < len(series_b[x["nombre"]]) else None
            if (v is None) != (w is None) or (v is not None and abs(v - w) > 1e-6):
                return False
    return True


def innecesarios(graficos):
    """{orden: motivo} de los gráficos que sobran:
      1. duplicado exacto de otro (mismas categorías y cifras): queda el primero;
      2. contenido en otro más completo (las mismas cifras con menos años, p. ej. «PBI» 2017-2026 dentro de «PBI (NUEVO)»
         2015-2026);
      3. la versión de un mes anterior del mismo gráfico y año (p. ej. «…, enero 2026» cuando ya está «…, enero-agosto
         2026»); si la mayoría de los gráficos de una hoja quedan así, sale la hoja entera (la hoja del mes anterior).
    Las comparaciones con el año anterior (agosto 2025 frente a agosto 2026) no se tocan."""
    fuera, vistos = {}, {}
    for g in graficos:
        f = _firma(g)
        if f in vistos:
            fuera[g["orden"]] = f"duplicado de N° {vistos[f]}"
        else:
            vistos[f] = g["orden"]
    for a in graficos:
        if a["orden"] in fuera:
            continue
        b = next((b for b in graficos if b is not a and b["orden"] not in fuera and _contenido(a, b)), None)
        if b:
            fuera[a["orden"]] = f"contenido en N° {b['orden']} ({b['hoja']}), que trae más años"
    por_titulo = {}
    for g in graficos:
        if g["orden"] not in fuera and _fecha_titulo(g) and _titulo_base(g):
            por_titulo.setdefault(_titulo_base(g), []).append(g)
    viejos = {}
    for gs in por_titulo.values():
        for a in gs:
            ya, ma, _ = _fecha_titulo(a)
            b = next((b for b in gs if b is not a and _fecha_titulo(b)[0] == ya and ya and _fecha_titulo(b)[1] > ma), None)
            if b:
                viejos[a["orden"]] = f"versión de un mes anterior (ya está N° {b['orden']}: «{b.get('titulo')}»)"
    fuera.update(viejos)
    hojas = {}
    for g in graficos:
        hojas.setdefault(g["hoja"], []).append(g)
    for hoja, gs in hojas.items():
        if len(gs) >= 2 and sum(g["orden"] in viejos for g in gs) * 2 >= len(gs):
            for g in gs:
                fuera.setdefault(g["orden"], f"hoja «{hoja}» de un mes anterior (sus gráficos ya están con fecha más reciente)")
    return fuera


def _clave(g):
    """Identifica un gráfico entre cargas de las SERIES (para recordar los que se ocultan a mano)."""
    return f"{g.get('fuente') or 'SERIES'}|{_sin_tilde(g['hoja'])}|{_sin_tilde(g.get('titulo'))}|{_sin_tilde(g.get('subtitulo'))}"


def _tabla():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS drae_graficos (depto TEXT, orden INTEGER, hoja TEXT, spec TEXT, archivo TEXT, fecha TEXT)"))
        cx.execute(text("CREATE TABLE IF NOT EXISTS drae_ocultos (depto TEXT, clave TEXT, PRIMARY KEY (depto, clave))"))


def guardar(depto, archivo, graficos):
    """Reemplaza los gráficos del departamento que vienen de esa fuente (SERIES o libro del DRAE) por los de este libro.
    Del libro del DRAE se dejan fuera los gráficos auxiliares (una sola categoría), las copias rotas (una serie con
    #¡REF!) y las series auxiliares («Aux2018»)."""
    _tabla()
    fuente = fuente_de(archivo) or "SERIES"
    if fuente == "DRAE":
        roto = lambda g: any("#" in x["nombre"] and "REF" in x["nombre"].upper() for x in g["series"])
        graficos = [g for g in graficos if len([c for c in g["categorias"] if str(c).strip()]) >= 2 and not roto(g)]
        for i, g in enumerate(graficos):
            g["orden"] = BASE_DRAE + i + 1
            g["series"] = [x for x in g["series"] if not re.match(r"^aux", x["nombre"].strip(), re.I)] or g["series"]
    for g in graficos:
        g["fuente"] = fuente
    sobran = innecesarios(graficos)
    graficos = [g for g in graficos if g["orden"] not in sobran]
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rango = "orden > :b" if fuente == "DRAE" else "orden <= :b"
    with db.motor().begin() as cx:
        cx.execute(text(f"DELETE FROM drae_graficos WHERE depto = :d AND {rango}"), {"d": depto, "b": BASE_DRAE})
        for g in graficos:
            cx.execute(text("INSERT INTO drae_graficos (depto, orden, hoja, spec, archivo, fecha) VALUES (:d, :o, :h, :s, :a, :f)"),
                       {"d": depto, "o": g["orden"], "h": g["hoja"], "s": json.dumps(g, ensure_ascii=False), "a": archivo, "f": ahora})
    return len(graficos)


def leer(depto):
    """{archivo, fecha, graficos} del departamento (graficos vacío si nunca se cargaron sus SERIES)."""
    _tabla()
    with db.motor().connect() as cx:
        filas = cx.execute(text("SELECT spec, archivo, fecha FROM drae_graficos WHERE depto = :d ORDER BY orden"), {"d": depto}).all()
    if not filas:
        return {"archivo": None, "fecha": None, "graficos": [], "archivos": []}
    archivos = {}
    for f in filas:
        archivos.setdefault(f[1], f[2])
    with db.motor().connect() as cx:
        ocultos = {r[0] for r in cx.execute(text("SELECT clave FROM drae_ocultos WHERE depto = :d"), {"d": depto}).all()}
    graficos = [json.loads(f[0]) for f in filas]
    for g in graficos:
        g["oculto"] = _clave(g) in ocultos
    return {"archivo": filas[0][1], "fecha": filas[0][2], "graficos": graficos,
            "archivos": [{"archivo": a, "fecha": fe} for a, fe in archivos.items()]}


def cambiar_titulo(depto, orden, titulo, subtitulo):
    """Corrige a mano el título de un gráfico (se pierde si se vuelven a cargar las SERIES)."""
    _tabla()
    with db.motor().begin() as cx:
        fila = cx.execute(text("SELECT spec FROM drae_graficos WHERE depto = :d AND orden = :o"), {"d": depto, "o": orden}).first()
        if fila is None:
            return False
        g = json.loads(fila[0])
        g["titulo"], g["subtitulo"] = titulo.strip(), subtitulo.strip()
        cx.execute(text("UPDATE drae_graficos SET spec = :s WHERE depto = :d AND orden = :o"),
                   {"s": json.dumps(g, ensure_ascii=False), "d": depto, "o": orden})
    return True


def ocultar(depto, orden, oculto=True):
    """Oculta (o vuelve a mostrar) un gráfico; se recuerda aunque se vuelvan a cargar las SERIES."""
    _tabla()
    with db.motor().begin() as cx:
        fila = cx.execute(text("SELECT spec FROM drae_graficos WHERE depto = :d AND orden = :o"), {"d": depto, "o": orden}).first()
        if fila is None:
            return False
        clave = _clave(json.loads(fila[0]))
        cx.execute(text("DELETE FROM drae_ocultos WHERE depto = :d AND clave = :c"), {"d": depto, "c": clave})
        if oculto:
            cx.execute(text("INSERT INTO drae_ocultos (depto, clave) VALUES (:d, :c)"), {"d": depto, "c": clave})
    return True


def depurar(depto, aplicar=False):
    """Quita de la base los gráficos innecesarios ya guardados (cada fuente por separado). -> [{orden, hoja, titulo, motivo}]"""
    graficos = leer(depto)["graficos"]
    salida = []
    for fuente in ("SERIES", "DRAE"):
        gs = [g for g in graficos if (g.get("fuente") or "SERIES") == fuente]
        for orden, motivo in innecesarios(gs).items():
            g = next(x for x in gs if x["orden"] == orden)
            salida.append({"orden": orden, "hoja": g["hoja"], "titulo": g.get("titulo"), "motivo": motivo})
    if aplicar and salida:
        with db.motor().begin() as cx:
            for x in salida:
                cx.execute(text("DELETE FROM drae_graficos WHERE depto = :d AND orden = :o"), {"d": depto, "o": x["orden"]})
    return sorted(salida, key=lambda x: x["orden"])
