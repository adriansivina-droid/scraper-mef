"""Reporte de situación hídrica · Zona Oriente (Loreto, San Martín, Ucayali), con el formato del de la Sucursal Piura.

Arma, con los datos de SENAMHI guardados en la página, dos archivos que van juntos:
- un Excel con una hoja por gráfico: los datos en columnas (un año hidrológico por columna) y el gráfico de Excel que los usa;
  la hoja «Resumen» calcula con fórmulas el último dato, las diferencias y la alerta. Si se cambian los datos, cambian los gráficos;
- un PowerPoint con los mismos gráficos (gráficos de PowerPoint, editables: clic derecho → Editar datos) y los textos del día.

Diapositivas: portada · situación de hoy · Loreto (2) · San Martín · Ucayali · nivel diario del mes por año · caudales.
"""
import io
import re
from datetime import date, timedelta
from pathlib import Path

import xlsxwriter
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_MARK
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from . import hidrologia

BANNER = Path(__file__).parent / "plantillas" / "bcrp_banner.png"
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]
MES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
REGION = {"16": "Loreto", "22": "San Martín", "25": "Ucayali"}
CORTO = {"16": "LOR", "22": "SMN", "25": "UCA"}
# estaciones principales, en el orden en que salen (las demás de la región van después, por nombre)
PRIORIDAD = {"16": ["240102", "240001", "240111", "221402", "250101", "230602", "220105", "240103", "220107", "230603", "251102", "240005"],
             "22": ["230715", "212600", "221804", "221801", "210006"],
             "25": ["240504", "250103", "231201", "251105", "231101"]}
CAUDAL_PRIMERO = ["240103", "220105", "220107", "240111"]           # Amazonas (Tamshiyacu), Marañón (San Regis, Borja), Napo
CIUDAD = {"240102": "Iquitos", "240001": "Iquitos", "240111": "Mazán", "240103": "Iquitos", "221402": "Nauta", "250101": "Requena",
          "230602": "Yurimaguas", "220105": "Loreto", "220107": "Datem del Marañón", "230603": "Lagunas", "251102": "Contamana",
          "240005": "Ramón Castilla", "240504": "Pucallpa", "230715": "Picota"}
# colores: el año en curso oscuro, los anteriores más claros; promedio verde; umbrales como SENAMHI
C_AÑOS = ["1F3864", "5B9BD5", "A5A5A5", "C55A11"]
C_PROM, C_AMA, C_NAR, C_ROJ = "70AD47", "E8C700", "ED7D31", "C00000"
FILL_ALERTA = {"roja": "FF0000", "naranja": "FFA500", "amarilla": "FFFF00", "normal": "E2EFDA", "sin umbral": "F2F2F2"}
NAVY, GRIS, TX2 = RGBColor(0x1F, 0x38, 0x64), RGBColor(0x59, 0x59, 0x59), RGBColor(0x44, 0x54, 0x6A)


# ── utilidades ───────────────────────────────────────────────────────────────
def coma(v, d=2):
    """110.5 → «110,50» (como en la síntesis: coma decimal y espacio de miles)."""
    if v is None:
        return "—"
    t = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("-" if v < 0 else "") + t


def signo(v, d=2):
    return "—" if v is None else ("+" if v > 0 else "") + coma(v, d)


def fecha_larga(d):
    return f"{d.day} de {MES_LARGO[d.month - 1]}"


