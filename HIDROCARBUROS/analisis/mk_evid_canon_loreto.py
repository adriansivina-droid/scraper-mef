# Uso: python3 mk_evid_canon_loreto.py Loreto_petroleo_2025_evidencia.xlsx  (requiere t_full.pkl: tablas leídas de los Excel de canon con canon_xls.py)
"""Punto 5: hoja de evidencia Canon_lotes_2025 en Loreto_petroleo_2025_evidencia.xlsx (datos de los Excel de canon reales)."""
import pickle, sys, openpyxl, pandas as pd
from openpyxl.styles import Font, Alignment
X = sys.argv[1]
cl, dist, mun = [pickle.load(open("t_full.pkl", "rb"))[i] for i in (1, 3, 4)]
wb = openpyxl.load_workbook(X)
if "Canon_lotes_2025" in wb.sheetnames:
    del wb["Canon_lotes_2025"]
ws = wb.create_sheet("Canon_lotes_2025", wb.sheetnames.index("Canon_Loreto") + 1)
F, FB, FT, FN = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True), Font(name="Arial", size=12, bold=True), Font(name="Arial", size=9)
NUM, PCT, ENT = '#,##0.00;\\(#,##0.00\\);\\-', '0.0%;\\(0.0%\\);\\-', '#,##0;\\(#,##0\\);\\-'
fila = [1]
def put(vals, font=F, fmts=None, wrap=False):
    r = fila[0]
    for j, v in enumerate(vals):
        c = ws.cell(r, j + 1, v); c.font = font
        if fmts and j < len(fmts) and fmts[j]: c.number_format = fmts[j]
        if wrap: c.alignment = Alignment(wrap_text=True, vertical="top")
    fila[0] += 1
    return r
def salto(n=1): fila[0] += n
put(["Canon y sobrecanon de Loreto 2025: por lote, por beneficiario y por municipalidad"], FT)
put(["Fuente: PERUPETRO, Excel de canon (página «Canon y Sobre Canon»: «Canon Petrolero 2024/2025», determinación; «Canon por Año Loreto», distribución; "
     "página «Canon Municipalidades»: «Canon por Año Loreto», bloque validado con la PCM). Leídos con el notebook PP_Produccion_Lotes.ipynb, sección 9."], FN)
salto()
# A. Canon por lote (determinación), US$
put(["A. Canon y sobrecanon generado por los lotes de la zona Loreto / Ucayali (millones de US$)"], FB)
h = put(["Lote", "Producto", "Volumen 2025 (bbl o MM BTU)", "Valor de la producción 2025", "Canon y sobrecanon 2025", "Canon / valor",
         "Parte de Loreto 2025", "Parte de Ucayali 2025", "Parte de Loreto 2024", "Var. Loreto 2025 vs 2024", "Participación en lo de Loreto 2025"], FB, wrap=True)
z = cl[cl.ZONA.str.contains("LORETO", na=False) & cl.AÑO.isin([2024, 2025])]
g = z.groupby(["AÑO", "LOTE", "PRODUCTO"])[["VOLUMEN", "VALOR_PRODUCCION_US$", "CANON_TOTAL_US$", "CANON_DEP_1_US$", "CANON_DEP_2_US$"]].sum()
l24 = z[z.AÑO == 2024].groupby("LOTE")["CANON_DEP_1_US$"].sum() / 1e6
r0 = fila[0]
filas = []
for (lote, prod), v in g.xs(2025, level="AÑO").iterrows():
    if lote == "67":
        continue
    filas.append((lote, prod, v))
for lote, prod, v in filas:
    r = fila[0]
    nom = "Ajustes de meses anteriores" if lote.startswith("AJUSTES") else f"Lote {lote}"
    p24 = None if lote.startswith("AJUSTES") or prod == "LGN" else round(float(l24.get(lote, 0)), 4)
    put([nom, {"PETROLEO": "Petróleo", "GAS": "Gas natural", "LGN": "LGN", "CONDENSADO": "Condensado"}.get(prod, prod) if not lote.startswith("AJUSTES") else "", v["VOLUMEN"] or None, round(v["VALOR_PRODUCCION_US$"] / 1e6, 4),
         round(v["CANON_TOTAL_US$"] / 1e6, 4), f"=IF(D{r}=0,\"\",E{r}/D{r})", round(v["CANON_DEP_1_US$"] / 1e6, 4),
         round(v["CANON_DEP_2_US$"] / 1e6, 4), p24, f"=IF(OR(I{r}=\"\",I{r}=0),\"\",G{r}/I{r}-1)", None],
        fmts=[None, None, ENT, NUM, NUM, '0.00%', NUM, NUM, NUM, PCT, PCT])
