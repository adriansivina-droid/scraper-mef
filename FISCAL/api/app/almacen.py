"""Almacén de archivos en la base de la página: reemplaza a Google Drive para el flujo de hidrocarburos.

Los notebooks de HIDROCARBUROS/ guardaban en Drive (carpetas DATA y CONTROL) sus CSV acumulados, los PDF de PERUPETRO
ya bajados, los Excel de canon y las capas y el HTML del mapa. Ahora guardan todo aquí, en la tabla «almacen», con las
mismas carpetas e IDs: `ServicioDrive` imita las pocas llamadas de la API de Drive que usan (files().list con
«'<carpeta>' in parents», create, update y get_media, más MediaFileUpload y MediaIoBaseDownload), así que los notebooks
corren sin cambios (HIDROCARBUROS/automatizacion/ejecutar_notebooks.py lo instala en GitHub Actions).

`sincronizar` carga en las bases de la página lo nuevo de DATA (producción de líquidos, gas y diaria por lote, canon
por departamento) y el mapa de lotes. La corre el mismo flujo al terminar, y el botón de la página.
Los archivos van comprimidos (zlib) y en base64, en una columna de texto (igual en Postgres y en SQLite).

Excepción: DATA/PDF (los PDF anuales de PERUPETRO, ~450 MB, públicos y que el notebook vuelve a bajar si faltan) no va a
la base, para no llenarla: si ALMACEN_LOCAL apunta a una carpeta, se guarda allí (en GitHub Actions, la caché del flujo).
La carpeta «PDF» sigue en la base; solo su contenido va a disco.
"""
import base64
import json
import os
import re
import threading
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from . import carga, db, hidrocarburos

CARPETA_DATA = "1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq"      # los mismos IDs que tenían en Drive (fijos en los notebooks)
CARPETA_CONTROL = "1TKjS2Wjpnf26oladjhqstmN5c9Irq-Aj"
RAICES = {CARPETA_DATA: "DATA", CARPETA_CONTROL: "CONTROL"}
CARPETA = "application/vnd.google-apps.folder"
MAPAS = ("PP_mapa_lotes_plus.html", "PP_mapa_lotes.html")   # el primero que haya, en ese orden
EN_DISCO = {"PDF"}                                       # subcarpetas de DATA cuyo contenido no va a la base
_en_curso = threading.Lock()


class SincronizacionEnCurso(Exception):
    pass


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _tabla():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS almacen (id TEXT PRIMARY KEY, nombre TEXT, padre TEXT, mime TEXT, "
                        "contenido TEXT, tamano BIGINT, modificado TEXT)"))


def _codificar(datos):
    return base64.b64encode(zlib.compress(datos, 6)).decode("ascii")


def _decodificar(texto):
    return zlib.decompress(base64.b64decode(texto)) if texto else b""


# ── Carpetas en disco (ALMACEN_LOCAL) ──
def _disco():
    d = os.environ.get("ALMACEN_LOCAL", "").strip()
    return Path(d) if d else None


def _carpetas_en_disco():
    """IDs de las subcarpetas de DATA cuyo contenido va a disco (vacío si no hay ALMACEN_LOCAL)."""
    if _disco() is None:
        return set()
    with db.motor().connect() as cx:
        filas = cx.execute(text("SELECT id, nombre FROM almacen WHERE padre = :p AND mime = :m"), {"p": CARPETA_DATA, "m": CARPETA}).all()
    return {i for i, n in filas if n in EN_DISCO}


def _ruta_disco(id_):
    """«disco:<carpeta>/<nombre>» -> ruta, o None si no es de disco."""
    if not str(id_).startswith("disco:"):
        return None
    carpeta, nombre = id_[len("disco:"):].split("/", 1)
    if "/" in nombre or nombre in ("", ".", ".."):
        raise FileNotFoundError(id_)
    return _disco() / carpeta / nombre


