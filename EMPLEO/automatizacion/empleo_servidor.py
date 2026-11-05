"""Corre Scraping_MTPE_Empleo_x_Region_Actividad.ipynb sin Colab (GitHub Actions) y carga el Excel en la base del API.

    python EMPLEO/automatizacion/empleo_servidor.py                         # los 26 ámbitos del tablero, sin el total Perú
    python EMPLEO/automatizacion/empleo_servidor.py --regiones LOR,SMN,UCA  # Loreto, San Martín y Ucayali
    python EMPLEO/automatizacion/empleo_servidor.py --regiones "La Libertad,Piura"  # solo esas (las demás no se tocan)
    python EMPLEO/automatizacion/empleo_servidor.py --desde 2016            # todos los años del tablero

El notebook trae el total de trabajadores de cada región (sin sectores) desde 2025 hasta el último mes publicado.

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
# el selector del notebook: 1 Perú y luego los 26 ámbitos en este orden (app.empleo.REGIONES)
AMBITOS = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cusco", "Huancavelica",
           "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque", "Lima Metropolitana", "Lima Provincias", "Loreto",
           "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"]


def _clave(t):
    import unicodedata
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower())


def seleccion(texto):
    """«TODAS», «LOR,SMN,UCA» o nombres de regiones separados por comas (con o sin tildes) -> números del notebook.
    Solo se reemplazan en la base las regiones raspadas; las demás quedan como están."""
    if texto.strip().upper() in SELECCION:
        return SELECCION[texto.strip().upper()]
    claves = {_clave(r): i for i, r in enumerate(AMBITOS, 2)}
    nums, malas = [], []
    for r in (x for x in texto.split(",") if x.strip()):
        (nums.append(str(claves[_clave(r)])) if _clave(r) in claves else malas.append(r.strip()))
    if malas or not nums:
        raise SystemExit(f"Región no válida: {', '.join(malas) or '(ninguna)'}. Usa TODAS, LOR,SMN,UCA o nombres como «La Libertad,Piura».")
    return ",".join(nums)


def sustituir_colab():
    colab, files = types.ModuleType("google.colab"), types.ModuleType("google.colab.files")
    files.download = lambda *a, **k: None
    colab.files = files
    sys.modules["google.colab"], sys.modules["google.colab.files"] = colab, files


def celdas(seleccion, desde=None):
    """Las celdas de código del notebook, con la pregunta de regiones respondida y, si se pide, otro DESDE_ANIO."""
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
            if desde and re.match(r"^DESDE_ANIO\s*=", linea):
                linea = f"DESDE_ANIO = {int(desde)}"
            lineas.append(linea)
        salida.append("\n".join(lineas))
    if not pregunta:
        raise RuntimeError("El notebook ya no pregunta las regiones con «entrada = input(…)»: revisa empleo_servidor.py")
    return salida


class Avance:
    """Deja el avance en la tabla «progreso» de la base para la barra de la página: lee los «REGIÓN [i/n]: X» que imprime
    el notebook. Solo en GitHub Actions (GITHUB_RUN_ID) y con base; si falla, el scraper sigue igual."""
    PATRON = re.compile(r"REGIÓN \[(\d+)/(\d+)\]: (.+)")

    def __init__(self, salida):
        self.salida, self.corrida = salida, os.environ.get("GITHUB_RUN_ID")
        self.activo = bool(self.corrida and os.environ.get("DATABASE_URL"))

    def marcar(self, fraccion, texto):
        if not self.activo:
            return
        try:
            sys.path.insert(0, str(RAIZ / "FISCAL" / "api"))
            from app import db
            db.guardar_progreso(self.corrida, 1, fraccion, texto)
        except Exception as e:                          # la barra no debe tumbar el scraper
            self.salida.write(f"[avance] no se pudo guardar: {e}\n")
            self.activo = False

    def write(self, texto):
        m = self.PATRON.search(texto)
        if m:
            i, n, region = int(m.group(1)), int(m.group(2)), m.group(3).strip()
            self.marcar((i - 1) / n * 0.97, f"{region} ({i} de {n} regiones)")
        return self.salida.write(texto)

    def flush(self):
        self.salida.flush()

    def __getattr__(self, k):
        return getattr(self.salida, k)


def raspar(seleccion, desde=None):
    TRABAJO.mkdir(parents=True, exist_ok=True)
    for viejo in TRABAJO.glob("*_empleo.xlsx"):
        viejo.unlink()
    os.chdir(TRABAJO)                                   # el notebook guarda el Excel en la carpeta actual
    sustituir_colab()
    g = {"__name__": "__main__", "display": lambda *x, **k: print(*x)}
    avance = Avance(sys.stdout)
    avance.marcar(0.0, "abriendo el tablero del MTPE")
    sys.stdout = avance
    for i, codigo in enumerate(celdas(seleccion, desde), 1):
        print(f"\n── celda {i} ──", flush=True)
        obj = compile(codigo, f"empleo.ipynb#celda{i}", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        resultado = eval(obj, g)                        # una celda con «await» devuelve una corrutina
        if asyncio.iscoroutine(resultado):
            asyncio.run(resultado)
    sys.stdout = avance.salida
    avance.marcar(0.97, "cargando en la base de datos")
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
    ap.add_argument("--regiones", default="TODAS", help="TODAS, LOR,SMN,UCA o nombres separados por comas («La Libertad,Piura»)")
    ap.add_argument("--desde", type=int, default=None, help="primer año a guardar (por defecto, el DESDE_ANIO del notebook: 2025)")
    a = ap.parse_args()
    lineas = [f"## Scraper de empleo (MTPE) · {a.regiones} · {datetime.now():%d/%m/%Y %H:%M}", ""]
    t0, ok = time.time(), True
    try:
        ruta = raspar(seleccion(a.regiones), a.desde)
        import pandas as pd
        df = pd.read_excel(ruta)
        ultimo = df.assign(P=df["AÑO"] * 100 + df["MES"]).groupby("REGIÓN")["P"].max()
        lineas.append(f"**Raspado: ✅** {len(df):,} filas en {(time.time() - t0) / 60:.1f} min ({ruta.name}).")
        lineas += ["", "| Región | Meses | Desde | Último mes |", "|---|---|---|---|"]
        lineas += [f"| {r} | {len(df[df['REGIÓN'] == r])} | {df[df['REGIÓN'] == r]['AÑO'].min()}-{df[(df['REGIÓN'] == r)].sort_values(['AÑO', 'MES'])['MES'].iloc[0]:02d} | {p // 100}-{p % 100:02d} |" for r, p in ultimo.items()]
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
