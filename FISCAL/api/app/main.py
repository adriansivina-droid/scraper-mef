"""Departamento de estudios BCRP-IQT: API para descargar las bases de los scrapers del MEF y de pesca (DIREPRO). Corre con `uvicorn app.main:app`."""
import json
import os
import re
import secrets
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from . import archivos, carga, db, drive
from .catalogo import BASES, DEPARTAMENTOS, GRUPOS, NIVELES

app = FastAPI(title="Departamento de estudios BCRP-IQT", version="1.0", docs_url="/docs", redoc_url=None)
_basic = HTTPBasic(auto_error=False)
ESTATICOS = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")   # solo estilos: los datos siempre piden clave
_RE_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_CARGA_MB = 200


def acceso(cred: HTTPBasicCredentials | None = Depends(_basic)):
    """Usuario y contraseña del equipo (variables APP_USUARIO y APP_CLAVE). Sin APP_CLAVE no se pide nada (uso local)."""
    clave = os.environ.get("APP_CLAVE")
    if not clave:
        return
    usuario = os.environ.get("APP_USUARIO", "fiscal")
    if cred is None or not (secrets.compare_digest(cred.username, usuario) and secrets.compare_digest(cred.password, clave)):
        raise HTTPException(401, "Usuario o contraseña incorrectos.", headers={"WWW-Authenticate": 'Basic realm="Departamento de estudios BCRP-IQT"'})


def _lista(valor, validos, nombre):
    elegidos = [v for v in (valor or "").split(",") if v]
    malos = [v for v in elegidos if v not in validos]
    if malos:
        raise HTTPException(422, f"{nombre} no válido: {', '.join(malos)}.")
    return elegidos


def _filtros(base, departamento, nivel, desde, hasta):
    bases = _lista(base, BASES, "base")
    deptos = _lista(departamento, DEPARTAMENTOS, "departamento")
    niveles = [NIVELES[n] for n in _lista(nivel, NIVELES, "nivel")]
    if not bases:
        raise HTTPException(422, "Marca al menos una base.")
    if not deptos:
        raise HTTPException(422, "Marca al menos un departamento.")
    if any(BASES[b].usa_niveles for b in bases) and not niveles:
        raise HTTPException(422, "Marca al menos un nivel de gobierno.")
    for p in (desde, hasta):
        if not _RE_PERIODO.match(p or ""):
            raise HTTPException(422, f"Periodo no válido: {p!r} (formato AAAA-MM).")
    if desde > hasta:
        raise HTTPException(422, f"El periodo está al revés: desde={desde} es posterior a hasta={hasta}.")
    orden = [b for b in BASES if b in bases]              # las hojas salen siempre en el orden del catálogo
    return orden, deptos, niveles


def _registros(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))


def _tablas(bases, deptos, niveles, desde, hasta):
    return {b: db.leer(b, deptos, niveles, desde, hasta) for b in bases}


def _avisos(bases, deptos):
    disp, avisos = db.disponibilidad(), []
    for b in bases:
        propios = [d for d in deptos if not BASES[b].departamentos or d in BASES[b].departamentos]
        if not propios:
            avisos.append(f"{BASES[b].nombre}: solo tiene datos de {', '.join(DEPARTAMENTOS[d].title() for d in BASES[b].departamentos)}.")
            continue
        sin = [d for d in propios if d not in disp[b]["departamentos"]]
        if sin:
            nombres = f"{len(sin)} departamentos" if len(sin) > 6 else ", ".join(DEPARTAMENTOS[d].title() for d in sin)
            avisos.append(f"{BASES[b].nombre}: sin datos para {nombres}.")
    return avisos


def _prefijo(bases):
    grupos = {BASES[b].grupo for b in bases}
    return "bases_pesca" if grupos == {"pesca"} else "bases_fiscal" if "pesca" not in grupos else "bases"


def _sufijo(deptos):
    return "todos" if len(deptos) >= 25 else "-".join(deptos)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/salud", include_in_schema=False)
def salud():
    return {"ok": True}


@app.get("/", include_in_schema=False, dependencies=[Depends(acceso)])
def inicio():
    return FileResponse(ESTATICOS / "index.html")


@app.get("/v1/catalogo", dependencies=[Depends(acceso)])
def catalogo():
    return {"grupos": GRUPOS,
            "bases": [{"id": b.id, "grupo": b.grupo, "etiqueta": b.etiqueta, "nombre": b.nombre, "hoja": b.hoja,
                       "columnas": b.columnas, "anchos": b.anchos, "valor": b.valor, "periodicidad": b.periodicidad,
                       "usa_niveles": b.usa_niveles, "descripcion": b.descripcion, "departamentos": list(b.departamentos)}
                      for b in BASES.values()],
            "departamentos": [{"codigo": c, "nombre": n} for c, n in DEPARTAMENTOS.items()],
            "niveles": list(NIVELES)}


