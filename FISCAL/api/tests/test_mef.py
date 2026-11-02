"""Botón «Actualizar desde el MEF»: lanza el scraper en GitHub Actions (sin GitHub de verdad: se simulan sus respuestas)."""
import os

import pytest

from app import db, mef
from tests.test_api import cliente_http


class Respuesta:
    def __init__(self, codigo, datos=None):
        self.status_code, self._datos = codigo, datos or {}

    def json(self):
        return self._datos


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'mef.db'}")
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    yield cliente_http()
    db.reiniciar_motor()


@pytest.fixture()
def github(monkeypatch):
    llamadas = []
    monkeypatch.setenv("GITHUB_ACCIONES_TOKEN", "tok")

    def post(url, headers=None, json=None, timeout=None):
        llamadas.append(("POST", url, json, headers))
        return Respuesta(204)

    def get(url, headers=None, params=None, timeout=None):
        llamadas.append(("GET", url, params, headers))
        return Respuesta(200, {"workflow_runs": [{"id": 1, "status": "in_progress", "conclusion": None, "event": "workflow_dispatch",
                                                  "created_at": "2026-10-28T10:00:00Z", "updated_at": "2026-10-28T10:05:00Z",
                                                  "html_url": "https://github.com/x/y/actions/runs/1", "display_title": "Scraper del MEF · año en curso"}]})
    monkeypatch.setattr(mef.requests, "post", post)
    monkeypatch.setattr(mef.requests, "get", get)
    return llamadas


def test_sin_token(cliente, monkeypatch):
    monkeypatch.delenv("GITHUB_ACCIONES_TOKEN", raising=False)
    assert cliente.get("/v1/mef").json() == {"configurado": False, "corridas": []}
    assert cliente.post("/v1/mef/actualizar").status_code == 503


def test_lanza_y_muestra_corridas(cliente, github):
    r = cliente.post("/v1/mef/actualizar?desde=2025-01&hasta=2026-09")
    assert r.status_code == 200 and r.json()["lanzado"]
    metodo, url, cuerpo, enc = github[0]
    assert url.endswith("/actions/workflows/fiscal_scraper.yml/dispatches") and enc["Authorization"] == "Bearer tok"
    assert cuerpo == {"ref": "main", "inputs": {"desde": "2025-01", "hasta": "2026-09", "prueba": False}}
    e = cliente.get("/v1/mef").json()
    assert e["configurado"] and e["corridas"][0]["estado"] == "in_progress" and e["corridas"][0]["enlace"].startswith("https://github.com/")


def test_periodo_invalido_no_llama_a_github(cliente, github):
    assert cliente.post("/v1/mef/actualizar?desde=2026-13").status_code == 422
    assert cliente.post("/v1/mef/actualizar?desde=2026-09&hasta=2026-01").status_code == 422
    assert github == []


def test_token_sin_permiso(cliente, github, monkeypatch):
    monkeypatch.setattr(mef.requests, "post", lambda *a, **k: Respuesta(403))
    r = cliente.post("/v1/mef/actualizar")
    assert r.status_code == 502 and "permiso de Actions" in r.json()["detail"]


def test_archivos_propios_lanzan_su_flujo(cliente, github):
    e = cliente.get("/v1/mef/archivos").json()
    assert set(e["archivos"]) == {"dev-municipalidad", "pim-funcion", "pim-municipalidad"} and e["archivos"]["pim-funcion"]["filas"] == 0
    r = cliente.post("/v1/mef/archivos/actualizar?archivo=pim-municipalidad&desde=2026-01&departamentos=22,16")
    assert r.status_code == 200 and r.json()["departamentos"] == "16,22"
    url, cuerpo = github[-1][1], github[-1][2]
    assert url.endswith("/actions/workflows/fiscal_archivos.yml/dispatches")
    assert cuerpo["inputs"] == {"archivo": "pim-municipalidad", "desde": "2026-01", "hasta": "", "departamentos": "16,22", "prueba": False}
    todos = ",".join(f"{i:02d}" for i in range(1, 26))
    assert cliente.post(f"/v1/mef/archivos/actualizar?archivo=dev-municipalidad&departamentos={todos}").json()["departamentos"] == "TODOS"
    assert cliente.post("/v1/mef/archivos/actualizar?archivo=otro").status_code == 422
    assert cliente.post("/v1/mef/archivos/actualizar?archivo=pim-funcion&departamentos=98").status_code == 422


