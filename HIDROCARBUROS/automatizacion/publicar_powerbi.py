"""Arma los archivos que lee Power BI a partir de la base de hidrocarburos (la de DATABASE_URL; en GitHub Actions, el
SQLite «almacen.sqlite» que se guarda en la Release «hidrocarburos-datos» del repositorio).

    python publicar_powerbi.py CARPETA_DE_SALIDA

Deja en la carpeta:
  · hidro_produccion.csv   producción fiscalizada por mes, departamento, lote, operador y producto (PERUPETRO; los meses que
                           la estadística mensual aún no publica salen de la producción diaria: columna FUENTE)
  · hidro_canon.csv        canon y sobrecanon petrolero transferido por mes y departamento (millones de soles)
  · hidro_lotes_operador.csv  qué lotes operó cada operador en cada año (para cruzar con las exportaciones por empresa)
  · PP_mapa_lotes_plus.html   el mapa de lotes (se abre con doble clic; Power BI no lo muestra)
  · LEEME.txt              qué es cada archivo y cuándo se actualizó

Todos van en UTF-8 con BOM y separados por comas, con PERIODO (primer día del mes) para el eje de tiempo de Power BI.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent / "FISCAL" / "api"))
from app import db, hidrocarburos  # noqa: E402

def _periodo(df):
    a = pd.to_numeric(df["AÑO"], errors="coerce").astype("Int64")
    m = pd.to_numeric(df["MES"].astype(str).str.extract(r"(\d+)")[0], errors="coerce").astype("Int64")
    out = df.copy()
    out["AÑO"], out["MES"] = a, m
    out.insert(0, "PERIODO", pd.to_datetime({"year": a, "month": m, "day": 1}, errors="coerce").dt.date)
    return out


def _guardar(df, ruta):
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"  {ruta.name}: {len(df):,} filas")


def main():
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "powerbi")
    salida.mkdir(parents=True, exist_ok=True)
    lineas = ["HIDROCARBUROS · ARCHIVOS PARA POWER BI", "=" * 60,
              f"Actualizado: {datetime.now(timezone(timedelta(hours=-5))):%d/%m/%Y %H:%M} (hora de Lima; GitHub Actions, flujo «Hidrocarburos · actualización»)", ""]

    prod = db.leer_todo("hidro-produccion")
    if prod is None or prod.empty:
        sys.exit("No hay producción de hidrocarburos en la base: nada que publicar.")
    prod = _periodo(prod)
    prod["VOLUMEN"] = pd.to_numeric(prod["VOLUMEN"], errors="coerce")
    prod["PROMEDIO_DIARIO"] = pd.to_numeric(prod["PROMEDIO_DIARIO"], errors="coerce")
    emp = hidrocarburos._con_empresa(prod)["EMPRESA"]          # el nombre homologado que usa la página
    prod.insert(prod.columns.get_loc("OPERADOR") + 1, "EMPRESA", emp.map(lambda e: hidrocarburos.nombre_empresa(e) if e else ""))
    prod = prod.sort_values(["PERIODO", "DEPARTAMENTO", "LOTE", "PRODUCTO"])
    _guardar(prod, salida / "hidro_produccion.csv")
    lineas.append(f"hidro_produccion.csv  {len(prod):,} filas · {prod['PERIODO'].min():%m/%Y} a {prod['PERIODO'].max():%m/%Y}")

    canon = db.leer_todo("hidro-canon")
    if canon is not None and not canon.empty:
        canon = _periodo(canon)
        canon["CANON_MM_SOLES"] = pd.to_numeric(canon["CANON_MM_SOLES"], errors="coerce")
        canon = canon.sort_values(["PERIODO", "DEPARTAMENTO"])
        _guardar(canon, salida / "hidro_canon.csv")
        lineas.append(f"hidro_canon.csv       {len(canon):,} filas · {canon['PERIODO'].min():%m/%Y} a {canon['PERIODO'].max():%m/%Y}")

    # lotes que operó cada operador cada año (petróleo y líquidos con volumen), con el nombre de empresa que usa la página
    liq = prod[(prod["VOLUMEN"] > 0) & (prod["PRODUCTO"] != "GAS NATURAL")]
    ops = (liq.groupby(["AÑO", "DEPARTAMENTO", "EMPRESA", "LOTE"], as_index=False)["VOLUMEN"].sum()
           .rename(columns={"VOLUMEN": "VOLUMEN_LIQUIDOS_BARRILES"}))
    _guardar(ops.sort_values(["AÑO", "DEPARTAMENTO", "LOTE"]), salida / "hidro_lotes_operador.csv")
    lineas.append(f"hidro_lotes_operador.csv  {len(ops):,} filas")

    mapa = db.documento("mapa-hidrocarburos")
    if mapa:
        (salida / "PP_mapa_lotes_plus.html").write_text(mapa[0], encoding="utf-8")
        lineas.append(f"PP_mapa_lotes_plus.html  mapa de lotes ({mapa[1][:10]})")

    lineas += ["", "Fuente: PERUPETRO (producción fiscalizada mensual y diaria; canon y sobrecanon).",
               "Enlace fijo de cada archivo:",
               "https://github.com/adriansivina-droid/scraper-mef/releases/download/hidrocarburos-datos/<archivo>"]
    (salida / "LEEME.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8-sig")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
