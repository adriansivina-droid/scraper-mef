"""Conexión a la base de datos (Postgres en Railway; SQLite en local) y lecturas por base."""
import base64
import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import create_engine, event, exc, inspect, text

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
# Tope de cada consulta en el servidor de la página (segundos; main.py lo fija al arrancar). Los scrapers de GitHub usan
# este mismo módulo sin tope: sus cargas y mantenimientos pueden tardar más.
TOPE_CONSULTA_S = None


def _opciones(url):
    """Que una caída de Neon o de la red no deje hilos esperando para siempre: sin estos topes, unas pocas consultas
    colgadas agotaban los hilos del servidor y la página entera dejaba de responder."""
    if not url.startswith("postgresql"):
        return {}
    return {"connect_args": {"connect_timeout": 15},       # Neon despierta en 1-5 s; 15 s = la base no está
            "pool_timeout": 20,                            # esperar una conexión libre del pool, a lo más 20 s
            "pool_recycle": 280}                           # Neon cierra las conexiones inactivas a los 5 min


_candado = threading.Lock()
_creadas = set()


def motor():
    global _motor
    if _motor is not None:
        return _motor
    with _candado:                                  # dos peticiones simultáneas al arrancar no crean dos motores
        if _motor is None:
            _motor = _nuevo_motor()
    return _motor


def _nuevo_motor():
    url = url_base_datos()
    m = create_engine(url, pool_pre_ping=True, **_opciones(url))
    if TOPE_CONSULTA_S and m.dialect.name == "postgresql":
        @event.listens_for(m, "connect")
        def _tope(conexion, _registro):
            try:
                with conexion.cursor() as cur:
                    cur.execute(f"SET statement_timeout = {int(TOPE_CONSULTA_S * 1000)}")
                conexion.commit()
            except Exception:          # un pooler que no acepte SET no debe tumbar la conexión: se sigue sin tope
                conexion.rollback()
    _crear(m, "CREATE TABLE IF NOT EXISTS cargas (id INTEGER PRIMARY KEY, fecha TEXT, origen TEXT, resumen TEXT)"
           if m.dialect.name == "sqlite" else "CREATE TABLE IF NOT EXISTS cargas (id SERIAL PRIMARY KEY, fecha TEXT, origen TEXT, resumen TEXT)")
    return m


def _crear(m, sentencia):
    """Un CREATE TABLE IF NOT EXISTS que aguanta la carrera: en Postgres, dos conexiones que crean la misma tabla en el
    mismo instante chocan (UniqueViolation en pg_type) y una petición devolvía error 500."""
    try:
        with m.begin() as cx:
            cx.execute(text(sentencia))
    except (exc.IntegrityError, exc.ProgrammingError):
        nombre = re.search(r"CREATE TABLE IF NOT EXISTS\s+\"?(\w+)", sentencia, re.I).group(1)
        if not inspect(m).has_table(nombre):
            raise


def crear_tablas(*sentencias):
    """Crea las tablas auxiliares una sola vez por proceso (antes, cada lectura de un documento, del IPC o del avance
    abría una transacción de escritura solo para el CREATE TABLE IF NOT EXISTS)."""
    if all(x in _creadas for x in sentencias):
        return
    m = motor()
    with _candado:
        for x in sentencias:
            if x not in _creadas:
                _crear(m, x)
                _creadas.add(x)


def vaciar(cx, tabla):
    """Borra todas las filas de una tabla dentro de la transacción «cx». En Postgres con TRUNCATE, que devuelve el espacio
    al instante: DELETE deja filas muertas y, tras varias reescrituras completas, la tabla ocupaba el doble en Neon."""
    if cx.dialect.name == "postgresql":
        cx.execute(text(f'TRUNCATE TABLE "{tabla}"'))
    else:
        cx.execute(text(f'DELETE FROM "{tabla}"'))