def test_scraper_de_un_archivo_solo_corre_su_bloque():
    import re
    import sys
    from datetime import date
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "automatizacion"))
    import scraper_servidor as s
    fijar = dict(s.ARCHIVOS["dev-municipalidad"]["fijar"], DEPARTAMENTOS_NACIONAL=["16"])
    lineas = [l for c in s.celdas(fijar) for l in c.split("\n") if re.match(r"^(BLOQUES_|NIVELES_A|DEPARTAMENTOS_NAC)", l)]
    assert "BLOQUES_MENSUALES = ['Funcion']" in lineas and "BLOQUES_ANUALES = []" in lineas and "NIVELES_A_CORRER = ['M']" in lineas
    assert s.periodo_anual("", "", date(2026, 10, 30)) == ("2026-01", "2026-09")
    assert s.periodo_anual("2024-05", "2027-03", date(2026, 10, 30)) == ("2024-01", "2026-09")
    assert s.periodo_anual("2025-01", "", date(2026, 10, 30)) == ("2025-01", "2025-12")


def test_barra_de_avance(cliente, github, monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "automatizacion"))
    import scraper_servidor as s
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    g = {"BLOQUES_MENSUALES": ["Funcion"], "NIVELES_A_CORRER": ["M"], "CONTROL_ANUAL": True, "BLOQUES_ANUALES": [],
         "PLAN": {2026: ["1", "2", "3"]}}
    av = s.Avance(g)
    assert av._esperadas() == 4                      # 3 meses + el control anual
    Barra = av.tqdm(lambda it, **k: it)
    list(Barra([], total=0))                          # un mes sin consultas no cuenta
    for _ in range(2):
        list(Barra(range(5), desc="2026 Enero"))
    av.avisar("Control Funcion.M 2026", forzar=True)
    e = cliente.get("/v1/mef/archivos").json()        # la corrida simulada (id 1) sigue en curso
    p = e["corridas"][0]["progreso"]
    assert p == [{"tramo": 1, "fraccion": 0.5, "texto": "Control Funcion.M 2026", "fecha": p[0]["fecha"]}]


def test_control_de_los_tres_archivos(cliente):
    """Los CSV de CONTROL de los tres archivos (25 departamentos) se guardan y se comparan con la base de la página."""
    from tests.test_api import _csv, zip_de
    import pandas as pd
    suf = "TODOS LOS DEPARTAMENTOS"
    s = {
        # devengado municipal (2.6) de Amazonas en dos meses de 2025 y su control (vista anual del MEF)
        f"output/DEVENGADO/Gobierno Municipal/DEV Funcion.Municipalidad 2025 - Meses 01-02 - {suf}.csv": _csv(pd.DataFrame([
            dict(AÑO=2025, MES=f"{m}: Mes", DEPARTAMENTO="01: AMAZONAS", FUNCION="15: TRANSPORTE", MUNICIPALIDAD="010101-300001: MUNICIPALIDAD X", DEVENGADO=1000.0)
            for m in (1, 2)])),
        f"output/DEVENGADO/CARPETA DE CONTROL/CONTROL Municipalidad 2025 - Meses 01-02 - {suf}.csv": _csv(pd.DataFrame([
            dict(AÑO=2025, DEPARTAMENTO="01: AMAZONAS", COD_FUNCION="15", DEV_SUMA_MESES=2000.0, DEV_REF_ANUAL=2000.0)])),
        # PIM por función de Áncash: el MEF dice 5000 y la página tiene 4000 (revisar)
        f"output/PIM/PIM X FUNCIÓN/DATA/PIM Funcion 2025 - {suf}.csv": _csv(pd.DataFrame([
            {"AÑO": 2025, "DEPARTAMENTO": "02: ÁNCASH", "NIVEL DE GOBIERNO": "GOBIERNOS REGIONALES", "FUNCION": "22: EDUCACION", "PIM": 4000.0}])),
        f"output/PIM/PIM X FUNCIÓN/CONTROL/CONTROL PIM Funcion 2025 - {suf}.csv": _csv(pd.DataFrame([
            dict(AÑO=2025, DEPARTAMENTO="02: ÁNCASH", COD_FUNCION="22", PIM_SUMA_NIVELES=4000.0, PIM_REF_TOTAL=5000.0)])),
        # PIM municipal de Apurímac y su control (PIM de gobiernos locales en el MEF)
        f"output/PIM/PIM X FUNCIÓN X MUNICIPALIDAD/DATA/PIM Funcion.Municipalidad 2025 - {suf}.csv": _csv(pd.DataFrame([
            dict(AÑO=2025, DEPARTAMENTO="03: APURÍMAC", FUNCION="18: SANEAMIENTO", MUNICIPALIDAD="030101-300100: MUNICIPALIDAD Y", PIM=700.0)])),
        f"output/PIM/PIM X FUNCIÓN X MUNICIPALIDAD/CONTROL/CONTROL PIM Funcion.Municipalidad 2025 - {suf}.csv": _csv(pd.DataFrame([
            dict(AÑO=2025, DEPARTAMENTO="03: APURÍMAC", COD_FUNCION="18", FUNCION="18: SANEAMIENTO", PIM_SUMA_MUNICIPIOS=700.0, PIM_REF_GL=700.0, DIF=0.0, ESTADO="OK")])),
    }
    r = cliente.post("/v1/cargas", files=[("archivos", ("output.zip", zip_de(s), "application/zip"))])
    assert r.status_code == 200, r.text
    dev = cliente.get("/v1/mef/archivos/control?archivo=dev-municipalidad").json()["control"]
    assert [(f["depto"], f["anio"], f["estado"], f["meses"]) for f in dev] == [("01", 2025, "coincide", "01 a 02")]
    assert dev[0]["nombre"] == "Amazonas"
    pim = cliente.get("/v1/mef/archivos/control?archivo=pim-funcion").json()["control"]
    assert [(f["depto"], f["estado"], f["dif"]) for f in pim] == [("02", "revisar", -1000.0)]
    assert pim[0]["funciones"] == [{"funcion": "22 Educación", "mef": 5000.0, "pagina": 4000.0, "dif": -1000.0}]
    muni = cliente.get("/v1/mef/archivos/control?archivo=pim-municipalidad").json()["control"]
    assert [(f["depto"], f["estado"]) for f in muni] == [("03", "coincide")]
    assert cliente.get("/v1/mef/archivos/control?archivo=otro").status_code == 422