r1 = fila[0] - 1
rt = put(["Total", "", None, f"=SUM(D{r0}:D{r1})", f"=SUM(E{r0}:E{r1})", f"=E{fila[0]}/D{fila[0]}", f"=SUM(G{r0}:G{r1})", f"=SUM(H{r0}:H{r1})",
          f"=SUM(I{r0}:I{r1})", f"=G{fila[0]}/I{fila[0]}-1", None], FB, [None, None, None, NUM, NUM, '0.00%', NUM, NUM, NUM, PCT, PCT])
for r in range(r0, r1 + 1):
    ws.cell(r, 11, f"=G{r}/G${rt}").number_format = PCT; ws.cell(r, 11).font = F
put(["Nota: el canon es el 18,75 % del valor de la producción que considera la determinación; de los Lotes 95 y 8 (Loreto) corresponde 80 % a Loreto y 20 % a Ucayali, "
     "y del Lote 31-C (Ucayali) 20 % a Loreto. En el Excel de 2024, el Lote 8 figura con unidad «MM BTU» (35 068), aunque es petróleo (35 mil barriles en la producción fiscalizada)."], FN)
salto()
# B. Lote 95 por mes
put(["B. Lote 95: parte de Loreto del canon, por mes de producción, 2025 (millones de US$)"], FB)
put(["Mes", "Volumen (bbl)", "Canon y sobrecanon del lote", "Parte de Loreto"], FB, wrap=True)
m = z[(z.AÑO == 2025) & (z.LOTE == "95")].groupby("MES")[["VOLUMEN", "CANON_TOTAL_US$", "CANON_DEP_1_US$"]].sum()
MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
rb0 = fila[0]
for mm, v in m.iterrows():
    put([f"{MES[mm - 1]}-2025", v["VOLUMEN"], round(v["CANON_TOTAL_US$"] / 1e6, 4), round(v["CANON_DEP_1_US$"] / 1e6, 4)], fmts=[None, ENT, NUM, NUM])
rb1 = fila[0] - 1
put(["Año", f"=SUM(B{rb0}:B{rb1})", f"=SUM(C{rb0}:C{rb1})", f"=SUM(D{rb0}:D{rb1})"], FB, [None, ENT, NUM, NUM])
s1 = put(["1er semestre", None, None, f"=SUM(D{rb0}:D{rb0 + 5})"], fmts=[None, None, None, NUM])
s2 = put(["2do semestre", None, None, f"=SUM(D{rb0 + 6}:D{rb1})"], fmts=[None, None, None, NUM])
put(["Var. 2do vs 1er semestre", None, None, f"=D{s2}/D{s1}-1"], FB, [None, None, None, PCT])
salto()
# C. Distribución por beneficiario
put(["C. Canon y sobrecanon transferido a Loreto, por beneficiario (millones de S/)"], FB)
put(["Beneficiario (como figura en el Excel)", "Tipo", "% 2023", "2023", "% 2024–2025", "2024", "2025", "Participación 2025"], FB, wrap=True)
d = dist[(dist.DEPARTAMENTO == "LORETO") & dist.AÑO.isin([2023, 2024, 2025])]
p = d.pivot_table(index=["BENEFICIARIO", "TIPO_BENEFICIARIO"], columns="AÑO", values="MONTO_SOLES", aggfunc="sum").fillna(0) / 1e6
pc = d.groupby(["BENEFICIARIO", "AÑO"]).PORCENTAJE.first()
def pct(b, a):
    x = pc.get((b, a)); 
    try: return float(x)
    except (TypeError, ValueError):
        x = str(x or "").replace("%", "").strip()
        return float(x) / 100 if x else None
rc0 = fila[0]
orden = {"MUNICIPALIDADES": 0, "GOBIERNO REGIONAL": 1, "UNIVERSIDADES": 2, "IIAP": 3, "INSTITUTOS": 4, "LEY 29289": 5}
for (b, t), v in sorted(p.iterrows(), key=lambda x: (orden.get(x[0][1], 9), x[0][0])):
    r = fila[0]
    put([b, {"IIAP": "IIAP", "LEY 29289": "Descuento Ley 29289"}.get(t, t.capitalize()), pct(b, 2023), round(v.get(2023, 0), 4), pct(b, 2025), round(v.get(2024, 0), 4),
         round(v.get(2025, 0), 4), None], fmts=[None, None, '0.0%', NUM, '0.0%', NUM, NUM, PCT])
