"""Extrae las subpartidas nacionales (10 dígitos) de un arancel SUNAT convertido a markdown,
con su descripción completa (partida > niveles '-' > texto)."""
import re, sys, json

COD10 = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}$")
CODCORTO = re.compile(r"^\d{4}\.\d{1,2}(\.\d{2})?$")      # 0101.10 / 0101.2 / 0101.10.10
PARTIDA4 = re.compile(r"^\d{2}\.\d{2}$")                  # 01.01 (encabezado de partida)

def limpiar(t):
    t = re.sub(r"\*\*|__|(?<!\w)_(?!\w)", "", t)
    return " ".join(t.replace("\\", "").split()).strip()

def celdas(linea):
    partes = linea.strip().strip("|").split("|")
    return [p for p in partes]

def items_descripcion(celda):
    """Divide la celda de descripción en ítems [(nivel, texto)].
    Formato A (2012+): '-<br>-<br>Texto<br>continuación'. Formato B (2002): '- - Texto<br>continuación'."""
    toks = [t.strip() for t in celda.split("<br>")]
    items, nivel_pend = [], 0
    for t in toks:
        if not t:
            continue
        if re.fullmatch(r"(-\s*)+", t):                      # solo guiones (formato A)
            nivel_pend += t.count("-")
            continue
        m = re.match(r"^((?:-\s*)+)(.*)$", t)                 # guiones + texto (formato B)
        if m and m.group(2):
            items.append([nivel_pend + m.group(1).count("-"), limpiar(m.group(2))]); nivel_pend = 0
        elif nivel_pend:                                     # texto tras guiones sueltos
            items.append([nivel_pend, limpiar(t)]); nivel_pend = 0
        elif items:                                          # continuación de línea
            items[-1][1] = (items[-1][1] + " " + limpiar(t)).strip()
        else:
            items.append([0, limpiar(t)])
    return [(n, x) for n, x in items if x]

def extraer(path):
    texto = open(path, encoding="utf-8").read().splitlines()
    out, sin_desc = {}, []
    cap, titulo_partida, pila = None, "", {}
    for linea in texto:
        if not linea.startswith("|"):
            continue
        c = celdas(linea)
        if len(c) < 2:
            continue
        cod_cel = limpiar(c[0].replace("<br>", " <br> "))
        codigos = [limpiar(x) for x in c[0].split("<br>") if limpiar(x)]
        desc_cel = c[1]
        # encabezado de partida (4 dígitos) o partida sin subdivisiones en negrita
        if len(codigos) == 1 and (PARTIDA4.match(codigos[0]) or (COD10.match(codigos[0]) and "**" in c[0])):
            titulo_partida = limpiar(desc_cel.replace("<br>", " "))
            pila = {}
            if COD10.match(codigos[0]):
                out[codigos[0].replace(".", "")] = titulo_partida
            continue
        items = items_descripcion(desc_cel)
        if not codigos and items:                            # fila de subtítulo sin código
            for n, x in items:
                pila = {k: v for k, v in pila.items() if k < n}; pila[n] = x
            continue
        validos = [k for k in codigos if COD10.match(k) or CODCORTO.match(k)]
        if not validos:
            continue
        # emparejar códigos con ítems: los de 10 dígitos van a ítems "hoja",
        # los cortos (0101.10) a ítems que terminan en ':'
        asign = {}
        if len(validos) == len(items):
            asign = {i: validos[i] for i in range(len(items))}
        else:
            j = 0
            for i, (n, x) in enumerate(items):
                if j >= len(validos):
                    break
                corto = not COD10.match(validos[j])
                if x.endswith(":") == corto:
                    asign[i] = validos[j]; j += 1
            if j < len(validos):                             # no cuadró: alinear por el final
                faltan = [k for k in validos if k not in asign.values()]
                hojas = [i for i, (n, x) in enumerate(items) if not x.endswith(":") and i not in asign]
                for i, k in zip(hojas, faltan):
                    asign[i] = k
        for i, (n, x) in enumerate(items):
            pila = {k: v for k, v in pila.items() if k < n}; pila[n] = x
            k = asign.get(i)
            if k and COD10.match(k):
                ruta = [titulo_partida] + [pila[l] for l in sorted(pila) if l < n] + [x]
                out[k.replace(".", "")] = " > ".join(r.rstrip(":") for r in ruta if r)
        for k in validos:
            if COD10.match(k) and k.replace(".", "") not in out:
                sin_desc.append(k)
                out[k.replace(".", "")] = ""
    return out, sin_desc

if __name__ == "__main__":
    res = {}
    for v in sys.argv[2:]:
        d, sd = extraer(f"{sys.argv[1]}/{v}.md")
        res[v] = d
        print(f"{v}: {len(d)} partidas | sin descripción: {sum(1 for x in d.values() if not x)}", file=sys.stderr)
    json.dump(res, open(f"{sys.argv[1]}/partidas.json", "w"), ensure_ascii=False)
