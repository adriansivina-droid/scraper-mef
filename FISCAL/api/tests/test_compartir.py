"""Compartir con terceros: un enlace con permisos por sector y pestaña; el servidor niega todo lo demás."""
import pytest
from fastapi.testclient import TestClient

from app import compartir, db, hidrologia
from app.main import app
from tests.test_hidrologia import crudo, subir

EQUIPO = ("fiscal", "clave-del-equipo")


@pytest.fixture()
def sitio(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'prueba.db'}")
    monkeypatch.setenv("APP_CLAVE", EQUIPO[1])
    db.reiniciar_motor()
    hidrologia._armado.update(version=None, carpeta=None, resumen=None)
    equipo = TestClient(app)
    equipo.auth = EQUIPO
    yield equipo
    db.reiniciar_motor()


def invitar(equipo, permisos, dias=30, nombre="Gerencia", descargas=True):
    r = equipo.post("/v1/compartir", json={"nombre": nombre, "dias": dias, "permisos": permisos, "descargas": descargas})
    assert r.status_code == 200, r.text
    return r.json()


def entrar(enlace):
    """Un navegador nuevo, sin usuario ni clave: abre el enlace y guarda la cookie."""
    invitado = TestClient(app, follow_redirects=False)
    r = invitado.get(enlace.replace("http://testserver", ""))
    assert r.status_code == 303 and compartir.COOKIE in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]
    assert r.headers["location"] == "/"                     # la clave sale de la dirección
    return invitado


def test_sin_credenciales_no_entra(sitio):
    assert TestClient(app).get("/v1/estado").status_code == 401
    assert TestClient(app).get("/?t=inventada").status_code == 403
    assert TestClient(app, cookies={compartir.COOKIE: "inventada"}).get("/v1/estado").status_code == 401


def test_el_invitado_ve_solo_lo_que_se_le_dio(sitio):
    subir(sitio, crudo())
    inv = invitar(sitio, {"lor": ["pesca", "hidrologia"], "tres": ["empleo"]})
    g = entrar(inv["enlace"])
    yo = g.get("/v1/acceso/yo").json()
    assert yo["equipo"] is False and yo["nombre"] == "Gerencia" and yo["permisos"] == {"lor": ["hidrologia", "pesca"], "tres": ["empleo"]}
    assert g.get("/v1/estado").status_code == 200 and g.get("/v1/catalogo").status_code == 200
    # lo permitido
    for url in ("/v1/cuadros/pesca?departamento=16", "/v1/hidrologia", "/v1/hidrologia/estaciones?departamento=16", "/v1/empleo/totales",
                "/v1/hidrologia/serie?estacion=240001&variable=NIVEL&anio=2026", "/v1/hidrologia/descargar?archivo=diario&departamento=16",
                "/v1/descargas/vista-previa?base=pesca-loreto&departamento=16&desde=2026-01&hasta=2026-02", "/v1/descargas/empleo?regiones=Lima&formato=json"):
        assert g.get(url).status_code not in (401, 403), url
    # otra región, otro sector, todo el país, bases crudas
    for url in ("/v1/cuadros/pesca?departamento=22", "/v1/cuadros/manufactura?departamento=16", "/v1/cuadros/ejecucion?departamento=16&sector=gasto",
                "/v1/hidrologia/estaciones?departamento=22", "/v1/hidrologia/estaciones?departamento=todos", "/v1/hidrologia/descargar?archivo=diario",
                "/v1/hidrologia/descargar?archivo=todo", "/v1/hidrologia/crudo/indice", "/v1/drae?departamento=16", "/v1/hidrocarburos/mapa",
                "/v1/descargas/vista-previa?base=pesca-loreto,empleo&departamento=22&desde=2026-01&hasta=2026-02",
                "/v1/descargas/vista-previa?base=expo-sunat&departamento=16&desde=2026-01&hasta=2026-02", "/v1/mef/archivos", "/v1/contraste/ejecucion?departamento=16"):
        assert g.get(url).status_code == 403, url
    # administrar, subir, actualizar: nunca
    for url in ("/v1/compartir", "/v1/estado/espacio", "/v1/ipc", "/v1/fiscal/archivos", "/v1/hidrocarburos/archivos", "/v1/exportaciones/sunat?departamento=16"):
        assert g.get(url).status_code == 403, url
    assert g.post("/v1/cargas").status_code == 403 and g.post("/v1/hidrologia/crudo", json={"piezas": []}).status_code == 403
    assert g.post("/v1/compartir", json={"nombre": "x", "permisos": {"lor": ["pesca"]}}).status_code == 403
    assert g.delete(f"/v1/compartir/{inv['id']}").status_code == 403
    assert g.post("/v1/mef/actualizar").status_code == 403 and g.post("/v1/drae/titulo?departamento=16&orden=1", json={}).status_code == 403


