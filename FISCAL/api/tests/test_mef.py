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


def test_huecos_y_remiendo_conservan_lo_guardado(cliente, monkeypatch):
    """Una función cuya consulta falló (CSV HUECOS) no borra lo que ya tenía la página, y un remiendo (« - FUNCIONES 15»)
    reemplaza solo esa función; el control de un remiendo solo pisa sus códigos. El botón Corregir arma el remiendo."""
    from tests.test_api import _csv, zip_de
    import pandas as pd
    suf = "02 - 08 - 21"
    fila = lambda f, m, v, mes=11: dict(AÑO=2025, MES=f"{mes}: Noviembre", DEPARTAMENTO="02: ÁNCASH", FUNCION=f, MUNICIPALIDAD=m, DEVENGADO=v)
    dev = f"output/DEVENGADO/Gobierno Municipal/DEV Funcion.Municipalidad 2025 - Mes 11 - {suf}"
    ctl = f"output/DEVENGADO/CARPETA DE CONTROL/CONTROL Municipalidad 2025 - Mes 11 - {suf}"
    # 1) carga buena: transporte y educación
    r = cliente.post("/v1/cargas", files=[("archivos", ("a.zip", zip_de({f"{dev}.csv": _csv(pd.DataFrame([
        fila("15: TRANSPORTE", "MUNI A", 5000.0), fila("22: EDUCACION", "MUNI A", 300.0)]))}), "application/zip"))])
    assert r.status_code == 200, r.text
    # 2) corrida con el transporte fallido: el hueco conserva los 5000
    r = cliente.post("/v1/cargas", files=[("archivos", ("b.zip", zip_de({
        f"{dev}.csv": _csv(pd.DataFrame([fila("22: EDUCACION", "MUNI A", 310.0)])),
        f"output/DEVENGADO/CARPETA DE CONTROL/HUECOS Funcion.Municipalidad 2025 - Mes 11.csv": _csv(pd.DataFrame([
            dict(AÑO=2025, MES=11, COD_DEPTO="02", COD_FUNCION="15", ERROR="ConnectionError")])),
        f"{ctl}.csv": _csv(pd.DataFrame([dict(AÑO=2025, DEPARTAMENTO="02: ÁNCASH", COD_FUNCION="15", DEV_REF_ANUAL=5400.0),
                                         dict(AÑO=2025, DEPARTAMENTO="02: ÁNCASH", COD_FUNCION="22", DEV_REF_ANUAL=310.0)]))}), "application/zip"))])
    assert r.status_code == 200, r.text
    assert any("se mantuvieron 1 filas de funciones cuya consulta falló" in a for a in r.json()["avisos"])
    guardado = db.leer("inv-dev-municipalidad", ["02"], [], "2025-11", "2025-11")
    assert dict(zip(guardado["FUNCION"], guardado["DEVENGADO"])) == {"15: TRANSPORTE": 5000.0, "22: EDUCACION": 310.0}
    func = db.leer("inv-dev-funcion", ["02"], ["M"], "2025-11", "2025-11")
    assert func["DEVENGADO"].sum() == 5310.0                  # la suma municipal también conserva el transporte
    # 3) el control marca transporte (-400) y el botón Corregir arma un remiendo solo de esa función
    control = cliente.get("/v1/mef/archivos/control?archivo=dev-municipalidad").json()["control"]
    assert [(f["depto"], f["estado"], f["dif"]) for f in control] == [("02", "revisar", -400.0)]
    lanzado = []
    monkeypatch.setenv("GITHUB_ACCIONES_TOKEN", "tok")
    monkeypatch.setattr(mef.requests, "post", lambda url, headers=None, json=None, timeout=None: lanzado.append(json) or Respuesta(204))
    assert cliente.post("/v1/mef/archivos/corregir?umbral=500").json()["lanzado"] is False
    r = cliente.post("/v1/mef/archivos/corregir?umbral=200").json()
    assert r["lanzado"] and r["casos"][0]["nombre"] == "Áncash"
    assert lanzado[-1]["inputs"] == {"archivo": "dev-municipalidad", "desde": "2025-01", "hasta": "2025-12", "departamentos": "02",
                                     "funciones": "15", "prueba": False}
    # 4) el remiendo trae solo transporte: educación queda como estaba y el control solo pisa el código 15
    r = cliente.post("/v1/cargas", files=[("archivos", ("c.zip", zip_de({
        f"{dev} - FUNCIONES 15.csv": _csv(pd.DataFrame([fila("15: TRANSPORTE", "MUNI A", 5100.0), fila("15: TRANSPORTE", "MUNI B", 300.0)])),
        f"{ctl} - FUNCIONES 15.csv": _csv(pd.DataFrame([dict(AÑO=2025, DEPARTAMENTO="02: ÁNCASH", COD_FUNCION="15", DEV_REF_ANUAL=5400.0)]))}),
        "application/zip"))])
    assert r.status_code == 200, r.text
    guardado = db.leer("inv-dev-municipalidad", ["02"], [], "2025-11", "2025-11")
    assert sorted(zip(guardado["FUNCION"], guardado["MUNICIPALIDAD"], guardado["DEVENGADO"])) == [
        ("15: TRANSPORTE", "MUNI A", 5100.0), ("15: TRANSPORTE", "MUNI B", 300.0), ("22: EDUCACION", "MUNI A", 310.0)]
    control = cliente.get("/v1/mef/archivos/control?archivo=dev-municipalidad").json()["control"]
    assert [(f["depto"], f["estado"], f["mef"], f["pagina"]) for f in control] == [("02", "coincide", 5710.0, 5710.0)]


