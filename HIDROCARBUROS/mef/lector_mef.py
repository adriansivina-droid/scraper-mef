# ── Lector: canon y sobrecanon petrolero recaudado por cada municipalidad (MEF, Consulta Amigable de Ingresos) ──
# La consulta es ASP.NET con postbacks (Navegar_3.aspx?y=AAAA + __doPostBack): no se arma por URL como la de gasto,
# así que se maneja un navegador real (Playwright): elegir la fila (radio) y pulsar el botón de la dimensión siguiente.
import re, asyncio

DIMS = ("Fuente de Financiamiento", "Rubro", "Tipo de Recurso", "Nivel de Gobierno", "Gob.Loc./Mancom.", "Sector", "Pliego",
        "Unidad Ejecutora", "Departamento", "Provincia", "Municipalidad", "Tipo de Ingreso")

JS_ESTADO = r"""() => {
  const limpio = s => (s || '').replace(/\s+/g, ' ').trim();
  const num = s => { const t = limpio(s).replace(/,/g, ''); return /^-?\d+(\.\d+)?$/.test(t) ? parseFloat(t) : null; };
  const out = {dim: null, filas: [], migas: [], botones: []};
  const radios = [...document.querySelectorAll('input[type=radio]')];
  for (const tr of document.querySelectorAll('tr')) {
    const celdas = [...tr.children].filter(x => x.tagName === 'TD' || x.tagName === 'TH');
    const tx = celdas.map(c => limpio(c.innerText));
    if (!out.dim && tx.some(t => /^Recaudado/.test(t)) && !tr.querySelector('input[type=radio]'))
      out.dim = tx.find(t => t && !/^(PIA|PIM|Recaudado)/.test(t)) || null;
    const r = tr.querySelector('input[type=radio]');
    const etiqueta = tx.find(t => /^[0-9A-ZÑ]{1,3}(-\d+)?:\s/.test(t));
    const nums = tx.map(num).filter(v => v !== null);
    if (r && etiqueta) out.filas.push({i: radios.indexOf(r), etiqueta, recaudado: nums.length ? nums[nums.length - 1] : null});
    else if (!r && etiqueta === undefined && tx.length) {
      const m = tx.find(t => /^(TOTAL|Fuente de Financiamiento|Rubro|Tipo de Recurso|Nivel de Gobierno|Gob\.Loc|Sector|Pliego|Departamento|Provincia)\b/.test(t));
      if (m && nums.length) out.migas.push({etiqueta: m, recaudado: nums[nums.length - 1]});
    }
  }
  out.botones = [...document.querySelectorAll('input[type=submit],input[type=button],button')].map(b => limpio(b.value || b.innerText)).filter(x => x);
  return out;
}"""

