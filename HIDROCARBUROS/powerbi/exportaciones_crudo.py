"""Exportaciones de petróleo crudo por lote, para Power BI, en la PC (el Excel de SUNAT no se publica en GitHub).

    python exportaciones_crudo.py          (o doble clic en «Actualizar exportaciones.bat»)

Lee los Excel «Petróleo crudo - <región>.xlsx» (hoja Consolidado, como se subían a la página) de CARPETA\\ENTRADA,
baja la producción de PERUPETRO de la Release de GitHub (hidro_produccion.csv) y asigna cada exportación al lote que
operaba la empresa ese año, con la misma regla de la página. Deja en CARPETA:
  · hidro_expo_empresa.csv   AÑO, MES, DEPARTAMENTO, RUC, EMPRESA, FOB_MM_USD (tal como el Excel)
  · hidro_expo_lote.csv      AÑO, DEPARTAMENTO, EMPRESA, RUC, LOTES, ESTIMADO (lote del año anterior: «*»), SIN_LOTE, FOB_MM_USD

La carpeta se elige en «configuracion.txt» (CARPETA = …); si no, Documentos\\Power BI\\Hidrocarburos.
"""
import importlib
import io
import sys
import types
import urllib.request
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
PRODUCCION = "https://github.com/adriansivina-droid/scraper-mef/releases/download/hidrocarburos-datos/hidro_produccion.csv"


def configuracion():
    conf = {"CARPETA": str(Path.home() / "Documents" / "Power BI" / "Hidrocarburos")}
    archivo = AQUI / "configuracion.txt"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                if v.strip():
                    conf[k.strip().upper()] = v.strip().strip('"')
    return {k: Path(v).expanduser() for k, v in conf.items()}


def modulo():
    """hidrocarburos.py de la página (copia en ./motor o, en el repositorio, FISCAL/api/app)."""
    fuente = next((p for p in (AQUI / "motor", AQUI.parents[1] / "FISCAL" / "api" / "app") if (p / "hidrocarburos.py").exists()), None)
    if fuente is None:
        sys.exit("No encuentro hidrocarburos.py (debe estar en la carpeta «motor» al lado de este archivo).")
    paquete = types.ModuleType("hidro_local")
    paquete.__path__ = [str(fuente)]
    sys.modules["hidro_local"] = paquete
    return importlib.import_module("hidro_local.hidrocarburos")


def produccion():
    with urllib.request.urlopen(PRODUCCION, timeout=120) as r:
        return pd.read_csv(io.BytesIO(r.read()), encoding="utf-8-sig", dtype={"LOTE": str, "LOTE_HISTORICO": str})


def main(prod=None):
    conf = configuracion()
    carpeta = conf["CARPETA"]
    entrada = carpeta / "ENTRADA"
    entrada.mkdir(parents=True, exist_ok=True)
    h = modulo()
    excels = [p for p in sorted(entrada.glob("*.xlsx")) if not p.name.startswith("~$")]
    if not excels:
        sys.exit(f"Deja en {entrada} los Excel «Petróleo crudo - <región>.xlsx» (hoja Consolidado).")
    expo = []
    for p in excels:
        try:
            expo.append(h.leer_expo_crudo(p))
            print(f"  {p.name}: {len(expo[-1])} filas")
        except Exception as e:                       # otro Excel en la carpeta: se avisa y se sigue
            print(f"  ⚠ {p.name}: {e}")
    if not expo:
        sys.exit("Ningún Excel tenía la hoja Consolidado de exportaciones de crudo.")
    expo = pd.concat(expo, ignore_index=True).drop(columns=["_depto", "_nivel"], errors="ignore")
    expo = expo.drop_duplicates(["AÑO", "MES", "DEPARTAMENTO", "RUC", "EMPRESA"], keep="last")
    expo.to_csv(carpeta / "hidro_expo_empresa.csv", index=False, encoding="utf-8-sig")
    prod = produccion() if prod is None else prod
    filas = []
    for depto, e in expo.groupby("DEPARTAMENTO"):
        r = h.exportaciones_crudo(e, prod, sin_lote=True)
        if not r:
            continue
        for emp in r["empresas"]:
            for a, v, ls in zip(r["anios"], emp["valores"], emp["lotes_anio"]):
                if v:
                    filas.append({"AÑO": a["anio"], "DEPARTAMENTO": depto, "EMPRESA": emp["nombre"], "RUC": emp["ruc"],
                                  "LOTES": " y ".join(l.rstrip("*") for l in ls) or "Sin lote",
                                  "ESTIMADO": int(any(l.endswith("*") for l in ls)), "SIN_LOTE": int(emp["sin_lote"]),
                                  "ANIO_PARCIAL": int(a["parcial"]), "FOB_MM_USD": v})
    lote = pd.DataFrame(filas)
    lote.to_csv(carpeta / "hidro_expo_lote.csv", index=False, encoding="utf-8-sig")
    print(f"hidro_expo_empresa.csv: {len(expo)} filas · hidro_expo_lote.csv: {len(lote)} filas → {carpeta}")
    print("Listo. En Power BI: Inicio → Actualizar.")


if __name__ == "__main__":
    main()
