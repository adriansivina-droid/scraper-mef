"""Importaciones por la aduana de Iquitos desde la base mensual (M_AAAAMM.xlsx): el flujo de ANUAL_PRO - IMPORTACIONES.

  1. Se sube la base del mes tal como llega (aduana, ruc, partida, fob, flete, seguro, kilos, pais_adqui, cuode, periodo,
     cuod1, daduana). No hay limpieza: entran todas las filas de la aduana de Iquitos (226).
  2. Cada fila se completa como la hoja ORIGEN del proyecto:
       · TIPO, CATEGORÍA y DESC. CUODE: la partida manda si su FUENTE es «MANUAL» y tiene tipo; si no, el CUODE de la
         fila (tabla CUODE); si no hay CUODE, la partida; si nada, «SIN CUODE» (se pide clasificar);
       · CIF = FOB + flete + seguro; EMPRESA por RUC (EMPRESAS); PRODUCTO = el de la partida, corregido con PROD_UNICOS;
       · PAÍS y CONTINENTE por código (PAISES).
  3. El ESTAD propuesto (Cuadro N° 16) suma por categoría el FOB redondeado a miles fila por fila, como el CUADRO 16.
Subir ANUAL_PRO - IMPORTACIONES (.xlsm o .xlsx: hojas ORIGEN, PARTIDAS y UNICOS) carga sus diccionarios y su ORIGEN.
"""
import io
import re

import pandas as pd
from openpyxl import load_workbook
from sqlalchemy import text

from . import db
from .sunat_expo import MESES, Sugeridor, _clave, _minus, _pct, _r0, _r1, _y

ADUANA_IQUITOS = "226"
CRUDAS = ["aduana", "ruc", "partida", "fob", "flete", "seguro", "kilos", "pais_adqui", "cuode", "periodo"]
COLUMNAS = ["AÑO", "MES", "DEPARTAMENTO", "ADUANA", "RUC", "EMPRESA", "PARTIDA", "PRODUCTO", "COD_CUODE", "TIPO", "CATEGORIA",
            "DESC_CUODE", "RUBRO_ESTAD", "COD_PAIS", "PAIS", "CONTINENTE", "KILOS", "FLETE", "SEGURO", "CIF", "ESTADO", "MOTIVO",
            "FOB_USD", "FOB"]
# categoría (CUODE) -> código de la fila del Cuadro N° 16 del ESTAD
CODIGO_FILA = {"bienes de consumo no duradero": "100", "bienes de consumo duraderos": "200", "otros bienes de consumo diversos": "010",
               "combustibles, lubricantes y conexos": "300", "materias primas para la agricultura": "400",
               "materias primas para la industria": "500", "materiales de construccion": "600", "para la agricultura": "700",
               "para la industria": "800", "equipo de transporte": "900"}
# cómo se nombra cada categoría en el texto de la síntesis
EN_TEXTO = {"bienes de consumo no duradero": "bienes de consumo no duradero", "bienes de consumo duraderos": "bienes de consumo duradero",
            "otros bienes de consumo diversos": "otros bienes de consumo", "combustibles, lubricantes y conexos": "combustibles y lubricantes",
            "materias primas para la agricultura": "materias primas e insumos para la agricultura",
            "materias primas para la industria": "materias primas e insumos para la industria", "materiales de construccion": "materiales de construcción",
            "para la agricultura": "bienes de capital para la agricultura", "para la industria": "bienes de capital para la industria",
            "equipo de transporte": "bienes de capital para equipos de transporte"}


def en_texto(categoria):
    return EN_TEXTO.get(_clave(categoria), _minus(str(categoria)))


TABLAS = {"partidas": ["PARTIDA", "TIPO", "CATEGORIA", "DESC_CUODE", "PRODUCTO", "FUENTE"],
          "cuode": ["CUODE", "TIPO", "CATEGORIA", "DESC_CUODE"],
          "empresas": ["RUC", "RAZON_SOCIAL", "ESTADO_SUNAT", "CONDICION"],
          "unicos": ["PRODUCTO_ORIGINAL", "PRODUCTO_CORREGIDO"],
          "paises": ["COD", "PAIS", "CONTINENTE"]}


def _tabla(nombre):
    return f"impo_dic_{nombre}"