def reiniciar_motor():
    """Para las pruebas: vuelve a leer DATABASE_URL."""
    global _motor
    _motor = None
    _creadas.clear()


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
            # un solo DELETE por cada 400 claves (antes, uno por clave: cada uno recorría la tabla entera)
            claves = [(int(a), int(m), str(d), str(n)) for a, m, d, n in df[INTERNAS].drop_duplicates().itertuples(index=False)]
            for i in range(0, len(claves), 400):
                lote, params = claves[i:i + 400], {}
                for j, (a, m, d, n) in enumerate(lote):
                    params.update({f"a{j}": a, f"m{j}": m, f"d{j}": d, f"n{j}": n})
                valores = ", ".join(f"(:a{j}, :m{j}, :d{j}, :n{j})" for j in range(len(lote)))
                cx.execute(text(f'DELETE FROM "{b.tabla}" WHERE (_anio, _mes, _depto, _nivel) IN (VALUES {valores})'), params)
        df[b.columnas + INTERNAS].to_sql(b.tabla, cx, if_exists="append", index=False, chunksize=5000)
    return len(df)


def _filtro(b, deptos, niveles, desde, hasta):
    """(WHERE, parámetros) de una base por departamento, nivel y periodo; None si no puede haber filas."""
    if not deptos or (b.usa_niveles and not niveles):
        return None
    params = {f"d{i}": d for i, d in enumerate(deptos)}
    filtro = [f"_depto IN ({', '.join(':' + k for k in params)})"]
    if b.usa_niveles:
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
    return " AND ".join(filtro), params


def _orden(b):
    return ["_anio", "_mes", "_depto", "_nivel"] + [c for c in b.columnas if c not in ("AÑO", "MES", b.valor)]


def leer(base_id, deptos, niveles, desde, hasta):
    """Filas de una base filtradas por departamento, nivel (códigos E/R/M) y periodo (AAAA-MM), en el orden de las hojas."""
    b = BASES[base_id]
    f = _filtro(b, deptos, niveles, desde, hasta)
    if f is None or not existe(b.tabla):
        return pd.DataFrame(columns=b.columnas)
    with motor().connect() as cx:
        df = _completar(pd.read_sql(text(f'SELECT * FROM "{b.tabla}" WHERE {f[0]}'), cx, params=f[1]), b)
    orden = _orden(b)
    df = df.sort_values(orden, ascending=[False, True] + [True] * (len(orden) - 2), kind="stable")
    return df[b.columnas].reset_index(drop=True)


def muestra(base_id, deptos, niveles, desde, hasta, filas):
    """(número de filas, las primeras «filas» en el orden de las hojas), contadas y cortadas en la base de datos: la
    vista previa de descargas antes leía la base entera (cientos de miles de filas) para mostrar 8, en cada cambio de filtro."""
    b = BASES[base_id]
    f = _filtro(b, deptos, niveles, desde, hasta)
    if f is None or not existe(b.tabla):
        return 0, pd.DataFrame(columns=b.columnas)
    with motor().connect() as cx:
        tiene = {c["name"] for c in inspect(cx).get_columns(b.tabla)}
        orden = ", ".join(f'"{c}"' + (" DESC" if i == 0 else "") for i, c in enumerate(_orden(b)) if c in tiene)
        total = cx.execute(text(f'SELECT COUNT(*) FROM "{b.tabla}" WHERE {f[0]}'), f[1]).scalar()
        df = pd.read_sql(text(f'SELECT * FROM "{b.tabla}" WHERE {f[0]} ORDER BY {orden} LIMIT {int(filas)}'), cx, params=f[1])
    return int(total or 0), _completar(df, b)[b.columnas]


