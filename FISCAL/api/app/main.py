"""Departamento de estudios BCRP-IQT: API para descargar las bases de los scrapers del MEF y de pesca (DIREPRO). Corre con `uvicorn app.main:app`."""
import io
import json
import os
import re
import secrets
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from . import archivos, carga, db, drive, empleo, hidrocarburos, mef
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


def _adjunto(nombre):
    """Encabezado de descarga; los nombres con tildes («San Martín») van también en UTF-8 (RFC 5987)."""
    plano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return {"Content-Disposition": f"attachment; filename=\"{plano}\"; filename*=UTF-8''{quote(nombre)}"}


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
    sectores = {{"inversion": "fiscal", "gasto": "fiscal"}.get(BASES[b].grupo, BASES[b].grupo) for b in bases}
    return f"bases_{sectores.pop()}" if len(sectores) == 1 else "bases"


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
    # la hoja de estilos lleva su fecha de modificación: tras cada despliegue el navegador baja la nueva y no mezcla la
    # página nueva con estilos viejos guardados en caché
    version = int((ESTATICOS / "estilo.css").stat().st_mtime)
    html = (ESTATICOS / "index.html").read_text(encoding="utf-8").replace('href="/static/estilo.css"', f'href="/static/estilo.css?v={version}"')
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


@app.get("/v1/catalogo", dependencies=[Depends(acceso)])
def catalogo():
    return {"grupos": GRUPOS,
            "bases": [{"id": b.id, "grupo": b.grupo, "etiqueta": b.etiqueta, "nombre": b.nombre, "hoja": b.hoja,
                       "columnas": b.columnas, "anchos": b.anchos, "valor": b.valor, "periodicidad": b.periodicidad,
                       "usa_niveles": b.usa_niveles, "descripcion": b.descripcion, "departamentos": list(b.departamentos)}
                      for b in BASES.values()],
            "departamentos": [{"codigo": c, "nombre": n} for c, n in DEPARTAMENTOS.items()],
            "niveles": list(NIVELES),
            "empleo": {"regiones": empleo.REGIONES, "grupos": empleo.GRUPOS_REGIONES}}


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
    return Response(contenido, media_type=tipo, headers=_adjunto(nombre))


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
    """Carga los archivos nuevos o modificados de Drive: crudos de pesca y CSV de hidrocarburos (todos, con todo=true)."""
    if not drive.configurado():
        raise HTTPException(503, "Falta la credencial de Drive (variable GOOGLE_DRIVE_CREDENCIAL en Render).")
    try:
        return drive.sincronizar(origen=origen, todo=todo)
    except drive.SincronizacionEnCurso as e:
        raise HTTPException(409, str(e))
    except Exception as e:                       # credencial vencida, carpeta sin permiso, Drive caído…
        raise HTTPException(502, f"No se pudo leer Drive: {e}")


@app.get("/v1/mef", dependencies=[Depends(acceso)])
def mef_estado():
    """Si el botón «Actualizar desde el MEF» está configurado y las últimas corridas del scraper en GitHub."""
    if not mef.configurado():
        return {"configurado": False, "corridas": []}
    try:
        return {"configurado": True, "corridas": mef.corridas()}
    except (mef.ErrorGitHub, OSError) as e:
        return {"configurado": True, "corridas": [], "error": str(e)}


@app.post("/v1/mef/actualizar", dependencies=[Depends(acceso)])
def mef_actualizar(desde: str = "", hasta: str = "", prueba: bool = False):
    """Lanza el scraper del MEF en GitHub Actions; al terminar (unos minutos) carga los datos en la base."""
    if not mef.configurado():
        raise HTTPException(503, "Falta el token de GitHub (variable GITHUB_ACCIONES_TOKEN en Render).")
    try:
        mef.lanzar(desde, hasta, prueba)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except (mef.ErrorGitHub, OSError) as e:
        raise HTTPException(502, str(e))
    return {"lanzado": True, "desde": desde or None, "hasta": hasta or None, "prueba": prueba}


@app.get("/v1/empleo", dependencies=[Depends(acceso)])
def empleo_estado():
    """Si el botón «Actualizar empleo» está configurado y las últimas corridas del scraper de empleo en GitHub."""
    if not mef.configurado():
        return {"configurado": False, "corridas": []}
    try:
        return {"configurado": True, "corridas": mef.corridas(nombre="empleo")}
    except (mef.ErrorGitHub, OSError) as e:
        return {"configurado": True, "corridas": [], "error": str(e)}


@app.post("/v1/empleo/actualizar", dependencies=[Depends(acceso)])
def empleo_actualizar(regiones: str = Query("LOR,SMN,UCA", pattern="^(LOR,SMN,UCA|TODAS)$")):
    """Lanza el scraper de empleo (Power BI del MTPE) en GitHub Actions; al terminar carga los datos en la base."""
    if not mef.configurado():
        raise HTTPException(503, "Falta el token de GitHub (variable GITHUB_ACCIONES_TOKEN en Render).")
    try:
        mef.lanzar(nombre="empleo", inputs={"regiones": regiones})
    except (mef.ErrorGitHub, OSError) as e:
        raise HTTPException(502, str(e))
    return {"lanzado": True, "regiones": regiones}


