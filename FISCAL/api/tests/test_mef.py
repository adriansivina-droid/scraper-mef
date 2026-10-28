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
        return Respuesta(200, {"workflow_runs": [{"status": "in_progress", "conclusion": None, "event": "workflow_dispatch",
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
