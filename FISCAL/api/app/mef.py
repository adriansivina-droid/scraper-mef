"""Scrapers lanzados desde la página: «Actualizar desde el MEF» (.github/workflows/fiscal_scraper.yml) y «Actualizar
empleo» (empleo_scraper.yml) piden una corrida a GitHub Actions y muestran sus últimas corridas. Los scrapers no corren
en Render: duran varios minutos y GitHub lo hace gratis; al terminar cargan los datos en la misma base de datos
(FISCAL/automatizacion/scraper_servidor.py y EMPLEO/automatizacion/empleo_servidor.py).

Necesita GITHUB_ACCIONES_TOKEN: un token de GitHub (fine-grained) con acceso solo a este repositorio y permiso
Actions: lectura y escritura. Pasos en FISCAL/api/README.md.
"""
import os
import re

import requests

REPO = os.environ.get("GITHUB_REPO", "adriansivina-droid/scraper-mef")
FLUJOS = {"mef": "fiscal_scraper.yml", "empleo": "empleo_scraper.yml"}   # scrapers que se lanzan desde la página


def _api(nombre):
    return f"https://api.github.com/repos/{REPO}/actions/workflows/{FLUJOS[nombre]}"


_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ErrorGitHub(Exception):
    pass


def configurado():
    return bool(os.environ.get("GITHUB_ACCIONES_TOKEN", "").strip())


def _encabezados():
    return {"Authorization": f"Bearer {os.environ['GITHUB_ACCIONES_TOKEN'].strip()}",
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _fallo(r):
    motivo = {401: "el token no es válido o venció", 403: "el token no tiene permiso de Actions (lectura y escritura)",
              404: "el token no tiene acceso al repositorio o no existe el flujo"}.get(r.status_code, f"HTTP {r.status_code}")
    return ErrorGitHub(f"GitHub rechazó la solicitud: {motivo}.")


def lanzar(desde="", hasta="", prueba=False, nombre="mef", inputs=None):
    """Pide a GitHub una corrida del scraper. MEF: desde/hasta vacíos = año en curso hasta el último mes cerrado."""
    for p in (desde, hasta):
        if p and not _PERIODO.match(p):
            raise ValueError(f"Periodo no válido: {p!r} (formato AAAA-MM).")
    if desde and hasta and desde > hasta:
        raise ValueError(f"El periodo está al revés: {desde} es posterior a {hasta}.")
    entradas = inputs if inputs is not None else {"desde": desde, "hasta": hasta, "prueba": bool(prueba)}
    r = requests.post(f"{_api(nombre)}/dispatches", headers=_encabezados(), timeout=30, json={"ref": "main", "inputs": entradas})
    if r.status_code != 204:
        raise _fallo(r)


def corridas(cuantas=5, nombre="mef"):
    """Últimas corridas: estado, resultado, quién la lanzó (programada o a mano) y enlace."""
    r = requests.get(f"{_api(nombre)}/runs", headers=_encabezados(), params={"per_page": cuantas}, timeout=30)
    if r.status_code != 200:
        raise _fallo(r)
    return [{"estado": c["status"], "resultado": c.get("conclusion"), "origen": c["event"], "inicio": c["created_at"],
             "actualizado": c["updated_at"], "enlace": c["html_url"], "titulo": c.get("display_title", "")}
            for c in r.json().get("workflow_runs", [])]