def _hijos_disco(padre):
    carpeta = _disco() / padre
    if not carpeta.is_dir():
        return []
    return [{"id": f"disco:{padre}/{f.name}", "name": f.name, "mimeType": "application/pdf" if f.suffix.lower() == ".pdf" else "application/octet-stream",
             "modifiedTime": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"), "size": f.stat().st_size}
            for f in sorted(carpeta.iterdir()) if f.is_file()]


# ── Operaciones básicas ──
def hijos(padre):
    """[{id, name, mimeType, modifiedTime, size}] de una carpeta."""
    _tabla()
    if padre in _carpetas_en_disco():
        return _hijos_disco(padre)
    with db.motor().connect() as cx:
        filas = cx.execute(text("SELECT id, nombre, mime, modificado, tamano FROM almacen WHERE padre = :p ORDER BY nombre"),
                           {"p": padre}).all()
    return [{"id": i, "name": n, "mimeType": m, "modifiedTime": f, "size": t} for i, n, m, f, t in filas]


def crear(nombre, padre, contenido=None, mime=None, id_=None):
    """Archivo (o carpeta si contenido es None y mime es de carpeta). Devuelve su id."""
    _tabla()
    if contenido is not None and padre in _carpetas_en_disco():
        ruta = _disco() / padre / Path(nombre).name
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
        return f"disco:{padre}/{ruta.name}"
    id_ = id_ or uuid.uuid4().hex
    with db.motor().begin() as cx:
        cx.execute(text("DELETE FROM almacen WHERE id = :i"), {"i": id_})
        cx.execute(text("INSERT INTO almacen (id, nombre, padre, mime, contenido, tamano, modificado) "
                        "VALUES (:i, :n, :p, :m, :c, :t, :f)"),
                   {"i": id_, "n": nombre, "p": padre, "m": mime or "application/octet-stream",
                    "c": None if contenido is None else _codificar(contenido), "t": len(contenido or b""), "f": _ahora()})
    return id_


def reemplazar(id_, contenido, nombre=None):
    _tabla()
    ruta = _ruta_disco(id_)
    if ruta is not None:
        ruta.write_bytes(contenido)
        return
    with db.motor().begin() as cx:
        r = cx.execute(text("UPDATE almacen SET contenido = :c, tamano = :t, modificado = :f" + (", nombre = :n" if nombre else "")
                            + " WHERE id = :i"),
                       {"c": _codificar(contenido), "t": len(contenido), "f": _ahora(), "n": nombre, "i": id_})
    if r.rowcount == 0:
        raise FileNotFoundError(f"no hay ningún archivo {id_} en el almacén")


def leer(id_):
    _tabla()
    ruta = _ruta_disco(id_)
    if ruta is not None:
        if not ruta.is_file():
            raise FileNotFoundError(id_)
        return ruta.read_bytes()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT contenido FROM almacen WHERE id = :i"), {"i": id_}).first()
    if r is None:
        raise FileNotFoundError(f"no hay ningún archivo {id_} en el almacén")
    return _decodificar(r[0])


def resumen():
    """Archivos y MB por carpeta raíz (para la página y los registros)."""
    _tabla()
    with db.motor().connect() as cx:
        filas = cx.execute(text("SELECT id, nombre, padre, mime, tamano, modificado FROM almacen")).all()
    padre = {i: p for i, _, p, _, _, _ in filas}

    def raiz(i):
        vistos = set()
        while i in padre and i not in vistos:
            vistos.add(i)
            i = padre[i]
        return RAICES.get(i, "otra")
    salida = {}
    for i, n, p, m, t, f in filas:
        if m == CARPETA:
            continue
        x = salida.setdefault(raiz(i), {"archivos": 0, "mb": 0.0, "modificado": ""})
        x["archivos"] += 1
        x["mb"] += (t or 0) / 1e6
        x["modificado"] = max(x["modificado"], f or "")
    return {k: {**v, "mb": round(v["mb"], 1)} for k, v in salida.items()}


def vacio():
    return not any(resumen().get(k, {}).get("archivos") for k in ("DATA", "CONTROL"))


# ── Sustituto de la API de Drive para los notebooks ──
class _Pedido:
    def __init__(self, hacer):
        self._hacer = hacer

    def execute(self, *a, **k):
        return self._hacer()


class MediaFileUpload:
    def __init__(self, filename, mimetype=None, resumable=False, **k):
        self.filename, self.mimetype = filename, mimetype

    def datos(self):
        return Path(self.filename).read_bytes()


class MediaIoBaseUpload:
    def __init__(self, fd, mimetype=None, resumable=False, **k):
        self.fd, self.mimetype = fd, mimetype

    def datos(self):
        self.fd.seek(0)
        return self.fd.read()


class MediaIoBaseDownload:
    def __init__(self, fh, request, **k):
        self.fh, self.request = fh, request

    def next_chunk(self, *a, **k):
        self.fh.write(self.request.execute())
        return None, True


class HttpError(Exception):
    def __init__(self, resp=None, content=b"", uri=None):
        super().__init__(content)
        self.resp, self.content = resp, content


class _Archivos:
    def list(self, q="", fields=None, pageSize=None, pageToken=None, **k):
        m = re.search(r"'([^']+)'\s+in\s+parents", q or "")
        if not m:
            raise ValueError(f"consulta no soportada por el almacén: {q!r}")
        return _Pedido(lambda: {"files": hijos(m.group(1))})

    def create(self, body=None, media_body=None, fields=None, **k):
        body = body or {}
        padre = (body.get("parents") or [CARPETA_DATA])[0]
        datos = media_body.datos() if media_body is not None else None
        mime = body.get("mimeType") or getattr(media_body, "mimetype", None)
        return _Pedido(lambda: {"id": crear(body["name"], padre, datos, mime)})

    def update(self, fileId=None, body=None, media_body=None, **k):
        def hacer():
            reemplazar(fileId, media_body.datos() if media_body is not None else leer(fileId), (body or {}).get("name"))
            return {"id": fileId}
        return _Pedido(hacer)

    def get_media(self, fileId=None, **k):
        return _Pedido(lambda: leer(fileId))


class ServicioDrive:
    def files(self):
        return _Archivos()


def build(servicio="drive", version="v3", **k):
    if servicio != "drive":
        raise ValueError(f"el almacén de la página solo reemplaza a Drive, no a {servicio!r}")
    return ServicioDrive()


# ── Carga en la página ──
class LectorAlmacen:
    """Misma interfaz que leía la sincronización con Drive."""

    def listar(self, carpeta, aceptar=None):
        aceptar = aceptar or (lambda n: True)
        return [a for a in hijos(carpeta) if a["mimeType"] != CARPETA and aceptar(a["name"])]

    def subcarpeta(self, carpeta, nombre):
        return next((a["id"] for a in hijos(carpeta) if a["name"] == nombre and a["mimeType"] == CARPETA), None)

    def bajar(self, file_id):
        return leer(file_id)


def _tablas_sinc():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS almacen_vistos (file_id TEXT PRIMARY KEY, nombre TEXT, modificado TEXT, fecha TEXT)"))
        cx.execute(text("CREATE TABLE IF NOT EXISTS almacen_sincronizaciones (fecha TEXT, origen TEXT, resumen TEXT)"))


def ultima():
    """La última carga de hidrocarburos desde el almacén (también las que no encontraron nada nuevo), o None."""
    _tablas_sinc()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT fecha, origen, resumen FROM almacen_sincronizaciones ORDER BY fecha DESC LIMIT 1")).first()
    return None if r is None else {"fecha": r[0], "origen": r[1], "resumen": json.loads(r[2])}


def _a_cargar(lector):
    """De cada tipo de CSV de DATA, el más reciente (pueden quedar CSV de corridas con otro rango de años), y el mapa."""
    ultimos = {}
    for a in lector.listar(CARPETA_DATA, hidrocarburos.tipo):
        t = hidrocarburos.tipo(a["name"])
        if t not in ultimos or a["modifiedTime"] > ultimos[t]["modifiedTime"]:
            ultimos[t] = a
    mapa = lector.subcarpeta(CARPETA_DATA, "MAPA")
    if mapa:
        htmls = {a["name"]: a for a in lector.listar(mapa, lambda n: n in MAPAS)}
        elegido = next((htmls[n] for n in MAPAS if n in htmls), None)
        if elegido:
            ultimos["mapa"] = elegido
    return list(ultimos.values())


def sincronizar(origen="botón de la página", todo=False, lector=None):
    """Carga en las bases los CSV nuevos o modificados de DATA (todos, con todo=True) y el mapa. Devuelve el resumen."""
    if not _en_curso.acquire(blocking=False):
        raise SincronizacionEnCurso("Ya hay una carga de hidrocarburos en curso; espera a que termine.")
    try:
        _tablas_sinc()
        lector = lector or LectorAlmacen()
        with db.motor().connect() as cx:
            vistos = {} if todo else dict(cx.execute(text("SELECT file_id, modificado FROM almacen_vistos")).all())
        lista = _a_cargar(lector)
        nuevos = [a for a in lista if vistos.get(a["id"]) != a["modifiedTime"]]
        mapas = [a for a in nuevos if a["name"] in MAPAS]
        datos = [a for a in nuevos if a["name"] not in MAPAS]
        for a in mapas:                                 # el mapa no es una base: se guarda tal cual para la página
            db.guardar_documento("mapa-hidrocarburos", lector.bajar(a["id"]).decode("utf-8", "replace"), a["modifiedTime"])
        if datos:
            resumen_ = carga.cargar(f"Hidrocarburos ({origen}): {', '.join(a['name'] for a in datos)}"[:250],
                                    [(a["name"], lector.bajar(a["id"])) for a in datos])
        else:
            resumen_ = {"bases": {}, "avisos": [] if mapas else [f"No hay CSV nuevos ni modificados en DATA ({len(lista)} a cargar)."]}
        if mapas:
            resumen_["avisos"].append(f"Mapa de lotes de hidrocarburos actualizado ({mapas[0]['name']}).")
        resumen_["archivos"] = [{"nombre": a["name"]} for a in nuevos]
        ahora = _ahora()
        with db.motor().begin() as cx:
            # un archivo que no se pudo leer también queda visto: se vuelve a intentar si cambia o con todo=True
            for a in nuevos:
                cx.execute(text("DELETE FROM almacen_vistos WHERE file_id = :i"), {"i": a["id"]})
                cx.execute(text("INSERT INTO almacen_vistos (file_id, nombre, modificado, fecha) VALUES (:i, :n, :m, :f)"),
                           {"i": a["id"], "n": a["name"], "m": a["modifiedTime"], "f": ahora})
            cx.execute(text("INSERT INTO almacen_sincronizaciones (fecha, origen, resumen) VALUES (:f, :o, :r)"),
                       {"f": ahora, "o": origen, "r": json.dumps(resumen_, ensure_ascii=False)})
        return resumen_
    finally:
        _en_curso.release()


def descargar(id_):
    """(nombre, bytes) de un archivo del almacén, para bajarlo desde la página."""
    _tabla()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT nombre, contenido, mime FROM almacen WHERE id = :i"), {"i": id_}).first()
    if r is None or r[2] == CARPETA:
        raise FileNotFoundError(id_)
    return r[0], _decodificar(r[1])


def arbol():
    """Todas las carpetas y archivos (sin contenido), para la página."""
    _tabla()
    with db.motor().connect() as cx:
        filas = cx.execute(text("SELECT id, nombre, padre, mime, tamano, modificado FROM almacen ORDER BY nombre")).all()
    return [{"id": i, "nombre": n, "padre": p, "carpeta": m == CARPETA, "kb": round((t or 0) / 1024), "modificado": f}
            for i, n, p, m, t, f in filas]