rc1 = fila[0] - 1
rct = put(["Total", "", None, f"=SUM(D{rc0}:D{rc1})", None, f"=SUM(F{rc0}:F{rc1})", f"=SUM(G{rc0}:G{rc1})", None], FB, [None, None, None, NUM, None, NUM, NUM])
for r in range(rc0, rc1 + 1):
    ws.cell(r, 8, f"=G{r}/G${rct}").number_format = PCT; ws.cell(r, 8).font = F
put(["Nota: desde el 30 de enero de 2024 se aplica la Ley N° 31934 (nota del Excel). En 2023 los % (52, 5, 3 y 40) se aplican después de descontar la Ley N° 29289 "
     "(contrapartida nacional y servicio de deuda). La suma 2025 del Excel (S/ 213,84 millones) difiere en S/ 0,01 millones de la Estadística Mensual (S/ 213,85 millones)."], FN)
salto()
# D. Municipalidades ene–set 2025
mm_ = mun[(mun.DEPARTAMENTO == "LORETO") & (mun.AÑO == 2025) & (mun.SECCION == "GOBIERNOS LOCALES")]
meses = sorted(mm_.MES.unique())
put([f"D. Canon y sobrecanon por municipalidad, Loreto, {MES[meses[0] - 1].lower()}–{MES[meses[-1] - 1].lower()} 2025 (millones de S/; meses con dato en el Excel de Canon Municipalidades)"], FB)
put(["Municipalidad", "Nivel", "Provincia", "Monto", "Participación", "% del área del Lote 95 en el distrito"], FB, wrap=True)
area = {"TAPICHE": 0.38, "SOPLIN": 0.23, "EMILIO SAN MARTIN": 0.16, "PUINAHUA": 0.11, "CAPELO": 0.086, "ALTO TAPICHE": 0.027}
gm = mm_.groupby(["MUNICIPALIDAD", "NIVEL", "PROVINCIA"]).MONTO_SOLES.sum().div(1e6).sort_values(ascending=False)
rd0 = fila[0]
for (mu, ni, pr), v in gm.items():
    put([mu.title(), ni.title(), pr.title(), round(v, 4), None, area.get(mu)], fmts=[None, None, None, NUM, PCT, '0.0%'])
rd1 = fila[0] - 1
rdt = put([f"Total ({len(gm)} municipalidades)", "", "", f"=SUM(D{rd0}:D{rd1})", None, None], FB, [None, None, None, NUM])
for r in range(rd0, rd1 + 1):
    ws.cell(r, 5, f"=D{r}/D${rdt}").number_format = PCT; ws.cell(r, 5).font = F
put(["Provincia de Requena", "", "", f'=SUMIF(C{rd0}:C{rd1},"Requena",D{rd0}:D{rd1})', f"=D{fila[0]}/D{rdt}", None], FB, [None, None, None, NUM, PCT])
put([f"Rubro municipal de la Distribución, mismos meses (control)", "", "",
     round(dist[(dist.DEPARTAMENTO == "LORETO") & (dist.AÑO == 2025) & (dist.TIPO_BENEFICIARIO == "MUNICIPALIDADES") & dist.MES.isin(meses)].MONTO_SOLES.sum() / 1e6, 4)],
    fmts=[None, None, None, NUM])
put([f"Comunidades (5 %), mismos meses", "", "",
     round(mun[(mun.DEPARTAMENTO == "LORETO") & (mun.AÑO == 2025) & (mun.SECCION != "GOBIERNOS LOCALES")].MONTO_SOLES.sum() / 1e6, 4)], fmts=[None, None, None, NUM])
put(["Nota: el % del área del Lote 95 por distrito sale del cruce del polígono del lote con los límites distritales de GADM 4.1 (mapa de lotes del proyecto, corrida del 20/10/2026); "
     "un séptimo distrito con una parte menor del lote no tiene municipalidad emparejada. Gobiernos locales + comunidades = rubro municipal de la Distribución."], FN)
for col, w in zip("ABCDEFGHIJK", (34, 16, 16, 16, 16, 14, 14, 14, 14, 14, 16)):
    ws.column_dimensions[col].width = w
wb.save(X)
print("ok", ws.max_row, "filas")