def leer_tabla(nombre):
    if not db.existe(_tabla(nombre)):
        return pd.DataFrame(columns=TABLAS[nombre])
    with db.motor().connect() as cx:
        df = pd.read_sql(text(f'SELECT * FROM "{_tabla(nombre)}"'), cx)
    return df.reindex(columns=TABLAS[nombre])


def guardar_tabla(nombre, df):
    df = df.reindex(columns=TABLAS[nombre]).astype(object).where(lambda x: x.notna(), None)
    with db.motor().begin() as cx:
        cx.execute(text(f'DROP TABLE IF EXISTS "{_tabla(nombre)}"'))
        df.to_sql(_tabla(nombre), cx, index=False, chunksize=5000)
    return len(df)


def _txt(s):
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).replace({"nan": None, "None": None, "": None})


# ── Reconocer y leer ──
def es_anual_pro(ruta):
    try:
        wb = load_workbook(ruta, read_only=True)
        nombres = set(wb.sheetnames)
        wb.close()
        return {"ORIGEN", "PARTIDAS", "UNICOS"} <= nombres
    except Exception:
        return False


def es_base(ruta):
    try:
        cab = {str(c).strip().lower() for c in pd.read_excel(ruta, sheet_name=0, nrows=0).columns}
        return {"ruc", "partida", "fob", "flete", "seguro", "cuode", "periodo"} <= cab
    except Exception:
        return False


def cargar_diccionarios(ruta):
    """PARTIDAS (con la tabla CUODE a la derecha) y UNICOS (PAISES, EMPRESAS, PROD_UNICOS lado a lado)."""
    avisos = []
    p = pd.read_excel(ruta, sheet_name="PARTIDAS", dtype=str)
    p.columns = [str(c).strip() for c in p.columns]
    part = pd.DataFrame({"PARTIDA": _txt(p["PARTIDA_TEXTO"]).str.zfill(10), "TIPO": p.get("TIPO"), "CATEGORIA": p.get("CATEGORIA"),
                         "DESC_CUODE": p.get("DESC. CUODE"), "PRODUCTO": p.get("PRODUCTO"), "FUENTE": p.get("FUENTE")}).dropna(subset=["PARTIDA"])
    guardar_tabla("partidas", part)
    avisos.append(f"Partidas: {len(part)}.")
    # tabla CUODE: columnas «Cuode», «TIPO.1», «CATEGORÍA», «DESC. CUODE.1» (a la derecha de la tabla PARTIDA)
    if "Cuode" in p.columns:
        cu = pd.DataFrame({"CUODE": _txt(p["Cuode"]), "TIPO": p.get("TIPO.1"), "CATEGORIA": p.get("CATEGORÍA"), "DESC_CUODE": p.get("DESC. CUODE.1")})
        cu = cu.dropna(subset=["CUODE", "CATEGORIA"])
        cu["CUODE"] = cu["CUODE"].str.lstrip("0").replace("", "0")
        guardar_tabla("cuode", cu.drop_duplicates("CUODE"))
        avisos.append(f"CUODE: {cu['CUODE'].nunique()} códigos.")
    u = pd.read_excel(ruta, sheet_name="UNICOS", dtype=str)
    cab = [str(c).strip().split(".")[0] for c in u.columns]
    def col(nombre, desde=0):
        return u.iloc[:, cab.index(nombre, desde)] if nombre in cab[desde:] else None
    if "CÓDIGO" in cab:
        i = cab.index("CÓDIGO")
        pa = pd.DataFrame({"COD": _txt(u.iloc[:, i + 1]).str.zfill(3), "PAIS": u.iloc[:, i + 2], "CONTINENTE": u.iloc[:, i + 3]}).dropna(subset=["COD"])
        pa["COD"] = pa["COD"].str.lstrip("0").replace("", "0")
        guardar_tabla("paises", pa)
        avisos.append(f"Países: {len(pa)}.")
    if "RUC" in cab:
        emp = pd.DataFrame({"RUC": _txt(col("RUC")), "RAZON_SOCIAL": col("RAZÓN SOCIAL")}).dropna(subset=["RUC"])
        viejo = leer_tabla("empresas")
        guardar_tabla("empresas", pd.concat([viejo[~viejo["RUC"].astype(str).isin(emp["RUC"])], emp], ignore_index=True))
        avisos.append(f"Empresas: {len(emp)} RUC.")
    if "PRODUCTO_ORIGINAL" in cab:
        un = pd.DataFrame({"PRODUCTO_ORIGINAL": col("PRODUCTO_ORIGINAL"), "PRODUCTO_CORREGIDO": col("PRODUCTO_CORREGIDO")}).dropna(subset=["PRODUCTO_ORIGINAL"])
        guardar_tabla("unicos", un)
        avisos.append(f"Productos únicos: {len(un)}.")
    return avisos


