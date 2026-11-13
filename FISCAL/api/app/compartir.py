"""Compartir la página con terceros: un enlace con permisos por sector y por pestaña (Loreto, San Martín, Ucayali, Perú).

El equipo (usuario y clave de APP_CLAVE) crea una invitación: nombre, cuántos días vale y qué sectores ve en cada pestaña.
Queda un enlace `…/?t=<clave>`; el servidor guarda solo la huella (SHA-256) de la clave, así que no se puede volver a ver.
Quien abre el enlace recibe una cookie y entra a la página sin escribir usuario ni clave, pero solo con lo que se le dio.

La regla vive en el servidor (`permitido`): cada petición del invitado se compara con una lista de lo que puede pedir; lo que no
está en la lista se niega (nunca escribir, subir, actualizar ni administrar). La página oculta lo demás, pero no confía en eso.
"""
import hashlib
import json
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect, text

from . import db

COOKIE = "acceso_invitado"

# lo que se puede compartir en cada pestaña: (id, nombre en pantalla)
SECTORES_REGION = [("pesca", "Pesca"), ("hidro", "Hidrocarburos"), ("manu", "Manufactura"), ("empleo", "Empleo"), ("expo", "Exportaciones"),
                   ("impo", "Importaciones"), ("gasto", "Gasto corriente no financiero"), ("inversion", "Inversión pública"),
                   ("hidrologia", "Hidrología (SENAMHI)"), ("drae", "Gráficos DRAE")]
SECTORES_PERU = [("hidro-peru", "Ríos del Perú (SENAMHI): mapa, hidrogramas y descargas"), ("empleo", "Empleo: total, por sectores y LONG de las 26 regiones"),
                 ("mef", "MEF: 3 archivos y 25 departamentos"), ("bases", "Bases comparativas (pesca y empleo de las tres regiones)")]
# qué sectores existen en cada región (los mismos que muestra la página)
EXISTEN = {"lor": {"pesca", "hidro", "manu", "empleo", "expo", "impo", "gasto", "inversion", "hidrologia", "drae"},
           "smn": {"pesca", "manu", "empleo", "expo", "gasto", "inversion", "hidrologia", "drae"},
           "uca": {"pesca", "hidro", "manu", "empleo", "expo", "gasto", "inversion", "hidrologia", "drae"},
           "tres": {"hidro-peru", "empleo", "mef", "bases"}}
PESTAÑAS = {"lor": "Loreto", "smn": "San Martín", "uca": "Ucayali", "tres": "Perú"}
TAB_DE_DEPTO = {"16": "lor", "22": "smn", "25": "uca"}
DEPTO_DE_NOMBRE = {"loreto": "16", "san martin": "22", "ucayali": "25"}
# un sector de una región también se ve si se compartió el equivalente nacional de la pestaña Perú
NACIONAL = {"gasto": "mef", "inversion": "mef", "empleo": "empleo", "hidrologia": "hidro-peru"}
# las bases que se pueden descargar: sector al que pertenece cada una (las bases crudas de SUNAT no se comparten)
SECTOR_DE_BASE = {"inv-dev-funcion": "inversion", "inv-dev-municipalidad": "inversion", "inv-dev-fuente": "inversion", "inv-pim-funcion": "inversion",
                  "inv-pim-municipalidad": "inversion", "inv-proyectos": "inversion", "gasto-dev-generica": "gasto", "gasto-dev-fuente": "gasto",
                  "pesca-loreto": "pesca", "pesca-san-martin": "pesca", "pesca-ucayali": "pesca", "manu-ivf": "manu", "empleo": "empleo",
                  "empleo-sectores": "empleo", "hidro-produccion": "hidro", "hidro-canon": "hidro", "hidro-expo-empresa": "hidro",
                  "expo-estad": "expo", "impo-estad": "impo"}
_candado = threading.Lock()
_tabla_lista = None


