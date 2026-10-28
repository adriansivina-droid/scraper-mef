"""Cuadros de pesca para la síntesis de cada región (sobre los LONG de las bases pesca-*):

  · producción pesquera: VBP (miles de soles de 2007) y volúmenes por estado, especie u origen, del mes y del
    acumulado Ene.-Mes de un año contra otro, con su variación %;
  · series del VBP de los dos años mes a mes y su variación interanual;
  · con los formatos de la sucursal (los Excel «Formato Cuadros …» de cada región): «Producción pesquera» de la
    síntesis (mes y Ene.-Mes, y la fila SECTOR PESCA con la variación del VBP a precios de 2007) y el Cuadro Nº 07 mes a
    mes con el total de cada año.
"""
import io

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from .pesca import ESPECIES_07, _clave

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
MESES_CORTOS = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Set.", "Oct.", "Nov.", "Dic."]
# Cuadro Nº 07, bloque «Desembarque fresco» (como ESPECIES_FRESCO del notebook de Loreto)
ESPECIES_FRESCO = ["Llambina", "Ractacara", "Boquichico", "Palometa", "Sardina", "Carachama", "Paiche", "Fasaco", "Acarahuazú",
                   "Sabálo", "Gamitana", "Chambira", "Paña", "Bagre", "Zungaro Doncella", "Lisa", "Mota", "Maparate", "Arahuana"]
FUENTE = {"pesca-loreto": "DIREPRO Loreto", "pesca-san-martin": "DIREPRO San Martín", "pesca-ucayali": "DIREPRO Ucayali"}


def etiqueta(p, corta=False):
    return f"{(MESES_CORTOS if corta else MESES)[p % 100 - 1]} {p // 100}"


def _var(a, b):
    return None if not a else round((b / a - 1) * 100, 1)


def _filas(base_id, df):
    """[(nombre, unidad, máscara, columna, nivel)] del cuadro de producción de cada región (nivel 0 = total)."""
    if base_id == "pesca-loreto":
        pez = df["ESTADO"] != "ORNAMENTAL"
        f = [("Valor bruto pesquero", "miles de S/ de 2007", df["VBP"].notna(), "VBP", 0),
             ("Desembarque total", "t", pez, "VOLUMEN", 0),
             ("Estado fresco", "t", df["ESTADO"] == "FRESCO", "VOLUMEN", 1),
             ("Estado seco salado", "t", df["ESTADO"] == "SECO SALADO", "VOLUMEN", 1),
             ("Estado salpreso", "t", df["ESTADO"] == "SALPRESO", "VOLUMEN", 1),
             ("Boquichico", "t", pez & (df["ESPECIE_CUADRO"] == "Boquichico"), "VOLUMEN", 1),
             ("Llambina/Palometa", "t", pez & (df["ESPECIE_CUADRO"] == "Llambina/Palometa"), "VOLUMEN", 1),
             ("Peces ornamentales vivos", "miles de unidades", ~pez, "VOLUMEN", 0)]
        return f
    if base_id == "pesca-san-martin":
        sm = df["DEPARTAMENTO"].astype(str).str.upper() == "SAN MARTÍN"
        f = [("Valor bruto pesquero", "miles de S/ de 2007", sm, "VBP", 0),
             ("Producción de San Martín", "t", sm, "VOLUMEN", 0)]
        f += [(o, "t", sm & (df["ORIGEN"] == o), "VOLUMEN", 1) for o in ("Acuicultura", "Extracción de ríos")]
        f += [(f"Estado {e.lower()}", "t", sm & (df["ESTADO_OK"] == e), "VOLUMEN", 1) for e in ("FRESCO", "SECO SALADO", "SALPRESO")]
        principales = df[sm & (df["ESPECIE_OK"] != "Otras")].groupby("ESPECIE_OK")["VOLUMEN"].sum().sort_values(ascending=False).index[:6]
        f += [(e, "t", sm & (df["ESPECIE_OK"] == e), "VOLUMEN", 1) for e in principales]
        f.append(("Llega de otros departamentos", "t", ~sm, "VOLUMEN", 0))
        return f
    fresco = df["TIPO"] == "FRESCO"
    f = [("Valor bruto pesquero", "miles de S/ de 2007", df["TIPO"].isin(["FRESCO", "SECO-SALADO"]), "VBP", 0),
         ("Desembarque de pescado", "t", df["TIPO"] == "AGREGADO", "VOLUMEN", 0),
         ("Fresco", "t", fresco, "VOLUMEN", 1), ("Seco-salado", "t", df["TIPO"] == "SECO-SALADO", "VOLUMEN", 1)]
    principales = df[fresco & (df["ESPECIES_OK"] != "Otros")].groupby("ESPECIES_OK")["VOLUMEN"].sum().sort_values(ascending=False).index[:6]
    f += [(f"{e} (fresco)", "t", fresco & (df["ESPECIES_OK"] == e), "VOLUMEN", 1) for e in principales]
    f.append(("Peces ornamentales", "unidades", df["TIPO"] == "ORNAMENTAL", "VOLUMEN", 0))
    return f