def test_una_estacion_de_otra_region_no_se_ve(sitio):
    subir(sitio, crudo())
    g = entrar(invitar(sitio, {"smn": ["hidrologia"]})["enlace"])           # solo San Martín: la estación 240001 es de Loreto (DZ 8)
    assert g.get("/v1/hidrologia/serie?estacion=240001&variable=NIVEL&anio=2026").status_code == 403
    assert g.get("/v1/hidrologia/anios?estacion=240001&variable=NIVEL").status_code == 403
    p = entrar(invitar(sitio, {"tres": ["hidro-peru"]})["enlace"])            # «Ríos del Perú»: todas, y en cualquier región
    assert p.get("/v1/hidrologia/serie?estacion=240001&variable=NIVEL&anio=2026").status_code == 200
    assert p.get("/v1/hidrologia/estaciones?departamento=22").status_code == 200 and p.get("/v1/hidrologia/descargar?archivo=todo").status_code == 200


def test_perú_incluye_el_mef_de_cada_departamento(sitio):
    g = entrar(invitar(sitio, {"tres": ["mef"]})["enlace"])
    assert g.get("/v1/mef/archivos").status_code == 200
    for dep in ("16", "01", "25"):
        assert g.get(f"/v1/descargas/vista-previa?base=inv-dev-funcion&departamento={dep}&nivel=GN&desde=2026-01&hasta=2026-02").status_code != 403
    assert g.get("/v1/cuadros/ejecucion?departamento=01&sector=inversion").status_code != 403
    assert g.get("/v1/descargas/vista-previa?base=empleo&departamento=16&desde=2026-01&hasta=2026-02").status_code == 403


def test_vence_y_se_revoca(sitio):
    inv = invitar(sitio, {"lor": ["pesca"]})
    g = entrar(inv["enlace"])
    assert g.get("/v1/cuadros/pesca?departamento=16").status_code != 401
    lista = sitio.get("/v1/compartir").json()["invitaciones"]
    assert lista[0]["estado"] == "activa" and lista[0]["accesos"] == 1 and "huella" not in lista[0]
    assert sitio.delete(f"/v1/compartir/{inv['id']}").status_code == 200
    assert g.get("/v1/cuadros/pesca?departamento=16").status_code == 401                      # revocada: la cookie ya no sirve
    assert sitio.get("/v1/compartir").json()["invitaciones"][0]["estado"] == "revocada"
    # vencida
    inv2 = invitar(sitio, {"lor": ["pesca"]})
    from sqlalchemy import text
    with db.motor().begin() as cx:
        cx.execute(text("UPDATE invitaciones SET vence = '2020-01-01T00:00:00+00:00' WHERE id = :i"), {"i": inv2["id"]})
    assert TestClient(app).get(inv2["enlace"].replace("http://testserver", "")).status_code == 403


def test_crear_pide_datos_y_limpia_permisos(sitio):
    assert sitio.post("/v1/compartir", json={"nombre": "", "permisos": {"lor": ["pesca"]}}).status_code == 422
    assert sitio.post("/v1/compartir", json={"nombre": "X", "permisos": {}}).status_code == 422
    assert sitio.post("/v1/compartir", json={"nombre": "X", "permisos": {"smn": ["hidro", "impo"], "otra": ["pesca"]}}).status_code == 422    # hidro e impo no existen en San Martín
    assert sitio.post("/v1/compartir", json={"nombre": "X", "permisos": {"smn": ["hidro", "pesca"]}}).status_code == 200
    assert compartir.listar()[0]["permisos"] == {"smn": ["pesca"]}
    assert "huella" not in str(sitio.get("/v1/compartir").json())


def test_salir_del_acceso_de_invitado(sitio):
    g = entrar(invitar(sitio, {"lor": ["pesca"]})["enlace"])
    assert g.get("/v1/acceso/yo").json()["equipo"] is False
    r = g.get("/salir")
    assert r.status_code == 303 and compartir.COOKIE in r.headers["set-cookie"] and "Max-Age=0" in r.headers["set-cookie"]
    g.cookies.clear()                                            # el navegador borra la cookie vencida
    r = g.get("/")
    assert r.status_code == 401 and "Basic" in r.headers["www-authenticate"]       # vuelve a pedir usuario y clave


