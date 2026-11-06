"""Gráficos DRAE: los gráficos de las SERIES se leen de su XML (datos guardados en el gráfico, título de las celdas de
arriba) y se guardan en la base al subir el libro en la página."""
import io
import zipfile

import pytest

from app import db, drae
from tests.test_api import cliente_http

C = 'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
M = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
R = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
T = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _ser(nombre, cats, vals, extra=""):
    pts = lambda xs, num: "".join(f'<c:pt idx="{i}"><c:v>{x}</c:v></c:pt>' for i, x in enumerate(xs))
    return (f'<c:ser><c:idx val="0"/><c:tx><c:strRef><c:f>H!$C$4</c:f><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>{nombre}</c:v></c:pt></c:strCache></c:strRef></c:tx>{extra}'
            f'<c:cat><c:strRef><c:f>H!$B$5:$B$7</c:f><c:strCache><c:ptCount val="{len(cats)}"/>{pts(cats, False)}</c:strCache></c:strRef></c:cat>'
            f'<c:val><c:numRef><c:f>H!$C$5:$C$7</c:f><c:numCache><c:formatCode>0.0</c:formatCode><c:ptCount val="{len(vals)}"/>{pts(vals, True)}</c:numCache></c:numRef></c:val></c:ser>')


def libro():
    """Un libro mínimo con una hoja «PBI», el título en B2 y un gráfico combinado (barras Loreto + línea Perú)."""
    grafico = (f'<?xml version="1.0"?><c:chartSpace {C}><c:chart><c:autoTitleDeleted val="1"/><c:plotArea>'
               f'<c:barChart><c:barDir val="col"/><c:grouping val="clustered"/>{_ser("Loreto", ["2024", "2025", "2026*"], [6.6, 4.9, -2.9], "<c:dLbls><c:showVal val=\"1\"/></c:dLbls>")}<c:axId val="1"/><c:axId val="2"/></c:barChart>'
               f'<c:lineChart><c:grouping val="standard"/>{_ser("Perú", ["2024", "2025", "2026*"], [3.5, 3.4, 2.6])}<c:axId val="1"/><c:axId val="2"/></c:lineChart>'
               f'<c:catAx><c:axId val="1"/></c:catAx><c:valAx><c:axId val="2"/></c:valAx></c:plotArea></c:chart></c:chartSpace>')
    dibujo = ('<?xml version="1.0"?><xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
              'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><xdr:twoCellAnchor><xdr:from><xdr:col>3</xdr:col><xdr:row>4</xdr:row></xdr:from>'
              '<xdr:to><xdr:col>10</xdr:col><xdr:row>20</xdr:row></xdr:to><xdr:graphicFrame><a:graphic><a:graphicData>'
              f'<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="{T}" r:id="rId1"/></a:graphicData></a:graphic></xdr:graphicFrame></xdr:twoCellAnchor>'
              '<xdr:twoCellAnchor><xdr:from><xdr:col>3</xdr:col><xdr:row>21</xdr:row></xdr:from><xdr:to><xdr:col>9</xdr:col><xdr:row>22</xdr:row></xdr:to></xdr:twoCellAnchor></xdr:wsDr>')
    hoja = (f'<?xml version="1.0"?><worksheet {M}><sheetData><row r="2"><c r="B2" t="s"><v>0</v></c></row>'
            f'<row r="22"><c r="D22" t="s"><v>1</v></c></row></sheetData><drawing r:id="rId1"/></worksheet>')
    archivos = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "xl/workbook.xml": f'<?xml version="1.0"?><workbook {M}><sheets><sheet name="PBI" sheetId="1" r:id="rId1"/><sheet name="Oculta" sheetId="2" state="hidden" r:id="rId2"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": f'<?xml version="1.0"?><Relationships {R}><Relationship Id="rId1" Type="{T}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{T}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/sharedStrings.xml": f'<?xml version="1.0"?><sst {M}><si><t>EVOLUCIÓN DE LA ACTIVIDAD PRODUCTIVA, 2024 - 2026 (Var. real)</t></si><si><t>Fuente: INEI</t></si></sst>',
        "xl/worksheets/sheet1.xml": hoja,
        "xl/worksheets/_rels/sheet1.xml.rels": f'<?xml version="1.0"?><Relationships {R}><Relationship Id="rId1" Type="{T}/drawing" Target="../drawings/drawing1.xml"/></Relationships>',
        "xl/drawings/drawing1.xml": dibujo,
        "xl/drawings/_rels/drawing1.xml.rels": f'<?xml version="1.0"?><Relationships {R}><Relationship Id="rId1" Type="{T}/chart" Target="../charts/chart1.xml"/></Relationships>',
        "xl/charts/chart1.xml": grafico,
    }
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for k, v in archivos.items():
            z.writestr(k, v)
    return b.getvalue()


