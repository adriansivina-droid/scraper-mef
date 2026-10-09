"""Construye el diccionario de subpartidas nacionales SUNAT (2002-2022) a partir de
las correlaciones teóricas y los aranceles en markdown. Salidas en EXPORT/arancel/."""
import json, re, sys, unicodedata, collections, os, difflib
import pandas as pd

SP = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
VERS = ["2002", "2007", "2012", "2017", "2022"]
VIGOR = {"2002": "2002-01-01", "2007": "2007-04-01", "2012": "2012-01-01",
         "2017": "2017-01-01", "2022": "2022-01-01"}
NORMA = {"2002": "D.S. 239-2001-EF", "2007": "D.S. 017-2007-EF", "2012": "D.S. 238-2011-EF",
         "2017": "D.S. 342-2016-EF", "2022": "D.S. 404-2021-EF"}

CAPITULOS = {
 1:"Animales vivos",2:"Carne y despojos comestibles",3:"Pescados y crustáceos, moluscos y demás invertebrados acuáticos",
 4:"Leche y productos lácteos; huevos de ave; miel natural; productos comestibles de origen animal",
 5:"Los demás productos de origen animal",6:"Plantas vivas y productos de la floricultura",
 7:"Hortalizas, plantas, raíces y tubérculos alimenticios",8:"Frutas y frutos comestibles; cortezas de agrios (cítricos), melones o sandías",
 9:"Café, té, yerba mate y especias",10:"Cereales",11:"Productos de la molinería; malta; almidón y fécula; inulina; gluten de trigo",
 12:"Semillas y frutos oleaginosos; semillas y frutos diversos; plantas industriales o medicinales; paja y forraje",
 13:"Gomas, resinas y demás jugos y extractos vegetales",14:"Materias trenzables y demás productos de origen vegetal",
 15:"Grasas y aceites animales, vegetales o de origen microbiano; ceras",16:"Preparaciones de carne, pescado, crustáceos, moluscos o insectos",
 17:"Azúcares y artículos de confitería",18:"Cacao y sus preparaciones",19:"Preparaciones a base de cereales, harina, almidón, fécula o leche; productos de pastelería",
 20:"Preparaciones de hortalizas, frutas u otros frutos o demás partes de plantas",21:"Preparaciones alimenticias diversas",
 22:"Bebidas, líquidos alcohólicos y vinagre",23:"Residuos y desperdicios de las industrias alimentarias; alimentos para animales",
 24:"Tabaco y sucedáneos del tabaco elaborados",25:"Sal; azufre; tierras y piedras; yesos, cales y cementos",
 26:"Minerales metalíferos, escorias y cenizas",27:"Combustibles minerales, aceites minerales y productos de su destilación; ceras minerales",
 28:"Productos químicos inorgánicos; compuestos de metal precioso, tierras raras o elementos radiactivos",29:"Productos químicos orgánicos",
 30:"Productos farmacéuticos",31:"Abonos",32:"Extractos curtientes o tintóreos; pigmentos, pinturas y barnices; tintas",
 33:"Aceites esenciales y resinoides; preparaciones de perfumería, de tocador o de cosmética",
 34:"Jabón, agentes de superficie orgánicos, preparaciones para lavar, lubricantes, ceras, velas",35:"Materias albuminoideas; almidones modificados; colas; enzimas",
 36:"Pólvora y explosivos; artículos de pirotecnia; fósforos; materias inflamables",37:"Productos fotográficos o cinematográficos",
 38:"Productos diversos de las industrias químicas",39:"Plástico y sus manufacturas",40:"Caucho y sus manufacturas",
 41:"Pieles (excepto la peletería) y cueros",42:"Manufacturas de cuero; artículos de talabartería; artículos de viaje, bolsos",
 43:"Peletería y confecciones de peletería; peletería facticia o artificial",44:"Madera, carbón vegetal y manufacturas de madera",
 45:"Corcho y sus manufacturas",46:"Manufacturas de espartería o cestería",47:"Pasta de madera o de las demás materias fibrosas celulósicas; papel o cartón para reciclar",
 48:"Papel y cartón; manufacturas de pasta de celulosa, de papel o cartón",49:"Productos editoriales, de la prensa y de otras industrias gráficas",
 50:"Seda",51:"Lana y pelo fino u ordinario; hilados y tejidos de crin",52:"Algodón",53:"Las demás fibras textiles vegetales; hilados de papel",
 54:"Filamentos sintéticos o artificiales",55:"Fibras sintéticas o artificiales discontinuas",56:"Guata, fieltro y tela sin tejer; hilados especiales; cordeles, cuerdas",
 57:"Alfombras y demás revestimientos para el suelo, de materia textil",58:"Tejidos especiales; superficies textiles con mechón insertado; encajes; tapicería",
 59:"Telas impregnadas, recubiertas, revestidas o estratificadas; artículos técnicos de materia textil",60:"Tejidos de punto",
 61:"Prendas y complementos de vestir, de punto",62:"Prendas y complementos de vestir, excepto los de punto",
 63:"Los demás artículos textiles confeccionados; prendería y trapos",64:"Calzado, polainas y artículos análogos; partes",
 65:"Sombreros, demás tocados, y sus partes",66:"Paraguas, sombrillas, bastones, látigos, fustas",
 67:"Plumas y plumón preparados; flores artificiales; manufacturas de cabello",68:"Manufacturas de piedra, yeso, cemento, amianto, mica o materias análogas",
 69:"Productos cerámicos",70:"Vidrio y sus manufacturas",71:"Perlas, piedras preciosas o semipreciosas, metales preciosos y sus manufacturas; bisutería; monedas",
 72:"Fundición, hierro y acero",73:"Manufacturas de fundición, hierro o acero",74:"Cobre y sus manufacturas",75:"Níquel y sus manufacturas",
 76:"Aluminio y sus manufacturas",77:"(Reservado)",78:"Plomo y sus manufacturas",79:"Cinc y sus manufacturas",80:"Estaño y sus manufacturas",
 81:"Los demás metales comunes; cermets; manufacturas de estas materias",82:"Herramientas y útiles, artículos de cuchillería y cubiertos, de metal común",
 83:"Manufacturas diversas de metal común",84:"Reactores nucleares, calderas, máquinas, aparatos y artefactos mecánicos; partes",
 85:"Máquinas, aparatos y material eléctrico, y sus partes; aparatos de grabación o reproducción de sonido e imagen",
 86:"Vehículos y material para vías férreas; aparatos de señalización",87:"Vehículos automóviles, tractores, velocípedos y demás vehículos terrestres; partes",
 88:"Aeronaves, vehículos espaciales, y sus partes",89:"Barcos y demás artefactos flotantes",
 90:"Instrumentos y aparatos de óptica, fotografía, cinematografía, medida, control, precisión o médico-quirúrgicos",
 91:"Aparatos de relojería y sus partes",92:"Instrumentos musicales; sus partes y accesorios",93:"Armas, municiones, y sus partes y accesorios",
 94:"Muebles; mobiliario médico-quirúrgico; artículos de cama; luminarias; construcciones prefabricadas",
 95:"Juguetes, juegos y artículos para recreo o deporte; sus partes",96:"Manufacturas diversas",
 97:"Objetos de arte o colección y antigüedades",98:"Mercancías con tratamiento especial (capítulo nacional)"}

