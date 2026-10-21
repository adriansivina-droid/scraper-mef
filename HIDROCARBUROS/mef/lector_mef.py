# ── Lector del MEF (Consulta Amigable de Ingresos): canon y sobrecanon petrolero por nivel de gobierno y por municipalidad ──
# La consulta de ingresos navega por FORMULARIO ASP.NET (postback), no por URL:
#   · los filtros puestos en la URL (también en la de «Exportar») se IGNORAN: probado a mano con Navegar_1 y Navegar_6 (2026),
#     la exportación con 10=5 devolvió el total del país;
#   · cada clic = POST al Navegar_N.aspx con los campos ocultos de la página (__VIEWSTATE, __EVENTVALIDATION…),
#     grp1 = valor del radio de la fila elegida («código/PIA/PIM/recaudado») y el botón de la dimensión siguiente
#     (p. ej. ctl00$CPH1$BtnRubro=Rubro). Es lo que hace el navegador; aquí se hace con requests, sin navegador;
#   · el estado viaja en el __VIEWSTATE: cada página leída se guarda y se vuelve a enviar con otra fila para ramificar
#     (otro departamento, otro nivel) sin repetir el camino. Cada paso se valida con el historial (breadcrumb) y la
#     cabecera de la tabla; si una página guardada deja de servir, se rehace el camino desde la raíz;
#   · la página Navegar_N de cada año se toma del iframe de default.aspx?y=AAAA.
import re, time, random, unicodedata, html as _html
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://apps5.mineco.gob.pe/transparenciaingresos/mensual"
D_FUENTE, D_RUBRO, D_TIPO, D_NIVEL = "Fuente de Financiamiento", "Rubro", "Tipo de Recurso", "Nivel de Gobierno"
D_GOBLOC, D_DEPTO, D_MUNI = "Gob.Loc./Mancom.", "Departamento", "Municipalidad"
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

def _texto(td):
    return " ".join(td.get_text(" ", strip=True).split())

def misma_dim(cabecera, dim):
    c, d = norm(cabecera), norm(dim)
    return bool(c) and (c.startswith(d[:10]) or d.startswith(c[:10]))

class Pagina:
    """Página del navegador. dim: dimensión listada · filtros: historial [(etiqueta, recaudado)] (el 1.º es TOTAL) ·
    filas: [(codigo, etiqueta, recaudado)] · radios: {codigo: valor del radio} · botones: {texto: nombre} ·
    ocultos: campos ocultos del formulario · accion: destino del formulario."""
    def __init__(self, contenido, url=""):
        self.url = url
        if isinstance(contenido, bytes):
            try:
                contenido = contenido.decode("utf-8")
            except UnicodeDecodeError:
                contenido = contenido.decode("cp1252", errors="replace")
        s = BeautifulSoup(contenido, "html.parser")
        f = s.find("form")
        self.accion = _html.unescape(f.get("action") or "") if f else ""
        self.ocultos = {i.get("name"): i.get("value") or "" for i in s.find_all("input", attrs={"type": "hidden"}) if i.get("name")}
        self.botones = {" ".join((i.get("value") or "").split()): i.get("name")
                        for i in s.find_all("input", attrs={"type": "submit"}) if i.get("name")}
        data = s.find("table", class_="Data")
        self.tiene_tabla = data is not None
        mt = s.find("table", class_="MapTable")
        celdas = [_texto(td) for td in (mt.find("tr").find_all("td") if mt and mt.find("tr") else [])]
        self.dim = next((c for c in celdas if c and c not in ("PIA", "PIM", "Recaudado")), "")
        hist = s.find("table", class_="History")
        self.filtros = []
        for tr in (hist.find_all("tr") if hist else []):
            tds = [_texto(td) for td in tr.find_all("td")]
            et = next((t for t in tds if t and a_numero(t) is None), "")
            if et:
                self.filtros.append((et, a_numero(tds[-1])))
        self.filas, self.radios = [], {}
        for tr in (data.find_all("tr") if data else []):
            r = tr.find("input", attrs={"type": "radio"})
            tds = [_texto(td) for td in tr.find_all("td")]
            et = next((t for t in tds if t and a_numero(t) is None), "")
            if not et or r is None:
                continue
            partes = (r.get("value") or "").split("/")
            rec = a_numero(partes[-1]) if len(partes) >= 3 else None
            if rec is None:
                rec = a_numero(tds[-1]) or 0.0
            m = _CODIGO.match(et)
            cod = (partes[0] if partes and partes[0] else (m.group(1) if m else et)).strip()
            self.filas.append((cod, et, rec))
            self.radios[cod] = r.get("value") or ""

    def boton(self, dim):
        return next(((t, n) for t, n in self.botones.items() if misma_dim(t, dim)), None)

