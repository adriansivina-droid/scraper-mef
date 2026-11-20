"""ESTAD de Ejecución del presupuesto: las hojas de gasto e inversión del ESTAD armadas con las bases del MEF, fila por
fila según su etiqueta (cada región las ordena y nombra a su manera)."""
import io
import os
from datetime import datetime

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from app import db, estad_fiscal
from tests.test_api import cliente_http


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'estad.db'}")
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    yield cliente_http()
    db.reiniciar_motor()


def _base(base_id, filas):
    df = pd.DataFrame(filas)
    df = df.assign(_anio=df["AÑO"], _mes=df["MES"].str[:2].astype(int), _depto="16", _nivel=df["NIVEL_GOBIERNO"].str[0])
    db.guardar(base_id, df)


def datos():
    """Gobierno Regional de Loreto, enero y febrero de 2026 (soles)."""
    g, f, fu, ifu = [], [], [], []
    for mes, k in (("01: Enero", 1), ("02: Febrero", 2)):
        com = {"AÑO": 2026, "MES": mes, "NIVEL_GOBIERNO": "R: GOBIERNOS REGIONALES", "DEPARTAMENTO": "16: LORETO"}
        for cod, v, des in (("5-2-1", 100_000, "SIN DESGLOSE"), ("5-2-3", 20_400, "SIN DESGLOSE"), ("5-2-4", 3_000, "SIN DESGLOSE"),
                            ("6-2-4", 5_000, "SIN DESGLOSE"), ("6-2-6", 50_000, "SIN DESGLOSE"), ("7-2-8", 1_000, "AMORTIZACIÓN"),
                            ("7-2-8", 200, "INTERESES Y COMISIONES")):
            g.append({**com, "COD_GENERICA": cod, "GENERICA": cod, "DESGLOSE": des, "DEVENGADO": float(v * k)})
        for cod, v in (("1", 150_000), ("5", 29_600)):
            f.append({**com, "GENERICA": "TODAS", "COD_FUENTE": cod, "FUENTE": cod, "DEVENGADO": float(v * k)})
        for fun, v in (("15: TRANSPORTE", 30_000), ("16: COMUNICACIONES", 2_000), ("22: EDUCACION", 18_000)):
            fu.append({**com, "ENTIDAD": "GR", "FUNCION": fun, "DEVENGADO": float(v * k)})
        for cod, v in (("1", 40_000), ("5", 10_000)):
            ifu.append({**com, "GENERICA": "6-2-6", "COD_FUENTE": cod, "FUENTE": cod, "DEVENGADO": float(v * k)})
    _base("gasto-dev-generica", g); _base("gasto-dev-fuente", f); _base("inv-dev-funcion", fu); _base("inv-dev-fuente", ifu)


def libro():
    """Un ESTAD de Loreto con dos hojas fiscales (filas en otro orden, etiquetas con errores de tipeo y una repetida)."""
    wb = Workbook()
    wb.active.title = "15.Export"
    meses = [datetime(2025, 12, 1), datetime(2026, 1, 1), datetime(2026, 2, 1)]
    def hoja(nombre, titulo, filas):
        ws = wb.create_sheet(nombre)
        ws["A1"], ws["A2"], ws["A3"] = "CUADRO Nº 21", titulo, "(Miles de Soles)"
        for j, m in enumerate(meses, 2):
            ws.cell(5, j, m)
        for i, (et, vals) in enumerate(filas, 7):
            ws.cell(i, 1, et)
            for j, v in enumerate(vals, 2):
                if v is not None:
                    ws.cell(i, j, v)
        ws.cell(7 + len(filas) + 1, 1, "Fuente: MEF.")
        ws.cell(7 + len(filas) + 4, 1, "LORETO: GASTOS (REALES)")       # el cuadro en reales de abajo no se toca
    hoja("GASTOS G.R.", "LORETO: GASTOS NO FINANCIEROS DEL GOBIERNO REGIONAL1/", [
        ("TOTAL DE GASTOS", [1, 180, 999]), ("GASTOS CORRIENTES", [1, 123, 246]), ("Personal y obligaciones", [1, 100, 200]),
        ("Bienes y servicios", [1, 20, 41]), ("Donaciones y transferencias", [1, 3, 6]), ("GASTOS DE CAPITAL", [1, 55, 110]),
        ("Donaciones y transferencias (2)", [1, 5, 10]), ("Adquisición de activos no financieros", [1, 50, 100]),
        ("SERVICIO DE LA DEUDA", [1, 1, 2]), ("Intereses+comisiones", [1, 0, 0]), ("Amortización", [1, 1, 2]), ("", [None] * 3),
        ("GASTOS POR FUENTE", [1, 180, 359]), ("Recursos ordinarios (Asignación MEF)", [1, 150, 300]), ("Recursos determinados", [1, 30, 59]),
        ("Recusos por operaiones de crédito", [None] * 3), ("Fondo de compensación regional", [None] * 3)])
    hoja("INVERSIÓN G.R.", "LORETO:  INVERSIÓN NO FINANCIERA DEL GOBIERNO REGIONAL", [
        ("INVERSIONES POR FUNCIONES", [1, 50, 100]), ("Educación", [1, 18, 36]), ("Transporte y Comunicaciones", [1, 32, 64]),
        ("Transporte y Comunicaciones", [None] * 3), ("FUENTES DE FINANCIAMIENTO", [1, 50, 100]), ("Recursos ordinarios", [1, 40, 80]),
        ("Recursos determinados", [1, 10, 20])])
    wb.create_sheet("INGRESOS G.R.")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_conceptos():
    assert estad_fiscal.concepto("Personal y obligaciones", "corriente", "gasto") == ("gen", ["5-2-1"])
    assert estad_fiscal.concepto("Donaciones y transferencias (2)", "capital", "gasto") == ("gen", ["6-2-4"])
    assert estad_fiscal.concepto("Donaciones y transferencias", "fuente", "gasto") == ("fue", ["4"])
    assert estad_fiscal.concepto("6-27: ADQUISICION DE ACTIVOS FINANCIEROS", "capital", "gasto") == ("gen", ["6-2-7"])
    assert estad_fiscal.concepto("Recusos por operaiones de crédito", "fuente", "inversion") == ("ifu", ["3"])
    assert estad_fiscal.concepto("4: DONACIONES Y TRANSFERENCIAS", "fuente", "gasto") == ("fue", ["4"])
    assert estad_fiscal.concepto("Transporte y Comunicaciones", None, "inversion") == ("fun", ["15", "16"])
    assert estad_fiscal.concepto("Medio Ambiente", None, "inversion") == ("fun", ["17"])
    assert estad_fiscal.concepto("Fondo de compensación regional", "fuente", "gasto") is None
    assert estad_fiscal.hoja_fiscal("INGRESOS G.R.") is None and estad_fiscal.hoja_fiscal("INVERSIÓN G.L.") == ("M", "inversion")


