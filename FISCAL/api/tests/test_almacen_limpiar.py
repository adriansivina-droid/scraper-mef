"""Limpieza del almacén: borra los CSV contenidos en otro de mayor rango, las capturas de error viejas y las capas del
mapa que la última corrida no regeneró; conserva todo lo demás."""
from app import almacen, db


def test_limpiar(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'alm.db'}")
    db.reiniciar_motor()
    D, C = almacen.CARPETA_DATA, almacen.CARPETA_CONTROL
    mapa = almacen.crear("MAPA", D, mime=almacen.CARPETA)
    almacen.crear("PP_produccion_lote_mes_1994-2026.csv", D, b"a" * 900, modificado="2026-11-05T13:49:05Z")
    almacen.crear("PP_produccion_lote_mes_2026-2026.csv", D, b"b" * 90, modificado="2026-10-21T16:37:54Z")
    almacen.crear("PP_produccion_lote_mes_1990-1995.csv", D, b"c" * 90, modificado="2026-10-21T16:37:54Z")   # no está contenido
    almacen.crear("CONTROL PP mef_error_2003.png", C, b"png", modificado="2026-10-20T19:53:29Z")
    almacen.crear("PP_OLEODUCTO_NORPERUANO.geojson", mapa, b"{}", modificado="2026-11-05T14:27:44Z")
    almacen.crear("EXT_OLEODUCTO_NORPERUANO.geojson", mapa, b"{}", modificado="2026-10-12T03:19:32Z")
    almacen.crear("PP_lotes_indicadores.geojson", mapa, b"{}", modificado="2026-09-01T00:00:00Z")          # se relee: queda
    almacen.crear("PP_mapa_lotes_plus.html", mapa, b"<html>", modificado="2026-09-01T00:00:00Z")
    prueba = almacen.limpiar(aplicar=False)
    assert sorted(x["nombre"] for x in prueba["archivos"]) == [
        "CONTROL PP mef_error_2003.png", "EXT_OLEODUCTO_NORPERUANO.geojson", "PP_produccion_lote_mes_2026-2026.csv"]
    assert len(almacen.hijos(D)) == 4                                   # en prueba no borra nada
    almacen.limpiar(aplicar=True)
    assert {a["name"] for a in almacen.hijos(D)} == {"MAPA", "PP_produccion_lote_mes_1994-2026.csv", "PP_produccion_lote_mes_1990-1995.csv"}
    assert {a["name"] for a in almacen.hijos(mapa)} == {"PP_OLEODUCTO_NORPERUANO.geojson", "PP_lotes_indicadores.geojson", "PP_mapa_lotes_plus.html"}
    assert almacen.hijos(C) == [] and almacen.limpiar(aplicar=True)["archivos"] == []
    db.reiniciar_motor()


def test_convertir_de_texto_a_binario(tmp_path, monkeypatch):
    """Lo guardado antes (zlib en base64, columna de texto) se sigue leyendo y `convertir` lo pasa a binario sin cambiar
    un byte; un archivo dañado se deja como estaba."""
    import base64
    import os
    import zlib

    from sqlalchemy import text
    monkeypatch.setenv("DATABASE_URL", os.environ.get("PRUEBA_DATABASE_URL") or f"sqlite:///{tmp_path / 'alm2.db'}")
    db.reiniciar_motor()
    with db.motor().begin() as cx:                      # la tabla como la creaba la versión anterior, sin «binario»
        cx.execute(text("DROP TABLE IF EXISTS almacen"))
        cx.execute(text("CREATE TABLE almacen (id TEXT PRIMARY KEY, nombre TEXT, padre TEXT, mime TEXT, contenido TEXT, tamano BIGINT, modificado TEXT)"))
        viejo = {"v1": os.urandom(5000) + b"a" * 20000, "v2": "año;mes\n2026;11\n".encode("utf-8") * 300}
        for i, datos in viejo.items():
            cx.execute(text("INSERT INTO almacen VALUES (:i, :n, :p, 'text/csv', :c, :t, '2026-11-01T00:00:00Z')"),
                       {"i": i, "n": i + ".csv", "p": almacen.CARPETA_DATA, "c": base64.b64encode(zlib.compress(datos, 6)).decode(), "t": len(datos)})
        cx.execute(text("INSERT INTO almacen VALUES ('malo', 'malo.csv', :p, 'text/csv', 'no-es-base64-valido', 10, '2026-11-01T00:00:00Z')"),
                   {"p": almacen.CARPETA_DATA})
    almacen._tabla_lista = None
    assert almacen.leer("v1") == viejo["v1"] and almacen.descargar("v2") == ("v2.csv", viejo["v2"])   # se lee sin convertir
    nuevo = almacen.crear("nuevo.csv", almacen.CARPETA_DATA, b"n" * 4000)
    prueba = almacen.convertir(aplicar=False)
    assert prueba["pendientes"] == 3 and prueba["convertidos"] == 0 and not prueba["aplicado"]
    r = almacen.convertir()
    assert r["convertidos"] == 2 and r["sin_tocar"] == ["malo.csv"]
    assert almacen.leer("v1") == viejo["v1"] and almacen.leer("v2") == viejo["v2"] and almacen.leer(nuevo) == b"n" * 4000
    with db.motor().connect() as cx:
        filas = dict(cx.execute(text("SELECT id, contenido IS NULL FROM almacen")).all())
    assert filas["v1"] and filas["v2"] and filas[nuevo] and not filas["malo"]
    assert almacen.convertir()["convertidos"] == 0                       # repetirlo no hace nada
    almacen.reemplazar("v1", b"otro")
    assert almacen.leer("v1") == b"otro" and {a["name"] for a in almacen.hijos(almacen.CARPETA_DATA)} == {"v1.csv", "v2.csv", "malo.csv", "nuevo.csv"}
    db.reiniciar_motor()
