# ── Lector por URL: canon y sobrecanon petrolero recaudado por cada municipalidad (MEF, Consulta Amigable de Ingresos) ──
# La navegación de ingresos es por postback (botones), pero el botón «Exportar a Excel» abre una URL con toda la ruta:
#   Navegar_1.aspx?_tgt=xls&_uhc=yes&0=&10=<fuente>&11=&y=AAAA      (probado a mano: descarga una tabla HTML con extensión .xls)
#   · 0 = TOTAL (siempre vacía y primera); luego los filtros «clave=código»; la ÚLTIMA clave vacía es la dimensión listada;
#   · cada clave numérica es una dimensión: se DESCUBREN pidiendo cada clave en la raíz y leyendo la cabecera de la tabla;
#   · cada filtro se valida con el historial (tabla History: TOTAL + una fila por filtro aplicado). Si el MEF ignora un
#     filtro, se prueban variantes del código (con/sin cero a la izquierda) y, si sigue sin aplicarse, se informa.
#   · los montos de la exportación vienen redondeados a soles enteros.
import re, time, random, unicodedata
import requests
from bs4 import BeautifulSoup

BASE = "https://apps5.mineco.gob.pe/transparenciaingresos/mensual"
PAGINAS = (6, 1, 3, 2, 4, 5, 7, 8)              # Navegar_N.aspx: cambia según el año (2026 = 6); se calibra por año
FORMATO = {"_tgt": "xls", "_uhc": "yes"}
CLAVES_PROBAR = [str(k) for k in range(1, 61)]
DIM_NECESARIAS = ("Fuente de Financiamiento", "Tipo de Recurso", "Nivel de Gobierno")
# las demás se buscan en la raíz y, si ahí no aparecen, bajo la ruta donde se necesitan
DIM_OPCIONALES = ("Rubro", "Gob.Loc./Mancom.", "Departamento", "Municipalidad")
_CODIGO = re.compile(r"^([\w\-\.]+)\s*:")
_KCOD = re.compile(r"kCod\s*=\s*[\"']([^\"']*)[\"']")

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
    """Tabla exportada. dim: dimensión listada (cabecera) · filtros: historial [(etiqueta, recaudado)] (el 1.º es TOTAL) ·
    filas: [(codigo, etiqueta, recaudado)]."""
    def __init__(self, contenido, url=""):
        self.url = url
        if isinstance(contenido, bytes):
            try:
                contenido = contenido.decode("utf-8")
            except UnicodeDecodeError:
                contenido = contenido.decode("cp1252", errors="replace")
        s = BeautifulSoup(contenido, "html.parser")
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
        self.filas = []
        for tr in (data.find_all("tr") if data else []):
            tds = [_texto(td) for td in tr.find_all("td")]
            et = next((t for t in tds if t and a_numero(t) is None), "")
            if not et or len(tds) < 2:
                continue
            k = _KCOD.search(tr.get("onclick") or "")
            m = _CODIGO.match(et)
            cod = k.group(1) if k else (m.group(1) if m else et)
            self.filas.append((cod.strip(), et, a_numero(tds[-1]) or 0.0))

def variantes(ruta):
    """La ruta tal cual y con los códigos numéricos con/sin cero a la izquierda (por si el MEF ignora el filtro)."""
    vs = [ruta,
          [(k, v.zfill(2) if v.isdigit() else v) for k, v in ruta],
          [(k, v.lstrip("0") or "0" if v.isdigit() else v) for k, v in ruta]]
    out = []
    for v in vs:
        if v not in out:
            out.append(v)
    return out