def leer_origen(ruta):
    d = pd.read_excel(ruta, sheet_name="ORIGEN", header=4, dtype=str)
    d.columns = [str(c).strip().lower() for c in d.columns]
    d = d.rename(columns={"cod_pais": "pais_adqui", "fenum": "periodo"})
    return d[[c for c in CRUDAS if c in d.columns]]


def leer_crudo(ruta):
    d = pd.read_excel(ruta, sheet_name=0, dtype=str)
    d.columns = [str(c).strip().lower() for c in d.columns]
    return d[[c for c in CRUDAS if c in d.columns]]


# ── Procesar ──
def estructura_estad():
    from .catalogo import BASES
    t = BASES["impo-estad"].tabla
    if not db.existe(t):
        return []
    with db.motor().connect() as cx:
        p = cx.execute(text(f'SELECT MAX(_anio * 100 + _mes) FROM "{t}"')).scalar()
        if p is None:
            return []
        df = pd.read_sql(text(f'SELECT "ORDEN", "NIVEL", "TIPO", "GRUPO", "RUBRO" FROM "{t}" WHERE (_anio * 100 + _mes) = :p'), cx, params={"p": int(p)})
    df = df.drop_duplicates("ORDEN").sort_values("ORDEN")
    return [{"orden": int(r.ORDEN), "nivel": r.NIVEL, "tipo": r.TIPO or "", "grupo": r.GRUPO or "", "rubro": r.RUBRO} for r in df.itertuples()]


def _fila_estad(est, categoria):
    cod = CODIGO_FILA.get(_clave(categoria))
    if not cod:
        return None
    f = next((f for f in est if f["nivel"] == "producto" and f"({cod})" in f["rubro"]), None)
    return f["rubro"] if f else None


def procesar(crudo):
    if "ruc" not in crudo.columns:                    # filas de la base: a columnas crudas
        crudo = pd.DataFrame({"aduana": crudo["ADUANA"], "ruc": crudo["RUC"], "partida": crudo["PARTIDA"], "fob": crudo["FOB_USD"],
                              "flete": crudo["FLETE"], "seguro": crudo["SEGURO"], "kilos": crudo["KILOS"], "pais_adqui": crudo["COD_PAIS"],
                              "cuode": crudo["COD_CUODE"], "periodo": crudo["AÑO"].astype(int).astype(str) + crudo["MES"].astype(int).map("{:02d}".format)})
    d = crudo[crudo["ruc"].notna() & crudo["fob"].notna()].copy()
    d["periodo"] = _txt(d["periodo"])
    d = d[d["periodo"].str.fullmatch(r"\d{6}", na=False)]
    num = lambda c: pd.to_numeric(d.get(c), errors="coerce").fillna(0.0)
    out = pd.DataFrame({"AÑO": d["periodo"].str[:4].astype(int), "MES": d["periodo"].str[4:].astype(int), "DEPARTAMENTO": "LORETO",
                        "ADUANA": _txt(d["aduana"]), "RUC": _txt(d["ruc"]), "PARTIDA": _txt(d["partida"]).str.zfill(10),
                        "COD_CUODE": _txt(d["cuode"]).str.lstrip("0"), "COD_PAIS": _txt(d["pais_adqui"]).str.lstrip("0"),
                        "KILOS": num("kilos"), "FLETE": num("flete"), "SEGURO": num("seguro"), "FOB_USD": num("fob")})
    out["CIF"] = out["FOB_USD"] + out["FLETE"] + out["SEGURO"]
    part = leer_tabla("partidas").drop_duplicates("PARTIDA").set_index("PARTIDA")
    cuode = leer_tabla("cuode").drop_duplicates("CUODE").set_index("CUODE")
    emp = leer_tabla("empresas").assign(RUC=lambda x: x["RUC"].astype(str)).drop_duplicates("RUC", keep="last").set_index("RUC")
    unicos = leer_tabla("unicos").drop_duplicates("PRODUCTO_ORIGINAL").set_index("PRODUCTO_ORIGINAL")["PRODUCTO_CORREGIDO"]
    paises = leer_tabla("paises").drop_duplicates("COD").set_index("COD")
    est = estructura_estad()
    m = lambda serie, tabla, col: serie.map(tabla[col]) if len(tabla) else pd.Series(None, index=serie.index)
    fuente, p_tipo = m(out["PARTIDA"], part, "FUENTE").fillna(""), m(out["PARTIDA"], part, "TIPO")
    manual = fuente.str.upper().str.startswith("MANUAL") & p_tipo.notna()
    for col in ("TIPO", "CATEGORIA", "DESC_CUODE"):
        c, p_ = m(out["COD_CUODE"], cuode, col), m(out["PARTIDA"], part, col)
        out[col] = p_.where(manual, c.where(c.notna(), p_))
    out["EMPRESA"] = m(out["RUC"], emp, "RAZON_SOCIAL").fillna("SIN RAZÓN SOCIAL")
    original = m(out["PARTIDA"], part, "PRODUCTO")
    corregido = original.map(unicos) if len(unicos) else pd.Series(None, index=out.index)
    out["PRODUCTO"] = corregido.where(corregido.notna(), original).fillna("SIN DESCRIPCIÓN")
    out["PAIS"] = m(out["COD_PAIS"], paises, "PAIS").fillna("SIN PAÍS")
    out["CONTINENTE"] = m(out["COD_PAIS"], paises, "CONTINENTE").fillna("SIN PAÍS")
    out["FOB"] = [_r0(v / 1000) for v in out["FOB_USD"]]
    estado, motivo, rubro = [], [], []
    for adu, cat in zip(out["ADUANA"], out["CATEGORIA"]):
        r = _fila_estad(est, cat) if est else None
        if adu != ADUANA_IQUITOS:
            estado.append("otra aduana"); motivo.append(f"Aduana {adu}: el cuadro es solo de la aduana de Iquitos"); r = None
        elif cat is None or (isinstance(cat, float) and pd.isna(cat)):
            estado.append("clasificar"); motivo.append("Sin CUODE ni tipo en la partida")
        else:
            estado.append("ok"); motivo.append("")
        rubro.append(r)
    out["ESTADO"], out["MOTIVO"], out["RUBRO_ESTAD"] = estado, motivo, rubro
    out["_anio"], out["_mes"], out["_depto"], out["_nivel"] = out["AÑO"], out["MES"], "16", ""
    return out[COLUMNAS + ["_anio", "_mes", "_depto", "_nivel"]].reset_index(drop=True)


