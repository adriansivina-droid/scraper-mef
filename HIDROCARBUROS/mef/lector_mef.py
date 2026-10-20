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

    async def municipalidades(self, anio, tipo_patron, dep_patron=r"^16:\s*LORETO"):
        """Filas «Municipalidad» del departamento para un tipo de recurso. Devuelve (filas, total_departamento, ruta)."""
        await self.abrir_anio(anio)
        ruta = []
        pasos = [(r"^5:\s*RECURSOS DETERMINADOS", "Rubro"), (r"^18:", "Tipo de Recurso"), (tipo_patron, "Nivel de Gobierno"),
                 (r"^M:", None), (dep_patron, "Municipalidad")]
        for patron, siguiente in pasos:
            f = await self.elegir(patron)
            if f is None:
                e = await self.estado()
                return None, None, ruta + [f"NO ENCONTRADO {patron} en «{e['dim']}»"]
            ruta.append(f["etiqueta"])
            if siguiente is None:                          # nivel M: en años recientes aparece «Gob.Loc./Mancom.» antes del departamento
                if await self.ir_a("Gob.Loc./Mancom."):
                    g = await self.elegir(r"^M:")
                    if g: ruta.append(g["etiqueta"])
                if not await self.ir_a("Departamento"):
                    return None, None, ruta + ["SIN BOTÓN Departamento"]
                continue
            if not await self.ir_a(siguiente):
                return None, None, ruta + [f"SIN BOTÓN {siguiente}"]
        e = await self.estado()
        total = next((m["recaudado"] for m in e["migas"] if m["etiqueta"].startswith("Departamento")), None)
        return e["filas"], total, ruta

    async def tipos_petroleros(self, anio):
        """Tipos de recurso del rubro 18 que dicen «PETROLERO» (5 y K, según el año)."""
        await self.abrir_anio(anio)
        for patron, siguiente in ((r"^5:\s*RECURSOS DETERMINADOS", "Rubro"), (r"^18:", "Tipo de Recurso")):
            if await self.elegir(patron) is None or not await self.ir_a(siguiente):
                return []
        e = await self.estado()
        return [(f["etiqueta"], f["recaudado"]) for f in e["filas"] if re.search("PETROLER", f["etiqueta"], re.I)]

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
