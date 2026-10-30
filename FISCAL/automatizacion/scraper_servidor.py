"""Fase 2: corre Fiscal_Scraper.ipynb sin Colab (GitHub Actions) y carga lo que baja en la base de datos del API (Neon).

    python FISCAL/automatizacion/scraper_servidor.py                       # año en curso hasta el último mes cerrado
    python FISCAL/automatizacion/scraper_servidor.py --desde 2025-01 --hasta 2026-09
    python FISCAL/automatizacion/scraper_servidor.py --prueba              # PRUEBA_RAPIDA del notebook: un mes, Loreto
    python FISCAL/automatizacion/scraper_servidor.py --archivo pim-funcion --desde 2026-01   # solo un archivo (ver ARCHIVOS)

Cómo lo hace: lee las celdas de código del notebook (el mismo que se usa en Colab: si cambia allá, cambia aquí), quita
las líneas «!pip», reemplaza Drive por una carpeta de trabajo y fija el periodo en el BLOQUE 2. Luego carga la carpeta
Scrapeo/output con app.carga (lo mismo que subir el .zip en la página). Necesita DATABASE_URL; sin ella solo raspa.
"""
import argparse
import json
import os
import re
import sys
import time
import traceback
import types
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FISCAL = AQUI.parent
NOTEBOOK = FISCAL / "Fiscal_Scraper.ipynb"
TRABAJO = Path(os.environ.get("FISCAL_TRABAJO", Path.home() / "fiscal_trabajo"))
RUTA_COLAB = "/content/drive/MyDrive/Fiscal"
# Scrapers propios de los tres archivos de los 25 departamentos (.github/workflows/fiscal_archivos.yml): el mismo notebook,
# pero solo con el bloque de ese archivo. Lo demás de la base fiscal no se toca.
ARCHIVOS = {
    "dev-municipalidad": {"nombre": "DEV Funcion.Municipalidad", "anual": False,
                          "fijar": {"NIVELES_A_CORRER": ["M"], "BLOQUES_MENSUALES": ["Funcion"], "BLOQUES_ANUALES": []}},
    "pim-funcion": {"nombre": "PIM Funcion", "anual": True,
                    "fijar": {"BLOQUES_MENSUALES": [], "BLOQUES_ANUALES": ["PIM"]}},
    "pim-municipalidad": {"nombre": "PIM Funcion.Municipalidad", "anual": True,
                          "fijar": {"BLOQUES_MENSUALES": [], "BLOQUES_ANUALES": ["PIM_Municipalidad"]}},
}


def periodo_por_defecto(hoy=None):
    """Del enero del año del último mes cerrado hasta ese mes (el MEF sigue ajustando los meses anteriores del año)."""
    hoy = hoy or date.today()
    anio, mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    return f"{anio}-01", f"{anio}-{mes:02d}"


def tramo_por_defecto(tramo, hoy=None):
    """El año por defecto en dos tramos (enero-junio y julio-último mes cerrado), cada uno en su propio job de GitHub:
    con 3 consultas simultáneas un año completo no entra en las 6 horas que GitHub da a un job. None: no hay tramo."""
    d0, d1 = periodo_por_defecto(hoy)
    anio, mes = d1[:4], int(d1[5:])
    if tramo == 1:
        return d0, f"{anio}-{min(mes, 6):02d}"
    return (f"{anio}-07", d1) if mes >= 7 else None


def sustituir_colab():
    """«google.colab.drive» (Drive ya es una carpeta local) y, si falta, «IPython.display» (display imprime)."""
    colab, drive = types.ModuleType("google.colab"), types.ModuleType("google.colab.drive")
    drive.mount = lambda *a, **k: None
    colab.drive = drive
    sys.modules["google.colab"], sys.modules["google.colab.drive"] = colab, drive
    try:
        import IPython.display  # noqa: F401
    except ImportError:
        ipy, disp = types.ModuleType("IPython"), types.ModuleType("IPython.display")
        disp.display = lambda *x, **k: print(*x)
        ipy.display = disp
        sys.modules["IPython"], sys.modules["IPython.display"] = ipy, disp