def leer(archivos):
    partes, avisos = [], []
    for n, ruta, tipo in archivos:
        if tipo == "anual":
            avisos += [f"{ruta.name}: {a}" for a in cargar_diccionarios(ruta)]
            crudo = leer_origen(ruta)
        else:
            crudo = leer_crudo(ruta)
        df = procesar(crudo)
        if df.empty:
            continue
        per = sorted(set(zip(df["AÑO"], df["MES"])))
        cuenta = df.groupby("ESTADO")["FOB"].agg(["count", "sum"])
        avisos.append(f"{ruta.name}: importaciones {per[0][0]}-{per[0][1]:02d} a {per[-1][0]}-{per[-1][1]:02d}, " +
                      ", ".join(f"{k} {int(v['count'])} filas ({v['sum']:,.0f} mil US$)".replace(",", " ") for k, v in cuenta.iterrows()) + ".")
        partes.append(df.assign(_archivo=n))
    return ({"impo-base": pd.concat(partes, ignore_index=True)} if partes else {}), avisos


def reprocesar():
    base = db.leer_todo("impo-base")
    if base is None or base.empty:
        return 0
    df = procesar(base)
    from .catalogo import BASES, INTERNAS
    b = BASES["impo-base"]
    with db.motor().begin() as cx:                    # una sola transacción
        cx.execute(text(f'DELETE FROM "{b.tabla}"'))
        df[b.columnas + INTERNAS].to_sql(b.tabla, cx, if_exists="append", index=False, chunksize=5000)
    return len(df)


# ── Revisión, ESTAD propuesto, resumen ──
def _base(desde="1990-01", hasta="2100-12"):
    return db.leer("impo-base", ["16"], [], desde, hasta)


