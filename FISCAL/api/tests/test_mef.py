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
