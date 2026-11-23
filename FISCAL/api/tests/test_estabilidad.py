"""Que la página no se cuelgue: trabajos pesados limitados, vista previa cortada en la base de datos, tablas auxiliares
creadas una sola vez y sin choques entre peticiones simultáneas."""
import pandas as pd
import pytest
from sqlalchemy import text

from app import db
from app.main import TrabajosPesados
from tests.test_api import cliente_http


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'estab.db'}")
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    yield cliente_http()
    db.reiniciar_motor()


@pytest.mark.parametrize("ruta, consulta, pesado", [
    ("/v1/descargas", b"base=x&formato=xlsx", True),
    ("/v1/descargas/vista-previa", b"base=x", False),
    ("/v1/ejecucion/estad", b"departamento=16", False),               # la vista en la página es liviana
    ("/v1/ejecucion/estad", b"departamento=16&formato=xlsx", True),
    ("/v1/cuadros/ejecucion", b"departamento=16&formato=xlsx", True),
    ("/v1/cuadros/ejecucion", b"departamento=16", False),
    ("/v1/importaciones/estad.xlsx", b"periodo=2026-01", True),
    ("/v1/cargas", b"", True),
    ("/v1/estado", b"", False),
    ("/salud", b"", False),
])
def test_que_es_un_trabajo_pesado(ruta, consulta, pesado):
    assert TrabajosPesados.es_pesado(ruta, consulta) is pesado


def test_ocupado_responde_503_legible(cliente, monkeypatch):
    """Si los turnos están tomados, después de esperar responde 503: JSON para la página, HTML si se navegó a la descarga."""
    monkeypatch.setattr(TrabajosPesados, "MAX_PESADOS", 0)               # todos los turnos tomados
    monkeypatch.setattr(TrabajosPesados, "_sem", (None, None))
    monkeypatch.setattr(TrabajosPesados, "ESPERA_S", 0.05)
    r = cliente.get("/v1/ejecucion/estad?departamento=16&formato=xlsx")
    assert r.status_code == 503 and "ocupado" in r.json()["detail"] and r.headers["retry-after"] == "60"
    r = cliente.get("/v1/ejecucion/estad?departamento=16&formato=xlsx", headers={"Accept": "text/html"})
    assert r.status_code == 503 and "Volver a la página" in r.text
    assert cliente.get("/salud").json() == {"ok": True}                 # lo liviano no hace fila
    TrabajosPesados._sem = (None, None)


def test_vista_previa_cuenta_y_corta_en_la_base(cliente):
    filas = [{"AÑO": a, "MES": f"{m:02d}: X", "NIVEL_GOBIERNO": f"{n}: X", "DEPARTAMENTO": "16: LORETO", "COD_GENERICA": c,
              "GENERICA": c, "DESGLOSE": "SIN DESGLOSE", "DEVENGADO": float(a + m)}
             for a in (2025, 2026) for m in range(1, 13) for n in "ERM" for c in ("5-2-1", "5-2-3", "6-2-6")]
    df = pd.DataFrame(filas)
    db.guardar("gasto-dev-generica", df.assign(_anio=df["AÑO"], _mes=df["MES"].str[:2].astype(int), _depto="16", _nivel=df["NIVEL_GOBIERNO"].str[0]))
    completo = db.leer("gasto-dev-generica", ["16"], ["R", "M"], "2025-03", "2026-08")
    n, muestra = db.muestra("gasto-dev-generica", ["16"], ["R", "M"], "2025-03", "2026-08", 8)
    assert n == len(completo) == 18 * 2 * 3
    assert muestra.equals(completo.head(8).reset_index(drop=True))
    v = cliente.get("/v1/descargas/vista-previa?base=gasto-dev-generica&departamento=16&nivel=regional,locales"
                    "&desde=2025-03&hasta=2026-08&filas=8").json()
    assert v["filas_total"] == 108 and len(v["archivos"][0]["muestra"]) == 8


def test_tablas_auxiliares_una_sola_vez(cliente):
    sql = "CREATE TABLE IF NOT EXISTS prueba_aux (a TEXT)"
    db.crear_tablas(sql)
    with db.motor().begin() as cx:
        cx.execute(text("DROP TABLE prueba_aux"))
    db.crear_tablas(sql)                                   # ya la creó este proceso: no vuelve a la base de datos
    assert not db.existe("prueba_aux")
    db._crear(db.motor(), sql)                             # y crearla otra vez (o a la vez que otro) no falla
    db._crear(db.motor(), sql)
    assert db.existe("prueba_aux")


def test_base_caida_da_503_legible(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")      # nadie escucha en el puerto 1
    monkeypatch.delenv("APP_CLAVE", raising=False)
    db.reiniciar_motor()
    try:
        r = TestClient(app, raise_server_exceptions=False).get("/v1/estado")
        assert r.status_code == 503 and "no responde" in r.json()["detail"]
    finally:
        db.reiniciar_motor()