def test_leer_series():
    g = drae.leer_series(libro())
    assert len(g) == 1                                     # la hoja oculta no entra
    x = g[0]
    assert (x["hoja"], x["orden"], x["tipo"]) == ("PBI", 1, "combinado")
    assert (x["titulo"], x["subtitulo"]) == ("Evolución de la actividad productiva, 2024 - 2026", "(Var. real)")
    assert x["notas"] == ["Fuente: INEI"]
    assert x["categorias"] == ["2024", "2025", "2026*"]
    assert [(s["nombre"], s["tipo"], s["valores"], s["etiquetas"], s["formato"]) for s in x["series"]] == [
        ("Loreto", "barras", [6.6, 4.9, -2.9], True, "0.0"), ("Perú", "lineas", [3.5, 3.4, 2.6], False, "0.0")]


def test_departamento_por_nombre():
    assert drae.depto_de("SERIES LORETO (OFICIAL) - ENLACE ESTAD.xlsx") == "16"
    assert drae.depto_de("SERIES_SMN.xlsx") == "22" and drae.depto_de("SERIES SMN 04-2026.xlsx") == "22"
    assert drae.depto_de("SERIES UCAYALI.xlsx") == "25" and drae.depto_de("SERIES_UCA.xlsx") == "25"
    assert drae.depto_de("ESTADLO.xlsx") is None and drae.depto_de("SERIES_LIMA.xlsx") is None
    # los libros de gráficos del DRAE
    assert drae.depto_de("DRAE_SMT_Nov-26.xlsx") == "22" and drae.fuente_de("DRAE_SMT_Nov-26.xlsx") == "DRAE"
    assert drae.depto_de("DRAE_Ucayali-Set26_Parte5.xlsx") == "25" and drae.fuente_de("SERIES_UCA.xlsx") == "SERIES"


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'drae.db'}")
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    yield cliente_http()
    db.reiniciar_motor()


def test_subir_series_y_corregir_titulo(cliente):
    assert cliente.get("/v1/drae?departamento=16").json() == {"archivo": None, "fecha": None, "graficos": [], "archivos": []}
    r = cliente.post("/v1/cargas", files=[("archivos", ("SERIES LORETO (OFICIAL).xlsx", libro(), "application/octet-stream"))])
    assert r.status_code == 200, r.text
    assert r.json()["avisos"] == ["SERIES LORETO (OFICIAL).xlsx: 1 gráficos DRAE guardados."]
    d = cliente.get("/v1/drae?departamento=16").json()
    assert d["archivo"] == "SERIES LORETO (OFICIAL).xlsx" and d["graficos"][0]["series"][1]["nombre"] == "Perú"
    assert cliente.get("/v1/drae?departamento=22").json()["graficos"] == []
    assert cliente.post("/v1/drae/titulo?departamento=16&orden=1", json={"titulo": "Loreto: PBI", "subtitulo": "(Var. %)"}).json() == {"ok": True}
    assert cliente.get("/v1/drae?departamento=16").json()["graficos"][0]["titulo"] == "Loreto: PBI"
    assert cliente.post("/v1/drae/titulo?departamento=16&orden=9", json={"titulo": "x"}).status_code == 404
    assert cliente.get("/v1/drae?departamento=15").status_code == 422