# ── almacenamiento ───────────────────────────────────────────────────────────
def _tabla():
    global _tabla_lista
    m = db.motor()
    if _tabla_lista is m:
        return
    with m.begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS invitaciones (id TEXT PRIMARY KEY, huella TEXT UNIQUE, nombre TEXT, creado TEXT, vence TEXT, "
                        "permisos TEXT, ultimo_acceso TEXT, accesos INTEGER DEFAULT 0, revocada INTEGER DEFAULT 0, descargas INTEGER DEFAULT 0)"))
        if "descargas" not in {c["name"] for c in inspect(cx).get_columns("invitaciones")}:      # tablas creadas antes
            cx.execute(text("ALTER TABLE invitaciones ADD COLUMN descargas INTEGER DEFAULT 0"))
    _tabla_lista = m


def _ahora():
    return datetime.now(timezone.utc)


def _huella(token):
    return hashlib.sha256(token.encode()).hexdigest()


def limpiar_permisos(permisos):
    """Deja solo pestañas y sectores que existen; devuelve {pestaña: [sectores]} sin pestañas vacías."""
    out = {}
    for tab, lista in (permisos or {}).items():
        if tab in EXISTEN and isinstance(lista, list):
            ok = sorted({s for s in lista if s in EXISTEN[tab]})
            if ok:
                out[tab] = ok
    return out


def crear(nombre, dias, permisos, descargas=False):
    """Crea una invitación. Devuelve (id, token): el token solo se ve ahora. «descargas»: si puede bajar los datos (CSV, Excel);
    sin ese permiso solo ve los cuadros y gráficos en la página y puede copiarlos o bajarlos como imagen."""
    _tabla()
    permisos = limpiar_permisos(permisos)
    if not permisos:
        raise ValueError("Marca al menos un sector en alguna pestaña.")
    nombre = (nombre or "").strip()[:80]
    if not nombre:
        raise ValueError("Escribe para quién es (por ejemplo, «Gerencia de la Sucursal»).")
    dias = max(1, min(int(dias), 365))
    token = secrets.token_urlsafe(24)
    ident = uuid.uuid4().hex[:10]
    ahora = _ahora()
    with db.motor().begin() as cx:
        cx.execute(text("INSERT INTO invitaciones (id, huella, nombre, creado, vence, permisos, accesos, revocada, descargas) "
                        "VALUES (:i, :h, :n, :c, :v, :p, 0, 0, :d)"),
                   {"i": ident, "h": _huella(token), "n": nombre, "c": ahora.isoformat(timespec="seconds"),
                    "v": (ahora + timedelta(days=dias)).isoformat(timespec="seconds"), "p": json.dumps(permisos), "d": 1 if descargas else 0})
    return ident, token


def listar():
    _tabla()
    with db.motor().connect() as cx:
        filas = cx.execute(text("SELECT id, nombre, creado, vence, permisos, ultimo_acceso, accesos, revocada, descargas FROM invitaciones ORDER BY creado DESC")).all()
    ahora = _ahora().isoformat(timespec="seconds")
    return [{"id": i, "nombre": n, "creado": c, "vence": v, "permisos": json.loads(p), "ultimo_acceso": u, "accesos": a or 0, "descargas": bool(d),
             "estado": "revocada" if r else "vencida" if v < ahora else "activa"} for i, n, c, v, p, u, a, r, d in filas]


def revocar(ident):
    _tabla()
    with db.motor().begin() as cx:
        return cx.execute(text("UPDATE invitaciones SET revocada = 1 WHERE id = :i"), {"i": ident}).rowcount > 0


