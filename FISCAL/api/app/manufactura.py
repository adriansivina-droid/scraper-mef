"""Manufactura: el índice de volumen físico manufacturero (IVFM) de cada región y el cuadro de la síntesis.

Entra el libro IVFM de la región tal como lo arma la Sucursal (IVFM-LO 2026 TOTAL.xlsx, IVFM-SM-2026 TOTAL.xlsx,
IVFM-UCA-2026 TOTAL.xlsx): una hoja «IVF … TOTAL» con un bloque por año. De cada bloque se toman solo los
«Índices mensuales» de cada rama CIIU (4 dígitos) y, de la columna D, su ponderación base 2007; el IVF ponderado,
los grupos y el total se calculan aquí, igual que en el libro:

  · índice de un grupo (primaria, no primaria) o del total = Σ (ponderación × índice) / Σ ponderación del grupo;
  · var. % del mes: índice del mes t / mismo mes de t-1; enero-mes: promedio de los índices de enero al mes;
  · contribución (puntos): var. % de la rama × (ponderación × índice de t-1) / Σ (ponderación × índice de t-1);
  · estructura %: participación de la rama en el IVF ponderado de todo el año anterior (Σ de sus 12 meses).

Así el cuadro sale del IVFM sin copiar nada a mano (Manuf_Base, Manufactura_Cuadro y Manufactura_Graf del libro
«Cdro - Graf» de cada región).
"""
import io
import re
import unicodedata

import openpyxl
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from .catalogo import DEPARTAMENTOS

