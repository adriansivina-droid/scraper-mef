"""ESTAD de Ejecución del presupuesto: las hojas de gasto e inversión de los libros ESTAD (ESTADLO, ESTADSMN, ESTADUCA)
armadas con los datos del MEF que ya tiene la página.

Hojas (una por nivel de gobierno): «GASTO(S) G.N./G.R./G.L.» (gasto por genérica, servicio de la deuda y por fuente) e
«INVERSIÓN G.N./G.R./G.L.» (inversión por función y, si la hoja la trae, por fuente). Las de INGRESOS no: la página no
descarga los ingresos.

Cada región ordena y nombra las filas a su manera, así que cada fila se reconoce por su etiqueta (`concepto`) y se llena
con la base que corresponde:
  · genéricas y deuda ........ gasto-dev-generica (5-21 … 5-25, 6-24 … 6-27, 7-28 con amortización e intereses)
  · gasto por fuente ......... gasto-dev-fuente (todas las genéricas)
  · inversión por función .... inv-dev-funcion (genérica 2.6)
  · inversión por fuente ..... inv-dev-fuente (genérica 2.6)
Montos en miles de soles, redondeados a la unidad, como en el ESTAD. Las filas que la página no puede separar (Fondo de
Compensación Regional y Privatizaciones y concesiones, que son rubros dentro de Recursos determinados) quedan vacías, y
una fila repetida (Loreto: «Transporte y Comunicaciones» dos veces) se llena solo la primera vez, como en el ESTAD.

El orden de filas sale del último libro ESTAD subido a la página (se guarda con `cargar_libro`, junto con los valores de
sus últimos 25 meses para compararlos); si no se subió, del que viene con la página (estad_fiscal_filas.json, solo
etiquetas). Contra el ESTAD cargado (2025 a julio 2026) coincide el 97 % de las celdas a ±1 mil soles; el resto son
revisiones posteriores del MEF.
"""
import base64
import io
import json
import re
import unicodedata
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from . import db

DEPTOS = {"16": "LORETO", "22": "SAN MARTÍN", "25": "UCAYALI"}
CORTO = {"16": "LOR", "22": "SMN", "25": "UCA"}
NIVEL = {"E": "Gobierno Nacional", "R": "Gobierno Regional", "M": "Gobiernos Locales"}
FUNCIONES = [("LEGISLATIVA", "01"), ("RELACIONES EXTERIORES", "02"), ("PLANEAMIENTO", "03"), ("DEFENSA", "04"),
             ("ORDEN PUBLICO", "05"), ("JUSTICIA", "06"), ("TRABAJO", "07"), ("COMERCIO", "08"), ("TURISMO", "09"),
             ("AGROPECUARIA", "10"), ("PESCA", "11"), ("ENERGIA", "12"), ("MINERIA", "13"), ("INDUSTRIA", "14"),
             ("TRANSPORTE", "15"), ("COMUNICACIONES", "16"), ("AMBIENTE", "17"), ("SANEAMIENTO", "18"), ("VIVIENDA", "19"),
             ("SALUD", "20"), ("CULTURA", "21"), ("EDUCACION", "22"), ("PROTECCION SOCIAL", "23"), ("PREVISION SOCIAL", "24"),
             ("DEUDA PUBLICA", "25")]
CORRIENTES, CAPITAL = ["5-2-1", "5-2-2", "5-2-3", "5-2-4", "5-2-5"], ["6-2-4", "6-2-5", "6-2-6", "6-2-7"]
POR_DEFECTO = Path(__file__).with_name("estad_fiscal_filas.json")
MESES_VALORES = 25                    # meses del ESTAD subido que se guardan para comparar


