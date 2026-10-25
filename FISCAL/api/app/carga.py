"""Lee lo que producen los scrapers (CSV de Fiscal/Scrapeo/output, o PIM_Funcion.xlsx) y lo convierte a las bases del catálogo.

Se reconocen los archivos por su nombre, el mismo que usan Fiscal_Scraper y los scrapers anteriores:
  DEV Funcion.<Nivel> AAAA - Mes MM - ….csv   DEV InvFuente.<Nivel> …   DEV Generica.<Nivel> …   DEV Deuda.<Nivel> …
  DEV Fuente.<Nivel> …   PIM Funcion AAAA - ….csv   PIM Funcion.Municipalidad AAAA - ….csv
Los archivos CONTROL y LOG se ignoran.
"""
import io
import os
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd

from . import db
from .catalogo import BASES, INTERNAS, NIVEL_DE_CORTO, NIVEL_MEF, NIVEL_PIM

_RE_MES = re.compile(r"(\d{4}) - Mes (\d{2})")
_RE_DEV = re.compile(r"^DEV (Funcion|InvFuente|Generica|Deuda|Fuente)\.(GobNacional|GobRegional|Municipalidad) ")
_RE_PIM_MUNI = re.compile(r"^PIM Funcion\.Municipalidad (\d{4})")
_RE_PIM = re.compile(r"^PIM Funcion (\d{4})")
NIVEL_DE_TEXTO = {v: k for k, v in NIVEL_PIM.items()}


