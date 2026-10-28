"""Conexión a la base de datos (Postgres en Railway; SQLite en local) y lecturas por base."""
import base64
import json
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from .catalogo import BASES, INTERNAS


def url_base_datos():
    url = os.environ.get("DATABASE_URL", "sqlite:///fiscal_local.db")
    # Railway entrega postgresql://…; SQLAlchemy necesita el driver explícito
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_motor = None


def motor():
    global _motor
    if _motor is None:
        _motor = create_engine(url_base_datos(), pool_pre_ping=True)
        with _motor.begin() as cx:
            cx.execute(text("CREATE TABLE IF NOT EXISTS cargas (id INTEGER PRIMARY KEY, fecha TEXT, origen TEXT, resumen TEXT)"
                            if _motor.dialect.name == "sqlite" else
                            "CREATE TABLE IF NOT EXISTS cargas (id SERIAL PRIMARY KEY, fecha TEXT, origen TEXT, resumen TEXT)"))
    return _motor


def reiniciar_motor():
    """Para las pruebas: vuelve a leer DATABASE_URL."""
    global _motor
    _motor = None


def existe(tabla):
    return inspect(motor()).has_table(tabla)


def guardar(base_id, df):
    """Reemplaza en la tabla las filas de los mismos periodos, departamentos y niveles que trae df (recargar no duplica)."""
    b = BASES[base_id]
    if df.empty:
        return 0
    m = motor()
    with m.begin() as cx:
        if existe(b.tabla):                            # una columna nueva del catálogo se agrega a la tabla existente
            tiene = {c["name"] for c in inspect(cx).get_columns(b.tabla)}
            for col in b.columnas:
                if col not in tiene:
                    tipo = "DOUBLE PRECISION" if pd.api.types.is_numeric_dtype(df[col]) else "TEXT"
                    cx.execute(text(f'ALTER TABLE "{b.tabla}" ADD COLUMN "{col}" {tipo}'))
        if existe(b.tabla) and b.reemplaza_periodo:
            # la serie completa: se borra el tramo de periodos que trae, en todos los departamentos (un lote puede
            # cambiar de departamento cuando se cruza con el mapa)
            for nivel, g in df.groupby("_nivel"):
                p = g["_anio"] * 100 + g["_mes"]
                cx.execute(text(f'DELETE FROM "{b.tabla}" WHERE _nivel = :n AND (_anio * 100 + _mes) BETWEEN :p0 AND :p1'),
                           {"n": nivel, "p0": int(p.min()), "p1": int(p.max())})
        elif existe(b.tabla):
            claves = df[INTERNAS].drop_duplicates().itertuples(index=False)
            for anio, mes, depto, nivel in claves:
                cx.execute(text(f'DELETE FROM "{b.tabla}" WHERE _anio = :a AND _mes = :m AND _depto = :d AND _nivel = :n'),
                           {"a": int(anio), "m": int(mes), "d": depto, "n": nivel})
        df[b.columnas + INTERNAS].to_sql(b.tabla, cx, if_exists="append", index=False, chunksize=5000)
    return len(df)


def leer(base_id, deptos, niveles, desde, hasta):
    """Filas de una base filtradas por departamento, nivel (códigos E/R/M) y periodo (AAAA-MM), en el orden de las hojas."""
    b = BASES[base_id]
    if not existe(b.tabla) or not deptos:
        return pd.DataFrame(columns=b.columnas)
    params = {f"d{i}": d for i, d in enumerate(deptos)}
    filtro = [f"_depto IN ({', '.join(':' + k for k in params)})"]
    if b.usa_niveles:
        if not niveles:
            return pd.DataFrame(columns=b.columnas)
        params.update({f"n{i}": n for i, n in enumerate(niveles)})
        filtro.append(f"_nivel IN ({', '.join(':n' + str(i) for i in range(len(niveles)))})")
    a0, m0 = int(desde[:4]), int(desde[5:7])
    a1, m1 = int(hasta[:4]), int(hasta[5:7])
    if b.periodicidad == "anual":
        filtro.append("_anio BETWEEN :a0 AND :a1")
        params.update(a0=a0, a1=a1)
    else:
        filtro.append("(_anio * 100 + _mes) BETWEEN :p0 AND :p1")
        params.update(p0=a0 * 100 + m0, p1=a1 * 100 + m1)
    with motor().connect() as cx:
        df = _completar(pd.read_sql(text(f'SELECT * FROM "{b.tabla}" WHERE {" AND ".join(filtro)}'), cx, params=params), b)
    orden = ["_anio", "_mes", "_depto", "_nivel"] + [c for c in b.columnas if c not in ("AÑO", "MES", b.valor)]
    df = df.sort_values(orden, ascending=[False, True] + [True] * (len(orden) - 2), kind="stable")
    return df[b.columnas].reset_index(drop=True)