class MEFIngresos:
    def __init__(self, log=print, pausa=(0.8, 1.6), base=BASE):
        self.log, self.pausa, self.base = log, pausa, base.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                             "Chrome/124.0 Safari/537.36", "Accept-Language": "es-PE,es;q=0.9"})
        self.pagina = None                               # número N de Navegar_N.aspx del año abierto
        self._anio = None
        self._cache = {}                                 # (filtros…, dimensión listada) → Pagina

    def _pedir(self, metodo, url, datos=None, reintentos=3):
        err = ""
        for i in range(reintentos):
            try:
                r = self.s.request(metodo, url, data=datos, timeout=90,
                                   headers={"Referer": url if metodo == "POST" else f"{self.base}/default.aspx"})
                if r.status_code == 200:
                    time.sleep(random.uniform(*self.pausa))
                    return Pagina(r.content, r.url), None
                err = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                err = f"{type(e).__name__}: {e}"
            if i + 1 < reintentos:
                time.sleep(min(20, 2 ** i + random.random()))
        return None, err

    def preparar(self, anio, forzar=False):
        """Abre el año: default.aspx?y=AAAA y el marco que trae (Navegar_N.aspx); la raíz debe listar las fuentes."""
        if self._anio == anio and not forzar:
            return True
        self._anio, self._cache = None, {}
        try:
            r = self.s.get(f"{self.base}/default.aspx", params={"y": anio}, timeout=60)
            m = re.search(r"<iframe[^>]+src=[\"']([^\"']*Navegar_\d+\.aspx[^\"']*)[\"']", r.text, re.I)
            src = _html.unescape(m.group(1)) if m else f"Navegar_6.aspx?y={anio}"
        except requests.RequestException as e:
            self.log(f"   ❌ default.aspx {anio}: {e}"); return False
        url = urljoin(f"{self.base}/", src)
        pg, err = self._pedir("GET", url)
        if pg is None or not pg.tiene_tabla:
            self.log(f"   ❌ {anio}: el marco {url} no trajo la tabla ({err or 'sin tabla Data'})"); return False
        m = re.search(r"Navegar_(\d+)", url)
        self.pagina = m.group(1) if m else "?"
        if not misma_dim(pg.dim, D_FUENTE):
            self.log(f"   ❌ {anio}: la raíz lista «{pg.dim}», no «{D_FUENTE}» (botones: {', '.join(pg.botones)})"); return False
        self._cache[()] = pg
        self._anio = anio
        self.log(f"🔎 {anio}: Navegar_{self.pagina}.aspx · raíz con {len(pg.filas)} fuentes")
        return True

    def _postear(self, padre, cod, dim):
        """Desde la página `padre`: elige la fila `cod` y pulsa el botón de `dim`. Valida historial y cabecera."""
        if cod not in padre.radios:
            return None, f"la fila «{cod}» no está en «{padre.dim}»"
        b = padre.boton(dim)
        if b is None:
            return None, f"sin botón «{dim}» (botones: {', '.join(padre.botones) or '–'})"
        datos = dict(padre.ocultos)
        datos.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", "grp1": padre.radios[cod], b[1]: b[0]})
        pg, err = self._pedir("POST", urljoin(padre.url, padre.accion) if padre.accion else padre.url, datos)
        if pg is None:
            return None, err
        if not pg.tiene_tabla:
            return None, "SIN_TABLA (sin datos para esa combinación)"
        etq = next((e for c, e, _ in padre.filas if c == cod), cod)
        if not misma_dim(pg.dim, dim):
            return None, f"ESTADO: se pidió «{dim}» y la tabla lista «{pg.dim}»"
        if len(pg.filtros) != len(padre.filtros) + 1 or norm(etq) not in norm(pg.filtros[-1][0]):
            return None, f"ESTADO: filtro no aplicado (historial: {' › '.join(f for f, _ in pg.filtros)})"
        return pg, None

    def listar(self, anio, ruta, dim):
        """Página que lista `dim` bajo los filtros `ruta` = [(dimensión, código)…] (la primera dimensión es la de la raíz)."""
        if not self.preparar(anio):
            return None, "no se pudo abrir el año"
        if not ruta:
            pg = self._cache[()]
            return (pg, None) if misma_dim(pg.dim, dim) else (None, f"la raíz lista «{pg.dim}»")
        dims = [d for d, _ in ruta[1:]] + [dim]          # la página tras el filtro i lista dims[i]
        err = ""
        for intento in (1, 2):
            pg = self._cache[()]
            for i in range(len(ruta)):
                clave = tuple(ruta[:i + 1]) + (dims[i],)  # filtros hasta i + la dimensión que lista esa página
                if clave in self._cache:
                    pg = self._cache[clave]; continue
                nueva, err = self._postear(pg, ruta[i][1], dims[i])
                if nueva is None:
                    break
                self._cache[clave] = pg = nueva
            else:
                return pg, None
            # una página guardada ya no sirve (el estado quedó en la sesión): se rehace el camino desde la raíz
            if intento == 1 and err.startswith("ESTADO") and self.preparar(anio, forzar=True):
                continue
            break
        return None, err

    @staticmethod
    def elegir(pg, patron):
        return next(((c, e, v) for c, e, v in pg.filas if re.search(patron, e, re.I)), None)

    # ── recorrido del canon ──
    def ruta_tipos(self, anio):
        """Esquema del año: desde 2007 fuente 5 → rubro 18; hasta 2006 fuente 01 (Canon y sobrecanon). Devuelve (ruta, tipos)."""
        pg, err = self.listar(anio, [], D_FUENTE)
        if err:
            return None, [], err
        for patron, con_rubro in ((r"^0?5:\s*RECURSOS DETERMINADOS", True), (r"^0?1:\s*CANON Y SOBRECANON", False)):
            f = self.elegir(pg, patron)
            if not f:
                continue
            ruta = [(D_FUENTE, f[0])]
            if con_rubro:
                pr, err = self.listar(anio, ruta, D_RUBRO)
                if err:
                    return None, [], f"rubro: {err}"
                r18 = self.elegir(pr, r"^18:")
                if not r18:
                    return None, [], "sin rubro 18"
                ruta = ruta + [(D_RUBRO, r18[0])]
            pt, err = self.listar(anio, ruta, D_TIPO)
            if err:
                return None, [], f"tipo de recurso: {err}"
            return ruta, pt.filas, None
        return None, [], "sin fuente 5 (Recursos determinados) ni 01 (Canon y sobrecanon)"

    def niveles(self, anio, ruta, tipo):
        """Distribución por nivel de gobierno (E nacional, M locales, R regionales) de un tipo de recurso.
        Devuelve (ruta con el tipo, página «Nivel de Gobierno», error)."""
        r = ruta + [(D_TIPO, tipo[0])]
        pn, err = self.listar(anio, r, D_NIVEL)
        return r, pn, (f"nivel de gobierno: {err}" if err else None)

    def departamentos_de_nivel(self, anio, r_tipo, nivel):
        """Departamentos bajo un nivel de gobierno (si la página no ofrece «Departamento» pero sí «Gob.Loc./Mancom.»,
        pasa antes por la fila M de gobiernos locales, como en los años recientes)."""
        pn, err = self.listar(anio, r_tipo, D_NIVEL)
        if err:
            return None, None, f"nivel: {err}"
        r = r_tipo + [(D_NIVEL, nivel[0])]
        if pn.boton(D_DEPTO) is None and pn.boton(D_GOBLOC) is not None:
            pg, err = self.listar(anio, r, D_GOBLOC)
            if err:
                return None, None, f"gob. local: {err}"
            g = self.elegir(pg, r"^M:") or (pg.filas[0] if pg.filas else None)
            if g is None:
                return None, None, "gob. local sin filas"
            r = r + [(D_GOBLOC, g[0])]
        pd_, err = self.listar(anio, r, D_DEPTO)
        return r, pd_, (f"departamento: {err}" if err else None)

    def hasta_departamentos(self, anio, ruta, tipo):
        """Agrega tipo de recurso y nivel M (y gob. local si corresponde) y lista los departamentos."""
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
        """Municipalidades del departamento elegido; total = historial del departamento."""
        pm, err = self.listar(anio, ruta_dep + [(D_DEPTO, dep[0])], D_MUNI)
        if err:
            return None, None, f"municipalidad: {err}"
        return pm.filas, (pm.filtros[-1][1] if pm.filtros else None), None

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