COLUMNAS = ["AÑO", "MES", "DEPARTAMENTO", "GRUPO", "CIIU", "RAMA", "PONDERACION", "INDICE"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
CORTOS = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Set.", "Oct.", "Nov.", "Dic."]
PRIMARIA, NO_PRIMARIA = "MANUFACTURA PRIMARIA", "MANUFACTURA NO PRIMARIA"
# código de la hoja («IVF LO 2026 TOTAL», «IVF SM26 TOTAL», «IVF UC 2026 TOTAL») o del encabezado «REGION : …»
REGION = {"LO": "16", "SM": "22", "UC": "25", "LORETO": "16", "SANMARTIN": "22", "UCAYALI": "25"}
# nombres de la síntesis (Manufactura_Cuadro de cada región) por código CIIU; algunos cambian por región
NOMBRES = {"1511": "Productos cárnicos", "1513": "Conservas de palmito", "1514": "Aceite y manteca", "1520": "Productos lácteos",
           "1531": "Pilado de arroz", "1533": "Alimentos para animales", "1541": "Productos de panadería", "1543": "Chocolates",
           "1553": "Bebidas malteadas", "1554": "Bebidas gaseosas", "2010": "Madera aserrada", "2021": "Triplay",
           "2212": "Periódicos", "2221": "Impresión", "2320": "Refinación de petróleo", "2411": "Oxígeno industrial",
           "2424": "Jabón", "2693": "Ladrillos", "2694": "Cemento", "2695": "Ladrillos, bloques y adoquines",
           "2710": "Calaminas", "2899": "Mallas metálicas", "2911": "Motores para pozos", "2912": "Bombas para pozos",
           "3591": "Motocicletas y motokar"}
NOMBRES_REGION = {"22": {"2320": "Biodiesel", "1520": "Queso y mantequilla"}, "25": {"2899": "Clavos para madera"}}
# ramas que el cuadro de la síntesis presenta juntas: en Loreto, motores y bombas para pozos son la misma rama (bombas de agua)
FUSIONES = {"16": {"2912": "2911"}}
FUENTE = "Fuente: DIREPRO y Empresas. Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos."


def _clave(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", t.upper())


def reconocer(ruta):
    """True si es un libro IVFM (hoja «IVF …» con «INDICE VOLUMEN FISICO MANUFACTURERO»)."""
    try:
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception:
        return False
    try:
        for ws in wb.worksheets:
            b2 = next(ws.iter_rows(min_row=2, max_row=2, min_col=2, max_col=2, values_only=True))[0]
            if "VOLUMENFISICOMANUFACTURERO" in _clave(b2):
                return True
        return False
    finally:
        wb.close()


def _depto(ws):
    m = re.match(r"^\s*IVF\s*([A-Z]{2})", ws.title, re.I)
    if m and m.group(1).upper() in REGION:
        return REGION[m.group(1).upper()]
    for fila in ws.iter_rows(min_row=1, max_row=3, values_only=True):
        for v in fila:
            if isinstance(v, str) and "REGION" in _clave(v):
                k = _clave(v.split(":", 1)[-1])
                if k in REGION:
                    return REGION[k]
    return None


def leer_libro(ruta):
    """-> (departamento, DataFrame con COLUMNAS), avisos. Una fila por rama CIIU y mes con datos."""
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = next((w for w in wb.worksheets if "VOLUMENFISICOMANUFACTURERO" in _clave(w["B2"].value)), None)
    if ws is None:
        return None, pd.DataFrame(columns=COLUMNAS), [f"{ruta.name}: no tiene la hoja del IVF manufacturero."]
    depto = _depto(ws)
    if depto is None:
        return None, pd.DataFrame(columns=COLUMNAS), [f"{ruta.name}: no se reconoce la región (la hoja debe llamarse «IVF LO/SM/UC …»)."]
    # ramas: código CIIU de 4 dígitos en C y ponderación numérica en D; el grupo, por la fila «INDUSTRIA …» de arriba
    ramas, grupo = [], None
    for r in range(5, ws.max_row + 1):
        b = _clave(ws.cell(r, 2).value)
        if b.startswith("INDUSTRIANOPRIMARIA"):
            grupo = NO_PRIMARIA
        elif b.startswith("INDUSTRIAPRIMARIA"):
            grupo = PRIMARIA
        ciiu = str(ws.cell(r, 3).value or "").strip()
        pond = ws.cell(r, 4).value
        if re.fullmatch(r"\d{4}", ciiu) and isinstance(pond, (int, float)) and grupo:
            ramas.append((r, grupo, ciiu, str(ws.cell(r, 2).value or "").strip(), float(pond)))
    # bloques «Índices mensuales AAAA» (el libro escribe también «Inidces»)
    bloques = {}
    for c in range(1, ws.max_column + 1):
        for fila in (1, 2):
            m = re.match(r"\s*In\w*ces\s+mensuales\s+(\d{4})", str(ws.cell(fila, c).value or ""), re.I)
            if m:
                bloques[int(m.group(1))] = c
    filas, avisos = [], []
    for anio, c0 in sorted(bloques.items()):
        for m in range(12):
            vals = [ws.cell(r, c0 + m).value for r, *_ in ramas]
            vals = [float(v) if isinstance(v, (int, float)) else 0.0 for v in vals]
            if not any(vals):                        # mes sin datos todavía (setiembre-diciembre en 0)
                continue
            for (r, grupo, ciiu, rama, pond), v in zip(ramas, vals):
                filas.append({"AÑO": anio, "MES": m + 1, "DEPARTAMENTO": DEPARTAMENTOS[depto], "GRUPO": grupo, "CIIU": ciiu,
                              "RAMA": rama, "PONDERACION": pond, "INDICE": v})
    df = pd.DataFrame(filas, columns=COLUMNAS)
    if df.empty:
        avisos.append(f"{ruta.name}: no se encontraron índices mensuales.")
    return depto, df, avisos


def leer(archivos):
    """archivos: [(n_archivo, ruta)] -> DataFrame con columnas internas, avisos."""
    partes, avisos = [], []
    for n, ruta in archivos:
        depto, df, av = leer_libro(ruta)
        avisos += av
        if df.empty:
            continue
        p = df["AÑO"] * 100 + df["MES"]
        avisos.append(f"{ruta.name}: IVF manufacturero de {DEPARTAMENTOS[depto].title()}, {df['CIIU'].nunique()} ramas, "
                      f"{p.min() // 100}-{p.min() % 100:02d} a {p.max() // 100}-{p.max() % 100:02d}.")
        partes.append(df.assign(_anio=df["AÑO"], _mes=df["MES"], _depto=depto, _nivel="", _archivo=n))
    return (pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()), avisos


# ── El cuadro de la síntesis ──
def _var(a, b):
    """var. % de b respecto de a; None si la base es 0 (el libro muestra «-» o #DIV/0!)."""
    return None if not a or b is None else (b / a - 1) * 100


def etiqueta(p, corta=True):
    return f"{(CORTOS if corta else MESES)[p % 100 - 1]} {p // 100}"


def cuadros(depto, df, periodo=None):
    """df: filas de la base manu-ivf de un departamento. periodo AAAA-MM (por defecto, el último con datos)."""
    if df is None or df.empty:
        return None
    df = df.copy()
    for c in ("AÑO", "MES"):
        df[c] = df[c].astype(int)
    df["P"] = df["AÑO"] * 100 + df["MES"]
    df["W"], df["I"] = pd.to_numeric(df["PONDERACION"]), pd.to_numeric(df["INDICE"])
    df["CIIU"] = df["CIIU"].astype(str)
    fus = FUSIONES.get(depto, {})
    if fus and df["CIIU"].isin(list(fus)).any():
        # la rama unida: ponderación = suma; índice = promedio ponderado de los índices (lo mismo que suma el IVF)
        df["CIIU"] = df["CIIU"].replace(fus)
        df["WI"] = df["W"] * df["I"]
        claves = ["AÑO", "MES", "P", "CIIU"]
        prim = df.drop_duplicates(claves)[claves + ["DEPARTAMENTO", "GRUPO", "RAMA"]]
        sumas = df.groupby(claves, as_index=False)[["W", "WI"]].sum()
        df = prim.merge(sumas, on=claves)
        df["I"] = (df["WI"] / df["W"]).where(df["W"] > 0, 0.0)
    periodos = sorted(df["P"].unique())
    ultimo = int(periodos[-1])
    p = int(periodo.replace("-", "")) if periodo else ultimo
    if p not in periodos:
        raise ValueError(f"No hay IVF manufacturero de {etiqueta(p, False)} (último mes: {etiqueta(ultimo, False)}).")
    a, m = p // 100, p % 100
    # ramas en el orden del libro (primaria primero), con la ponderación y el grupo de la carga más reciente
    orden = list(dict.fromkeys(df["CIIU"]))
    ramas = df.sort_values(["AÑO", "MES"]).drop_duplicates("CIIU", keep="last").set_index("CIIU")
    pos = {c: i for i, c in enumerate(orden)}
    orden.sort(key=lambda c: (ramas.at[c, "GRUPO"] != PRIMARIA, pos[c]))
    ramas = ramas.loc[orden]
    w = ramas["W"]
    I = df.pivot_table(index="P", columns="CIIU", values="I", aggfunc="last").reindex(columns=ramas.index).fillna(0.0)
    nombre = {c: NOMBRES_REGION.get(depto, {}).get(c) or NOMBRES.get(c) or str(ramas.at[c, "RAMA"]).capitalize() for c in ramas.index}
    grupos = {PRIMARIA: [c for c in ramas.index if ramas.at[c, "GRUPO"] == PRIMARIA],
              NO_PRIMARIA: [c for c in ramas.index if ramas.at[c, "GRUPO"] == NO_PRIMARIA]}

    def ind(q, cs):                                    # índice de un conjunto de ramas en el periodo q
        if q not in I.index or not cs or not w[cs].sum():
            return None
        return float((I.loc[q, cs] * w[cs]).sum() / w[cs].sum())

    def prom(anio, cs):                                 # promedio enero-mes
        qs = [anio * 100 + k for k in range(1, m + 1) if anio * 100 + k in I.index]
        vals = [ind(q, cs) for q in qs]
        return sum(vals) / len(vals) if vals and len(qs) == m else None

    todas = list(ramas.index)
    # bases de la contribución: Σ (ponderación × índice) de t-1, del mes y del promedio enero-mes
    base_mes = sum(float(w[c]) * (I.at[p - 100, c] if p - 100 in I.index else 0.0) for c in todas)
    prom_ant = {c: prom(a - 1, [c]) for c in todas}
    base_acu = sum(float(w[c]) * (prom_ant[c] or 0.0) for c in todas)
    # estructura %: el IVF ponderado de todo el año anterior
    q_ant = [q for q in I.index if q // 100 == a - 1]
    peso_ant = {c: float(w[c]) * float(I.loc[q_ant, c].sum()) for c in todas} if q_ant else {c: 0.0 for c in todas}
    tot_ant = sum(peso_ant.values())

    def fila(nombre_f, cs, nivel):
        mb, ma = ind(p - 100, cs), ind(p, cs)
        ab, aa = prom(a - 1, cs), prom(a, cs)
        vm, va = _var(mb, ma), _var(ab, aa)
        c_mes = sum((_var(I.at[p - 100, c], I.at[p, c]) or 0) * float(w[c]) * I.at[p - 100, c] / base_mes
                    for c in cs if p - 100 in I.index) if base_mes else None
        c_acu = sum((_var(prom_ant[c], prom(a, [c])) or 0) * float(w[c]) * (prom_ant[c] or 0) / base_acu for c in cs) if base_acu else None
        vacia = not any([mb, ma, ab, aa])
        return {"nombre": nombre_f, "nivel": nivel, "ciiu": cs[0] if nivel == 2 else None, "vacia": vacia,
                "estructura": (sum(peso_ant[c] for c in cs) / tot_ant * 100) if tot_ant else None,
                "ponderacion": float(w[cs].sum()),
                "mes_b": mb, "mes_a": ma, "var_mes": vm, "contrib_mes": None if vacia else c_mes,
                "acum_b": ab, "acum_a": aa, "var_acum": va, "contrib_acum": None if vacia else c_acu}

    filas = []
    for g, cs in grupos.items():
        if not cs:
            continue
        filas.append(fila(g, cs, 0))
        filas += [fila(nombre[c], [c], 2) for c in cs]
    total = fila("SECTOR MANUFACTURA", todas, 0)
    total["total"] = True
    filas.append(total)
    # serie para los gráficos: total, primaria y no primaria, y su var. % a 12 meses (los últimos 25 meses)
    serie = []
    for q in [x for x in periodos if x <= p]:
        q = int(q)
        punto = {"periodo": etiqueta(q), "p": f"{q // 100}-{q % 100:02d}"}
        for k, cs in (("total", todas), ("primaria", grupos[PRIMARIA]), ("no_primaria", grupos[NO_PRIMARIA])):
            v = ind(q, cs)
            punto[k] = v
            punto[f"var_{k}"] = _var(ind(q - 100, cs), v) if q - 100 in I.index else None
        serie.append(punto)
    return {"periodo": f"{a}-{m:02d}", "ultimo": f"{ultimo // 100}-{ultimo % 100:02d}", "anio": a, "comparar": a - 1, "mes": m,
            "titulo_mes": MESES[m - 1], "acumulado": "Enero" if m == 1 else f"Enero - {MESES[m - 1]}",
            "meses": [f"{int(q) // 100}-{int(q) % 100:02d}" for q in periodos], "departamento": DEPARTAMENTOS[depto],
            "cuadro": filas, "serie": serie, "serie_25": serie[-25:],
            "estructura_de": a - 1 if q_ant else None, "meses_estructura": len(q_ant)}


def excel(region, c):
    """El cuadro de la síntesis y la serie mensual en un Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Cuadro"
    neg, centro = Font(bold=True), Alignment(horizontal="center")
    a, b, mes = c["anio"], c["comparar"], c["titulo_mes"]
    ws.append([f"{region.upper()}: ÍNDICE DE VOLUMEN FÍSICO MANUFACTURERO 1/"])
    ws.append(["(Var. % real respecto a similar periodo del año anterior)"])
    ws.append([])
    ws.append(["Ramas de actividad", "Estructura porcentual", mes, None, c["acumulado"], None])
    ws.append([None, f"{c['estructura_de'] or b} 2/", "Var. %", "Contribución 3/", "Var. %", "Contribución 3/"])
    for f in c["cuadro"]:
        guion = lambda v: "-" if f["vacia"] or v is None else v
        ws.append([("   " * (f["nivel"] // 2)) + f["nombre"], f["estructura"], guion(f["var_mes"]), guion(f["contrib_mes"]),
                   guion(f["var_acum"]), guion(f["contrib_acum"])])
        if f["nivel"] == 0:
            for celda in ws[ws.max_row]:
                celda.font = neg
    ws.merge_cells("C4:D4"); ws.merge_cells("E4:F4")
    for fila in ws.iter_rows(min_row=6, min_col=2, max_col=6):
        for celda in fila:
            celda.number_format = "0.0"
            celda.alignment = Alignment(horizontal="right")
    for celda in ws[4] + ws[5]:
        celda.font, celda.alignment = neg, centro
    ws.append([])
    for t in ["1/ Cifras preliminares.", "2/ Estimado a precios de 2007.",
              "3/ Puntos porcentuales: var. % de la rama × su peso (ponderación 2007 × índice del año anterior).", FUENTE]:
        ws.append([t])
    ws["A1"].font = neg
    ws.column_dimensions["A"].width = 34
    wi = wb.create_sheet("Índices")
    wi.append([f"{region.upper()}: ÍNDICE DE VOLUMEN FÍSICO MANUFACTURERO (índices, 2007 = 100)"]); wi.append([])
    wi.append(["Ramas de actividad", f"{mes} {b}", f"{mes} {a}", f"{c['acumulado']} {b}", f"{c['acumulado']} {a}"])
    for f in c["cuadro"]:
        wi.append([("   " * (f["nivel"] // 2)) + f["nombre"], f["mes_b"], f["mes_a"], f["acum_b"], f["acum_a"]])
        for celda in wi[wi.max_row][1:]:
            celda.number_format = "0.0"
    wi.column_dimensions["A"].width = 34
    wg = wb.create_sheet("Serie")
    wg.append([f"{region.upper()}: ÍNDICE DE VOLUMEN FÍSICO MANUFACTURERO"])
    wg.append(["(Índice y var. % respecto a similar mes del año anterior)"])
    wg.append([])
    wg.append(["Mes", "Primaria", "No primaria", "Total", "Var. % primaria", "Var. % no primaria", "Var. % total"])
    for s in c["serie"]:
        wg.append([s["periodo"], s["primaria"], s["no_primaria"], s["total"], s["var_primaria"], s["var_no_primaria"], s["var_total"]])
    for fila in wg.iter_rows(min_row=5, min_col=2):
        for celda in fila:
            celda.number_format = "0.0"
    for celda in wg[4]:
        celda.font = neg
    wg["A1"].font = neg
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()