def leer_todo(base_id):
    """Todas las filas de una base, sin columnas internas (None si está vacía)."""
    b = BASES[base_id]
    if not existe(b.tabla):
        return None
    with motor().connect() as cx:
        return _completar(pd.read_sql(text(f'SELECT * FROM "{b.tabla}"'), cx), b)[b.columnas]


def _completar(df, b):
    """Una columna que el catálogo agregó después de crear la tabla (se crea en la próxima carga) sale vacía."""
    for c in b.columnas:
        if c not in df.columns:
            df[c] = None
    return df


def disponibilidad():
    """Por base: departamentos cargados, primer y último periodo y número de filas."""
    salida = {}
    with motor().connect() as cx:
        for b in BASES.values():
            if not existe(b.tabla):
                salida[b.id] = {"filas": 0, "departamentos": [], "desde": None, "hasta": None}
                continue
            r = cx.execute(text(f'SELECT COUNT(*), MIN(_anio * 100 + _mes), MAX(_anio * 100 + _mes) FROM "{b.tabla}"')).one()
            deptos = [d for (d,) in cx.execute(text(f'SELECT DISTINCT _depto FROM "{b.tabla}" ORDER BY _depto'))]
            periodo = (lambda p: None if p is None else (str(p // 100) if b.periodicidad == "anual" else f"{p // 100}-{p % 100:02d}"))
            salida[b.id] = {"filas": int(r[0]), "departamentos": deptos, "desde": periodo(r[1]), "hasta": periodo(r[2])}
    return salida


def registrar_carga(origen, resumen):
    with motor().begin() as cx:
        cx.execute(text("INSERT INTO cargas (fecha, origen, resumen) VALUES (:f, :o, :r)"),
                   {"f": datetime.now(timezone.utc).isoformat(timespec="seconds"), "o": origen, "r": json.dumps(resumen, ensure_ascii=False)})


def ultima_carga():
    with motor().connect() as cx:
        r = cx.execute(text("SELECT fecha, origen, resumen FROM cargas ORDER BY id DESC LIMIT 1")).first()
    return None if r is None else {"fecha": r[0], "origen": r[1], "resumen": json.loads(r[2])}


# ── Documentos (p. ej. el mapa de lotes de hidrocarburos): un archivo por nombre ──
def _documentos():
    with motor().begin() as cx:
        cx.execute(text("CREATE TABLE IF NOT EXISTS documentos (nombre TEXT PRIMARY KEY, contenido TEXT, modificado TEXT, fecha TEXT)"))


def guardar_documento(nombre, contenido, modificado):
    _documentos()
    with motor().begin() as cx:
        cx.execute(text("DELETE FROM documentos WHERE nombre = :n"), {"n": nombre})
        cx.execute(text("INSERT INTO documentos (nombre, contenido, modificado, fecha) VALUES (:n, :c, :m, :f)"),
                   {"n": nombre, "c": contenido, "m": modificado, "f": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def documento(nombre):
    """(contenido, modificado) o None."""
    _documentos()
    with motor().connect() as cx:
        r = cx.execute(text("SELECT contenido, modificado FROM documentos WHERE nombre = :n"), {"n": nombre}).first()
    return None if r is None else (r[0], r[1])


# ── Archivos generados por los notebooks (Excel del procesamiento fiscal, variaciones, proyectos) ──
# Se guardan como documentos «archivo:<carpeta>/<nombre>» con el contenido en base64.
def guardar_archivo(carpeta, nombre, contenido):
    guardar_documento(f"archivo:{carpeta}/{nombre}", base64.b64encode(contenido).decode("ascii"),
                      datetime.now(timezone.utc).isoformat(timespec="seconds"))


def archivos(carpeta):
    """[{nombre, fecha, kb}] de una carpeta, el más reciente primero."""
    _documentos()
    prefijo = f"archivo:{carpeta}/"
    with motor().connect() as cx:
        filas = cx.execute(text("SELECT nombre, modificado, LENGTH(contenido) FROM documentos WHERE nombre LIKE :p"),
                           {"p": prefijo + "%"}).all()
    salida = [{"nombre": n[len(prefijo):], "fecha": m, "kb": round(int(t or 0) * 3 / 4 / 1024)} for n, m, t in filas]
    return sorted(salida, key=lambda x: (x["fecha"] or "", x["nombre"]), reverse=True)


def archivo(carpeta, nombre):
    """bytes o None."""
    doc = documento(f"archivo:{carpeta}/{nombre}")
    return None if doc is None else base64.b64decode(doc[0])
