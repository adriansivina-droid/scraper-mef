"""Scraper de INGRESOS del MEF (Consulta Amigable de Ingresos, mensual) para las hojas INGRESOS G.R. y G.L. del ESTAD.

    python ingresos_mef.py --anios 2025-2026 [--deptos 16,22,25] [--salida carpeta] [--cargar]

Consulta https://apps5.mineco.gob.pe/transparenciaingresos/mensual/Navegar_6.aspx con los mismos parámetros que arma el
navegador. Las claves se obtuvieron recorriendo la consulta:
  1 nivel de gobierno (R / M) · 2 sector (99 = gobiernos regionales) · 3 pliego (453 Loreto, 459 San Martín, 462 Ucayali)
  23 tipo de gobierno local (M = municipalidades) · 5 departamento · 8 fuente · 9 rubro · 17 mes
  18 genérica · 19 subgenérica · 20 detalle de subgenérica · 21 específica · 22 detalle de específica

Por cada región y nivel baja, mes a mes (agrupando por mes, una consulta por concepto), el recaudado de:
  · todas las genéricas (1-1 … 1-9) y las subgenéricas de 1-3 (tasas, venta de bienes, servicios), 1-4 (donaciones y
    transferencias corrientes y de capital) y 1-5 (rentas de la propiedad, multas, otros);
  · el detalle de las donaciones y transferencias (de otras unidades de gobierno, participaciones de recursos determinados:
    canon y sobrecanon y su detalle, renta de aduanas, eliminación de exoneraciones, FONCOMUN, asignación especial);
  · las fuentes y los rubros.
El monto sale del valor de cada fila (trae los céntimos). Sin --cargar deja el CSV; con --cargar (y DATABASE_URL) lo
guarda en la base «ingresos» de la página.
"""
import argparse
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://apps5.mineco.gob.pe/transparenciaingresos/mensual/Navegar_6.aspx"
DEPTOS = {"16": "16: LORETO", "22": "22: SAN MARTIN", "25": "25: UCAYALI"}
PLIEGO_GR = {"16": "453", "22": "459", "25": "462"}
NIVELES = {"R": "R: GOBIERNOS REGIONALES", "M": "M: GOBIERNOS LOCALES"}
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
CLAVES = [("GENERICA", "18"), ("SUBGENERICA", "19"), ("DETALLE_SUBGENERICA", "20"), ("ESPECIFICA", "21"), ("ESPECIFICA_DETALLE", "22")]
# qué ramas del clasificador se abren (el resto queda en su nivel): las que piden las hojas de ingresos del ESTAD
ABRIR = {"1-3", "1-4", "1-5", "1-4-1", "1-4-2", "1-4-1-3", "1-4-1-4", "1-4-2-3", "1-4-1-3-1", "1-4-2-3-1", "1-4-1-4-1", "1-4-1-4-6"}
PAUSA = (0.4, 1.2)


def sesion():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                      "Referer": "https://apps5.mineco.gob.pe/transparenciaingresos/mensual/default.aspx"})
    return s


def consultar(s, params, reintentos=5):
    """[(codigo, etiqueta, recaudado)] de la tabla de detalle (el monto, con céntimos, sale del valor del botón)."""
    p = {"_tgt": "frame", "_uhc": "yes", "0": "", **params, "ap": "ActProy"}
    ultimo = ""
    for i in range(reintentos):
        try:
            r = s.get(URL, params=p, timeout=60)
            if r.status_code == 200:
                t = BeautifulSoup(r.content, "html.parser").find("table", class_="Data")
                if t is not None:
                    filas = []
                    for tr in t.find_all("tr"):
                        radio = tr.find("input", attrs={"type": "radio"})
                        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                        if radio is None or not tds:
                            continue
                        partes = (radio.get("value") or "").split("/")
                        etiqueta = next((x for x in tds if x), "")
                        try:
                            monto = float(partes[-1]) if partes[-1] else 0.0
                        except ValueError:
                            monto = float(re.sub(r"[^\d.\-]", "", tds[-1]) or 0)
                        filas.append((partes[0].strip(), etiqueta, monto))
                    time.sleep(random.uniform(*PAUSA))
                    return filas
                ultimo = "sin tabla"
            else:
                ultimo = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            ultimo = f"{type(e).__name__}: {e}"
        time.sleep(min(40, 3 * 2 ** i + random.random()))
    raise RuntimeError(f"El MEF no respondió ({ultimo}) a {params}")


def _base(nivel, depto):
    return {"1": "R", "2": "99", "3": PLIEGO_GR[depto]} if nivel == "R" else {"1": "M", "23": "M", "5": depto}


def _etiqueta(et):
    return re.sub(r"^[\w\-]+\s*:\s*", "", et).strip()


