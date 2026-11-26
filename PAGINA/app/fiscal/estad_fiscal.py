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
import functools
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

from .. import db

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
    """(nivel E/R/M, tipo 'gasto'|'inversion'|'ingresos') de una hoja del ESTAD, o None."""
    h = _k(nombre)
    n = "E" if "G.N" in h else "R" if "G.R" in h else "M" if "G.L" in h else None
    t = "ingresos" if "INGRESO" in h else "gasto" if "GASTO" in h else "inversion" if "INVERSI" in h else None
    return (n, t) if n and t else None


def concepto_ingresos(etiqueta, bloque, ctx):
    """Una fila de las hojas de INGRESOS -> ("ing", términos) o None. Términos: [[signo, selector]] con selector
    «C:código» (clasificador), «F:fuente», «H:padre:palabra» (el hijo del padre cuyo nombre la contiene) o «Z» (cero).
    ctx: qué filas trae la hoja (cada región separa conceptos distintos)."""
    e = re.sub(r"^\d+\s*:\s*", "", _k(etiqueta))
    e = re.sub(r"^[-.\s]+", "", e)
    if not e or e.startswith(("FUENTE", "1 /", "1/", "CUADRO", "(")):
        return None
    t = lambda *xs: ("ing", [[1, x] for x in xs])
    if bloque in ("dyt_total", "dyt_corr", "dyt_cap"):
        p = "1-4-2" if bloque == "dyt_cap" else "1-4-1"
        if bloque == "dyt_total":
            return t("C:1-4")
        if e.startswith("D Y T CORRIENTES"):
            return t("C:1-4-1")
        if e.startswith("D DE CAPITAL"):
            return t("C:1-4-2")
        if e.startswith("DE GOBIERNOS EXTRANJEROS"):
            return t(f"C:{p}-1")
        if e.startswith("DE ORGANISMOS INTERNACIONALES"):
            return t(f"C:{p}-2")
        if e.startswith("DE AGENCIAS"):
            return t(f"H:{p}:AGENCIA")
        if e.startswith("DE OTRAS UNIDADES DE GOBIERNO"):
            return t(f"C:{p}-3")
        for clave, palabra in (("DEL GOBIERNO NACIONAL", "NACIONAL"), ("DEL GOBIERNO REGIONAL", "REGIONAL"), ("DE LOS GOBIERNOS REGIONALES", "REGIONAL"),
                               ("DE LOS GOBIERNOS LOCALES", "LOCAL"), ("DE OTRAS ENTIDADES", "ENTIDADES"), ("DE FONDOS", "FONDOS")):
            if e.startswith(clave):
                return t(f"H:{p}-3-1:{palabra}")
        if e.startswith("POR PARTICIPACIONES"):
            return t("C:1-4-1-4")
        if e.startswith("CANON Y SOBRECANON"):
            return t("C:1-4-1-4-1")
        for clave in ("SOBRECANON PETROLERO", "CANON PETROLERO", "CANON MINERO", "CANON GASIFERO", "CANON FORESTAL", "CANON HIDROENERGETICO"):
            if e.startswith(clave):
                return t(f"H:1-4-1-4-1:{clave}")
        if e.startswith("REGALIA"):
            return t("H:1-4-1-4:REGALIA")
        if e.startswith("RENTA DE ADUANAS"):
            return t("H:1-4-1-4:ADUANA")
        if "ELIMINACION" in e or "ELEMINACION" in e:
            return ("ing", [[1, "H:1-4-1-4:ELIMINACION"]] + ([] if ctx["foncor"] else [[1, "H:1-4-1-4:COMPENSACION REGIONAL"]]))
        if e.startswith("FONCOMUN"):
            return ("ing", [[1, "H:1-4-1-4:COMPENSACION MUNICIPAL"]] + ([] if ctx["eliminacion"] else [[1, "H:1-4-1-4:ELIMINACION"]]))
        if e.startswith("FONDO DE COMPENSACION REGIONAL") or e.startswith("FONCOR"):
            return t("H:1-4-1-4:COMPENSACION REGIONAL")
        if e.startswith("POR ASIGNACION ESPECIAL"):
            return t("H:1-4-1-4:ASIGNACION ESPECIAL")
        if e.startswith("POR PLAN DE INCENTIVOS"):
            return t("H:1-4-1-4-6:INCENTIVOS")
        if e.startswith("POR BONO"):
            return t("H:1-4-1-4-6:BONO")
        return None
    if bloque == "fuente":
        if e.startswith(("TOTAL INGRESOS POR FUENTE", "INGRESOS POR FUENTE")):
            return t("F:*")
        if "DETERMINADOS" in e:
            return t("F:5")
        if "DIRECTAMENTE" in e:
            return t("F:2")
        if "CREDITO" in e or "OPERACIONES" in e:
            return t("F:3")
        if e.startswith("DONACIONES"):
            return t("F:4")
        if "COMPESACION" in e or "COMPENSACION" in e or "PRIVATIZ" in e:
            return ("ing", [[1, "Z"]])
        return None
    if e.startswith(("TOTAL DE INGRESOS", "INGRESOS DEL GOBIERNO", "INGRESOS DE LOS GOBIERNOS")):
        return t(*[f"C:1-{i}" for i in range(1, 10)])
    if e.startswith("INGRESOS CORRIENTES"):
        return t("C:1-1", "C:1-2", "C:1-3", "C:1-4-1" if ctx["transferencias"] else "C:1-4", "C:1-5")
    if e.startswith("IMPUESTOS"):
        return t("C:1-1")
    if e.startswith("CONTRIBUCIONES SOCIALES"):
        return t("C:1-2")
    if e.startswith("VENTA DE BIENES Y SERVICIOS"):
        return t("C:1-3")
    if e.startswith("TASAS"):
        return t("C:1-3-2")
    if e == "VENTA DE BIENES":
        return t("C:1-3-1")
    if e.startswith("PRESTACION DE SERVICIOS"):
        return t("C:1-3-3")
    if e.startswith("RENTAS DE LA PROPIEDAD"):
        return t("C:1-5-1")
    if e.startswith("MULTAS"):
        return t("C:1-5-2")
    if e.startswith("DONACIONES Y TRANSFERENCIAS"):
        return t("C:1-4-1" if ctx["transferencias"] else "C:1-4")
    if e.startswith("OTROS INGRESOS CORRIENTES"):
        return ("ing", [[1, "C:1-5"]] + ([[-1, "C:1-5-1"]] if ctx["rentas"] else []) + ([[-1, "C:1-5-2"]] if ctx["multas"] else []))
    if e.startswith("OTROS INGRESOS"):
        return t("C:1-5")
    if e.startswith("INGRESOS DE CAPITAL"):
        return t("C:1-6", "C:1-7")
    if e.startswith("VENTA DE ACTIVOS NO FINANCIEROS"):
        return t("C:1-6")
    if e.startswith("VENTA DE ACTIVOS FINANCIEROS"):
        return t("C:1-7")
    if e.startswith("TRANSFERENCIAS"):
        return t("C:1-4-2")
    if e.startswith("FINANCIAMIENTO"):
        return t("C:1-8", "C:1-9")
    if e.startswith("ENDEUDAMIENTO"):
        return t("C:1-8")
    if e.startswith("SALDO"):
        return t("C:1-9")
    return None


