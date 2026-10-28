"""Fase 2: el botón «Actualizar desde el MEF» lanza el scraper en GitHub Actions (.github/workflows/fiscal_scraper.yml) y
muestra sus últimas corridas. El scraper no corre en Render: dura varios minutos y GitHub lo hace gratis; al terminar
carga los datos en la misma base de datos (FISCAL/automatizacion/scraper_servidor.py).

Necesita GITHUB_ACCIONES_TOKEN: un token de GitHub (fine-grained) con acceso solo a este repositorio y permiso
Actions: lectura y escritura. Pasos en FISCAL/api/README.md.
"""
import os
import re

import requests

REPO = os.environ.get("GITHUB_REPO", "adriansivina-droid/scraper-mef")
FLUJO = "fiscal_scraper.yml"
API = f"https://api.github.com/repos/{REPO}/actions/workflows/{FLUJO}"
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


def lanzar(desde="", hasta="", prueba=False):
    """Pide a GitHub una corrida del scraper. desde/hasta vacíos: año en curso hasta el último mes cerrado."""
    for p in (desde, hasta):
        if p and not _PERIODO.match(p):
            raise ValueError(f"Periodo no válido: {p!r} (formato AAAA-MM).")
    if desde and hasta and desde > hasta:
        raise ValueError(f"El periodo está al revés: {desde} es posterior a {hasta}.")
    r = requests.post(f"{API}/dispatches", headers=_encabezados(), timeout=30,
                      json={"ref": "main", "inputs": {"desde": desde, "hasta": hasta, "prueba": bool(prueba)}})
    if r.status_code != 204:
        raise _fallo(r)


def corridas(cuantas=5):
    """Últimas corridas: estado, resultado, quién la lanzó (programada o a mano) y enlace."""
    r = requests.get(f"{API}/runs", headers=_encabezados(), params={"per_page": cuantas}, timeout=30)
    if r.status_code != 200:
        raise _fallo(r)
    return [{"estado": c["status"], "resultado": c.get("conclusion"), "origen": c["event"], "inicio": c["created_at"],
             "actualizado": c["updated_at"], "enlace": c["html_url"], "titulo": c.get("display_title", "")}
            for c in r.json().get("workflow_runs", [])]
