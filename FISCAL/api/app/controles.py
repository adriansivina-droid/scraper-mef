"""Contraste con lo publicado por el MEF: los CSV de CONTROL del scraper (Fiscal_Scraper.ipynb).

En cada corrida, el scraper consulta además la vista anual de Consulta Amigable (todo el año, sin elegir mes) y la deja
en los CSV de CONTROL junto a la suma de los meses que raspó:
  · CONTROL <Nivel> AAAA … / CONTROL <Bloque> <Nivel> AAAA …  (devengado: DEV_REF_ANUAL = lo publicado por el MEF)
  · CONTROL PIM Funcion AAAA …                              (PIM: PIM_REF_TOTAL = el total de los tres niveles en el MEF)
  · CONTROL PIM Funcion.Municipalidad AAAA …                (PIM de GL: PIM_REF_GL = el PIM de gobiernos locales en el MEF)
Aquí se guarda la referencia del MEF por departamento, nivel, año y código, y `contraste` la compara con lo que la página
tiene en sus bases para ese mismo año (no con lo que trajo una sola corrida). Del año en curso, la vista anual del MEF
incluye lo devengado en el mes abierto: la página va por debajo hasta que ese mes se cierre y se raspe.
"""
import re
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import text

from . import db

NIVEL_DE_CORTO = {"GobNacional": "E", "GobRegional": "R", "Municipalidad": "M"}
NIVELES = {"E": "Gobierno Nacional", "R": "Gobiernos Regionales", "M": "Gobiernos Locales"}
_RE_DEV = re.compile(r"^CONTROL (?:(Generica|Fuente|InvFuente|Deuda) )?(GobNacional|GobRegional|Municipalidad) (\d{4})")
_RE_PIM = re.compile(r"^CONTROL PIM Funcion(?:\.Municipalidad)? (\d{4})")
# qué base de la página corresponde a cada bloque del scraper
BLOQUES = {"Funcion": ("inv-dev-funcion", "DEVENGADO", "Inversión por función"), "InvFuente": ("inv-dev-fuente", "DEVENGADO", "Inversión por fuente"),
           "Generica": ("gasto-dev-generica", "DEVENGADO", "Gasto por genérica"), "Fuente": ("gasto-dev-fuente", "DEVENGADO", "Gasto por fuente"),
           "PIM": ("inv-pim-funcion", "PIM", "PIM por función")}
POR_SECTOR = {"gasto": ["Generica", "Fuente"], "inversion": ["Funcion", "InvFuente", "PIM"]}


def _tabla():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS mef_controles (bloque TEXT, nivel TEXT, anio INTEGER, depto TEXT, codigo TEXT, "
                        "ref DOUBLE PRECISION, fecha TEXT, archivo TEXT)"))


def leer(nombre, df):
    """Un CSV de CONTROL -> filas (bloque, nivel, anio, depto, codigo, ref) o None si no es un control conocido."""
    m, p = _RE_DEV.match(nombre), _RE_PIM.match(nombre)
    depto = lambda: df["DEPARTAMENTO"].astype(str).str.extract(r"^(\d+)")[0].str.zfill(2)
    if p and "Municipalidad" in nombre and "PIM_REF_GL" in df.columns:
        return pd.DataFrame({"bloque": "PIM_M", "nivel": "M", "anio": int(p.group(1)), "depto": depto(),
                             "codigo": df["COD_FUNCION"].astype(str), "ref": pd.to_numeric(df["PIM_REF_GL"], errors="coerce").fillna(0)})
    if p and "Municipalidad" not in nombre and "PIM_REF_TOTAL" in df.columns:
        return pd.DataFrame({"bloque": "PIM", "nivel": "", "anio": int(p.group(1)), "depto": df["DEPARTAMENTO"].astype(str).str.extract(r"^(\d+)")[0].str.zfill(2),
                             "codigo": df["COD_FUNCION"].astype(str), "ref": pd.to_numeric(df["PIM_REF_TOTAL"], errors="coerce").fillna(0)})
    if m and "DEV_REF_ANUAL" in df.columns:
        bloque = m.group(1) or "Funcion"
        if bloque == "Deuda":
            return None                                   # la deuda ya va dentro de la genérica 2.8
        clave = next((c for c in ("COD_FUNCION", "COD_GENERICA", "COD_FUENTE", "CLASIFICACION") if c in df.columns), None)
        return pd.DataFrame({"bloque": bloque, "nivel": NIVEL_DE_CORTO[m.group(2)], "anio": int(m.group(3)),
                             "depto": df["DEPARTAMENTO"].astype(str).str.extract(r"^(\d+)")[0].str.zfill(2),
                             "codigo": df[clave].astype(str) if clave else "", "ref": pd.to_numeric(df["DEV_REF_ANUAL"], errors="coerce").fillna(0)})
    return None


