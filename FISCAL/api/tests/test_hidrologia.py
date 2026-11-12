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
    assert v["años"] == [2025, 2026]
    u = v["ultimo"]
    assert {k: u[k] for k in ("fecha", "valor", "anterior", "promedio", "rojo", "naranja", "amarillo")} == {
        "fecha": "2026-09-04", "valor": 122.0, "anterior": 124.3, "promedio": 123.0, "rojo": 122.06, "naranja": 123.09, "amarillo": 123.94}
    # 122,0 está bajo el umbral rojo, pero el dato es de hace 69 días (la recolección es del 12/11): no se da como alerta
    assert u["alerta"]["estado"] == "sin_dato" and u["alerta"]["calculada"] == "roja" and u["alerta"]["nivel"] is None
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


def test_rango_de_fechas(cliente):
    subir(cliente, crudo())
    # cruza dos años hidrológicos: del 2/9/2025 (2025-2026) al 3/9/2026 (2026-2027)
    s = cliente.get("/v1/hidrologia/rango?estacion=240001&variable=NIVEL&desde=2025-09-02&hasta=2026-09-03").json()
    assert s["desde"] == "2025-09-02" and s["hasta"] == "2026-09-03" and s["dias"] == 367
    assert s["actual"][:3] == [124.1, 124.2, 124.3] and s["actual"][-3:] == [122.5, 122.4, None]
    assert s["anterior"][-3] == 124.0 and s["rojo"][-1] == 122.06
    # fechas al revés: se ordenan; más de 5 años o sin datos: aviso
    assert cliente.get("/v1/hidrologia/rango?estacion=240001&variable=NIVEL&desde=2026-09-04&hasta=2026-09-01").json()["actual"] == [122.5, 122.4, None, 122.0]
    assert cliente.get("/v1/hidrologia/rango?estacion=240001&variable=NIVEL&desde=2010-01-01&hasta=2026-09-01").status_code == 422
    assert cliente.get("/v1/hidrologia/rango?estacion=240001&variable=NIVEL&desde=2023-01-01&hasta=2023-02-01").status_code == 404


def test_todo_el_pais_con_coordenadas(cliente):
    subir(cliente, crudo())
    e = {x["codigo"]: x for x in cliente.get("/v1/hidrologia/estaciones?departamento=todos").json()["estaciones"]}
    assert set(e) == {"240001", "999"}
    # coordenadas de la copia del mapa de SENAMHI (09/11/2026); el departamento sale de la Información Diaria; «999» no está en el mapa
    assert e["240001"]["departamento"] == "LORETO" and e["240001"]["lat"] == -3.8891 and e["240001"]["zonal"] == "08" and e["240001"]["color"] is None
    assert e["999"]["lat"] is None and e["999"]["departamento"] == ""
    # con la lista del mapa que trae el recolector v4, llegan las coordenadas y el color de alerta del día
    c = crudo("2026-11-13")
    c["monitoreo"] = [{"codZonal": "08", "nomZonal": "#FFA500-DIRECCION ZONAL 8", "codEstacion": "240001", "latitud": -3.79, "longitud": -73.35}]
    subir(cliente, c)
    x = next(x for x in cliente.get("/v1/hidrologia/estaciones?departamento=todos").json()["estaciones"] if x["codigo"] == "240001")
    assert (x["lat"], x["lon"], x["color"], x["direccion_zonal"]) == (-3.79, -73.35, "#FFA500", "DZ 8 · Loreto")
    f = filas(cliente.get("/v1/hidrologia/descargar?archivo=estaciones"))
    assert next(r for r in f if r["COD_ESTACION"] == "240001")["LATITUD"] == "-3.79"


