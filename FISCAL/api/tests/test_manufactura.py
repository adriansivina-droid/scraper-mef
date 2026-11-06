"""Manufactura: lectura del IVFM de una región y el cuadro de la síntesis (mes, enero-mes, contribución y estructura)."""
import io

import pytest
from openpyxl import Workbook

from app import db
from tests.test_api import cliente_http


def ivfm():
    """Un IVFM mínimo con el formato del de Loreto: refinación (primaria, 60) y gaseosas (no primaria, 40), 2025 y 2026."""
    wb = Workbook()
    ws = wb.active
    ws.title = "IVF LO 2026 TOTAL"
    ws["B2"] = "INDICE VOLUMEN FISICO MANUFACTURERO "
    ws["C3"], ws["D3"] = "CIIU", "Ponderac."
    ws["B8"], ws["B15"] = "INDUSTRIA PRIMARIA", "INDUSTRIA NO PRIMARIA "
    ws["B13"], ws["C13"], ws["D13"] = "FAB. DE REFI. DE PETROLEO", 2320, 60.0
    ws["B20"], ws["C20"], ws["D20"] = "ELAB. GASEOSA Y AGUA MINERAL", 1554, 40.0
    for anio, c0, ref, gas in ((2025, 6, [100.0] * 12, [50.0] * 12), (2026, 20, [90.0, 120.0] + [0] * 10, [60.0, 40.0] + [0] * 10)):
        ws.cell(1, c0, f"Inidces mensuales {anio}")
        for m in range(12):
            ws.cell(13, c0 + m, ref[m])
            ws.cell(20, c0 + m, gas[m])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'manu.db'}")
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    c = cliente_http()
    r = c.post("/v1/cargas", files=[("archivos", ("IVFM-LO 2026 TOTAL.xlsx", ivfm(), "application/octet-stream"))])
    assert r.status_code == 200, r.text
    yield c
    db.reiniciar_motor()


def test_carga_y_cuadro(cliente):
    e = cliente.get("/v1/estado").json()["bases"]["manu-ivf"]
    assert e["departamentos"] == ["16"] and e["desde"] == "2025-01" and e["hasta"] == "2026-02"      # los meses en 0 no se guardan
    c = cliente.get("/v1/cuadros/manufactura?departamento=16&periodo=2026-02").json()["cuadros"]
    f = {x["nombre"]: x for x in c["cuadro"]}
    assert list(f) == ["MANUFACTURA PRIMARIA", "Refinación de petróleo", "MANUFACTURA NO PRIMARIA", "Bebidas gaseosas", "SECTOR MANUFACTURA"]
    t = f["SECTOR MANUFACTURA"]
    # total = Σ ponderación × índice / 100: feb 2025 = 80, feb 2026 = 88 -> +10 %
    assert (t["mes_b"], t["mes_a"]) == (80.0, 88.0) and t["var_mes"] == pytest.approx(10.0)
    # contribución: refinación +20 % × 6000/8000 = +15; gaseosas -20 % × 2000/8000 = -5 (suman la var. del total)
    assert f["Refinación de petróleo"]["contrib_mes"] == pytest.approx(15.0) and f["Bebidas gaseosas"]["contrib_mes"] == pytest.approx(-5.0)
    # enero-febrero: promedio 2026 = (78 + 88)/2 = 83 frente a 80 -> +3,75 %
    assert t["acum_a"] == pytest.approx(83.0) and t["var_acum"] == pytest.approx(3.75)
    # estructura: IVF ponderado de 2025 -> 6000 / 8000 = 75 %
    assert f["MANUFACTURA PRIMARIA"]["estructura"] == pytest.approx(75.0) and c["estructura_de"] == 2025
    assert c["serie"][-1]["var_total"] == pytest.approx(10.0)
    assert cliente.get("/v1/cuadros/manufactura?departamento=16&formato=xlsx").status_code == 200
    assert cliente.get("/v1/cuadros/manufactura?departamento=16&periodo=2027-01").status_code == 422
    assert cliente.get("/v1/cuadros/manufactura?departamento=22").json()["cuadros"] is None
