# Simulador de la Consulta Amigable de Ingresos por URL (estructura del HTML real: MapTable, History, Data, radio «cód/PIA/PIM/rec»).
# Claves simuladas: 10 fuente · 12 rubro · 11 tipo · 1 nivel · 37 gob.loc · 5 departamento · 7 municipalidad · 23 mes.
# Uso: python3 mock_mef_url.py  (puerto 8766)
import urllib.parse, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
NOMBRES = {"10": "Fuente de Financiamiento", "12": "Rubro", "11": "Tipo de Recurso", "1": "Nivel de Gobierno",
           "37": "Gob.Loc./Mancom.", "5": "Departamento", "7": "Municipalidad", "23": "Mes"}
MUNIS = {"01-301454": ("MUNICIPALIDAD PROVINCIAL DE REQUENA", 4819640.25), "06-301459": ("MUNICIPALIDAD DISTRITAL DE PUINAHUA", 373651.10),
         "01-301422": ("MUNICIPALIDAD PROVINCIAL DE MAYNAS - IQUITOS", 9114760.40)}

def opciones(anio, f, k):
    nuevo = anio >= 2007
    if k == "10":
        return {"1": "RECURSOS ORDINARIOS", "5": "RECURSOS DETERMINADOS"} if nuevo else {"00": "RECURSOS ORDINARIOS", "01": "CANON Y SOBRECANON"}
    if k == "12":
        return {"18": "CANON Y SOBRECANON, REGALIAS, RENTA DE ADUANAS Y PARTICIPACIONES"} if f.get("10") == "5" else None
    if k == "11":
        if nuevo:
            d = {"0": "CANON", "5": "CANON Y SOBRECANON PETROLERO"}
            if anio >= 2020: d["K"] = "SUB CUENTA - CANON Y SOBRECANON PETROLERO"
            return d if "12" in f else None
        return {"0": "NORMAL"} if anio == 2005 else {"0": "NORMAL", "4": "CANON Y SOBRECANON PETROLERO"}
    if k == "1":
        if anio <= 2004: return {"E": "GOBIERNO NACIONAL"}
        if anio < 2007 and f.get("11") == "0" and anio != 2005: return {"E": "GOBIERNO NACIONAL"}
        return {"E": "GOBIERNO NACIONAL", "M": "GOBIERNOS LOCALES"}
    if k == "37":
        return {"M": "MUNICIPALIDADES"} if anio >= 2020 and f.get("1") == "M" else None
    if k == "5":
        return {"15": "LIMA", "16": "LORETO"} if f.get("1") == "M" else None
    if k == "7":
        if "5" not in f: return None
        mult = 2 if f.get("11") == "K" else 1
        return {c: (n, v * mult) for c, (n, v) in MUNIS.items()}
    if k == "23":
        return {"1": "ENERO", "2": "FEBRERO"}
    return None

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
        if not u.path.lower().startswith("/navegar_3.aspx"):
            self.send_response(200); self.end_headers(); self.wfile.write(b"<html><title>Consulta Amigable de Ingresos</title></html>"); return
        anio = int(dict(q).get("y", 2007)); f = {}; listar = None
        for k, v in q:
            if k in ("0", "y", "_tgt", "_uhc"): continue
            if v == "" and listar is None: listar = k
            elif listar is None: f[k] = v
        ops = opciones(anio, f, listar) if listar else None
        hist = "<tr><td></td><td>TOTAL</td><td>1</td><td>1</td><td>999,999</td></tr>"
        for k, v in f.items():
            o = opciones(anio, {kk: vv for kk, vv in f.items() if kk != k}, k) or {}
            nom = o.get(v, "?"); nom = nom[0] if isinstance(nom, tuple) else nom
            tot = 14308051.75 if k == "5" else 1000
            if k == "5" and f.get("11") == "K": tot *= 2
            hist += f"<tr><td></td><td>{NOMBRES.get(k, k)} {v}: {html.escape(nom)}</td><td>0</td><td>0</td><td>{tot:,.0f}</td></tr>"
        if ops is None:
            b = f"<html><body><table class='History'>{hist}</table><p>sin datos</p></body></html>".encode()
        else:
            filas = ""
            for c, n in ops.items():
                nom, val = n if isinstance(n, tuple) else (n, 100.0)
                filas += (f"<tr><td><input type='radio' name='grp1' value='{c}/0/0/{val:.2f}'></td><td>{c}: {html.escape(nom)}</td>"
                          f"<td>0</td><td>0</td><td>{val:,.0f}</td></tr>")
            b = (f"<html><body><table class='History'>{hist}</table><table class='MapTable'><tr><td>&nbsp;</td><td>{NOMBRES.get(listar, listar)}</td>"
                 f"<td>PIA</td><td>PIM</td><td>Recaudado</td></tr></table><table class='Data'>{filas}</table></body></html>").encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), H).serve_forever()
