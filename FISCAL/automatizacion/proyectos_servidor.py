"""Corre FISCAL/Fiscal_Proyectos.ipynb sin Colab (GitHub Actions) y guarda los proyectos en la base del API.

    python FISCAL/automatizacion/proyectos_servidor.py                 # último mes con inversión en la base
    python FISCAL/automatizacion/proyectos_servidor.py --mes 2026-09

El notebook elige, por departamento y nivel, las 5 funciones que más explican la variación de la inversión del mes
contra el mismo mes del año anterior y consulta al MEF sus 5 proyectos con mayor devengado (unas 45 consultas). Aquí:
  · los CSV «DEV Funcion.*» que el notebook lee de Scrapeo/output se arman con la base «Inversión por función» (así
    no hace falta volver a bajar el año anterior);
  · se corren sus bloques 1 a 5 (sin el Excel ni la subida a Drive del bloque 6) y su resultado (`plan`) se guarda en la
    base «Proyectos detrás de las variaciones». Necesita DATABASE_URL.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
NOTEBOOK = AQUI.parent / "Fiscal_Proyectos.ipynb"
RUTA_COLAB = "/content/drive/MyDrive/Fiscal"
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(RAIZ / "FISCAL" / "api"))
from scraper_servidor import sustituir_colab  # noqa: E402

CARPETA = {"E": ("Gobierno Nacional", "GobNacional"), "R": ("Gobierno Regional", "GobRegional"), "M": ("Gobierno Municipal", "Municipalidad")}
DEPTOS = ["16", "22", "25"]


def ultimo_mes():
    from app import db
    df = db.leer("inv-dev-funcion", DEPTOS, ["E", "R", "M"], "1990-01", "2100-12")
    if df.empty:
        raise RuntimeError("La base «Inversión por función» está vacía: corre antes el scraper del MEF.")
    p = int((df["AÑO"].astype(int) * 100 + df["MES"].astype(str).str.extract(r"^(\d+)")[0].astype(int)).max())
    return f"{p // 100}-{p % 100:02d}"


def preparar_csv(raiz, mes):
    """DEV Funcion.<nivel> AAAA - Mes MM - … .csv del mes y del mismo mes del año anterior, desde la base."""
    from app import db
    a, m = int(mes[:4]), int(mes[5:])
    for anio in (a - 1, a):
        for nivel, (carpeta, corto) in CARPETA.items():
            df = db.leer("inv-dev-funcion", DEPTOS, [nivel], f"{anio}-{m:02d}", f"{anio}-{m:02d}")
            if df.empty:
                continue
            destino = raiz / "Scrapeo" / "output" / "DEVENGADO" / carpeta
            destino.mkdir(parents=True, exist_ok=True)
            df.to_csv(destino / f"DEV Funcion.{corto} {anio} - Mes {m:02d} - LOR - SMN - UCA.csv", index=False, encoding="utf-8-sig")


def celdas(mes, raiz):
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    salida, fijado = [], False
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        codigo = "".join(c["source"])
        if "BLOQUE 6" in codigo.split("\n")[0]:
            break                                          # Excel y subida a Drive: no hacen falta aquí
        lineas = []
        for linea in codigo.split("\n"):
            if linea.lstrip().startswith(("!", "%")):
                continue
            if re.match(r"^MES_ANALISIS\s*=", linea):
                linea, fijado = f"MES_ANALISIS = {mes!r}", True
            lineas.append(linea)
        salida.append("\n".join(lineas).replace(RUTA_COLAB, str(raiz)))
    if not fijado:
        raise RuntimeError("El notebook ya no define MES_ANALISIS en el BLOQUE 2: revisa proyectos_servidor.py")
    return salida


def filas(g):
    """El `plan` del notebook -> filas de la base inv-proyectos (una por proyecto; una sin proyecto si no hubo)."""
    u, u_ant, etq = g["u"], g["u_ant"], g["etq_mes"]
    salida = []
    for p in g["plan"]:
        nivel = p["nivel"]["codigo"]
        if not p["funciones"]:                          # el nivel se muestra igual, con su diferencia
            salida.append({"AÑO": u.year, "MES": u.month, "DEPARTAMENTO": f"{p['cod_depto']}: {p['departamento']}",
                           "NIVEL_GOBIERNO": p["nivel"]["nombre"], "DIFERENCIA_NIVEL": p["diferencia"], "MES_CONSULTADO": etq(p["fecha"]),
                           "N_FUNCION": 0, "FUNCION": "", "ANTERIOR": 0.0, "ACTUAL": 0.0, "DIFERENCIA_FUNCION": 0.0, "N_PROYECTO": 0,
                           "CODIGO": "", "PROYECTO": "Ninguna función en la lista de " + ("aumentos" if p["positivo"] else "caídas"),
                           "DEVENGADO": 0.0, "PCT_FUNCION": None, "_anio": u.year, "_mes": u.month, "_depto": p["cod_depto"], "_nivel": nivel})
        for i, f in enumerate(p["funciones"], 1):
            base = {"AÑO": u.year, "MES": u.month, "DEPARTAMENTO": f"{p['cod_depto']}: {p['departamento']}",
                    "NIVEL_GOBIERNO": p["nivel"]["nombre"], "DIFERENCIA_NIVEL": p["diferencia"], "MES_CONSULTADO": etq(p["fecha"]),
                    "N_FUNCION": i, "FUNCION": f["nombre"], "ANTERIOR": f["anterior"], "ACTUAL": f["actual"],
                    "DIFERENCIA_FUNCION": f["diferencia"], "_anio": u.year, "_mes": u.month, "_depto": p["cod_depto"], "_nivel": nivel}
            proyectos = f.get("proyectos")
            if not proyectos:
                salida.append({**base, "N_PROYECTO": 0, "CODIGO": "", "DEVENGADO": 0.0, "PCT_FUNCION": None,
                               "PROYECTO": "No se pudo consultar esta función" if proyectos is None else f"Sin proyectos con devengado en {etq(p['fecha'])}"})
            for k, (codigo, proyecto, d) in enumerate(proyectos or [], 1):
                tot = f.get("devengado_funcion") or 0
                salida.append({**base, "N_PROYECTO": k, "CODIGO": str(codigo), "PROYECTO": proyecto, "DEVENGADO": float(d),
                               "PCT_FUNCION": round(d / tot * 100, 1) if tot else None})
    return pd.DataFrame(salida)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mes", default="", help="AAAA-MM (por defecto, el último con inversión en la base)")
    a = ap.parse_args()
    lineas, ok, t0 = [], True, time.time()
    try:
        mes = a.mes or ultimo_mes()
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", mes):
            sys.exit(f"Mes no válido: {mes!r}")
        lineas.append(f"## Proyectos detrás de las variaciones · {mes} · {datetime.now():%d/%m/%Y %H:%M}\n")
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp) / "Fiscal"
            preparar_csv(raiz, mes)
            sustituir_colab()
            g = {"__name__": "__main__", "display": lambda *x, **k: print(*x)}
            os.chdir(tmp)
            for i, codigo in enumerate(celdas(mes, raiz), 1):
                print(f"\n── celda {i} ──", flush=True)
                exec(compile(codigo, f"Fiscal_Proyectos.ipynb#celda{i}", "exec"), g)
        df = filas(g)
        from app import db
        filas_guardadas = db.guardar("inv-proyectos", df) if not df.empty else 0
        con = df[df["N_PROYECTO"] > 0] if not df.empty else df
        lineas.append(f"**✅ {len(con)} proyectos** de {df[['_depto', '_nivel', 'FUNCION']].drop_duplicates().shape[0] if not df.empty else 0} "
                      f"funciones guardados en la base ({filas_guardadas} filas, {(time.time() - t0) / 60:.1f} min).")
        lineas += [f"- ⚠ {x}" for x in g.get("avisos", [])] + [f"- ❌ {x}" for x in g.get("errores", [])]
        ok = filas_guardadas > 0
    except BaseException as e:
        traceback.print_exc()
        lineas.append(f"**❌ {type(e).__name__}: {str(e)[:500]}**")
        ok = False
    texto = "\n".join(lineas)
    print("\n" + texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
