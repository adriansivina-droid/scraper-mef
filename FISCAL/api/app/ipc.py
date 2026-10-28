"""IPC de Lima Metropolitana para deflactar el gasto y la inversión (variaciones % reales).

Dos fuentes, la primera que funcione:
  · la API de estadísticas del BCRP (serie IPC_SERIE_BCRP, por defecto PN01270PM: índice de precios de Lima
    Metropolitana, dic. 2021 = 100); se consulta en cada sincronización con Drive y con el botón de la página;
  · el IPC.xlsx que usa Fiscal_Procesamiento.ipynb (Fecha en la columna B e IPC en la C desde la fila 4), tomado de
    Drive o subido en la página.
La base del índice no importa: las variaciones reales comparan valores deflactados con la misma serie.
"""
import io
import os
import re
from datetime import date, datetime, timezone

import pandas as pd
import requests
from sqlalchemy import text

from . import db

SERIE_BCRP = os.environ.get("IPC_SERIE_BCRP", "PN01270PM")
URL_BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{serie}/json/{desde}/{hasta}"
_MES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def _tabla():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS ipc (periodo TEXT PRIMARY KEY, valor DOUBLE PRECISION, fuente TEXT, fecha TEXT)"))


def guardar(serie, fuente):
    """serie: {'AAAA-MM': valor}. Reemplaza esos meses. Devuelve cuántos guardó."""
    _tabla()
    serie = {p: float(v) for p, v in serie.items() if v is not None and 20 < float(v) < 1000}   # un índice, no una tasa
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.motor().begin() as cx:
        for p, v in serie.items():
            cx.execute(text("DELETE FROM ipc WHERE periodo = :p"), {"p": p})
            cx.execute(text("INSERT INTO ipc (periodo, valor, fuente, fecha) VALUES (:p, :v, :f, :a)"), {"p": p, "v": v, "f": fuente, "a": ahora})
    return len(serie)


def serie():
    """{'AAAA-MM': valor} (vacío si no hay IPC cargado)."""
    _tabla()
    with db.motor().connect() as cx:
        return dict(cx.execute(text("SELECT periodo, valor FROM ipc")).all())


def estado():
    _tabla()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT COUNT(*), MIN(periodo), MAX(periodo) FROM ipc")).one()
        f = cx.execute(text("SELECT fuente, fecha FROM ipc ORDER BY fecha DESC LIMIT 1")).first()
    return {"meses": int(r[0]), "desde": r[1], "hasta": r[2], "fuente": f[0] if f else None, "actualizado": f[1] if f else None}


def de_bcrp(desde_anio=2010, sesion=requests):
    """{'AAAA-MM': valor} de la API del BCRP. Los periodos vienen como «Ene.2024»."""
    url = URL_BCRP.format(serie=SERIE_BCRP, desde=f"{desde_anio}-1", hasta=f"{date.today().year}-12")
    r = sesion.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    salida = {}
    for p in r.json().get("periods", []):
        m = re.match(r"^([A-Za-z]{3})\w*\.?\s*(\d{4})$", str(p.get("name", "")).strip())
        valor = (p.get("values") or [None])[0]
        if not m or valor in (None, "n.d.", ""):
            continue
        mes = _MES.get(m.group(1).lower())
        if mes:
            salida[f"{m.group(2)}-{mes:02d}"] = float(str(valor).replace(",", ""))
    if not salida:
        raise ValueError("la API del BCRP no devolvió datos del IPC")
    return salida


def de_excel(contenido):
    """{'AAAA-MM': valor} del IPC.xlsx de Fiscal_Procesamiento (Fecha en B, IPC en C desde la fila 4) o de un Excel con
    columnas FECHA e IPC."""
    crudo = pd.read_excel(io.BytesIO(contenido), sheet_name=0, header=None)
    salida = {}
    for _, fila in crudo.iterrows():
        valores = [v for v in fila.tolist() if pd.notna(v)]
        fecha = next((pd.Timestamp(v) for v in valores if isinstance(v, (datetime, date, pd.Timestamp))), None)
        numero = next((float(v) for v in valores if isinstance(v, (int, float)) and not isinstance(v, bool) and 20 < float(v) < 1000), None)
        if fecha is not None and numero is not None:
            salida[f"{fecha.year}-{fecha.month:02d}"] = numero
    if not salida:
        raise ValueError("no se encontraron filas con fecha e índice")
    return salida


def es_ipc(nombre):
    return bool(re.match(r"^IPC.*\.xlsx$", nombre, re.I))


def actualizar_bcrp():
    """Trae el IPC del BCRP y lo guarda. Devuelve el texto para el resumen."""
    s = {k: v for k, v in de_bcrp().items() if 20 < v < 1000}
    if not s:
        raise ValueError(f"la serie {SERIE_BCRP} del BCRP no es un índice (¿variación %?); cambia IPC_SERIE_BCRP")
    n = guardar(s, f"BCRP, serie {SERIE_BCRP}")
    return f"IPC de Lima (BCRP, {SERIE_BCRP}): {n} meses, hasta {max(s)}."
