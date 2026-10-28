"""Cuadros de pesca: producción del mes y acumulada contra otro año, series del VBP y Cuadro Nº 07 de Loreto."""
import io

import pandas as pd
from openpyxl import load_workbook

from tests.test_hidrocarburos import cliente  # noqa: F401
from app.pesca import LOR_COLUMNAS, SMN_COLUMNAS, UCA_COLUMNAS

MESES = [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 4)]


def long(hoja, columnas, filas):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as w:
        pd.DataFrame(filas, columns=columnas).to_excel(w, sheet_name=hoja, index=False)
    return buf.getvalue()


def lor():
    f = []
    for a, m in MESES:
        k = 1.2 if a == 2026 else 1.0
        f += [dict(AÑO=a, MES=m, DEPARTAMENTO="LORETO", FUENTE="DESEMBARQUE", ESTADO="FRESCO", DESTINO="", ESPECIE="Boquichico",
                   ESPECIE_CORREGIDA="Boquichico", ESPECIE_OK="Boquichico", ESPECIE_CUADRO="Boquichico", UNIDAD="t", VOLUMEN=100 * k, VBP=327.504 * k),
              dict(AÑO=a, MES=m, DEPARTAMENTO="LORETO", FUENTE="DESEMBARQUE", ESTADO="SECO SALADO", DESTINO="", ESPECIE="Paiche",
                   ESPECIE_CORREGIDA="Paiche", ESPECIE_OK="Paiche", ESPECIE_CUADRO="Otros", UNIDAD="t", VOLUMEN=10, VBP=29.8778),
              dict(AÑO=a, MES=m, DEPARTAMENTO="LORETO", FUENTE="POR ESPECIES", ESTADO="ORNAMENTAL", DESTINO="Mercado externo", ESPECIE="Otocinclo",
                   ESPECIE_CORREGIDA="Otocinclo", ESPECIE_OK="Otocinclo", ESPECIE_CUADRO="Otros", UNIDAD="miles de unidades", VOLUMEN=50, VBP=51.645)]
    return long("LOR_PESCA", LOR_COLUMNAS, f)


def smn():
    f = []
    for a, m in MESES:
        f += [dict(AÑO=a, MES=m, DEPARTAMENTO="SAN MARTÍN", ORIGEN="Acuicultura", ESTADO="FRESCO", ESTADO_OK="FRESCO", ESPECIE="TILAPIA",
                   ESPECIE_OK="Tilapia", VOLUMEN=20 if a == 2026 else 10, VBP=0),
              dict(AÑO=a, MES=m, DEPARTAMENTO="Otros", ORIGEN="Extracción de ríos", ESTADO="FRESCO", ESTADO_OK="FRESCO", ESPECIE="UCAYALI",
                   ESPECIE_OK="Otras", VOLUMEN=5, VBP=0)]
    return long("SMN_PESCA", SMN_COLUMNAS, f)


def uca():
    f = []
    for a, m in MESES:
        f += [dict(AÑO=a, MES=m, TIPO="FRESCO", ESPECIES="BOQUICHICO", ESPECIES_CORREGIDO="Boquichico", ESPECIES_OK="Boquichico", VOLUMEN=30, VBP=98.25),
              dict(AÑO=a, MES=m, TIPO="AGREGADO", ESPECIES="TOTAL", ESPECIES_CORREGIDO="Total", ESPECIES_OK="Otros", VOLUMEN=30, VBP=0),
              dict(AÑO=a, MES=m, TIPO="ORNAMENTAL", ESPECIES="NEON", ESPECIES_CORREGIDO="Neon", ESPECIES_OK="Neon", VOLUMEN=1000, VBP=0)]
    return long("UCA_PESCA", UCA_COLUMNAS, f)


def test_cuadros_de_las_tres_regiones(cliente):  # noqa: F811
    r = cliente.post("/v1/cargas", files=[("archivos", (n, b, "application/octet-stream")) for n, b in
                                          (("LOR_PESCA_LONG.xlsx", lor()), ("SMN_PESCA_LONG.xlsx", smn()), ("UCA_PESCA_LONG.xlsx", uca()))])
    assert r.status_code == 200, r.text
    c = cliente.get("/v1/cuadros/pesca?departamento=16").json()["cuadros"]
    assert c["periodo"] == "2026-03" and c["comparar"] == 2025
    f = {x["nombre"]: x for x in c["filas"]}
    assert f["Estado fresco"]["var_mes"] == 20.0 and f["Estado fresco"]["acum_a"] == 360.0
    assert f["Peces ornamentales vivos"]["mes_a"] == 50.0 and f["Desembarque total"]["mes_a"] == 130.0
    assert c["mensual"]["b"][11] is not None and c["mensual"]["a"][3] is None
    c7 = {}
    for x in c["cuadro_07"]:                            # el bloque fresco repite nombres: vale la primera aparición
        c7.setdefault(x["nombre"], x)
    assert c7["Boquichico"]["ahora"] == 120.0 and c7["Paiche"]["antes"] == 10.0 and c7["Mercado externo"]["ahora"] == 50.0
    s = cliente.get("/v1/cuadros/pesca?departamento=22").json()["cuadros"]
    fs = {x["nombre"]: x for x in s["filas"]}
    assert fs["Producción de San Martín"]["var_mes"] == 100.0 and fs["Llega de otros departamentos"]["mes_a"] == 5.0 and "Tilapia" in fs
    u = cliente.get("/v1/cuadros/pesca?departamento=25&periodo=2026-02&formato=xlsx")
    assert load_workbook(io.BytesIO(u.content)).sheetnames == ["Producción", "VBP mensual"]
    assert cliente.get("/v1/cuadros/pesca?departamento=16&comparar=2026").status_code == 422
