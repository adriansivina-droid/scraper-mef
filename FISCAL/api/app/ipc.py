"""IPC de Lima Metropolitana para deflactar el gasto y la inversión (variaciones % reales).

Dos fuentes, la primera que funcione:
  · la API de estadísticas del BCRP: prueba las series de IPC_SERIE_BCRP (separadas por comas; por defecto la del
    índice de Lima base dic. 2021 = 100 y la de base anterior) y se queda con la que llega al mes más reciente; una
    serie que no llega a los últimos 4 meses se descarta (la de base anterior terminó en dic. 2021). Se consulta en
    cada sincronización con Drive y con el botón de la página;
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

SERIES_BCRP = [x.strip() for x in os.environ.get("IPC_SERIE_BCRP", "PN38705PM,PN01270PM").split(",") if x.strip()]
SERIE_BCRP = SERIES_BCRP[0]
URL_BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{serie}/json/{desde}/{hasta}"
_MES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def _tabla():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS ipc (periodo TEXT PRIMARY KEY, valor DOUBLE PRECISION, fuente TEXT, fecha TEXT)"))


def guardar(serie, fuente):
    """serie: {'AAAA-MM': valor}, la serie completa de una fuente: reemplaza todo lo cargado (dos bases distintas del
    índice no se mezclan). Devuelve cuántos meses guardó."""
    _tabla()
    serie = {p: float(v) for p, v in serie.items() if v is not None and 20 < float(v) < 1000}   # un índice, no una tasa
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.motor().begin() as cx:
        if serie:
            cx.execute(text("DELETE FROM ipc"))
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


def de_bcrp(desde_anio=2010, sesion=requests, serie=None):
    """{'AAAA-MM': valor} de una serie de la API del BCRP. Los periodos vienen como «Ene.2024»."""
    url = URL_BCRP.format(serie=serie or SERIE_BCRP, desde=f"{desde_anio}-1", hasta=f"{date.today().year}-12")
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


def _vigente(s, hoy=None):
    """La serie llega a alguno de los últimos 4 meses (el IPC sale a inicios del mes siguiente)."""
    hoy = hoy or date.today()
    limite = (hoy.year * 12 + hoy.month - 1) - 4
    return bool(s) and int(max(s)[:4]) * 12 + int(max(s)[5:]) - 1 >= limite


def actualizar_bcrp():
    """Trae el IPC del BCRP (la serie vigente que llegue más lejos) y lo guarda. Devuelve el texto para el resumen."""
    mejores, motivos = [], []
    for serie in SERIES_BCRP:
        try:
            s = {k: v for k, v in de_bcrp(serie=serie).items() if 20 < v < 1000}
        except Exception as e:
            motivos.append(f"{serie}: {type(e).__name__}")
            continue
        if not s:
            motivos.append(f"{serie}: no es un índice")
        elif not _vigente(s):
            motivos.append(f"{serie}: termina en {max(s)}")
        else:
            mejores.append((max(s), serie, s))
    if not mejores:
        raise ValueError("ninguna serie del BCRP está al día (" + "; ".join(motivos) + ")")
    _, serie, s = max(mejores)
    n = guardar(s, f"BCRP, serie {serie}")
    return f"IPC de Lima (BCRP, {serie}): {n} meses, hasta {max(s)}."