def recorrer(anio, nivel, depto, s=None):
    """Filas (AÑO, MES, NIVEL_GOBIERNO, DEPARTAMENTO, CLASIFICADOR, CODIGO, CONCEPTO, RECAUDADO) de un año."""
    s = s or sesion()
    base = {**_base(nivel, depto), "y": str(anio)}
    filas = []

    def mensual(ruta, clasificador, codigo, concepto):
        for mes, _, monto in consultar(s, {**base, **ruta, "17": ""}):
            if mes.isdigit():
                filas.append({"AÑO": anio, "MES": f"{int(mes):02d}: {MESES[int(mes) - 1]}", "NIVEL_GOBIERNO": NIVELES[nivel],
                              "DEPARTAMENTO": DEPTOS[depto], "CLASIFICADOR": clasificador, "CODIGO": codigo,
                              "CONCEPTO": concepto, "RECAUDADO": monto})

    def rama(ruta, nivel_clas):
        nombre, clave = CLAVES[nivel_clas]
        for cod, et, _ in consultar(s, {**base, **ruta, clave: ""}):
            r2 = {**ruta, clave: cod}
            mensual(r2, nombre, cod, _etiqueta(et))
            if cod in ABRIR and nivel_clas + 1 < len(CLAVES):
                rama(r2, nivel_clas + 1)

    rama({}, 0)
    for clasificador, clave in (("FUENTE", "8"), ("RUBRO", "9")):
        for cod, et, _ in consultar(s, {**base, clave: ""}):
            mensual({clave: cod}, clasificador, cod, _etiqueta(et))
    return filas


def bajar(anios, deptos, hilos=3):
    trabajos = [(a, n, d) for a in anios for d in deptos for n in NIVELES]
    salida = []
    with ThreadPoolExecutor(hilos) as ex:
        for (a, n, d), filas in zip(trabajos, ex.map(lambda t: recorrer(*t), trabajos)):
            print(f"  {a} {NIVELES[n][:20]} {DEPTOS[d]}: {len(filas)} filas", flush=True)
            salida += filas
    df = pd.DataFrame(salida)
    if not df.empty:
        hoy = date.today()
        df = df[(df["AÑO"] * 100 + df["MES"].str[:2].astype(int)) < hoy.year * 100 + hoy.month]   # solo meses cerrados
    return df


def control(df):
    """Que las ramas abiertas sumen lo mismo que su concepto padre, mes a mes (±1 sol)."""
    avisos = []
    g = df[df.CLASIFICADOR != "FUENTE"].groupby(["AÑO", "MES", "NIVEL_GOBIERNO", "DEPARTAMENTO"])
    for k, x in g:
        cod = dict(zip(x.CODIGO, x.RECAUDADO))
        for padre in ABRIR:
            hijos = [c for c in cod if c.startswith(padre + "-") and c.count("-") == padre.count("-") + 1]
            if padre in cod and hijos and abs(sum(cod[h] for h in hijos) - cod[padre]) > 1:
                avisos.append(f"{k}: {padre} = {cod[padre]:,.0f} pero sus partes suman {sum(cod[h] for h in hijos):,.0f}")
    return avisos


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anios", default=str(date.today().year), help="AAAA o AAAA-AAAA")
    ap.add_argument("--deptos", default="16,22,25")
    ap.add_argument("--salida", default="ingresos_mef")
    ap.add_argument("--cargar", action="store_true", help="guardar en la base «ingresos» de la página (DATABASE_URL)")
    a = ap.parse_args()
    a0, _, a1 = a.anios.partition("-")
    anios = list(range(int(a0), int(a1 or a0) + 1))
    deptos = [d.strip() for d in a.deptos.split(",")]
    t0 = time.time()
    df = bajar(anios, deptos)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    nombre = salida / f"ING Recaudado {anios[0]}-{anios[-1]} - {'-'.join(deptos)}.csv"
    df.to_csv(nombre, index=False, encoding="utf-8-sig")
    avisos = control(df)
    lineas = [f"## Ingresos del MEF · {a.anios} · {', '.join(deptos)}", "",
              f"{len(df):,} filas en {(time.time() - t0) / 60:.1f} min → {nombre.name}",
              f"Control (las partes suman su concepto): {'✅ todo cuadra' if not avisos else f'⚠ {len(avisos)} diferencias'}"]
    lineas += [f"- {x}" for x in avisos[:30]]
    if a.cargar:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
        from app import db
        x = df.assign(_anio=df["AÑO"], _mes=df["MES"].str[:2].astype(int), _depto=df["DEPARTAMENTO"].str[:2],
                      _nivel=df["NIVEL_GOBIERNO"].str[0])
        lineas.append(f"Cargado en la página: {db.guardar('ingresos', x):,} filas.")
    texto = "\n".join(lineas)
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write(texto + "\n")


if __name__ == "__main__":
    main()