def titulo(t):
    t = str(t or "").lower()
    t = re.sub(r"(^|[\s(/-])(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
    return re.sub(r" (De|Del|La|Los|Las|El|Y) ", lambda m: m.group(0).lower(), t).replace("Dhn", "DHN").replace("Lpo", "LPO").replace("Ird", "IRD")


def rio_corto(r):
    return titulo(str(r).replace("RÍO ", "").replace("RIO ", ""))


def alerta(valor, rojo, naranja, amarillo):
    """«roja», «naranja», «amarilla», «normal» o «sin umbral»; y si los umbrales son de nivel bajo (vaciante)."""
    if valor is None or rojo is None:
        return "sin umbral", None
    otro = amarillo if amarillo is not None else naranja
    baja = otro is not None and rojo < otro
    pasa = (lambda t: t is not None and valor <= t) if baja else (lambda t: t is not None and valor >= t)
    return ("roja" if pasa(rojo) else "naranja" if pasa(naranja) else "amarilla" if pasa(amarillo) else "normal"), baja


# eje del hidrograma: 1 de setiembre a 31 de agosto (365 días; el 29 de febrero se deja fuera para que las líneas no se corten)
EJE = [d for d in (date(2023, 9, 1) + timedelta(days=i) for i in range(366)) if (d.month, d.day) != (2, 29)]
ETQ_DIA = [f"{d.day:02d}-{MES[d.month - 1]}" for d in EJE]
ETQ_EJE = [MES[d.month - 1].capitalize() if d.day == 1 else "" for d in EJE]


def _al_eje(s, clave):
    """Una serie de hidrologia.anios() (366 días, con 29/2) llevada al eje de 365. «clave»: un año («2026») o promedio/umbral."""
    por = {}
    base = date.fromisoformat(s["desde"])
    for i, v in enumerate(s["años"][clave] if clave in s["años"] else s[clave]):
        d = base + timedelta(days=i)
        por[(d.month, d.day)] = v
    return [por.get((d.month, d.day)) for d in EJE]


def pos_en_eje(d):
    return next((i for i, x in enumerate(EJE) if (x.month, x.day) == (d.month, d.day)), None)


# ── datos ────────────────────────────────────────────────────────────────────
def _estacion(e, variable, años_max=3):
    """Hidrograma y último dato de una estación, para una variable."""
    s = hidrologia.anios(e["codigo"], variable)
    v = e["variables"].get(variable) or {}
    u = v.get("ultimo") or {}
    if not s or not u.get("fecha"):
        return None
    f = date.fromisoformat(u["fecha"])
    ah = hidrologia.año_hidrologico(f)
    años = [y for y in sorted((int(y) for y in s["años"]), reverse=True) if y <= ah][:años_max]
    series = {y: _al_eje(s, str(y)) for y in años}
    i = pos_en_eje(f)
    hace7 = None
    if i is not None:
        j = i - 7
        hace7 = series[ah][j] if j >= 0 and ah in series else (series.get(ah - 1) or [None] * 365)[j] if j < 0 else None
    umb = {k: _al_eje(s, k) for k in ("promedio", "rojo", "naranja", "amarillo")}
    ult_umb = {k: next((x for x in reversed(umb[k]) if x is not None), None) for k in ("rojo", "naranja", "amarillo")}
    nivel, baja = alerta(u.get("valor"), ult_umb["rojo"], ult_umb["naranja"], ult_umb["amarillo"])
    return {"codigo": e["codigo"], "estacion": titulo(e["estacion"]), "rio": rio_corto(e["rio"]), "ciudad": CIUDAD.get(e["codigo"], ""),
            "seguro": e.get("departamento_seguro", True) or e.get("zonal") in ("08", "09"), "variable": variable, "unidad": v.get("unidad", ""), "fecha": f, "ah": ah,
            "valor": u.get("valor"), "hace7": hace7, "anterior": u.get("anterior"), "promedio": u.get("promedio"), **ult_umb,
            "alerta": nivel, "baja": baja, "años": años, "series": series, "umbrales": umb, "i": i}


def _ordenar(depto, estaciones):
    pr = PRIORIDAD.get(depto, [])
    return sorted(estaciones, key=lambda e: (pr.index(e["codigo"]) if e["codigo"] in pr else 99, e["rio"], e["estacion"]))


def datos():
    """Todo lo que usan el Excel y el PowerPoint. None si no hay datos de SENAMHI."""
    if not hidrologia.hay_datos():
        return None
    regiones = {}
    for depto in REGION:
        lista = []
        for e in _ordenar(depto, hidrologia.estaciones_de(depto)):
            x = _estacion(e, "NIVEL") if "NIVEL" in e["variables"] else None
            if x:
                x["depto"] = depto
                lista.append(x)
        regiones[depto] = lista
    caudales = []
    for depto in REGION:
        for e in sorted(_ordenar(depto, hidrologia.estaciones_de(depto)), key=lambda e: CAUDAL_PRIMERO.index(e["codigo"]) if e["codigo"] in CAUDAL_PRIMERO else 99):
            if "CAUDAL" in e["variables"]:
                x = _estacion(e, "CAUDAL")
                if x:
                    x["depto"] = depto
                    caudales.append(x)
    todas = [x for l in regiones.values() for x in l]
    if not todas:
        return None
    hoy = max(x["fecha"] for x in todas)
    return {"fecha": hoy, "regiones": regiones, "caudales": caudales[:2], "recolectado": hidrologia.estado().get("recolectado", "")}


# ── textos del día ───────────────────────────────────────────────────────────
NOM_ALERTA = {"roja": "roja", "naranja": "naranja", "amarilla": "amarilla"}


def _frase_estacion(x):
    partes = [f"el río {x['rio']} en {x['estacion']}{' (' + x['ciudad'] + ')' if x['ciudad'] and x['ciudad'] not in x['estacion'] else ''} registra "
              f"{coma(x['valor'])} {x['unidad']}"]
    if x["hace7"] is not None:
        d = x["valor"] - x["hace7"]
        partes.append(f"{'sube' if d > 0 else 'baja'} {coma(abs(d))} m en la última semana" if abs(d) >= 0.005 else "sin cambio en la última semana")
    if x["promedio"] is not None:
        d = x["valor"] - x["promedio"]
        partes.append(f"{coma(abs(d))} m {'por encima' if d > 0 else 'por debajo'} de su promedio histórico")
    return ", ".join(partes)


def _alertas(lista):
    al = [x for x in lista if x["alerta"] in NOM_ALERTA]
    if not al:
        return ""
    tx = "; ".join(f"{x['rio']} en {x['estacion']} ({NOM_ALERTA[x['alerta']]}{', nivel bajo' if x['baja'] else ', crecida'})" for x in al)
    return f" En alerta: {tx}."


def mensaje_resumen(D):
    todas = [x for l in D["regiones"].values() for x in l]
    con = [x for x in todas if x["alerta"] != "sin umbral"]
    al = [x for x in con if x["alerta"] in NOM_ALERTA]
    bajas = sum(1 for x in al if x["baja"])
    neg = f"Al {fecha_larga(D['fecha'])}, {len(al)} de {len(con)} estaciones con umbral del Oriente presentan alerta"
    if al:
        neg += f" ({bajas} por nivel bajo y {len(al) - bajas} por crecida)." if bajas and len(al) - bajas else (" por nivel bajo (vaciante)." if bajas else " por crecida.")
    else:
        neg += "."
    rojas = [x for x in al if x["alerta"] == "roja"]
    extra = (" Alerta roja en " + ", ".join(f"el {x['rio']} ({x['estacion']})" for x in rojas) + ".") if rojas else ""
    return neg, extra


def mensaje_region(depto, lista):
    if not lista:
        return f"{REGION[depto]}: SENAMHI no tiene estaciones con datos en la región.", ""
    neg = f"{REGION[depto]}: {_frase_estacion(lista[0])}."
    neg = neg[0] + neg[1:]
    return neg, _alertas(lista)


# ── Excel ────────────────────────────────────────────────────────────────────
def _nombre_hoja(t, usados):
    t = re.sub(r"[\[\]:*?/\\]", "", t)[:31]
    base, k = t, 2
    while t in usados:
        t = f"{base[:28]} {k}"
        k += 1
    usados.add(t)
    return t


def excel(D, ejemplo=False):
    """El libro de Excel: Índice, Resumen (con fórmulas), una hoja por hidrograma, la tabla diaria y los caudales."""
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"title": "Reporte de situación hídrica - Zona Oriente", "company": "BCRP - Sucursal Iquitos", "comments": "Fuente: SENAMHI"})
    F = lambda **k: wb.add_format({"font_name": "Arial", "font_size": 9, **k})        # noqa: E731
    f_tit, f_sub = F(bold=True, font_size=12, font_color="#1F3864"), F(italic=True, font_color="#595959")
    f_cab = F(bold=True, bg_color="#1F3864", font_color="#FFFFFF", border=1, align="center", valign="vcenter", text_wrap=True)
    f_num, f_num1, f_txt = F(num_format="0.00", border=1), F(num_format="#,##0", border=1), F(border=1)
    f_dif = F(num_format="+0.00;-0.00;0.00", border=1)
    f_fecha = F(num_format="dd/mm/yyyy", border=1, align="center")
    f_nota = F(font_size=8, italic=True, font_color="#595959")
    f_ej = F(bold=True, font_color="#C00000", font_size=11)
    usados, hojas = {"Índice", "Resumen", "Tabla diaria"}, {}

    ind = wb.add_worksheet("Índice")
    res = wb.add_worksheet("Resumen")
    ind.set_column("A:A", 4); ind.set_column("B:B", 34); ind.set_column("C:C", 80)
    ind.write("B2", "REPORTE DE SITUACIÓN HÍDRICA · ZONA ORIENTE", f_tit)
    ind.write("B3", f"Loreto, San Martín y Ucayali · datos de SENAMHI al {D['fecha']:%d/%m/%Y}", f_sub)
    if ejemplo:
        ind.write("B4", "EJEMPLO CON DATOS ILUSTRATIVOS: genera el real desde la página (Perú → Ríos del Perú → Descargar datos).", f_ej)
    ind.write_row("B6", ["Hoja", "Qué tiene / en qué diapositiva va"], f_cab)
    filas_ind = [("Resumen", "Último dato de cada estación, diferencias y alerta (fórmulas). Diapositiva 2.")]

    # hojas de hidrogramas
    def hoja_hidrograma(x, etiqueta):
        nom = _nombre_hoja(etiqueta, usados)
        ws = wb.add_worksheet(nom)
        hojas[(x["codigo"], x["variable"])] = nom
        ws.set_column("A:A", 9); ws.set_column("B:B", 6); ws.set_column("C:J", 10)
        ws.write("A1", f"{'Nivel' if x['variable'] == 'NIVEL' else 'Caudal'} del río {x['rio']} · estación {x['estacion']} ({x['unidad']})", f_tit)
        cols = [f"{y}-{str(y + 1)[2:]}" for y in x["años"]] + ["Prom. histórico", "Amarillo", "Naranja", "Rojo"]
        ws.write_row(2, 0, ["Día", "Eje"] + cols, f_cab)
        ws.set_row(2, 28)
        serie = [x["series"][y] for y in x["años"]] + [x["umbrales"][k] for k in ("promedio", "amarillo", "naranja", "rojo")]
        fmt = f_num1 if x["variable"] == "CAUDAL" else f_num
        for r, (dia, eje) in enumerate(zip(ETQ_DIA, ETQ_EJE)):
            ws.write_string(3 + r, 0, dia, f_txt)
            ws.write_string(3 + r, 1, eje, f_txt)
            for c, s in enumerate(serie):
                if s[r] is not None:
                    ws.write_number(3 + r, 2 + c, s[r], fmt)
                else:
                    ws.write_blank(3 + r, 2 + c, None, fmt)
        ws.freeze_panes(3, 2)
        ult = 3 + len(EJE) - 1
        ch = wb.add_chart({"type": "line"})
        estilos = [(C_AÑOS[k % 4], 2.25 if k == 0 else 1.5, "solid") for k in range(len(x["años"]))] + \
                  [(C_PROM, 1.5, "dash"), (C_AMA, 1.25, "long_dash"), (C_NAR, 1.25, "long_dash"), (C_ROJ, 1.25, "long_dash")]
        for c, (color, ancho, guion) in enumerate(estilos):
            if not any(v is not None for v in serie[c]):
                continue
            ch.add_series({"name": [nom, 2, 2 + c], "categories": [nom, 3, 1, ult, 1], "values": [nom, 3, 2 + c, ult, 2 + c],
                           "line": {"color": "#" + color, "width": ancho, "dash_type": guion}, "marker": {"type": "none"}})
        todos = [v for s in serie for v in s if v is not None]
        lo, hi, paso = _escala(todos)
        ch.set_title({"name": f"{'Nivel' if x['variable'] == 'NIVEL' else 'Caudal'} del río {x['rio']}, estación {x['estacion']}",
                      "name_font": {"name": "Arial", "size": 11, "bold": True}})
        ch.set_x_axis({"num_font": {"name": "Arial", "size": 8}, "interval_unit": 1, "major_tick_mark": "none", "line": {"color": "#BFBFBF"}})
        ch.set_y_axis({"name": x["unidad"], "name_font": {"name": "Arial", "size": 8, "bold": False}, "num_font": {"name": "Arial", "size": 8},
                       "min": lo, "max": hi, "major_unit": paso,
                       "major_gridlines": {"visible": True, "line": {"color": "#E7E6E6"}}, "num_format": "#,##0" if x["variable"] == "CAUDAL" else "0.0"})
        ch.set_legend({"position": "bottom", "font": {"name": "Arial", "size": 8}})
        ch.show_blanks_as("gap")
        ch.set_size({"width": 720, "height": 340})
        ch.set_chartarea({"border": {"none": True}})
        ws.insert_chart(2, 2 + len(serie) + 1, ch)                  # a la derecha de los datos, sin taparlos
        ws.write(len(EJE) + 4, 0, "Fuente: SENAMHI. Cada columna es un año hidrológico (1 de setiembre a 31 de agosto). Escribe o pega los datos nuevos en la columna del año en curso: el gráfico se actualiza solo.", f_nota)
        return nom

    for depto, lista in D["regiones"].items():
        for x in lista[:8 if depto == "16" else 4]:
            nom = hoja_hidrograma(x, f"{CORTO[depto]} {x['rio']} {x['estacion']}")
            filas_ind.append((nom, f"Hidrograma del río {x['rio']} en {x['estacion']} ({REGION[depto]})."))
    for x in D["caudales"]:
        nom = hoja_hidrograma(x, f"Caudal {x['rio']} {x['estacion']}")
        filas_ind.append((nom, f"Caudal del río {x['rio']} en {x['estacion']}. Diapositiva de caudales."))

    # resumen con fórmulas (el último dato y las diferencias salen de las hojas de cada estación)
    res.set_column("A:A", 11); res.set_column("B:C", 20); res.set_column("D:D", 11); res.set_column("E:L", 11); res.set_column("M:M", 14)
    res.write("A1", "Situación de los principales ríos del Oriente", f_tit)
    res.write("A2", f"(nivel en m.s.n.m., al {D['fecha']:%d/%m/%Y})", f_sub)
    cab = ["Región", "Río", "Estación", "Fecha", "Nivel", "Hace 7 días", "Var. 7 días", "Año anterior", "Var. anual", "Prom. histórico",
           "Dif. vs prom.", "Umbral rojo", "Alerta"]
    res.write_row(3, 0, cab, f_cab); res.set_row(3, 28)
    r = 4
    for depto, lista in D["regiones"].items():
        for x in lista:
            hoja = hojas.get((x["codigo"], "NIVEL"))
            res.write(r, 0, REGION[depto], f_txt); res.write(r, 1, x["rio"], f_txt); res.write(r, 2, x["estacion"] + ("" if x["seguro"] else " *"), f_txt)
            res.write_datetime(r, 3, _dt(x["fecha"]), f_fecha)
            fila = 3 + x["i"] + 1 if x["i"] is not None else None              # fila (1 = primera) del día en la hoja de la estación
            col = "C"                                                          # el año en curso es la primera columna de años
            if hoja and fila:
                q = f"'{hoja}'"
                res.write_formula(r, 4, f"={q}!{col}{fila}", f_num, x["valor"])
                if x["hace7"] is not None and x["i"] >= 7:
                    res.write_formula(r, 5, f"={q}!{col}{fila - 7}", f_num, x["hace7"])
                else:
                    _num(res, r, 5, x["hace7"], f_num)
                if len(x["años"]) > 1:
                    res.write_formula(r, 7, f"={q}!D{fila}", f_num, x["anterior"])
                else:
                    _num(res, r, 7, x["anterior"], f_num)
                pc = chr(ord("C") + len(x["años"]))                            # columna del promedio
                res.write_formula(r, 9, f"={q}!{pc}{fila}", f_num, x["promedio"])
                rc = chr(ord(pc) + 3)
                res.write_formula(r, 11, f"=IF({q}!{rc}{fila}=\"\",\"\",{q}!{rc}{fila})", f_num, x["rojo"] if x["rojo"] is not None else "")
            else:
                for c, k in ((4, "valor"), (5, "hace7"), (7, "anterior"), (9, "promedio"), (11, "rojo")):
                    _num(res, r, c, x[k], f_num)
            fr = r + 1
            res.write_formula(r, 6, f'=IF(OR(E{fr}="",F{fr}=""),"",E{fr}-F{fr})', f_dif, _dif(x["valor"], x["hace7"]))
            res.write_formula(r, 8, f'=IF(OR(E{fr}="",H{fr}=""),"",E{fr}-H{fr})', f_dif, _dif(x["valor"], x["anterior"]))
            res.write_formula(r, 10, f'=IF(OR(E{fr}="",J{fr}=""),"",E{fr}-J{fr})', f_dif, _dif(x["valor"], x["promedio"]))
            res.write(r, 12, x["alerta"].capitalize() + ("" if x["alerta"] in ("normal", "sin umbral") else " (bajo)" if x["baja"] else " (crecida)"), F(border=1, bg_color="#" + FILL_ALERTA[x["alerta"]], bold=x["alerta"] == "roja", font_color="#FFFFFF" if x["alerta"] == "roja" else "#000000"))
            r += 1
    res.write(r + 1, 0, "Fuente: SENAMHI. Las columnas Nivel, Hace 7 días, Año anterior, Prom. histórico y Umbral rojo toman el dato de la hoja de cada estación; las variaciones se calculan aquí.", f_nota)
    res.write(r + 2, 0, "La alerta es la que corresponde a los umbrales de SENAMHI: en unas estaciones avisan de nivel bajo (vaciante) y en otras de crecida. * Sin departamento en SENAMHI: se incluye por su dirección zonal.", f_nota)
    res.freeze_panes(4, 3)

    # tabla diaria del mes (como la de caudales del reporte de Piura)
    td = wb.add_worksheet("Tabla diaria")
    T = tabla_diaria(D)
    td.write("A1", f"Nivel diario de los principales ríos del Oriente, 1 al {D['fecha'].day} de {MES_LARGO[D['fecha'].month - 1]} (m.s.n.m.)", f_tit)
    td.set_column("A:A", 7); td.set_column(1, 1 + len(T["columnas"]), 8)
    c = 1
    for est, años in T["grupos"]:
        if len(años) > 1:
            td.merge_range(2, c, 2, c + len(años) - 1, est, f_cab)
        else:
            td.write(2, c, est, f_cab)
        c += len(años)
    td.write_row(3, 0, ["Día"] + [str(T["año_cal"](a)) for _, años in T["grupos"] for a in años], f_cab)
    for i, fila in enumerate(T["filas"]):
        td.write(4 + i, 0, fila[0], f_txt)
        for j, v in enumerate(fila[1:]):
            _num(td, 4 + i, 1 + j, v, f_num)
    base = 4 + len(T["filas"])
    for k, (nombre, color) in enumerate((("Umbral amarillo", "#FFFF00"), ("Umbral naranja", "#FFA500"), ("Umbral rojo", "#FF0000"))):
        td.write(base + k, 0, nombre, F(border=1, bg_color=color, bold=True))
        c = 1
        for (est, años), u in zip(T["grupos"], T["umbrales"]):
            v = u[k]
            if len(años) > 1:
                td.merge_range(base + k, c, base + k, c + len(años) - 1, "" if v is None else v, F(num_format="0.00", border=1, align="center"))
            else:
                _num(td, base + k, c, v, f_num)
            c += len(años)
    td.write(base + 4, 0, "Fuente: SENAMHI. Dato diario (promedio del mínimo y el máximo del día). «—»: sin dato publicado.", f_nota)
    filas_ind.append(("Tabla diaria", "Nivel diario del mes, por año, de las estaciones principales. Diapositiva 7."))
    for k, (h, t) in enumerate(filas_ind):
        ind.write(6 + k, 1, h, f_txt); ind.write(6 + k, 2, t, f_txt)
    ind.write(8 + len(filas_ind), 1, "Para actualizar: descarga de nuevo el Excel y el PowerPoint desde la página, o escribe los datos nuevos en la columna del año en curso de cada hoja.", f_nota)
    wb.close()
    return buf.getvalue()