def validar(token, entrada=False):
    """La invitación vigente de ese token ({id, nombre, vence, permisos}) o None. «entrada» cuenta un ingreso por el enlace."""
    if not token or len(token) > 100:
        return None
    _tabla()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT id, nombre, vence, permisos, revocada, ultimo_acceso, descargas FROM invitaciones WHERE huella = :h"), {"h": _huella(token)}).first()
    if r is None or r[4] or r[2] < _ahora().isoformat(timespec="seconds"):
        return None
    ahora = _ahora()
    if entrada or not r[5] or r[5] < (ahora - timedelta(minutes=10)).isoformat(timespec="seconds"):     # no escribir en cada petición
        with db.motor().begin() as cx:
            cx.execute(text("UPDATE invitaciones SET ultimo_acceso = :u, accesos = COALESCE(accesos, 0) + :n WHERE id = :i"),
                       {"u": ahora.isoformat(timespec="seconds"), "n": 1 if entrada else 0, "i": r[0]})
    return {"id": r[0], "nombre": r[1], "vence": r[2], "permisos": json.loads(r[3]), "descargas": bool(r[6])}


# ── qué puede pedir un invitado ──────────────────────────────────────────────
def _tiene(perm, tab, sector):
    return sector in perm.get(tab, [])


def depto_ok(perm, sector, depto):
    """¿Puede ver el sector para ese departamento («16», «22», «25» u otro)?"""
    tab = TAB_DE_DEPTO.get(depto)
    if tab and _tiene(perm, tab, sector):
        return True
    if NACIONAL.get(sector) and _tiene(perm, "tres", NACIONAL[sector]):
        return True
    return bool(tab and sector in ("pesca", "empleo") and _tiene(perm, "tres", "bases"))       # «Comparar regiones»


def cualquier_region(perm, sector):
    """«todos»: basta con tener el sector en alguna pestaña de región (o el equivalente nacional)."""
    return any(_tiene(perm, t, sector) for t in ("lor", "smn", "uca")) or bool(NACIONAL.get(sector) and _tiene(perm, "tres", NACIONAL[sector]))


def _lista(valor):
    return [x.strip() for x in (valor or "").split(",") if x.strip()]


def depto_ok_o_todos(sector, d):
    return ("todos", sector) if d == "todos" else ("depto", sector, d)


def _estaciones_permitidas(perm):
    """Códigos de estación que puede ver: todas con «Ríos del Perú»; si no, las de las regiones con Hidrología."""
    from . import hidrologia
    if _tiene(perm, "tres", "hidro-peru"):
        return None
    out = set()
    for d, tab in TAB_DE_DEPTO.items():
        if _tiene(perm, tab, "hidrologia"):
            out |= set(hidrologia._codigos(d))
    return out


RUTAS_DE_DESCARGA = {"/v1/descargas", "/v1/descargas/vista-previa", "/v1/descargas/empleo", "/v1/hidrologia/descargar", "/v1/bcrp/excel"}


def es_descarga(metodo, ruta, q):
    """¿La petición baja datos en un archivo (CSV, Excel) o su vista previa? Las imágenes se arman en el navegador y no pasan por aquí."""
    return (ruta in RUTAS_DE_DESCARGA or q.get("formato", "json") not in ("json", "") or
            (ruta == "/v1/hidrocarburos/mapa" and str(q.get("descargar", "")).lower() in ("true", "1")))