def propuesta(anio, mes, df=None):
    est = estructura_estad()
    if not est:
        return None
    df = _base(f"{anio}-{mes:02d}", f"{anio}-{mes:02d}") if df is None else df
    directo = df[df["ESTADO"] == "ok"].groupby("RUBRO_ESTAD")["FOB"].sum().to_dict()
    valores = {f["orden"]: (directo.get(f["rubro"], 0.0) if f["nivel"] == "producto" else 0.0) for f in est}
    for f in est:
        if f["nivel"] == "tipo":
            valores[f["orden"]] = sum(valores[h["orden"]] for h in est if h["nivel"] == "producto" and h["tipo"] == f["rubro"])
    for f in est:
        if f["nivel"] == "total":
            valores[f["orden"]] = sum(valores[t["orden"]] for t in est if t["nivel"] == "tipo")
    cargado = db.leer("impo-estad", ["16"], [], f"{anio}-{mes:02d}", f"{anio}-{mes:02d}")
    car = dict(zip(cargado["RUBRO"], cargado["FOB"])) if not cargado.empty else {}
    filas = [{**f, "sunat": valores[f["orden"]], "estad": None if f["rubro"] not in car else float(car[f["rubro"]]),
              "dif": None if f["rubro"] not in car else round(valores[f["orden"]] - float(car[f["rubro"]]), 1)} for f in est]
    return {"filas": filas, "hay_estad": bool(car)}


def pasar_al_estad(anio, mes):
    p = propuesta(anio, mes)
    if p is None:
        raise ValueError("No hay estructura del Cuadro N° 16: falta el ESTAD de importaciones de Loreto.")
    df = pd.DataFrame([{"AÑO": anio, "MES": mes, "DEPARTAMENTO": "LORETO", "ORDEN": f["orden"], "NIVEL": f["nivel"], "TIPO": f["tipo"],
                        "GRUPO": f["grupo"], "RUBRO": f["rubro"], "FOB": float(f["sunat"])} for f in p["filas"]])
    return db.guardar("impo-estad", df.assign(_anio=anio, _mes=mes, _depto="16", _nivel=""))


def revision(periodo=None):
    df = _base()
    if df.empty:
        return None
    df["AÑO"], df["MES"] = df["AÑO"].astype(int), df["MES"].astype(int)
    meses = sorted({f"{a}-{m:02d}" for a, m in zip(df["AÑO"], df["MES"])})
    periodo = periodo if periodo in meses else meses[-1]
    a, m = int(periodo[:4]), int(periodo[5:7])
    mes = df[(df["AÑO"] == a) & (df["MES"] == m)]
    estados = mes.groupby("ESTADO")["FOB"].agg(["count", "sum"]).reset_index().rename(columns={"count": "filas", "sum": "fob"}).to_dict("records")
    sin_rs = [{"ruc": r, "fob": float(g["FOB"].sum()), "filas": len(g), "productos": g["PRODUCTO"].value_counts().index[:3].tolist()}
              for r, g in df[df["EMPRESA"] == "SIN RAZÓN SOCIAL"].groupby("RUC")]
    falta = df[(df["ESTADO"] == "clasificar") | (df["PRODUCTO"] == "SIN DESCRIPCIÓN")]
    partidas = [{"partida": p, "fob": float(g["FOB"].sum()), "filas": len(g), "cuode": g["COD_CUODE"].iloc[0], "producto": g["PRODUCTO"].iloc[0],
                 "categoria": g["CATEGORIA"].iloc[0] if g["CATEGORIA"].notna().any() else None} for p, g in falta.groupby("PARTIDA")]
    cu = leer_tabla("cuode")
    return {"periodo": periodo, "meses": meses, "estados": estados, "empresas": sorted(sin_rs, key=lambda x: -x["fob"]),
            "partidas": sorted(partidas, key=lambda x: -x["fob"]), "propuesta": propuesta(a, m, mes), "nombres": nombres_sin_corregir(mes),
            "categorias": sorted({(str(t), str(c)) for t, c in cu[["TIPO", "CATEGORIA"]].dropna().itertuples(index=False)})}


def nombres_sin_corregir(mes):
    """Partidas del mes cuyo nombre es aún el texto del arancel (no está en PROD_UNICOS), con un nombre común sugerido."""
    part = leer_tabla("partidas").drop_duplicates("PARTIDA").set_index("PARTIDA")["PRODUCTO"]
    unicos = leer_tabla("unicos").drop_duplicates("PRODUCTO_ORIGINAL").set_index("PRODUCTO_ORIGINAL")["PRODUCTO_CORREGIDO"]
    ok = mes[mes["ESTADO"] == "ok"]
    sug = Sugeridor(unicos)
    salida = []
    for partida, g in ok.groupby("PARTIDA"):
        original = part.get(partida)
        if not isinstance(original, str) or original in unicos.index:
            continue
        n, p = sug.sugerir(original)
        salida.append({"partida": partida, "original": original, "fob": float(g["FOB"].sum()), "categoria": g["CATEGORIA"].iloc[0],
                       "sugerido": n if p >= 0.4 else None})
    return sorted(salida, key=lambda x: -x["fob"])


