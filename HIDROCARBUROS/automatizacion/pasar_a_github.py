"""Una sola vez: copia el almacén de hidrocarburos de Neon (DATA y CONTROL de los notebooks) a un SQLite que desde ahora
vive en la Release «hidrocarburos-datos» del repositorio, y arma ahí las bases (producción, canon y mapa).

    NEON_URL=postgresql://…  DATABASE_URL=sqlite:////ruta/almacen.sqlite  python pasar_a_github.py

Lo corre el flujo «Hidrocarburos · pasar a GitHub». Neon no se toca (solo se lee): lo que hay allí se borra después,
cuando se quite Hidrocarburos de la página.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect, text

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent / "FISCAL" / "api"))
from app import almacen, db  # noqa: E402


def _url(u):
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return "postgresql+psycopg://" + u[len("postgresql://"):] if u.startswith("postgresql://") else u


def main():
    neon = os.environ.get("NEON_URL", "").strip()
    if not neon:
        sys.exit("Falta NEON_URL (la base de la página)")
    if not db.url_base_datos().startswith("sqlite"):
        sys.exit("DATABASE_URL debe ser el SQLite de destino (sqlite:////ruta/almacen.sqlite)")
    origen = create_engine(_url(neon))
    if "almacen" not in inspect(origen).get_table_names():
        sys.exit("Neon no tiene la tabla «almacen»: no hay nada que pasar.")
    almacen._tabla()
    if not almacen.vacio():
        sys.exit("El SQLite de destino ya tiene archivos: no se sobrescribe.")
    with origen.connect() as cx:
        filas = cx.execute(text("SELECT id, nombre, padre, mime, contenido, tamano, modificado, binario FROM almacen")).all()
    with db.motor().begin() as cx:
        for f in filas:
            cx.execute(text("INSERT INTO almacen (id, nombre, padre, mime, contenido, tamano, modificado, binario) "
                            "VALUES (:i, :n, :p, :m, :c, :t, :f, :b)"),
                       {"i": f[0], "n": f[1], "p": f[2], "m": f[3], "c": f[4], "t": f[5], "f": f[6],
                        "b": None if f[7] is None else bytes(f[7])})
    print(f"Almacén copiado: {len(filas)} filas.", almacen.resumen())
    r = almacen.sincronizar(origen="paso a GitHub", todo=True)
    for base, x in r.get("bases", {}).items():
        print(f"  {base}: {x['filas']} filas · {x['periodos'][0]} a {x['periodos'][-1]}")
    for a in r.get("avisos", []):
        print("  ·", a)
    if not r.get("bases"):
        sys.exit("No se armó ninguna base con lo copiado.")
    if pd.read_sql(text("SELECT COUNT(*) AS n FROM almacen"), db.motor())["n"][0] != len(filas):
        sys.exit("El número de archivos copiados no coincide.")


if __name__ == "__main__":
    main()