def test_comparar_anios(cliente):
    subir(cliente, crudo())
    s = cliente.get("/v1/hidrologia/anios?estacion=240001&variable=NIVEL").json()
    assert sorted(s["años"]) == ["2025", "2026"] and s["dias"] == 366 and len(s["años"]["2026"]) == 366
    # el año 2025-2026 sale del «anterior» del hidrograma 2026-2027; los días van sobre el mismo eje (1/9 en la posición 0)
    assert s["años"]["2025"][:4] == [124.0, 124.1, 124.2, 124.3] and s["años"]["2026"][:4] == [122.5, 122.4, None, 122.0]
    assert s["rojo"][0] == 122.06 and s["promedio"][0] == 123.0
    assert cliente.get("/v1/hidrologia/anios?estacion=240001&variable=CAUDAL").status_code == 404


def test_inicio_es_la_recoleccion_mas_antigua(cliente):
    assert hidrologia.inicio() == date(2023, 1, 1)                       # sin nada guardado
    c = crudo()
    c["meta"]["desdeFecha"] = "2020-01-01"                                # la corrida larga, desde 2020
    subir(cliente, c)
    assert hidrologia.inicio() == date(2020, 1, 1)
    d = crudo("2026-11-13")
    d["meta"]["desdeFecha"] = "2026-11-01"                                # la actualización diaria no lo mueve
    subir(cliente, d)
    assert hidrologia.inicio() == date(2020, 1, 1)
    # los años del hidrograma ya no se cortan en 2022: el 2025-2026 sigue y entra el que se tenga desde 2019-2020
    e = cliente.get("/v1/hidrologia/estaciones?departamento=16").json()["estaciones"]
    assert e[0]["variables"]["NIVEL"]["años"] == [2025, 2026]


def test_reporte_hidrico_oriente(cliente):
    import io
    import zipfile
    assert cliente.get("/v1/hidrologia/reporte").status_code == 404                  # sin datos
    subir(cliente, crudo())
    p = cliente.get("/v1/hidrologia/reporte?formato=pptx")
    assert p.status_code == 200 and "Oriente" in p.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(p.content))
    diapos = [n for n in z.namelist() if n.startswith("ppt/slides/slide")]
    assert len(diapos) >= 6 and any(n.startswith("ppt/charts/") for n in z.namelist())
    texto = z.read("ppt/slides/slide2.xml").decode()
    # el último dato (122,0, bajo el umbral rojo) es de hace 69 días: la tabla dice «Sin dato reciente» y no lo cuenta como alerta
    assert "Santa María de Nanay" in texto and "Sin dato reciente" in texto and "Roja" not in texto
    x = cliente.get("/v1/hidrologia/reporte?formato=xlsx")
    assert x.status_code == 200
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames[:2] == ["Índice", "Resumen"] and "Tabla diaria" in wb.sheetnames
    res = wb["Resumen"]
    assert res["C5"].value == "Santa María de Nanay" and str(res["E5"].value).startswith("='LOR Nanay")


# ── doble control de las alertas ─────────────────────────────────────────────
HOY = date(2026, 11, 12)


def dato(valor, fecha="2026-11-11", rojo=122.06, naranja=123.09, amarillo=123.94, promedio=123.4):
    return {"fecha": fecha, "valor": valor, "rojo": rojo, "naranja": naranja, "amarillo": amarillo, "promedio": promedio}


PLANA = [123.5 + 0.02 * (i % 3) for i in range(60)]                     # serie tranquila: ningún salto


def bajando(final):
    """Una serie que baja despacio hasta «final» (así llega un río a una alerta por nivel bajo: sin saltos)."""
    return [final + 1.8 * (59 - i) / 59 for i in range(60)]


def evaluar(valor, color, historia=None, **kw):
    h = list(historia if historia is not None else PLANA)
    h[-1] = valor
    return hidrologia.evaluar_alerta(dato(valor, **kw), HOY, color, h)


def test_alerta_confirmada_cuando_coinciden_la_pagina_y_senamhi():
    a = evaluar(121.9, "#FF0000", historia=bajando(121.9))
    assert (a["estado"], a["nivel"], a["baja"]) == ("confirmada", "roja", True) and "coinciden" in a["motivos"][0]
    assert evaluar(123.0, "#FFA500")["nivel"] == "naranja" and evaluar(123.5, "#FFFF00")["estado"] == "confirmada"


