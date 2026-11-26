"""Una sola vez: en los peces ornamentales de Loreto ya guardados en la página, intercambia ESPECIE y ESPECIE_CORREGIDA.

Antes, ESPECIE llevaba el nombre común y ESPECIE_CORREGIDA el científico; desde noviembre de 2026 es al revés
(ESPECIE = nombre científico, ESPECIE_CORREGIDA = nombre común), como en el pescado de consumo. El intercambio y la
marca que impide repetirlo se guardan en la misma transacción: correrlo otra vez no hace nada.

    DATABASE_URL=… python PESCA/automatizacion/pesca_ornamentales_especie.py
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "FISCAL" / "api"))
from app import db  # noqa: E402

MARCA = "migracion:pesca-ornamentales-especie-2026-11"
TABLA = db.BASES["pesca-loreto"].tabla


def main():
    db._documentos()
    if db.documento(MARCA):
        print(f"Ya se hizo antes ({db.documento(MARCA)[1]}): no se toca nada.")
        return
    if not db.existe(TABLA):
        print(f"No existe {TABLA}: no hay nada que corregir.")
        return
    with db.motor().begin() as cx:
        antes = cx.execute(text(f'SELECT "ESPECIE", "ESPECIE_CORREGIDA" FROM "{TABLA}" WHERE "ESTADO" = :e LIMIT 3'), {"e": "ORNAMENTAL"}).all()
        n = cx.execute(text(f'UPDATE "{TABLA}" SET "ESPECIE" = "ESPECIE_CORREGIDA", "ESPECIE_CORREGIDA" = "ESPECIE" '
                            'WHERE "ESTADO" = :e'), {"e": "ORNAMENTAL"}).rowcount
        despues = cx.execute(text(f'SELECT "ESPECIE", "ESPECIE_CORREGIDA" FROM "{TABLA}" WHERE "ESTADO" = :e LIMIT 3'), {"e": "ORNAMENTAL"}).all()
        ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cx.execute(text("INSERT INTO documentos (nombre, contenido, modificado, fecha) VALUES (:n, :c, :m, :f)"),
                   {"n": MARCA, "c": f"{n} filas", "m": ahora, "f": ahora})
    lineas = ["## Peces ornamentales de Loreto: ESPECIE ↔ ESPECIE_CORREGIDA", "", f"Filas corregidas: {n}", "",
              "| Antes: ESPECIE | Antes: ESPECIE_CORREGIDA | Ahora: ESPECIE | Ahora: ESPECIE_CORREGIDA |", "|---|---|---|---|"]
    lineas += [f"| {a[0]} | {a[1]} | {d[0]} | {d[1]} |" for a, d in zip(antes, despues)]
    texto = "\n".join(lineas)
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write(texto + "\n")


if __name__ == "__main__":
    main()