class MEFIngresosURL:
    def __init__(self, log=print, pausa=(0.8, 1.6), base=BASE):
        self.log, self.pausa, self.base = log, pausa, base.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                             "Chrome/124.0 Safari/537.36", "Accept-Language": "es-PE,es;q=0.9",
                               "Referer": f"{self.base}/default.aspx"})
        self.pagina = 1
        self.claves = {}
        self._anio_sesion = self._cal_anio = None
        self._no_hay = set()

    def url(self, anio, ruta, listar, pagina=None):
        q = "&".join([f"{k}={v}" for k, v in FORMATO.items()] + ["0="] + [f"{k}={v}" for k, v in ruta] + [f"{listar}=", f"y={anio}"])
        return f"{self.base}/Navegar_{pagina or self.pagina}.aspx?{q}"

    def _bajar(self, anio, ruta, listar, pagina=None, reintentos=3):
        if self._anio_sesion != anio:                    # como el navegador: la página principal fija el año en la sesión
            try:
                self.s.get(f"{self.base}/default.aspx", params={"y": anio}, timeout=40)
            except requests.RequestException:
                pass
            self._anio_sesion = anio
        u, err = self.url(anio, ruta, listar, pagina), ""
        for i in range(reintentos):
            try:
                r = self.s.get(u, timeout=90)
                if r.status_code == 200:
                    pg = Pagina(r.content, u)
                    if pg.tiene_tabla:
                        time.sleep(random.uniform(*self.pausa))
                        return pg, None
                    t = BeautifulSoup(r.content, "html.parser")
                    txt = " ".join(t.get_text(" ", strip=True).split())
                    err = f"SIN_TABLA ({len(r.content):,} bytes, texto: {txt[:120]!r})"
                else:
                    err = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                err = f"{type(e).__name__}: {e}"
            if i + 1 < reintentos:
                time.sleep(min(20, 2 ** i + random.random()))
        return None, err

    def _get(self, anio, ruta, listar, pagina=None, reintentos=3):
        """ruta = [(clave, código)…]; listar = clave a listar. Exige que el historial muestre todos los filtros."""
        err = ""
        for rv in variantes(ruta):
            pg, err = self._bajar(anio, rv, listar, pagina, reintentos)
            if pg is None:
                return None, err
            if len(pg.filtros) >= len(ruta) + 1:
                return pg, None
            err = (f"FILTRO_IGNORADO: el MEF aplicó {max(0, len(pg.filtros) - 1)} de {len(ruta)} filtros "
                   f"(historial: {' › '.join(f for f, _ in pg.filtros) or '–'}) · {pg.url}")
            reintentos = 1
        return None, err

    def _descubrir_raiz(self, anio, claves, buscadas):
        """Pide cada clave en la raíz (0=&k=) y anota qué dimensión lista según la cabecera."""
        for k in CLAVES_PROBAR:
            if not buscadas:
                break
            if k in claves.values():
                continue
            pg, _ = self._bajar(anio, [], k, reintentos=1)
            if pg is None or not pg.dim:
                continue
            d = next((x for x in buscadas if misma_dim(pg.dim, x)), None)
            if d:
                claves[d] = k; buscadas.remove(d)
                self.log(f"     clave {k:>2} = {pg.dim}")

    def _prueba_filtro(self, anio):
        """Tipos de recurso bajo una fuente: el historial debe mostrar la fuente (si no, esta página ignora los filtros)."""
        pf, err = self.listar(anio, [], "Fuente de Financiamiento")
        if err:
            return f"fuentes: {err}"
        f = self.elegir(pf, r"RECURSOS DETERMINADOS|CANON") or pf.filas[0]
        pt, err = self.listar(anio, [(self.claves["Fuente de Financiamiento"], f[0])], "Tipo de Recurso")
        if err:
            return err
        self.log(f"   · filtro OK en Navegar_{self.pagina}: {pt.filtros[-1][0]} → {len(pt.filas)} tipos de recurso")
        return None

    def preparar(self, anio):
        """Deja lista la página y las claves del año: primero prueba las del año anterior; si no sirven, recalibra."""
        if self._cal_anio == anio:
            return True
        if self.claves and self._prueba_filtro(anio) is None:
            self._cal_anio = anio
            return True
        ok = self.calibrar(anio)
        self._cal_anio = anio if ok else None
        return ok

    def calibrar(self, anio):
        """Elige el Navegar_N cuya exportación SÍ aplica los filtros (en 2026 la navegación usa Navegar_6; Navegar_1 exporta
        pero ignora la fuente) y descubre la clave de cada dimensión en esa página."""
        self.log(f"🔎 Calibrando la consulta de {anio}…")
        for n in PAGINAS:
            self.pagina, self.claves = n, {}
            pg, err = self._bajar(anio, [], "10", reintentos=1)
            if pg is None:
                self.log(f"   · Navegar_{n}.aspx: {err}"); continue
            self.log(f"   · Navegar_{n}.aspx exporta; claves:")
            self._descubrir_raiz(anio, self.claves, ["Fuente de Financiamiento", "Tipo de Recurso"])
            if len(self.claves) < 2:
                self.log("     sin fuente o tipo de recurso"); continue
            err = self._prueba_filtro(anio)
            if err:
                self.log(f"     ✗ {err}"); continue
            resto = [d for d in DIM_NECESARIAS + DIM_OPCIONALES if d not in self.claves]
            self._descubrir_raiz(anio, self.claves, resto)
            faltan = [d for d in DIM_NECESARIAS if d not in self.claves]
            if faltan:
                self.log(f"     ✗ no se encontró la clave de: {', '.join(faltan)}"); continue
            return True
        self.claves = {}
        return False

    def descubrir(self, anio, ruta, buscadas):
        """Prueba claves candidatas bajo `ruta` y anota cuál lista cada dimensión buscada (por la cabecera de la tabla)."""
        faltan = [d for d in buscadas if d not in self.claves and (anio, d) not in self._no_hay]
        usadas = {k for k, _ in ruta} | set(self.claves.values())
        for k in CLAVES_PROBAR:
            if not faltan:
                break
            if k in usadas:
                continue
            pg, _ = self._get(anio, ruta, k, reintentos=1)
            if pg is None or not pg.dim:
                continue
            d = next((x for x in faltan if misma_dim(pg.dim, x)), None)
            if d:
                self.claves[d] = k; faltan.remove(d)
                self.log(f"   · clave {k} = {d}")
        self._no_hay |= {(anio, d) for d in faltan}
        return faltan

    def listar(self, anio, ruta, dim, reintentos=3):
        """Filas de la dimensión `dim` bajo `ruta`, validando que la tabla liste esa dimensión."""
        k = self.claves.get(dim)
        if k is None:
            return None, f"clave desconocida para «{dim}»"
        pg, err = self._get(anio, ruta, k, reintentos=reintentos)
        if err:
            return None, err
        if not misma_dim(pg.dim, dim):
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
        if not self.preparar(anio):
            return None, [], "ningún Navegar_N aplicó los filtros en la exportación (ver calibración)"
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
        pn, err = self.listar(anio, r, "Nivel de Gobierno")
        return r, pn, (f"nivel de gobierno: {err}" if err else None)

    def departamentos_de_nivel(self, anio, r_tipo, nivel):
        """Lista los departamentos bajo un nivel de gobierno (en M agrega «Gob.Loc./Mancom. M» si existe)."""
        r = r_tipo + [(self.claves["Nivel de Gobierno"], nivel[0])]
        if nivel[0] == "M":
            if "Gob.Loc./Mancom." not in self.claves and anio >= 2015:
                self.descubrir(anio, r, ["Gob.Loc./Mancom.", "Departamento"])
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
