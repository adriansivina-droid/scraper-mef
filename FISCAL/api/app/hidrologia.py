"""Hidrología: nivel y caudal de los ríos (SENAMHI, Monitoreo Hidrológico).

SENAMHI no responde a servidores en la nube, así que la recolección la hace el navegador (HIDROLOGIA/senamhi_navegador.js)
y entrega un archivo «SENAMHI_crudo_AAAA-MM-DD.json». La página guarda sus piezas tal cual, comprimidas, en la tabla
«senamhi_crudo» (una fila por hidrograma, por consulta de Información Diaria y por mes), y con ellas arma al vuelo los
mismos CSV que el notebook HIDROLOGIA/SENAMHI_Rios.ipynb y los datos del gráfico. Guardar las piezas y no las filas ocupa
unas 10 veces menos en la base de datos.
"""
import csv
import io
import json
import os
import re
import tempfile
import threading
import unicodedata
import zipfile
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from . import db

INICIO = date(2023, 1, 1)                      # los CSV empiezan aquí, como en el notebook
SERIES = ("datoActual", "datoAnterior", "minimo", "maximo", "promHistorico", "rojo", "naranja", "amarillo")
ZONALES = {"01": "DZ 1 · Piura", "02": "DZ 2 · Lambayeque", "03": "DZ 3 · Cajamarca", "04": "DZ 4 · Lima",
           "05": "DZ 5 · Ica", "06": "DZ 6 · Arequipa", "07": "DZ 7 · Tacna", "08": "DZ 8 · Loreto",
           "09": "DZ 9 · San Martín", "10": "DZ 10 · Huánuco", "11": "DZ 11 · Junín", "12": "DZ 12 · Cusco",
           "13": "DZ 13 · Puno"}
DEPTOS = {"16": "LORETO", "22": "SAN MARTIN", "25": "UCAYALI"}
ZONAL_DE = {"16": "08", "22": "09", "25": "10"}  # dirección zonal que atiende a cada departamento (si SENAMHI no da el departamento)
MES_EN = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10,
          "NOV": 11, "DEC": 12}
_RE_CLAVE = re.compile(r"^(meta|estaciones|zonales|infoMeta|fichas|historiaOk|graf:[^:]{1,40}:(NIVEL|CAUDAL):\d{4}"
                       r"|men:\d{4}-\d{2}|inf:\d{4}-\d{2}-\d{2}:\d{2}:\d{2})$")
ARCHIVOS = {"diario": "SENAMHI_rios_diario.csv", "info-diaria": "SENAMHI_rios_info_diaria.csv",
            "mensual": "SENAMHI_rios_mensual.csv", "estaciones": "SENAMHI_ESTACIONES.csv",
            "control": "CONTROL SENAMHI rios_diario.csv", "control-info": "CONTROL SENAMHI rios_info_diaria.csv",
            "control-mensual": "CONTROL SENAMHI rios_mensual.csv", "log": "LOG SENAMHI consultas.csv"}
