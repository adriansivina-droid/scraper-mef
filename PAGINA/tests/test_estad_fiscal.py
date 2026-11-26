"""ESTAD de Ejecución del presupuesto: las hojas de gasto e inversión del ESTAD armadas con las bases del MEF, fila por
fila según su etiqueta (cada región las ordena y nombra a su manera)."""
import io
import os
from datetime import datetime

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from app import db
from app.fiscal import estad_fiscal
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
    assert estad_fiscal.hoja_fiscal("INGRESOS G.R.") == ("R", "ingresos") and estad_fiscal.hoja_fiscal("INVERSIÓN G.L.") == ("M", "inversion")


def test_estad_fiscal_con_el_libro_subido(cliente, tmp_path):
    datos()
    r = cliente.post("/v1/cargas", files=[("archivos", ("ESTADLO.xlsx", libro(), "application/octet-stream"))])
    assert r.status_code == 200 and any("2 hojas de gasto e inversión de Loreto" in a for a in r.json()["avisos"])
    e = cliente.get("/v1/ejecucion/estad?departamento=16&desde=2026-01&hasta=2026-02").json()
    assert e["origen"]["subido"] and e["meses"] == ["2026-01", "2026-02"] and [h["hoja"] for h in e["hojas"]] == ["GASTOS G.R.", "INVERSIÓN G.R."]
    g = {f["etiqueta"]: f for f in e["hojas"][0]["filas"]}
    assert g["TOTAL DE GASTOS"]["valores"] == {"2026-01": 179.6, "2026-02": 359.2}         # miles de soles, con decimales
    assert g["Bienes y servicios"]["valores"]["2026-02"] == 40.8 and g["Amortización"]["valores"]["2026-01"] == 1.0
    assert g["Recursos determinados"]["valores"]["2026-01"] == 29.6
    assert not g["Fondo de compensación regional"]["llena"]
    inv = e["hojas"][1]["filas"]
    tc = [f for f in inv if f["etiqueta"] == "Transporte y Comunicaciones"]
    assert tc[0]["valores"]["2026-01"] == 32.0 and not tc[1]["llena"]                      # la repetida no se llena
    # diferencias con el ESTAD subido: el total de febrero (999 contra 359); diciembre no se pidió
    assert [(d["etiqueta"], d["mes"]) for d in e["diferencias"]] == [("TOTAL DE GASTOS", "2026-02")]
    x = cliente.get("/v1/ejecucion/estad?departamento=16&desde=2026-01&hasta=2026-02&formato=xlsx")
    wb = load_workbook(io.BytesIO(x.content))
    ws = wb["GASTOS G.R."]                         # armado con el scraper: Ene..Dic 2026 en B..M y el total en N
    assert ws["A1"].value == "CUADRO Nº 21" and ws["A1"].font.bold and ws["A1"].font.name == "Arial"
    assert ws["B4"].value == 2026 and ws["B5"].value == "Ene." and ws["N4"].value == "Total"
    assert ws["A7"].value == "TOTAL DE GASTOS" and ws["B7"].value == 179.6 and ws["C7"].value == 359.2
    assert ws["B7"].number_format == "#,##0" and ws["B7"].font.underline == "single" and ws["N7"].value == "=SUM(B7:M7)"
    assert ws["D7"].value is None                                  # marzo: aún no hay datos
    assert ws["B9"].value == 100 and not ws["B9"].font.bold
    assert wb["Diferencias"]["C2"].value == "TOTAL DE GASTOS" and "15.Export" not in wb.sheetnames


def test_excel_del_scraper_con_reales_y_variaciones(cliente):
    """El Excel sale entero del scraper (sin ESTAD subido): todos los años, total por año, variaciones y cuadro en reales."""
    from app.fiscal import ipc
    datos()
    ipc.guardar({"2025-12": 99.0, "2026-01": 100.0, "2026-02": 100.5}, "prueba")
    _base("gasto-dev-generica", [{"AÑO": 2025, "MES": "02: Febrero", "NIVEL_GOBIERNO": "R: GOBIERNOS REGIONALES", "DEPARTAMENTO": "16: LORETO",
                                   "COD_GENERICA": "5-2-1", "GENERICA": "5-2-1", "DESGLOSE": "SIN DESGLOSE", "DEVENGADO": 50_000.0}])
    x = cliente.get("/v1/ejecucion/estad?departamento=16&formato=xlsx")
    ws = load_workbook(io.BytesIO(x.content))["GASTOS G.R."]
    # 2025 en B..M (total N), 2026 en O..Z (total AA); variaciones desde AC
    assert ws["B4"].value == 2025 and ws["O4"].value == 2026 and ws["C9"].value == 50.0 and ws["O9"].value == 100.0
    assert ws["AC4"].value == "Var.% 2026/2025" and ws["AC5"].value == "Feb." and ws["AD5"].value == "Ene.-Feb."
    assert ws["AC9"].value == '=IFERROR((P9/C9-1)*100,"")' and ws["AF9"].value == "=SUM(O9:P9)" and ws["AE9"].value == "=SUM(B9:C9)"
    # cuadro en reales: misma estructura, cada mes dividido por el deflactor (IPC de Lima en base 2009)
    reales = next(r for r in range(20, ws.max_row + 1) if str(ws.cell(r, 1).value or "").endswith("(REALES)"))
    r_def = reales + 1
    assert abs(ws.cell(r_def, 16).value - 100.5 / 100 * 1.56776) < 1e-9                  # P: febrero 2026
    assert abs(ws.cell(reales, 16).value - 0.5) < 1e-9                                   # var. % del IPC
    fila_total_real = next(r for r in range(r_def + 1, ws.max_row + 1) if ws.cell(r, 1).value == "TOTAL DE GASTOS")
    assert ws.cell(fila_total_real, 16).value == f'=IFERROR(P7/P${r_def},"")'


