# Simulador de la Consulta Amigable de Ingresos con navegación por FORMULARIO (postback ASP.NET), como el MEF real:
# default.aspx?y=AAAA trae un iframe Navegar_N.aspx (2007+ = 6; antes = 1); la raíz lista las fuentes; cada POST lleva
# __VIEWSTATE (aquí: el estado en base64), grp1 = «código/PIA/PIM/recaudado» de la fila elegida y el botón de la dimensión.
# default.aspx siempre apunta a Navegar_6 (como el MEF); antes de 2007 solo responde Navegar_1. Al abrir, la raíz muestra solo TOTAL con el botón «Fuente» (como el MEF). Las URL con filtros se ignoran (como en el MEF). Desde 2020 el nivel M pasa por «Gob.Loc./Mancom.» antes del departamento.
# El POST debe llevar el año del formulario (ctl00$CPH1$DrpYear), como lo envía el navegador.
# Uso: python3 mock_mef.py  (puerto 8766)
import urllib.parse, html, re, json, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
F, RU, T, N, G, D, MU = "Fuente de Financiamiento", "Rubro", "Tipo de Recurso", "Nivel de Gobierno", "Gob.Loc./Mancom.", "Departamento", "Municipalidad"
BOTON = {"Fuente": "BtnFuente", RU: "BtnRubro", T: "BtnTipoRecurso", N: "BtnNivelGobierno", G: "BtnGobLoc", D: "BtnDepartamento", MU: "BtnMunicipalidad",
         "Mes": "BtnMes", "Sector": "BtnSector", "Pliego": "BtnPliego"}
CABECERA = {G: "Gobiernos Locales / Mancomunidades"}     # el botón dice «Gob.Loc./Mancom.», la cabecera no (como en el MEF)
MUNIS = {"01-301454": ("MUNICIPALIDAD PROVINCIAL DE REQUENA", 4819640.25), "06-301459": ("MUNICIPALIDAD DISTRITAL DE PUINAHUA", 373651.10),
         "01-301422": ("MUNICIPALIDAD PROVINCIAL DE MAYNAS - IQUITOS", 9114760.40)}

def opciones(anio, f, dim):
    """f = {dimensión: código} ya filtrado; devuelve {código: (nombre, recaudado)} o None si no hay datos."""
    nuevo = anio >= 2007
    if dim == "":
        return {"TOTAL": ("TOTAL", 1e11)}
    if dim == F:
        return ({"1": ("RECURSOS ORDINARIOS", 9e9), "5": ("RECURSOS DETERMINADOS", 5e9)} if nuevo
                else {"00": ("RECURSOS ORDINARIOS", 9e9), "01": ("CANON Y SOBRECANON", 1e9)})
    if dim == RU:
        return {"18": ("CANON Y SOBRECANON, REGALIAS, RENTA DE ADUANAS Y PARTICIPACIONES", 3e9)} if f.get(F) == "5" else None
    if dim == T:
        if nuevo:
            d = {"0": ("CANON", 7e8), "5": ("CANON Y SOBRECANON PETROLERO", 30e6)}
            if anio >= 2020: d["K"] = ("SUB CUENTA - CANON Y SOBRECANON PETROLERO", 60e6)
            return d
        return {"0": ("NORMAL", 3e8)} if anio == 2005 else {"0": ("NORMAL", 3e8), "4": ("CANON Y SOBRECANON PETROLERO", 1.5e8)}
    if dim == N:
        tot = opciones(anio, f, T)[f[T]][1]
        if anio <= 2004 or (anio < 2007 and f.get(T) == "0" and anio != 2005):
            return {"E": ("GOBIERNO NACIONAL", tot)}
        return {"E": ("GOBIERNO NACIONAL", tot * .1), "M": ("GOBIERNOS LOCALES", tot * .6), "R": ("GOBIERNOS REGIONALES", tot * .3)}
    if dim == G:
        return {"M": ("MUNICIPALIDADES", 1e6), "C": ("MANCOMUNIDADES", 0.0)} if f.get(N) == "M" else None
    if dim == D:
        if f.get(N) not in ("M", "R"): return None
        return {"15": ("LIMA", 5e6), "16": ("LORETO", 14308051.75 * (2 if f.get(T) == "K" else 1))}
    if dim == "Sector":                                # 2003: sin nivel de gobierno; el petrolero va al CND (PCM)
        return {"01": ("PRESIDENCIA CONSEJO MINISTROS", opciones(anio, f, T)[f[T]][1])} if T in f else None
    if dim == "Pliego":
        return {"013": ("CONSEJO NACIONAL DE DESCENTRALIZACION", opciones(anio, f, T)[f[T]][1])} if "Sector" in f else None
    if dim == MU:
        mult = 2 if f.get(T) == "K" else 1
        return {c: (n, v * mult) for c, (n, v) in MUNIS.items()} if D in f else None
    return None

