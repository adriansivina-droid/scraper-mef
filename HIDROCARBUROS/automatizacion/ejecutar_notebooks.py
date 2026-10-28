"""Ejecuta los notebooks del proyecto sin Colab (GitHub Actions u otra máquina), en orden, y deja un resumen.

    python ejecutar_notebooks.py diario      # producción (PERUPETRO) → mapas
    python ejecutar_notebooks.py mensual     # producción → canon municipal del MEF (año anterior y actual) → mapas

Cómo lo hace: lee las celdas de código de cada .ipynb, quita las líneas «!pip»/«%…», cambia «/content/» por una carpeta
de trabajo y las ejecuta en orden, como «Ejecutar todo» en Colab, con los valores por defecto de cada notebook (salvo los
del MEF, que se fijan abajo). «google.colab» se reemplaza por un sustituto: la autenticación de Drive usa la credencial de
la variable GOOGLE_APPLICATION_CREDENTIALS (en GitHub, el secreto GOOGLE_DRIVE_CREDENCIAL) y userdata.get lee variables de
entorno. Los widgets (ipywidgets) funcionan sin pantalla: se usa su valor por defecto.

Con PP_ALMACEN=pagina (así corre en GitHub Actions) no se usa Drive: la API de Drive de los notebooks se reemplaza por
el almacén de la página (FISCAL/api/app/almacen.py, en la base DATABASE_URL), con las mismas carpetas DATA y CONTROL, y
al terminar se cargan en la página la producción, el canon y el mapa. Antes hay que copiar una vez lo que había en Drive
(HIDROCARBUROS/automatizacion/migrar_drive.py); con el almacén vacío no corre, para no perder los históricos.
"""
import json, os, re, sys, time, types, traceback
from datetime import date, datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)                         # HIDROCARBUROS/
TRABAJO = os.environ.get("PP_TRABAJO", os.path.join(os.path.expanduser("~"), "pp_trabajo"))
HOY = date.today()

# notebook, nombre corto y valores que se fijan (los de «#@param»); el resto, por defecto
PRODUCCION = ("PP_Produccion_Lotes.ipynb", "Producción, canon y regalías (PERUPETRO)", {})
MEF = ("PP_MEF_Canon_Municipal.ipynb", "Canon municipal (MEF)",
       {"ANIO_INICIO": HOY.year - 1, "ANIO_FIN": HOY.year, "DETALLE": "Anual", "DEPARTAMENTO": "LOS 6 PETROLEROS"})
MAPA = ("PP_Mapa_Lotes_Plus.ipynb", "Mapas (simple y Plus)", {})
MODOS = {"diario": [PRODUCCION, MAPA], "mensual": [PRODUCCION, MEF, MAPA]}


def sustituir_colab():
    """Módulos «google.colab.*» mínimos para correr fuera de Colab."""
    import google                                    # paquete de google-auth (namespace)
    colab = types.ModuleType("google.colab")
    auth = types.ModuleType("google.colab.auth")
    auth.authenticate_user = lambda *a, **k: None    # la credencial ya está en GOOGLE_APPLICATION_CREDENTIALS
    output = types.ModuleType("google.colab.output")
    output.enable_custom_widget_manager = lambda *a, **k: None
    userdata = types.ModuleType("google.colab.userdata")
    def _get(k):
        if k not in os.environ:
            raise KeyError(f"Falta la variable de entorno {k} (en GitHub: Settings → Secrets)")
        return os.environ[k]
    userdata.get = _get
    files = types.ModuleType("google.colab.files")
    files.download = lambda *a, **k: None
    for n, m in (("auth", auth), ("output", output), ("userdata", userdata), ("files", files)):
        setattr(colab, n, m); sys.modules[f"google.colab.{n}"] = m
    sys.modules["google.colab"] = colab
    google.colab = colab


def usar_almacen_de_la_pagina():
    """«googleapiclient» (discovery.build, http.MediaFileUpload/MediaIoBaseDownload, errors.HttpError) → almacén."""
    sys.path.insert(0, os.path.join(os.path.dirname(RAIZ), "FISCAL", "api"))
    from app import almacen
    if almacen.vacio():
        sys.exit("El almacén de la página está vacío: corre antes «Hidrocarburos · migrar desde Drive» (una sola vez) "
                 "para no perder los históricos que estaban en Drive.")
    paquete = types.ModuleType("googleapiclient")
    for nombre, cosas in (("discovery", {"build": almacen.build}),
                          ("http", {"MediaFileUpload": almacen.MediaFileUpload, "MediaIoBaseUpload": almacen.MediaIoBaseUpload,
                                    "MediaIoBaseDownload": almacen.MediaIoBaseDownload}),
                          ("errors", {"HttpError": almacen.HttpError})):
        m = types.ModuleType(f"googleapiclient.{nombre}")
        m.__dict__.update(cosas)
        setattr(paquete, nombre, m)
        sys.modules[f"googleapiclient.{nombre}"] = m
    sys.modules["googleapiclient"] = paquete
    print("🗄️  Almacén de la página:", ", ".join(f"{k}: {v['archivos']} archivos, {v['mb']} MB" for k, v in almacen.resumen().items()), flush=True)
    return almacen