@app.get("/v1/descargas/empleo", dependencies=[Depends(acceso)])
def descarga_empleo(regiones: str = "todas", desde: str = "", hasta: str = "",
                    formato: str = Query("xlsx", pattern="^(xlsx|csv|json)$"), filas: int = Query(10, ge=0, le=100)):
    """Empleo en el formato LONG del scraper (AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO), una hoja.

    regiones: nombres separados por comas (con o sin tildes: «Loreto,San Martin,Lima Metropolitana») o «todas».
    desde/hasta AAAA-MM opcionales (vacío = todo lo cargado). formato=json da el conteo y una muestra de `filas` filas.
    """
    if regiones.strip().lower() == "todas":
        pedidas = list(empleo.REGIONES)
    else:
        pedidas, malas = [], []
        for r in (x.strip() for x in regiones.split(",") if x.strip()):
            (pedidas.append(empleo.region_de(r)) if empleo.region_de(r) else malas.append(r))
        if malas or not pedidas:
            raise HTTPException(422, f"Región no válida: {', '.join(malas) or '(ninguna)'}. Usa los nombres de /v1/catalogo (empleo.regiones) o «todas».")
    for p in (desde, hasta):
        if p and not _RE_PERIODO.match(p):
            raise HTTPException(422, f"Periodo no válido: {p!r} (formato AAAA-MM).")
    if desde and hasta and desde > hasta:
        raise HTTPException(422, f"El periodo está al revés: desde={desde} es posterior a hasta={hasta}.")
    deptos = sorted({empleo.depto_de(r) for r in pedidas})
    df = empleo.long(db.leer("empleo", deptos, [], desde or "1990-01", hasta or "2100-12"), pedidas)
    nombre = empleo.nombre_long(pedidas)
    if formato == "json":
        con_datos, p = set(df["REGIÓN"].map(empleo.region_de)), df["AÑO"] * 100 + df["MES"]
        mes = lambda x: f"{x // 100}-{x % 100:02d}" if len(df) else None
        return {"archivo": nombre, "filas": len(df), "columnas": empleo.COLUMNAS, "muestra": _registros(df.head(filas)),
                "desde": mes(p.min()), "hasta": mes(p.max()), "sin_datos": [r for r in pedidas if r not in con_datos]}
    if formato == "csv":
        return Response(archivos.csv(df), media_type="text/csv",
                        headers=_adjunto(nombre[:-5] + ".csv"))
    buf = io.BytesIO()
    df.to_excel(buf, index=False)                      # igual que el notebook: una hoja, sin formato
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers=_adjunto(nombre))


@app.get("/v1/hidrocarburos/mapa", dependencies=[Depends(acceso)])
def mapa_hidrocarburos(descargar: bool = False):
    """El mapa de lotes de PERUPETRO (DATA/MAPA/PP_mapa_lotes_plus.html, del flujo de hidrocarburos), tal como lo arma su
    notebook; se toma de Drive en cada sincronización."""
    doc = db.documento("mapa-hidrocarburos")
    if doc is None:
        return HTMLResponse("<p style='font-family:sans-serif;color:#5A5A9E;padding:24px'>Todavía no se cargó el mapa: "
                            "sincroniza Drive (el flujo de hidrocarburos lo deja en DATA/MAPA).</p>", status_code=404)
    extra = _adjunto("Mapa de Hidrocarburos - Perú.html") if descargar else {}
    return HTMLResponse(doc[0], headers={**extra, "X-Mapa-Modificado": doc[1] or ""})


@app.get("/v1/cuadros/hidrocarburos", dependencies=[Depends(acceso)])
def cuadro_hidrocarburos(departamento: str = Query(..., pattern=r"^\d{2}$"), periodo: str = "",
                         formato: str = Query("json", pattern="^(json|xlsx)$")):
    """Producción por producto y lote (mes y acumulado contra el año anterior), promedio diario, anexo por lote y canon
    de un departamento (periodo AAAA-MM; vacío = último mes con producción)."""
    if departamento not in DEPARTAMENTOS:
        raise HTTPException(422, f"departamento no válido: {departamento}.")
    if periodo and not _RE_PERIODO.match(periodo):
        raise HTTPException(422, f"Periodo no válido: {periodo!r} (formato AAAA-MM).")
    prod = db.leer("hidro-produccion", [departamento], [], "1990-01", "2100-12")
    canon = db.leer("hidro-canon", [departamento], [], "1990-01", "2100-12")
    try:
        c = hidrocarburos.cuadros(prod, canon, periodo or None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    region = DEPARTAMENTOS[departamento].title().replace(" De ", " de ")
    if c is None:
        return {"region": region, "cuadros": None}
    if formato == "xlsx":
        return Response(hidrocarburos.excel(region, c), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers=_adjunto(f"Hidrocarburos {region} {c['periodo']}.xlsx"))
    return {"region": region, "cuadros": c}


@app.get("/v1/cuadros/empleo", dependencies=[Depends(acceso)])
def cuadro_empleo(departamento: str = Query(..., pattern=r"^\d{2}$"), periodo: str = "",
                  formato: str = Query("json", pattern="^(json|xlsx)$")):
    """Cuadro, gráfico y anexo de empleo de la síntesis de una región (periodo AAAA-MM; vacío = último mes con datos)."""
    if departamento not in DEPARTAMENTOS:
        raise HTTPException(422, f"departamento no válido: {departamento}.")
    if periodo and not _RE_PERIODO.match(periodo):
        raise HTTPException(422, f"Periodo no válido: {periodo!r} (formato AAAA-MM).")
    df = db.leer("empleo", [departamento], [], "1990-01", "2100-12")
    try:
        c = empleo.cuadros(df, periodo or None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    region = DEPARTAMENTOS[departamento].title().replace(" De ", " de ")
    if c is None:
        return {"region": region, "cuadros": None}
    if formato == "xlsx":
        nombre = f"Empleo {region} {c['periodo']}.xlsx"
        return Response(empleo.excel(region, c), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers=_adjunto(nombre))
    return {"region": region, "cuadros": c}