# ── Formatos de la sucursal: «Producción pesquera» de la síntesis y Cuadro Nº 07 (mes a mes, total de cada año) ──
LOR_FRESCO = ["Llambina", "Ractacara", "Boquichico", "Palometa", "Sardina"]
UCA_FRESCO = ["Bagre", "Ractacara", "Boquichico", "Palometa", "Chiu Chiu", "Sardina"]
SMN_ESPECIES = [("Tilapia", "Tilapia"), ("Gamitana", "Gamitana"), ("Camarón gigante", "Camarón gigante"), ("Paco", "Paco"),
                ("Paiche", "Paiche"), ("Boquichico", "Boquichico")]
DESTINOS = [("Mercado interno", "Mercado interno"), ("Mercado externo", "Mercado externo"),
            ("Stock remanente y/o mortandad", "Stock remanente y/o mortandad")]
ELABORACION = "Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos."


def _grupo(t, lista, cols, otro="Otras especies"):
    """Especie de la lista (por su nombre sin tildes, en la primera columna que coincida) o «Otras especies»."""
    claves = {_clave(e): e for e in lista}
    return [next((claves[_clave(v)] for v in fila if _clave(v) in claves), otro) for fila in zip(*[t[c] for c in cols])]


def formato(base_id, df):
    """Filas de los dos cuadros: [(nombre, sub-DataFrame o None si es un título, nivel)] y la máscara del VBP."""
    if base_id == "pesca-loreto":
        pez, orn = df[df["ESTADO"] != "ORNAMENTAL"], df[df["ESTADO"] == "ORNAMENTAL"]
        fre = pez[pez["ESTADO"] == "FRESCO"]
        g = pd.Series(_grupo(fre, LOR_FRESCO, ["ESPECIE_CORREGIDA", "ESPECIE_OK"]), index=fre.index)
        g07 = pd.Series(_grupo(fre, ESPECIES_FRESCO, ["ESPECIE_CORREGIDA", "ESPECIE_OK"]), index=fre.index)
        sint = ([("Consumo Humano (toneladas)", pez, 0), ("Fresco", fre, 1)] + [(e, fre[g == e], 2) for e in LOR_FRESCO + ["Otras especies"]]
                + [("Salpreso", pez[pez["ESTADO"] == "SALPRESO"], 1), ("Seco salado", pez[pez["ESTADO"] == "SECO SALADO"], 1),
                   ("Ornamentales (miles de unidades)", orn, 0)] + [(n, orn[orn["DESTINO"] == d], 1) for n, d in DESTINOS])
        c07 = ([("DESEMBARQUE (t.m.)", pez, 0)] + [(n, pez[pez["ESTADO"] == e], 1) for n, e in (("Fresco", "FRESCO"), ("Salpreso", "SALPRESO"), ("Seco-salado", "SECO SALADO"))]
               + [("TOTAL (t.m.)", pez, 0)] + [(e, pez[pez["ESPECIE_OK"] == e], 1) for e in ESPECIES_07]
               + [("Otros", pez[~pez["ESPECIE_OK"].isin(ESPECIES_07)], 1), ("PECES ORNAMENTALES 1/", orn, 0)]
               + [(n if n != "Stock remanente y/o mortandad" else "Stock Reman. y/o Mort.", orn[orn["DESTINO"] == d], 1) for n, d in DESTINOS]
               + [("Desembarque fresco", fre, 0)] + [(e, fre[g07 == e], 1) for e in ESPECIES_FRESCO + ["Otras especies"]])
        return {"titulo": "LORETO: PRODUCCIÓN PESQUERA 1/", "unidad": "(Toneladas y miles de unidades)", "filas": sint,
                "vbp": df, "pesca": "SECTOR PESCA 2/", "notas": ["1/ Cifras preliminares", "2/ Estimado a precios de 2007.", "Fuente: DIREPRO.", ELABORACION],
                "c07_titulo": "LORETO: INDICADORES DEL SECTOR PESQUERO", "c07_unidad": "(Toneladas métricas)", "c07": c07,
                "c07_notas": ["1/ Miles de unidades.", "Fuente: Dirección Regional Sectorial de la Producción - Loreto.", "* Información preliminar"]}
    if base_id == "pesca-san-martin":
        sm = df[df["DEPARTAMENTO"].astype(str).str.upper() == "SAN MARTÍN"]
        otros = df[df["DEPARTAMENTO"].astype(str).str.upper() != "SAN MARTÍN"]
        g = pd.Series(_grupo(sm, [e for e, _ in SMN_ESPECIES], ["ESPECIE_OK", "ESPECIE"]), index=sm.index)
        sint = [("Producción Interna", sm, 0), ("Fresco", sm, 1)] + [(n, sm[g == e], 2) for n, e in SMN_ESPECIES] + [("Otras especies", sm[g == "Otras especies"], 2)]
        c07 = ([("TOTAL", df, 0), ("INGRESO OTROS DPTOS. (CONTINENTAL)", otros, 0)]
               + [(n, otros[otros["ESTADO_OK"] == e], 1) for n, e in (("Fresco", "FRESCO"), ("Salpreso", "SALPRESO"), ("Seco-Salado", "SECO SALADO"))]
               + [("PRODUCCIÓN INTERNA (fresco + fresco refrigerado)", sm, 0), ("Acuicultura", sm[sm["ORIGEN"] == "Acuicultura"], 1),
                  ("Extracción río Huallaga", sm[sm["ORIGEN"] != "Acuicultura"], 1), ("Producción interna por especies:", sm, 0)]
               + [(n if e != "Boquichico" else "Boquichico (extracción)", sm[g == e], 1) for n, e in SMN_ESPECIES] + [("Otras", sm[g == "Otras especies"], 1)])
        return {"titulo": "SAN MARTÍN: PRODUCCIÓN PESQUERA 1/", "unidad": "(Toneladas)", "filas": sint, "vbp": sm, "pesca": "SECTOR PESCA 1/",
                "notas": ["1/ Estimado a precios de 2007. Cifras preliminares.", "Fuente: Dirección Regional Sectorial de la Producción - San Martín.", ELABORACION],
                "c07_titulo": "SAN MARTÍN: INDICADORES DEL SECTOR PESQUERO", "c07_unidad": "(Toneladas métricas)", "c07": c07,
                "c07_notas": ["Fuente: Dirección Regional Sectorial de la Producción - San Martín."]}
    fre, seco = df[df["TIPO"] == "FRESCO"], df[df["TIPO"] == "SECO-SALADO"]
    agr, orn, consumo = df[df["TIPO"] == "AGREGADO"], df[df["TIPO"] == "ORNAMENTAL"], df[df["TIPO"].isin(["FRESCO", "SECO-SALADO"])]
    g = pd.Series(_grupo(fre, UCA_FRESCO, ["ESPECIES_OK", "ESPECIES_CORREGIDO"]), index=fre.index)
    otro = agr["ESPECIES_CORREGIDO"].map(_clave).isin(["otros", "otrasespecies"])
    especies = sorted(set(agr.loc[~otro, "ESPECIES_CORREGIDO"]), key=_clave)
    sint = ([("Consumo Humano", consumo, 0), ("Fresco", fre, 1)] + [(e, fre[g == e], 2) for e in UCA_FRESCO + ["Otras especies"]]
            + [("Seco salado", seco, 1)])
    c07 = ([("TOTAL", consumo, 0), ("Fresco", fre, 1), ("Seco-Salado", seco, 1), ("TOTAL 1/", agr if not agr.empty else consumo, 0)]
           + [(e, agr[agr["ESPECIES_CORREGIDO"] == e], 1) for e in especies] + [("Otros", agr[otro], 1),
              ("PECES ORNAMENTALES (unidades)", orn, 0), ("Desembarque fresco", None, 0)]
           + [(e, fre[g == e], 1) for e in UCA_FRESCO + ["Otras especies"]] + [("TOTAL", fre, 0)])
    return {"titulo": "UCAYALI: PRODUCCIÓN PESQUERA 1/", "unidad": "(Toneladas)", "filas": sint, "vbp": consumo, "pesca": "SECTOR PESCA 2/",
            "notas": ["1/ Cifras preliminares.", "2/ Estimado a precios de 2007.", "Fuente: DIREPRO.", ELABORACION],
            "c07_titulo": "UCAYALI: DESEMBARQUE DE PESCADO PARA CONSUMO HUMANO", "c07_unidad": "(Toneladas métricas)", "c07": c07,
            "c07_notas": ["Fuente: Dirección Regional de la Producción - Ucayali.", "1/ Incluye pescado fresco y seco-salado."]}


