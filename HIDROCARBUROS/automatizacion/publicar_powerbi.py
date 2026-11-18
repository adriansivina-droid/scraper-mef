"""Arma los archivos que lee Power BI a partir de la base de hidrocarburos (la de DATABASE_URL; en GitHub Actions, el
SQLite «almacen.sqlite» que se guarda en la Release «hidrocarburos-datos» del repositorio).

    python publicar_powerbi.py CARPETA_DE_SALIDA

Deja en la carpeta:
  · hidro_produccion.csv   producción fiscalizada por mes, departamento, lote, operador y producto (PERUPETRO), sin doble
                           conteo: los meses que la estadística mensual aún no publica salen de la producción diaria
                           (columna FUENTE); el mes en curso, incompleto, trae PARCIAL = 1
  · hidro_canon.csv        canon y sobrecanon petrolero transferido por mes y departamento (millones de soles)
  · hidro_lotes_operador.csv  qué lotes operó cada operador en cada año
  · hidro_lotes_ruc.csv    el lote de cada RUC exportador de crudo por año (para cruzar con el Excel de exportaciones)
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
from app import almacen, db, hidrocarburos  # noqa: E402
from sqlalchemy import text  # noqa: E402

# lo que no va en la Release pública: las exportaciones por empresa (Excel de SUNAT que se subía a la página)
PRIVADOS = ("PP_exportaciones_crudo%",)


def quitar_privados():
    """Borra del almacén (que se publica) los archivos de PRIVADOS y la base de exportaciones por empresa."""
    tabla = db.BASES["hidro-expo-empresa"].tabla
    hay_tabla = db.existe(tabla)
    with db.motor().begin() as cx:
        n = sum(cx.execute(text("DELETE FROM almacen WHERE nombre LIKE :p"), {"p": p}).rowcount for p in PRIVADOS)
        if hay_tabla:
            cx.execute(text(f'DROP TABLE "{tabla}"'))
            n += 1
    if n:
        print(f"  Quitados del almacén (no se publican): {n}")

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


def _lotes_por_ruc(prod):
    """AÑO, RUC, LOTES, ESTIMADO, SIN_LOTE de los exportadores de crudo conocidos, con la regla de la página (el lote que
    operaba la empresa ese año; si no produjo, el de hasta dos años antes, ESTIMADO = 1). Power BI lo cruza por RUC y año
    con el Excel de exportaciones, que no se publica."""
    anios = range(2000, int(prod["AÑO"].max()) + 1)
    rucs = {**{r: k[0] for r, k in hidrocarburos.OPERADOR_DE_RUC.items()}, **hidrocarburos.SIN_LOTE_RUC}
    falsa = pd.DataFrame([{"AÑO": a, "MES": 1, "DEPARTAMENTO": "LORETO", "RUC": r, "EMPRESA": n, "FOB_MM_USD": 1.0}
                          for r, n in rucs.items() for a in anios])
    r = hidrocarburos.exportaciones_crudo(falsa, prod, sin_lote=True)
    filas = [{"AÑO": a["anio"], "RUC": e["ruc"], "LOTES": " y ".join(l.rstrip("*") for l in ls) or "Sin lote",
              "ESTIMADO": int(any(l.endswith("*") for l in ls)), "SIN_LOTE": int(e["sin_lote"])}
             for e in r["empresas"] for a, ls in zip(r["anios"], e["lotes_anio"])]
    return pd.DataFrame(filas).sort_values(["RUC", "AÑO"])


def main():
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "powerbi")
    salida.mkdir(parents=True, exist_ok=True)
    almacen._tabla()
    quitar_privados()
    lineas = ["HIDROCARBUROS · ARCHIVOS PARA POWER BI", "=" * 60,
              f"Actualizado: {datetime.now(timezone(timedelta(hours=-5))):%d/%m/%Y %H:%M} (hora de Lima; GitHub Actions, flujo «Hidrocarburos · actualización»)", ""]

    prod = db.leer_todo("hidro-produccion")
    if prod is None or prod.empty:
        sys.exit("No hay producción de hidrocarburos en la base: nada que publicar.")
    prod = _periodo(prod)
    prod["VOLUMEN"] = pd.to_numeric(prod["VOLUMEN"], errors="coerce")
    prod["PROMEDIO_DIARIO"] = pd.to_numeric(prod["PROMEDIO_DIARIO"], errors="coerce")
    prod = prod.astype({"AÑO": int, "MES": int})
    emp = hidrocarburos._con_empresa(prod)["EMPRESA"]          # el nombre homologado que usa la página
    prod.insert(prod.columns.get_loc("OPERADOR") + 1, "EMPRESA", emp.map(lambda e: hidrocarburos.nombre_empresa(e) if e else ""))
    # como la página: la estadística mensual primero y la producción diaria solo donde aquella aún no llega (si no, se
    # sumaría dos veces); el mes en curso, incompleto, va aparte con PARCIAL = 1 (solo para gráficos, no para cuadros)
    lotes_ruc = _lotes_por_ruc(prod)
    unida, parcial, _ = hidrocarburos._unir(prod)
    partes = [unida.assign(PARCIAL=0)]
    if parcial:
        partes.append(parcial["filas"].assign(PARCIAL=1, LOTE_C=parcial["filas"]["LOTE_HISTORICO"].map(hidrocarburos._lote)))
    prod = pd.concat(partes, ignore_index=True).rename(columns={"LOTE_C": "LOTE_NOMBRE"}).drop(columns=["P"])
    prod = prod.sort_values(["PERIODO", "DEPARTAMENTO", "LOTE", "PRODUCTO"])
    _guardar(prod, salida / "hidro_produccion.csv")
    lineas.append(f"hidro_produccion.csv  {len(prod):,} filas · {prod['PERIODO'].min():%m/%Y} a {prod['PERIODO'].max():%m/%Y}"
                  + (f" ({parcial['P'] % 100:02d}/{parcial['P'] // 100} parcial: {parcial['dias']} de {parcial['de']} días, PARCIAL = 1)" if parcial else ""))

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

    _guardar(lotes_ruc, salida / "hidro_lotes_ruc.csv")
    lineas.append(f"hidro_lotes_ruc.csv  {len(lotes_ruc):,} filas (lote de cada RUC exportador, por año)")

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