class Avance:
    """Barra de carga de la página: cuenta las barras tqdm del notebook (un mes, un control, el PIM…) y deja la fracción
    hecha en la tabla «progreso» de la base (como mucho cada 20 s). Solo en GitHub Actions (GITHUB_RUN_ID) y con base."""

    def __init__(self, g):
        self.g, self.hechas, self.esperadas, self.ultimo = g, 0, None, 0.0
        self.corrida, self.tramo = os.environ.get("GITHUB_RUN_ID"), int(os.environ.get("TRAMO") or 1)
        self.activa = bool(self.corrida and os.environ.get("DATABASE_URL"))

    def _esperadas(self):
        """Barras que hará el notebook, con su configuración ya fijada (BLOQUE 2)."""
        g = self.g
        bm, ba = g.get("BLOQUES_MENSUALES", []), g.get("BLOQUES_ANUALES", [])
        por_anio = (("PIM" in ba) + ("PIM_Municipalidad" in ba)
                    + (len(bm) * len(g.get("NIVELES_A_CORRER", [])) if bm and g.get("CONTROL_ANUAL") else 0))
        return max(1, sum((len(ms) if bm else 0) + por_anio for ms in g.get("PLAN", {}).values()))

    def avisar(self, texto, fraccion=None, forzar=False):
        if not self.activa or (not forzar and time.time() - self.ultimo < 20):
            return
        self.ultimo = time.time()
        if fraccion is None:
            fraccion = min(self.hechas / (self.esperadas or self._esperadas()), 0.99)
        try:
            sys.path.insert(0, str(FISCAL / "api"))
            from app import db
            db.guardar_progreso(self.corrida, self.tramo, fraccion, texto)
        except Exception as e:       # la barra es un extra: nunca detiene el raspado
            print(f"(no se pudo guardar el avance: {e})")

    def tqdm(self, real):
        avance = self

        class Barra:
            def __init__(self, iterable=None, total=None, desc="", **k):
                self.iterable, self.desc = iterable, desc or ""
                self.total = total if total is not None else (len(iterable) if hasattr(iterable, "__len__") else 0)
                self.interna = real(iterable, total=total, desc=desc, **k)

            def __iter__(self):
                if not self.total:              # meses sin consultas (p. ej. solo PIM): no cuentan
                    yield from self.interna
                    return
                if avance.esperadas is None:
                    avance.esperadas = avance._esperadas()
                for i, x in enumerate(self.interna, 1):
                    yield x
                    avance.avisar(self.desc, min((avance.hechas + i / self.total) / avance.esperadas, 0.99))
                avance.hechas += 1
                avance.avisar(self.desc, forzar=False)

            def __getattr__(self, nombre):
                return getattr(self.interna, nombre)
        return Barra


def celdas(fijar):
    """Código del notebook listo para correr aquí: sin «!pip», con la carpeta de trabajo y el periodo fijado."""
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    salida = []
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        lineas = []
        for linea in "".join(c["source"]).split("\n"):
            if linea.lstrip().startswith(("!", "%")):
                continue
            m = re.match(r"^(\w+)\s*=", linea)
            if m and m.group(1) in fijar:
                linea = f"{m.group(1)} = {fijar[m.group(1)]!r}"
            lineas.append(linea)
        salida.append("\n".join(lineas).replace(RUTA_COLAB, str(TRABAJO / "Fiscal")))
    faltan = [k for k in fijar if not any(re.search(rf"^{k} = ", s, re.M) for s in salida)]
    if faltan:
        raise RuntimeError(f"El notebook ya no define {', '.join(faltan)} en el BLOQUE 2: revisa scraper_servidor.py")
    return salida


def periodo_anual(desde, hasta, hoy=None):
    """PIM: es anual; los meses del notebook solo dicen qué años correr (los meses sin bloques mensuales no consultan
    nada). Termina en diciembre o en el último mes cerrado: el notebook calibra la consulta con ese último mes (con
    enero, Consulta Amigable devolvió páginas vacías). El año en curso, si enero aún no cerró, no se puede pedir."""
    d0, d1 = periodo_por_defecto(hoy)
    a0, a1 = int((desde or d1)[:4]), min(int((hasta or desde or d1)[:4]), int(d1[:4]))
    return f"{min(a0, a1)}-01", (d1 if a1 == int(d1[:4]) else f"{a1}-12")


AVANCE = [None]


def raspar(desde, hasta, prueba, archivo=None, departamentos=None):
    a0, m0 = map(int, desde.split("-"))
    a1, m1 = map(int, hasta.split("-"))
    fijar = {"PRUEBA_RAPIDA": prueba, "AÑO_INICIO": a0, "MES_INICIO": m0, "AÑO_FIN": a1, "MES_FIN": m1,
             "WORKERS": int(os.environ.get("FISCAL_WORKERS", "3"))}   # consultas simultáneas: con 6, el MEF devolvió páginas cruzadas (2026)
    if archivo:
        fijar.update(ARCHIVOS[archivo]["fijar"])
    if departamentos:
        fijar["DEPARTAMENTOS_NACIONAL"] = departamentos
    (TRABAJO / "Fiscal").mkdir(parents=True, exist_ok=True)
    sustituir_colab()
    g = {"__name__": "__main__", "display": lambda *x, **k: print(*x)}
    avance = AVANCE[0] = Avance(g)
    import tqdm.auto
    tqdm.auto.tqdm = avance.tqdm(tqdm.auto.tqdm)      # el notebook hace «from tqdm.auto import tqdm» en el BLOQUE 1
    avance.avisar("Calibrando la consulta al MEF…", 0.0, forzar=True)
    for i, codigo in enumerate(celdas(fijar), 1):
        print(f"\n── celda {i} ──", flush=True)
        exec(compile(codigo, f"Fiscal_Scraper.ipynb#celda{i}", "exec"), g)
    return TRABAJO / "Fiscal" / "Scrapeo" / "output"