def asignar_nombres(filas):
    """filas: [{original, nombre}] -> PROD_UNICOS (texto del arancel -> nombre común)."""
    un = leer_tabla("unicos")
    nuevas = pd.DataFrame([{"PRODUCTO_ORIGINAL": f["original"], "PRODUCTO_CORREGIDO": str(f["nombre"]).strip()}
                           for f in filas if f.get("original") and str(f.get("nombre") or "").strip()])
    if len(nuevas):
        guardar_tabla("unicos", pd.concat([un[~un["PRODUCTO_ORIGINAL"].isin(nuevas["PRODUCTO_ORIGINAL"])], nuevas], ignore_index=True))
    return len(nuevas)


HOJAS_DICCIONARIO = {"PARTIDAS": "partidas", "CUODE": "cuode", "PROD_UNICOS": "unicos", "EMPRESAS": "empresas", "PAISES": "paises"}
LEEME_IMPO = "Diccionarios de importaciones (página del Departamento de Estudios Económicos)"


def diccionarios_excel():
    from .sunat_expo import diccionarios_excel as hacer
    return hacer(LEEME_IMPO, HOJAS_DICCIONARIO, leer_tabla)


def es_diccionario(ruta):
    from .sunat_expo import es_diccionario as es
    return es(ruta, LEEME_IMPO)


def cargar_diccionario_excel(ruta):
    from .sunat_expo import cargar_diccionario_excel as cargar
    return cargar(ruta, HOJAS_DICCIONARIO, guardar_tabla, TABLAS)


def actualizar_empresas(filas):
    emp = leer_tabla("empresas")
    emp["RUC"] = emp["RUC"].astype(str)
    for f in filas:
        ruc = re.sub(r"\D", "", str(f.get("RUC") or ""))
        if len(ruc) != 11 or not str(f.get("RAZON_SOCIAL") or "").strip():
            continue
        emp = pd.concat([emp[emp["RUC"] != ruc], pd.DataFrame([{"RUC": ruc, "RAZON_SOCIAL": str(f["RAZON_SOCIAL"]).strip()}])], ignore_index=True)
    guardar_tabla("empresas", emp)


def actualizar_partidas(filas):
    """Clasificación manual de una partida (FUENTE = MANUAL: gana al CUODE de la fila)."""
    part, cu = leer_tabla("partidas"), leer_tabla("cuode")
    for f in filas:
        k = re.sub(r"\D", "", str(f.get("PARTIDA") or "")).zfill(10)
        if k == "0" * 10:
            continue
        previa = part[part["PARTIDA"] == k]
        fila = {c: (previa[c].iloc[0] if len(previa) else None) for c in TABLAS["partidas"]}
        fila["PARTIDA"] = k
        if f.get("CATEGORIA"):
            c = cu[cu["CATEGORIA"] == f["CATEGORIA"]]
            fila.update(TIPO=c["TIPO"].iloc[0] if len(c) else fila["TIPO"], CATEGORIA=f["CATEGORIA"], FUENTE="MANUAL")
        if f.get("PRODUCTO"):
            fila["PRODUCTO"] = str(f["PRODUCTO"]).strip()
        part = pd.concat([part[part["PARTIDA"] != k], pd.DataFrame([fila])], ignore_index=True)
    guardar_tabla("partidas", part)


def pendientes_ruc():
    base = db.leer_todo("impo-base")
    return sorted(set(base.loc[base["EMPRESA"] == "SIN RAZÓN SOCIAL", "RUC"].astype(str))) if base is not None else []


def guardar_padron(encontrados):
    emp = leer_tabla("empresas")
    emp["RUC"] = emp["RUC"].astype(str)
    nuevos = encontrados[encontrados["RUC"].isin(pendientes_ruc())]
    emp = pd.concat([emp[~emp["RUC"].isin(nuevos["RUC"])], nuevos.rename(columns={"ESTADO": "ESTADO_SUNAT"})], ignore_index=True)
    guardar_tabla("empresas", emp)
    return len(nuevos)


