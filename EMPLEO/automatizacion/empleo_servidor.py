"""Corre Scraping_MTPE_Empleo_x_Region_Actividad.ipynb sin Colab (GitHub Actions) y carga el Excel en la base del API.

    python EMPLEO/automatizacion/empleo_servidor.py                 # Loreto, San Martín y Ucayali
    python EMPLEO/automatizacion/empleo_servidor.py --regiones TODAS  # los 26 ámbitos del tablero, sin el total Perú

Cómo lo hace: lee las celdas de código del notebook (el mismo de Colab: si cambia allá, cambia aquí), quita las líneas
«!apt-get»/«!pip», responde la pregunta de regiones (el «input» del selector) y reemplaza la descarga de Colab por una
carpeta de trabajo. Luego sube el Excel con app.carga, como si se subiera en la página. Necesita DATABASE_URL.
"""
import argparse
import ast
import asyncio
import json
import os
import re
import sys
import time
import traceback
import types
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
NOTEBOOK = AQUI.parent / "Scraping_MTPE_Empleo_x_Region_Actividad.ipynb"
TRABAJO = Path(os.environ.get("EMPLEO_TRABAJO", Path.home() / "empleo_trabajo"))
# números del selector del notebook (REGIONES): 18 Loreto, 24 San Martín, 27 Ucayali; 2-27 = todas menos «Perú»
SELECCION = {"LOR,SMN,UCA": "18,24,27", "TODAS": "2-27"}


def sustituir_colab():
    colab, files = types.ModuleType("google.colab"), types.ModuleType("google.colab.files")
    files.download = lambda *a, **k: None
    colab.files = files
    sys.modules["google.colab"], sys.modules["google.colab.files"] = colab, files


def celdas(seleccion):
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    salida, pregunta = [], False
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        lineas, sigue = [], False
        for linea in "".join(c["source"]).split("\n"):
            if sigue or linea.lstrip().startswith(("!", "%")):     # «!apt-get … \» sigue en la línea de abajo
                sigue = linea.rstrip().endswith("\\")
                continue
            if re.match(r"^entrada\s*=\s*input\(", linea):
                linea, pregunta = f"entrada = {seleccion!r}", True
            lineas.append(linea)
        salida.append("\n".join(lineas))
    if not pregunta:
        raise RuntimeError("El notebook ya no pregunta las regiones con «entrada = input(…)»: revisa empleo_servidor.py")
    return salida


def raspar(seleccion):
    TRABAJO.mkdir(parents=True, exist_ok=True)
    for viejo in TRABAJO.glob("*_empleo.xlsx"):
        viejo.unlink()
    os.chdir(TRABAJO)                                   # el notebook guarda el Excel en la carpeta actual
    sustituir_colab()
    g = {"__name__": "__main__", "display": lambda *x, **k: print(*x)}
    for i, codigo in enumerate(celdas(seleccion), 1):
        print(f"\n── celda {i} ──", flush=True)
        obj = compile(codigo, f"empleo.ipynb#celda{i}", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        resultado = eval(obj, g)                        # una celda con «await» devuelve una corrutina
        if asyncio.iscoroutine(resultado):
            asyncio.run(resultado)
    archivos = sorted(TRABAJO.glob("*_empleo.xlsx"))
    if not archivos:
        raise RuntimeError("El scraper no generó el Excel de empleo (ver los mensajes de arriba).")
    return archivos[-1]


def cargar(ruta):
    sys.path.insert(0, str(RAIZ / "FISCAL" / "api"))
    from app import carga
    return carga.cargar(f"scraper de empleo en GitHub Actions ({datetime.now():%Y-%m-%d %H:%M})", [(ruta.name, ruta.read_bytes())])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--regiones", choices=list(SELECCION), default="LOR,SMN,UCA")
    a = ap.parse_args()
    lineas = [f"## Scraper de empleo (MTPE) · {a.regiones} · {datetime.now():%d/%m/%Y %H:%M}", ""]
    t0, ok = time.time(), True
    try:
        ruta = raspar(SELECCION[a.regiones])
        import pandas as pd
        df = pd.read_excel(ruta)
        ultimo = df.assign(P=df["AÑO"] * 100 + df["MES"]).groupby("REGIÓN")["P"].max()
        lineas.append(f"**Raspado: ✅** {len(df):,} filas en {(time.time() - t0) / 60:.1f} min ({ruta.name}).")
        lineas += ["", "| Región | Actividades | Último mes |", "|---|---|---|"]
        lineas += [f"| {r} | {df[df['REGIÓN'] == r]['ACTIVIDAD_ECONOMICA'].nunique()} de 7 | {p // 100}-{p % 100:02d} |" for r, p in ultimo.items()]
        if not os.environ.get("DATABASE_URL"):
            lineas.append("⚠ Falta DATABASE_URL: no se cargó en la base de datos.")
            ok = False
        else:
            r = cargar(ruta)
            x = r["bases"].get("empleo")
            lineas += ["", f"**Carga en la base de datos: {'✅' if x else '❌'}**"
                       + (f" {x['filas']:,} filas · {x['periodos'][0]} a {x['periodos'][-1]}" if x else "")]
            lineas += [f"- {m}" for m in r["avisos"]]
            ok = bool(x)
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