def guardar(partes):
    """partes: [(nombre del archivo, DataFrame de leer)]. Reemplaza lo guardado del mismo bloque, nivel, año y departamento."""
    partes = [(n, d) for n, d in partes if d is not None and not d.empty]
    if not partes:
        return 0
    _tabla()
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = 0
    with db.motor().begin() as cx:
        for nombre, d in partes:
            for (b, n, a, dep), g in d.groupby(["bloque", "nivel", "anio", "depto"]):
                cx.execute(text("DELETE FROM mef_controles WHERE bloque = :b AND nivel = :n AND anio = :a AND depto = :d"),
                           {"b": b, "n": n, "a": int(a), "d": dep})
                g.assign(fecha=ahora, archivo=nombre).to_sql("mef_controles", cx, if_exists="append", index=False)
                total += len(g)
    return total


def _referencias(departamento, bloques):
    _tabla()
    with db.motor().connect() as cx:
        q = text(f"SELECT bloque, nivel, anio, SUM(ref) AS ref, MAX(fecha) AS fecha FROM mef_controles WHERE depto = :d AND bloque IN "
                 f"({', '.join(':b' + str(i) for i in range(len(bloques)))}) GROUP BY bloque, nivel, anio")
        return pd.read_sql(q, cx, params={"d": departamento, **{f"b{i}": b for i, b in enumerate(bloques)}})


def contraste(departamento, sector, hoy=None):
    """Por bloque, nivel y año: lo publicado por el MEF (vista anual, al día de la corrida) contra lo que tiene la página."""
    hoy = hoy or date.today()
    refs = _referencias(departamento, POR_SECTOR[sector])
    filas, orden = [], {b: i for i, b in enumerate(POR_SECTOR[sector])}
    for r in sorted(refs.itertuples(), key=lambda r: (orden[r.bloque], -r.anio, "ERM".find(r.nivel))):
        base, valor, etiqueta = BLOQUES[r.bloque]
        niveles = [r.nivel] if r.nivel else ["E", "R", "M"]
        df = db.leer(base, [departamento], niveles, f"{r.anio}-01", f"{r.anio}-12")
        pagina = float(pd.to_numeric(df[valor], errors="coerce").sum()) if not df.empty else 0.0
        meses = sorted({int(str(x).split(":")[0]) for x in df["MES"]}) if "MES" in df.columns and not df.empty else []
        dif = pagina - float(r.ref)
        tol = max(5.0, 5.0 * max(len(meses), 1))
        en_curso = r.anio == hoy.year and r.bloque != "PIM"
        if abs(dif) <= tol:
            estado = "coincide"
        elif en_curso and dif < 0:
            estado = "mes en curso"                       # el MEF ya suma lo devengado en el mes abierto
        else:
            estado = "revisar"
        filas.append({"bloque": etiqueta, "nivel": NIVELES.get(r.nivel, "Tres niveles"), "anio": int(r.anio), "mef": round(float(r.ref), 2),
                      "pagina": round(pagina, 2), "dif": round(dif, 2), "estado": estado, "fecha": r.fecha,
                      "meses": f"{meses[0]:02d} a {meses[-1]:02d}" if meses else "sin datos"})
    return filas