def normalizar(txt):
    t = unicodedata.normalize("NFKD", str(txt or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def _codigo_depto(serie):
    return serie.astype(str).str.extract(r"^(\d+)")[0].str.zfill(2)


def _leer_csv(ruta):
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    m = _RE_MES.search(ruta.name)
    if m:
        df["_anio"], df["_mes"] = int(m.group(1)), int(m.group(2))
    else:
        df["_anio"] = df["AÑO"].astype(int)
        df["_mes"] = df["MES"].astype(str).str.extract(r"^(\d+)")[0].astype(int) if "MES" in df.columns else 0
    df["_depto"] = _codigo_depto(df["DEPARTAMENTO"])
    return df


def clasificar_deuda(texto):
    t = normalizar(texto)
    return "AMORTIZACIÓN" if "amortiz" in t else "INTERESES Y COMISIONES" if ("interes" in t or "comision" in t) else None


def unir_generica_y_deuda(gen, deu):
    """La 2.8 de DEV Generica se reemplaza por su desglose de DEV Deuda; lo que no se pudo clasificar queda como diferencia."""
    if gen.empty:
        return gen
    gen = gen.copy()
    gen["DESGLOSE"] = ""
    es_deuda = (gen["COD_GENERICA"].astype(str).str.strip().str.split("-").str[0].eq("7")
                | gen["GENERICA"].map(lambda e: "servicio de la deuda" in normalizar(e)))
    if not es_deuda.any():
        return gen
    gen.loc[es_deuda, "DESGLOSE"] = "SIN DESGLOSE"
    if deu.empty:
        return gen
    deu = deu[deu["CLASIFICACION"].astype(str) != "TOTAL"].copy()
    deu["DESGLOSE"] = [clasificar_deuda(c) or clasificar_deuda(r) for c, r in zip(deu["CLASIFICACION"], deu["RUTA"])]
    clave = ["_anio", "_mes", "_depto", "_nivel"]
    partes = [gen[~es_deuda]]
    for _, fila in gen[es_deuda].iterrows():
        d = deu
        for k in clave:
            d = d[d[k] == fila[k]]
        clasif = d[d["DESGLOSE"].notna()].groupby("DESGLOSE")["DEVENGADO"].sum()
        if clasif.empty:
            partes.append(fila.to_frame().T)
            continue
        filas = []
        for etiqueta, monto in clasif.items():
            f = fila.copy(); f["DESGLOSE"], f["DEVENGADO"] = etiqueta, monto
            filas.append(f)
        resto = float(fila["DEVENGADO"]) - float(clasif.sum())
        if abs(resto) > 1:
            f = fila.copy(); f["DESGLOSE"], f["DEVENGADO"] = "OTROS (sin clasificar)", resto
            filas.append(f)
        partes.append(pd.DataFrame(filas))
    return pd.concat(partes, ignore_index=True)


def leer_archivos(raiz):
    """-> {base_id: DataFrame con las columnas de la base + columnas internas}, avisos."""
    raiz = Path(raiz)
    por_bloque, avisos = {}, []
    pim, pim_muni = [], []
    for n_archivo, ruta in enumerate(sorted(raiz.rglob("*"))):
        if not ruta.is_file() or ruta.name.startswith(("CONTROL", "LOG", ".")):
            continue
        if ruta.suffix.lower() == ".xlsx":
            hoja = pd.read_excel(ruta, sheet_name=0)
            if list(hoja.columns[:5]) == BASES["inv-pim-funcion"].columnas:
                hoja = hoja.dropna(how="all")
                hoja["_anio"], hoja["_mes"], hoja["_depto"] = hoja["AÑO"].astype(int), 0, _codigo_depto(hoja["DEPARTAMENTO"])
                hoja["_archivo"] = n_archivo
                pim.append(hoja)
            else:
                avisos.append(f"{ruta.name}: no tiene las columnas de PIM_Funcion.xlsx; se ignoró.")
            continue
        if ruta.suffix.lower() != ".csv":
            continue
        m = _RE_DEV.match(ruta.name)
        if m:
            df = _leer_csv(ruta).assign(_archivo=n_archivo)
            df["_nivel"] = NIVEL_DE_CORTO[m.group(2)]
            por_bloque.setdefault((m.group(1), NIVEL_DE_CORTO[m.group(2)]), []).append(df)
        elif _RE_PIM_MUNI.match(ruta.name):
            pim_muni.append(_leer_csv(ruta).assign(_archivo=n_archivo))
        elif _RE_PIM.match(ruta.name):
            pim.append(_leer_csv(ruta).assign(_archivo=n_archivo))
        else:
            avisos.append(f"{ruta.name}: nombre no reconocido; se ignoró.")

    def juntar(bloque, niveles=("E", "R", "M")):
        partes = [df for n in niveles for df in por_bloque.get((bloque, n), [])]
        return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

    bases = {}
    # inversión por función: GN y GR tal cual; en locales, suma de las municipalidades
    func = juntar("Funcion", ("E", "R"))
    muni = juntar("Funcion", ("M",))
    if not muni.empty:
        bases["inv-dev-municipalidad"] = muni.assign(_nivel="")
        agg = muni.groupby(["_anio", "_mes", "_depto", "_archivo", "AÑO", "MES", "DEPARTAMENTO", "FUNCION"], as_index=False)["DEVENGADO"].sum()
        agg["NIVEL_GOBIERNO"], agg["ENTIDAD"], agg["_nivel"] = NIVEL_MEF["M"], "MUNICIPALIDADES (SUMA)", "M"
        func = pd.concat([func, agg], ignore_index=True)
    if not func.empty:
        bases["inv-dev-funcion"] = func
    for bloque, base_id in [("InvFuente", "inv-dev-fuente"), ("Fuente", "gasto-dev-fuente")]:
        df = juntar(bloque)
        if not df.empty:
            bases[base_id] = df
    gen = unir_generica_y_deuda(juntar("Generica"), juntar("Deuda"))
    if not gen.empty:
        bases["gasto-dev-generica"] = gen
    if pim:
        df = pd.concat(pim, ignore_index=True)
        df["_nivel"] = df["NIVEL DE GOBIERNO"].map(NIVEL_DE_TEXTO).fillna("")
        bases["inv-pim-funcion"] = df
    if pim_muni:
        bases["inv-pim-municipalidad"] = pd.concat(pim_muni, ignore_index=True).assign(_nivel="")

    for base_id, df in bases.items():
        faltan = [c for c in BASES[base_id].columnas if c not in df.columns]
        if faltan:
            avisos.append(f"{BASES[base_id].nombre}: faltan las columnas {', '.join(faltan)}; no se cargó.")
            bases[base_id] = None
            continue
        b = BASES[base_id]
        df["_mes"], df["_anio"] = df["_mes"].astype(int), df["_anio"].astype(int)
        df["AÑO"] = df["AÑO"].astype(int)
        df[b.valor] = pd.to_numeric(df[b.valor], errors="coerce").fillna(0.0)
        # si un mismo periodo, departamento y nivel viene en dos archivos (p. ej. el CSV del scraper y PIM_Funcion.xlsx),
        # se queda el último archivo leído: así una carga nunca duplica filas
        ultimo = df.groupby(INTERNAS)["_archivo"].transform("max")
        if (df["_archivo"] != ultimo).any():
            avisos.append(f"{b.nombre}: algunos periodos venían en más de un archivo; se usó el último.")
            bases[base_id] = df[df["_archivo"] == ultimo]
    return {k: v for k, v in bases.items() if v is not None}, avisos


def cargar(origen, archivos):
    """archivos: lista de (nombre, bytes). Un .zip se descomprime. Guarda en la base de datos y devuelve el resumen."""
    with tempfile.TemporaryDirectory() as tmp:
        for nombre, contenido in archivos:
            nombre = os.path.basename(nombre)
            if nombre.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                    for info in z.infolist():
                        destino = (Path(tmp) / info.filename).resolve()
                        if info.is_dir() or not str(destino).startswith(str(Path(tmp).resolve())):
                            continue                  # sin rutas fuera de la carpeta temporal
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        destino.write_bytes(z.read(info))
            else:
                (Path(tmp) / nombre).write_bytes(contenido)
        bases, avisos = leer_archivos(tmp)
    resumen = {"bases": {}, "avisos": avisos}
    for base_id, df in bases.items():
        filas = db.guardar(base_id, df)
        resumen["bases"][base_id] = {"filas": filas, "departamentos": sorted(df["_depto"].unique().tolist()),
                                     "periodos": sorted({f"{a}" if m == 0 else f"{a}-{m:02d}" for a, m in zip(df["_anio"], df["_mes"])})}
    if not bases:
        resumen["avisos"].append("No se encontró ningún archivo de los scrapers en lo que subiste.")
    db.registrar_carga(origen, resumen)
    return resumen


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m app.carga <carpeta Scrapeo/output o archivo .zip>")
    ruta = Path(sys.argv[1])
    archivos = [(ruta.name, ruta.read_bytes())] if ruta.is_file() else \
        [(str(p.relative_to(ruta)), p.read_bytes()) for p in ruta.rglob("*") if p.is_file()]
    print(cargar(f"comando: {ruta}", archivos))