def _sintesis(f, ventanas):
    def fila(nombre, t, nivel, col="VOLUMEN"):
        v = {w: float(t.loc[t["P"].isin(ps), col].sum()) for w, ps in ventanas.items()}
        return {"nombre": nombre, "nivel": nivel, **{w: round(x, 3) for w, x in v.items()},
                "var_mes": _var(v["mes_b"], v["mes_a"]), "var_acum": _var(v["acum_b"], v["acum_a"])}
    filas = [fila(n, t, nv) for n, t, nv in f["filas"]]
    pesca = fila(f["pesca"], f["vbp"], 0, "VBP")
    filas.append({"nombre": f["pesca"], "nivel": 0, "solo_var": True, "var_mes": pesca["var_mes"], "var_acum": pesca["var_acum"]})
    return {"titulo": f["titulo"], "unidad": f["unidad"], "notas": f["notas"], "filas": filas}


def _cuadro_07(f, anios, hasta):
    """Cuadro Nº 07 mes a mes (hasta el mes del informe) con el total de cada año."""
    todos = pd.concat([t for _, t, _ in f["c07"] if t is not None])
    hay = set(todos.loc[todos["P"] <= hasta, "P"])
    columnas = [(a, m) for a in anios for m in range(1, 13) if a * 100 + m in hay]
    filas = []
    for nombre, t, nivel in f["c07"]:
        if t is None:
            filas.append({"nombre": nombre, "nivel": nivel, "titulo": True})
            continue
        g = t[t["P"] <= hasta].groupby("P")["VOLUMEN"].sum()
        filas.append({"nombre": nombre, "nivel": nivel, "meses": [round(float(g.get(a * 100 + m, 0)), 3) for a, m in columnas],
                      "totales": {str(a): round(float(g[(g.index // 100) == a].sum()), 3) for a in anios}})
    return {"titulo": f["c07_titulo"], "unidad": f["c07_unidad"], "notas": f["c07_notas"], "anios": [str(a) for a in anios],
            "columnas": [f"{MESES_CORTOS[m - 1]} {a}" for a, m in columnas], "anio_de_columna": [str(a) for a, _ in columnas], "filas": filas}


def cuadros(base_id, df, periodo=None, comparar=None):
    if df.empty:
        return None
    df = df.assign(P=df["AÑO"].astype(int) * 100 + df["MES"].astype(int))
    df["VOLUMEN"] = pd.to_numeric(df["VOLUMEN"], errors="coerce").fillna(0)
    df["VBP"] = pd.to_numeric(df["VBP"], errors="coerce").fillna(0)
    periodos = sorted(set(df["P"]))
    ultimo = periodos[-1]
    p = int(periodo.replace("-", "")) if periodo else ultimo
    if p not in periodos:
        raise ValueError(f"No hay datos de pesca de {etiqueta(p)} (último mes: {etiqueta(ultimo)}).")
    a, m = p // 100, p % 100
    b = int(comparar) if comparar else a - 1
    if b >= a:
        raise ValueError(f"El año de comparación ({b}) debe ser anterior a {a}.")
    pb = b * 100 + m
    ventanas = {"mes_b": [pb], "mes_a": [p], "acum_b": list(range(b * 100 + 1, pb + 1)), "acum_a": list(range(a * 100 + 1, p + 1))}
    filas = []
    for nombre, unidad, mascara, col, nivel in _filas(base_id, df):
        t = df[mascara]
        v = {w: float(t.loc[t["P"].isin(ps), col].sum()) for w, ps in ventanas.items()}
        filas.append({"nombre": nombre, "unidad": unidad, "nivel": nivel, **{w: round(x, 3) for w, x in v.items()},
                      "var_mes": _var(v["mes_b"], v["mes_a"]), "var_acum": _var(v["acum_b"], v["acum_a"])})
    vbp = df[_filas(base_id, df)[0][2]].groupby("P")["VBP"].sum()
    serie = lambda anio: [round(float(vbp[anio * 100 + k]), 3) if anio * 100 + k in vbp.index else None for k in range(1, 13)]
    interanual = [{"periodo": etiqueta(q, True), "var": _var(float(vbp[q - 100]), float(vbp[q])) if q - 100 in vbp.index else None}
                  for q in [x for x in periodos if x <= p][-25:]]
    salida = {"periodo": f"{a}-{m:02d}", "ultimo": f"{ultimo // 100}-{ultimo % 100:02d}", "anio": a, "comparar": b,
              "titulo_mes": MESES[m - 1], "anios": sorted({q // 100 for q in periodos}), "filas": filas,
              "mensual": {"meses": MESES_CORTOS, "a": serie(a), "b": serie(b)}, "interanual": interanual, "fuente": FUENTE[base_id]}
    f = formato(base_id, df)
    salida["sintesis"] = _sintesis(f, ventanas)
    salida["cuadro_07"] = _cuadro_07(f, sorted({b, a}), p)
    salida["_formato"] = (f, p)                          # para el Excel (toda la historia del Cuadro Nº 07); no va al JSON
    return salida


def excel(region, c):
    wb = Workbook()
    neg, centro = Font(bold=True), Alignment(horizontal="center")
    a, b, mes = c["anio"], c["comparar"], c["titulo_mes"]
    ws = wb.active
    ws.title = "Producción"
    ws.append([f"{region.upper()}: PRODUCCIÓN PESQUERA"]); ws.append([])
    ws.append(["", "Unidad", f"{mes} {b}", f"{mes} {a}", "Var. %", f"Ene.-{mes[:3]}. {b}", f"Ene.-{mes[:3]}. {a}", "Var. %"])
    for x in ws[3]:
        x.font, x.alignment = neg, centro
    for f in c["filas"]:
        ws.append([("   " * f["nivel"]) + f["nombre"], f["unidad"], f["mes_b"], f["mes_a"], f["var_mes"], f["acum_b"], f["acum_a"], f["var_acum"]])
        for i, x in enumerate(ws[ws.max_row]):
            x.number_format = "0.0" if i in (4, 7) else "#,##0.0"
            if f["nivel"] == 0:
                x.font = neg
    ws.append([]); ws.append([f"Fuente: {c['fuente']}. Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos."])
    ws["A1"].font = neg
    ws.column_dimensions["A"].width = 40; ws.column_dimensions["B"].width = 20
    _excel_formatos(wb, c, neg, centro)
    wm = wb.create_sheet("VBP mensual")
    wm.append([f"{region.upper()}: VALOR BRUTO PESQUERO (miles de S/ de 2007)"]); wm.append([]); wm.append(["Mes", str(b), str(a)])
    for i, k in enumerate(c["mensual"]["meses"]):
        wm.append([k, c["mensual"]["b"][i], c["mensual"]["a"][i]])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _excel_formatos(wb, c, neg, centro):
    """Las dos hojas con el formato de la sucursal: «Producción pesquera» (síntesis) y «Cuadro 07» (toda la historia)."""
    a, b, mes, m = c["anio"], c["comparar"], c["titulo_mes"], int(c["periodo"][5:])
    st = c["sintesis"]
    ws = wb.create_sheet("Producción pesquera", 0)
    for fila in (["Mes", mes, m], ["Año t", a], ["Año t-1", b], ["Acumulado", f"Enero - {mes}"], [], [],
                 ["", st["titulo"]], ["", st["unidad"]], [],
                 ["", "", mes, "", "Var. %", f"Enero - {mes}", "", "Var. %"], ["", "", b, a, "", b, a, ""]):
        ws.append(fila)
    for fila in (10, 11):
        for x in ws[fila]:
            x.font, x.alignment = neg, centro
    ws.append([])                                       # como en el formato: los datos empiezan en la fila 13
    for f in st["filas"]:
        nombre = ("   " * f["nivel"]) + f["nombre"]
        if f.get("solo_var"):
            ws.append(["", nombre, None, None, f["var_mes"], None, None, f["var_acum"]])
        else:
            ws.append(["", nombre, round(f["mes_b"]), round(f["mes_a"]), f["var_mes"], round(f["acum_b"]), round(f["acum_a"]), f["var_acum"]])
        for i, x in enumerate(ws[ws.max_row]):
            x.number_format = "0.0" if i in (4, 7) else "#,##0"
            if f["nivel"] < 2:
                x.font = neg
    for t in st["notas"]:
        ws.append(["", t])
    ws.column_dimensions["B"].width = 34
    fp = c.get("_formato")
    if not fp:
        return
    f, p = fp
    anios = sorted({int(x) // 100 for x in pd.concat([t for _, t, _ in f["c07"] if t is not None])["P"]})
    todo = _cuadro_07(f, anios, p)
    w7 = wb.create_sheet("Cuadro 07", 1)
    w7.append(["Cuadro N° 07"]); w7.append([todo["titulo"]]); w7.append([todo["unidad"]])
    cab_anio, cab_mes = [""], [""]
    for anio in todo["anios"]:
        meses = [col.split(" ")[0] for col, x in zip(todo["columnas"], todo["anio_de_columna"]) if x == anio]
        cab_anio += [int(anio)] + [""] * (len(meses) - 1) + ["Total"]
        cab_mes += meses + [int(anio)]
    w7.append(cab_anio); w7.append(cab_mes)
    for x in list(w7[4]) + list(w7[5]):
        x.font, x.alignment = neg, centro
    for fl in todo["filas"]:
        if fl.get("titulo"):
            w7.append([fl["nombre"]]); w7.cell(w7.max_row, 1).font = neg
            continue
        fila = [("  " * fl["nivel"]) + fl["nombre"]]
        for anio in todo["anios"]:
            fila += [round(v) for v, x in zip(fl["meses"], todo["anio_de_columna"]) if x == anio] + [round(fl["totales"][anio])]
        w7.append(fila)
        if fl["nivel"] == 0:
            for x in w7[w7.max_row]:
                x.font = neg
    for t in todo["notas"]:
        w7.append([t])
    w7.column_dimensions["A"].width = 44
    w7.freeze_panes = "B6"