@app.get("/v1/estado", dependencies=[Depends(acceso)])
def estado():
    return {"bases": db.disponibilidad(), "ultima_carga": db.ultima_carga()}


@app.get("/v1/descargas/vista-previa", dependencies=[Depends(acceso)])
def vista_previa(base: str = "", departamento: str = "", nivel: str = "", desde: str = "", hasta: str = "", filas: int = Query(12, le=100)):
    bases, deptos, niveles = _filtros(base, departamento, nivel, desde, hasta)
    tablas = _tablas(bases, deptos, niveles, desde, hasta)
    return {"archivos": [{"base": b, "hoja": BASES[b].hoja, "filas": len(df), "columnas": BASES[b].columnas,
                          "muestra": _registros(df.head(filas))} for b, df in tablas.items()],
            "filas_total": sum(len(df) for df in tablas.values()),
            "descarga": f"{_prefijo(bases)}_{desde}_{hasta}.xlsx", "avisos": _avisos(bases, deptos)}


@app.get("/v1/descargas", dependencies=[Depends(acceso)])
def descargas(base: str = "", departamento: str = "", nivel: str = "", desde: str = "", hasta: str = "",
              formato: str = Query("xlsx", pattern="^(xlsx|csv|json)$"), pagina: int = Query(1, ge=1), tamano: int = Query(1000, ge=1, le=10000)):
    bases, deptos, niveles = _filtros(base, departamento, nivel, desde, hasta)
    tablas = _tablas(bases, deptos, niveles, desde, hasta)
    if formato == "json":
        ini = (pagina - 1) * tamano
        return JSONResponse({b: {"filas": len(df), "pagina": pagina, "datos": _registros(df.iloc[ini:ini + tamano])}
                             for b, df in tablas.items()})
    if formato == "xlsx":
        nombre = f"{_prefijo(bases)}_{desde}_{hasta}.xlsx"
        contenido, tipo = archivos.excel(tablas), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif len(tablas) == 1:
        b = bases[0]
        nombre, contenido, tipo = f"{BASES[b].hoja} {desde}_{hasta} - {_sufijo(deptos)}.csv", archivos.csv(tablas[b]), "text/csv"
    else:
        nombre = f"{_prefijo(bases)}_{desde}_{hasta}.zip"
        contenido = archivos.zip_csv(tablas, lambda b: f"{BASES[b].hoja} {desde}_{hasta} - {_sufijo(deptos)}.csv")
        tipo = "application/zip"
    return Response(contenido, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@app.post("/v1/cargas", dependencies=[Depends(acceso)])
async def cargas(archivos_subidos: list[UploadFile] = File(..., alias="archivos")):
    """Carga los CSV del scraper (sueltos o la carpeta Scrapeo/output en un .zip), PIM_Funcion.xlsx o los Excel de pesca."""
    contenido, total = [], 0
    for a in archivos_subidos:
        datos = await a.read()
        total += len(datos)
        if total > MAX_CARGA_MB * 1024 * 1024:
            raise HTTPException(413, f"Lo subido pasa de {MAX_CARGA_MB} MB.")
        contenido.append((a.filename or "archivo", datos))
    return carga.cargar(f"subida del {date.today().isoformat()}: {', '.join(n for n, _ in contenido)[:200]}", contenido)


@app.get("/v1/drive", dependencies=[Depends(acceso)])
def drive_estado():
    """Si la sincronización con Drive está configurada, sus carpetas y la última sincronización."""
    return {"configurado": drive.configurado(), "carpetas": drive.CARPETAS, "ultima": drive.ultima()}


@app.post("/v1/drive/sincronizar", dependencies=[Depends(acceso)])
def drive_sincronizar(todo: bool = False, origen: str = Query("botón de la página", max_length=60)):
    """Carga los Excel nuevos o modificados de las carpetas de crudos de pesca en Drive (todos, con todo=true)."""
    if not drive.configurado():
        raise HTTPException(503, "Falta la credencial de Drive (variable GOOGLE_DRIVE_CREDENCIAL en Render).")
    try:
        return drive.sincronizar(origen=origen, todo=todo)
    except drive.SincronizacionEnCurso as e:
        raise HTTPException(409, str(e))
    except Exception as e:                       # credencial vencida, carpeta sin permiso, Drive caído…
        raise HTTPException(502, f"No se pudo leer Drive: {e}")
