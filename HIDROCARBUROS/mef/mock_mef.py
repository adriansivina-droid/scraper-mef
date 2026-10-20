# Simulador mínimo de la Consulta Amigable de Ingresos (postback con radio + botón de dimensión)
import json, html, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
MUNIS = {"01-301454: MUNICIPALIDAD PROVINCIAL DE REQUENA": 4819640, "06-301459: MUNICIPALIDAD DISTRITAL DE PUINAHUA": 373651,
         "01-301422: MUNICIPALIDAD PROVINCIAL DE MAYNAS - IQUITOS": 9114760}
def hijos(anio, ruta, dim):
    n = len(ruta)
    if dim == "Fuente de Financiamiento": return {"1: RECURSOS ORDINARIOS": 5, "5: RECURSOS DETERMINADOS": 100}
    if dim == "Rubro": return {"18: CANON Y SOBRECANON, REGALIAS, RENTA DE ADUANAS Y PARTICIPACIONES": 90}
    if dim == "Tipo de Recurso":
        d = {"0: CANON": 50, "5: CANON Y SOBRECANON PETROLERO": 355110316}
        if anio >= 2020: d["K: SUB CUENTA - CANON Y SOBRECANON PETROLERO"] = 546062163
        return d
    if dim == "Nivel de Gobierno": return {"E: GOBIERNO NACIONAL": 1, "M: GOBIERNOS LOCALES": 214414086}
    if dim == "Gob.Loc./Mancom.": return {"M: MUNICIPALIDADES": 214414086}
    if dim == "Departamento": return {"15: LIMA": 3, "16: LORETO": 72246640}
    if dim == "Municipalidad":
        k = 2 if ruta[2][1].startswith("K") else 1
        return {m: v * k for m, v in MUNIS.items()}
    return {}
def botones(anio, ruta, dim):
    usados = {d for d, _ in ruta} | {dim}
    todos = ["Rubro", "Tipo de Recurso", "Nivel de Gobierno", "Departamento", "Municipalidad", "Mes"]
    if anio >= 2020 and any(c.startswith("M:") for _, c in ruta) and not any(d == "Gob.Loc./Mancom." for d, _ in ruta):
        todos.insert(3, "Gob.Loc./Mancom.")
    return [b for b in todos if b not in usados]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def responder(self, anio, ruta, dim):
        filas = "".join(f"<tr onclick=\"kCod='{html.escape(k.split(':')[0])}'\"><td><input type=radio name=grp1 value='{html.escape(k)}'></td><td>{html.escape(k)}</td><td>0</td><td>0</td><td>{v:,}</td></tr>" for k, v in hijos(anio, ruta, dim).items())
        migas = "".join(f"<tr><td></td><td>{html.escape(d)} {html.escape(c)}</td><td>0</td><td>0</td><td>{(72246640 if d=='Departamento' else 1):,}</td></tr>" for d, c in ruta)
        bts = "".join(f"<input type=submit name=btn value='{b}'>" for b in botones(anio, ruta, dim))
        h = f"""<html><body><form method=post action='Navegar_3.aspx?y={anio}'><input type=hidden name=st value='{html.escape(json.dumps([ruta, dim]))}'>
        {bts}<table><tr><td></td><td>TOTAL</td><td>0</td><td>0</td><td>999</td></tr>{migas}
        <tr><td></td><td>{dim}</td><td>PIA</td><td>PIM</td><td>Recaudado</td></tr>{filas}</table></form></body></html>"""
        b = h.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "y" not in q: self.send_response(404); self.end_headers(); return
        self.responder(int(q["y"][0]), [], "Fuente de Financiamiento")
    def do_POST(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); anio = int(q["y"][0])
        f = urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        ruta, dim = json.loads(f["st"][0]); sel = f.get("grp1", [None])[0]
        if sel: ruta = ruta + [[dim, sel]]
        self.responder(anio, ruta, f["btn"][0])
ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