COLS = {
    "diario": ["COD_ESTACION", "ESTACION", "RIO", "VARIABLE", "UNIDAD", "FECHA", "AÑO", "MES", "DIA", "AÑO_HIDROLOGICO", "VALOR",
               "MINIMO", "MAXIMO", "PROM_HISTORICO", "UMBRAL_ROJO", "UMBRAL_NARANJA", "UMBRAL_AMARILLO", "SERIE", "FECHA_EXTRACCION"],
    "info-diaria": ["COD_ESTACION", "ESTACION", "CUERPO_AGUA", "CUENCA", "DEPARTAMENTO", "ZONA", "REGION_HIDROGRAFICA", "COD_ZONAL",
                    "FECHA", "AÑO", "MES", "DIA", "HORA", "UNIDAD", "VALOR", "ANOMALIA", "UNIDAD_ANOMALIA", "TENDENCIA", "UMBRAL_ROJO",
                    "FECHA_EXTRACCION"],
    "mensual": ["AÑO", "MES", "FECHA", "COD_ESTACION", "ESTACION", "CUERPO_AGUA", "DEPARTAMENTO", "ZONA", "REGION_HIDROGRAFICA",
                "COD_ZONAL", "UNIDAD", "VALOR_MES", "VALOR_MES_ANTERIOR", "ANOMALIA", "UNIDAD_ANOMALIA", "TENDENCIA", "UMBRAL_ROJO",
                "FECHA_EXTRACCION"],
    "estaciones": ["ID_ESTACION", "COD_ESTACION", "ESTACION", "SUB_ESTACION", "ESTADO", "COD_ZONAL", "DIRECCION_ZONAL", "DEPARTAMENTO",
                   "FECHA_HORA_ULTIMA", "VARIABLE_OPCION", "RIO", "VARIABLES_CON_DATOS", "FECHA_EXTRACCION"],
    "control": ["COD_ESTACION", "ESTACION", "VARIABLE", "ESTADO", "PRIMERA_FECHA", "ULTIMA_FECHA", "DIAS_CON_DATO", "DIAS_FALTANTES",
                "SALTOS_RAROS", "LLEGA_AL_INICIO", "CRUCE_MENSUAL_DIF_MAX_%", "FECHA_EXTRACCION"],
    "control-info": ["FECHA", "HORA", "ESTACIONES", "CON_DATO", "ESTADO", "FECHA_EXTRACCION"],
    "control-mensual": ["AÑO", "MES", "SERVIDO", "ESTACIONES", "ESTADO", "FECHA_EXTRACCION"],
    "log": ["COD_ESTACION", "ESTACION", "VARIABLE", "VARIABLE_OPCION", "FECHA_HORA_PEDIDA", "INICIO_SERIE", "FILAS", "ESTADO",
            "FECHA_EXTRACCION"],
}


# ── utilidades ───────────────────────────────────────────────────────────────
def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFKD", str(t)) if not unicodedata.combining(c)).upper().strip()


def num(v):
    """Número o None (SENAMHI usa -999 para «sin dato»)."""
    if v is None or v == "":
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if v <= -999 or v != v else round(v, 4)


def _fecha_ms(ms):
    return (datetime(1970, 1, 1) + timedelta(milliseconds=int(ms))).date()


