"""Pruebas de exportaciones: libros ESTAD que imitan ESTADLO (15.Export y 16.Import) y ESTADUCA (15.XLS)."""
import io
from datetime import datetime

import pandas as pd
from openpyxl import Workbook, load_workbook

from tests.test_pesca import cliente, datos, subir  # noqa: F401  (la misma base temporal)

FILAS_LOR = ["TOTAL EXPORTACIONES", None, "PRODUCTOS TRADICIONALES", "Petróleo crudo y derivados", "PRODUCTOS NO TRADICIONALES",
             "Forestales", "Madera aserrada", "Otros acabados", "Pesqueros", "Peces ornamentales", "Agropecuarios", "Cacao en grano",
             "Animales vivos", "Resto2/", "OTRAS EXPORTACIONES3/"]


def _hoja(ws, titulo, filas, valores, anios=(2025, 2026), meses_ultimo=8):
    """Como el ESTAD: año en la fila 4 (en el primer mes), fecha en la fila 5, una columna Total por año y, al final, la
    columna «Var.%» (con fecha en la fila 5) y la «Ene.-Ago.» que no se deben leer."""
    ws["A1"], ws["A2"], ws["A3"] = "Cuadro Nº 15", titulo, "(Miles de US dólares)"
    col, columnas = 2, []
    for a in anios:
        for m in range(1, 13):
            ws.cell(4, col, a if m == 1 else None)
            ws.cell(5, col, datetime(a, m, 1))
            columnas.append((col, a, m))
            col += 1
        ws.cell(4, col, "Total")
        ws.cell(5, col, a)
        col += 1
    ws.cell(4, col, "Var.% 2026/2025")
    ws.cell(5, col, datetime(2026, meses_ultimo, 1))
    ws.cell(4, col + 1, 2026)
    ws.cell(5, col + 1, "Ene.-Jul.")
    for i, rot in enumerate(filas):
        r = 7 + i
        if rot is None:
            continue
        ws.cell(r, 1, rot)
        for c, a, m in columnas:
            if (a, m) <= (2026, meses_ultimo):
                ws.cell(r, c, valores(rot, a, m))
        ws.cell(r, col, 999999)                       # la Var.% no es un mes
        ws.cell(r, col + 1, 888888)
    r = 7 + len(filas) + 1
    ws.cell(r, 1, "1/ Preliminar.")
    ws.cell(r + 1, 1, "2/ Incluye aceite de palo de rosa, entre otros.")
    ws.cell(r + 2, 1, "Fuente: BCRP - Oficina Principal y SUNAT.")


def valores_lor(rot, a, m):
    base = {"Petróleo crudo y derivados": 24215 if (a, m) == (2025, 8) else 17033 if (a, m) == (2026, 8) else 20000,
            "Madera aserrada": 40, "Otros acabados": 10, "Peces ornamentales": 70, "Cacao en grano": 290 if a == 2026 else 0,
            "Animales vivos": 90, "Resto2/": 20, "OTRAS EXPORTACIONES3/": 0}
    grupos = {"Forestales": ["Madera aserrada", "Otros acabados"], "Pesqueros": ["Peces ornamentales"], "Agropecuarios": ["Cacao en grano"]}
    if rot in base:
        return base[rot]
    if rot in grupos:
        return sum(base[x] for x in grupos[rot])
    if rot == "PRODUCTOS TRADICIONALES":
        return base["Petróleo crudo y derivados"]
    nt = sum(base[x] for x in ["Madera aserrada", "Otros acabados", "Peces ornamentales", "Cacao en grano", "Animales vivos", "Resto2/"])
    if rot == "PRODUCTOS NO TRADICIONALES":
        return nt
    return base["Petróleo crudo y derivados"] + nt                     # TOTAL


