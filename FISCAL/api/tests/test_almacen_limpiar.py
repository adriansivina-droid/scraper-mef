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