# ── Control de los tres archivos de los 25 departamentos («MEF · 3 archivos») ──
# archivo -> (bloque y nivel del CONTROL, base de la página, columna del monto, es anual)
ARCHIVOS = {"dev-municipalidad": ("Funcion", "M", "inv-dev-municipalidad", "DEVENGADO", False),
            "pim-funcion": ("PIM", "", "inv-pim-funcion", "PIM", True),
            "pim-municipalidad": ("PIM_M", "M", "inv-pim-municipalidad", "PIM", True)}


FUNCIONES = dict(enumerate(["", "Legislativa", "Relaciones exteriores", "Planeamiento", "Defensa", "Orden público", "Justicia", "Trabajo",
                             "Comercio", "Turismo", "Agropecuaria", "Pesca", "Energía", "Minería", "Industria", "Transporte", "Comunicaciones",
                             "Ambiente", "Saneamiento", "Vivienda", "Salud", "Cultura y deporte", "Educación", "Protección social",
                             "Previsión social", "Deuda pública"]))


def _cod(funcion):
    m = re.match(r"^\s*(\d+)", str(funcion))
    return m.group(1).zfill(2) if m else str(funcion)


def control_archivo(archivo, hoy=None):
    """Por departamento y año: lo publicado por el MEF (vista anual, guardado de los CSV de CONTROL de cada corrida) contra
    lo que tiene la página en la base del archivo, con las funciones que no cuadran."""
    hoy = hoy or date.today()
    bloque, nivel, base_id, valor, anual = ARCHIVOS[archivo]
    _tabla()
    with db.motor().connect() as cx:
        refs = pd.read_sql(text("SELECT depto, anio, codigo, SUM(ref) AS ref, MAX(fecha) AS fecha FROM mef_controles "
                                "WHERE bloque = :b AND nivel = :n GROUP BY depto, anio, codigo"), cx, params={"b": bloque, "n": nivel})
    if refs.empty:
        return []
    refs["codigo"] = refs["codigo"].map(_cod)
    b = db.BASES[base_id]
    filas = []
    for (dep, anio), g in sorted(refs.groupby(["depto", "anio"]), key=lambda x: (-x[0][1], x[0][0])):
        df = db.leer(base_id, [dep], ["E", "R", "M"], f"{anio}-01", f"{anio}-12") if db.existe(b.tabla) else pd.DataFrame()
        montos = pd.to_numeric(df[valor], errors="coerce").fillna(0) if not df.empty else pd.Series(dtype=float)
        pagina = df.assign(_c=df["FUNCION"].map(_cod), _v=montos).groupby("_c")["_v"].sum() if not df.empty else pd.Series(dtype=float)
        meses = [] if anual or df.empty else sorted({int(str(x).split(":")[0]) for x in df["MES"]})
        ref = g.groupby("codigo")["ref"].sum()
        mef, pag = float(ref.sum()), float(pagina.sum())
        dif = pag - mef
        tol = max(5.0, 5.0 * max(len(meses), 1))
        en_curso = not anual and int(anio) == hoy.year
        estado = "coincide" if abs(dif) <= tol else ("mes en curso" if en_curso and dif < 0 else "sin datos" if df.empty else "revisar")
        funciones = []
        if estado != "coincide":
            for c in sorted(set(ref.index) | set(pagina.index)):
                d = float(pagina.get(c, 0.0)) - float(ref.get(c, 0.0))
                if abs(d) > max(3.0, 3.0 * max(len(meses), 1)):
                    funciones.append({"funcion": f"{c} {FUNCIONES.get(int(c), '')}".strip() if c.isdigit() else c, "mef": round(float(ref.get(c, 0.0)), 2), "pagina": round(float(pagina.get(c, 0.0)), 2), "dif": round(d, 2)})
        filas.append({"depto": dep, "anio": int(anio), "mef": round(mef, 2), "pagina": round(pag, 2), "dif": round(dif, 2), "estado": estado,
                      "fecha": g["fecha"].max(), "meses": (f"{meses[0]:02d} a {meses[-1]:02d}" if meses else ("anual" if anual and not df.empty else "sin datos")),
                      "funciones": funciones})
    return filas
