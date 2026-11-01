"""Gasto por función de un departamento, varios años (vista anual de Consulta Amigable): PIM y devengado de TODAS las
genéricas, por nivel de gobierno, función y genérica. Para estudios (p. ej. «gasto público sectorial en Loreto»).

Usa la navegación del notebook (BLOQUE 3 de Fiscal_Scraper.ipynb) y no toca la base de datos: deja un CSV en
$FISCAL_TRABAJO y lo imprime comprimido en el registro (entre marcas CSV-GZ-B64) para poder recuperarlo sin artefactos.
"""
import argparse, base64, gzip, io, json, os, random, re, sys, threading, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

NOTEBOOK = Path(__file__).resolve().parents[1] / "Fiscal_Scraper.ipynb"
SECTORES = {"22", "20", "15", "16", "12", "18", "19", "17"}   # educación, salud, transporte, comunicaciones, energía, saneamiento, vivienda, ambiente
NIVELES = {"E": "GOBIERNO NACIONAL", "R": "GOBIERNO REGIONAL", "M": "GOBIERNOS LOCALES"}


def navegacion():
    """Ejecuta solo el BLOQUE 3 (navegación) con la configuración mínima que necesita."""
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    codigo = next("".join(c["source"]) for c in nb["cells"] if "BLOQUE 3" in "".join(c["source"])[:80])
    g = dict(os=os, re=re, time=time, random=random, unicodedata=unicodedata, threading=threading, requests=requests,
             np=np, BeautifulSoup=BeautifulSoup, PAUSA=(0.2, 0.6), PARAMS_EXTRA={},
             CLAVE_GENERICA="24", CLAVE_MES="23", CLAVE_FUNCION="8",
             NIVELES_GOB={"E": {"claves_depto": ["21"]}, "R": {"claves_depto": ["21"]}, "M": {"claves_depto": ["5", "21"]}})
    exec(compile(codigo, "Fiscal_Scraper.ipynb#bloque3", "exec"), g)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--departamento", default="16")
    ap.add_argument("--desde", type=int, default=2016)
    ap.add_argument("--hasta", type=int, default=2025)
    ap.add_argument("--genericas", choices=["todas", "sectores", "ninguna"], default="todas",
                    help="desglose por genérica: todas las funciones, solo educación/salud/transporte/saneamiento… o ninguno (rápido)")
    a = ap.parse_args()
    g = navegacion()
    dep, anios = a.departamento, list(range(a.desde, a.hasta + 1))

    for f in g["FORMATOS"]:                                   # formato de URL que hoy acepta el MEF
        p, err = g["consultar"](anios[-1], "", "E", dep, [], "24", formato=f, reintentos=2)
        print(f"formato {f['nombre']}: {err or f'{len(p.filas)} filas'}", flush=True)
        if p and p.filas and not g["validar"](p, "E", dep):
            g["FORMATO"] = f; break
    if g["FORMATO"] is None:
        sys.exit("Consulta Amigable no devolvió tablas (¿MEF caído?).")

    filas, errores = [], []
    def por_funcion(anio, nivel):
        fs, err, aviso = g["filas_de"](anio, "", nivel, dep, [], "8", f"{anio} {nivel} funciones")
        if err:
            errores.append(err); return []
        if aviso:
            print("  ", aviso)
        salida = []
        for valor, et, dev, pim in fs:
            m = re.match(r"^(\d+)", et)
            cod = m.group(1).zfill(2) if m else valor
            if a.genericas == "ninguna" or (a.genericas == "sectores" and cod not in SECTORES):
                salida.append(dict(AÑO=anio, NIVEL=NIVELES[nivel], COD_FUNCION=cod, FUNCION=et, GENERICA="(SIN DESGLOSE)", PIM=pim, DEVENGADO=dev))
                continue
            gen, e2, _ = g["filas_de"](anio, "", nivel, dep, [("8", cod)], "24", f"{anio} {nivel} {et[:30]} genéricas",
                                       candidatos=g["candidatos_de"](valor, et))
            if e2:
                errores.append(e2)
                salida.append(dict(AÑO=anio, NIVEL=NIVELES[nivel], COD_FUNCION=cod, FUNCION=et, GENERICA="(SIN DESGLOSE)", PIM=pim, DEVENGADO=dev))
                continue
            for _, eg, dg, pg in gen:
                salida.append(dict(AÑO=anio, NIVEL=NIVELES[nivel], COD_FUNCION=cod, FUNCION=et, GENERICA=eg, PIM=pg, DEVENGADO=dg))
            sg = sum(x[2] for x in gen)
            if abs(sg - dev) > max(1, len(gen)):
                print(f"   CUADRE {anio} {nivel} {et[:30]}: genéricas {sg:,.0f} vs función {dev:,.0f}")
        print(f"{anio} {NIVELES[nivel]}: {len(fs)} funciones, devengado {sum(x[2] for x in fs)/1e6:,.1f} millones", flush=True)
        return salida

    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda t: por_funcion(*t), [(y, n) for y in anios for n in NIVELES]):
            filas += r

    df = pd.DataFrame(filas).sort_values(["AÑO", "NIVEL", "COD_FUNCION", "GENERICA"])
    tot = df.groupby("AÑO")[["PIM", "DEVENGADO"]].sum() / 1e6
    print("\nTotales (millones de soles):\n" + tot.round(1).to_string())
    if errores:
        print(f"\n⚠️ {len(errores)} error(es):\n  " + "\n  ".join(errores[:40]))
    destino = Path(os.environ.get("FISCAL_TRABAJO", ".")) / f"gasto_funcion_{dep}_{a.desde}_{a.hasta}_{a.genericas}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False, encoding="utf-8")
    b64 = base64.b64encode(gzip.compress(df.to_csv(index=False).encode())).decode()
    print("\nCSV-GZ-B64-INICIO")
    for i in range(0, len(b64), 3000):
        print(b64[i:i + 3000])
    print("CSV-GZ-B64-FIN")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as s:
            s.write(f"### Gasto por función · departamento {dep} · {a.desde}-{a.hasta}\n\n{len(df)} filas · "
                    f"{len(errores)} errores\n\n```\n{tot.round(1).to_string()}\n```\n")
    if errores and len(errores) > len(df) // 10:
        sys.exit(1)


if __name__ == "__main__":
    main()