def test_cancelar_corrida(cliente, monkeypatch):
    """Solo se cancelan corridas en curso de los flujos de la página."""
    monkeypatch.setenv("GITHUB_ACCIONES_TOKEN", "tok")
    corridas = {7: {"path": ".github/workflows/fiscal_archivos.yml", "status": "in_progress", "display_title": "dev-municipalidad · 2025-01 a 2026-10"},
                8: {"path": ".github/workflows/fiscal_scraper.yml", "status": "completed", "display_title": "Scraper del MEF"},
                9: {"path": ".github/workflows/otro.yml", "status": "in_progress", "display_title": "otro"}}
    canceladas = []
    monkeypatch.setattr(mef.requests, "get", lambda url, headers=None, timeout=None, **k: Respuesta(200, corridas[int(url.rsplit("/", 1)[1])]))
    monkeypatch.setattr(mef.requests, "post", lambda url, headers=None, timeout=None, **k: canceladas.append(url) or Respuesta(202))
    r = cliente.post("/v1/corridas/cancelar?id=7")
    assert r.status_code == 200 and r.json()["estado"] == "cancelando"
    assert canceladas == ["https://api.github.com/repos/adriansivina-droid/scraper-mef/actions/runs/7/cancel"]
    assert cliente.post("/v1/corridas/cancelar?id=8").status_code == 422      # ya terminó
    assert cliente.post("/v1/corridas/cancelar?id=9").status_code == 422      # no es de la página
    assert len(canceladas) == 1
    monkeypatch.delenv("GITHUB_ACCIONES_TOKEN")
    assert cliente.post("/v1/corridas/cancelar?id=7").status_code == 503


def test_periodo_elegido_en_cuatro_tramos():
    """DEV Función·Municipalidad de los 25 departamentos: un periodo elegido se parte en tramos seguidos (un job cada uno)."""
    import importlib, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "automatizacion"))
    partir = importlib.import_module("scraper_servidor").partir
    assert [partir("2025-01", "2025-12", 4, k) for k in range(1, 5)] == [("2025-01", "2025-03"), ("2025-04", "2025-06"), ("2025-07", "2025-09"), ("2025-10", "2025-12")]
    assert [partir("2026-01", "2026-10", 4, k) for k in range(1, 5)] == [("2026-01", "2026-03"), ("2026-04", "2026-06"), ("2026-07", "2026-08"), ("2026-09", "2026-10")]
    assert [partir("2026-09", "2026-09", 4, k) for k in range(1, 5)] == [("2026-09", "2026-09"), None, None, None]
    assert partir("2025-11", "2026-02", 2, 2) == ("2026-01", "2026-02")
