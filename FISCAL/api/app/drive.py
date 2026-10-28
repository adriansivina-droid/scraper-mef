"""Sincroniza desde Drive la pesca y los hidrocarburos: baja los archivos nuevos o modificados y los carga como si se
hubieran subido en la página.
  · Pesca: los Excel de las carpetas de crudos de cada DIREPRO.
  · Hidrocarburos: de la carpeta DATA del Proyecto Petróleo (HIDROCARBUROS/perupetro_produccion.md), solo la producción
    de líquidos y de gas por lote (el CSV más reciente de cada uno) y el canon por departamento. Lo usan el botón «Sincronizar desde Drive» y GitHub Actions
(.github/workflows/pesca_drive.yml).

Credencial: variable GOOGLE_DRIVE_CREDENCIAL con el JSON de HIDROCARBUROS/automatizacion/PP_Credencial_Drive.ipynb
(tipo authorized_user, la misma que usa el flujo de hidrocarburos) o el de una cuenta de servicio con acceso a las
carpetas. Solo se lee: el API nunca escribe ni borra en Drive.
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from . import carga, db, hidrocarburos, ipc

# carpeta de crudos de cada base de pesca (PESCA/pesca.md); se pueden cambiar con variables de entorno
CARPETAS = {
    "pesca-loreto": os.environ.get("DRIVE_CRUDOS_LORETO", "1FRKRjpHi_KX5twCCafYiHedPuQPscWqj"),
    "pesca-san-martin": os.environ.get("DRIVE_CRUDOS_SAN_MARTIN", "1Kkwys70cT3Z4ia5T7tO6CmNuQX-mSKWT"),
    "pesca-ucayali": os.environ.get("DRIVE_CRUDOS_UCAYALI", "1AEEvAfbtJwbkW773mKg-BIsDwjigjCg9"),
    "hidrocarburos": os.environ.get("DRIVE_HIDROCARBUROS_DATA", "1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq"),
}
MAPAS = ("PP_mapa_lotes_plus.html", "PP_mapa_lotes.html")   # el primero que haya, en ese orden
REGION = {"pesca-loreto": "Loreto", "pesca-san-martin": "San Martín", "pesca-ucayali": "Ucayali", "hidrocarburos": "Hidrocarburos"}
API = "https://www.googleapis.com/drive/v3/files"
_en_curso = threading.Lock()


class SincronizacionEnCurso(Exception):
    pass


def configurado():
    return bool(os.environ.get("GOOGLE_DRIVE_CREDENCIAL", "").strip())


class LectorDrive:
    """Lista y baja archivos de Drive con la credencial (solo lectura)."""

    def __init__(self, credencial_json):
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        info = json.loads(credencial_json)
        alcance = ["https://www.googleapis.com/auth/drive.readonly"] if info.get("type") == "service_account" else None
        cred, _ = google.auth.load_credentials_from_dict(info, scopes=alcance)
        self.sesion = AuthorizedSession(cred)

    def listar(self, carpeta, aceptar=None):
        """[{id, name, modifiedTime}] de los archivos de la carpeta que pasan `aceptar(nombre)` (por defecto, los .xlsx). Falla si la cuenta no puede ver la carpeta (Drive
        devolvería una lista vacía y parecería que no hay archivos)."""
        r = self.sesion.get(f"{API}/{carpeta}", params={"fields": "id,name,mimeType", "supportsAllDrives": "true"}, timeout=60)
        if r.status_code == 404:
            raise PermissionError(f"la cuenta de la credencial no puede ver la carpeta {carpeta}: compártela con esa "
                                  "cuenta o revisa el ID")
        r.raise_for_status()
        if r.json().get("mimeType") != "application/vnd.google-apps.folder":
            raise ValueError(f"el ID {carpeta} no es una carpeta de Drive")
        archivos, pagina = [], None
        while True:
            params = {"q": f"'{carpeta}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'",
                      "fields": "nextPageToken,files(id,name,modifiedTime)", "pageSize": 1000,
                      "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            if pagina:
                params["pageToken"] = pagina
            r = self.sesion.get(API, params=params, timeout=60)
            r.raise_for_status()
            j = r.json()
            archivos += j.get("files", [])
            pagina = j.get("nextPageToken")
            if not pagina:
                aceptar = aceptar or (lambda n: n.lower().endswith(".xlsx") and not n.startswith("~$"))
                return [a for a in archivos if aceptar(a["name"])]

    def subcarpeta(self, carpeta, nombre):
        """ID de la subcarpeta con ese nombre, o None."""
        q = (f"'{carpeta}' in parents and trashed = false and name = '{nombre}' "
             "and mimeType = 'application/vnd.google-apps.folder'")
        r = self.sesion.get(API, params={"q": q, "fields": "files(id)", "supportsAllDrives": "true",
                                         "includeItemsFromAllDrives": "true"}, timeout=60)
        r.raise_for_status()
        f = r.json().get("files", [])
        return f[0]["id"] if f else None

    def buscar(self, nombre):
        """Archivos con ese nombre en todo lo que ve la cuenta: [{id, name, modifiedTime}]."""
        r = self.sesion.get(API, params={"q": f"name = '{nombre}' and trashed = false", "fields": "files(id,name,modifiedTime)",
                                         "supportsAllDrives": "true", "includeItemsFromAllDrives": "true", "corpora": "allDrives"}, timeout=60)
        r.raise_for_status()
        return r.json().get("files", [])

    def bajar(self, file_id):
        r = self.sesion.get(f"{API}/{file_id}", params={"alt": "media", "supportsAllDrives": "true"}, timeout=300)
        r.raise_for_status()
        return r.content


def _tablas():
    with db.motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS drive_archivos (file_id TEXT PRIMARY KEY, nombre TEXT, base TEXT, "
                        "modificado TEXT, fecha TEXT)"))
        cx.execute(text("CREATE TABLE IF NOT EXISTS drive_sincronizaciones (fecha TEXT, origen TEXT, resumen TEXT)"))


def _vistos():
    with db.motor().connect() as cx:
        return dict(cx.execute(text("SELECT file_id, modificado FROM drive_archivos")).all())


def ultima():
    """La última sincronización (también las que no encontraron nada nuevo), o None."""
    _tablas()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT fecha, origen, resumen FROM drive_sincronizaciones ORDER BY fecha DESC LIMIT 1")).first()
    return None if r is None else {"fecha": r[0], "origen": r[1], "resumen": json.loads(r[2])}


def _nombre_unico(nombre, usados):
    """Dos carpetas pueden tener archivos con el mismo nombre: se distinguen sin perder el AAAA-MM del nombre."""
    if nombre not in usados:
        return nombre
    p, i = Path(nombre), 2
    while f"{p.stem} ({i}){p.suffix}" in usados:
        i += 1
    return f"{p.stem} ({i}){p.suffix}"


def _listar(lector, base_id, carpeta):
    if base_id != "hidrocarburos":
        return lector.listar(carpeta)
    # de cada tipo, solo el más reciente (en DATA pueden quedar CSV de corridas con otro rango de años)
    ultimos = {}
    for a in lector.listar(carpeta, hidrocarburos.tipo):
        t = hidrocarburos.tipo(a["name"])
        if t not in ultimos or a["modifiedTime"] > ultimos[t]["modifiedTime"]:
            ultimos[t] = a
    # el mapa de lotes (DATA/MAPA/PP_mapa_lotes_plus.html; si no está, el simple) se guarda aparte para la página
    mapa = lector.subcarpeta(carpeta, "MAPA") if hasattr(lector, "subcarpeta") else None
    if mapa:
        htmls = {a["name"]: a for a in lector.listar(mapa, lambda n: n in MAPAS)}
        elegido = next((htmls[n] for n in MAPAS if n in htmls), None)
        if elegido:
            ultimos["mapa"] = elegido
    return list(ultimos.values())


def _ipc(lector):
    """IPC de Lima para las variaciones reales: del BCRP; si no responde, el IPC.xlsx más reciente de Drive."""
    try:
        return ipc.actualizar_bcrp()
    except Exception as e:
        motivo = f"el BCRP no respondió ({type(e).__name__})"
    try:
        hallados = lector.buscar("IPC.xlsx") if hasattr(lector, "buscar") else []
        if hallados:
            a = max(hallados, key=lambda x: x["modifiedTime"])
            s = ipc.de_excel(lector.bajar(a["id"]))
            return f"IPC de Lima: {motivo}; se usó IPC.xlsx de Drive ({ipc.guardar(s, 'IPC.xlsx de Drive')} meses, hasta {max(s)})."
    except Exception as e:
        return f"IPC de Lima: {motivo} y no se pudo leer IPC.xlsx de Drive ({e})."
    return f"IPC de Lima: {motivo} y no hay IPC.xlsx en Drive; las variaciones quedan en términos nominales."


def sincronizar(origen="botón de la página", todo=False, lector=None):
    """Carga los Excel nuevos o modificados (todos, con todo=True) de las carpetas de crudos. Devuelve el resumen."""
    if not _en_curso.acquire(blocking=False):
        raise SincronizacionEnCurso("Ya hay una sincronización en curso; espera a que termine.")
    try:
        _tablas()
        lector = lector or LectorDrive(os.environ["GOOGLE_DRIVE_CREDENCIAL"])
        vistos = {} if todo else _vistos()
        listados = {base_id: _listar(lector, base_id, carpeta) for base_id, carpeta in CARPETAS.items()}
        nuevos = [(base_id, a) for base_id, lista in listados.items() for a in lista if vistos.get(a["id"]) != a["modifiedTime"]]
        mapas = [a for _, a in nuevos if a["name"] in MAPAS]
        datos = [(b, a) for b, a in nuevos if a["name"] not in MAPAS]
        for a in mapas:                                 # el mapa no es una base: se guarda tal cual para la página
            db.guardar_documento("mapa-hidrocarburos", lector.bajar(a["id"]).decode("utf-8", "replace"), a["modifiedTime"])
        if datos:
            usados, archivos = set(), []
            for _, a in datos:
                nombre = _nombre_unico(a["name"], usados)
                usados.add(nombre)
                archivos.append((nombre, lector.bajar(a["id"])))
            resumen = carga.cargar(f"Drive ({origen}): {', '.join(a['name'] for _, a in datos)}"[:250], archivos)
        elif mapas:
            resumen = {"bases": {}, "avisos": []}
        else:
            hay = ", ".join(f"{REGION[b]}: {len(lista)}" for b, lista in listados.items())
            resumen = {"bases": {}, "avisos": [f"No hay archivos nuevos ni modificados en las carpetas de Drive "
                                               f"(archivos en cada carpeta · {hay})."]}
        if mapas:
            resumen["avisos"].append(f"Mapa de lotes de hidrocarburos actualizado ({mapas[0]['name']}).")
        resumen["avisos"].append(_ipc(lector))
        resumen["archivos"] = [{"base": b, "nombre": a["name"]} for b, a in nuevos]
        resumen["carpetas"] = {b: len(lista) for b, lista in listados.items()}
        ahora = datetime.now(timezone.utc).isoformat(timespec="microseconds")   # ordena las sincronizaciones
        with db.motor().begin() as cx:
            # un archivo que no se pudo leer también queda visto: se vuelve a intentar si cambia o con todo=True
            for base_id, a in nuevos:
                cx.execute(text("DELETE FROM drive_archivos WHERE file_id = :i"), {"i": a["id"]})
                cx.execute(text("INSERT INTO drive_archivos (file_id, nombre, base, modificado, fecha) VALUES (:i, :n, :b, :m, :f)"),
                           {"i": a["id"], "n": a["name"], "b": base_id, "m": a["modifiedTime"], "f": ahora})
            cx.execute(text("INSERT INTO drive_sincronizaciones (fecha, origen, resumen) VALUES (:f, :o, :r)"),
                       {"f": ahora, "o": origen, "r": json.dumps(resumen, ensure_ascii=False)})
        return resumen
    finally:
        _en_curso.release()