def test_estad_fiscal_con_el_libro_subido(cliente, tmp_path):
    datos()
    r = cliente.post("/v1/cargas", files=[("archivos", ("ESTADLO.xlsx", libro(), "application/octet-stream"))])
    assert r.status_code == 200 and any("2 hojas de gasto e inversión de Loreto" in a for a in r.json()["avisos"])
    e = cliente.get("/v1/ejecucion/estad?departamento=16&desde=2026-01&hasta=2026-02").json()
    assert e["origen"]["subido"] and e["meses"] == ["2026-01", "2026-02"] and [h["hoja"] for h in e["hojas"]] == ["GASTOS G.R.", "INVERSIÓN G.R."]
    g = {f["etiqueta"]: f for f in e["hojas"][0]["filas"]}
    assert g["TOTAL DE GASTOS"]["valores"] == {"2026-01": 180, "2026-02": 359}             # miles de soles, redondeado
    assert g["Bienes y servicios"]["valores"]["2026-02"] == 41 and g["Amortización"]["valores"]["2026-01"] == 1
    assert g["Recursos determinados"]["valores"]["2026-01"] == 30
    assert not g["Fondo de compensación regional"]["llena"]
    inv = e["hojas"][1]["filas"]
    tc = [f for f in inv if f["etiqueta"] == "Transporte y Comunicaciones"]
    assert tc[0]["valores"]["2026-01"] == 32 and not tc[1]["llena"]                      # la repetida no se llena
    # diferencias con el ESTAD subido: el total de febrero (999 contra 359); diciembre no se pidió
    assert [(d["etiqueta"], d["mes"]) for d in e["diferencias"]] == [("TOTAL DE GASTOS", "2026-02")]
    x = cliente.get("/v1/ejecucion/estad?departamento=16&desde=2026-01&hasta=2026-02&formato=xlsx")
    wb = load_workbook(io.BytesIO(x.content))
    ws = wb["GASTOS G.R."]
    assert ws["A7"].value == "TOTAL DE GASTOS" and ws["B7"].value == 180 and ws["C7"].value == 359 and ws["B5"].value == datetime(2026, 1, 1)
    assert wb["Diferencias"]["C2"].value == "TOTAL DE GASTOS"


def test_estad_fiscal_sin_libro_usa_el_de_la_pagina(cliente):
    datos()
    e = cliente.get("/v1/ejecucion/estad?departamento=16").json()
    assert not e["origen"]["subido"] and e["hasta"] == "2026-02" and e["desde"] == "2026-01"
    assert len(e["hojas"]) == 6 and e["diferencias"] == []
    gr = next(h for h in e["hojas"] if h["hoja"] == "GASTOS G.R.")
    assert next(f for f in gr["filas"] if f["etiqueta"] == "TOTAL DE GASTOS")["valores"]["2026-02"] == 359
    assert cliente.get("/v1/ejecucion/estad?departamento=22").status_code == 404
