"""Razón social de los RUC nuevos de exportaciones (GitHub Actions, .github/workflows/expo_padron_ruc.yml).

Lo mismo que razon_social_ruc.py (Colab), pero con los RUC que la página tiene pendientes: los de las bases mensuales
de exportaciones e importaciones que no tienen razón social en sus tablas de empresas. Baja el padrón reducido de SUNAT (~300 MB comprimido), se queda con
esos RUC (RUC, RAZON_SOCIAL, ESTADO, CONDICION), los guarda en la tabla de empresas (las nuevas quedan con BORRAR PARA
vacío: por verificar en la página) y vuelve a procesar la base.
Necesita DATABASE_URL (la misma base de la página).
"""
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "FISCAL" / "api"))
from app import sunat_expo, sunat_impo  # noqa: E402

URL = "http://www2.sunat.gob.pe/padron_reducido_ruc.zip"


def buscar(rucs, contenido=None):
    objetivo = set(rucs)
    if contenido is None:
        print("Descargando el padrón reducido de SUNAT…", flush=True)
        r = requests.get(URL, timeout=1800)
        r.raise_for_status()
        contenido = r.content
    z = zipfile.ZipFile(io.BytesIO(contenido))
    nombre = [n for n in z.namelist() if n.lower().endswith(".txt")][0]
    hallados = []
    with z.open(nombre) as f:
        lector = pd.read_csv(f, sep="|", encoding="latin-1", dtype=str, usecols=[0, 1, 2, 3], header=0,
                             names=["RUC", "RAZON_SOCIAL", "ESTADO", "CONDICION"], chunksize=500_000,
                             on_bad_lines="skip", quoting=3, engine="python")
        for bloque in lector:
            sel = bloque[bloque["RUC"].isin(objetivo)]
            if not sel.empty:
                hallados.append(sel)
    if not hallados:
        return pd.DataFrame(columns=["RUC", "RAZON_SOCIAL", "ESTADO", "CONDICION"])
    df = pd.concat(hallados).drop_duplicates("RUC")
    for c in ("RAZON_SOCIAL", "ESTADO", "CONDICION"):
        df[c] = df[c].str.strip()
    return df


def main():
    expo, impo = sunat_expo.pendientes_ruc(), sunat_impo.pendientes_ruc()
    rucs = sorted(set(expo) | set(impo))
    print(f"RUC sin razón social: {len(rucs)} ({len(expo)} de exportaciones, {len(impo)} de importaciones)")
    if not rucs:
        return
    df = buscar(rucs)
    n = sunat_expo.guardar_padron(df[df["RUC"].isin(expo)]) + sunat_impo.guardar_padron(df)
    faltan = sorted(set(rucs) - set(df["RUC"]))
    print(f"Encontrados en el padrón: {n} de {len(rucs)}")
    if faltan:
        print(f"::warning::No están en el padrón: {', '.join(faltan)}")
    print(f"Bases reprocesadas: exportaciones {sunat_expo.reprocesar()} filas, importaciones {sunat_impo.reprocesar()} filas")


if __name__ == "__main__":
    main()