def cargar(carpeta):
    sys.path.insert(0, str(FISCAL / "api"))
    from app import carga
    archivos = [(str(p.relative_to(carpeta)), p.read_bytes()) for p in sorted(carpeta.rglob("*.csv"))]
    return carga.cargar(f"scraper en GitHub Actions ({datetime.now():%Y-%m-%d %H:%M})", archivos)


def main():
    d0, d1 = periodo_por_defecto()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", default="", help=f"AAAA-MM (por defecto {d0})")
    ap.add_argument("--hasta", default="", help=f"AAAA-MM (por defecto {d1}, el último mes cerrado)")
    ap.add_argument("--prueba", action="store_true", help="PRUEBA_RAPIDA del notebook: solo el mes «desde» y Loreto")
    ap.add_argument("--tramo", type=int, choices=[1, 2], help="sin --desde/--hasta: 1 = enero-junio, 2 = julio-último mes cerrado")
    ap.add_argument("--archivo", choices=list(ARCHIVOS), help="solo ese archivo de los 25 departamentos (sin el resto de la base fiscal)")
    ap.add_argument("--departamentos", default="", help="con --archivo: TODOS (por defecto) o códigos separados por comas, p. ej. 16,22,25")
    a = ap.parse_args()
    deps = None
    if a.departamentos and a.departamentos.strip().upper() != "TODOS":
        deps = [c.strip().zfill(2) for c in a.departamentos.split(",") if c.strip()]
        if not deps or any(not (c.isdigit() and 1 <= int(c) <= 25) for c in deps):
            sys.exit(f"Departamentos no válidos: {a.departamentos!r} (TODOS o códigos 01-25 separados por comas)")
    anual = bool(a.archivo and ARCHIVOS[a.archivo]["anual"])
    if anual:
        a.desde, a.hasta, a.tramo = *periodo_anual(a.desde, a.hasta), None
    if a.tramo and not (a.desde or a.hasta):
        t = tramo_por_defecto(a.tramo)
        if t is None:
            print(f"Tramo {a.tramo}: el último mes cerrado es {d1}; no hay meses de julio en adelante. Nada que hacer.")
            return
        d0, d1 = t
    desde, hasta = a.desde or d0, a.hasta or d1
    for p in (desde, hasta):
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", p):
            sys.exit(f"Periodo no válido: {p!r} (formato AAAA-MM)")
    if a.prueba:
        hasta = desde
    titulo = f"{ARCHIVOS[a.archivo]['nombre']} · " if a.archivo else ""
    rango = f"{desde[:4]} a {hasta[:4]}" if anual and desde[:4] != hasta[:4] else desde[:4] if anual else f"{desde} a {hasta}"
    lineas = [f"## Scraper del MEF · {titulo}{rango}{' · ' + ', '.join(deps) if deps else ''}{' · PRUEBA' if a.prueba else ''} · {datetime.now():%d/%m/%Y %H:%M}", ""]
    t0, ok = time.time(), True
    try:
        carpeta = raspar(desde, hasta, a.prueba, a.archivo, deps)
        csvs = sorted(carpeta.rglob("*.csv"))
        logs = [p.name for p in csvs if p.name.startswith("LOG")]
        lineas.append(f"**Raspado: ✅** {len(csvs)} archivos en {(time.time() - t0) / 60:.1f} min.")
        if logs:
            lineas.append(f"⚠ Consultas con error o sin cuadre: ver {', '.join(logs)} (en el artefacto de la corrida).")
        if a.prueba:
            lineas.append("Prueba: no se carga en la base de datos (solo trae Loreto).")
        elif not os.environ.get("DATABASE_URL"):
            lineas.append("⚠ Falta DATABASE_URL: no se cargó en la base de datos.")
            ok = False
        else:
            if AVANCE[0]:
                AVANCE[0].avisar("Cargando en la base de datos…", 0.99, forzar=True)
            r = cargar(carpeta)
            lineas += ["**Carga en la base de datos: ✅**", "", "| Base | Filas | Periodos |", "|---|---|---|"]
            lineas += [f"| {b} | {x['filas']:,} | {x['periodos'][0]} a {x['periodos'][-1]} |" for b, x in r["bases"].items()]
            lineas += [f"- {x}" for x in r["avisos"]]
            ok = bool(r["bases"])
    except BaseException as e:
        traceback.print_exc()
        lineas.append(f"**❌ {type(e).__name__}: {str(e)[:500]}**")
        ok = False
    if AVANCE[0]:
        AVANCE[0].avisar("Terminado" if ok else "Falló: revisa la corrida en GitHub", 1.0 if ok else None, forzar=True)
    texto = "\n".join(lineas)
    print("\n" + texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
