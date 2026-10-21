# ── Lector por URL: canon y sobrecanon petrolero recaudado por cada municipalidad (MEF, Consulta Amigable de Ingresos) ──
# Igual que los scrapers de FISCAL/ (Consulta Amigable de gasto): la ruta va en la URL, con requests y sin navegador.
#   Navegar_N.aspx?_tgt=frame&_uhc=yes&0=&10=<fuente>&11=<tipo>&…&<clave a listar>=&y=AAAA
#   · cada clave numérica es una dimensión; la PRIMERA clave vacía es la que se lista (lo que viene después se ignora);
#   · claves vistas en el exportUrl de la página: 0 = TOTAL, 10 = Fuente de financiamiento, 11 = Tipo de recurso, 2 = Sector;
#   · las demás (rubro, nivel de gobierno, gob. local, departamento, municipalidad) se DESCUBREN: se prueba cada clave y se lee
#     qué dimensión muestra la cabecera de la tabla. Cada filtro se valida con el breadcrumb (como en FISCAL).
import re, time, random, unicodedata
import requests
from bs4 import BeautifulSoup

BASE = "https://apps5.mineco.gob.pe/transparenciaingresos/mensual"
PAGINAS = (3, 1, 2, 4, 5, 6, 7)                 # Navegar_N.aspx: el número cambia; se calibra
# Los mismos formatos que calibran los scrapers de FISCAL/ (Consulta Amigable de gasto): el navegador pide el iframe con
# _tgt=frame&_uhc=yes y termina en ap=ActProy; se prueban también POST y las variantes sin «ap».
FORMATOS = [
    {"nombre": "navegador GET", "metodo": "GET", "pre": {"_tgt": "frame", "_uhc": "yes"}, "post": {"ap": "ActProy"}},
    {"nombre": "GET + ap", "metodo": "GET", "pre": {}, "post": {"ap": "ActProy"}},
    {"nombre": "POST + ap", "metodo": "POST", "pre": {}, "post": {"ap": "ActProy"}},
    {"nombre": "POST original", "metodo": "POST", "pre": {}, "post": {}},
    {"nombre": "frame sin ap", "metodo": "GET", "pre": {"_tgt": "frame", "_uhc": "yes"}, "post": {}},
    {"nombre": "GET simple", "metodo": "GET", "pre": {}, "post": {}},
]
CLAVES_CONOCIDAS = {"Fuente de Financiamiento": "10", "Tipo de Recurso": "11", "Sector": "2"}
CANDIDATAS = ["1", "37", "5", "7", "12", "13", "14", "15", "16", "17", "18", "19", "20", "3", "4", "6", "8", "9", "21", "22",
              "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "38", "39", "40"]
DIM_BUSCADAS = ("Rubro", "Nivel de Gobierno", "Gob.Loc./Mancom.", "Departamento", "Municipalidad")
_CODIGO = re.compile(r"^([\w\-\.]+)\s*:")

def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()

def a_numero(t):
    t = (t or "").replace(",", "").replace("\xa0", "").strip()
    try:
        return float(t)
    except ValueError:
        return None

class Pagina:
    """dim: dimensión listada (cabecera de la tabla) · filtros: breadcrumb [(etiqueta, recaudado)] ·
    filas: [(codigo, etiqueta, recaudado)] (recaudado exacto del valor del radio «código/PIA/PIM/recaudado»)."""
    def __init__(self, html, url=""):
        self.url = url
        s = BeautifulSoup(html, "html.parser")
        self.tiene_tabla = s.find("table", class_="Data") is not None
        mt = s.find("table", class_="MapTable")
        celdas = mt.find("tr").find_all("td") if mt and mt.find("tr") else []
        self.dim = " ".join(celdas[1].get_text(" ", strip=True).split()) if len(celdas) > 1 else ""
        hist = s.find("table", class_="History")
        self.filtros = []
        for tr in (hist.find_all("tr") if hist else []):
            tds = tr.find_all("td")
            if len(tds) >= 3:
                et = " ".join(tds[1].get_text(" ", strip=True).split())
                self.filtros.append((et, a_numero(tds[-1].get_text(strip=True))))
        self.filas = []
        data = s.find("table", class_="Data")
        for tr in (data.find_all("tr") if data else []):
            r = tr.find("input", attrs={"type": "radio"})
            tds = tr.find_all("td")
            if r is None or len(tds) < 3:
                continue
            et = " ".join(tds[1].get_text(" ", strip=True).split())
            partes = (r.get("value") or "").split("/")
            rec = a_numero(partes[-1]) if len(partes) >= 3 else None
            if rec is None:
                rec = a_numero(tds[-1].get_text(strip=True))
            m = _CODIGO.match(et)
            cod = partes[0] if partes and partes[0] else (m.group(1) if m else et)
            self.filas.append((cod.strip(), et, rec or 0.0))

class MEFIngresosURL:
    def __init__(self, log=print, pausa=(0.8, 1.6), base=BASE):
        self.log, self.pausa, self.base = log, pausa, base.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                             "Chrome/124.0 Safari/537.36", "Accept-Language": "es-PE,es;q=0.9",
                               "Referer": f"{self.base}/default.aspx"})
        self.pagina = self.formato = None
        self.claves = dict(CLAVES_CONOCIDAS)
        self._anio_sesion = None

    def _get(self, anio, ruta, listar, pagina=None, formato=None, reintentos=3):
        """ruta = [(clave, valor)…]; listar = clave a listar (vacía). Devuelve (Pagina | None, error)."""
        pagina, formato = pagina or self.pagina, formato or self.formato
        if self._anio_sesion != anio:                    # como el navegador: la página principal fija el año en la sesión
            try:
                self.s.get(f"{self.base}/default.aspx", params={"y": anio}, timeout=40)
            except requests.RequestException:
                pass
            self._anio_sesion = anio
        p = dict(formato["pre"]); p["0"] = ""
        for k, v in ruta:
            p[k] = v
        p[listar] = ""
        p["y"] = anio
        p.update(formato["post"])
        err = ""
        for i in range(reintentos):
            try:
                r = self.s.request(formato.get("metodo", "GET"), f"{self.base}/Navegar_{pagina}.aspx", params=p, timeout=40)
                if r.status_code == 200:
                    pg = Pagina(r.content, r.url)
                    if pg.tiene_tabla:
                        time.sleep(random.uniform(*self.pausa))
                        return pg, None
                    t = BeautifulSoup(r.content, "html.parser")
                    tit = " ".join((t.title.get_text() if t.title else "").split())
                    txt = " ".join(t.get_text(" ", strip=True).split())
                    err = f"SIN_TABLA (título «{tit[:50]}», {len(r.content):,} bytes, texto: {txt[:120]!r})"
                else:
                    err = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                err = f"{type(e).__name__}: {e}"
            time.sleep(min(20, 2 ** i + random.random()))
        return None, err

    def calibrar(self, anio):
        """Elige el Navegar_N y el formato que listan las fuentes de financiamiento."""
        for n in PAGINAS:
            for f in FORMATOS:
                pg, err = self._get(anio, [], "10", pagina=n, formato=f, reintentos=1)
                ok = pg is not None and pg.filas and norm(pg.dim).startswith("fuente")
                self.log(f"   · Navegar_{n}.aspx ({f['nombre']}): {'OK, ' + str(len(pg.filas)) + ' fuentes' if ok else (err or 'otra tabla: ' + (pg.dim if pg else ''))}")
                if ok:
                    self.pagina, self.formato = n, f
                    return True
        return False

    def descubrir(self, anio, ruta, buscadas):
        """Prueba claves candidatas bajo `ruta` y anota cuál lista cada dimensión buscada (por la cabecera de la tabla)."""
        faltan = [d for d in buscadas if d not in self.claves]
        usadas = {k for k, _ in ruta} | set(self.claves.values())
        for k in CANDIDATAS:
            if not faltan:
                break
            if k in usadas:
                continue
            pg, _ = self._get(anio, ruta, k, reintentos=1)
            if pg is None or not pg.dim:
                continue
            d = next((x for x in faltan if norm(pg.dim).startswith(norm(x)[:10])), None)
            if d:
                self.claves[d] = k; faltan.remove(d)
                self.log(f"   · clave {k} = {d}")
        return faltan

    def listar(self, anio, ruta, dim, reintentos=3):
        """Filas de la dimensión `dim` bajo `ruta`, validando que la tabla liste esa dimensión."""
        k = self.claves.get(dim)
        if k is None:
            return None, f"clave desconocida para «{dim}»"
        pg, err = self._get(anio, ruta, k, reintentos=reintentos)
        if err:
            return None, err
        if not norm(pg.dim).startswith(norm(dim)[:10]):
            return None, f"se pidió «{dim}» y la tabla lista «{pg.dim}»"
        return pg, None

    @staticmethod
    def elegir(pg, patron):
        return next(((c, e, v) for c, e, v in pg.filas if re.search(patron, e, re.I)), None)

    @staticmethod
    def filtro_aplicado(pg, etiqueta):
        """El breadcrumb termina en el filtro elegido (p. ej. «Departamento 16: LORETO»)."""
        return bool(pg.filtros) and norm(etiqueta) in norm(pg.filtros[-1][0])

    def ruta_tipos(self, anio):
        """Esquema del año: desde 2007 fuente 5 → rubro 18; hasta 2006 fuente 01 (Canon y sobrecanon). Devuelve (ruta, tipos)."""
        pg, err = self.listar(anio, [], "Fuente de Financiamiento")
        if err:
            return None, [], err
        for patron, con_rubro in ((r"^0?5:\s*RECURSOS DETERMINADOS", True), (r"^0?1:\s*CANON Y SOBRECANON", False)):
            f = self.elegir(pg, patron)
            if not f:
                continue
            ruta = [(self.claves["Fuente de Financiamiento"], f[0])]
            if con_rubro:
                if "Rubro" not in self.claves:
                    self.descubrir(anio, ruta, ["Rubro"])
                pr, err = self.listar(anio, ruta, "Rubro")
                if err:
                    return None, [], f"rubro: {err}"
                r18 = self.elegir(pr, r"^18:")
                if not r18:
                    return None, [], "sin rubro 18"
                ruta = ruta + [(self.claves["Rubro"], r18[0])]
            pt, err = self.listar(anio, ruta, "Tipo de Recurso")
            if err:
                return None, [], f"tipo de recurso: {err}"
            return ruta, pt.filas, None
        return None, [], "sin fuente 5 (Recursos determinados) ni 01 (Canon y sobrecanon)"

    def niveles(self, anio, ruta, tipo):
        """Distribución por nivel de gobierno (E nacional, M locales, R regionales) de un tipo de recurso.
        Devuelve (ruta con el tipo, página «Nivel de Gobierno», error)."""
        r = ruta + [(self.claves["Tipo de Recurso"], tipo[0])]
        if "Nivel de Gobierno" not in self.claves:
            self.descubrir(anio, r, ["Nivel de Gobierno"])
        pn, err = self.listar(anio, r, "Nivel de Gobierno")
        return r, pn, (f"nivel de gobierno: {err}" if err else None)

    def departamentos_de_nivel(self, anio, r_tipo, nivel):
        """Lista los departamentos bajo un nivel de gobierno (en M agrega «Gob.Loc./Mancom. M» si existe)."""
        r = r_tipo + [(self.claves["Nivel de Gobierno"], nivel[0])]
        if nivel[0] == "M":
            if "Gob.Loc./Mancom." not in self.claves:      # solo en años recientes; en gasto es la clave 37
                pg, _ = self._get(anio, r, "37", reintentos=1)
                if pg is not None and norm(pg.dim).startswith("gob"):
                    self.claves["Gob.Loc./Mancom."] = "37"; self.log("   · clave 37 = Gob.Loc./Mancom.")
            if "Gob.Loc./Mancom." in self.claves:
                pg, err = self.listar(anio, r, "Gob.Loc./Mancom.")
                if not err:
                    g = self.elegir(pg, r"^M:")
                    if g:
                        r = r + [(self.claves["Gob.Loc./Mancom."], g[0])]
        if "Departamento" not in self.claves:
            self.descubrir(anio, r, ["Departamento"])
        # el nivel nacional puede no tener detalle por departamento: un solo intento fuera de M
        pd_, err = self.listar(anio, r, "Departamento", reintentos=3 if nivel[0] == "M" else 1)
        return r, pd_, (f"departamento: {err}" if err else None)

    def hasta_departamentos(self, anio, ruta, tipo):
        """Agrega tipo de recurso y nivel M (y gob. local M si existe) y lista los departamentos."""
        r, pn, err = self.niveles(anio, ruta, tipo)
        if err:
            return None, None, err
        m = self.elegir(pn, r"^M:")
        if not m:
            return None, None, "sin gobiernos locales (nivel M) en este tipo de recurso"
        r, pd_, err = self.departamentos_de_nivel(anio, r, m)
        if err:
            return None, None, err
        return r, pd_, None

    def municipalidades(self, anio, ruta_dep, dep):
        """Lista las municipalidades del departamento elegido; total = breadcrumb del departamento."""
        r = ruta_dep + [(self.claves["Departamento"], dep[0])]
        if "Municipalidad" not in self.claves:
            self.descubrir(anio, r, ["Municipalidad"])
        pm, err = self.listar(anio, r, "Municipalidad")
        if err:
            return None, None, f"municipalidad: {err}"
        if not self.filtro_aplicado(pm, dep[1].split(":", 1)[1] if ":" in dep[1] else dep[1]):
            return None, None, f"el filtro de departamento no se aplicó (breadcrumb: {pm.filtros[-1][0] if pm.filtros else '–'})"
        total = pm.filtros[-1][1] if pm.filtros else None
        return pm.filas, total, None

def nombre_municipalidad(etiqueta):
    """«01-301422: MUNICIPALIDAD PROVINCIAL DE MAYNAS - IQUITOS» → (código, nivel, municipalidad, provincia)."""
    cod, _, txt = etiqueta.partition(":")
    txt = txt.strip().upper()
    m = re.match(r"MUNICIPALIDAD\s+(PROVINCIAL|DISTRITAL)\s+(?:(?:DE\s+LA|DEL|DE)\s+)?(.*)$", txt)
    if not m:
        return cod.strip(), "", txt, ""
    nivel, nom = m.group(1), m.group(2).strip()
    if nivel == "PROVINCIAL":
        prov, _, capital = nom.partition(" - ")
        return cod.strip(), nivel, (capital or prov).strip(), prov.strip()
    return cod.strip(), nivel, nom, ""