def _top(d, campo, n=5):
    tot = d["FOB_USD"].sum()
    g = d.groupby(campo)["FOB_USD"].sum().sort_values(ascending=False)
    salida = []
    for k, v in g.head(n).items():
        if v <= 0:
            continue
        prods = d[d[campo] == k].groupby("PRODUCTO")["FOB_USD"].sum().sort_values(ascending=False).head(3)
        salida.append({"nombre": k, "fob": float(v) / 1000, "pct": _r1(v / tot * 100) if tot else None, "productos": [p for p, x in prods.items() if x > 0]})
    return salida


def _millones(v):
    return _pct(_r1(v / 1e6))


def resumen(periodo=None):
    df = _base()
    if df.empty:
        return None
    df["AÑO"], df["MES"] = df["AÑO"].astype(int), df["MES"].astype(int)
    ok = df[df["ESTADO"] == "ok"]
    meses = sorted({f"{a}-{m:02d}" for a, m in zip(df["AÑO"], df["MES"])})
    periodo = periodo if periodo in meses else meses[-1]
    a, m = int(periodo[:4]), int(periodo[5:7])
    sel = {"mes": ok[(ok["AÑO"] == a) & (ok["MES"] == m)], "acumulado": ok[(ok["AÑO"] == a) & (ok["MES"] <= m)]}
    ant = {"mes": ok[(ok["AÑO"] == a - 1) & (ok["MES"] == m)], "acumulado": ok[(ok["AÑO"] == a - 1) & (ok["MES"] <= m)]}
    hay_ant = bool((df["AÑO"] == a - 1).any())
    salida = {"periodo": periodo, "meses": meses, "nombre_mes": MESES[m - 1], "anio": a, "hay_anterior": hay_ant, "flujo": "impo"}
    for k, d in sel.items():
        tot, tot_b = d["FOB_USD"].sum() / 1000, ant[k]["FOB_USD"].sum() / 1000
        salida[k] = {"total": tot, "anterior": tot_b if hay_ant else None, "var": _r1((tot / tot_b - 1) * 100) if hay_ant and tot_b else None,
                     "productos": _top(d, "PRODUCTO", 8), "destinos": _top(d, "PAIS"), "continentes": _top(d, "CONTINENTE", 6),
                     "aduanas": _top(d, "CATEGORIA", 10), "empresas": _top(d, "EMPRESA")}
    salida["destacados"] = _destacados(sel, ant, hay_ant, a, m)
    salida["textos"] = _textos(sel, ant, hay_ant, a, m)
    return salida


def _destacados(sel, ant, hay_ant, a, m):
    d, da, nombre = sel["mes"], sel["acumulado"], MESES[m - 1]
    tot = d["FOB_USD"].sum()
    if tot <= 0:
        return [{"titulo": f"{nombre.capitalize()} {a}", "valor": "Sin importaciones", "detalle": "la aduana de Iquitos no registró importaciones en el mes"}]
    prod = d.groupby("PRODUCTO")["FOB_USD"].sum().sort_values(ascending=False)
    pais = d.groupby("PAIS")["FOB_USD"].sum().sort_values(ascending=False)
    cat = d.groupby("CATEGORIA")["FOB_USD"].sum().sort_values(ascending=False)
    salida = [{"titulo": "Principal producto del mes", "valor": prod.index[0], "detalle": f"{_pct(_r1(prod.iloc[0] / tot * 100))} % de lo importado (US$ {_millones(prod.iloc[0])} millones)"},
              {"titulo": "Principal origen", "valor": pais.index[0], "detalle": f"{_pct(_r1(pais.iloc[0] / tot * 100))} % de las importaciones del mes"},
              {"titulo": "Uso o destino principal", "valor": cat.index[0], "detalle": f"{_pct(_r1(cat.iloc[0] / tot * 100))} % del valor del mes"},
              {"titulo": "Países de origen", "valor": f"{d['PAIS'].nunique()}", "detalle": f"en {nombre}; {da['PAIS'].nunique()} en lo que va del año"},
              {"titulo": "Empresas importadoras", "valor": f"{d['RUC'].nunique()}", "detalle": f"en {nombre}; {da['RUC'].nunique()} en lo que va del año"}]
    if hay_ant and ant["acumulado"]["FOB_USD"].sum() > 0:
        v = _r1((da["FOB_USD"].sum() / ant["acumulado"]["FOB_USD"].sum() - 1) * 100)
        salida.append({"titulo": f"Enero-{nombre} vs. año anterior", "valor": f"{_pct(v)} %", "detalle": f"US$ {_millones(da['FOB_USD'].sum())} millones frente a {_millones(ant['acumulado']['FOB_USD'].sum())}"})
    return salida