def _contexto_ingresos(etiquetas):
    es = [re.sub(r"^[\d\s:.-]+", "", _k(x)) for _, x in etiquetas]
    return {"transferencias": any(x == "TRANSFERENCIAS" for x in es), "rentas": any(x.startswith("RENTAS DE LA PROPIEDAD") for x in es),
            "multas": any(x.startswith("MULTAS") for x in es), "foncor": any(x.startswith(("FONDO DE COMPENSACION REGIONAL", "FONCOR")) for x in es),
            "eliminacion": any("ELIMINACION" in x or "ELEMINACION" in x for x in es)}


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
    e = re.sub(r"^\d+\s*:\s*", "", _k(etiqueta))
    if actual and actual.startswith("dyt"):
        if e.startswith("D Y T CORRIENTES"):
            return "dyt_corr"
        if e.startswith("D DE CAPITAL"):
            return "dyt_cap"
        return actual
    if e.startswith("INGRESOS CORRIENTES"):
        return "corriente"
    if e.startswith("INGRESOS DE CAPITAL"):
        return "capital"
    if e.startswith("FINANCIAMIENTO"):
        return "financiamiento"
    if "POR FUENTE" in e or e.startswith("FUENTES DE FINANCIAMIENTO"):
        return "fuente"
    if e.startswith("GASTOS CORRIENTES"):
        return "corriente"
    if e.startswith("GASTOS DE CAPITAL"):
        return "capital"
    if e.startswith("SERVICIO DE LA DEUDA"):
        return "deuda"
    return actual


