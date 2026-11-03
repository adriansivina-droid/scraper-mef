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
# departamento por el nombre del archivo: «SERIES LORETO (OFICIAL).xlsx», «SERIES_SMN.xlsx», «SERIES UCAYALI.xlsx»
_RE_SERIES = re.compile(r"^SERIES[\s_\-]+(LORETO|LOR|SAN[\s_]*MART[IÍ]N|SMN|UCAYALI|UCA)\b", re.I)
DEPTO = {"LOR": "16", "LORETO": "16", "SMN": "22", "SANMARTIN": "22", "SANMARTÍN": "22", "UCA": "25", "UCAYALI": "25"}


def depto_de(nombre):
    """'16' / '22' / '25' si el nombre es el de unas SERIES, si no None."""
    m = _RE_SERIES.match(posixpath.basename(nombre).strip())
    return DEPTO.get(re.sub(r"[\s_]", "", m.group(1)).upper()) if m else None


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
            series.append({"nombre": nombre_s, "tipo": tipo, "valores": v, "eje": 2 if secundario else 1,
                           "etiquetas": dl is not None and dl.get("val") == "1", "formato": _formato(ser.find("c:val", NS)),
                           "color_original": _color_serie(ser)})
    series = [s for s in series if any(x is not None for x in s["valores"])]
    if not series:
        return None
    n = max(len(s["valores"]) for s in series)
    cat = (cat + [""] * n)[:n]
    if len({s["tipo"] for s in series}) > 1:
        tipo_base = "combinado"
    return {"tipo": tipo_base, "apilado": apilado, "horizontal": horizontal, "categorias": cat, "series": series}


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
            ch = anc.find(".//c:chart", NS)
            texto = " ".join((x.text or "") for x in anc.iter("{%s}t" % NS["a"])).strip() if ch is None else ""
            anclas.append({"pos": pos, "chart": rel_dib.get(ch.get("{%s}id" % NS["r"])) if ch is not None else None, "texto": texto})
        celdas = None
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
            graficos.append({"hoja": hoja.get("name").strip(), "orden_hoja": nh, "titulo": titulo, "subtitulo": subtitulo,
                             "notas": notas[:4], **g})
    for i, g in enumerate(graficos):
        g["orden"] = i + 1
    return graficos


# ── base de datos ──
def _tabla():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS drae_graficos (depto TEXT, orden INTEGER, hoja TEXT, spec TEXT, archivo TEXT, fecha TEXT)"))


def guardar(depto, archivo, graficos):
    """Reemplaza los gráficos DRAE del departamento por los de este libro."""
    _tabla()
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.motor().begin() as cx:
        cx.execute(text("DELETE FROM drae_graficos WHERE depto = :d"), {"d": depto})
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
        return {"archivo": None, "fecha": None, "graficos": []}
    return {"archivo": filas[0][1], "fecha": filas[0][2], "graficos": [json.loads(f[0]) for f in filas]}


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
