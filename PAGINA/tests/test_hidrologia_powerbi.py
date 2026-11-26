"""Hidrología para Power BI en la PC (HIDROLOGIA/powerbi/actualizar_hidrologia.py): lee el JSON del recolector de
Descargas, guarda el historial en un SQLite local y arma los CSV en DATA y CONTROL."""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from tests.test_hidrologia import crudo

RUTA = Path(__file__).resolve().parents[2] / "HIDROLOGIA" / "powerbi" / "actualizar_hidrologia.py"


def _modulo():
    spec = importlib.util.spec_from_file_location("actualizar_hidrologia", RUTA)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_actualizar_hidrologia_local(tmp_path, monkeypatch):
    for k in [k for k in sys.modules if k.startswith("senamhi_local")]:
        monkeypatch.delitem(sys.modules, k)
    carpeta, descargas = tmp_path / "PBI", tmp_path / "Descargas"
    descargas.mkdir()
    (descargas / "SENAMHI_crudo_2026-11-12.json").write_text(json.dumps(crudo()), encoding="utf-8")
    m = _modulo()
    monkeypatch.setattr(m, "configuracion", lambda: {"CARPETA": carpeta, "DESCARGAS": descargas})
    m.main()
    diario = pd.read_csv(carpeta / "DATA" / "SENAMHI_rios_diario.csv", encoding="utf-8-sig", dtype={"COD_ESTACION": str})
    assert len(diario) and set(diario["COD_ESTACION"]) >= {"240001"}
    assert (carpeta / "DATA" / "SENAMHI_ESTACIONES.csv").exists() and (carpeta / "CONTROL" / "CONTROL SENAMHI rios_diario.csv").exists()
    assert (carpeta / "ENTRADA" / "procesados" / "SENAMHI_crudo_2026-11-12.json").exists()
    assert not list(descargas.iterdir()) and (carpeta / "hidrologia.sqlite").exists()
    n = len(diario)
    m.main()                                       # sin JSON nuevos: rearma con el historial
    assert len(pd.read_csv(carpeta / "DATA" / "SENAMHI_rios_diario.csv", encoding="utf-8-sig")) == n