def _textos(sel, ant, hay_ant, a, m):
    """Como la síntesis: valor del mes, origen, frente al mismo mes del año anterior, y en qué se compró; luego el acumulado."""
    d, nombre = sel["mes"], MESES[m - 1]
    tot, tot_b = d["FOB_USD"].sum(), ant["mes"]["FOB_USD"].sum()
    textos = []
    if tot > 0:
        paises = d.groupby("PAIS")["FOB_USD"].sum().sort_values(ascending=False)
        origen = f"provenientes de {paises.index[0]}" if len(paises) == 1 else f"provenientes principalmente de {_y(list(paises.index[:2]))}"
        if not hay_ant:
            frente = ""
        elif tot_b <= 0:
            frente = ", frente a un valor nulo registrado en similar mes del año anterior"
        else:
            v = _r1((tot / tot_b - 1) * 100)
            frente = f", {'superior' if v >= 0 else 'inferior'} en {_pct(abs(v))} por ciento respecto a similar mes del año anterior"
        cats = d.groupby(["TIPO", "CATEGORIA"])["FOB_USD"].sum().sort_values(ascending=False).head(2)
        partes = []
        for (tipo, cat), v in cats.items():
            prods = d[d["CATEGORIA"] == cat].groupby("PRODUCTO")["FOB_USD"].sum().sort_values(ascending=False).head(2)
            partes.append(f"{en_texto(cat)} ({_y([_minus(p) for p in prods.index])}) por USD {_millones(v)} millones")
        textos.append(f"Las importaciones por la aduana de Iquitos fueron de USD {_millones(tot)} millones en {nombre} de {a}, {origen}{frente}. "
                      f"Las compras correspondieron principalmente a {_y(partes)}.")
    else:
        textos.append(f"En {nombre} de {a} no se registraron importaciones por la aduana de Iquitos.")
    if m > 1:
        acu, acu_b = sel["acumulado"]["FOB_USD"].sum(), ant["acumulado"]["FOB_USD"].sum()
        if hay_ant and acu_b > 0:
            v = _r1((acu / acu_b - 1) * 100)
            dif = (sel["acumulado"].groupby("CATEGORIA")["FOB_USD"].sum().sub(ant["acumulado"].groupby("CATEGORIA")["FOB_USD"].sum(), fill_value=0)).sort_values()
            motor = dif.index[0] if v < 0 else dif.index[-1]
            textos.append(f"En el periodo enero-{nombre}, las importaciones acumularon USD {_millones(acu)} millones, lo que representa "
                          f"{'una contracción' if v < 0 else 'un crecimiento'} de {_pct(abs(v))} por ciento respecto a similar periodo del año anterior, "
                          f"sustentad{'a' if v < 0 else 'o'} principalmente por las {'menores' if v < 0 else 'mayores'} adquisiciones de {en_texto(motor)}.")
        else:
            textos.append(f"En el periodo enero-{nombre}, las importaciones acumularon USD {_millones(acu)} millones.")
    return textos


def excel_propuesta(anio, mes):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    p = propuesta(anio, mes)
    wb = Workbook()
    ws = wb.active
    ws.title = "ESTAD propuesto"
    ws.append([f"LORETO: ADUANA IQUITOS IMPORTACIONES FOB SEGÚN USO O DESTINO ECONÓMICO · {anio}-{mes:02d}"])
    ws.append(["(Miles de US dólares) · desde la base mensual"])
    ws.append(["Rubro", "Base mensual (propuesto)", "ESTAD cargado", "Diferencia"])
    for f in (p or {}).get("filas", []):
        ws.append([("   " if f["nivel"] == "producto" else "") + f["rubro"], f["sunat"], f["estad"], f["dif"]])
        if f["nivel"] != "producto":
            ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.column_dimensions["A"].width = 40
    det = _base(f"{anio}-{mes:02d}", f"{anio}-{mes:02d}")
    w2 = wb.create_sheet("Detalle")
    w2.append(COLUMNAS)
    for r in det[COLUMNAS].itertuples(index=False):
        w2.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in r])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