def botones(anio, f, dim):
    if dim == "":
        return [N, "Fuente", RU, "Mes"]
    usados = set(f) | {dim}
    if anio == 2003:
        return [x for x in (T, "Sector", "Pliego") if x not in usados] + ["Mes"]
    b = [x for x in (RU, T, N, G, D, MU) if x not in usados]
    if anio >= 2020 and N in f and f.get(N) == "M" and G not in f and dim != G: b = [x for x in b if x != D]
    if dim == N and anio >= 2020: b = [x for x in b if x != D]     # en M hay que pasar por Gob.Loc. (los otros niveles no tienen departamento aquí)
    return b + ["Mes"]

def pagina(anio, filtros, dim, n):
    f = dict(filtros)
    hist = "<tr><td onclick='GoUpTo(0)'><img src='u.gif'/></td><td>TOTAL</td><td>1</td><td>1</td><td>999,999</td></tr>"
    pref = {}
    for i, (d, c) in enumerate(filtros):
        nom, val = opciones(anio, pref, d)[c]
        pref[d] = c
        hist += f"<tr><td onclick='GoUpTo({i+1})'><img/></td><td>{d} {c}: {html.escape(nom)}</td><td>0</td><td>0</td><td>{val:,.2f}</td></tr>"
    ops = opciones(anio, f, dim)
    vs = base64.b64encode(json.dumps({"y": anio, "f": filtros, "d": dim}).encode()).decode()
    btn = "".join(f"<input type='submit' name='ctl00$CPH1${BOTON[x]}' value='{x}' onclick='OnClickButton();' class='Button' />"
                  for x in botones(anio, f, dim))
    cuerpo = ""
    if ops is not None:
        filas = "".join(f"<tr onclick='kCod=\"{c}\";tr_clk({i}, this)'><td><input type='radio' name='grp1' value='{c}/0/0/{v:.2f}' "
                        f"onclick='kCod=\"{c}\";grp1_clk({i})'></td><td>{c}: {html.escape(nom)}</td><td>0</td><td>0</td><td>{v:,.0f}</td></tr>"
                        for i, (c, (nom, v)) in enumerate(ops.items()))
        cuerpo = (f"<table class='MapTable'><tr><td>&nbsp;</td><td>{CABECERA.get(dim, dim)}</td><td>PIA</td><td>PIM</td><td>Recaudado</td></tr></table>"
                  f"<table class='Data'>{filas}</table>")
    return (f"<html><body><form method='post' action='Navegar_{n}.aspx?y={anio}' id='form1'>"
            f"<input type='hidden' name='__EVENTTARGET' value=''/><input type='hidden' name='__EVENTARGUMENT' value=''/>"
            f"<input type='hidden' name='__VIEWSTATE' value='{vs}'/><input type='hidden' name='__EVENTVALIDATION' value='x'/>"
            f"<select name='ctl00$CPH1$DrpYear'><option value='2025'>2025</option><option value='{anio}' selected='selected'>{anio}</option></select>"
            f"{btn}<table class='History'>{hist}</table>{cuerpo}</form></body></html>").encode("utf-8")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def responder(self, b):
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query, keep_blank_values=True))
        anio = int(q.get("y", 2026)); n = 6 if anio >= 2007 else 1
        if anio == 2003:                                   # 2003: <frame src="Navegar.aspx?y=2003">, sin número
            if u.path.lower().startswith("/default.aspx"):
                return self.responder(f"<html><frameset><frame name='frame0' src='Navegar.aspx?y={anio}' /></frameset></html>".encode())
            if u.path.lower() == "/navegar.aspx":
                return self.responder(pagina(anio, [], F, 1))
            return self.responder(b"<html>Consulta Amigable Portal del MEF</html>")
        if u.path.lower().startswith("/default.aspx"):
            return self.responder(f"<html><iframe src='Navegar_6.aspx?y={anio}'></iframe></html>".encode())
        if u.path.lower() == f"/navegar_{n}.aspx":
            return self.responder(pagina(anio, [], "", n))
        self.responder(b"<html>Navegador</html>")
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        largo = int(self.headers.get("Content-Length", 0))
        datos = dict(urllib.parse.parse_qsl(self.rfile.read(largo).decode(), keep_blank_values=True))
        st = json.loads(base64.b64decode(datos["__VIEWSTATE"]))
        n = int(re.search(r"navegar_(\d+)", u.path.lower()).group(1))
        anio, filtros, dim = st["y"], [tuple(x) for x in st["f"]], st["d"]
        if datos.get("ctl00$CPH1$DrpYear") != str(anio):     # sin el año del formulario el MEF no arma la tabla
            return self.responder(b"<html><body><form></form>Consulta Amigable de Ingresos - Navegador</body></html>")
        nuevo = next((v for k, v in datos.items() if k.startswith("ctl00$CPH1$Btn")), None)
        cod = (datos.get("grp1") or "").split("/")[0]
        if nuevo is None or not cod or nuevo not in botones(anio, dict(filtros), dim):
            return self.responder(pagina(anio, filtros, dim, n))
        if dim == "":
            return self.responder(pagina(anio, [], F, n))    # TOTAL + «Fuente» → lista de fuentes (sin filtro nuevo)
        self.responder(pagina(anio, filtros + [(dim, cod)], nuevo, n))

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), H).serve_forever()