# ---------- 1. Correlaciones ----------
def norm(x):
    if pd.isna(x): return None
    s = str(x).strip()
    if s.endswith(".0"): s = s[:-2]
    d = re.sub(r"[.\s]", "", s)
    return d.zfill(10) if d.isdigit() and 7 <= len(d) <= 10 else None

def leaf(t):
    """'- - - Para carrera' -> (3, 'Para carrera')"""
    if not isinstance(t, str): return None, ""
    t = " ".join(t.replace("\n", " ").split())
    m = re.match(r"^((?:-\s*)*)(.*)$", t)
    return m.group(1).count("-"), m.group(2).strip().rstrip(":").strip()

C = os.path.join(SP, "corr")
FUENTES = {  # transición: (archivo, hoja, fila inicial, versión de la descripción)
 ("2002","2007"): (f"{C}/correlacion-Teorica-2002-2007/correlacion-Teorica-2002-2007.xlsx", "Hoja1", 8, "2007"),
 ("2007","2012"): (f"{C}/correlacionTeorica2007-2012/correlacionTeorica2007-2012.xls", "Cambios Correlacion 2007-2012", 1, "2007"),
 ("2012","2017"): (f"{C}/correlacionTeorica2012-2017/correlacionTeorica2012-2017.xls", "Arancel 2012", 1, "2012"),
 ("2017","2022"): (f"{C}/correlacionTeorica2017-2022/correlacionTeorica2017-2022.xlsx", "CORRELACION ARANCEL TOTAL", 1, "2022")}

pares = {}                    # (v,w) -> set((a,b))
desc = {v: {} for v in VERS}  # v -> code -> texto hoja
nivel = {v: {} for v in VERS}
codigos = {v: set() for v in VERS}
for (v, w), (p, sh, ini, vdesc) in FUENTES.items():
    df = pd.read_excel(p, sheet_name=sh, header=None).iloc[ini:, :3]
    s = set()
    for a, b, d in df.values:
        a, b = norm(a), norm(b)
        if a: codigos[v].add(a)
        if b: codigos[w].add(b)
        if a and b: s.add((a, b))
        cod_d = a if vdesc == v else b
        if cod_d and isinstance(d, str) and cod_d not in desc[vdesc]:
            n, t = leaf(d); desc[vdesc][cod_d] = t; nivel[vdesc][cod_d] = n
    pares[(v, w)] = s