def filas_guardadas(base_id, depto, anio, meses):
    """Filas tal como están en la tabla (con sus columnas internas) de un departamento, año y meses."""
    b = BASES[base_id]
    if not meses or not existe(b.tabla):
        return pd.DataFrame(columns=b.columnas + INTERNAS)
    params = {"d": depto, "a": int(anio), **{f"m{i}": int(m) for i, m in enumerate(meses)}}
    with motor().connect() as cx:
        df = pd.read_sql(text(f'SELECT * FROM "{b.tabla}" WHERE _depto = :d AND _anio = :a AND _mes IN '
                              f'({", ".join(":m" + str(i) for i in range(len(meses)))})'), cx, params=params)
    return df[[c for c in b.columnas + INTERNAS if c in df.columns]]


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
    """Por base: departamentos cargados, primer y último periodo y número de filas. Una consulta por base (la página la
    pide cada vez que se abre)."""
    salida = {}
    m = motor()
    tablas = set(inspect(m).get_table_names())
    with m.connect() as cx:
        for b in BASES.values():
            if b.tabla not in tablas:
                salida[b.id] = {"filas": 0, "departamentos": [], "desde": None, "hasta": None}
                continue
            filas = cx.execute(text(f'SELECT _depto, COUNT(*), MIN(_anio * 100 + _mes), MAX(_anio * 100 + _mes) FROM "{b.tabla}" '
                                    f'GROUP BY _depto ORDER BY _depto')).all()
            periodo = (lambda p: None if p is None else (str(p // 100) if b.periodicidad == "anual" else f"{p // 100}-{p % 100:02d}"))
            salida[b.id] = {"filas": int(sum(f[1] for f in filas)), "departamentos": [f[0] for f in filas],
                            "desde": periodo(min((f[2] for f in filas), default=None)), "hasta": periodo(max((f[3] for f in filas), default=None))}
    return salida


def registrar_carga(origen, resumen):
    with motor().begin() as cx:
        cx.execute(text("INSERT INTO cargas (fecha, origen, resumen) VALUES (:f, :o, :r)"),
                   {"f": datetime.now(timezone.utc).isoformat(timespec="seconds"), "o": origen, "r": json.dumps(resumen, ensure_ascii=False)})


def ultima_carga():
    with motor().connect() as cx:
        r = cx.execute(text("SELECT fecha, origen, resumen FROM cargas ORDER BY id DESC LIMIT 1")).first()
    return None if r is None else {"fecha": r[0], "origen": r[1], "resumen": json.loads(r[2])}


# ── Avance de los scrapers en GitHub (barra de carga de la página): una fila por corrida y tramo ──
def _progreso():
    crear_tablas("CREATE TABLE IF NOT EXISTS progreso (corrida TEXT, tramo INTEGER, fraccion REAL, texto TEXT, fecha TEXT, "
                 "PRIMARY KEY (corrida, tramo))")


def guardar_progreso(corrida, tramo, fraccion, texto):
    _progreso()
    ahora = datetime.now(timezone.utc)
    with motor().begin() as cx:
        cx.execute(text("DELETE FROM progreso WHERE (corrida = :c AND tramo = :t) OR fecha < :viejo"),
                   {"c": str(corrida), "t": int(tramo), "viejo": (ahora - timedelta(days=7)).isoformat(timespec="seconds")})
        cx.execute(text("INSERT INTO progreso (corrida, tramo, fraccion, texto, fecha) VALUES (:c, :t, :x, :tx, :f)"),
                   {"c": str(corrida), "t": int(tramo), "x": float(fraccion), "tx": texto[:200], "f": ahora.isoformat(timespec="seconds")})


def progreso(corridas):
    """{corrida: [{tramo, fraccion, texto, fecha}]} de las corridas pedidas."""
    corridas = [str(c) for c in corridas]
    if not corridas:
        return {}
    _progreso()
    params = {f"c{i}": c for i, c in enumerate(corridas)}
    with motor().connect() as cx:
        filas = cx.execute(text(f"SELECT corrida, tramo, fraccion, texto, fecha FROM progreso WHERE corrida IN "
                                f"({', '.join(':' + k for k in params)}) ORDER BY tramo"), params).all()
    salida = {}
    for c, t, x, tx, f in filas:
        salida.setdefault(c, []).append({"tramo": t, "fraccion": x, "texto": tx, "fecha": f})
    return salida


# ── Documentos (p. ej. el mapa de lotes de hidrocarburos): un archivo por nombre ──
def _documentos():
    crear_tablas("CREATE TABLE IF NOT EXISTS documentos (nombre TEXT PRIMARY KEY, contenido TEXT, modificado TEXT, fecha TEXT)")


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