def _un_año_antes(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return None


def año_hidrologico(d):
    """De setiembre a agosto; se nombra por el año en que empieza."""
    return d.year if d.month >= 9 else d.year - 1


def _dmy(d):
    return d.strftime("%d/%m/%Y") if d else ""


def _dia_txt(iso):
    """«2026-11-12» → «12/11/2026»."""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso and len(iso) >= 10 else ""


# ── tabla de piezas crudas ───────────────────────────────────────────────────
_tabla_lista = None
_candado = threading.Lock()


def _tabla():
    global _tabla_lista
    m = db.motor()
    if _tabla_lista is m:
        return
    binario = "BYTEA" if m.dialect.name == "postgresql" else "BLOB"
    with m.begin() as cx:
        cx.execute(text(f"CREATE TABLE IF NOT EXISTS senamhi_crudo (clave TEXT PRIMARY KEY, datos {binario}, huella TEXT, "
                        "dia TEXT, actualizado TEXT)"))
    _tabla_lista = m


def indice():
    """{clave: huella} de lo guardado: el navegador lo compara con su archivo y sube solo lo que cambió."""
    _tabla()
    with db.motor().connect() as cx:
        return {c: h for c, h in cx.execute(text("SELECT clave, huella FROM senamhi_crudo")).all()}


def guardar(piezas, dia):
    """Guarda piezas [{clave, huella, valor}] recolectadas el día «dia» (AAAA-MM-DD). No pisa lo recolectado en un día
    posterior (por si se sube un archivo viejo). Devuelve cuántas guardó y cuántas dejó pasar."""
    _tabla()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", dia or ""):
        raise ValueError("Falta el día de la recolección (AAAA-MM-DD).")
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    claves = [str(p.get("clave", "")) for p in piezas]
    malas = [c for c in claves if not _RE_CLAVE.match(c)]
    if malas:
        raise ValueError(f"Pieza no reconocida: {malas[0][:60]}")
    guardadas = viejas = 0
    with db.motor().begin() as cx:
        previas = {}
        for i in range(0, len(claves), 400):
            lote = claves[i:i + 400]
            marcas = ", ".join(f":c{k}" for k in range(len(lote)))
            previas.update({c: d for c, d in cx.execute(text(f"SELECT clave, dia FROM senamhi_crudo WHERE clave IN ({marcas})"),
                                                        {f"c{k}": c for k, c in enumerate(lote)}).all()})
        for p, clave in zip(piezas, claves):
            if clave in previas and (previas[clave] or "") > dia:
                viejas += 1
                continue
            datos = zlib.compress(json.dumps(p.get("valor"), ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
            par = {"c": clave, "d": datos, "h": str(p.get("huella", ""))[:40], "dia": dia, "a": ahora}
            if clave in previas:
                cx.execute(text("UPDATE senamhi_crudo SET datos = :d, huella = :h, dia = :dia, actualizado = :a WHERE clave = :c"), par)
            else:
                cx.execute(text("INSERT INTO senamhi_crudo (clave, datos, huella, dia, actualizado) VALUES (:c, :d, :h, :dia, :a)"), par)
                previas[clave] = dia
            guardadas += 1
    return {"guardadas": guardadas, "omitidas_por_viejas": viejas}


def piezas_de_archivo(crudo):
    """El archivo «SENAMHI_crudo_….json» del navegador, partido en piezas (lo mismo que hace la página al subirlo)."""
    out = [{"clave": k, "valor": crudo[k]} for k in ("meta", "estaciones", "zonales", "infoMeta", "fichas") if crudo.get(k)]
    for g in crudo.get("graficas") or []:
        out.append({"clave": f"graf:{g['cod']}:{g['variable']}:{g['y']}", "valor": g})
    out += [{"clave": f"men:{k}", "valor": v} for k, v in (crudo.get("mensual") or {}).items()]
    out += [{"clave": f"inf:{k[:10]}:{k[11:]}", "valor": v} for k, v in (crudo.get("infoDiaria") or {}).items()]
    return out


def _leer(clave, defecto=None):
    _tabla()
    with db.motor().connect() as cx:
        r = cx.execute(text("SELECT datos FROM senamhi_crudo WHERE clave = :c"), {"c": clave}).first()
    return defecto if r is None else json.loads(zlib.decompress(bytes(r[0])))


def _piezas(prefijo):
    """(clave, valor, día de recolección) de las piezas cuyo nombre empieza con «prefijo», en orden de clave."""
    _tabla()
    with db.motor().connect() as cx:
        claves = sorted((c for (c,) in cx.execute(text("SELECT clave FROM senamhi_crudo WHERE clave LIKE :p"),
                                                  {"p": prefijo + "%"}).all()), key=lambda c: c.split(":"))
        for i in range(0, len(claves), 200):
            lote = claves[i:i + 200]
            marcas = ", ".join(f":c{k}" for k in range(len(lote)))
            filas = {c: (d, dia) for c, d, dia in cx.execute(
                text(f"SELECT clave, datos, dia FROM senamhi_crudo WHERE clave IN ({marcas})"), {f"c{k}": c for k, c in enumerate(lote)}).all()}
            for c in lote:
                if c in filas:
                    yield c, json.loads(zlib.decompress(bytes(filas[c][0]))), filas[c][1] or ""


def version():
    """Cambia cada vez que se guarda algo: sirve para saber si lo armado en disco sigue vigente."""
    _tabla()
    with db.motor().connect() as cx:
        n, a = cx.execute(text("SELECT COUNT(*), MAX(actualizado) FROM senamhi_crudo")).first()
    return f"{n}-{a or ''}"


# ── del crudo a filas (las mismas reglas que el notebook) ────────────────────
def _filas_grafica(g):
    """Filas diarias de un hidrograma: datoActual es el año hidrológico pedido y datoAnterior, el anterior."""
    c = g.get("data") or {}
    fh = c.get("fechaHora") or []
    if g.get("estado") != "OK" or not fh:
        return []
    s = {k: (list(c.get(k) or []) + [None] * len(fh))[:len(fh)] for k in SERIES}
    base = [str(c.get("codEstacion", "") or g.get("cod", "")), c.get("nomEstacion", ""), c.get("nomRio", ""), g.get("variable", ""),
            c.get("unidad", "")]
    out = []
    for i, ms in enumerate(fh):
        f = _fecha_ms(ms)
        v = num(s["datoActual"][i])
        if v is not None:
            out.append((f, "ACTUAL", base, v, num(s["minimo"][i]), num(s["maximo"][i]), num(s["promHistorico"][i]),
                        num(s["rojo"][i]), num(s["naranja"][i]), num(s["amarillo"][i])))
        va, fa = num(s["datoAnterior"][i]), _un_año_antes(f)
        if va is not None and fa is not None:
            out.append((fa, "ANTERIOR", base, va, None, None, None, None, None, None))
    return out


def _cuantil(valores, q):
    """Cuantil con interpolación lineal (como pandas)."""
    v = sorted(valores)
    if not v:
        return 0.0
    p = (len(v) - 1) * q
    i = int(p)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (p - i)


def _escritor(ruta, columnas):
    f = open(ruta, "w", encoding="utf-8-sig", newline="")
    w = csv.writer(f, lineterminator="\n")
    w.writerow(columnas)
    return f, w


def _v(x):
    return "" if x is None else x


def _departamento(cod, meta_info, zonales):
    """Departamento de la estación: el que da SENAMHI (Información Diaria) o, si no, vacío."""
    return sin_tildes((meta_info.get(cod) or {}).get("nomDepa") or "")


def armar(carpeta):
    """Escribe en «carpeta» todos los CSV y devuelve el resumen (filas, estaciones, fechas, estaciones por departamento)."""
    carpeta = Path(carpeta)
    meta = _leer("meta", {}) or {}
    estaciones = _leer("estaciones", []) or []
    zonales = {str(k): str(v) for k, v in (_leer("zonales", {}) or {}).items()}
    fichas = _leer("fichas", {}) or {}
    meta_info = {str(k): v for k, v in (_leer("infoMeta", {}) or {}).items()}
    nombre_est = {str(e.get("codEstacion")): e.get("nomEstacion", "") for e in estaciones}
    hoy_txt = _dia_txt(meta.get("hoy", ""))

    # 1. Información Mensual (antes que el diario: el control la cruza)
    f, w = _escritor(carpeta / ARCHIVOS["mensual"], COLS["mensual"])
    fc, wc = _escritor(carpeta / ARCHIVOS["control-mensual"], COLS["control-mensual"])
    mensual, filas_m, n_men = {}, [], 0                       # {(cod, unidad, año, mes): valor}
    for clave, contenido, dia in _piezas("men:"):
        a, m = int(clave[4:8]), int(clave[9:11])
        servido, filas = (None, None), []
        for bloque in contenido or []:
            r = re.match(r"([A-Z]{3})-(\d{2})$", str((bloque.get("informacion") or {}).get("primDescripcion", "")).strip().upper())
            servido = (2000 + int(r.group(2)), MES_EN[r.group(1)]) if r and r.group(1) in MES_EN else (None, None)
            filas += bloque.get("detalle") or []
        ok = servido == (a, m)
        wc.writerow([a, m, f"{servido[1]:02d}/{servido[0]}" if servido[0] else "", len(filas),
                     "OK" if ok and filas else "SIN DATOS" if not filas else "AÚN NO PUBLICADO (devuelve otro mes)", _dia_txt(dia)])
        if not ok:
            continue
        for x in filas:
            cod = str(x.get("codEsta", ""))
            valor = num(x.get("dato"))
            filas_m.append((cod, a, m, [a, m, f"01/{m:02d}/{a}", cod, x.get("nomEsta", ""), x.get("cuerpoAgua", ""), x.get("nomDepa", ""),
                                        x.get("nomSector", ""), x.get("uniHidrografica", ""), x.get("codZonal", ""), x.get("unidad", ""),
                                        _v(valor), _v(num(x.get("datoAnt"))), _v(num(x.get("datAnomalia"))), x.get("uniAnomalia", ""),
                                        x.get("tendencia") or "", _v(num(x.get("umbralRojo"))), _dia_txt(dia)]))
            if valor:
                mensual[(cod, sin_tildes(x.get("unidad", "")), a, m)] = valor
            if cod not in meta_info and x.get("nomDepa"):
                meta_info[cod] = {"nomDepa": x.get("nomDepa"), "cuerpoAgua": x.get("cuerpoAgua")}
    for _, _, _, fila in sorted(filas_m, key=lambda t: t[:3]):
        w.writerow(fila)
        n_men += 1
    f.close(); fc.close()

    # 2. Hidrograma diario, estación por estación
    f, w = _escritor(carpeta / ARCHIVOS["diario"], COLS["diario"])
    fl, wl = _escritor(carpeta / ARCHIVOS["log"], COLS["log"])
    control, rio, variables, n_dia, ultima = [], {}, {}, 0, None
    grupo, clave_g = [], None

    def cerrar(grupo):
        nonlocal n_dia, ultima
        if not grupo:
            return
        cod, var = grupo[0][0].split(":")[1:3]
        elegidas, estados = {}, []
        # prioridad: el dato del año pedido (ACTUAL) sobre el visto desde el año siguiente; a igualdad, lo más reciente
        for clave, g, dia in sorted(grupo, key=lambda t: t[2], reverse=True):
            filas = _filas_grafica(g)
            ini = _fecha_ms(g["inicio"]) if g.get("inicio") is not None else None
            estado = g.get("estado", "")
            estados.append(estado)
            wl.writerow([cod, nombre_est.get(cod, ""), var, g.get("opcion", ""), g.get("fh", ""), _dmy(ini), len(filas),
                         f"DEVOLVIO OTRO AÑO ({_dmy(ini)})" if estado == "DEVOLVIO OTRO AÑO" and ini else estado, _dia_txt(dia)])
            for fila in filas:
                if fila[0] < INICIO:
                    continue
                previa = elegidas.get(fila[0])
                if previa is None or (previa[1] != "ACTUAL" and fila[1] == "ACTUAL"):
                    elegidas[fila[0]] = fila + (dia,)
        fila_c = {"COD_ESTACION": cod, "ESTACION": nombre_est.get(cod, ""), "VARIABLE": var}
        if not elegidas:
            fila_c["ESTADO"] = ("SIN DATOS" if all(e == "SIN DATOS" for e in estados) else
                                "SIN RESPUESTA" if "SIN RESPUESTA" in estados else estados[0] if estados else "SIN DATOS")
            control.append(fila_c)
            return
        fechas = sorted(elegidas)
        valores, meses = [], {}
        for d in fechas:
            _, serie, base, v, mn, mx, prom, ro, na, am, dia = elegidas[d]
            w.writerow(base + [_dmy(d), d.year, d.month, d.day, año_hidrologico(d), v, _v(mn), _v(mx), _v(prom), _v(ro), _v(na), _v(am),
                               serie, _dia_txt(dia)])
            valores.append(v)
            k = (sin_tildes(base[4]), d.year, d.month)
            s = meses.setdefault(k, [0.0, 0])
            s[0] += v; s[1] += 1
        n_dia += len(fechas)
        base = elegidas[fechas[-1]][2]
        rio.setdefault(cod, base[2])
        variables.setdefault(cod, set()).add(var)
        fila_c["ESTACION"] = fila_c["ESTACION"] or base[1]
        saltos_abs = [abs(b - a) for a, b in zip(valores, valores[1:])]
        lim = _cuantil(saltos_abs, 0.9) if len(saltos_abs) > 10 else 0
        saltos = sum(1 for s in saltos_abs if s > 20 * lim) if lim > 0 else 0
        llega = fechas[0] <= INICIO + timedelta(days=31)
        cruces = [abs((s / n) / mensual[(cod, u, a, m)] - 1) * 100 for (u, a, m), (s, n) in meses.items()
                  if n >= 25 and mensual.get((cod, u, a, m))]
        fila_c.update({"PRIMERA_FECHA": _dmy(fechas[0]), "ULTIMA_FECHA": _dmy(fechas[-1]), "DIAS_CON_DATO": len(fechas),
                       "DIAS_FALTANTES": (fechas[-1] - fechas[0]).days + 1 - len(fechas), "SALTOS_RAROS": saltos, "LLEGA_AL_INICIO": llega,
                       "CRUCE_MENSUAL_DIF_MAX_%": round(max(cruces), 2) if cruces else "",
                       "ESTADO": "REVISAR (saltos)" if saltos else "OK" if llega else
                       f"OK desde {_dmy(fechas[0])} (SENAMHI no trae más atrás)"})
        control.append(fila_c)
        if ultima is None or fechas[-1] > ultima:
            ultima = fechas[-1]

    for clave, g, dia in _piezas("graf:"):
        k = clave.rsplit(":", 1)[0]
        if k != clave_g:
            cerrar(grupo)
            grupo, clave_g = [], k
        grupo.append((clave, g, dia))
    cerrar(grupo)
    f.close(); fl.close()
    f, w = _escritor(carpeta / ARCHIVOS["control"], COLS["control"])
    for c in control:
        w.writerow([_v(c.get(k)) for k in COLS["control"][:-1]] + [hoy_txt])
    f.close()

    # 3. Información Diaria
    f, w = _escritor(carpeta / ARCHIVOS["info-diaria"], COLS["info-diaria"])
    fc, wc = _escritor(carpeta / ARCHIVOS["control-info"], COLS["control-info"])
    filas_i, n_inf, est_inf = [], 0, set()
    for clave, (n, filas), dia in _piezas("inf:"):
        d, hora = date(int(clave[4:8]), int(clave[9:11]), int(clave[12:14])), clave[15:]
        wc.writerow([_dmy(d), hora, n, len(filas), "OK", _dia_txt(dia)])
        for cod, dato, anom, tend, umbral, unidad, uni_anom in filas:
            v = num(dato)
            if v is None:
                continue
            m = meta_info.get(str(cod)) or {}
            filas_i.append((str(cod), d, hora, [str(cod), m.get("nomEsta", ""), m.get("cuerpoAgua", ""), m.get("nomCuenca", ""),
                                                m.get("nomDepa", ""), m.get("nomSector", ""), m.get("uniHidrografica", ""),
                                                m.get("codZonal", ""), _dmy(d), d.year, d.month, d.day, hora, unidad or "", v,
                                                _v(num(anom)), uni_anom or "", tend or "", _v(num(umbral)), _dia_txt(dia)]))
    filas_i.sort(key=lambda t: t[:3])
    for cod, _, _, fila in filas_i:
        w.writerow(fila)
        est_inf.add(cod)
    n_inf = len(filas_i)
    del filas_i
    f.close(); fc.close()

    # 4. Estaciones
    f, w = _escritor(carpeta / ARCHIVOS["estaciones"], COLS["estaciones"])
    por_depto = {}
    for e in estaciones:
        cod = str(e.get("codEstacion"))
        depto = _departamento(cod, meta_info, zonales)
        fi = fichas.get(cod) or {}
        w.writerow([_v(e.get("idEstacion")), cod, e.get("nomEstacion", ""), _v(e.get("subEstacion")), _v(e.get("estado")),
                    zonales.get(cod, ""), ZONALES.get(zonales.get(cod, ""), ""), depto, fi.get("fecha_hora", ""),
                    fi.get("variable_opcion", ""), rio.get(cod, ""), " / ".join(sorted(variables.get(cod, []))), hoy_txt])
        if cod in variables:
            por_depto[depto or "(sin departamento)"] = por_depto.get(depto or "(sin departamento)", 0) + 1
    f.close()
    return {"recolectado": meta.get("hoy", ""), "ultima_fecha": ultima.isoformat() if ultima else "", "estaciones": len(estaciones),
            "estaciones_con_datos": len(variables), "filas_diario": n_dia, "filas_info_diaria": n_inf, "estaciones_info_diaria": len(est_inf),
            "filas_mensual": n_men, "a_revisar": sum(1 for c in control if str(c.get("ESTADO", "")).startswith("REVISAR")),
            "por_departamento": por_depto}


# ── lo armado, en disco (se rehace solo cuando cambian los datos) ────────────
_armado = {"version": None, "carpeta": None, "resumen": None}


def preparado():
    """(carpeta con los CSV, resumen). Los arma si los datos cambiaron desde la última vez."""
    with _candado:
        v = version()
        if _armado["version"] != v or not (_armado["carpeta"] and os.path.isdir(_armado["carpeta"])):
            carpeta = tempfile.mkdtemp(prefix="senamhi_")
            resumen = armar(carpeta)
            vieja = _armado["carpeta"]
            _armado.update(version=v, carpeta=carpeta, resumen=resumen)
            _catalogo.clear()
            if vieja and os.path.isdir(vieja):
                for n in os.listdir(vieja):
                    os.remove(os.path.join(vieja, n))
                os.rmdir(vieja)
        return _armado["carpeta"], _armado["resumen"]


def hay_datos():
    _tabla()
    with db.motor().connect() as cx:
        return bool(cx.execute(text("SELECT COUNT(*) FROM senamhi_crudo WHERE clave LIKE 'graf:%'")).scalar())


def estado():
    """Resumen para la página (sin armar nada si aún no hay datos)."""
    if not hay_datos():
        return {"hay": False}
    return {"hay": True, **preparado()[1]}


def _codigos(departamento):
    """Estaciones de un departamento («16», «22», «25»): las que SENAMHI marca con ese departamento y, de las que no
    traen departamento, las de la dirección zonal que lo atiende. Devuelve {código: True si el departamento es seguro}."""
    nombre = DEPTOS[departamento]
    meta_info = {str(k): v for k, v in (_leer("infoMeta", {}) or {}).items()}
    zonales = {str(k): str(v) for k, v in (_leer("zonales", {}) or {}).items()}
    out = {}
    for e in _leer("estaciones", []) or []:
        cod = str(e.get("codEstacion"))
        d = sin_tildes((meta_info.get(cod) or {}).get("nomDepa") or "")
        if d == nombre:
            out[cod] = True
        elif not d and zonales.get(cod) == ZONAL_DE[departamento]:
            out[cod] = False
    return out


def filtrar(archivo, departamento=""):
    """(nombre, ruta del CSV). Con departamento, deja solo sus estaciones (en un archivo temporal aparte)."""
    carpeta, _ = preparado()
    origen = os.path.join(carpeta, ARCHIVOS[archivo])
    if not departamento or "COD_ESTACION" not in COLS[archivo]:
        return ARCHIVOS[archivo], origen
    codigos = set(_codigos(departamento))
    k = COLS[archivo].index("COD_ESTACION")
    nombre = ARCHIVOS[archivo].replace(".csv", f"_{DEPTOS[departamento].replace(' ', '_')}.csv")
    destino = os.path.join(carpeta, "_" + nombre)
    if not os.path.exists(destino):
        with open(origen, encoding="utf-8-sig", newline="") as fi, open(destino + ".tmp", "w", encoding="utf-8-sig", newline="") as fo:
            r, w = csv.reader(fi), csv.writer(fo, lineterminator="\n")
            w.writerow(next(r))
            w.writerows(fila for fila in r if fila[k] in codigos)
        os.replace(destino + ".tmp", destino)
    return nombre, destino


def paquete(departamento=""):
    """Zip con todos los CSV (de un departamento o de todo el país)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for a in ARCHIVOS:
            if departamento and "COD_ESTACION" not in COLS[a]:
                continue
            nombre, ruta = filtrar(a, departamento)
            z.write(ruta, ("CONTROL/" if a.startswith(("control", "log")) else "DATA/") + nombre)
    return buf.getvalue()


# ── gráfico: el hidrograma de SENAMHI ────────────────────────────────────────
_catalogo = {}


def estaciones_de(departamento):
    """Estaciones del departamento con datos: variables, años hidrológicos y el último dato de cada variable."""
    preparado()
    if departamento in _catalogo:
        return _catalogo[departamento]
    codigos = _codigos(departamento)
    meta_info = {str(k): v for k, v in (_leer("infoMeta", {}) or {}).items()}
    nombres = {str(e.get("codEstacion")): e.get("nomEstacion", "") for e in _leer("estaciones", []) or []}
    out = {}
    for clave, g, dia in _piezas("graf:"):
        _, cod, var, y = clave.split(":")
        c = g.get("data") or {}
        if cod not in codigos or g.get("estado") != "OK" or not c.get("fechaHora"):
            continue
        e = out.setdefault(cod, {"codigo": cod, "estacion": c.get("nomEstacion") or nombres.get(cod, cod), "rio": c.get("nomRio", ""),
                                 "cuenca": (meta_info.get(cod) or {}).get("nomCuenca", ""), "departamento_seguro": codigos[cod],
                                 "variables": {}})
        v = e["variables"].setdefault(var, {"unidad": c.get("unidad", ""), "años": set(), "ultimo": None})
        y = int(y)
        v["años"].add(y)
        if any(num(x) is not None for x in c.get("datoAnterior") or []):
            v["años"].add(y - 1)
        if v["ultimo"] is None or y >= v["ultimo"]["_y"]:
            actual = c.get("datoActual") or []
            for i in range(len(actual) - 1, -1, -1):
                if num(actual[i]) is not None:
                    serie = lambda k: num((c.get(k) or [None] * len(actual))[i])   # noqa: E731
                    v["ultimo"] = {"_y": y, "fecha": _fecha_ms(c["fechaHora"][i]).isoformat(), "valor": num(actual[i]),
                                   "anterior": serie("datoAnterior"), "promedio": serie("promHistorico"), "rojo": serie("rojo"),
                                   "naranja": serie("naranja"), "amarillo": serie("amarillo")}
                    break
    lista = []
    for e in out.values():
        for v in e["variables"].values():
            v["años"] = sorted(a for a in v["años"] if a >= año_hidrologico(INICIO))
            if v["ultimo"]:
                v["ultimo"].pop("_y")
        lista.append(e)
    lista.sort(key=lambda e: (e["rio"], e["estacion"]))
    _catalogo[departamento] = lista
    return lista


def serie(codigo, variable, año):
    """El hidrograma de un año hidrológico (1 de setiembre a 31 de agosto): el año, el anterior, el promedio histórico,
    mínimo y máximo del día y los umbrales. Si ese año no se pidió directamente, se arma con lo que traen los vecinos."""
    propio = _leer(f"graf:{codigo}:{variable}:{año}")
    sig = _leer(f"graf:{codigo}:{variable}:{año + 1}")
    ant = _leer(f"graf:{codigo}:{variable}:{año - 1}")
    ok = lambda g: g and g.get("estado") == "OK" and (g.get("data") or {}).get("fechaHora")   # noqa: E731
    propio, sig, ant = (g["data"] if ok(g) else None for g in (propio, sig, ant))
    if not (propio or sig):
        return None
    dias, d = [], date(año, 9, 1)
    while d < date(año + 1, 9, 1):
        dias.append(d)
        d += timedelta(days=1)

    def por_dia(c, k, corrimiento=0):
        """{(mes, día): valor} de la serie k; con corrimiento, la fecha se lleva tantos años atrás o adelante."""
        if not c or not c.get(k):
            return {}
        out = {}
        for ms, v in zip(c["fechaHora"], c[k]):
            f, v = _fecha_ms(ms), num(v)
            if v is not None:
                out[(f.month, f.day)] = v
        return out

    toma = lambda m: [m.get((d.month, d.day)) for d in dias]   # noqa: E731
    fuente = propio or sig or ant
    actual = por_dia(propio, "datoActual") or por_dia(sig, "datoAnterior")
    anterior = por_dia(propio, "datoAnterior") or por_dia(ant, "datoActual")
    ref = propio or sig
    return {"codigo": codigo, "variable": variable, "año": año, "estacion": fuente.get("nomEstacion", ""), "rio": fuente.get("nomRio", ""),
            "unidad": fuente.get("unidad", ""), "desde": dias[0].isoformat(), "dias": len(dias),
            "actual": toma(actual), "anterior": toma(anterior), "promedio": toma(por_dia(ref, "promHistorico")),
            "minimo": toma(por_dia(propio, "minimo")), "maximo": toma(por_dia(propio, "maximo")),
            "rojo": toma(por_dia(ref, "rojo")), "naranja": toma(por_dia(ref, "naranja")), "amarillo": toma(por_dia(ref, "amarillo"))}


def rango(codigo, variable, desde, hasta):
    """La serie continua entre dos fechas (hasta 5 años): se une el hidrograma de cada año hidrológico que toca el tramo.
    «anterior» es el mismo día un año antes, como en el gráfico de SENAMHI."""
    if hasta < desde:
        desde, hasta = hasta, desde
    if (hasta - desde).days > 5 * 366:
        raise ValueError("El rango puede ser de hasta 5 años.")
    claves = ("actual", "anterior", "promedio", "minimo", "maximo", "rojo", "naranja", "amarillo")
    out = {k: [] for k in claves}
    base = None
    for y in range(año_hidrologico(desde), año_hidrologico(hasta) + 1):
        s = serie(codigo, variable, y)
        inicio = date(y, 9, 1)
        n = (date(y + 1, 9, 1) - inicio).days
        for i in range(n):
            d = inicio + timedelta(days=i)
            if desde <= d <= hasta:
                for k in claves:
                    out[k].append(s[k][i] if s else None)
        if s and base is None:
            base = s
    if base is None or not any(v is not None for v in out["actual"]):
        return None
    return {"codigo": codigo, "variable": variable, "estacion": base["estacion"], "rio": base["rio"], "unidad": base["unidad"],
            "desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": len(out["actual"]), **out}