def test_el_enlace_manda_sobre_las_credenciales_guardadas_en_el_navegador(sitio):
    """Una computadora con el usuario y la clave del equipo recordados (se envían solas) que abre un enlace de invitado ve
    solo lo compartido, no toda la página."""
    inv = invitar(sitio, {"lor": ["pesca"]})
    token = inv["enlace"].split("t=")[1]
    navegador = TestClient(app, follow_redirects=False)
    navegador.auth = EQUIPO                                              # las credenciales viajan en cada petición
    r = navegador.get(f"/?t={token}")
    assert r.status_code == 303 and compartir.COOKIE in r.headers["set-cookie"]
    for url in ("/v1/compartir", "/v1/estado/espacio", "/v1/cuadros/manufactura?departamento=16"):
        assert navegador.get(url).status_code == 403, url
    assert navegador.get("/v1/acceso/yo").json()["equipo"] is False
    assert navegador.get("/v1/cuadros/pesca?departamento=16").status_code != 403
    # «Salir» borra la cookie y vuelve el acceso completo del equipo
    navegador.get("/salir")
    navegador.cookies.clear()
    assert navegador.get("/v1/acceso/yo").json()["equipo"] is True
    assert navegador.get("/v1/compartir").status_code == 200


def test_sin_permiso_de_descarga_ve_pero_no_baja_datos(sitio):
    subir(sitio, crudo())
    g = entrar(invitar(sitio, {"lor": ["pesca", "hidrologia", "hidro"]}, descargas=False)["enlace"])
    assert g.get("/v1/acceso/yo").json()["descargas"] is False
    # ve los cuadros, los gráficos y el mapa (lo que arma la página y se copia o baja como imagen)
    for url in ("/v1/cuadros/pesca?departamento=16", "/v1/hidrologia/estaciones?departamento=16", "/v1/hidrocarburos/mapa",
                "/v1/hidrologia/serie?estacion=240001&variable=NIVEL&anio=2026"):
        assert g.get(url).status_code not in (401, 403), url
    # no baja archivos de datos (CSV, Excel), ni su vista previa
    for url in ("/v1/cuadros/pesca?departamento=16&formato=xlsx", "/v1/hidrologia/descargar?archivo=diario&departamento=16",
                "/v1/descargas/vista-previa?base=pesca-loreto&departamento=16&desde=2026-01&hasta=2026-02",
                "/v1/descargas?base=pesca-loreto&departamento=16&desde=2026-01&hasta=2026-02&formato=csv", "/v1/hidrocarburos/mapa?descargar=true"):
        r = g.get(url)
        assert r.status_code == 403 and "no descargar los datos" in r.json()["detail"], url
    assert g.post("/v1/bcrp/excel", json={}).status_code == 403
    # con el permiso, sí
    c = entrar(invitar(sitio, {"lor": ["pesca"]}, descargas=True)["enlace"])
    assert c.get("/v1/cuadros/pesca?departamento=16&formato=xlsx").status_code != 403
    assert {x["descargas"] for x in sitio.get("/v1/compartir").json()["invitaciones"]} == {True, False}


def test_un_enlace_nuevo_funciona_en_una_ventana_con_un_enlace_revocado(sitio):
    """Incógnito: la ventana conserva la cookie de un enlace anterior ya revocado; el enlace nuevo de la dirección debe mandar."""
    viejo = invitar(sitio, {"lor": ["pesca"]})
    ventana = entrar(viejo["enlace"])
    sitio.delete(f"/v1/compartir/{viejo['id']}")
    nuevo = invitar(sitio, {"smn": ["empleo"]}, nombre="Otro")
    r = ventana.get(nuevo["enlace"].replace("http://testserver", ""))
    assert r.status_code == 303 and compartir.COOKIE in r.headers["set-cookie"]
    assert ventana.get("/v1/acceso/yo").json()["nombre"] == "Otro"


def test_enlace_vencido_muestra_una_pagina_legible(sitio):
    r = TestClient(app).get("/?t=inventada")
    assert r.status_code == 403 and "text/html" in r.headers["content-type"] and "Este enlace ya no es válido" in r.text
    assert TestClient(app).get("/v1/estado").headers["content-type"].startswith("application/json")        # lo demás, igual