def permitido(perm, metodo, ruta, q, descargas=False):
    """(True, "") si el invitado puede hacer esta petición; si no, (False, motivo). `q` = parámetros de la dirección.
    «descargas»: si la invitación permite bajar los datos (CSV, Excel)."""
    no = (False, "Esa parte de la página no está incluida en el acceso que recibiste.")
    ok = (True, "")
    if not descargas and es_descarga(metodo, ruta, q):
        return False, "Tu acceso permite ver los cuadros y gráficos, y bajarlos como imagen, pero no descargar los datos."
    if metodo == "POST":
        return ok if ruta == "/v1/bcrp/excel" else no            # solo arma un Excel con lo que la página ya mostró
    if metodo != "GET":
        return no
    if ruta in ("/", "/v1/catalogo", "/v1/estado", "/v1/acceso/yo"):
        return ok
    exigencias = []                                              # lo que hay que tener para esta petición
    if ruta in ("/v1/descargas", "/v1/descargas/vista-previa"):
        bases, deptos = _lista(q.get("base")), _lista(q.get("departamento"))
        if not bases or not deptos:
            return ok                                            # el servidor la rechaza con su propio mensaje
        for b in bases:
            if b not in SECTOR_DE_BASE:
                return no
            exigencias += [("depto", SECTOR_DE_BASE[b], d) for d in deptos]
    elif ruta == "/v1/drae":
        exigencias = [("depto", "drae", q.get("departamento", ""))]
    elif ruta == "/v1/cuadros/ejecucion":
        exigencias = [("depto", q.get("sector", "gasto") if q.get("sector") in ("gasto", "inversion") else "gasto", q.get("departamento", ""))]
    elif ruta in ("/v1/variaciones", "/v1/proyectos"):
        exigencias = [("depto", "inversion", q.get("departamento", ""))]
    elif ruta == "/v1/cuadros/pesca":
        exigencias = [("depto", "pesca", q.get("departamento", ""))]
    elif ruta == "/v1/cuadros/exportaciones":
        exigencias = [("depto", "impo" if q.get("flujo") == "impo" else "expo", q.get("departamento", ""))]
    elif ruta in ("/v1/cuadros/hidrocarburos", "/v1/cuadros/hidrocarburos/empresas", "/v1/cuadros/hidrocarburos/exportaciones"):
        exigencias = [depto_ok_o_todos("hidro", q.get("departamento", ""))]
    elif ruta == "/v1/hidrocarburos/mapa":
        exigencias = [("todos", "hidro")]
    elif ruta == "/v1/cuadros/manufactura":
        exigencias = [("depto", "manu", q.get("departamento", ""))]
    elif ruta == "/v1/cuadros/empleo":
        exigencias = [("depto", "empleo", q.get("departamento", ""))]
    elif ruta in ("/v1/empleo/totales", "/v1/empleo/sectores"):
        exigencias = [("tab", "tres", "empleo")]
    elif ruta == "/v1/descargas/empleo":
        regiones = _lista(q.get("regiones", "todas"))
        if not regiones or regiones[0].lower() == "todas":
            exigencias = [("tab", "tres", "empleo")]
        else:
            from . import empleo
            for r in regiones:
                nombre = empleo.region_de(r)
                d = DEPTO_DE_NOMBRE.get((nombre or r).lower().replace("í", "i").replace("á", "a"))
                exigencias.append(("depto", "empleo", d) if d else ("tab", "tres", "empleo"))
    elif ruta in ("/v1/mef/archivos", "/v1/mef/archivos/control"):
        exigencias = [("tab", "tres", "mef")]
    elif ruta == "/v1/hidrologia":
        if not (_tiene(perm, "tres", "hidro-peru") or any(_tiene(perm, t, "hidrologia") for t in ("lor", "smn", "uca"))):
            return no
    elif ruta == "/v1/hidrologia/estaciones":
        d = q.get("departamento", "")
        exigencias = [("tab", "tres", "hidro-peru")] if d == "todos" else [("depto", "hidrologia", d)]
    elif ruta in ("/v1/hidrologia/serie", "/v1/hidrologia/anios", "/v1/hidrologia/rango"):
        permitidas = _estaciones_permitidas(perm)
        if permitidas is not None and q.get("estacion") not in permitidas:
            return no
    elif ruta == "/v1/hidrologia/descargar":
        d = q.get("departamento", "")
        exigencias = [("tab", "tres", "hidro-peru")] if not d else [("depto", "hidrologia", d)]
    else:
        return no                                                # todo lo demás: negado
    for e in exigencias:
        if e[0] == "depto" and not depto_ok(perm, e[1], e[2]):
            return no
        if e[0] == "todos" and not cualquier_region(perm, e[1]):
            return no
        if e[0] == "tab" and not _tiene(perm, e[1], e[2]):
            return no
    return ok