# hoja REVISADO (ajustes 2017-2022, sobre todo textiles y vidrio)
rv = pd.read_excel(FUENTES[("2017","2022")][0], sheet_name="REVISADO", header=None).iloc[5:, 1:3].dropna()
extra = {(norm(a), norm(b)) for a, b in rv.values if norm(a) and norm(b)}
pares[("2017","2022")] |= extra
for a, b in extra: codigos["2017"].add(a); codigos["2022"].add(b)

# ---------- 2. Aranceles en markdown (descripción jerárquica y códigos) ----------
def util(t):
    """Descripción usable: con al menos 3 letras seguidas."""
    return isinstance(t, str) and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{3}", t) is not None

md = json.load(open(os.path.join(SP, "arancel_src/partidas.json")))
titulo4 = {}   # partida 4 dígitos -> título (de la versión más reciente con dato)
for v in VERS:
    if v not in md: continue
    for c, t in md[v].items():
        if not re.fullmatch(r"\d{10}", c): continue
        codigos[v].add(c)
        segs = [x.strip() for x in t.split(" > ")]
        if segs and segs[0]:
            titulo4[c[:4]] = re.split(r"\s+-\s+", segs[0])[0].strip()
        hoja_md = segs[-1] if segs else ""
        if not util(desc[v].get(c)) and util(hoja_md):
            desc[v][c] = hoja_md
for v in VERS:  # el regex de los md recupera códigos que el parser no asoció a una fila
    t = open(os.path.join(SP, f"arancel_src/{v}.md"), encoding="utf-8").read()
    if v == "2007":   # el md 2007 está dañado: solo se usan las correlaciones
        continue
    codigos[v] |= {re.sub(r"\D", "", m) for m in re.findall(r"(?<![\d.])\d{4}\.\d{2}\.\d{2}\.\d{2}(?![\d.])", t)}

# 2002: tablas que el PDF convirtió en imagen ("picture text")
t02 = open(os.path.join(SP, "arancel_src/2002.md"), encoding="utf-8").read()
for blk in re.findall(r"<!-- Start of picture text -->(.*?)<!-- End of picture text -->", t02, re.S):
    for it in blk.split("<br>"):
        m = re.match(r"\s*(\d{4}\.\d{2}\.\d{2}\.\d{2})\s+((?:-\s*)*)(.*?)\s+\d+\s*$", it)
        if m:
            c = m.group(1).replace(".", ""); codigos["2002"].add(c)
            if not util(desc["2002"].get(c)): desc["2002"][c] = m.group(3).strip()

def completa(c):
    for v in reversed(VERS):
        if v in md and md[v].get(c):
            return md[v][c]
    return ""

# ---------- 3. Continuidad entre versiones ----------
def continuidad(v, w):
    sal, ent = collections.defaultdict(set), collections.defaultdict(set)
    for a, b in pares[(v, w)]:
        sal[a].add(b); ent[b].add(a)
    ok = {}
    for c in codigos[v] & codigos[w]:
        s = sal.get(c, {c}); e = ent.get(c, {c})
        ok[c] = (s == {c} and e == {c})
    return ok, sal, ent

TRANS = list(zip(VERS, VERS[1:]))
CONT, SAL, ENT = {}, {}, {}
for t in TRANS:
    CONT[t], SAL[t], ENT[t] = continuidad(*t)