def _dt(d):
    from datetime import datetime
    return datetime(d.year, d.month, d.day)


def _num(ws, r, c, v, fmt):
    if v is None:
        ws.write_blank(r, c, None, fmt)
    else:
        ws.write_number(r, c, v, fmt)


def _dif(a, b):
    return "" if a is None or b is None else round(a - b, 2)


def _escala(valores):
    """Mínimo, máximo y paso «redondos» para el eje vertical (unas 5 a 8 divisiones)."""
    import math
    lo, hi = min(valores), max(valores)
    bruto = (hi - lo or abs(hi) or 1) / 6
    p = 10 ** math.floor(math.log10(bruto))
    paso = next(m * p for m in (1, 2, 2.5, 5, 10) if m * p >= bruto)
    return math.floor(lo / paso) * paso, math.ceil(hi / paso) * paso, paso


def tabla_diaria(D, n_est=5, n_años=4):
    """Días del mes en curso (hasta la fecha del reporte) × (estación, año): el nivel de ese día en cada año."""
    f = D["fecha"]
    elegidas = []
    for depto in ("16", "25", "22"):
        for x in D["regiones"][depto]:
            if len(elegidas) < n_est and (depto == "16" and len([e for e in elegidas if e["depto"] == "16"]) < 3 or depto != "16"
                                          and not any(e["depto"] == depto for e in elegidas)):
                elegidas.append(x)
    for x in D["regiones"]["16"]:
        if len(elegidas) < n_est and x not in elegidas:
            elegidas.append(x)
    grupos, umbrales, columnas = [], [], []
    for x in elegidas:
        años = sorted([y for y in x["años"]], reverse=False)[-n_años:]
        grupos.append((f"{x['rio']} ({x['estacion']})", años))
        umbrales.append([x["amarillo"], x["naranja"], x["rojo"]])
        columnas += [(x, y) for y in años]
    filas = []
    for dia in range(1, f.day + 1):
        i = pos_en_eje(date(2023 if f.month >= 9 else 2024, f.month, dia))
        filas.append([f"{dia}-{MES[f.month - 1]}"] + [x["series"][y][i] if i is not None else None for x, y in columnas])
    return {"grupos": grupos, "umbrales": umbrales, "columnas": columnas, "filas": filas, "año_cal": lambda y: y if f.month >= 9 else y + 1}


