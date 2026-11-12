"""Hidrología (SENAMHI): la página guarda las piezas del archivo del navegador y arma con ellas los CSV y el gráfico."""
import csv
import io
import zipfile
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import db, hidrologia
from app.main import app


def ms(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def grafica(cod, var, y, valores, anterior=None, dia="2026-11-12", estado="OK"):
    """Un hidrograma como lo guarda el recolector: año hidrológico «y» desde el 1 de setiembre."""
    fechas = [ms(date.fromordinal(date(y, 9, 1).toordinal() + i)) for i in range(len(valores))]
    data = None if estado != "OK" else {
        "codEstacion": cod, "nomEstacion": "SANTA MARÍA DE NANAY", "nomRio": "RÍO NANAY", "variable": var, "unidad": "m.s.n.m",
        "fechaHora": fechas, "datoActual": valores, "datoAnterior": anterior or [None] * len(valores),
        "minimo": [v and v - 0.1 for v in valores], "maximo": [v and v + 0.1 for v in valores], "promHistorico": [123.0] * len(valores),
        "rojo": [122.06] * len(valores), "naranja": [123.09] * len(valores), "amarillo": [123.94] * len(valores)}
    return {"dia": dia, "cod": cod, "variable": var, "opcion": "N", "y": y, "fh": f"{dia} 06:00:00", "estado": estado,
            "inicio": fechas[0] if data else None, "data": data}


def crudo(hoy="2026-11-12", valores=(122.5, 122.4, -999, 122.0)):
    return {"version": 3, "generado": hoy + "T15:00:00Z", "meta": {"hoy": hoy, "desdeFecha": "2023-01-01", "prueba": False},
            "estaciones": [{"idEstacion": 1, "codEstacion": "240001", "nomEstacion": "SANTA MARÍA DE NANAY", "subEstacion": None, "estado": 1},
                           {"idEstacion": 2, "codEstacion": "999", "nomEstacion": "OTRA", "subEstacion": None, "estado": 1}],
            "zonales": {"240001": "08", "999": "04"}, "fichas": {"240001": {"id": "240001", "fecha_hora": hoy + " 06:00:00", "variable_opcion": "N"}},
            "infoMeta": {"240001": {"nomEsta": "SANTA MARÍA DE NANAY", "cuerpoAgua": "RÍO NANAY", "nomCuenca": "Nanay", "nomDepa": "LORETO",
                                    "nomSector": "NORTE", "uniHidrografica": "Amazonas", "codZonal": "08", "uniAnomalia": "m"}},
            "graficas": [grafica("240001", "NIVEL", 2026, list(valores), anterior=[124.0, 124.1, 124.2, 124.3], dia=hoy),
                         grafica("240001", "CAUDAL", 2026, [], dia=hoy, estado="SIN DATOS"),
                         grafica("999", "NIVEL", 2026, [10.0, 11.0], dia=hoy)],
            "mensual": {"2026-10": [{"informacion": {"primDescripcion": "OCT-26"}, "detalle": [
                {"codEsta": "240001", "nomEsta": "SANTA MARÍA DE NANAY", "cuerpoAgua": "RÍO NANAY", "nomDepa": "LORETO", "unidad": "m.s.n.m",
                 "dato": 122.9, "datoAnt": 123.4, "datAnomalia": -0.5, "uniAnomalia": "m", "tendencia": "D", "umbralRojo": 122.06}]}],
                        "2026-11": [{"informacion": {"primDescripcion": "OCT-26"}, "detalle": [{"codEsta": "240001", "dato": 1}]}]},
            "infoDiaria": {hoy + " 06:00": [70, [["240001", 122.0, -1.3, "D", 122.06, "m.s.n.m", "m"]]]}}


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'prueba.db'}")
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    hidrologia._armado.update(version=None, carpeta=None, resumen=None)
    yield TestClient(app)
    db.reiniciar_motor()


def subir(cliente, c):
    piezas = [{**p, "huella": str(hash(str(p["valor"])))} for p in hidrologia.piezas_de_archivo(c)]
    r = cliente.post("/v1/hidrologia/crudo", json={"dia": c["meta"]["hoy"], "piezas": piezas})
    assert r.status_code == 200, r.text
    return r.json()


def filas(r):
    return list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))


def test_sin_datos(cliente):
    assert cliente.get("/v1/hidrologia").json() == {"hay": False}
    assert cliente.get("/v1/estado").json()["hidrologia"] is False
    assert cliente.get("/v1/hidrologia/estaciones?departamento=16").json()["estaciones"] == []
    assert cliente.get("/v1/hidrologia/descargar?archivo=diario").status_code == 404