def test_series_y_libro_del_drae_conviven(cliente):
    """El libro del DRAE se guarda aparte de las SERIES (orden 1001…): subir uno no borra los del otro."""
    subir = lambda nombre: cliente.post("/v1/cargas", files=[("archivos", (nombre, libro(), "application/octet-stream"))]).json()
    assert subir("SERIES_SMN.xlsx")["avisos"] == ["SERIES_SMN.xlsx: 1 gráficos DRAE guardados."]
    assert subir("DRAE_SMT_Nov-26.xlsx")["avisos"] == ["DRAE_SMT_Nov-26.xlsx: 1 gráficos DRAE guardados."]
    d = cliente.get("/v1/drae?departamento=22").json()
    assert [(g["orden"], g["fuente"]) for g in d["graficos"]] == [(1, "SERIES"), (1001, "DRAE")]
    assert {a["archivo"] for a in d["archivos"]} == {"SERIES_SMN.xlsx", "DRAE_SMT_Nov-26.xlsx"}
    subir("SERIES_SMN.xlsx")                                  # volver a subir las SERIES deja el libro del DRAE
    assert [g["fuente"] for g in cliente.get("/v1/drae?departamento=22").json()["graficos"]] == ["SERIES", "DRAE"]


def _g(orden, hoja, titulo, cats, vals, tipo="barras", nombre="Loreto"):
    return {"orden": orden, "hoja": hoja, "titulo": titulo, "subtitulo": "", "tipo": tipo, "categorias": cats,
            "series": [{"nombre": nombre, "valores": vals}]}


def test_graficos_innecesarios():
    gs = [_g(1, "PBI (NUEVO)", "Evolución del PBI, 2015 - 2026", ["2015", "2016", "2017"], [1.0, 2.0, 3.0]),
          _g(2, "PBI", "Evolución del PBI, 2016 - 2026", ["2016", "2017"], [2.0, 3.0]),            # contenido en 1
          _g(3, "PBI T", "PBI trimestral", ["I", "II"], [5.0, 6.0]),
          _g(4, "PBI T (2)", "PBI trimestral", ["I", "II"], [5.0, 6.0]),                            # duplicado de 3
          _g(5, "XS LOR AGOS-2026", "Loreto: Principales mercados, periodo enero-agosto.", ["A", "B"], [1.0, 2.0]),
          _g(6, "XS LOR AGOS-2026", "Loreto: Principales mercados, agosto 2025.", ["A", "B"], [3.0, 4.0]),   # año anterior: queda
          _g(7, "XS LOR AGO-2026", "Loreto: Principales mercados, enero 2026.", ["A", "B"], [5.0, 6.0]),    # mes anterior
          _g(8, "XS LOR AGO-2026", "Loreto: Principales productos de aduana Iquitos, enero 2026.", ["A"], [1.0])]  # su hoja ya es vieja
    fuera = drae.innecesarios(gs)
    assert sorted(fuera) == [2, 4, 7, 8]
    assert fuera[4] == "duplicado de N° 3" and fuera[2].startswith("contenido en N° 1") and "mes anterior" in fuera[7]


def test_ocultar_y_depurar(cliente):
    cliente.post("/v1/cargas", files=[("archivos", ("SERIES LORETO (OFICIAL).xlsx", libro(), "application/octet-stream"))])
    assert cliente.post("/v1/drae/ocultar?departamento=16&orden=1&oculto=true").json() == {"ok": True, "oculto": True}
    assert cliente.get("/v1/drae?departamento=16").json()["graficos"][0]["oculto"] is True
    cliente.post("/v1/cargas", files=[("archivos", ("SERIES LORETO (OFICIAL).xlsx", libro(), "application/octet-stream"))])
    assert cliente.get("/v1/drae?departamento=16").json()["graficos"][0]["oculto"] is True     # se recuerda al volver a subir
    cliente.post("/v1/drae/ocultar?departamento=16&orden=1&oculto=false")
    assert cliente.get("/v1/drae?departamento=16").json()["graficos"][0]["oculto"] is False
    assert cliente.post("/v1/drae/ocultar?departamento=16&orden=99").status_code == 404
    assert drae.depurar("16") == []