def _filas_de(etiquetas, tipo, bloque_inicial=None):
    """[(fila, etiqueta)] del cuadro nominal (hasta la nota «Fuente: MEF») -> [{fila, etiqueta, base, filtro}].
    En INGRESOS, el cuadro de donaciones y transferencias se pasa aparte, con bloque_inicial «dyt_total»."""
    salida, bloque, vistos = [], bloque_inicial, set()
    ctx = _contexto_ingresos(etiquetas) if tipo == "ingresos" else None
    for i, (fila, etiqueta) in enumerate(etiquetas):
        e = _k(etiqueta)
        if e.startswith(("FUENTE:", "FUENTE :")):
            break
        bloque = _bloque(etiqueta, bloque)
        c = concepto_ingresos(etiqueta, bloque, ctx) if tipo == "ingresos" else concepto(etiqueta, bloque, tipo)
        if c is not None:
            clave = (c[0], json.dumps(c[1]))
            if clave in vistos and c[1] != [[1, "Z"]]:  # fila repetida: el ESTAD solo llena la primera
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
            filas = [list(r) for r in ws.iter_rows(min_row=1, max_row=110, values_only=True)]
            titulo = [str(r[0]).strip() if r and r[0] is not None else "" for r in filas[:3]]
            depto = next((d for d, n in DEPTOS.items() if _k(" ".join(titulo)).find(_k(n) + ":") >= 0), None)
            ff = next((i for i, r in enumerate(filas[:10]) if sum(isinstance(v, datetime) for v in r) >= 3), None)
            if depto is None or ff is None:
                continue
            cols = {f"{v.year}-{v.month:02d}": j for j, v in enumerate(filas[ff]) if isinstance(v, datetime)}
            etiquetas = [(i + 1, r[0]) for i, r in enumerate(filas) if i > ff and r and isinstance(r[0], str) and r[0].strip()]
            items = _filas_de(etiquetas, ht[1])
            if ht[1] == "ingresos":                   # y el cuadro de donaciones y transferencias, más abajo
                k = next((j for j, (_, x) in enumerate(etiquetas) if _k(x).startswith("D Y T CORRIENTES")), None)
                if k:
                    dyt = etiquetas[k - 1:]
                    fin = next((j for j, (_, x) in enumerate(dyt) if _k(x).startswith(("FUENTE", "1 /", "1/"))), len(dyt))
                    items += [{**it, "bloque": "dyt"} for it in _filas_de(dyt[:fin], "ingresos", "dyt_total")]
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
                 "filas": [{"fila": it["fila"], "etiqueta": it["etiqueta"], **({"bloque": "dyt"} if it.get("bloque") else {})} for it in items],
                 "valores": valores})
        return salida
    finally:
        wb.close()