def test_si_senamhi_marca_blanco_no_se_pinta_la_alerta():
    # el caso de Cañad: la página calcula roja y SENAMHI la tiene en blanco → a verificar, no roja
    a = evaluar(121.9, "#FFFFFF", historia=bajando(121.9))
    assert a["estado"] == "a_verificar" and a["nivel"] is None and a["calculada"] == "roja" and "sin alerta" in a["motivos"][0]
    assert hidrologia.texto_alerta(a) == "A verificar"


def test_si_solo_senamhi_marca_alerta_se_muestra_como_de_senamhi():
    a = evaluar(124.5, "#FFA500")                                         # la página no ve alerta (124,5 > amarillo)
    assert a["estado"] == "senamhi" and a["nivel"] == "naranja" and hidrologia.texto_alerta(a) == "Según SENAMHI: Naranja"


def test_sin_el_color_de_senamhi_la_alerta_queda_sin_confirmar():
    a = evaluar(121.9, None, historia=bajando(121.9))
    assert a["estado"] == "sin_confirmar" and a["nivel"] == "roja" and hidrologia.texto_alerta(a).endswith("sin confirmar")


def test_un_dato_viejo_no_da_alerta():
    # la estación dejó de reportar: su último dato (en alerta) es de hace 3 meses
    a = hidrologia.evaluar_alerta(dato(121.9, fecha="2026-08-10"), HOY, None, PLANA)
    assert a["estado"] == "sin_dato" and a["nivel"] is None and "hace 94 días" in a["motivos"][0]
    assert hidrologia.evaluar_alerta(dato(121.9, fecha="2026-08-10"), HOY, "#FFFFFF", PLANA)["estado"] == "sin_dato"        # SENAMHI la ve en blanco
    a = hidrologia.evaluar_alerta(dato(121.9, fecha="2026-08-10"), HOY, "#FF0000", PLANA)                                   # SENAMHI sí marca roja
    assert (a["estado"], a["nivel"]) == ("senamhi", "roja")
    assert hidrologia.evaluar_alerta(dato(121.9, fecha="2026-11-10"), HOY, None, bajando(121.9))["estado"] == "sin_confirmar"       # 2 días: aún vale


def test_umbrales_incoherentes_o_incompletos_no_dan_alerta():
    a = evaluar(121.9, None, rojo=122.06, naranja=120.0, amarillo=123.94)                                       # rojo < naranja > amarillo
    assert a["estado"] == "sin_umbral" and "no son coherentes" in a["motivos"][0]
    a = evaluar(121.9, None, naranja=None, amarillo=None, promedio=123.4)                                          # solo rojo: tipo inferido
    assert a["estado"] == "a_verificar" and any("solo hay umbral rojo" in m for m in a["motivos"])
    assert evaluar(121.9, None, rojo=None, naranja=None, amarillo=None)["estado"] == "sin_umbral"


def test_un_salto_brusco_no_da_alerta():
    historia = [123.5 + 0.02 * (i % 3) for i in range(59)] + [100.0]                                           # de 123,5 a 100 en un día
    a = hidrologia.evaluar_alerta(dato(100.0), HOY, None, historia)
    assert a["estado"] == "a_verificar" and any("bruscamente" in m for m in a["motivos"])


def test_umbrales_de_crecida():
    a = evaluar(131.0, "#FF0000", rojo=130.0, naranja=129.0, amarillo=128.0, historia=[130.5 + 0.01 * (i % 3) for i in range(60)])
    assert (a["estado"], a["baja"], a["nivel"]) == ("confirmada", False, "roja")
    assert evaluar(125.0, "#FFFFFF", rojo=130.0, naranja=129.0, amarillo=128.0)["estado"] == "normal"
