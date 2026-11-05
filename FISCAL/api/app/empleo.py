"""Empleo: trabajadores asalariados privados formales (MTPE, Planilla Electrónica: PLAME y T-Registro).

Entra el Excel que genera EMPLEO/Scraping_MTPE_Empleo_x_Region_Actividad.ipynb (en Colab o en GitHub Actions):
columnas AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO, una fila por mes, región y actividad. Desde noviembre 2026 el
scraper trae solo el total de cada región (ACTIVIDAD_ECONOMICA = «Total») desde 2025; los meses anteriores conservan
el detalle por sectores que ya estaba en la base.

  · totales(): el total de trabajadores de cada región por mes, del año anterior y del año en curso, con su variación %;

También arma lo que publica la síntesis de cada región (junio 2026):
  · el cuadro «Trabajadores asalariados privados formales» (Loreto N° 6, San Martín N° 4, Ucayali N° 7): siete ramas y
    el total, el mes contra el mismo mes del año anterior y contra diciembre del año anterior, con su variación %;
  · el gráfico de la variación % interanual del total (25 meses);
  · el anexo por sectores (Loreto, Anexo 5): variación % interanual de cada sector en los últimos 13 meses.
"""
import io
import re
import unicodedata

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from .catalogo import DEPARTAMENTOS