def test_extraer_funcion_reintenta_y_anota_huecos(monkeypatch):
    """El notebook: una consulta municipal que falla dos veces queda en HUECOS; SOLO_FUNCIONES filtra; la referencia anual
    no baja a municipalidad. (Se ejecuta la celda de extractores con el MEF simulado.)"""
    import importlib, json, re, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "automatizacion"))
    servidor = importlib.import_module("scraper_servidor")
    assert any("SOLO_FUNCIONES = ['15']" in c for c in servidor.celdas({"SOLO_FUNCIONES": ["15"]}))
    nb = json.loads(servidor.NOTEBOOK.read_text(encoding="utf-8"))
    extractores = next("".join(c["source"]) for c in nb["cells"] if "BLOQUE 4 · EXTRACTORES" in "".join(c["source"]))
    consultas = []

    def filas_de(anio, mes, nivel, depto, ruta, agrupar, ctx, candidatos=None):
        consultas.append((mes, ruta[-1]))
        if agrupar == "8":                                 # funciones
            return [("15", "15: TRANSPORTE", 900.0, 0), ("22", "22: EDUCACION", 100.0, 0)], None, None
        if ruta[-1] == ("8", "15"):
            return [], "Función 02 > 15: ConnectionError", None
        return [("x", "MUNI A", 100.0, 0)], None, None

    g = {"filas_de": filas_de, "solo_muni": lambda n: [("37", "M")], "CLAVE_GENERICA": "24", "GENERICA_INVERSION": "6-2-6", "CLAVE_FUNCION": "8",
         "CLAVE_MUNICIPALIDAD": "7", "SIN_MANCOMUNIDADES": True, "_RE_MANCOM": re.compile("mancomunidad", re.I), "_CODIGO": re.compile(r"^(\d+)"),
         "FUNCIONES": {"15": "TRANSPORTE", "22": "EDUCACION"}, "meses_map": {"11": "11: Noviembre"}, "deptos_map": {"02": "02: ÁNCASH"},
         "NIVELES_GOB": {"M": {"etiqueta": "M: GOBIERNOS LOCALES"}}, "candidatos_de": lambda v, et: [v], "SOLO_FUNCIONES": None,
         "time": type("T", (), {"sleep": staticmethod(lambda s: None)}), "random": __import__("random")}
    exec(compile(extractores, "extractores", "exec"), g)
    regs, err, _ = g["extraer_funcion"](2025, "11", "M", "02")
    assert [r["FUNCION"] for r in regs] == ["22: EDUCACION"] and "ConnectionError" in err
    assert [(h["MES"], h["COD_DEPTO"], h["COD_FUNCION"]) for h in g["HUECOS"]] == [(11, "02", "15")]
    assert consultas.count(("11", ("8", "15"))) == 2           # reintentó una vez
    ref, err, _ = g["extraer_funcion"](2025, "", "M", "02", detalle=False)
    assert err is None and [(r["COD_FUNCION"], r["DEVENGADO"]) for r in ref] == [("15", 900.0), ("22", 100.0)]
    g["SOLO_FUNCIONES"] = ["22"]
    regs, err, _ = g["extraer_funcion"](2025, "11", "M", "02")
    assert err is None and [r["FUNCION"] for r in regs] == ["22: EDUCACION"]