def _k(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", t).strip()


def hoja_fiscal(nombre):
    """(nivel E/R/M, tipo 'gasto'|'inversion') de una hoja del ESTAD, o None (INGRESOS y las demás)."""
    h = _k(nombre)
    if "INGRESO" in h:
        return None
    n = "E" if "G.N" in h else "R" if "G.R" in h else "M" if "G.L" in h else None
    t = "gasto" if "GASTO" in h else "inversion" if "INVERSI" in h else None
    return (n, t) if n and t else None


def concepto(etiqueta, bloque, tipo):
    """Qué es una fila: (base, filtro) o None si es un título, una nota o algo que la página no separa.
    base: gen (genéricas), deu (servicio de la deuda), fue / ifu (gasto / inversión por fuente), fun (función)."""
    e = _k(etiqueta)
    if not e or e.startswith(("FUENTE:", "FUENTE :", "1 /", "1/", "CUADRO", "(")):
        return None
    sin_num = re.sub(r"^\d+\s*:\s*", "", e)
    fuente = "fue" if tipo == "gasto" else "ifu"
    if tipo == "gasto":
        if e.startswith(("TOTAL DE GASTOS", "GASTOS POR GENERICA")):
            return ("gen", None)
        if e.startswith("GASTOS POR FUENTE"):
            return ("fue", None)
        if e.startswith("GASTOS CORRIENTES"):
            return ("gen", CORRIENTES)
        if e.startswith("GASTOS DE CAPITAL"):
            return ("gen", CAPITAL)
        if e.startswith("SERVICIO DE LA DEUDA"):
            return ("gen", ["7-2-8"])
        if bloque != "fuente":
            if sin_num.startswith("PERSONAL"):
                return ("gen", ["5-2-1"])
            if sin_num.startswith("PENSIONES"):
                return ("gen", ["5-2-2"])
            if sin_num.startswith("BIENES"):
                return ("gen", ["5-2-3"])
            if sin_num.startswith("DONACIONES"):
                return ("gen", ["5-2-4"] if bloque == "corriente" else ["6-2-4"])
            if sin_num.startswith("OTROS GASTOS CORRIENTES"):
                return ("gen", ["5-2-5"])
            if sin_num.startswith("OTROS GASTOS DE CAPITAL"):
                return ("gen", ["6-2-5"])
            if "ACTIVOS NO FINANCIEROS" in e or "INVERSIONES NO FINANCIERAS" in e:
                return ("gen", ["6-2-6"])
            if "ACTIVOS FINANCIEROS" in e or "INVERSIONES FINANCIERAS" in e:
                return ("gen", ["6-2-7"])
            if sin_num.startswith("INTERESES"):
                return ("deu", "INTERESES Y COMISIONES")
            if sin_num.startswith("AMORTIZACION"):
                return ("deu", "AMORTIZACIÓN")
    else:
        if e.startswith(("TOTAL DE INVERSION", "INVERSION POR FUNCION", "INVERSIONES POR")):
            return ("fun", None)
        if e.startswith(("GASTOS POR FUENTE", "INVERSION POR FUENTE", "FUENTES DE FINANCIAMIENTO")):
            return ("ifu", None)
        if bloque != "fuente":
            if "TRANSPORTE" in sin_num and "COMUNICACIONES" in sin_num:
                return ("fun", ["15", "16"])
            for nombre, cod in FUNCIONES:
                if sin_num.startswith(nombre) or nombre in sin_num:
                    return ("fun", [cod])
    if bloque == "fuente":
        if "ORDINARIOS" in sin_num:
            return (fuente, ["1"])
        if "DIRECTAMENTE" in sin_num or "D. RECAUD" in sin_num:
            return (fuente, ["2"])
        if "CREDITO" in sin_num or "CRED" in sin_num or "OPERACIONES" in sin_num or "OPER." in sin_num or "OPERAIONES" in sin_num:
            return (fuente, ["3"])
        if sin_num.startswith("DONACIONES"):
            return (fuente, ["4"])
        if "DETERMINADOS" in sin_num:
            return (fuente, ["5"])
    return None


def _bloque(etiqueta, actual):
    e = _k(etiqueta)
    if "POR FUENTE" in e or e.startswith("FUENTES DE FINANCIAMIENTO"):
        return "fuente"
    if e.startswith("GASTOS CORRIENTES"):
        return "corriente"
    if e.startswith("GASTOS DE CAPITAL"):
        return "capital"
    if e.startswith("SERVICIO DE LA DEUDA"):
        return "deuda"
    return actual


def _filas_de(etiquetas, tipo):
    """[(fila, etiqueta)] del cuadro nominal (hasta la nota «Fuente: MEF») -> [{fila, etiqueta, base, filtro}]."""
    salida, bloque, vistos = [], None, set()
    for fila, etiqueta in etiquetas:
        e = _k(etiqueta)
        if e.startswith(("FUENTE:", "FUENTE :")):
            break
        bloque = _bloque(etiqueta, bloque)
        c = concepto(etiqueta, bloque, tipo)
        if c is not None:
            clave = (c[0], json.dumps(c[1]))
            if clave in vistos:                       # fila repetida: el ESTAD solo llena la primera
                c = None
            else:
                vistos.add(clave)
        salida.append({"fila": fila, "etiqueta": str(etiqueta).strip(), "base": c[0] if c else None, "filtro": c[1] if c else None})
    return salida


# ── El libro ESTAD subido ──
def leer_libro(ruta):
    """{depto: {"hojas": [{hoja, nivel, tipo, titulo, fila_fechas, filas, valores}]}} de un libro ESTAD; vacío si no
    tiene hojas de gasto o inversión. valores: {fila: {AAAA-MM: miles de soles}} de los últimos MESES_VALORES meses."""
    try:
        wb = load_workbook(ruta, read_only=True, data_only=True)
    except Exception:
        return {}
    try:
        salida = {}
        for ws in wb.worksheets:
            ht = hoja_fiscal(ws.title)
            if not ht:
                continue
            filas = [list(r) for r in ws.iter_rows(min_row=1, max_row=60, values_only=True)]
            titulo = [str(r[0]).strip() if r and r[0] is not None else "" for r in filas[:3]]
            depto = next((d for d, n in DEPTOS.items() if _k(" ".join(titulo)).find(_k(n) + ":") >= 0), None)
            ff = next((i for i, r in enumerate(filas[:10]) if sum(isinstance(v, datetime) for v in r) >= 3), None)
            if depto is None or ff is None:
                continue
            cols = {f"{v.year}-{v.month:02d}": j for j, v in enumerate(filas[ff]) if isinstance(v, datetime)}
            etiquetas = [(i + 1, r[0]) for i, r in enumerate(filas) if i > ff and r and isinstance(r[0], str) and r[0].strip()]
            items = _filas_de(etiquetas, ht[1])
            recientes = sorted(cols)[-MESES_VALORES:]
            # un mes que aún no se llenó con montos (p. ej. trae la variación %): su total es mucho menor que el de los demás
            fila_total = next((it["fila"] for it in items if it["base"] and it["filtro"] is None), None)
            if fila_total:
                r = filas[fila_total - 1]
                tot = {p: abs(float(r[cols[p]])) for p in recientes if cols[p] < len(r) and isinstance(r[cols[p]], (int, float))}
                tipico = sorted(tot.values())[len(tot) // 2] if tot else 0
                recientes = [p for p in recientes if p not in tot or tipico == 0 or tot[p] >= 0.05 * tipico]
            valores = {}
            for it in items:
                r = filas[it["fila"] - 1]
                v = {p: float(r[cols[p]]) for p in recientes if cols[p] < len(r) and isinstance(r[cols[p]], (int, float))}
                if v:
                    valores[str(it["fila"])] = v
            salida.setdefault(depto, {"hojas": []})["hojas"].append(
                {"hoja": ws.title, "nivel": ht[0], "tipo": ht[1], "titulo": titulo, "fila_fechas": ff + 1,
                 "filas": [{"fila": it["fila"], "etiqueta": it["etiqueta"]} for it in items], "valores": valores})
        return salida
    finally:
        wb.close()


def plantilla(ruta):
    """El libro ESTAD reducido a sus hojas de gasto e inversión, con su formato y sus fórmulas (totales, variaciones,
    cuadro en reales), para llenarlo después con los meses nuevos. bytes .xlsx (~400 KB)."""
    wb = load_workbook(ruta)
    try:
        quedan = [ws.title for ws in wb.worksheets if hoja_fiscal(ws.title)]
        for ws in list(wb.worksheets):
            if ws.title not in quedan:
                wb.remove(ws)
        for nombre in list(wb.defined_names):            # nombres que apuntan a hojas que ya no están
            dest = str(wb.defined_names[nombre].attr_text or "")
            hojas = re.findall(r"'?([^'!]+)'?!", dest)
            if hojas and any(h.strip("'") not in quedan for h in hojas if "[" not in h):
                del wb.defined_names[nombre]
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    finally:
        wb.close()


def cargar_libro(ruta, nombre=""):
    """Guarda el orden de filas, los valores recientes y la plantilla (formato y fórmulas) de las hojas fiscales de un
    ESTAD. -> avisos."""
    avisos = []
    libro = leer_libro(ruta)
    plantilla_xlsx = plantilla(ruta) if libro else None
    for depto, x in libro.items():
        x.update(archivo=nombre, fecha=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        db.guardar_documento(f"estad-fiscal-{depto}", json.dumps(x, ensure_ascii=False), x["fecha"])
        db.guardar_documento(f"estad-fiscal-plantilla-{depto}", base64.b64encode(plantilla_xlsx).decode(), x["fecha"])
        avisos.append(f"{nombre or 'ESTAD'}: {len(x['hojas'])} hojas de gasto e inversión de {DEPTOS[depto].title()} guardadas "
                      "(Ejecución del presupuesto → ESTAD).")
    return avisos


def estructura(depto):
    """(hojas, origen): el orden de filas del último ESTAD subido o, si no hay, el que viene con la página."""
    doc = db.documento(f"estad-fiscal-{depto}")
    if doc:
        x = json.loads(doc[0])
        return x["hojas"], {"archivo": x.get("archivo"), "fecha": x.get("fecha"), "subido": True}
    base = json.loads(POR_DEFECTO.read_text(encoding="utf-8"))
    return base[depto]["hojas"], {"archivo": base[depto].get("archivo"), "fecha": None, "subido": False}


# ── Cálculo con las bases de la página ──
def _datos(depto, desde, hasta):
    def prep(base):
        df = db.leer(base, [depto], list(NIVEL), desde, hasta)
        if df.empty:
            return df.assign(P="", N="", V=0.0)
        mes = pd.to_numeric(df["MES"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
        return df.assign(P=df["AÑO"].astype(int).astype(str) + "-" + mes.astype(int).map("{:02d}".format),
                         N=df["NIVEL_GOBIERNO"].astype(str).str[0], V=pd.to_numeric(df["DEVENGADO"], errors="coerce").fillna(0) / 1000)
    return {"gen": prep("gasto-dev-generica"), "fue": prep("gasto-dev-fuente"), "fun": prep("inv-dev-funcion"), "ifu": prep("inv-dev-fuente")}


def _valor(d, base, filtro, nivel, p):
    if base == "deu":
        x = d["gen"]
        x = x[(x.N == nivel) & (x.P == p)] if not x.empty else x
        if x.empty:
            return None                               # sin gasto ese mes: vacío; con gasto y sin deuda: 0
        x = x[x.COD_GENERICA.astype(str) == "7-2-8"]
        return x.loc[x.DESGLOSE.astype(str).str.upper() == filtro, "V"].sum()
    x = d[base]
    if x.empty:
        return None
    x = x[(x.N == nivel) & (x.P == p)]
    if x.empty:
        return None
    if filtro is None:
        return x.V.sum()
    if base == "gen":
        return x.loc[x.COD_GENERICA.astype(str).isin(filtro), "V"].sum()
    if base in ("fue", "ifu"):
        return x.loc[x.COD_FUENTE.astype(str).isin(filtro), "V"].sum()
    return x.loc[x.FUNCION.astype(str).str[:2].isin(filtro), "V"].sum()


def _r0(v):
    return None if v is None else int(Decimal(repr(float(v))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _miles(v):
    """Miles de soles sin redondear (soles / 1000, al céntimo): el Excel muestra los miles y guarda los decimales, así
    las variaciones reales del ESTAD salen precisas."""
    return None if v is None else round(float(v), 5)


def _meses(desde, hasta):
    a, m = int(desde[:4]), int(desde[5:7])
    salida = []
    while (a, m) <= (int(hasta[:4]), int(hasta[5:7])):
        salida.append(f"{a}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return salida


def ultimo_mes(depto):
    """El último mes con gasto por genérica en la página (AAAA-MM), o None."""
    df = db.leer("gasto-dev-generica", [depto], list(NIVEL), "1990-01", "2100-12")
    if df.empty:
        return None
    mes = pd.to_numeric(df["MES"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    p = (df["AÑO"].astype(int) * 100 + mes).max()
    return f"{p // 100}-{p % 100:02d}"


def armar(depto, desde=None, hasta=None):
    """Las hojas de gasto e inversión de la región, mes a mes, con el ESTAD subido al lado para comparar."""
    hasta = hasta or ultimo_mes(depto)
    if not hasta:
        return None
    desde = desde or f"{hasta[:4]}-01"
    meses = _meses(desde, hasta)
    hojas, origen = estructura(depto)
    d = _datos(depto, desde, hasta)
    salida = []
    for h in hojas:
        tipo, nivel = h["tipo"], h["nivel"]
        conceptos = {it["fila"]: it for it in _filas_de([(f["fila"], f["etiqueta"]) for f in h["filas"]], tipo)}
        filas = []
        for f in h["filas"]:
            c = conceptos.get(f["fila"], {})
            vals = {p: _miles(_valor(d, c["base"], c["filtro"], nivel, p)) for p in meses} if c.get("base") else {}
            estad = (h.get("valores") or {}).get(str(f["fila"]), {})
            filas.append({"fila": f["fila"], "etiqueta": f["etiqueta"], "llena": bool(c.get("base")), "valores": vals,
                          "estad": {p: estad[p] for p in meses if p in estad}})
        salida.append({"hoja": h["hoja"], "nivel": NIVEL[nivel], "tipo": tipo, "titulo": h.get("titulo", []),
                       "fila_fechas": h.get("fila_fechas", 5), "filas": filas})
    sin_fuente = sorted({p for p in meses if all(_valor(d, "fue", None, n, p) is None for n in NIVEL)})
    return {"departamento": DEPTOS[depto], "desde": desde, "hasta": hasta, "meses": meses, "hojas": salida, "origen": origen,
            "sin_fuente": sin_fuente, "unidad": "miles de soles"}


def diferencias(e, tolerancia=1):
    """Celdas donde lo calculado y el ESTAD subido difieren en más de «tolerancia» miles de soles."""
    salida = []
    for h in e["hojas"]:
        for f in h["filas"]:
            for p, v in f["estad"].items():
                c = f["valores"].get(p)
                if f["llena"] and c is not None and abs(c - v) > tolerancia:
                    salida.append({"hoja": h["hoja"], "fila": f["fila"], "etiqueta": f["etiqueta"], "mes": p, "estad": v,
                                   "pagina": c, "dif": c - v})
    return salida


def excel(e, depto=None):
    """El Excel del ESTAD: con el último ESTAD subido como plantilla (mismo formato, totales, variaciones y cuadro en
    reales, con sus fórmulas) llenado con los meses pedidos; si no se subió, uno simple con las mismas filas."""
    doc = db.documento(f"estad-fiscal-plantilla-{depto}") if depto else None
    if doc:
        return llenar_plantilla(base64.b64decode(doc[0]), e)
    return excel_simple(e)


_REF = re.compile(r"\$?[A-Z]{1,3}\$?\d+")
_SUELTAS = re.compile(r"(?<![:A-Z$])\$?([A-Z]{1,3})\$?(\d+)(?![:\d])(?!\s*:)")   # celdas sueltas (no rangos A1:A9)


def _con_referencias(v):
    return isinstance(v, str) and v.startswith("=") and bool(_REF.search(v[1:]))


def llenar_plantilla(xlsx, e):
    from openpyxl.formula.translate import Translator
    from . import ipc
    wb = load_workbook(io.BytesIO(xlsx))
    serie_ipc = ipc.serie()
    avisos = []
    # el bloque consolidado de G.R. (San Martín, Ucayali) apunta a otra copia del ESTAD en una carpeta de red
    # ('[1]GASTOS G.N.'!ET9): se apunta a la hoja del mismo libro, que es la que se acaba de llenar
    externas = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("=") and "[" in c.value:
                    nuevo = re.sub(r"'\[\d+\]([^']+)'!", lambda m: f"'{m.group(1)}'!" if m.group(1) in wb.sheetnames else m.group(0), c.value)
                    if nuevo != c.value:
                        c.value, externas = nuevo, externas + 1
    if externas:
        avisos.append(f"{externas} fórmulas que apuntaban a otra copia del ESTAD (vínculo externo) ahora usan las hojas de este libro.")
    for h in e["hojas"]:
        if h["hoja"] not in wb.sheetnames:
            avisos.append(f"{h['hoja']}: no está en el ESTAD subido.")
            continue
        ws = wb[h["hoja"]]
        ff = h["fila_fechas"]
        col = {}
        for c in ws[ff]:
            if isinstance(c.value, datetime):
                col[f"{c.value.year}-{c.value.month:02d}"] = c.column
        orden = sorted(col)
        faltan = [p for p in e["meses"] if p not in col]
        if faltan:
            avisos.append(f"{h['hoja']}: el ESTAD no tiene columna para {', '.join(faltan)}.")
        # la fila del deflactor: la que dividen las fórmulas del cuadro en reales (=+EV7/$EV$36)
        filas_def = re.findall(r"/\$[A-Z]{1,3}\$(\d+)", " ".join(str(c.value) for row in ws.iter_rows() for c in row
                                                                 if isinstance(c.value, str) and c.value.startswith("=")))
        fila_def = int(max(set(filas_def), key=filas_def.count)) if filas_def else None
        llenas = {f["fila"]: f for f in h["filas"] if f["llena"]}
        for p in e["meses"]:
            if p not in col:
                continue
            j = col[p]
            i = orden.index(p)
            antes = col[orden[i - 1]] if i else None
            # 1. montos de las filas que la página sabe llenar (miles de soles con decimales; el formato muestra los miles)
            for r, f in llenas.items():
                v = f["valores"].get(p)
                celda, previa = ws.cell(r, j), ws.cell(r, antes) if antes else None
                if _con_referencias(celda.value) or (previa is not None and _con_referencias(previa.value) and celda.value is None):
                    continue                              # total con fórmula: lo calcula el ESTAD
                if v is not None:
                    celda.value = v
                    if celda.number_format == "General":       # que se vean solo los miles (los decimales quedan en la celda)
                        celda.number_format = previa.number_format if previa is not None and previa.number_format != "General" else "#,##0"
            # 2. filas que no llena la página pero que el ESTAD pone en 0 (FONCOR, privatizaciones)
            for f in h["filas"]:
                if not f["llena"] and antes and ws.cell(f["fila"], j).value is None and ws.cell(f["fila"], antes).value == 0:
                    ws.cell(f["fila"], j).value = 0
            # 3. deflactor: variación % mensual del IPC (fila de encima) e índice encadenado
            if fila_def and antes:
                ip, ia = serie_ipc.get(p), serie_ipc.get(orden[i - 1])
                d_ant = ws.cell(fila_def, antes).value
                if ip and ia and isinstance(d_ant, (int, float)) and ws.cell(fila_def, j).value is None:
                    var = round((ip / ia - 1) * 100, 2)
                    ws.cell(fila_def - 1, j).value = var
                    ws.cell(fila_def, j).value = d_ant * (1 + var / 100)
                    for rr in (fila_def - 1, fila_def):
                        ws.cell(rr, j).number_format = ws.cell(rr, antes).number_format
                elif ws.cell(fila_def, j).value is None:
                    avisos.append(f"{h['hoja']}: falta el IPC de {etiqueta_mes(p)} para el deflactor.")
            # 4. fórmulas del mes anterior que este mes aún no tiene (totales, cuadro en reales, deflactados)
            if antes:
                nuevas = []
                for r in range(1, ws.max_row + 1):
                    previa, celda = ws.cell(r, antes), ws.cell(r, j)
                    if celda.value is None and _con_referencias(previa.value):
                        f = Translator(previa.value, origin=previa.coordinate).translate_formula(celda.coordinate)
                        # el ESTAD fija con $ la columna del propio mes (=+EV7/$EV$36): esa también se corre al mes nuevo
                        celda.value = re.sub(rf"\${previa.column_letter}\$(\d+)", rf"${celda.column_letter}$\1", f)
                        if celda.number_format == "General":
                            celda.number_format = previa.number_format
                        nuevas.append(celda)
                # una fórmula que usa un dato que la página no tiene (p. ej. el índice de precios al por mayor) se deja
                # vacía, como el ESTAD antes de cargar el mes (si no, daría #¡DIV/0!)
                letra, cambio = ws.cell(1, j).column_letter, True
                while cambio:
                    cambio = False
                    for celda in nuevas:
                        if celda.value is None:
                            continue
                        for c_, r_ in _SUELTAS.findall(celda.value):
                            if c_ == letra and ws.cell(int(r_), j).value is None:
                                celda.value, cambio = None, True
                                break
                        if celda.number_format == "General":
                            celda.number_format = previa.number_format
        # 5. las columnas de variación (Var.% y Ene.-mes) toman como referencia el último mes llenado: en el ESTAD es una
        #    celda «=EV5» (o «=EV38» en el cuadro en reales) que se cambia a mano cada mes
        if e["hasta"] in col and orden:
            ultima = max(col.values())
            nueva = ws.cell(1, col[e["hasta"]]).column_letter
            letras = {ws.cell(1, c).column_letter for c in col.values()}
            for row in ws.iter_rows(min_col=ultima + 1):
                for c in row:
                    m = re.fullmatch(r"=\+?(\$?)([A-Z]{1,3})(\$?)(\d+)", str(c.value or "").strip())
                    if m and m.group(2) in letras and int(m.group(4)) == c.row:
                        c.value = f"={m.group(1)}{nueva}{m.group(3)}{m.group(4)}"
    dif = diferencias(e)
    ws = wb.create_sheet("Diferencias")
    ws.append(["Hoja", "Fila", "Etiqueta", "Mes", "ESTAD subido", "Página", "Diferencia"])
    for x in dif:
        ws.append([x["hoja"], x["fila"], x["etiqueta"], x["mes"], x["estad"], x["pagina"], x["dif"]])
    if not dif:
        ws.append(["Sin diferencias de más de 1 mil soles con el ESTAD subido"])
    nota = wb.create_sheet("Notas")
    for t in [f"Meses llenados por la página: {etiqueta_mes(e['desde'])} a {etiqueta_mes(e['hasta'])}, con los datos del MEF "
              "(devengado, Consulta Amigable) en miles de soles con sus decimales: el formato muestra solo los miles.",
              "Los totales, el cuadro en reales y las variaciones son las fórmulas del ESTAD subido; el deflactor (variación "
              "% mensual e índice) sale del IPC de Lima que tiene la página.",
              "No se llenan: Fondo de Compensación Regional y Privatizaciones (el MEF los incluye en Recursos determinados), "
              "el índice de precios al por mayor ni las hojas de INGRESOS."] + avisos:
        nota.append([t])
    nota.column_dimensions["A"].width = 140
    wb.calculation.fullCalcOnLoad = True
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def etiqueta_mes(p):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
    return f"{meses[int(p[5:7]) - 1]} {p[:4]}"


def excel_simple(e):
    """Un libro con las mismas hojas y filas que el ESTAD (las etiquetas en la columna A, en su misma fila) y los meses
    en columnas, para copiar el bloque de meses y pegarlo en el ESTAD. Más una hoja «Diferencias» con el ESTAD subido."""
    wb = Workbook()
    wb.remove(wb.active)
    negrita, gris = Font(bold=True), PatternFill("solid", fgColor="EEEEEE")
    for h in e["hojas"]:
        ws = wb.create_sheet(h["hoja"][:31])
        for i, t in enumerate(h["titulo"][:3], 1):
            ws.cell(i, 1, t).font = negrita
        ff = h["fila_fechas"]
        ws.cell(ff - 1, 2, f"Calculado por la página con los datos del MEF ({e['unidad']}). Copia las columnas de los meses y pégalas en el ESTAD.")
        for j, p in enumerate(e["meses"], 2):
            c = ws.cell(ff, j, datetime(int(p[:4]), int(p[5:7]), 1))
            c.number_format, c.font, c.alignment = "mmm-yy", negrita, Alignment(horizontal="center")
        for f in h["filas"]:
            ws.cell(f["fila"], 1, f["etiqueta"])
            if not f["llena"]:
                ws.cell(f["fila"], 1).fill = gris
                continue
            for j, p in enumerate(e["meses"], 2):
                v = f["valores"].get(p)
                if v is not None:
                    ws.cell(f["fila"], j, v).number_format = "#,##0"   # los miles; los decimales quedan en la celda
        ws.column_dimensions["A"].width = 46
        for j in range(2, len(e["meses"]) + 2):
            ws.column_dimensions[ws.cell(1, j).column_letter].width = 11
        ws.freeze_panes = ws.cell(ff + 1, 2)
    dif = diferencias(e)
    ws = wb.create_sheet("Diferencias")
    ws.append(["Hoja", "Fila", "Etiqueta", "Mes", "ESTAD subido", "Página", "Diferencia"])
    for c in ws[1]:
        c.font = negrita
    for x in dif:
        ws.append([x["hoja"], x["fila"], x["etiqueta"], x["mes"], x["estad"], x["pagina"], x["dif"]])
    if not dif:
        ws.append(["Sin diferencias de más de 1 mil soles con el ESTAD subido" if e["origen"]["subido"]
                   else "Todavía no se subió el ESTAD de la región: no hay con qué comparar"])
    ws.column_dimensions["A"].width, ws.column_dimensions["C"].width = 18, 40
    nota = wb.create_sheet("Notas")
    for t in ["Montos en miles de soles (devengado), redondeados a la unidad. Fuente: MEF, Consulta Amigable.",
              "Gasto: genéricas 5-21 a 5-25 (corriente), 6-24 a 6-27 (capital) y 7-28 (servicio de la deuda: amortización e intereses).",
              "Inversión: genérica 2.6 (adquisición de activos no financieros) por función y por fuente de financiamiento.",
              "Filas en gris: la página no las llena (títulos, filas repetidas, o rubros que el MEF no separa en la consulta por "
              "fuente: Fondo de Compensación Regional y Privatizaciones y concesiones, que van dentro de Recursos determinados).",
              ("Meses sin datos por fuente (la página los tiene desde enero de 2025): " + ", ".join(e["sin_fuente"])) if e["sin_fuente"] else "",
              f"Orden de filas: {'el ESTAD subido (' + (e['origen']['archivo'] or '') + ')' if e['origen']['subido'] else 'el que viene con la página'}."]:
        if t:
            nota.append([t])
    nota.column_dimensions["A"].width = 140
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