# ── PowerPoint ───────────────────────────────────────────────────────────────
def _caja(sl, x, y, w, h, partes, tam=14, borde=False, alinear=PP_ALIGN.JUSTIFY, fuente="Barlow", relleno=None, ancla=MSO_ANCHOR.TOP, color=None):
    """Cuadro de texto. «partes»: lista de párrafos; cada párrafo, lista de (texto, negrita)."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancla
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    for k, par in enumerate(partes):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = alinear
        for texto, negrita in par:
            r = p.add_run()
            r.text = texto
            r.font.name, r.font.size, r.font.bold = fuente, Pt(tam), negrita
            if color is not None:
                r.font.color.rgb = color
    if borde:
        tb.line.color.rgb = RGBColor(0, 0, 0)
        tb.line.width = Pt(1)
    if relleno:
        tb.fill.solid()
        tb.fill.fore_color.rgb = RGBColor.from_string(relleno)
    return tb


def _barra(sl, negrita, resto, alto=0.62):
    """La barra de arriba: el mensaje del día, con la primera frase en negrita (como en el reporte de Piura)."""
    return _caja(sl, 0, 0, 13.333, alto, [[(negrita + " ", True), (resto.strip(), False)]], tam=13, borde=True)


def _fuente(sl, texto="Fuente: SENAMHI", y=7.08):
    _caja(sl, 0, y, 8, 0.32, [[(texto, False)]], tam=11, fuente="Arial", alinear=PP_ALIGN.LEFT)


def _etiqueta(sl, x, y, w, texto):
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.3))
    s.fill.solid(); s.fill.fore_color.rgb = RGBColor(0xE2, 0xEF, 0xDA)
    s.line.color.rgb = RGBColor(0x70, 0xAD, 0x47); s.line.width = Pt(1.25)
    tf = s.text_frame
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = texto; r.font.name, r.font.size, r.font.bold = "Barlow", Pt(11), True
    r.font.color.rgb = RGBColor(0, 0, 0)


def _titulo_grafico(sl, x, y, w, t1, t2, tam=12):
    _caja(sl, x, y, w, 0.5, [[(t1, True)], [(t2, False)]], tam=tam, alinear=PP_ALIGN.CENTER, fuente="Arial")


def _grafico(sl, x, y, w, h, est):
    """Hidrograma como gráfico de PowerPoint: un año por línea, promedio histórico y umbrales."""
    cd = CategoryChartData()
    cd.categories = ETQ_EJE
    estilos = []
    for k, a in enumerate(est["años"]):
        cd.add_series(f"{a}-{str(a + 1)[2:]}", est["series"][a], number_format="0.00")
        estilos.append((C_AÑOS[k % 4], 2.25 if k == 0 else 1.5, None))
    for k, nom, color, guion in (("promedio", "Prom. histórico", C_PROM, MSO_LINE.DASH), ("amarillo", "Amarillo", C_AMA, MSO_LINE.LONG_DASH),
                                 ("naranja", "Naranja", C_NAR, MSO_LINE.LONG_DASH), ("rojo", "Rojo", C_ROJ, MSO_LINE.LONG_DASH)):
        if any(v is not None for v in est["umbrales"][k]):
            cd.add_series(nom, est["umbrales"][k], number_format="0.00")
            estilos.append((color, 1.5 if k == "promedio" else 1.25, guion))
    gf = sl.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.font.name, ch.font.size = "Arial", Pt(8)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(8)
    for ser, (color, ancho, guion) in zip(ch.plots[0].series, estilos):
        ser.smooth = False
        ser.marker.style = XL_MARKER_STYLE.NONE
        ln = ser.format.line
        ln.color.rgb = RGBColor.from_string(color)
        ln.width = Pt(ancho)
        if guion:
            ln.dash_style = guion
    todos = [v for a in est["años"] for v in est["series"][a] if v is not None] + \
            [v for k in ("promedio", "amarillo", "naranja", "rojo") for v in est["umbrales"][k] if v is not None]
    va = ch.value_axis
    caudal = est["variable"] == "CAUDAL"
    va.minimum_scale, va.maximum_scale, va.major_unit = _escala(todos)
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xE7, 0xE6, 0xE6)
    va.tick_labels.number_format = "#,##0" if caudal else "0.0"
    va.tick_labels.number_format_is_linked = False
    va.format.line.fill.background()
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(8)
    ca.format.line.color.rgb = RGBColor(0xBF, 0xBF, 0xBF)
    ca.has_major_gridlines = False
    # que muestre todas las etiquetas (solo el 1 de cada mes tiene texto) y sin una marca por día; en el orden del esquema
    ca.major_tick_mark = XL_TICK_MARK.NONE
    cax = ca._element
    for el in cax.findall(qn("c:tickLblSkip")) + cax.findall(qn("c:tickMarkSkip")):
        cax.remove(el)
    nuevos = [cax.makeelement(qn("c:tickLblSkip"), {"val": "1"}), cax.makeelement(qn("c:tickMarkSkip"), {"val": "31"})]
    despues = cax.find(qn("c:noMultiLvlLbl"))
    for el in nuevos:
        if despues is not None:
            despues.addprevious(el)
        else:
            cax.append(el)
    # punto del último dato
    if est["i"] is not None:
        pt = ch.plots[0].series[0].points[est["i"]]
        pt.marker.style = XL_MARKER_STYLE.CIRCLE
        pt.marker.size = 6
        pt.marker.format.fill.solid(); pt.marker.format.fill.fore_color.rgb = RGBColor.from_string(C_AÑOS[0])
        pt.data_label.has_text_frame = True
        pt.data_label.text_frame.text = coma(est["valor"], 0 if caudal else 2)
        pt.data_label.font.size, pt.data_label.font.bold = Pt(8), True
    return gf


def _tabla(sl, x, y, w, filas, anchos=None, tam=9, cab=1, rellenos=None, alto_fila=0.22):
    nf, nc = len(filas), max(len(f) for f in filas)
    t = sl.shapes.add_table(nf, nc, Inches(x), Inches(y), Inches(w), Inches(alto_fila * nf)).table
    t.first_row = True
    if anchos:
        tot = sum(anchos)
        for j, a in enumerate(anchos):
            t.columns[j].width = Emu(int(Inches(w) * a / tot))
    for i, f in enumerate(filas):
        t.rows[i].height = Inches(alto_fila)
        for j in range(nc):
            v = f[j] if j < len(f) else ""
            cel = t.cell(i, j)
            cel.margin_left = cel.margin_right = Inches(0.03)
            cel.margin_top = cel.margin_bottom = Inches(0.01)
            cel.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cel.text_frame
            tf.text = "" if v is None else str(v)
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if (j == 0 and i >= cab) or (isinstance(v, str) and j < 3 and i >= cab and not re.match(r"^[-+\d—]", v)) else PP_ALIGN.CENTER
            for r in p.runs:
                r.font.size, r.font.name = Pt(tam), "Arial"
                r.font.bold = i < cab
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i < cab else RGBColor(0, 0, 0)
            cel.fill.solid()
            color = (rellenos or {}).get((i, j)) or ("1F3864" if i < cab else ("FFFFFF" if i % 2 else "F2F2F2"))
            cel.fill.fore_color.rgb = RGBColor.from_string(color)
            if color == "FF0000" and i >= cab:
                for r in p.runs:
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    r.font.bold = True
    return t


def powerpoint(D, ejemplo=False):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    vacia = prs.slide_layouts[6]
    f = D["fecha"]

    # 1. portada
    sl = prs.slides.add_slide(vacia)
    _caja(sl, 0.4, 0.9, 12.5, 1.5, [[("REPORTE DE SITUACIÓN HÍDRICA", True)], [("ZONA ORIENTE", True)]], tam=34, alinear=PP_ALIGN.CENTER, fuente="Helvetica", color=TX2)
    _caja(sl, 0.4, 2.55, 12.5, 0.5, [[("Loreto · San Martín · Ucayali", False)]], tam=20, alinear=PP_ALIGN.CENTER, fuente="Helvetica", color=RGBColor(0x84, 0x97, 0xB0))
    _caja(sl, 0.4, 3.35, 12.5, 1.3, [[("Departamento de Estudios Económicos", False)], [("Banco Central de Reserva del Perú", False)], [("Sucursal Iquitos", False)]],
          tam=22, alinear=PP_ALIGN.CENTER, fuente="Helvetica", color=RGBColor(0x84, 0x97, 0xB0))
    _caja(sl, 0.4, 4.95, 12.5, 0.5, [[(f"{f.day} de {MES_LARGO[f.month - 1]} de {f.year}", False)]], tam=22, alinear=PP_ALIGN.CENTER, fuente="Helvetica", color=RGBColor(0x84, 0x97, 0xB0))
    if ejemplo:
        _caja(sl, 3.2, 5.45, 7, 0.4, [[("EJEMPLO CON DATOS ILUSTRATIVOS — no usar", True)]], tam=14, alinear=PP_ALIGN.CENTER, color=RGBColor(0xC0, 0, 0))
    if BANNER.exists():
        sl.shapes.add_picture(str(BANNER), 0, Inches(6.06), Inches(13.35), Inches(1.46))

    # 2. situación de hoy (tabla)
    sl = prs.slides.add_slide(vacia)
    neg, resto = mensaje_resumen(D)
    _barra(sl, neg, resto, alto=0.62)
    _titulo_grafico(sl, 2.2, 0.7, 9, "Situación de los principales ríos del Oriente", f"(nivel en metros sobre el nivel del mar, al {f.day} de {MES_LARGO[f.month - 1]})", tam=14)
    filas = [["Región", "Río", "Estación", "Nivel", "Var. 7 días", "Var. anual", "Dif. vs prom.", "Umbral rojo", "Alerta SENAMHI"]]
    rell = {}
    for depto in ("16", "22", "25"):
        for x in D["regiones"][depto][:12 if depto == "16" else 3]:
            filas.append([REGION[depto], x["rio"], x["estacion"] + ("" if x["seguro"] else " *"), coma(x["valor"]), signo(_d(x["valor"], x["hace7"])),
                          signo(_d(x["valor"], x["anterior"])), signo(_d(x["valor"], x["promedio"])), coma(x["rojo"]),
                          x["alerta"].capitalize() + ("" if x["alerta"] in ("normal", "sin umbral") else " · bajo" if x["baja"] else " · crecida")])
            rell[(len(filas) - 1, 8)] = FILL_ALERTA[x["alerta"]]
    _tabla(sl, 0.55, 1.35, 12.25, filas, anchos=[1.1, 1.3, 1.9, 0.9, 0.95, 0.95, 1.05, 1.0, 1.5], tam=8.5, rellenos=rell, alto_fila=min(0.25, 5.3 / len(filas)))
    _caja(sl, 0.55, 6.72, 12.2, 0.35, [[("Var. 7 días: diferencia con el dato de hace una semana; Var. anual: con el mismo día del año pasado; Dif. vs prom.: con el promedio histórico del día (en metros). "
                                           "La alerta sigue los umbrales de SENAMHI: en unas estaciones son de nivel bajo (vaciante) y en otras de crecida. * Sin departamento en SENAMHI: se incluye por su dirección zonal.", False)]],
          tam=8, alinear=PP_ALIGN.LEFT)
    _fuente(sl)

    # 3-6. hidrogramas por región (4 por diapositiva)
    def lamina(depto, lista, parte=""):
        sl = prs.slides.add_slide(vacia)
        neg, resto = mensaje_region(depto, lista)
        _barra(sl, neg, resto, alto=0.62)
        _etiqueta(sl, 9.2, 0.66, 4.0, f"{REGION[depto]}{parte}")
        pos = [(0.15, 0.98), (6.75, 0.98), (0.15, 3.86), (6.75, 3.86)]
        for (x0, y0), est in zip(pos, lista[:4]):
            _titulo_grafico(sl, x0, y0, 6.4, f"Río {est['rio']} · estación {est['estacion']}{'' if est['seguro'] else ' *'}",
                            f"(nivel diario en m.s.n.m., años hidrológicos set–ago)", tam=10)
            _grafico(sl, x0, y0 + 0.4, 6.4, 2.44, est)
        if not lista:
            _caja(sl, 3, 3, 7, 1, [[("SENAMHI no tiene estaciones con datos de nivel en esta región.", False)]], tam=14, alinear=PP_ALIGN.CENTER)
        nota = "Cada línea es un año hidrológico (1 de setiembre a 31 de agosto); el punto es el último dato. Las líneas punteadas son el promedio histórico y los umbrales de alerta de SENAMHI."
        if any(not e["seguro"] for e in lista[:4]):
            nota += " * Estación sin departamento en SENAMHI: se incluye por su dirección zonal."
        _caja(sl, 0.15, 6.74, 13, 0.36, [[(nota, False)]], tam=8, alinear=PP_ALIGN.LEFT)
        _fuente(sl, y=7.12)

    lor = D["regiones"]["16"]
    lamina("16", lor[:4], " (1/2)" if len(lor) > 4 else "")
    if len(lor) > 4:
        lamina("16", lor[4:8], " (2/2)")
    lamina("22", D["regiones"]["22"][:4])
    lamina("25", D["regiones"]["25"][:4])

    # 7. nivel diario del mes, por año (como la tabla de caudales del reporte de Piura)
    sl = prs.slides.add_slide(vacia)
    T = tabla_diaria(D)
    ult_año = max(y for _, años in T["grupos"] for y in años) if T["grupos"] else f.year
    _barra(sl, f"En lo que va de {MES_LARGO[f.month - 1]} (al día {f.day}),", _texto_mes(T, f), alto=0.62)
    _titulo_grafico(sl, 2.2, 0.7, 9, f"Nivel diario de los principales ríos del Oriente", f"(metros sobre el nivel del mar, 1 al {f.day} de {MES_LARGO[f.month - 1]} de cada año)", tam=13)
    cab1 = [""] + [g if k == 0 else "" for g, años in T["grupos"] for k in range(len(años))]
    cab2 = ["Día"] + [str(T["año_cal"](y)) for _, años in T["grupos"] for y in años]
    filas = [cab1, cab2] + [[fl[0]] + [coma(v) if v is not None else "—" for v in fl[1:]] for fl in T["filas"]]
    rell = {}
    for k, (nom, color) in enumerate((("Alerta amarilla", "FFFF00"), ("Alerta naranja", "FFA500"), ("Alerta roja", "FF0000"))):
        fila = [nom]
        for u, (_, años) in zip(T["umbrales"], T["grupos"]):
            fila += [coma(u[k]) if u[k] is not None else "—"] + [""] * (len(años) - 1)
        filas.append(fila)
        rell[(len(filas) - 1, 0)] = color
    nfil = len(filas)
    tb = _tabla(sl, 0.35, 1.3, 12.6, filas, anchos=[1.1] + [1] * (len(filas[0]) - 1), tam=7.5, cab=2, rellenos=rell, alto_fila=min(0.3, 5.3 / nfil))
    # celdas combinadas: estación sobre sus años, y cada umbral sobre los años de su estación
    c = 1
    for _, años in T["grupos"]:
        if len(años) > 1:
            tb.cell(0, c).merge(tb.cell(0, c + len(años) - 1))
            for k in range(3):
                tb.cell(nfil - 3 + k, c).merge(tb.cell(nfil - 3 + k, c + len(años) - 1))
        c += len(años)
    _caja(sl, 0.35, 6.75, 12.6, 0.3, [[("Dato diario de SENAMHI (promedio del mínimo y el máximo del día). «—»: sin dato publicado. Umbrales de alerta de SENAMHI de cada estación.", False)]], tam=8, alinear=PP_ALIGN.LEFT)
    _fuente(sl)

    # 8. caudales
    if D["caudales"]:
        sl = prs.slides.add_slide(vacia)
        c0 = D["caudales"][0]
        _barra(sl, f"Caudal: el río {c0['rio']} en {c0['estacion']} lleva {coma(c0['valor'], 0)} m³/s al {fecha_larga(c0['fecha'])},",
               _texto_caudal(D["caudales"]), alto=0.62)
        for k, est in enumerate(D["caudales"][:2]):
            x0 = 0.15 + 6.6 * k
            _titulo_grafico(sl, x0, 0.8, 6.4, f"Caudal del río {est['rio']} · estación {est['estacion']}", "(metros cúbicos por segundo, años hidrológicos set–ago)", tam=11)
            _grafico(sl, x0, 1.3, 6.4, 5.1, est)
        _caja(sl, 0.15, 6.6, 13, 0.3, [[("Cada línea es un año hidrológico (1 de setiembre a 31 de agosto). Caudal calculado por SENAMHI a partir del nivel.", False)]], tam=8, alinear=PP_ALIGN.LEFT)
        _fuente(sl)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _d(a, b):
    return None if a is None or b is None else a - b


def _texto_mes(T, f):
    partes = []
    for (g, años), (k0) in zip(T["grupos"], range(len(T["grupos"]))):
        cols = [j for j, (x, y) in enumerate(T["columnas"]) if f"{x['rio']} ({x['estacion']})" == g]
        if len(cols) < 2:
            continue
        hoy_v = next((T["filas"][i][1 + cols[-1]] for i in range(len(T["filas"]) - 1, -1, -1) if T["filas"][i][1 + cols[-1]] is not None), None)
        ant = next((T["filas"][i][1 + cols[-2]] for i in range(len(T["filas"]) - 1, -1, -1) if T["filas"][i][1 + cols[-2]] is not None), None)
        if hoy_v is not None and ant is not None:
            partes.append(f"el {g.split(' (')[0]} en {g.split('(')[1][:-1]} está {coma(abs(hoy_v - ant))} m {'por encima' if hoy_v > ant else 'por debajo'} del mismo día de {T['año_cal'](años[-2])}")
    return ("; ".join(partes[:3]) + ".") if partes else "nivel diario de cada año en las estaciones principales."


def _texto_caudal(cs):
    partes = []
    for c in cs:
        if c["anterior"] is not None and c["anterior"]:
            d = (c["valor"] / c["anterior"] - 1) * 100
            partes.append(f"en {c['estacion']} el caudal está {coma(abs(d), 1)} % {'por encima' if d > 0 else 'por debajo'} del mismo día del año pasado")
    return ("; ".join(partes) + ".") if partes else ""