class MEFIngresos:
    def __init__(self, page, base, log=print, pausa=1.0):
        self.page, self.base, self.log, self.pausa = page, base.rstrip("/"), log, pausa
        self.frame = page.main_frame

    async def _esperar_recarga(self, accion, timeout=60000):
        await self.frame.evaluate("() => { window.__pp = 1; }")
        await accion()
        try:
            await self.frame.wait_for_function("() => window.__pp === undefined", timeout=timeout)
        except Exception:
            pass                                          # sin recarga (selección solo en el navegador)
        await self.frame.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(self.pausa)

    async def estado(self):
        return await self.frame.evaluate(JS_ESTADO)

    async def abrir_anio(self, anio):
        for url in (f"{self.base}/Navegar_3.aspx?y={anio}", f"{self.base}/default.aspx?y={anio}"):
            await self.page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(self.pausa)
            fr = next((f for f in self.page.frames if "navegar" in f.url.lower()), self.page.main_frame)
            self.frame = fr
            e = await self.estado()
            if e["filas"]:
                return e
        raise RuntimeError(f"{anio}: la consulta no mostró filas (¿bloqueo o cambio de la página?)")

    async def elegir(self, patron):
        e = await self.estado()
        f = next((x for x in e["filas"] if re.search(patron, x["etiqueta"], re.I)), None)
        if f is None:
            return None
        radio = self.frame.locator("input[type=radio]").nth(f["i"])
        await self._esperar_recarga(lambda: radio.click(), timeout=1500)
        return f

    async def ir_a(self, dimension):
        e = await self.estado()
        if e["dim"] and e["dim"].lower().startswith(dimension.lower()):
            return True
        if dimension not in e["botones"]:
            return False
        b = self.frame.locator(f"input[value='{dimension}'], button:has-text('{dimension}')").first
        await self._esperar_recarga(lambda: b.click())
        e = await self.estado()
        return bool(e["dim"] and e["dim"].lower().startswith(dimension.lower()))

    # dos clasificaciones: desde 2007, fuente 5 (Recursos determinados) → rubro 18 → tipo de recurso;
    # hasta 2006, fuente 01 (Canon y sobrecanon) → tipo de recurso (4: petrolero, 0: NORMAL…)
    ESQUEMAS = ([(r"^5:\s*RECURSOS DETERMINADOS", "Rubro"), (r"^18:", "Tipo de Recurso")],
                [(r"^0?1:\s*CANON Y SOBRECANON", "Tipo de Recurso")])

    async def _hasta_departamentos(self, anio, tipo_patron, esquema=0):
        """Navega hasta la lista «Departamento» (gobiernos locales) de un tipo de recurso. Devuelve la ruta o un error."""
        await self.abrir_anio(anio)
        ruta = []
        for patron, siguiente in self.ESQUEMAS[esquema] + [(tipo_patron, "Nivel de Gobierno"), (r"^M:", None)]:
            f = await self.elegir(patron)
            if f is None:
                e = await self.estado()
                return ruta + [f"NO ENCONTRADO {patron} en «{e['dim']}»"], False
            ruta.append(f["etiqueta"])
            if siguiente is None:                          # nivel M: en años recientes aparece «Gob.Loc./Mancom.» antes del departamento
                if await self.ir_a("Gob.Loc./Mancom."):
                    g = await self.elegir(r"^M:")
                    if g: ruta.append(g["etiqueta"])
                if not await self.ir_a("Departamento"):
                    return ruta + ["SIN BOTÓN Departamento"], False
            elif not await self.ir_a(siguiente):
                return ruta + [f"SIN BOTÓN {siguiente}"], False
        return ruta, True

    async def departamentos(self, anio, tipo_patron, esquema=0):
        """Departamentos con recaudado de ese tipo de recurso en gobiernos locales: [(etiqueta, recaudado)]."""
        ruta, ok = await self._hasta_departamentos(anio, tipo_patron, esquema)
        if not ok:
            return [], ruta
        e = await self.estado()
        return [(f["etiqueta"], f["recaudado"]) for f in e["filas"] if (f["recaudado"] or 0) > 0], ruta

    async def municipalidades(self, anio, tipo_patron, dep_patron=r"^16:\s*LORETO", esquema=0):
        """Filas «Municipalidad» del departamento para un tipo de recurso. Devuelve (filas, total_departamento, ruta)."""
        ruta, ok = await self._hasta_departamentos(anio, tipo_patron, esquema)
        if not ok:
            return None, None, ruta
        f = await self.elegir(dep_patron)
        if f is None:
            return None, None, ruta + [f"NO ENCONTRADO {dep_patron} en «Departamento»"]
        ruta.append(f["etiqueta"])
        if not await self.ir_a("Municipalidad"):
            return None, None, ruta + ["SIN BOTÓN Municipalidad"]
        e = await self.estado()
        total = next((m["recaudado"] for m in e["migas"] if m["etiqueta"].startswith("Departamento")), None)
        return e["filas"], total, ruta

    async def tipos_petroleros(self, anio, patron=r"PETROLER"):
        """Tipos de recurso que cumplen el patrón («PETROLERO»: 5 y K desde 2007; 4 hasta 2006): [(etiqueta, recaudado, esquema)]."""
        for esquema, pasos in enumerate(self.ESQUEMAS):
            await self.abrir_anio(anio)
            ok = True
            for pat, siguiente in pasos:
                if await self.elegir(pat) is None or not await self.ir_a(siguiente):
                    ok = False; break
            if not ok:
                continue
            e = await self.estado()
            return [(f["etiqueta"], f["recaudado"], esquema) for f in e["filas"] if re.search(patron, f["etiqueta"], re.I)]
        return []

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
