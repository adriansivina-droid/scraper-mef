"""IPC de Lima Metropolitana para deflactar el gasto y la inversión (variaciones % reales).

La fuente oficial es el INEI: el Excel «n01_indice-precios_al_consumidor-lm_<mes><aa>.xlsx» que publica cada mes (hoja
«Base Dic2021»: Año, Mes, Índice; el año solo en enero), subido en la página. Es el índice mensual con el que se deflacta.
Mientras haya un IPC del INEI cargado, el BCRP no lo reemplaza (ni a mano ni en las actualizaciones automáticas): si al
índice le falta el último mes, la variación de ese mes queda nominal hasta subir el Excel nuevo del INEI.
Respaldo, solo si no hay IPC del INEI:
  · la API de estadísticas del BCRP: prueba las series de IPC_SERIE_BCRP (separadas por comas; por defecto la del
    índice de Lima base dic. 2021 = 100 y la de base anterior) y se queda con la que llega al mes más reciente; una
    serie que no llega a los últimos 4 meses se descarta (la de base anterior terminó en dic. 2021). Se consulta sola
    (refrescar: al abrir los cuadros de ejecución si al IPC cargado le falta el mes anterior, a lo más una vez al día),
    antes de cada procesamiento fiscal y con el botón de la página;
  · el IPC.xlsx que usa Fiscal_Procesamiento.ipynb (Fecha en la columna B e IPC en la C desde la fila 4), subido en la
    página, por si el BCRP no responde.
La base del índice no importa: las variaciones reales comparan valores deflactados con la misma serie.
"""
import io
import os
import re
import threading
import time
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


_MESES_ES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "setiembre": 9,
             "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
FUENTE_INEI = "INEI"


def _hoja_inei(filas):
    """{'AAAA-MM': índice} de una hoja del INEI: encabezado «Año | Mes | Índice», el año solo en enero."""
    cab = next((i for i, f in enumerate(filas[:15]) if len(f) > 2 and str(f[0] or "").strip().lower() == "año"
                and str(f[1] or "").strip().lower() == "mes" and str(f[2] or "").strip().lower().startswith(("índice", "indice"))), None)
    if cab is None:
        return {}
    salida, anio = {}, None
    for f in filas[cab + 1:]:
        if len(f) < 3:
            continue
        if isinstance(f[0], (int, float)) and not isinstance(f[0], bool) and 1900 < f[0] < 2200:
            anio = int(f[0])
        mes = _MESES_ES.get(str(f[1] or "").strip().lower())
        if anio and mes and isinstance(f[2], (int, float)) and not isinstance(f[2], bool) and 20 < float(f[2]) < 1000:
            salida[f"{anio}-{mes:02d}"] = float(f[2])
    return salida


def de_inei(contenido):
    """(serie, base) del Excel del INEI: de sus hojas (una por base del índice), la que llega al mes más reciente."""
    hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None, header=None)
    mejores = []
    for nombre, h in hojas.items():
        filas = [list(r) for r in h.itertuples(index=False)]
        s = _hoja_inei(filas)
        if s:
            base = next((str(v) for f in filas[:4] for v in f if isinstance(v, str) and "base" in v.lower()), nombre)
            mejores.append((max(s), len(s), s, base.strip("() ")))
    if not mejores:
        return None, None
    _, _, s, base = max(mejores, key=lambda x: (x[0], x[1]))
    return s, base


def leer_excel(contenido, nombre):
    """(serie, fuente) de un Excel de IPC: el del INEI (fuente oficial) o, de respaldo, el IPC.xlsx de Fiscal_Procesamiento."""
    s, base = de_inei(contenido)
    if s:
        return s, f"{FUENTE_INEI}, IPC de Lima Metropolitana ({base}): {nombre}"
    return de_excel(contenido), nombre


def es_ipc(nombre):
    """IPC.xlsx (Fiscal_Procesamiento) o el Excel del INEI («n01_indice-precios_al_consumidor-lm_oct26.xlsx»)."""
    return bool(re.match(r"^IPC.*\.xlsx$", nombre, re.I) or re.search(r"indice[-_ ]?precios[-_ ]?al[-_ ]?consumidor.*\.xlsx$", nombre, re.I))


def es_inei_cargado():
    return str(estado().get("fuente") or "").startswith(FUENTE_INEI)


def _vigente(s, hoy=None):
    """La serie llega a alguno de los últimos 4 meses (el IPC sale a inicios del mes siguiente)."""
    hoy = hoy or date.today()
    limite = (hoy.year * 12 + hoy.month - 1) - 4
    return bool(s) and int(max(s)[:4]) * 12 + int(max(s)[5:]) - 1 >= limite


def actualizar_bcrp():
    """Trae el IPC del BCRP (la serie vigente que llegue más lejos) y lo guarda. Devuelve el texto para el resumen.
    Si el IPC cargado es el del INEI (la fuente oficial), no lo reemplaza."""
    if es_inei_cargado():
        e = estado()
        return f"IPC de Lima: se usa el del INEI (hasta {e['hasta']}); el BCRP no lo reemplaza. Para un mes nuevo, sube el Excel del INEI."
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


_ultimo_intento = [0.0]


def refrescar(horas=24, hoy=None):
    """Si al IPC cargado le falta el mes anterior, lo trae del BCRP en segundo plano (a lo más una vez cada `horas`).
    Nunca falla ni demora la respuesta: si el BCRP no responde, se queda el cargado."""
    hoy = hoy or date.today()
    anterior = f"{hoy.year - (hoy.month == 1)}-{(hoy.month - 2) % 12 + 1:02d}"
    e = estado()
    hasta = e["hasta"]
    if str(e.get("fuente") or "").startswith(FUENTE_INEI):
        return False                                   # el del INEI no se reemplaza con el del BCRP
    if (hasta and hasta >= anterior) or time.time() - _ultimo_intento[0] < horas * 3600:
        return False
    _ultimo_intento[0] = time.time()

    def traer():
        try:
            actualizar_bcrp()
        except Exception:
            pass
    threading.Thread(target=traer, daemon=True).start()
    return True