def celdas(nb_ruta, fijar):
    nb = json.load(open(nb_ruta, encoding="utf-8"))
    out = []
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        s = "".join(c["source"])
        lineas = []
        for l in s.split("\n"):
            if l.lstrip().startswith(("!", "%")):
                continue
            m = re.match(r"^(\w+)\s*=\s*.*#@param", l)
            if m and m.group(1) in fijar:
                l = f"{m.group(1)} = {fijar[m.group(1)]!r}"
            lineas.append(l)
        s = "\n".join(lineas).replace("/content/", TRABAJO.rstrip("/") + "/")
        out.append(s)
    return out


def ejecutar(nb, nombre, fijar):
    ruta = os.path.join(RAIZ, nb)
    t0 = time.time()
    print(f"\n{'═' * 100}\n▶ {nombre} · {nb} · {datetime.now():%d/%m/%Y %H:%M}\n{'═' * 100}", flush=True)
    g = {"__name__": "__main__"}
    try:                                             # en Colab «display» existe sin importarlo
        from IPython.display import display, HTML
        g.update(display=display, HTML=HTML)
    except ImportError:
        g.update(display=lambda *x, **k: print(*x), HTML=str)
    try:
        for i, s in enumerate(celdas(ruta, fijar), 1):
            print(f"── celda {i} ──", flush=True)
            exec(compile(s, f"{nb}#celda{i}", "exec"), g)
        estado = "OK"
    except SystemExit as e:                          # los notebooks se detienen con SystemExit y un mensaje
        estado = f"DETENIDO: {e}"
    except BaseException as e:
        traceback.print_exc()
        estado = f"ERROR: {type(e).__name__}: {e}"
    dur = time.time() - t0
    print(f"■ {nombre}: {estado} ({dur / 60:.1f} min)", flush=True)
    return {"NOTEBOOK": nb, "PASO": nombre, "ESTADO": estado, "MINUTOS": round(dur / 60, 1)}


def cargar_en_la_pagina(almacen):
    """La producción, el canon y el mapa que quedaron en DATA, a las bases de la página."""
    t0 = time.time()
    print(f"\n{'═' * 100}\n▶ Carga en la página\n{'═' * 100}", flush=True)
    try:
        r = almacen.sincronizar(origen="GitHub Actions")
        for base, x in r.get("bases", {}).items():
            print(f"  {base}: {x['filas']} filas · {x['periodos'][0]} a {x['periodos'][-1]}")
        for a in r.get("avisos", []):
            print("  ·", a)
        estado = "OK"
    except BaseException as e:
        traceback.print_exc()
        estado = f"ERROR: {type(e).__name__}: {e}"
    return {"NOTEBOOK": "-", "PASO": "Carga en la página", "ESTADO": estado, "MINUTOS": round((time.time() - t0) / 60, 1)}


def main():
    modo = (sys.argv[1] if len(sys.argv) > 1 else "diario").lower()
    if modo not in MODOS:
        sys.exit(f"Modo desconocido «{modo}»: usa {', '.join(MODOS)}")
    os.makedirs(TRABAJO, exist_ok=True)
    sustituir_colab()
    almacen = usar_almacen_de_la_pagina() if os.environ.get("PP_ALMACEN") == "pagina" else None
    res = []
    for nb, nombre, fijar in MODOS[modo]:
        res.append(ejecutar(nb, nombre, fijar))
        if nb == PRODUCCION[0] and not res[-1]["ESTADO"].startswith("OK"):
            print("⚠️ La producción falló: los mapas se generan igual con los datos que ya hay guardados.")
    if almacen is not None:
        res.append(cargar_en_la_pagina(almacen))
    lineas = [f"## Actualización {modo} · {datetime.now():%d/%m/%Y %H:%M}", "", "| Paso | Estado | Minutos |", "|---|---|---|"]
    lineas += [f"| {r['PASO']} | {'✅' if r['ESTADO'] == 'OK' else '❌'} {r['ESTADO'][:300]} | {r['MINUTOS']} |" for r in res]
    resumen = "\n".join(lineas)
    print("\n" + resumen)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write(resumen + "\n")
    json.dump(res, open(os.path.join(TRABAJO, "resumen_actualizacion.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(0 if all(r["ESTADO"] == "OK" for r in res) else 1)


if __name__ == "__main__":
    main()