def test_estad_fiscal_sin_libro_usa_el_de_la_pagina(cliente):
    datos()
    e = cliente.get("/v1/ejecucion/estad?departamento=16").json()
    assert not e["origen"]["subido"] and e["hasta"] == "2026-02" and e["desde"] == "2026-01"
    assert len(e["hojas"]) == 8 and e["diferencias"] == []          # 6 de gasto e inversión y 2 de ingresos
    gr = next(h for h in e["hojas"] if h["hoja"] == "GASTOS G.R.")
    assert next(f for f in gr["filas"] if f["etiqueta"] == "TOTAL DE GASTOS")["valores"]["2026-02"] == 359.2
    assert cliente.get("/v1/ejecucion/estad?departamento=22").status_code == 404


def test_hojas_de_ingresos():
    """INGRESOS G.R./G.L.: cada fila según su etiqueta, con las convenciones de cada ESTAD."""
    from app.fiscal import estad_fiscal as ef
    principal = [(7, "TOTAL DE INGRESOS"), (9, "INGRESOS CORRIENTES"), (11, "3: VENTA DE BIENES Y SERVICIOS"), (12, "4: DONACIONES Y TRANSFERENCIAS"),
                 (13, "5: OTROS INGRESOS"), (17, "FINANCIAMIENTO"), (19, "9: SALDOS DE BALANCE"), (21, "TOTAL INGRESOS POR FUENTE"),
                 (23, "5: RECURSOS DETERMINADOS"), (24, "Privatizaciones y concesiones"), (25, "Fondo de compensación regional")]
    dyt = [(53, "4: DONACIONES Y TRANSFERENCIAS"), (54, "D y T CORRIENTES"), (58, "Del Gobierno Nacional"), (63, "Canon petrolero"),
           (64, "Sobrecanon petrolero"), (65, "Eliminación exoneraciones"), (67, "D DE CAPITAL"), (71, "Del Gobierno Nacional")]
    h = {"tipo": "ingresos", "filas": [{"fila": f, "etiqueta": e} for f, e in principal] + [{"fila": f, "etiqueta": e, "bloque": "dyt"} for f, e in dyt]}
    c = ef._conceptos(h)
    assert c[9]["filtro"] == [[1, "C:1-1"], [1, "C:1-2"], [1, "C:1-3"], [1, "C:1-4"], [1, "C:1-5"]]
    assert c[24]["filtro"] == c[25]["filtro"] == [[1, "Z"]]                        # en 0 (van en recursos determinados)
    assert c[58]["filtro"] == [[1, "H:1-4-1-3-1:NACIONAL"]] and c[71]["filtro"] == [[1, "H:1-4-2-3-1:NACIONAL"]]
    # sin fila de FONCOR, «Eliminación exoneraciones» lleva también el Fondo de Compensación Regional (como el ESTAD de Loreto)
    assert c[65]["filtro"] == [[1, "H:1-4-1-4:ELIMINACION"], [1, "H:1-4-1-4:COMPENSACION REGIONAL"]]
    d = {"ing": pd.DataFrame([
        {"N": "R", "P": "2026-01", "CLASIFICADOR": "ESPECIFICA_DETALLE", "CODIGO": "1-4-1-4-1-1", "K": "CANON PETROLERO", "V": 10.0},
        {"N": "R", "P": "2026-01", "CLASIFICADOR": "ESPECIFICA_DETALLE", "CODIGO": "1-4-1-4-1-2", "K": "SOBRECANON PETROLERO", "V": 5.0},
        {"N": "R", "P": "2026-01", "CLASIFICADOR": "ESPECIFICA", "CODIGO": "1-4-1-4-7", "K": "FONDO DE COMPENSACION REGIONAL", "V": 30.0},
        {"N": "R", "P": "2026-01", "CLASIFICADOR": "FUENTE", "CODIGO": "5", "K": "RECURSOS DETERMINADOS", "V": 45.0}])}
    assert ef._valor(d, "ing", c[63]["filtro"], "R", "2026-01") == 10.0            # canon, sin el sobrecanon
    assert ef._valor(d, "ing", c[65]["filtro"], "R", "2026-01") == 30.0
    assert ef._valor(d, "ing", c[23]["filtro"], "R", "2026-01") == 45.0 and ef._valor(d, "ing", c[24]["filtro"], "R", "2026-01") == 0
    assert ef._valor(d, "ing", c[23]["filtro"], "R", "2026-02") is None            # mes sin datos: vacío


def test_anexo_sin_activos_financieros():
    import pandas as pd
    from app.fiscal import ejecucion
    g = pd.DataFrame({"AÑO": [2025] * 3, "MES": ["10: Octubre"] * 3, "NIVEL_GOBIERNO": ["E: GOBIERNO NACIONAL"] * 3,
                      "COD_GENERICA": ["6-2-5", "6-2-7", "6-2-6"],
                      "GENERICA": ["6-25: OTROS GASTOS", "6-27: ADQUISICION DE ACTIVOS FINANCIEROS", "6-26: ADQUISICION DE ACTIVOS NO FINANCIEROS"],
                      "DEVENGADO": [10, 249881, 500]})
    p = ejecucion.panel_no_financiero(g)
    assert p["MONTO"].sum() == 510
    assert p.loc[p.ITEM == "Otros gastos de capital", "MONTO"].sum() == 10
