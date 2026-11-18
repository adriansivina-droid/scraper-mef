"""Copia el historial de hidrología de la página (tabla «senamhi_crudo» de Neon) a un SQLite para la PC.

    NEON_URL=postgresql://…  python respaldo_desde_neon.py hidrologia.sqlite

Lo corre el flujo «Hidrología · respaldo para Power BI»; el hidrologia.sqlite que deja se copia a la carpeta de Power BI
(ver actualizar_hidrologia.py). Solo lee Neon.
"""
import os
import sys

from sqlalchemy import create_engine, inspect, text


def _url(u):
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return "postgresql+psycopg://" + u[len("postgresql://"):] if u.startswith("postgresql://") else u


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else "hidrologia.sqlite"
    if os.path.exists(destino):
        sys.exit(f"{destino} ya existe: no se sobrescribe.")
    origen = create_engine(_url(os.environ["NEON_URL"]))
    if "senamhi_crudo" not in inspect(origen).get_table_names():
        sys.exit("Neon no tiene la tabla «senamhi_crudo».")
    dst = create_engine(f"sqlite:///{destino}")
    with dst.begin() as cx:
        cx.execute(text("CREATE TABLE senamhi_crudo (clave TEXT PRIMARY KEY, datos BLOB, huella TEXT, dia TEXT, actualizado TEXT)"))
    n = mb = 0
    with origen.connect() as src:
        res = src.execution_options(stream_results=True).execute(text("SELECT clave, datos, huella, dia, actualizado FROM senamhi_crudo"))
        while lote := res.fetchmany(500):
            with dst.begin() as cx:
                cx.execute(text("INSERT INTO senamhi_crudo VALUES (:c, :d, :h, :dia, :a)"),
                           [{"c": r[0], "d": bytes(r[1]) if r[1] is not None else None, "h": r[2], "dia": r[3], "a": r[4]} for r in lote])
            n += len(lote)
            mb += sum(len(r[1] or b"") for r in lote) / 1e6
    print(f"senamhi_crudo: {n} piezas, {mb:.1f} MB comprimidos → {destino}")
    if not n:
        sys.exit("La tabla está vacía.")


if __name__ == "__main__":
    main()