def nd(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

todos = sorted(set().union(*codigos.values()))
filas = []
for c in todos:
    pres = [v for v in VERS if c in codigos[v]]
    # tramos estables: versiones consecutivas presentes y unidas por continuidad 1 a 1
    tramos, cur = [], []
    for v in VERS:
        if c not in codigos[v]:
            if cur: tramos.append(cur); cur = []
            continue
        if cur and not CONT[(cur[-1], v)].get(c, False):
            tramos.append(cur); cur = []
        cur.append(v)
    if cur: tramos.append(cur)
    largo = max(tramos, key=len)
    ultimo = tramos[-1]
    vig = "2022" in pres
    descs = {v: (desc[v].get(c, "") if util(desc[v].get(c)) else "") for v in VERS}
    # comparación de descripciones: primero las fuentes limpias (correlaciones 2007/2012/2022)
    comp = [nd(descs[v]) for v in largo if descs[v] and v in ("2007", "2012", "2022")]
    if len(comp) < 2:
        comp = [nd(descs[v]) for v in largo if descs[v]]
    misma = "" if len(largo) == 1 or len(comp) < 2 else (
        "SI" if min(difflib.SequenceMatcher(None, comp[0], x).ratio() for x in comp[1:]) >= 0.85 else "NO")
    if vig and len(ultimo) == len(VERS):
        estado = "ESTABLE 2002-HOY"
    elif vig and ultimo[0] == ultimo[-1] == "2022" and len(pres) == 1:
        estado = "NUEVA 2022"
    elif vig:
        estado = f"ESTABLE DESDE {ultimo[0]}"
    else:
        estado = f"DESCONTINUADA (ÚLTIMA {pres[-1]})"
    anteriores, siguientes = set(), set()
    for (v, w) in TRANS:
        if c in codigos[w] and not CONT[(v, w)].get(c, False):
            anteriores |= ENT[(v, w)].get(c, set())
        if c in codigos[v] and not CONT[(v, w)].get(c, False):
            siguientes |= SAL[(v, w)].get(c, set())
    anteriores.discard(c); siguientes.discard(c)
    hoja = next((descs[v] for v in ("2022", "2012", "2007", "2017", "2002") if descs[v]), "")
    if not hoja and siguientes:   # sin texto propio: se describe por su equivalente
        hoja = "≈ " + " / ".join(sorted({desc[w].get(x, "") for (v, w) in TRANS for x in siguientes if util(desc[w].get(x))}))[:300]
    cap = int(c[:2])
    filas.append({
        "PARTIDA": c, "CAPITULO": f"{cap:02d}", "CAPITULO_DESC": CAPITULOS.get(cap, ""),
        "PARTIDA_4": c[:4], "PARTIDA_4_DESC": titulo4.get(c[:4], ""), "SUBPARTIDA_6": c[:6],
        "CODIGO_SUNAT": f"{c[:4]}.{c[4:6]}.{c[6:8]}.{c[8:]}",
        "DESCRIPCION": hoja, "DESCRIPCION_COMPLETA": completa(c),
        **{f"V{v}": int(v in pres) for v in VERS},
        "PRIMERA_VERSION": pres[0], "ULTIMA_VERSION": pres[-1], "VIGENTE": int(vig),
        "ESTADO": estado,
        "SERIE_ESTABLE": f"{largo[0]}-{largo[-1]}" if len(largo) > 1 else largo[0],
        "SERIE_ESTABLE_DESDE": VIGOR[largo[0]],
        "SERIE_ESTABLE_HASTA": "vigente" if largo[-1] == "2022" else VIGOR[VERS[VERS.index(largo[-1]) + 1]],
        "TRAMOS": " | ".join(f"{t[0]}-{t[-1]}" if len(t) > 1 else t[0] for t in tramos),
        "MISMA_DESCRIPCION": misma,
        **{f"C{a[2:]}_{b[2:]}": ("" if not (c in codigos[a] and c in codigos[b]) else int(CONT[(a, b)].get(c, False))) for a, b in TRANS},
        "EQUIV_ANTERIORES": " ".join(sorted(anteriores)), "EQUIV_SIGUIENTES": " ".join(sorted(siguientes)),
        **{f"DESC_{v}": descs[v] for v in VERS},
    })
dic = pd.DataFrame(filas)

# correlaciones en formato largo
corr = []
for (v, w) in TRANS:
    for a, b in sorted(pares[(v, w)]):
        ns, ne = len(SAL[(v, w)][a]), len(ENT[(v, w)][b])
        tipo = ("SIN CAMBIO" if a == b and ns == ne == 1 else
                "RECODIFICADA 1:1" if ns == ne == 1 else
                "DIVIDIDA 1:N" if ns > 1 and ne == 1 else
                "FUSIONADA N:1" if ns == 1 and ne > 1 else "N:M")
        corr.append({"DE_VERSION": v, "A_VERSION": w, "PARTIDA_ORIGEN": a, "PARTIDA_DESTINO": b, "TIPO": tipo,
                     "DESC_ORIGEN": desc[v].get(a, ""), "DESC_DESTINO": desc[w].get(b, "")})
corr = pd.DataFrame(corr)

vers = pd.DataFrame([{"VERSION": v, "NORMA": NORMA[v], "VIGENTE_DESDE": VIGOR[v],
                      "VIGENTE_HASTA": VIGOR[VERS[i+1]] if i+1 < len(VERS) else "vigente",
                      "N_SUBPARTIDAS": len(codigos[v])} for i, v in enumerate(VERS)])

os.makedirs(OUT, exist_ok=True)
dic.to_csv(f"{OUT}/diccionario_partidas.csv", index=False, encoding="utf-8-sig")
corr.to_csv(f"{OUT}/correlaciones_sunat.csv", index=False, encoding="utf-8-sig")
vers.to_csv(f"{OUT}/versiones_arancel.csv", index=False, encoding="utf-8-sig")
json.dump({"versiones": vers.to_dict("records")}, open(f"{SP}/vers.json", "w"))
print(vers.to_string())
print(dic.ESTADO.value_counts().to_string())
print(corr.groupby(["DE_VERSION", "TIPO"]).size().unstack(fill_value=0).to_string())
