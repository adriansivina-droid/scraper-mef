"""Hidrología para Power BI, en tu PC (SENAMHI no responde a servidores: la recolección la hace el navegador).

Cada día:
  1. En https://www.senamhi.gob.pe/?p=monitoreo-hidrologico, F12 → Console, pega la línea del recolector y «Iniciar»
     (HIDROLOGIA/senamhi_rios.md). Al terminar descarga «SENAMHI_crudo_AAAA-MM-DD.json» en Descargas.
  2. Doble clic en «Actualizar hidrologia.bat» (o: python actualizar_hidrologia.py).
  3. En Power BI: Inicio → Actualizar.

Qué hace: toma los SENAMHI_crudo_*.json de Descargas (y de CARPETA\\ENTRADA), guarda sus piezas en el historial
(CARPETA\\hidrologia.sqlite, que reemplaza a la tabla de la página) y vuelve a armar en CARPETA\\DATA y CARPETA\\CONTROL los
mismos CSV que descargaba la página (diario, mensual, estaciones, controles). Los JSON ya leídos pasan a
CARPETA\\ENTRADA\\procesados.

La carpeta se elige en «configuracion.txt» (al lado de este archivo), línea CARPETA = …; si no hay, se usa
Documentos\\Power BI\\Hidrologia. El primer historial (lo que tenía la página) es el hidrologia.sqlite del flujo
«Hidrología · respaldo para Power BI» de GitHub: se copia a la CARPETA antes de la primera actualización.
"""
import importlib
import json
import os
import shutil
import sys
import types
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine

AQUI = Path(__file__).resolve().parent


def configuracion():
    conf = {"CARPETA": str(Path.home() / "Documents" / "Power BI" / "Hidrologia"), "DESCARGAS": str(Path.home() / "Downloads")}
    archivo = AQUI / "configuracion.txt"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                if v.strip():
                    conf[k.strip().upper()] = v.strip().strip('"')
    for k in ("CARPETA", "DESCARGAS"):                      # en GitHub Actions: HIDRO_CARPETA y HIDRO_DESCARGAS
        if os.environ.get(f"HIDRO_{k}"):
            conf[k] = os.environ[f"HIDRO_{k}"]
    return {k: Path(v).expanduser() for k, v in conf.items()}


def motor_hidrologia(sqlite):
    """El módulo de hidrología de la página (copia en ./motor o, en el repositorio, FISCAL/api/app) sobre el SQLite local."""
    fuente = next((p for p in (AQUI / "motor", AQUI.parents[1] / "FISCAL" / "api" / "app") if (p / "hidrologia.py").exists()), None)
    if fuente is None:
        sys.exit("No encuentro hidrologia.py (debe estar en la carpeta «motor» al lado de este archivo).")
    paquete = types.ModuleType("senamhi_local")
    paquete.__path__ = [str(fuente)]
    sys.modules["senamhi_local"] = paquete
    db = types.ModuleType("senamhi_local.db")
    motor = create_engine(f"sqlite:///{sqlite}")
    db.motor = lambda: motor
    sys.modules["senamhi_local.db"] = db
    return importlib.import_module("senamhi_local.hidrologia")


def main():
    conf = configuracion()
    carpeta, descargas = conf["CARPETA"], conf["DESCARGAS"]
    entrada, procesados = carpeta / "ENTRADA", carpeta / "ENTRADA" / "procesados"
    for d in (carpeta, entrada, procesados):
        d.mkdir(parents=True, exist_ok=True)
    print(f"Carpeta de Power BI: {carpeta}")
    hid = motor_hidrologia(carpeta / "hidrologia.sqlite")

    nuevos = sorted({*descargas.glob("SENAMHI_crudo_*.json"), *entrada.glob("SENAMHI_crudo_*.json")}, key=lambda p: p.name)
    nuevos = [p for p in nuevos if "prueba" not in p.name]
    if not nuevos and not hid.hay_datos():
        sys.exit("No hay datos: copia primero hidrologia.sqlite (el respaldo de la página) a la carpeta, o deja en "
                 "Descargas un SENAMHI_crudo_AAAA-MM-DD.json del recolector.")
    for p in nuevos:
        crudo = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(crudo, dict) or not crudo.get("meta") or not isinstance(crudo.get("graficas"), list):
            print(f"  ⚠ {p.name}: no es el JSON del recolector; se deja donde está.")
            continue
        dia = crudo["meta"].get("hoy") or str(crudo.get("generado", ""))[:10]
        r = hid.guardar(hid.piezas_de_archivo(crudo), dia)
        print(f"  {p.name}: {r['guardadas']} piezas guardadas, {r['omitidas_por_viejas']} más viejas que lo que ya había")
        destino = procesados / p.name
        if destino.exists():
            destino.unlink()
        shutil.move(str(p), destino)

    print("Armando los CSV…")
    tmp = carpeta / "_armando"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    resumen = hid.armar(tmp)
    for sub in ("DATA", "CONTROL"):
        (carpeta / sub).mkdir(exist_ok=True)
    for clave, nombre in hid.ARCHIVOS.items():
        sub = "CONTROL" if clave.startswith(("control", "log")) else "DATA"
        if (tmp / nombre).exists():
            shutil.move(str(tmp / nombre), carpeta / sub / nombre)        # reemplaza el anterior
    shutil.rmtree(tmp, ignore_errors=True)
    lineas = [f"Actualizado: {datetime.now():%d/%m/%Y %H:%M}"] + [f"{k}: {v}" for k, v in resumen.items() if not isinstance(v, (dict, list))]
    (carpeta / "LEEME.txt").write_text("HIDROLOGÍA (SENAMHI) · ARCHIVOS PARA POWER BI\n" + "\n".join(lineas) + "\n", encoding="utf-8-sig")
    print("\n".join(lineas))
    print("Listo. En Power BI: Inicio → Actualizar.")


if __name__ == "__main__":
    main()