COLUMNAS = ["AÑO", "MES", "REGIÓN", "ACTIVIDAD_ECONOMICA", "EMPLEO"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
MESES_CORTOS = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Set.", "Oct.", "Nov.", "Dic."]
# rama del cuadro de la síntesis (orden alfabético, como en el informe) y del anexo
RAMAS = {"Agrícola": "Agrícola", "Comercio": "Comercio", "Construcción": "Construcción", "Manufactura": "Manufactura",
         "Minería": "Minería", "No precisa": "Otros", "Servicios": "Servicios"}
ORDEN_CUADRO = ["Agrícola", "Comercio", "Construcción", "Manufactura", "Minería", "Otros", "Servicios"]
ORDEN_ANEXO = [("Agrícola", "Agricultura"), ("Minería", "Minería"), ("Manufactura", "Manufactura"),
               ("Construcción", "Construcción"), ("Comercio", "Comercio"), ("Servicios", "Servicios")]
FUENTE = "Fuente: MTPE, Planilla Electrónica – PLAME y T-Registro. Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos."


def _clave(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", t.lower())


_DEPTO_DE_REGION = {_clave(n): c for c, n in DEPARTAMENTOS.items()}
_DEPTO_DE_REGION.update({"limametropolitana": "15", "limaprovincias": "15", "lima": "15"})


def depto_de(region):
    return _DEPTO_DE_REGION.get(_clave(region))


# ── Formato LONG del scraper (descarga por regiones) ──
# los 26 ámbitos del tablero del MTPE, en el orden del selector del notebook (sin el total «Perú», que no se guarda)
REGIONES = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cusco", "Huancavelica",
            "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque", "Lima Metropolitana", "Lima Provincias", "Loreto",
            "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"]
# grupos de la página (macrorregiones); la descarga acepta cualquier combinación de regiones
GRUPOS_REGIONES = {
    "Sucursal Iquitos (Loreto, San Martín, Ucayali)": ["Loreto", "San Martín", "Ucayali"],
    "Oriente": ["Amazonas", "Loreto", "San Martín", "Ucayali"],
    "Norte": ["Cajamarca", "La Libertad", "Lambayeque", "Piura", "Tumbes"],
    "Centro": ["Áncash", "Ayacucho", "Huancavelica", "Huánuco", "Ica", "Junín", "Pasco"],
    "Sur": ["Apurímac", "Arequipa", "Cusco", "Madre de Dios", "Moquegua", "Puno", "Tacna"],
    "Lima y Callao": ["Callao", "Lima Metropolitana", "Lima Provincias"],
}


def region_de(texto):
    """Nombre de la región (de REGIONES) a partir de su nombre o clave sin tildes; None si no es una."""
    return {_clave(r): r for r in REGIONES}.get(_clave(texto))


def long(df, regiones):
    """Filas de las regiones pedidas en el formato del Excel del scraper, ordenadas como él."""
    claves = {_clave(r) for r in regiones}
    df = df[df["REGIÓN"].map(_clave).isin(claves)][COLUMNAS]
    return df.sort_values(["REGIÓN", "ACTIVIDAD_ECONOMICA", "AÑO", "MES"]).reset_index(drop=True)


def nombre_long(regiones):
    """Mismo nombre que pone el notebook: Loreto_empleo.xlsx, Loreto_San_Martín_Ucayali_empleo.xlsx, 26_regiones_empleo.xlsx."""
    regiones = [r for r in REGIONES if r in regiones]
    if len(regiones) <= 3:
        return f"{'_'.join(r.replace(' ', '_') for r in regiones)}_empleo.xlsx"
    return f"{len(regiones)}_regiones_empleo.xlsx"


def reconocer(ruta):
    """True si el Excel tiene las columnas del scraper de empleo."""
    columnas = {str(c).strip().upper() for c in pd.read_excel(ruta, sheet_name=0, nrows=0).columns}
    return {"AÑO", "MES", "REGIÓN", "ACTIVIDAD_ECONOMICA", "EMPLEO"} <= columnas


def leer(archivos):
    """archivos: [(n_archivo, ruta)] -> DataFrame con columnas internas, avisos."""
    partes, avisos = [], []
    for n, ruta in archivos:
        df = pd.read_excel(ruta, sheet_name=0)
        df.columns = [str(c).strip().upper() for c in df.columns]
        df = df[COLUMNAS].dropna(subset=["AÑO", "MES", "REGIÓN"])
        df["_depto"] = df["REGIÓN"].map(depto_de)
        sin = sorted(set(df.loc[df["_depto"].isna(), "REGIÓN"].astype(str)))
        if sin:
            avisos.append(f"Empleo: {', '.join(sin)} no es un departamento; no se cargó (el total del Perú no se guarda).")
        df = df[df["_depto"].notna()].copy()
        df["AÑO"], df["MES"] = df["AÑO"].astype(int), df["MES"].astype(int)
        df["EMPLEO"] = pd.to_numeric(df["EMPLEO"], errors="coerce").fillna(0)
        df["REGIÓN"], df["ACTIVIDAD_ECONOMICA"] = df["REGIÓN"].astype(str), df["ACTIVIDAD_ECONOMICA"].astype(str)
        # Lima Metropolitana y Lima Provincias comparten departamento: se reemplazan por separado
        df["_anio"], df["_mes"], df["_nivel"], df["_archivo"] = df["AÑO"], df["MES"], df["REGIÓN"].map(_clave), n
        partes.append(df)
    return (pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()), avisos


# ── Lo que publica la síntesis ──
TOTAL = "Total"


def _serie(df):
    """Trabajadores por rama y periodo (AAAA*100+MM) y el total: la fila «Total» del MTPE si la hay, si no la suma de las
    ramas. Los meses sin detalle por sectores quedan con las ramas vacías (NaN)."""
    df = df.assign(P=df["AÑO"] * 100 + df["MES"])
    es_total = df["ACTIVIDAD_ECONOMICA"].str.strip().str.lower() == "total"
    sect = df[~es_total].assign(RAMA=lambda d: d["ACTIVIDAD_ECONOMICA"].map(RAMAS).fillna("Otros"))
    t = sect.pivot_table(index="P", columns="RAMA", values="EMPLEO", aggfunc="sum").reindex(columns=ORDEN_CUADRO) if not sect.empty \
        else pd.DataFrame(columns=ORDEN_CUADRO, dtype=float)
    t = t.reindex(sorted(set(t.index) | set(df.loc[es_total, "P"])))
    t[TOTAL] = t[ORDEN_CUADRO].sum(axis=1, min_count=1)
    tot = df[es_total].groupby("P")["EMPLEO"].sum()
    t.loc[tot.index, TOTAL] = tot
    t.index = t.index.astype(int)
    return t


def totales(df, desde=2025):
    """El total de trabajadores de cada región por mes, desde «desde» hasta el último mes con datos.
    -> {"anios": [...], "ultimo": "AAAA-MM", "regiones": [{"region", "valores": {"AAAA-MM": n}, "var": {"AAAA-MM": %}}]}"""
    if df.empty:
        return {"anios": [], "ultimo": None, "regiones": []}
    salida, ultimo = [], 0
    for r in REGIONES:
        d = df[df["REGIÓN"].map(_clave) == _clave(r)]
        if d.empty:
            continue
        t = _serie(d)[TOTAL].dropna()
        ultimo = max(ultimo, int(t.index.max()))
        val = {f"{p // 100}-{p % 100:02d}": float(v) for p, v in t.items() if p // 100 >= desde}
        var = {f"{p // 100}-{p % 100:02d}": _var(float(t[p - 100]) if p - 100 in t.index else None, float(v))
               for p, v in t.items() if p // 100 >= desde}
        salida.append({"region": r, "valores": val, "var": var})
    anios = list(range(desde, ultimo // 100 + 1)) if ultimo else []
    return {"anios": anios, "ultimo": f"{ultimo // 100}-{ultimo % 100:02d}" if ultimo else None, "regiones": salida}


COLUMNAS_TOTAL = ["AÑO", "MES", "REGIÓN", "EMPLEO", "VAR_%"]
ACTIVIDADES = ["Agrícola", "Minería", "Manufactura", "Construcción", "Comercio", "Servicios", "No precisa"]


def de_actividad(df, actividad):
    """Las filas de una actividad, con la forma del total (para reusar totales(), excel_totales() y long_totales())."""
    d = df[df["ACTIVIDAD_ECONOMICA"].map(_clave) == _clave(actividad)]
    return d.assign(ACTIVIDAD_ECONOMICA="Total")


def long_sectores(df, desde):
    """Todas las actividades en formato LONG: AÑO, MES, REGIÓN, ACTIVIDAD_ECONOMICA, EMPLEO, VAR_%."""
    partes = []
    for a in ACTIVIDADES:
        x = long_totales(totales(de_actividad(df, a), desde))
        x.insert(3, "ACTIVIDAD_ECONOMICA", a)
        partes.append(x)
    out = pd.concat(partes, ignore_index=True)
    orden = {a: i for i, a in enumerate(ACTIVIDADES)}
    return out.sort_values(["REGIÓN", "ACTIVIDAD_ECONOMICA", "AÑO", "MES"], key=lambda c: c.map(orden) if c.name == "ACTIVIDAD_ECONOMICA" else c).reset_index(drop=True)


def long_totales(x):
    """El total por región en formato LONG: una fila por región y mes (AÑO, MES, REGIÓN, EMPLEO, VAR_%), ordenado por
    región, año y mes, como el Excel del scraper."""
    filas = [{"AÑO": int(m[:4]), "MES": int(m[5:]), "REGIÓN": r["region"], "EMPLEO": int(round(v)), "VAR_%": r["var"].get(m)}
             for r in x["regiones"] for m, v in sorted(r["valores"].items())]
    return pd.DataFrame(filas, columns=COLUMNAS_TOTAL)


def excel_totales(x, titulo="TRABAJADORES ASALARIADOS PRIVADOS FORMALES POR REGIÓN"):
    """Las regiones en filas y los meses en columnas: una hoja con el número de trabajadores y otra con la var. %."""
    wb = Workbook()
    neg = Font(bold=True)
    meses = [f"{a}-{m:02d}" for a in x["anios"] for m in range(1, 13) if f"{a}-{m:02d}" <= (x["ultimo"] or "")]
    titulo_hoja = titulo
    for i, (hoja, clave, titulo, fmt) in enumerate((("Trabajadores", "valores", "(Número de trabajadores)", "#,##0"),
                                                    ("Var. %", "var", "(Variación % respecto a similar mes del año anterior)", "0.0"))):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = hoja
        ws.append([titulo_hoja]); ws.append([titulo]); ws.append([])
        ws.append(["Región"] + [etiqueta(int(m.replace("-", "")), True) for m in meses])
        for r in x["regiones"]:
            ws.append([r["region"]] + [r[clave].get(m) for m in meses])
            for celda in ws[ws.max_row][1:]:
                celda.number_format = fmt
        ws.append([]); ws.append([FUENTE])
        ws["A1"].font = neg
        for celda in ws[4]:
            celda.font = neg
        ws.column_dimensions["A"].width = 20
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def _var(a, b):
    return None if not a or b is None else round((b / a - 1) * 100, 1)


def etiqueta(p, corta=False):
    return f"{(MESES_CORTOS if corta else MESES)[p % 100 - 1]} {p // 100}"


def cuadros(df, periodo=None):
    """df: filas de empleo de una región. periodo AAAA-MM (por defecto, el último con datos)."""
    if df.empty:
        return None
    t = _serie(df)
    ultimo = int(t.index.max())
    p = int(periodo.replace("-", "")) if periodo else ultimo
    if p not in t.index:
        raise ValueError(f"No hay datos de empleo para {etiqueta(p)} (último mes: {etiqueta(ultimo)}).")
    p_ant, p_dic = p - 100, (p // 100 - 1) * 100 + 12
    por_sectores = bool(t.loc[p, ORDEN_CUADRO].notna().any())      # desde 2025 el scraper trae solo el total
    fila = lambda rama: {"rama": rama, "mes_anterior": _val(t, p_ant, rama), "mes": _val(t, p, rama),
                         "var_mes": _var(_val(t, p_ant, rama), _val(t, p, rama)), "diciembre": _val(t, p_dic, rama),
                         "var_dic": _var(_val(t, p_dic, rama), _val(t, p, rama))}
    cuadro = [fila(r) for r in (ORDEN_CUADRO if por_sectores else []) + ["Total"]]
    periodos = [q for q in t.index if q <= p]
    grafico = [{"periodo": etiqueta(q, True), "var": _var(_val(t, q - 100, "Total"), t.at[q, "Total"])} for q in periodos[-25:]]
    anexo = [{"periodo": etiqueta(q, True), **{n: _var(_val(t, q - 100, r), _val(t, q, r)) for r, n in ORDEN_ANEXO},
              "Total": _var(_val(t, q - 100, "Total"), t.at[q, "Total"])} for q in periodos[-13:]]
    # número de trabajadores (total), desde enero de tres años antes, como el gráfico del portal del MTPE
    niveles = [{"periodo": etiqueta(q, True), "trabajadores": float(t.at[q, "Total"])} for q in periodos if q >= (p // 100 - 3) * 100 + 1]
    # el total por mes del año anterior y del año del informe (hasta el mes del informe)
    a = p // 100
    mensual = [{"mes": MESES[k - 1], "anterior": _val(t, (a - 1) * 100 + k, "Total"),
                "actual": _val(t, a * 100 + k, "Total") if a * 100 + k <= p else None,
                "var": _var(_val(t, (a - 1) * 100 + k, "Total"), _val(t, a * 100 + k, "Total")) if a * 100 + k <= p else None}
               for k in range(1, 13)]
    return {"periodo": f"{p // 100}-{p % 100:02d}", "ultimo": f"{ultimo // 100}-{ultimo % 100:02d}",
            "titulo_mes": MESES[p % 100 - 1], "anio": p // 100, "cuadro": cuadro, "grafico": grafico,
            "anexo": anexo if por_sectores else [], "niveles": niveles, "por_sectores": por_sectores, "mensual": mensual}


def _val(t, p, rama):
    if p not in t.index or pd.isna(t.at[p, rama]):
        return None
    return float(t.at[p, rama])


def excel(region, c):
    """Los tres cuadros en un Excel, con títulos, unidades y fuente como en la síntesis."""
    wb = Workbook()
    neg, centro = Font(bold=True), Alignment(horizontal="center")
    ws = wb.active
    ws.title = "Cuadro"
    a, mes = c["anio"], c["titulo_mes"]
    for fila in ([f"{region.upper()}: TRABAJADORES ASALARIADOS PRIVADOS FORMALES"], ["(Número de trabajadores)"], [],
                 ["Rama de actividad", f"{mes} {a - 1}", f"{mes} {a}", "Var. %", f"Dic. {a - 1}", f"{mes[:3]}. {a}", "Var. %"]):
        ws.append(fila)
    for r in c["cuadro"]:
        ws.append([r["rama"], r["mes_anterior"], r["mes"], r["var_mes"], r["diciembre"], r["mes"], r["var_dic"]])
    ws.append([]); ws.append([FUENTE])
    for celda in ws[4]:
        celda.font, celda.alignment = neg, centro
    for fila in ws.iter_rows(min_row=5, max_row=4 + len(c["cuadro"])):
        for i, celda in enumerate(fila):
            celda.number_format = "0.0" if i in (3, 6) else "#,##0"
        if fila[0].value == "Total":
            for celda in fila:
                celda.font = neg
    ws["A1"].font = neg
    for col, ancho in zip("ABCDEFG", [22, 12, 12, 9, 12, 12, 9]):
        ws.column_dimensions[col].width = ancho

    wg = wb.create_sheet("Gráfico")
    wg.append([f"{region.upper()}: TRABAJADORES ASALARIADOS PRIVADOS FORMALES"]); wg.append(["(Variación % respecto a similar mes del año anterior)"]); wg.append([])
    wg.append(["Mes", "Var. %"])
    for g in c["grafico"]:
        wg.append([g["periodo"], g["var"]])
    wg["A1"].font = neg
    wn = wb.create_sheet("Trabajadores")
    wn.append([f"{region.upper()}: NÚMERO DE TRABAJADORES ASALARIADOS PRIVADOS FORMALES"]); wn.append(["(Total, número de trabajadores)"]); wn.append([])
    wn.append(["Mes", "Trabajadores"])
    for g in c["niveles"]:
        wn.append([g["periodo"], g["trabajadores"]])
        wn.cell(wn.max_row, 2).number_format = "#,##0"
    wn["A1"].font = neg

    wa = wb.create_sheet("Anexo")
    wa.append([f"{region.upper()}: TRABAJADORES ASALARIADOS PRIVADOS FORMALES POR SECTORES ECONÓMICOS"])
    wa.append(["(Variación % con respecto al mismo mes del año anterior)"]); wa.append([])
    wa.append(["Mes"] + [n for _, n in ORDEN_ANEXO] + ["Total"])
    for r in c["anexo"]:
        wa.append([r["periodo"]] + [("n.d." if r[n] is None else r[n]) for _, n in ORDEN_ANEXO] + ["n.d." if r["Total"] is None else r["Total"]])
    wa.append([]); wa.append([FUENTE])
    wa["A1"].font = neg
    for hoja in (wg, wa):
        for celda in hoja[4]:
            celda.font, celda.alignment = neg, centro
        for fila in hoja.iter_rows(min_row=5):
            for celda in fila[1:]:
                if isinstance(celda.value, (int, float)):
                    celda.number_format = "0.0"
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()