def cargar_libro(ruta, nombre=""):
    """Guarda el orden de filas y los valores recientes (para comparar) de las hojas fiscales de un ESTAD. -> avisos."""
    avisos = []
    for depto, x in leer_libro(ruta).items():
        x.update(archivo=nombre, fecha=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        db.guardar_documento(f"estad-fiscal-{depto}", json.dumps(x, ensure_ascii=False), x["fecha"])
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
def _conceptos(h):
    """{fila: concepto} de una hoja, con el cuadro de donaciones y transferencias aparte en las de ingresos."""
    principal = [(f["fila"], f["etiqueta"]) for f in h["filas"] if not f.get("bloque")]
    dyt = [(f["fila"], f["etiqueta"]) for f in h["filas"] if f.get("bloque") == "dyt"]
    salida = {it["fila"]: it for it in _filas_de(principal, h["tipo"])}
    if dyt:
        salida.update({it["fila"]: it for it in _filas_de(dyt, "ingresos", "dyt_total")})
    return salida


def _datos(depto, desde, hasta):
    def prep(base):
        df = db.leer(base, [depto], list(NIVEL), desde, hasta)
        if df.empty:
            return df.assign(P="", N="", V=0.0)
        mes = pd.to_numeric(df["MES"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
        return df.assign(P=df["AÑO"].astype(int).astype(str) + "-" + mes.astype(int).map("{:02d}".format),
                         N=df["NIVEL_GOBIERNO"].astype(str).str[0], V=pd.to_numeric(df["DEVENGADO"], errors="coerce").fillna(0) / 1000)
    ing = db.leer("ingresos", [depto], list(NIVEL), desde, hasta)
    if not ing.empty:
        mes = pd.to_numeric(ing["MES"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
        ing = ing.assign(P=ing["AÑO"].astype(int).astype(str) + "-" + mes.astype(int).map("{:02d}".format),
                         N=ing["NIVEL_GOBIERNO"].astype(str).str[0], V=pd.to_numeric(ing["RECAUDADO"], errors="coerce").fillna(0) / 1000,
                         CODIGO=ing["CODIGO"].astype(str), K=ing["CONCEPTO"].map(_k))
    d = {"gen": prep("gasto-dev-generica"), "fue": prep("gasto-dev-fuente"), "fun": prep("inv-dev-funcion"), "ifu": prep("inv-dev-fuente"),
         "ing": ing}
    d["_idx"] = _indice(d)
    return d


# columnas que necesita cada base para calcular una celda
_CAMPOS = {"gen": ("COD_GENERICA", "DESGLOSE"), "fue": ("COD_FUENTE",), "ifu": ("COD_FUENTE",), "fun": ("FUNCION",),
           "ing": ("CLASIFICADOR", "CODIGO", "K")}


def _indice(d):
    """{base: {(nivel, mes): [(campos…, V)]}}: cada celda recorre las pocas filas de su nivel y mes en Python puro. Antes
    filtraba la base entera con pandas en cada celda: el Excel de 5 años hacía ~9 000 filtros (20 s en una PC, más de un
    minuto en el servidor, que mientras tanto casi no atendía a nadie más: la página se colgaba)."""
    idx = {}
    for base, campos in _CAMPOS.items():
        x, grupos = d.get(base), {}
        if x is not None and not x.empty:
            cols = [x["N"].astype(str), x["P"].astype(str)] + [x[c].astype(str) for c in campos] + [x["V"].astype(float)]
            for n, p, *resto in zip(*cols):
                grupos.setdefault((n, p), []).append(tuple(resto))
        idx[base] = grupos
    return idx


@functools.lru_cache(maxsize=256)
def _palabra(palabra):
    return re.compile(r"(?:^|\s)" + re.escape(palabra))     # «CANON PETROLERO» no es «SOBRECANON …»


def _valor_ingresos(d, terminos, nivel, p):
    x = d["_idx"]["ing"].get((nivel, p))
    if not x:
        return None
    total = 0.0
    for signo, sel in terminos:
        if sel == "Z":
            continue
        if sel.startswith("C:"):
            cod = sel[2:]
            v = sum(val for cl, c, _, val in x if c == cod and cl not in ("FUENTE", "RUBRO"))
        elif sel == "F:*":
            v = sum(val for cl, _, _, val in x if cl == "FUENTE")
        elif sel.startswith("F:"):
            cod = sel[2:]
            v = sum(val for cl, c, _, val in x if cl == "FUENTE" and c == cod)
        else:                                          # H:padre:palabra -> el hijo del padre que la contiene en su nombre
            _, padre, palabra = sel.split(":", 2)
            pre, guiones, rx = padre + "-", padre.count("-") + 1, _palabra(palabra)
            v = sum(val for cl, c, k, val in x if cl not in ("FUENTE", "RUBRO") and c.startswith(pre) and c.count("-") == guiones
                    and rx.search(k))
        total += signo * v
    return total


def _valor(d, base, filtro, nivel, p):
    if "_idx" not in d:
        d["_idx"] = _indice(d)
    if base == "ing":
        return _valor_ingresos(d, filtro, nivel, p)
    if base == "deu":
        x = d["_idx"]["gen"].get((nivel, p))
        if not x:
            return None                               # sin gasto ese mes: vacío; con gasto y sin deuda: 0
        return sum(v for cod, des, v in x if cod == "7-2-8" and des.upper() == filtro)
    x = d["_idx"][base].get((nivel, p))
    if not x:
        return None
    if filtro is None:
        return sum(f[-1] for f in x)
    if base == "fun":
        return sum(v for fn, v in x if fn[:2] in filtro)
    return sum(f[-1] for f in x if f[0] in filtro)     # gen: COD_GENERICA; fue / ifu: COD_FUENTE


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


def primer_anio(depto):
    """El primer año con gasto por genérica en la página, o None."""
    df = db.leer("gasto-dev-generica", [depto], list(NIVEL), "1990-01", "2100-12")
    return None if df.empty else int(df["AÑO"].astype(int).min())


def ultimo_mes(depto):
    """El último mes con gasto por genérica en la página (AAAA-MM), o None."""
    df = db.leer("gasto-dev-generica", [depto], list(NIVEL), "1990-01", "2100-12")
    if df.empty:
        return None
    mes = pd.to_numeric(df["MES"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    p = (df["AÑO"].astype(int) * 100 + mes).max()
    return f"{p // 100}-{p % 100:02d}"


def armar(depto, desde=None, hasta=None, sector=None):
    """Las hojas de gasto e inversión de la región, mes a mes, con el ESTAD subido al lado para comparar.
    sector: 'gasto' o 'inversion' para solo esas hojas (un invitado puede tener acceso a una sola)."""
    hasta = hasta or ultimo_mes(depto)
    if not hasta:
        return None
    desde = desde or f"{hasta[:4]}-01"
    meses = _meses(desde, hasta)
    hojas, origen = estructura(depto)
    if sector:                                    # las hojas de ingresos van con las de gasto
        hojas = [h for h in hojas if h["tipo"] == sector or (sector == "gasto" and h["tipo"] == "ingresos")]
    d = _datos(depto, desde, hasta)
    salida = []
    for h in hojas:
        tipo, nivel = h["tipo"], h["nivel"]
        conceptos = _conceptos(h)
        filas = []
        for f in h["filas"]:
            c = conceptos.get(f["fila"], {})
            vals = {p: _miles(_valor(d, c["base"], c["filtro"], nivel, p)) for p in meses} if c.get("base") else {}
            estad = (h.get("valores") or {}).get(str(f["fila"]), {})
            filas.append({"fila": f["fila"], "etiqueta": f["etiqueta"], "llena": bool(c.get("base")), "valores": vals,
                          "estad": {p: estad[p] for p in meses if p in estad}, **({"bloque": f["bloque"]} if f.get("bloque") else {})})
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


AZUL = "FF0000FF"
REBASE_2009 = 1.56776      # IPC de Lima base dic. 2021 = 100 -> la base del deflactor del ESTAD (nuevos soles de 2009)
MES_CORTO = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Set.", "Oct.", "Nov.", "Dic."]


def _estilo(tipo):
    """Fuente de una fila como en el ESTAD: total (negrita, subrayado, azul), grupo (negrita) o detalle."""
    if tipo == "total":
        return Font(name="Arial", size=10, bold=True, underline="single", color=AZUL)
    if tipo == "grupo":
        return Font(name="Arial", size=10, bold=True)
    return Font(name="Arial", size=10)


def _tipo_fila(f, filtro):
    if not f["llena"]:
        return "detalle"
    e = re.sub(r"^\d+\s*:\s*", "", _k(f["etiqueta"]))
    if filtro is None or e.startswith(("TOTAL", "INGRESOS DEL GOBIERNO", "INGRESOS DE LOS GOBIERNOS", "INGRESOS POR FUENTE")):
        return "total"
    return "grupo" if e.startswith(("GASTOS CORRIENTES", "GASTOS DE CAPITAL", "SERVICIO DE LA DEUDA", "INGRESOS CORRIENTES",
                                    "INGRESOS DE CAPITAL", "FINANCIAMIENTO", "TRANSFERENCIAS", "D Y T CORRIENTES", "D DE CAPITAL",
                                    "POR PARTICIPACIONES", "DE OTRAS UNIDADES")) else "detalle"


def excel(e, depto=None):
    """El ESTAD de gasto e inversión armado con los datos del scraper del MEF, con el diseño del ESTAD: un bloque de 12
    meses y su total por año, las variaciones del último mes y de enero a ese mes, y (en las hojas de gasto) el mismo
    cuadro en términos reales con el deflactor del IPC de Lima. Los montos van en miles de soles con sus decimales
    (soles / 1000): el formato muestra solo los miles."""
    from openpyxl.styles import Border, Side
    from openpyxl.utils import get_column_letter as L
    from . import ipc
    fino = Side(style="thin")
    t11, t10 = Font(name="Arial", size=11, bold=True, color=AZUL), Font(name="Arial", size=10, color=AZUL)
    t10b = Font(name="Arial", size=10, bold=True, color=AZUL)
    serie_ipc = ipc.serie()
    anios = list(range(int(e["desde"][:4]), int(e["hasta"][:4]) + 1))
    ah, mh = int(e["hasta"][:4]), int(e["hasta"][5:7])
    col_mes = {}                                            # AAAA-MM -> columna
    col_tot = {}
    c = 2
    for a in anios:
        for m in range(1, 13):
            col_mes[f"{a}-{m:02d}"] = c
            c += 1
        col_tot[a] = c
        c += 1
    c_var = c + 1                                           # una columna en blanco y las de variación
    wb = Workbook()
    wb.remove(wb.active)

    def cabecera(ws, r):
        """Fila r: años (y «Total»); fila r+1: meses (y el año del total); a la derecha, las variaciones."""
        for a in anios:
            c0 = col_mes[f"{a}-01"]
            ws.cell(r, c0, a).font = t10
            for m in range(1, 13):
                x = ws.cell(r + 1, c0 + m - 1, MES_CORTO[m - 1])
                x.font, x.alignment = t10, Alignment(horizontal="center")
                x.border = Border(bottom=fino, left=fino if m == 1 else None)
                ws.cell(r, c0 + m - 1).border = Border(top=fino, left=fino if m == 1 else None)
                ws.cell(r, c0 + m - 1).alignment = Alignment(horizontal="centerContinuous")
            for rr, v in ((r, "Total"), (r + 1, a)):
                x = ws.cell(rr, col_tot[a], v)
                x.font, x.alignment = t10, Alignment(horizontal="center")
                x.border = Border(left=fino, right=fino, top=fino if rr == r else None, bottom=fino if rr == r + 1 else None)
        etiquetas = [(f"Var.% {ah}/{ah - 1}", MESES_CORTOS_TXT(mh)), ("", f"Ene.-{MES_CORTO[mh - 1]}"), (ah - 1, f"Ene.-{MES_CORTO[mh - 1]}"),
                     (ah, f"Ene.-{MES_CORTO[mh - 1]}")]
        for k, (arriba, abajo) in enumerate(etiquetas):
            for rr, v in ((r, arriba), (r + 1, abajo)):
                x = ws.cell(rr, c_var + k, v if v != "" else None)
                x.font, x.alignment = t10b, Alignment(horizontal="center")
                x.border = Border(left=fino, right=fino, top=fino if rr == r else None, bottom=fino if rr == r + 1 else None)
        ws.merge_cells(start_row=r, start_column=c_var, end_row=r, end_column=c_var + 1)
        ws.cell(r, 1).border = Border(left=fino, right=fino, top=fino)
        ws.cell(r + 1, 1).border = Border(left=fino, right=fino, bottom=fino)

    def fila_datos(ws, r, etiqueta, tipo, valores, formula=None):
        """valores: {AAAA-MM: número} o formula(col) -> texto de la fórmula del mes."""
        fuente = _estilo(tipo)
        x = ws.cell(r, 1, etiqueta)
        x.font, x.border = fuente, Border(left=fino, right=fino)
        for p, cc in col_mes.items():
            if p > e["hasta"]:
                ws.cell(r, cc).border = Border(left=fino) if p.endswith("-01") else Border()
                continue
            v = formula(cc) if formula else valores.get(p)
            x = ws.cell(r, cc, v)
            x.font, x.number_format = fuente, "#,##0"
            if p.endswith("-01"):
                x.border = Border(left=fino)
        for a, cc in col_tot.items():
            x = ws.cell(r, cc, f"=SUM({L(col_mes[f'{a}-01'])}{r}:{L(col_mes[f'{a}-12'])}{r})")
            x.font, x.number_format, x.border = fuente, "#,##0", Border(left=fino, right=fino)
        actual, previo = L(col_mes[e["hasta"]]), L(col_mes.get(f"{ah - 1}-{mh:02d}", 0)) if f"{ah - 1}-{mh:02d}" in col_mes else None
        ene_a, ene_b = L(col_mes[f"{ah}-01"]), L(col_mes[f"{ah - 1}-01"]) if f"{ah - 1}-01" in col_mes else None
        acum_a = f"SUM({ene_a}{r}:{actual}{r})"
        acum_b = f"SUM({ene_b}{r}:{previo}{r})" if previo else None
        formulas = [f'=IFERROR(({actual}{r}/{previo}{r}-1)*100,"")' if previo else None,
                    f'=IFERROR(({L(c_var + 3)}{r}/{L(c_var + 2)}{r}-1)*100,"")' if previo else None,
                    f"={acum_b}" if acum_b else None, f"={acum_a}"]
        for k, v in enumerate(formulas):
            x = ws.cell(r, c_var + k, v)
            x.font, x.border = fuente, Border(left=fino, right=fino)
            x.number_format, x.alignment = ("#,##0.0" if k < 2 else "#,##0"), Alignment(horizontal="right")

    for h in e["hojas"]:
        ws = wb.create_sheet(h["hoja"][:31])
        ws.sheet_view.showGridLines = False
        tipo_hoja = h["tipo"]
        titulo = h["titulo"] + [""] * 3
        for i in range(3):
            ws.cell(i + 1, 1, titulo[i]).font = t11
        r_cab = 4
        cabecera(ws, r_cab)
        conceptos = _conceptos({"tipo": tipo_hoja, "filas": h["filas"]})
        # el cuadro empieza en la fila 7, como el ESTAD; las filas conservan su orden y sus espacios
        principal = [f for f in h["filas"] if not f.get("bloque")]
        dyt = [f for f in h["filas"] if f.get("bloque") == "dyt"]
        desfase = 7 - min(f["fila"] for f in principal)
        ultima_p = max(f["fila"] for f in principal) + desfase
        fila_de = {f["fila"]: f["fila"] + desfase for f in principal}
        if dyt:                                         # INGRESOS: el detalle de donaciones y transferencias, debajo
            r_dyt = ultima_p + 6
            ws.cell(r_dyt - 1, 1, "DONACIONES Y TRANSFERENCIAS (detalle)").font = t11
            cabecera(ws, r_dyt)
            fila_de.update({f["fila"]: f["fila"] - dyt[0]["fila"] + r_dyt + 3 for f in dyt})
        for f in h["filas"]:
            r = fila_de[f["fila"]]
            filtro = conceptos.get(f["fila"], {}).get("filtro")
            fila_datos(ws, r, f["etiqueta"], _tipo_fila(f, filtro), f["valores"] if f["llena"] else {})
            if not f["llena"]:
                cero = re.search(r"PRIVATIZ|COMPENSACION", _k(f["etiqueta"]))   # el ESTAD los pone en 0 (van en R. determinados)
                total_fuente = next((x for x in h["filas"] if x["llena"] and conceptos.get(x["fila"], {}).get("base") in ("fue", "ifu")
                                     and conceptos.get(x["fila"], {}).get("filtro") is None), None)
                for cc in list(col_mes.values()) + list(col_tot.values()) + [c_var + k for k in range(4)]:
                    ws.cell(r, cc).value = None
                if cero and total_fuente:
                    for p_, cc in col_mes.items():
                        if total_fuente["valores"].get(p_) is not None:
                            ws.cell(r, cc).value = 0
        ultima = max(fila_de.values())
        fuente_txt = ("Fuente: MEF, Consulta Amigable de Ingresos (recaudado)." if tipo_hoja == "ingresos"
                      else "Fuente: MEF, Consulta Amigable (devengado).") + " Elaborado con el scraper de la página."
        for fin in ([ultima_p, ultima] if dyt else [ultima]):
            for cc in range(1, c_var + 4):
                ws.cell(fin + 1, cc).border = Border(top=fino)
            ws.cell(fin + 2, 1, fuente_txt).font = Font(name="Arial", size=10)
            ws.cell(fin + 3, 1, "1 / Preliminar").font = Font(name="Arial", size=10)
        if tipo_hoja == "gasto":                            # el mismo cuadro en términos reales
            r0 = ultima + 6
            ws.cell(r0, 1, f"{e['departamento']}: {titulo[1].split(':', 1)[-1].strip()} (REALES)").font = t11
            ws.cell(r0 + 1, 1, "(Miles de soles de 2009)").font = t11
            r_def = r0 + 1
            for p, cc in col_mes.items():
                if p > e["hasta"] or p not in serie_ipc:
                    continue
                ws.cell(r_def, cc, serie_ipc[p] / 100 * REBASE_2009).number_format = "0.00"
                antes = f"{int(p[:4]) - (p[5:] == '01')}-{12 if p[5:] == '01' else int(p[5:]) - 1:02d}"
                if antes in serie_ipc:
                    ws.cell(r0, cc, (serie_ipc[p] / serie_ipc[antes] - 1) * 100).number_format = "0.00"
            ws.cell(r0, c_var - 1, "Var. % IPC mensual →").font = Font(name="Arial", size=8, italic=True)
            cabecera(ws, r0 + 2)
            for f in h["filas"]:
                r = fila_de[f["fila"]] + (r0 + 3 - 4)        # misma distancia a la cabecera que en el cuadro nominal
                if not f["llena"]:
                    ws.cell(r, 1, f["etiqueta"]).font = _estilo("detalle")
                    ws.cell(r, 1).border = Border(left=fino, right=fino)
                    continue
                filtro = conceptos.get(f["fila"], {}).get("filtro")
                rn = fila_de[f["fila"]]
                fila_datos(ws, r, f["etiqueta"], _tipo_fila(f, filtro), {},
                           formula=lambda cc, rn=rn: f'=IFERROR({L(cc)}{rn}/{L(cc)}${r_def},"")')
            ultima_r = max(fila_de.values()) + (r0 + 3 - 4)
            for cc in range(1, c_var + 4):
                ws.cell(ultima_r + 1, cc).border = Border(top=fino)
            ws.cell(ultima_r + 2, 1, "Deflactado con el IPC de Lima Metropolitana (INEI), llevado a base 2009 = 100.").font = Font(name="Arial", size=10)
        ws.column_dimensions["A"].width = 38
        for cc in col_mes.values():
            ws.column_dimensions[L(cc)].width = 9
        for cc in col_tot.values():
            ws.column_dimensions[L(cc)].width = 12
        ws.column_dimensions[L(c_var - 1)].width = 4.6
        for k, w in enumerate((8, 8, 12, 12)):
            ws.column_dimensions[L(c_var + k)].width = w
        ws.freeze_panes = ws.cell(r_cab + 2, 2)
        # que se abra mostrando el último año
        ws.sheet_view.topLeftCell = "A1"
    dif = diferencias(e)
    ws = wb.create_sheet("Diferencias")
    ws.append(["Hoja", "Fila", "Etiqueta", "Mes", "ESTAD subido", "Página", "Diferencia"])
    for x in dif:
        ws.append([x["hoja"], x["fila"], x["etiqueta"], x["mes"], x["estad"], x["pagina"], x["dif"]])
    if not dif:
        ws.append(["Sin diferencias de más de 1 mil soles con el ESTAD subido" if e["origen"]["subido"]
                   else "No hay un ESTAD subido con qué comparar"])
    nota = wb.create_sheet("Notas")
    for t in [f"Datos: scraper del MEF de la página (Consulta Amigable, devengado), {etiqueta_mes(e['desde'])} a {etiqueta_mes(e['hasta'])}.",
              "Montos en miles de soles con sus decimales (soles / 1000): el formato muestra solo los miles; los totales del año, "
              "las variaciones y el cuadro en reales se calculan con esos decimales.",
              "Gasto: genéricas 5-21 a 5-25 (corriente), 6-24 a 6-27 (capital) y 7-28 (servicio de la deuda). Inversión: genérica 2.6.",
              "Reales: cada mes dividido por el IPC de Lima Metropolitana del mes (INEI, base dic. 2021 = 100) llevado a base 2009 "
              f"(× {REBASE_2009}), como el deflactor del ESTAD. Las variaciones reales no dependen de la base.",
              "Ingresos (hojas INGRESOS G.R. y G.L.): recaudado de la Consulta Amigable de Ingresos del MEF por genérica, subgenérica, "
              "fuente y el detalle de donaciones y transferencias (canon, FONCOMUN, FONCOR, etc.), como los agrupa el ESTAD de la región.",
              "Sin dato: gasto e inversión por fuente antes de 2025 (la página los descarga desde enero de 2025); Fondo de Compensación "
              "Regional y Privatizaciones por fuente (el MEF los incluye en Recursos determinados).",
              f"Orden y nombre de las filas: {'el último ESTAD subido' if e['origen']['subido'] else 'los del ESTAD de la región (vienen con la página)'}."]:
        nota.append([t])
    nota.column_dimensions["A"].width = 140
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def MESES_CORTOS_TXT(m):
    return MES_CORTO[m - 1]


def etiqueta_mes(p):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
    return f"{meses[int(p[5:7]) - 1]} {p[:4]}"