def estadlo():
    wb = Workbook()
    wb.active.title = "01.XLS"
    wb.active["A2"] = "LORETO: PRODUCCIÓN AGROPECUARIA"
    _hoja(wb.create_sheet("15.Export"), "LORETO: EXPORTACIONES FOB POR GRUPO DE PRODUCTOS1/", FILAS_LOR, valores_lor)
    _hoja(wb.create_sheet("16.Import"), "LORETO: ADUANA IQUITOS IMPORTACIONES FOB SEGÚN USO O DESTINO ECONÓMICO",
          ["TOTAL IMPORTACIONES", None, "BIENES DE CONSUMO", "Bienes no duraderos (100)", "BIENES DE CAPITAL", "Bienes para la industria (800)"],
          lambda rot, a, m: 300 if rot.startswith("TOTAL") else 100 if "CONSUMO" in rot or "100" in rot else 200)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_estad_se_reconoce_y_se_lee_solo_por_meses(cliente):
    r = subir(cliente, **{"ESTADLO.xlsx": estadlo()})
    assert set(r["bases"]) == {"expo-estad", "impo-estad"}
    assert r["bases"]["expo-estad"]["periodos"][-1] == "2026-08"          # los meses vacíos del final no se guardan
    df = datos(cliente, "expo-estad", "16")
    assert 999999 not in set(df["FOB"]) and 888888 not in set(df["FOB"])  # ni la Var.% ni el Ene.-Mes
    fila = df[(df["AÑO"] == 2026) & (df["MES"] == 8)].set_index("RUBRO")
    assert fila.loc["Resto", "NIVEL"] == "grupo" and fila.loc["OTRAS EXPORTACIONES", "NIVEL"] == "tipo"
    assert fila.loc["Madera aserrada", "GRUPO"] == "Forestales" and fila.loc["Madera aserrada", "TIPO"] == "PRODUCTOS NO TRADICIONALES"


def test_cuadro_de_la_sintesis_sigue_la_regla_del_cuadro_lor(cliente):
    subir(cliente, **{"ESTADLO.xlsx": estadlo()})
    c = cliente.get("/v1/cuadros/exportaciones?departamento=16").json()["cuadros"]
    assert c["periodo"] == "2026-08" and c["dec"] == 2
    s = {f["nombre"]: f for f in c["sintesis"]}
    # 24 215 miles -> 24,22 (REDONDEAR de Excel, no 24,21 del redondeo bancario)
    assert s["Petróleo crudo y derivados"]["mes_b"] == 24.22
    assert list(s)[:2] == ["PRODUCTOS TRADICIONALES", "Petróleo crudo y derivados"]
    nt = [f["nombre"] for f in c["sintesis"] if f["nivel"] == 1][1:]
    assert nt == ["Agropecuarios", "Animales vivos", "Maderas y sus manufacturas", "Pesqueros", "Resto"]
    tot = s["TOTAL EXPORTACIONES"]
    tipos = [f for f in c["sintesis"] if f["nivel"] == 0 and not f["total"]]
    assert tot["mes_a"] == round(sum(f["mes_a"] for f in tipos), 2)
    assert tot["estructura"] == 100.0 and s["Agropecuarios"]["var_mes"] is None
    # anexo: 13 meses + el total del año anterior, con el TOTAL al final
    assert len(c["anexo"]["columnas"]) == 14 and c["anexo"]["columnas"][5]["total"]
    assert c["anexo"]["filas"][-1]["nombre"] == "TOTAL EXPORTACIONES"
    assert any(f["nombre"] == "Resto2/" for f in c["anexo"]["filas"])
    # gráficos
    assert c["variacion_anual"][-1]["etq"] == "2026*"
    assert c["no_tradicionales"]["actual"]["partes"][0]["nombre"] == "Cacao en grano"
    assert c["principales"]["mes"]["partes"][0]["nombre"] == "Petróleo crudo y derivados"
    assert c["notas_estad"][1].startswith("2/")
    assert cliente.get("/v1/cuadros/exportaciones?departamento=16&periodo=2026-03").json()["cuadros"]["periodo"] == "2026-03"


def test_importaciones_y_excel(cliente):
    subir(cliente, **{"ESTADLO.xlsx": estadlo()})
    c = cliente.get("/v1/cuadros/exportaciones?departamento=16&flujo=impo").json()["cuadros"]
    assert c["sintesis"][-1]["nombre"] == "TOTAL IMPORTACIONES" and c["sintesis"][-1]["mes_a"] == 0.3
    assert cliente.get("/v1/cuadros/exportaciones?departamento=25&flujo=impo").status_code == 422
    assert cliente.get("/v1/cuadros/exportaciones?departamento=22").json()["cuadros"] is None
    r = cliente.get("/v1/cuadros/exportaciones?departamento=16&formato=xlsx")
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Síntesis", "Anexo"]


def test_excel_bcrp_de_circulares_y_barras_horizontales(cliente):
    for tipo, spec in [("circular", {"titulo": "X", "circulos": [{"subtitulo": "2025", "partes": [{"nombre": "Cacao", "valor": 3}, {"nombre": "Otros", "valor": 1}]}]}),
                       ("hbarras", {"titulo": "X", "partes": [{"nombre": "Petróleo", "valor": 17.03}]})]:
        r = cliente.post("/v1/bcrp/excel", json={"tipo": tipo, "spec": spec, "nombre": "g"})
        assert r.status_code == 200
        assert load_workbook(io.BytesIO(r.content)).active._charts