def test_subir_y_descargar_los_csv_del_notebook(cliente):
    assert subir(cliente, crudo())["guardadas"] == 11
    e = cliente.get("/v1/hidrologia").json()
    assert e["hay"] and e["ultima_fecha"] == "2026-09-04" and e["recolectado"] == "2026-11-12"
    assert e["por_departamento"] == {"LORETO": 1, "(sin departamento)": 1} and cliente.get("/v1/estado").json()["hidrologia"] is True
    d = filas(cliente.get("/v1/hidrologia/descargar?archivo=diario"))
    assert list(d[0]) == hidrologia.COLS["diario"]
    nanay = [f for f in d if f["COD_ESTACION"] == "240001"]
    # el -999 es «sin dato»; del año anterior solo entra el valor
    assert [(f["FECHA"], f["VALOR"], f["SERIE"]) for f in nanay] == [
        ("01/09/2025", "124.0", "ANTERIOR"), ("02/09/2025", "124.1", "ANTERIOR"), ("03/09/2025", "124.2", "ANTERIOR"),
        ("04/09/2025", "124.3", "ANTERIOR"), ("01/09/2026", "122.5", "ACTUAL"), ("02/09/2026", "122.4", "ACTUAL"), ("04/09/2026", "122.0", "ACTUAL")]
    assert nanay[-1]["UMBRAL_ROJO"] == "122.06" and nanay[-1]["AÑO_HIDROLOGICO"] == "2026" and nanay[0]["MINIMO"] == ""
    # solo Loreto; el mes aún no publicado (devuelve octubre) no entra al mensual
    assert {f["COD_ESTACION"] for f in filas(cliente.get("/v1/hidrologia/descargar?archivo=diario&departamento=16"))} == {"240001"}
    assert [(f["AÑO"], f["MES"], f["VALOR_MES"]) for f in filas(cliente.get("/v1/hidrologia/descargar?archivo=mensual"))] == [("2026", "10", "122.9")]
    i = filas(cliente.get("/v1/hidrologia/descargar?archivo=info-diaria"))
    assert len(i) == 1 and i[0]["DEPARTAMENTO"] == "LORETO" and i[0]["HORA"] == "06:00" and i[0]["ANOMALIA"] == "-1.3"
    c = {(f["COD_ESTACION"], f["VARIABLE"]): f for f in filas(cliente.get("/v1/hidrologia/descargar?archivo=control"))}
    assert c[("240001", "CAUDAL")]["ESTADO"] == "SIN DATOS" and c[("240001", "NIVEL")]["DIAS_CON_DATO"] == "7"
    x = cliente.get("/v1/hidrologia/descargar?archivo=diario&departamento=16&formato=xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    z = zipfile.ZipFile(io.BytesIO(cliente.get("/v1/hidrologia/descargar?archivo=todo").content))
    assert "DATA/SENAMHI_rios_diario.csv" in z.namelist() and "CONTROL/CONTROL SENAMHI rios_diario.csv" in z.namelist()


def test_grafico_de_la_region(cliente):
    subir(cliente, crudo())
    e = cliente.get("/v1/hidrologia/estaciones?departamento=16").json()["estaciones"]
    assert [x["codigo"] for x in e] == ["240001"] and list(e[0]["variables"]) == ["NIVEL"]
    v = e[0]["variables"]["NIVEL"]
    assert v["años"] == [2025, 2026] and v["ultimo"] == {"fecha": "2026-09-04", "valor": 122.0, "anterior": 124.3, "promedio": 123.0,
                                                        "rojo": 122.06, "naranja": 123.09, "amarillo": 123.94}
    assert cliente.get("/v1/hidrologia/estaciones?departamento=22").json()["estaciones"] == []
    s = cliente.get("/v1/hidrologia/serie?estacion=240001&variable=NIVEL&anio=2026").json()
    assert s["desde"] == "2026-09-01" and s["dias"] == 365 and s["actual"][:4] == [122.5, 122.4, None, 122.0] and s["anterior"][3] == 124.3
    # el año anterior no se pidió directamente: se arma con lo que trae el hidrograma del siguiente
    s = cliente.get("/v1/hidrologia/serie?estacion=240001&variable=NIVEL&anio=2025").json()
    assert s["actual"][:2] == [124.0, 124.1] and s["rojo"][0] == 122.06
    assert cliente.get("/v1/hidrologia/serie?estacion=240001&variable=CAUDAL&anio=2026").status_code == 404


def test_actualizacion_diaria_y_archivo_viejo(cliente):
    subir(cliente, crudo())
    indice = cliente.get("/v1/hidrologia/crudo/indice").json()["piezas"]
    assert "graf:240001:NIVEL:2026" in indice and "inf:2026-11-12:06:00" in indice
    # al día siguiente SENAMHI corrige un dato y agrega otro: reemplaza, no duplica
    r = subir(cliente, crudo("2026-11-13", (122.5, 122.45, 122.2, 122.0, 121.9)))
    assert r["omitidas_por_viejas"] == 0
    d = [f for f in filas(cliente.get("/v1/hidrologia/descargar?archivo=diario")) if f["COD_ESTACION"] == "240001" and f["SERIE"] == "ACTUAL"]
    assert [f["VALOR"] for f in d] == ["122.5", "122.45", "122.2", "122.0", "121.9"] and d[-1]["FECHA_EXTRACCION"] == "13/11/2026"
    assert len(filas(cliente.get("/v1/hidrologia/descargar?archivo=info-diaria"))) == 2
    # un archivo viejo subido por error no pisa lo más reciente
    r = subir(cliente, crudo())
    assert r["omitidas_por_viejas"] == 10 and r["guardadas"] == 1
    assert cliente.get("/v1/hidrologia").json()["ultima_fecha"] == "2026-09-05"
    assert cliente.post("/v1/hidrologia/crudo", json={"dia": "2026-11-13", "piezas": [{"clave": "otra:cosa", "valor": 1}]}).status_code == 422
