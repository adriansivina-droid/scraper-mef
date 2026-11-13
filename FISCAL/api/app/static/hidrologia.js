// Hidrología: nivel y caudal de los ríos (SENAMHI). Sección de cada región: el hidrograma como el de SENAMHI,
// la descarga de los datos del scraper y la subida del archivo que deja el recolector del navegador.
// window.HIDRO.pintar(region, caja, pestaña) dibuja la pestaña pedida dentro de «caja».
(function () {
  "use strict";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"];
  const num = (v, d = 2) => v == null ? "—" : Number(v).toLocaleString("es-PE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const dmy = (iso) => iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "—";
  const titulo = (t) => String(t || "").toLowerCase().replace(/(^|\s)(\S)/g, (m, a, b) => a + b.toUpperCase()).replace(/ (De|Del|La|Los|Las|El|Y) /g, (m) => m.toLowerCase());
  const VAR = { NIVEL: "Nivel", CAUDAL: "Caudal" };
  const RECOLECTOR = "https://raw.githubusercontent.com/adriansivina-droid/scraper-mef/main/HIDROLOGIA/senamhi_navegador.js";
  const SENAMHI = "https://www.senamhi.gob.pe/?p=monitoreo-hidrologico";
  // favorito: en la página de SENAMHI carga el recolector y lo pone a trabajar; en cualquier otra, lleva a SENAMHI
  // línea para la consola (F12): solo carga el recolector y muestra su panel; la descarga empieza cuando se pulsa «Iniciar»
  const CONSOLA = `fetch('${RECOLECTOR}').then(r=>r.text()).then(eval)`;
  const FAVORITO = `javascript:(function(){if(!/senamhi\\.gob\\.pe$/.test(location.hostname)){location.href='${SENAMHI}';return}fetch('${RECOLECTOR}').then(function(r){return r.text()}).then(eval)})()`;

  async function api(url, opciones) {
    const r = await fetch(url, opciones);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : `El servidor respondió ${r.status}.`);
    return j;
  }

  // ── alerta: la calcula el servidor con un doble control (hidrologia.evaluar_alerta) y aquí solo se presenta ──
  // estados: confirmada (la página y el mapa de SENAMHI coinciden) · senamhi (solo SENAMHI marca alerta) · sin_confirmar (calculada,
  // falta el color de SENAMHI) · a_verificar (no pasó los controles) · normal · sin_umbral · sin_dato (dato viejo)
  const CLASE = { confirmada: "", senamhi: "", sin_confirmar: " hid-sinconf", a_verificar: " hid-verificar", normal: "", sin_umbral: "", sin_dato: " hid-sindato" };
  function alerta(u) {
    const a = u && u.alerta;
    if (!a || a.estado === "sin_umbral") return null;
    const nivel = a.nivel === "roja" ? "rojo" : a.nivel === "amarilla" ? "amarillo" : a.nivel || "normal";
    return { nivel: ["normal", "amarillo", "naranja", "rojo"].includes(nivel) && a.estado !== "a_verificar" && a.estado !== "sin_dato" ? nivel : "neutro", texto: a.texto, estado: a.estado, motivos: a.motivos || [], clase: CLASE[a.estado] || "" };
  }
  const chip = (a) => a ? `<span class="chip hid-${a.nivel}${a.clase}" title="${esc(a.motivos.join(". "))}">${esc(a.texto)}</span>` : '<span class="nota">sin umbrales</span>';

  // ── el hidrograma, con el aspecto del de SENAMHI ──
  // series en el orden de la leyenda de SENAMHI; cada una se muestra u oculta con un clic en la leyenda
  const SERIE = [["promedio", "Prom. Histórico", "#2EAA4A", 2], ["minimo", "Min", "#772244", 1.2], ["maximo", "Max", "#808080", 1.2],
    ["anterior", null, "#1AB6F9", 2], ["actual", null, "#1A1AD6", 2.8], ["rojo", "Rojo", "#E0281E", 1.8], ["naranja", "Naranja", "#F28C00", 1.8], ["amarillo", "Amarillo", "#E8D21A", 1.8]];
  // colores de los años, del más reciente al más antiguo: elegidos para que cualquier par (y con el promedio y los umbrales) se
  // distinga a simple vista: diferencia de color CIEDE2000 de al menos 22 entre todos (26 con hasta 6 años); por debajo de ~10 se confunden
  const PALETA = ["#1A1AD6", "#1AB6F9", "#574B19", "#FA42FA", "#226E77", "#772244", "#111111", "#6973D3", "#6D2303"];
  const colorAnio = (s, k) => PALETA[(s.claves.length - 1 - s.claves.indexOf(k)) % PALETA.length];
  // series que se dibujan: al comparar, el promedio, los años marcados (del más antiguo al más reciente) y los umbrales
  function serieDe(s, vista) {
    if (!s.comparar) return SERIE;
    const ys = s.claves.filter((k) => vista.marcados.has(k));
    return [["promedio", "Prom. Histórico", "#2EAA4A", 2], ...ys.map((k) => [k, etqAño(s, k), colorAnio(s, k), k === s.claves[s.claves.length - 1] ? 2.8 : 2]),
      ["rojo", "Rojo", "#E0281E", 1.8], ["naranja", "Naranja", "#F28C00", 1.8], ["amarillo", "Amarillo", "#E8D21A", 1.8]];
  }
  const etqAño = (s, k, corto) => s.cal ? k.slice(1) : corto ? `${k.slice(1)}-${String(+k.slice(1) + 1).slice(2)}` : `${k.slice(1)} - ${+k.slice(1) + 1}`;
  // de la respuesta de /anios (años hidrológicos, eje 1/9–31/8) a años calendario (eje 1/1–31/12): enero–agosto del año Y es el
  // año hidrológico Y-1; setiembre–diciembre, el Y. El promedio y los umbrales son por día del año, así que se copian igual
  function alCalendario(A) {
    const pos = {}, b0 = Date.parse(A.desde + "T00:00:00Z");
    for (let i = 0; i < A.dias; i++) { const d = new Date(b0 + i * 864e5); pos[(d.getUTCMonth() + 1) + "-" + d.getUTCDate()] = i; }
    const e0 = Date.UTC(2024, 0, 1), md = [];                 // eje de referencia: 2024 (tiene 29 de febrero)
    for (let i = 0; i < 366; i++) { const d = new Date(e0 + i * 864e5); md.push([d.getUTCMonth() + 1, d.getUTCDate()]); }
    const toma = (arr, [m, d]) => (arr ? arr[pos[m + "-" + d]] : null) ?? null;
    const años = {}, hid = Object.keys(A.años).map(Number);
    for (const y of [...new Set(hid.flatMap((h) => [h, h + 1]))].sort()) {
      const v = md.map((x) => toma(x[0] >= 9 ? A.años[y] : A.años[y - 1], x));
      if (v.some((x) => x != null) && y >= +(A.inicio || "0").slice(0, 4)) años[y] = v;      // desde el año en que empieza la recolección
    }
    const fija = (k) => md.map((x) => toma(A[k], x));
    return { ...A, desde: "2024-01-01", dias: 366, años, promedio: fija("promedio"), rojo: fija("rojo"), naranja: fija("naranja"), amarillo: fija("amarillo") };
  }
  // el 29 de febrero solo existe en años bisiestos: en los demás se completa con el promedio del 28/2 y el 1/3 para que la línea no se corte
  function sin29(S) {
    const i = Array.from({ length: S.dias }, (_, k) => new Date(Date.parse(S.desde + "T00:00:00Z") + k * 864e5)).findIndex((d) => d.getUTCMonth() === 1 && d.getUTCDate() === 29);
    if (i <= 0) return;
    for (const k of [...S.claves, "promedio", "rojo", "naranja", "amarillo"]) {
      const a = S[k];
      if (a && a[i] == null && a[i - 1] != null && a[i + 1] != null) a[i] = Math.round((a[i - 1] + a[i + 1]) / 2 * 1e4) / 1e4;
    }
  }
  const puntoDe = (s, vista) => s.comparar ? [...s.claves].reverse().find((k) => vista.marcados.has(k)) : "actual";   // la serie que lleva el punto del último dato
  const FECHA = (x0, i) => new Date(x0.getTime() + i * 864e5);
  const dd = (n) => String(n).padStart(2, "0");

  function hidrograma(s, vista) {
    const i0 = vista.i0, i1 = vista.i1, n = i1 - i0 + 1, x0 = FECHA(new Date(s.desde + "T00:00:00Z"), i0), ocultas = vista.ocultas || new Set();
    const W = 920, izq = 74, der = 22, arr = 70, alto = 300, et = nombres(s, vista);
    const parte = (k) => s[k].slice(i0, i1 + 1), SER = serieDe(s, vista), pk = puntoDe(s, vista);
    const visibles = SER.filter(([k]) => !ocultas.has(k) && parte(k).some((v) => v != null));
    const todos = visibles.flatMap(([k]) => parte(k)).filter((v) => v != null);
    if (!todos.length) return null;
    let lo = Math.min(...todos), hi = Math.max(...todos);
    const margen = (hi - lo || Math.abs(hi) || 1) * 0.05; lo -= margen; hi += margen;
    const paso = (() => { const b = (hi - lo) / 8, p = 10 ** Math.floor(Math.log10(b)), f = b / p; return (f < 1.5 ? 1 : f < 2.25 ? 2 : f < 3.5 ? 2.5 : f < 7.5 ? 5 : 10) * p; })();
    const dec = Math.max(0, Math.min(3, -Math.floor(Math.log10(paso) + 1e-9) + (paso / 10 ** Math.floor(Math.log10(paso)) === 2.5 ? 1 : 0)));
    lo = Math.floor(lo / paso) * paso; hi = Math.ceil(hi / paso) * paso;
    const ancho = W - izq - der;
    const X = (i) => izq + (n > 1 ? ancho * i / (n - 1) : ancho / 2), Y = (v) => arr + alto * (1 - (v - lo) / (hi - lo));
    const camino = (vals) => { let d = "", abierto = false; vals.forEach((v, i) => { if (v == null) { abierto = false; return; } d += `${abierto ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; abierto = true; }); return d; };
    let rejilla = "";
    for (let v = lo; v <= hi + paso / 2; v += paso) rejilla += `<line x1="${izq}" x2="${W - der}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#E3E3E3"/><text x="${izq - 8}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${num(v, dec)}</text>`;
    // eje de fechas: días en tramos cortos; el 1 de cada mes (o cada 2, 3, 6 meses) en los largos
    let eje = "";
    const marca = (i, t) => `<line x1="${X(i).toFixed(1)}" x2="${X(i).toFixed(1)}" y1="${arr + alto}" y2="${arr + alto + 6}" stroke="#9A9A9A"/><text x="${X(i).toFixed(1)}" y="${arr + alto + 20}" text-anchor="middle">${t}</text>`;
    if (n <= 75) {
      const cada = n <= 16 ? 1 : n <= 32 ? 3 : 7;
      for (let i = 0; i < n; i += cada) { const d = FECHA(x0, i); eje += marca(i, `${dd(d.getUTCDate())} ${MES[d.getUTCMonth()]}${i === 0 && !s.comparar ? " " + d.getUTCFullYear() : ""}`); }
    } else {
      const nm = n / 30.4, cada = nm <= 8 ? 1 : nm <= 14 ? 2 : nm <= 28 ? 3 : 6;
      let primero = true;
      for (let i = 0; i < n; i++) { const d = FECHA(x0, i); if (d.getUTCDate() === 1 && (d.getUTCMonth() - 8 + 12) % cada === 0) { eje += marca(i, `01 ${MES[d.getUTCMonth()]}${(d.getUTCMonth() === 0 || primero) && !s.comparar ? " " + d.getUTCFullYear() : ""}`); primero = false; } }
    }
    const UMB = ["rojo", "naranja", "amarillo"];                 // los umbrales van con línea discontinua: no se confunden con los años
    const trazos = visibles.map(([k, , c, w]) => { const d = camino(parte(k)); return d ? `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linejoin="round"${UMB.includes(k) ? ' stroke-dasharray="9 5"' : ""}/>` : ""; }).join("");
    const ult = pk ? parte(pk).reduce((a, v, i) => v != null ? i : a, -1) : -1;
    const punto = ult >= 0 && !ocultas.has(pk) ? `<circle cx="${X(ult).toFixed(1)}" cy="${Y(parte(pk)[ult]).toFixed(1)}" r="3.5" fill="${(SER.find((x) => x[0] === pk) || [])[2]}" stroke="#FFF" stroke-width="1.5"/>` : "";
    // leyenda abajo, en filas centradas, como la de SENAMHI
    const items = SER.filter(([k]) => s[k].some((v) => v != null)).map(([k, t, c]) => {
      const u = ["rojo", "naranja", "amarillo"].includes(k) ? parte(k).filter((v) => v != null).pop() : null;
      return { k, c, t: (t || et[k]) + (u != null ? ` ${num(u, 2)}` : "") };
    });
    const filas = [[]]; let lx = 0;
    items.forEach((it) => { const w = 34 + it.t.length * 6.9; if (lx + w > ancho && filas[filas.length - 1].length) { filas.push([]); lx = 0; } filas[filas.length - 1].push({ ...it, w }); lx += w; });
    const H = arr + alto + 48 + filas.length * 20 + 14;
    const leyenda = filas.map((f, r) => { const tot = f.reduce((a, it) => a + it.w, 0); let x = izq + (ancho - tot) / 2; const y = arr + alto + 48 + r * 20;
      return f.map((it) => { const o = ocultas.has(it.k), g = `<g data-serie="${it.k}" style="cursor:pointer" opacity="${o ? 0.35 : 1}"><rect x="${x}" y="${y - 12}" width="${it.w - 6}" height="18" fill="#FFF" fill-opacity="0"/><line x1="${x}" x2="${x + 22}" y1="${y - 3}" y2="${y - 3}" stroke="${it.c}" stroke-width="3"${["rojo", "naranja", "amarillo"].includes(it.k) ? ' stroke-dasharray="6 3"' : ""}/><text x="${x + 28}" y="${y + 1}" fill="#333" font-weight="600">${esc(it.t)}</text></g>`; x += it.w; return g; }).join(""); }).join("");
    const Var = VAR[s.variable].toUpperCase();
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="'Segoe UI', Arial, sans-serif" font-size="12" fill="#555" role="img" aria-label="Hidrograma de ${esc(s.estacion)}">
      <rect width="${W}" height="${H}" fill="#FFF"/>
      <text x="${W / 2}" y="26" text-anchor="middle" font-size="17" font-weight="600" fill="#333">HIDROGRAMA DE ${Var} DEL ${esc(String(s.rio || "").toUpperCase())}</text>
      <text x="${W / 2}" y="47" text-anchor="middle" font-size="12" fill="#666">ESTACIÓN ${esc(String(s.estacion || "").toUpperCase())}</text>
      <text transform="translate(18 ${arr + alto / 2}) rotate(-90)" text-anchor="middle" fill="#333">${Var} (${esc(s.unidad)})</text>
      ${rejilla}<line x1="${izq}" x2="${W - der}" y1="${arr + alto}" y2="${arr + alto}" stroke="#9A9A9A"/>${eje}
      ${trazos}${punto}${leyenda}
      <text x="${izq}" y="${H - 10}" font-size="11" fill="#777">${esc(et.periodo)}</text>
      <text x="${W - der}" y="${H - 10}" text-anchor="end" font-size="11" fill="#777">Fuente: SENAMHI</text></svg>`;
    return { svg, W, H, izq, der, arr, alto, n, x0, dec, i0 };
  }

  // barra de navegación (como la de SENAMHI): toda la serie en pequeño y el tramo visible, que se arrastra o se estira
  function navegador(s, vista) {
    const W = 920, H = 58, izq = 74, der = 22, n = s.dias, x0 = new Date(s.desde + "T00:00:00Z"), ancho = W - izq - der;
    const X = (i) => izq + ancho * i / Math.max(1, n - 1);
    const pk = puntoDe(s, vista), base = s.comparar ? (s[pk] || s.promedio) : s.actual.some((v) => v != null) ? s.actual : s.anterior, otro = s.comparar ? null : s.año != null ? s.anterior : null;
    const vals = [...base, ...(otro || [])].filter((v) => v != null);
    const lo = Math.min(...vals), hi = Math.max(...vals), Y = (v) => 6 + 36 * (1 - (v - lo) / (hi - lo || 1));
    const linea = (arr, c, op) => { let d = "", ab = false; arr.forEach((v, i) => { if (v == null) { ab = false; return; } d += `${ab ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; ab = true; }); return d ? `<path d="${d}" fill="none" stroke="${c}" stroke-width="1.2" opacity="${op}"/>` : ""; };
    let marcas = "";
    const nm = n / 30.4, cada = nm <= 14 ? 2 : nm <= 30 ? 4 : 6;
    for (let i = 0; i < n; i++) { const d = FECHA(x0, i); if (d.getUTCDate() === 1 && (d.getUTCMonth() - 8 + 12) % cada === 0) marcas += `<text x="${X(i).toFixed(1)}" y="${H - 3}" text-anchor="middle">${MES[d.getUTCMonth()]}${s.comparar ? "" : " " + String(d.getUTCFullYear()).slice(2)}</text>`; }
    const a = X(vista.i0), b = X(vista.i1);
    const asa = (x, k) => `<g data-nav="${k}" style="cursor:ew-resize"><rect x="${x - 6}" y="8" width="12" height="30" fill="transparent"/><rect x="${x - 4}" y="14" width="8" height="18" rx="2" fill="#F2F2F2" stroke="#888"/><line x1="${x - 1}" x2="${x - 1}" y1="18" y2="28" stroke="#888"/><line x1="${x + 1}" x2="${x + 1}" y1="18" y2="28" stroke="#888"/></g>`;
    return { W, izq, ancho, n, svg: `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="'Segoe UI', Arial, sans-serif" font-size="10" fill="#777" style="touch-action:none">
      <rect x="${izq}" y="4" width="${ancho}" height="40" fill="#F4F6FA" stroke="#CCD3DF"/>${otro ? linea(otro, "#4FA8EE", 0.6) : ""}${linea(base, "#5A6FA8", 1)}
      <rect data-nav="tramo" x="${a}" y="4" width="${Math.max(2, b - a)}" height="40" fill="#6685C2" fill-opacity="0.22" stroke="#6685C2" style="cursor:grab"/>
      ${asa(a, "ini")}${asa(b, "fin")}${marcas}</svg>` };
  }

  const tramoTxt = (s, vista) => { const f = (k) => FECHA(new Date(s.desde + "T00:00:00Z"), k); const t = (d) => `${d.getUTCDate()} ${MES[d.getUTCMonth()]}`; return `${t(f(vista.i0))} al ${t(f(vista.i1))}`; };
  // nombres de las series: por año hidrológico o por rango de fechas
  function nombres(s, vista) {
    const fi = (k) => FECHA(new Date(s.desde + "T00:00:00Z"), k).toISOString().slice(0, 10);
    const d = fi(vista ? vista.i0 : 0), h = fi(vista ? vista.i1 : s.dias - 1);
    if (s.comparar) {
      const ys = s.claves.filter((k) => vista && vista.marcados.has(k)).map((k) => etqAño(s, k, true));
      const recorte = vista && (vista.i0 > 0 || vista.i1 < s.dias - 1) ? ` · del ${tramoTxt(s, vista)}` : "";
      return { periodo: `${s.cal ? "Años" : "Años hidrológicos (set–ago)"}: ${ys.join(", ") || "ninguno"}${recorte}`, archivo: `anios_${ys.join("_")}` };
    }
    if (s.año != null) return { actual: `${s.año} - ${s.año + 1}`, anterior: `${s.año - 1} - ${s.año}`, archivo: `${s.año}-${s.año + 1}`,
      periodo: `Año hidrológico ${s.año}-${s.año + 1}${vista && (vista.i0 > 0 || vista.i1 < s.dias - 1) ? ` · del ${dmy(d)} al ${dmy(h)}` : ""}` };
    return { actual: "Valor diario", anterior: "Un año antes", periodo: `Del ${dmy(d)} al ${dmy(h)}`, archivo: `${d}_a_${h}` };
  }

  // ── pestaña «Gráfico» ──
  const st = {};                                              // por región: estación, variable y año elegidos
  async function grafico(r, caja) {
    caja.innerHTML = '<div class="loading"><span class="spin"></span>Leyendo las estaciones…</div>';
    let j;
    try { j = await api(`/v1/hidrologia/estaciones?departamento=${r.cod}`); }
    catch (e) { caja.innerHTML = `<div class="err-box"><b>No se pudo leer</b><span>${esc(e.message)}</span></div>`; return; }
    ponerHasta(j.resumen);
    if (!j.estaciones.length) {
      caja.innerHTML = `<div class="vacio-caja"><b>${j.resumen.hay ? `SENAMHI no tiene estaciones con datos en ${esc(r.nombre)}.` : "Todavía no hay datos de SENAMHI en la página."}</b><span>${j.resumen.hay ? "Los datos de las demás regiones están en «Descargar datos»." : (HIDRO.invitado ? "Vuelve a consultar más tarde." : "Ve a la pestaña «Actualizar»: allí se sube el archivo que deja el recolector.")}</span></div>`;
      return;
    }
    const e0 = st[r.cod] || (st[r.cod] = {}), pais = r.cod === "todos";
    if (pais) j.estaciones.sort((a, b) => (a.zonal || "99").localeCompare(b.zonal || "99") || a.rio.localeCompare(b.rio) || a.estacion.localeCompare(b.estacion));
    const filas = j.estaciones.flatMap((e) => Object.entries(e.variables).map(([v, d]) => ({ e, v, d })));
    const dudosas = pais ? 0 : j.estaciones.filter((e) => !e.departamento_seguro).length;
    const zonas = [...new Set(j.estaciones.map((e) => e.zonal).filter(Boolean))].sort();
    caja.innerHTML = `${pais ? `<div class="caja"><h3>Red de monitoreo hidrológico de SENAMHI</h3>
        <p>Las ${j.estaciones.length} estaciones con datos, en el mapa. Una alerta se pinta de color solo si <b>está confirmada</b>: la página la calcula con los umbrales de SENAMHI y el mapa de SENAMHI coincide, con un dato de los últimos 2 días y sin saltos raros. Lo demás se marca aparte. Haz clic en una estación para ver su último dato, el motivo de su alerta y su hidrograma.</p>
        <div class="fila"><label class="campo">Dirección zonal<select id="hid-dz"><option value="">Todas</option>${zonas.map((z) => `<option value="${z}">${esc(ZONAS[z] || "DZ " + z)}</option>`).join("")}</select></label>
          <label class="campo">Estación<select id="hid-buscar"></select></label></div>
        <div class="hid-mapa" id="hid-mapa"><div class="loading"><span class="spin"></span>Cargando el mapa…</div></div>
        <div class="hid-ley">${[["normal", "Sin alerta"], ["amarillo", "Alerta amarilla"], ["naranja", "Alerta naranja"], ["rojo", "Alerta roja"]].map(([k, t]) => `<span><i style="background:${PUNTO[k]}"></i>${t}</span>`).join("")}
          <span><i class="sinconf"></i>Calculada, sin confirmar con SENAMHI</span><span><i class="verificar"></i>A verificar (no pasó los controles)</span><span><i class="sindato"></i>Sin dato reciente</span></div></div>` : ""}
      <div class="caja"><h3>Situación de los ríos ${pais ? "del Perú" : "de " + esc(r.nombre)}</h3>
        <p>Último dato de cada estación, comparado con el mismo día del año pasado y con el promedio histórico. Haz clic en una fila para ver su gráfico.</p>
        <div class="scroll${pais ? " hid-largo" : ""}"><table class="hid-tabla"><tr>${pais ? "<th>Dirección zonal</th><th>Departamento</th>" : ""}<th>Río</th><th>Estación</th><th>Variable</th><th>Fecha</th><th class="n">Último dato</th><th class="n">Año anterior</th><th class="n">Promedio histórico</th><th>Alerta de SENAMHI</th></tr>
        ${filas.map(({ e, v, d }, k) => { const u = d.ultimo || {}, dif = (b) => b == null || u.valor == null ? "" : ` <small class="${u.valor - b >= 0 ? "sube" : "baja"}">${u.valor - b >= 0 ? "+" : "−"}${num(Math.abs(u.valor - b))}</small>`;
          return `<tr data-fila="${k}" data-zona="${esc(e.zonal)}" tabindex="0">${pais ? `<td>${esc(ZONAS[e.zonal] || "—")}</td><td>${esc(titulo(e.departamento)) || "—"}</td>` : ""}<td>${esc(titulo(e.rio))}</td><td><b>${esc(titulo(e.estacion))}</b>${e.departamento_seguro || pais ? "" : " *"}</td><td>${VAR[v]} <small>(${esc(d.unidad)})</small></td><td>${dmy(u.fecha)}</td><td class="n"><b>${num(u.valor)}</b></td><td class="n">${num(u.anterior)}${dif(u.anterior)}</td><td class="n">${num(u.promedio)}${dif(u.promedio)}</td><td>${chip(alerta(u))}</td></tr>`; }).join("")}</table></div>
        <p class="nota">La diferencia en color es cuánto está el río por encima (+) o por debajo (−) de esa referencia. Los umbrales los fija SENAMHI para cada estación: en unas avisan de nivel bajo (vaciante) y en otras de crecida. <b>Alerta:</b> «confirmada» = la página y el mapa de SENAMHI coinciden; «sin confirmar» = solo calculada (falta el color de SENAMHI de hoy); «a verificar» = no pasó un control (dato viejo, umbrales incoherentes, salto brusco o SENAMHI no la marca). Pasa el cursor sobre la alerta para ver el motivo.${dudosas ? ` * SENAMHI no indica el departamento de esa estación: se incluye por pertenecer a la dirección zonal que atiende a ${esc(r.nombre)}.` : ""}${pais ? " El departamento lo da SENAMHI solo para las estaciones principales." : ""}</p></div>
      <div class="caja"><h3>Hidrograma</h3>
        <div class="fila"><label class="campo">Estación<select id="hid-est">${j.estaciones.map((e) => `<option value="${esc(e.codigo)}">${esc(titulo(e.rio))} · ${esc(titulo(e.estacion))}</option>`).join("")}</select></label>
          <label class="campo">Variable<select id="hid-var"></select></label>
          <label class="campo">Ver<select id="hid-modo"><option value="cal">Comparar años (ene–dic)</option><option value="anio">Comparar años hidrológicos (set–ago, como SENAMHI)</option><option value="rango">Rango de fechas</option></select></label>
          <fieldset class="campo hid-anios" id="hid-c-anio"><legend>Años a comparar</legend><div id="hid-anios"></div></fieldset>
          <label class="campo" id="hid-c-desde" hidden>Desde<input type="date" id="hid-desde"></label><label class="campo" id="hid-c-hasta" hidden>Hasta<input type="date" id="hid-hasta-f"></label>
          <div class="fila hid-atajos" id="hid-atajos">${[["30", "30 días"], ["90", "90 días"], ["365", "1 año"], ["todo", "Todo"]].map(([k, t]) => `<button class="btn sec chico" type="button" data-atajo="${k}">${t}</button>`).join("")}</div></div>
        <div id="hid-graf"></div></div>`;
    const $ = (id) => caja.querySelector("#" + id), est = () => j.estaciones.find((e) => e.codigo === $("hid-est").value);
    const iso = (d) => d.toISOString().slice(0, 10), dia = (t) => Date.parse(t + "T00:00:00Z");
    function opciones() {
      const e = est(), vars = Object.keys(e.variables);
      if (!vars.includes(e0.v)) e0.v = vars.includes("NIVEL") ? "NIVEL" : vars[0];
      $("hid-var").innerHTML = vars.map((v) => `<option value="${v}"${v === e0.v ? " selected" : ""}>${VAR[v]} (${esc(e.variables[v].unidad)})</option>`).join("");
      e0.marcados = e0.marcados || new Set();
      if (!["cal", "anio", "rango"].includes(e0.modo)) e0.modo = "cal";
      const rango = e0.modo === "rango";
      $("hid-modo").value = e0.modo;
      $("hid-c-anio").hidden = rango; $("hid-c-desde").hidden = $("hid-c-hasta").hidden = !rango;
    }
    // la serie se pide una vez (el año, o todo desde 2023); elegir el tramo solo vuelve a dibujar, sin esperar al servidor
    let turno = 0, S = null, vista = null, h = null;
    const ocultas = e0.ocultas || (e0.ocultas = new Set());
    async function cargar() {
      const e = est(), g = $("hid-graf"), mio = ++turno;
      e0.c = e.codigo;
      g.innerHTML = '<div class="loading"><span class="spin"></span>Dibujando…</div>';
      const v = e.variables[e0.v], ult = (v.ultimo || {}).fecha || iso(new Date());
      const desde = `${Math.min(...v.años)}-09-01`;
      const url = e0.modo === "rango" ? `/v1/hidrologia/rango?estacion=${encodeURIComponent(e.codigo)}&variable=${e0.v}&desde=${desde}&hasta=${ult}`
        : `/v1/hidrologia/anios?estacion=${encodeURIComponent(e.codigo)}&variable=${e0.v}`;
      try { S = await api(url); if (mio !== turno) return; }
      catch (er) { if (mio !== turno) return; g.innerHTML = `<div class="err-box"><b>No se pudo leer la serie</b><span>${esc(er.message)}</span></div>`; return; }
      // tramo inicial: el año entero, o en rango el que se tenía elegido (si no, los últimos 90 días)
      const idx = (t) => Math.round((dia(t) - dia(S.desde)) / 864e5);
      if (e0.modo === "rango") {
        const a = e0.desde ? idx(e0.desde) : S.dias - 90, b = e0.hasta ? idx(e0.hasta) : S.dias - 1;
        vista = { i0: Math.max(0, Math.min(a, S.dias - 2)), i1: Math.min(S.dias - 1, Math.max(b, 1)) };
        if (vista.i1 <= vista.i0) vista = { i0: Math.max(0, S.dias - 90), i1: S.dias - 1 };
        $("hid-desde").min = $("hid-hasta-f").min = S.desde; $("hid-desde").max = $("hid-hasta-f").max = iso(FECHA(new Date(S.desde + "T00:00:00Z"), S.dias - 1));
      } else {                                              // comparar años: cada año es una serie «a2025» sobre el mismo eje
        if (e0.modo === "cal") { S = alCalendario(S); S.cal = true; }
        S.comparar = true; S.claves = Object.keys(S.años).sort().map((y) => "a" + y);
        S.claves.forEach((k) => { S[k] = S.años[k.slice(1)]; });
        sin29(S);
        vista = { i0: 0, i1: S.dias - 1, marcados: e0.marcados };
        for (const k of [...e0.marcados]) if (!S.claves.includes(k)) e0.marcados.delete(k);
        if (!e0.marcados.size) S.claves.slice(-2).forEach((k) => e0.marcados.add(k));
        // casillas: un año cada una, con el color de su línea; por defecto el actual y el anterior
        $("hid-anios").innerHTML = S.claves.slice().reverse().map((k) => `<label class="hid-chk"><input type="checkbox" data-anio="${k}"${e0.marcados.has(k) ? " checked" : ""}><i style="background:${colorAnio(S, k)}"></i>${etqAño(S, k)}</label>`).join("") +
          `<span class="hid-chk-acc"><button type="button" class="btn sec chico" data-todos="1">Todos</button><button type="button" class="btn sec chico" data-todos="2">Últimos 2</button><button type="button" class="btn sec chico" data-todos="0">Ninguno</button></span>`;
      }
      vista.marcados = e0.marcados; vista.ocultas = ocultas;
      g.innerHTML = `<div class="scroll"><div class="hid-marco"><div class="hid-lienzo"></div><div class="hid-nav"></div></div></div>
        <div class="fila"><button class="btn" type="button" data-a="copiar">Copiar</button><button class="btn sec" type="button" data-a="png">PNG</button><button class="btn sec" type="button" data-a="svg">SVG</button>
          <button class="btn sec" type="button" data-a="csv">Datos del gráfico (CSV)</button><span class="nota" data-msj></span></div>
        <p class="nota">${e0.modo === "rango" ? "" : "Marca arriba los años que quieres comparar. "}Arrastra el recuadro de la barra de abajo para moverte en el tiempo, o estira sus bordes para elegir el tramo. Haz clic en una serie de la leyenda para mostrarla u ocultarla. El promedio histórico y los umbrales son los que publica SENAMHI para la estación.</p>`;
      atar(g);
      pintar();
    }
    let pendiente = false;
    function pintar() {                                     // dibuja el tramo elegido (a lo sumo una vez por cuadro de animación)
      if (pendiente) return;
      pendiente = true;
      requestAnimationFrame(() => {
        pendiente = false;
        const g = $("hid-graf"), lienzo = g.querySelector(".hid-lienzo");
        h = hidrograma(S, vista);
        lienzo.innerHTML = h ? `${h.svg}<i class="hid-guia" hidden></i><div class="hid-tip" hidden></div>` : '<div class="vacio-caja"><b>Sin datos en ese tramo.</b></div>';
        g.querySelector(".hid-nav").innerHTML = navegador(S, vista).svg;
        if (e0.modo === "rango") { const x0 = new Date(S.desde + "T00:00:00Z"); e0.desde = iso(FECHA(x0, vista.i0)); e0.hasta = iso(FECHA(x0, vista.i1)); $("hid-desde").value = e0.desde; $("hid-hasta-f").value = e0.hasta; }
      });
    }
    function atar(g) {
      const lienzo = g.querySelector(".hid-lienzo"), nav = g.querySelector(".hid-nav"), msj = g.querySelector("[data-msj]");
      const decir = (t, ok) => { msj.textContent = t; msj.style.color = ok ? "" : "var(--error)"; };
      lienzo.addEventListener("click", (ev) => { const k = ev.target.closest("[data-serie]"); if (!k) return; const c = k.dataset.serie; ocultas.has(c) ? ocultas.delete(c) : ocultas.add(c); pintar(); });
      lienzo.addEventListener("pointermove", (ev) => {
        const guia = lienzo.querySelector(".hid-guia"), tip = lienzo.querySelector(".hid-tip");
        if (!h || !guia) return;
        const caj = lienzo.getBoundingClientRect(), k = caj.width / h.W, x = (ev.clientX - caj.left) / k, y = (ev.clientY - caj.top) / k;
        const i = Math.round((x - h.izq) / (h.W - h.izq - h.der) * (h.n - 1));
        if (i < 0 || i >= h.n || y < h.arr || y > h.arr + h.alto) { guia.hidden = tip.hidden = true; return; }
        const d = FECHA(h.x0, i), px = (h.izq + (h.W - h.izq - h.der) * i / Math.max(1, h.n - 1)) * k, et = nombres(S, vista), j2 = h.i0 + i;
        const SER = serieDe(S, vista), orden = S.comparar ? [...SER.filter((x) => /^a\d/.test(x[0])).reverse(), ...SER.filter((x) => !/^a\d/.test(x[0]))] : ["actual", "anterior", "promedio", "minimo", "maximo", "rojo", "naranja", "amarillo"].map((c) => SER.find((x) => x[0] === c));
        tip.innerHTML = `<b>${dd(d.getUTCDate())} ${MES[d.getUTCMonth()]}${S.comparar ? "" : " " + d.getUTCFullYear()}</b>` + orden.filter(([c]) => !ocultas.has(c) && S[c][j2] != null)
          .map(([c, t, col]) => `<div><i style="background:${col}"></i>${esc(t || et[c])}<b>${num(S[c][j2], 2)}</b></div>`).join("");
        guia.hidden = tip.hidden = false;
        guia.style.left = px + "px"; guia.style.top = h.arr * k + "px"; guia.style.height = h.alto * k + "px";
        tip.style.left = (px + 200 > caj.width ? px - 192 : px + 12) + "px"; tip.style.top = (h.arr + 8) * k + "px";
      });
      lienzo.addEventListener("pointerleave", () => { const a = lienzo.querySelector(".hid-guia"), b = lienzo.querySelector(".hid-tip"); if (a) a.hidden = b.hidden = true; });
      // barra de navegación: arrastrar el tramo, estirar sus bordes, o clic fuera para llevar el tramo allí
      let arrastre = null;
      const indice = (ev) => { const n = navegador(S, vista), c = nav.getBoundingClientRect(), x = (ev.clientX - c.left) * n.W / c.width; return Math.round((x - n.izq) / n.ancho * (S.dias - 1)); };
      nav.addEventListener("pointerdown", (ev) => {
        const parte = (ev.target.closest("[data-nav]") || {}).dataset?.nav, i = indice(ev), largo = vista.i1 - vista.i0;
        if (!parte) { vista.i0 = Math.max(0, Math.min(S.dias - 1 - largo, i - Math.round(largo / 2))); vista.i1 = vista.i0 + largo; pintar(); }
        arrastre = { parte: parte || "tramo", i, i0: vista.i0, i1: vista.i1 };
        nav.setPointerCapture(ev.pointerId); ev.preventDefault();
      });
      nav.addEventListener("pointermove", (ev) => {
        if (!arrastre) return;
        const d = indice(ev) - arrastre.i, largo = arrastre.i1 - arrastre.i0, min = 6;
        if (arrastre.parte === "tramo") { vista.i0 = Math.max(0, Math.min(S.dias - 1 - largo, arrastre.i0 + d)); vista.i1 = vista.i0 + largo; }
        else if (arrastre.parte === "ini") vista.i0 = Math.max(0, Math.min(arrastre.i1 - min, arrastre.i0 + d));
        else vista.i1 = Math.min(S.dias - 1, Math.max(arrastre.i0 + min, arrastre.i1 + d));
        pintar();
      });
      ["pointerup", "pointercancel"].forEach((t) => nav.addEventListener(t, () => { arrastre = null; }));
      const B = window.BCRP, nombre = () => `SENAMHI_${S.estacion}_${VAR[S.variable]}_${nombres(S, vista).archivo}`;
      g.querySelector('[data-a="copiar"]').addEventListener("click", async () => { try { await B.copiar(h.svg); decir("Copiado: pégalo en Word o PowerPoint con Ctrl+V.", true); } catch (er) { decir(er.message, false); } });
      g.querySelector('[data-a="png"]').addEventListener("click", async () => { try { await B.descargarPng(h.svg, nombre()); } catch (er) { decir(er.message, false); } });
      g.querySelector('[data-a="svg"]').addEventListener("click", () => B.descargar(h.svg, nombre()));
      g.querySelector('[data-a="csv"]').addEventListener("click", () => {
        const et = nombres(S, vista), x0 = new Date(S.desde + "T00:00:00Z");
        const cols = S.comparar ? [...S.claves.filter((k) => vista.marcados.has(k)).map((k) => [k, etqAño(S, k, true)]), ["promedio", "PROMEDIO_HISTORICO"], ["rojo", "UMBRAL_ROJO"], ["naranja", "UMBRAL_NARANJA"], ["amarillo", "UMBRAL_AMARILLO"]]
          : [["actual", "VALOR"], ["anterior", "UN_AÑO_ANTES"], ["promedio", "PROMEDIO_HISTORICO"], ["minimo", "MINIMO"], ["maximo", "MAXIMO"], ["rojo", "UMBRAL_ROJO"], ["naranja", "UMBRAL_NARANJA"], ["amarillo", "UMBRAL_AMARILLO"]];
        const lineas = [["FECHA", ...cols.map((c) => c[1])].join(",")];
        for (let i = vista.i0; i <= vista.i1; i++) lineas.push([S.comparar ? iso(FECHA(x0, i)).slice(8) + "/" + iso(FECHA(x0, i)).slice(5, 7) : dmy(iso(FECHA(x0, i))), ...cols.map(([k]) => S[k][i] ?? "")].join(","));
        const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + lineas.join("\n")], { type: "text/csv" })); a.download = nombre().replace(/\s+/g, "_") + ".csv";
        document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      });
    }
    if (j.estaciones.some((e) => e.codigo === e0.c)) $("hid-est").value = e0.c;
    opciones(); cargar();
    const verHidrograma = async (cod) => { $("hid-est").value = cod; e0.a = null; opciones(); await cargar(); requestAnimationFrame(() => requestAnimationFrame(() => $("hid-est").closest(".caja").scrollIntoView({ behavior: "smooth", block: "start" }))); };
    if (pais) mapa(caja, j.estaciones, e0, verHidrograma);
    $("hid-est").addEventListener("change", () => { opciones(); cargar(); });
    $("hid-var").addEventListener("change", () => { e0.v = $("hid-var").value; opciones(); cargar(); });
    // casillas de años: marcar o desmarcar solo vuelve a dibujar (los años ya están cargados)
    $("hid-c-anio").addEventListener("change", (ev) => {
      const k = ev.target.dataset.anio; if (!k || !S || !S.comparar) return;
      ev.target.checked ? e0.marcados.add(k) : e0.marcados.delete(k); pintar();
    });
    $("hid-c-anio").addEventListener("click", (ev) => {
      const a = ev.target.closest("[data-todos]"); if (!a || !S || !S.comparar) return;
      e0.marcados.clear(); (a.dataset.todos === "1" ? S.claves : a.dataset.todos === "2" ? S.claves.slice(-2) : []).forEach((k) => e0.marcados.add(k));
      caja.querySelectorAll("[data-anio]").forEach((c) => { c.checked = e0.marcados.has(c.dataset.anio); }); pintar();
    });
    $("hid-modo").addEventListener("change", () => { e0.modo = $("hid-modo").value; opciones(); cargar(); });
    const fechas = () => {
      if (!S || S.comparar) return;
      const x = (t) => Math.round((dia(t) - dia(S.desde)) / 864e5), a = $("hid-desde").value, b = $("hid-hasta-f").value;
      if (!a || !b) return;
      const [p, q] = [x(a), x(b)].sort((m, n) => m - n);
      vista.i0 = Math.max(0, Math.min(p, S.dias - 2)); vista.i1 = Math.min(S.dias - 1, Math.max(q, vista.i0 + 1)); pintar();
    };
    $("hid-desde").addEventListener("change", fechas); $("hid-hasta-f").addEventListener("change", fechas);
    caja.querySelectorAll("[data-atajo]").forEach((b) => b.addEventListener("click", () => {
      if (!S) return;
      const k = b.dataset.atajo, ref = S.comparar ? S[puntoDe(S, vista)] : null, fin = S.comparar ? Math.max(1, (ref || []).reduce((a, v, i) => v != null ? i : a, S.dias - 1)) : S.dias - 1;
      vista.i1 = k === "todo" ? S.dias - 1 : fin; vista.i0 = k === "todo" ? 0 : Math.max(0, vista.i1 - (+k - 1)); pintar(); }));
    caja.querySelectorAll("[data-fila]").forEach((tr) => { const ir = () => { const f = filas[+tr.dataset.fila]; $("hid-est").value = f.e.codigo; e0.v = f.v; e0.a = null; opciones(); cargar(); $("hid-graf").scrollIntoView({ behavior: "smooth", block: "center" }); };
      tr.addEventListener("click", ir); tr.addEventListener("keydown", (ev) => { if (ev.key === "Enter") ir(); }); });
  }

  // ── mapa de estaciones (todo el país), como el de SENAMHI ──
  const ZONAS = { "01": "DZ 1 · Piura", "02": "DZ 2 · Lambayeque", "03": "DZ 3 · Cajamarca", "04": "DZ 4 · Lima", "05": "DZ 5 · Ica", "06": "DZ 6 · Arequipa",
    "07": "DZ 7 · Tacna", "08": "DZ 8 · Loreto", "09": "DZ 9 · San Martín", "10": "DZ 10 · Huánuco", "11": "DZ 11 · Junín", "12": "DZ 12 · Cusco", "13": "DZ 13 · Puno" };
  const PUNTO = { normal: "#FFFFFF", amarillo: "#FFFF00", naranja: "#FFA500", rojo: "#FF0000", neutro: "#C8CDD6" };
  let leaflet = null;
  function cargarLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (leaflet) return leaflet;
    leaflet = new Promise((ok, mal) => {
      const css = document.createElement("link"); css.rel = "stylesheet"; css.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css"; document.head.appendChild(css);
      const js = document.createElement("script"); js.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js";
      js.onload = () => ok(window.L); js.onerror = () => { leaflet = null; mal(new Error("no se pudo cargar el mapa (Leaflet)")); }; document.head.appendChild(js);
    });
    return leaflet;
  }
  // estilo del punto según el doble control: color pleno solo si la alerta está confirmada (o la marca SENAMHI); «sin confirmar» lleva
  // un anillo discontinuo y «a verificar» o sin dato reciente van en gris: nunca se pinta una alerta que no pasó los controles
  function estiloDe(e) {
    const a = e.alerta, st = a ? a.estado : "sin_umbral";
    const nivel = a && a.nivel ? { roja: "rojo", amarilla: "amarillo", naranja: "naranja", normal: "normal" }[a.nivel] : null;
    if (st === "confirmada" || st === "senamhi") return { fillColor: PUNTO[nivel], color: "#333", weight: 1.5, dashArray: null };
    if (st === "sin_confirmar") return { fillColor: PUNTO[nivel], color: "#7A5B00", weight: 2.5, dashArray: "3 2" };
    if (st === "a_verificar") return { fillColor: PUNTO.neutro, color: "#C2185B", weight: 2.5, dashArray: "3 2" };
    if (st === "sin_dato") return { fillColor: "#F5F5F5", color: "#9AA0AA", weight: 1.5, dashArray: "2 3" };
    return { fillColor: PUNTO.normal, color: "#333", weight: 1.5, dashArray: null };
  }
  async function mapa(caja, estaciones, e0, verHidrograma) {
    const div = caja.querySelector("#hid-mapa"), zona = caja.querySelector("#hid-dz"), buscar = caja.querySelector("#hid-buscar");
    let L;
    try { L = await cargarLeaflet(); } catch (er) { div.innerHTML = `<div class="err-box"><b>No se pudo mostrar el mapa</b><span>${esc(er.message)}. La tabla y el hidrograma de abajo funcionan igual.</span></div>`; return; }
    div.innerHTML = "";
    const m = L.map(div, { scrollWheelZoom: false, zoomSnap: 0.5 }).setView([-9.2, -75], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 13, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Estaciones: SENAMHI' }).addTo(m);
    // pantalla completa: el mapa ocupa toda la pantalla (Esc o el mismo botón para salir); si el navegador no lo
    // permite (iPhone), el recuadro se agranda a toda la ventana
    const Pantalla = L.Control.extend({ options: { position: "topright" }, onAdd() {
      const b = L.DomUtil.create("button", "hid-full");
      b.type = "button"; b.title = "Ver en pantalla completa"; b.setAttribute("aria-label", "Ver en pantalla completa");
      b.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      L.DomEvent.disableClickPropagation(b);
      L.DomEvent.on(b, "click", () => {
        const activo = document.fullscreenElement === div || div.classList.contains("pantalla");
        if (activo) { if (document.fullscreenElement) document.exitFullscreen(); else { div.classList.remove("pantalla"); document.body.classList.remove("sin-scroll"); m.invalidateSize(); } return; }
        if (div.requestFullscreen) div.requestFullscreen().catch(() => { div.classList.add("pantalla"); document.body.classList.add("sin-scroll"); m.invalidateSize(); });
        else { div.classList.add("pantalla"); document.body.classList.add("sin-scroll"); m.invalidateSize(); }
      });
      return b;
    } });
    new Pantalla().addTo(m);
    // al entrar o salir, el mapa se vuelve a encuadrar sobre las estaciones visibles
    const alCambiar = () => { const activo = document.fullscreenElement === div; div.classList.toggle("completa", activo); m.scrollWheelZoom[activo ? "enable" : "disable"](); setTimeout(() => { m.invalidateSize(); encuadrar(); }, 80); };
    // para ver el hidrograma (que está debajo, en la página) primero se sale de la pantalla completa
    const salir = () => new Promise((ok) => {
      if (document.fullscreenElement === div) { document.addEventListener("fullscreenchange", () => setTimeout(ok, 120), { once: true }); document.exitFullscreen(); }
      else { if (div.classList.contains("pantalla")) { div.classList.remove("pantalla"); document.body.classList.remove("sin-scroll"); m.invalidateSize(); encuadrar(); } ok(); }
    });
    document.addEventListener("fullscreenchange", alCambiar);
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && div.classList.contains("pantalla")) { div.classList.remove("pantalla"); document.body.classList.remove("sin-scroll"); m.invalidateSize(); } });
    const puntos = {};
    const ultimo = (e) => Object.entries(e.variables).map(([v, d]) => d.ultimo ? `<div>${VAR[v]}: <b>${num(d.ultimo.valor)}</b> ${esc(d.unidad)} <small>(${dmy(d.ultimo.fecha)})</small></div>` : "").join("");
    estaciones.filter((e) => e.lat != null).forEach((e) => {
      const p = L.circleMarker([e.lat, e.lon], { radius: 6, fillOpacity: 1, ...estiloDe(e) });
      p.bindTooltip(`${titulo(e.estacion)} · ${titulo(e.rio)}`, { direction: "top", offset: [0, -6] });
      p.bindPopup(`<div class="hid-pop"><b>${esc(titulo(e.estacion))}</b><span>${esc(titulo(e.rio))} · ${esc(ZONAS[e.zonal] || "")}${e.departamento ? " · " + esc(titulo(e.departamento)) : ""}</span>${ultimo(e)}${e.alerta && e.alerta.estado !== "sin_umbral" ? `<div class="hid-al"><b>${esc(e.alerta.texto)}</b>${e.alerta.motivos.length ? `<ul>${e.alerta.motivos.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>` : ""}</div>` : ""}<button class="btn chico" type="button" data-ver="${esc(e.codigo)}">Ver hidrograma</button></div>`);
      p.on("popupopen", (ev) => { const b = ev.popup.getElement().querySelector("[data-ver]"); if (b) b.onclick = async () => { m.closePopup(); await salir(); verHidrograma(e.codigo); }; });
      puntos[e.codigo] = { p, e };
    });
    const visibles = () => Object.values(puntos).filter(({ e }) => !zona.value || e.zonal === zona.value);
    const encuadrar = () => { const vis = visibles(); if (vis.length) m.fitBounds(L.latLngBounds(vis.map(({ e }) => [e.lat, e.lon])).pad(0.15), { maxZoom: 8 }); };
    const filtrar = () => {
      const z = zona.value, vis = visibles();
      Object.values(puntos).forEach(({ p, e }) => { if (!z || e.zonal === z) p.addTo(m); else p.remove(); });
      buscar.innerHTML = '<option value="">Seleccione</option>' + vis.map(({ e }) => `<option value="${esc(e.codigo)}">${esc(titulo(e.estacion))} · ${esc(titulo(e.rio))}</option>`).join("");
      caja.querySelectorAll("tr[data-zona]").forEach((tr) => { tr.hidden = !!z && tr.dataset.zona !== z; });
      encuadrar();
      e0.zona = z;
    };
    zona.value = e0.zona || ""; filtrar();
    zona.addEventListener("change", filtrar);
    buscar.addEventListener("change", () => { const x = puntos[buscar.value]; if (!x) return; m.setView([x.e.lat, x.e.lon], 9); x.p.openPopup(); });
    setTimeout(() => m.invalidateSize(), 50);
  }

  // Perú: la misma sección con el mapa de todas las estaciones y las descargas de todo el país
  function peru(caja, pestaña) {
    const tabs = ["Mapa y gráfico", ...(HIDRO.sinDescargas ? [] : ["Descargar datos"]), ...(HIDRO.invitado ? [] : ["Actualizar"])], t = tabs.includes(pestaña) ? pestaña : tabs[0];
    caja.innerHTML = `<div class="tabs" role="tablist">${tabs.map((x) => `<button role="tab" type="button" data-hid-tab="${x}" aria-selected="${x === t}">${x}</button>`).join("")}</div><div id="hid-peru"></div>`;
    caja.querySelectorAll("[data-hid-tab]").forEach((b) => b.addEventListener("click", () => { HIDRO.pestañaPeru = b.dataset.hidTab; peru(caja, b.dataset.hidTab); }));
    const r = { cod: "todos", nombre: "Perú" }, c = caja.querySelector("#hid-peru");
    (t === "Actualizar" ? actualizar : t === "Descargar datos" ? descargas : grafico)(r, c);
  }

  function ponerHasta(res) {
    const b = document.getElementById("hid-hasta");
    if (b) b.textContent = res && res.hay ? `${dmy(res.ultima_fecha)} (recolectado el ${dmy(res.recolectado)})` : "Sin datos todavía";
  }

  // ── pestaña «Descargar datos» ──
  const ARCH = [["diario", "Serie diaria (hidrograma)", "Una fila por estación, variable y día: valor, mínimo, máximo, promedio histórico y umbrales. Todas las estaciones, nivel y caudal, desde 2023."],
    ["info-diaria", "Información Diaria", "Las estaciones principales a las 00:00, 06:00, 12:00 y 18:00, con la anomalía respecto a la normal, la tendencia y el umbral rojo."],
    ["mensual", "Información Mensual", "Valor del mes, mes anterior, anomalía y tendencia de las estaciones principales."],
    ["estaciones", "Estaciones", "Lista de estaciones: dirección zonal, departamento, río, variables con datos y fecha del último dato."],
    ["no-publicado", "Series no publicadas por SENAMHI", "Lo que SENAMHI devuelve de una variable que no publica en esa estación (en su página el botón está deshabilitado): por ejemplo, el «nivel» de las estaciones que solo publican caudal o el caudal de Bellavista. Probablemente sean lecturas internas sin validar: se guardan aparte y no se usan en el mapa, las alertas, los gráficos ni el reporte."],
    ["control", "Control de la serie diaria", "Por estación y variable: primera y última fecha, días con dato, días faltantes, saltos raros y estado (OK o REVISAR)."]];
  async function descargas(r, caja) {
    caja.innerHTML = '<div class="loading"><span class="spin"></span>Consultando…</div>';
    let res;
    try { res = await api("/v1/hidrologia"); } catch (e) { caja.innerHTML = `<div class="err-box"><b>No se pudo consultar</b><span>${esc(e.message)}</span></div>`; return; }
    ponerHasta(res);
    if (!res.hay) { caja.innerHTML = '<div class="vacio-caja"><b>Todavía no hay datos de SENAMHI en la página.</b><span>Ve a la pestaña «Actualizar»: allí se sube el archivo que deja el recolector.</span></div>'; return; }
    const pais = r.cod === "todos";
    const u = (a, d, f) => `/v1/hidrologia/descargar?archivo=${a}${d ? "&departamento=" + d : ""}${f ? "&formato=" + f : ""}`;
    caja.innerHTML = `<div class="caja"><h3>Datos del scraper de SENAMHI</h3>
      <p>Son los mismos archivos que arma el notebook de Colab. Hay <b>${num(res.filas_diario, 0)}</b> filas diarias de <b>${res.estaciones_con_datos}</b> estaciones, <b>${num(res.filas_info_diaria, 0)}</b> de Información Diaria y <b>${num(res.filas_mensual, 0)}</b> mensuales; el último dato es del <b>${dmy(res.ultima_fecha)}</b>.</p>
      <div class="scroll"><table><tr><th>Archivo</th><th>Qué trae</th>${pais ? "" : `<th>Solo ${esc(r.nombre)}</th>`}<th>Todo el país</th></tr>
      ${ARCH.map(([a, t, d]) => `<tr><td><b>${t}</b></td><td>${d}</td>${pais ? "" : `<td class="hid-enl"><a href="${u(a, r.cod, "xlsx")}">Excel</a> · <a href="${u(a, r.cod)}">CSV</a></td>`}<td class="hid-enl"><a href="${u(a)}">CSV</a>${a === "diario" || a === "no-publicado" || a === "info-diaria" ? "" : ` · <a href="${u(a, "", "xlsx")}">Excel</a>`}</td></tr>`).join("")}</table></div>
      <div class="fila">${pais ? "" : `<a class="btn" href="${u("todo", r.cod)}">Todo lo de ${esc(r.nombre)} (.zip)</a>`}<a class="btn${pais ? "" : " sec"}" href="${u("todo")}">Todo el país, con los controles (.zip)</a></div>
      ${pais && !HIDRO.invitado ? `<div class="caja hid-reporte"><h3>Reporte de situación hídrica · Zona Oriente</h3>
        <p>Con el formato del reporte de la Sucursal Piura, armado con los datos de hoy: portada, situación de los ríos del Oriente, hidrogramas de Loreto, San Martín y Ucayali, nivel diario del mes por año y caudales. El Excel trae una hoja por gráfico con sus datos (si cambias un dato, cambia el gráfico) y un resumen con fórmulas.</p>
        <div class="fila"><a class="btn" href="/v1/hidrologia/reporte?formato=pptx">PowerPoint (.pptx)</a><a class="btn sec" href="/v1/hidrologia/reporte?formato=xlsx">Excel con los datos y gráficos (.xlsx)</a></div></div>` : ""}
      ${pais ? `<p class="nota">Para un departamento en particular, cada región (Loreto, San Martín, Ucayali) tiene su sección Hidrología con sus propios archivos. Los CSV de todo el país traen las columnas COD_ZONAL y DEPARTAMENTO para filtrar.</p>` : ""}
      <p class="nota">Los CSV están en UTF-8 con comas. Si Excel muestra «AÃ‘O», usa el enlace «Excel» o ábrelo desde Datos → Desde texto/CSV. El significado de cada columna está en <a href="https://github.com/adriansivina-droid/scraper-mef/blob/main/HIDROLOGIA/docs/Diccionario_SENAMHI_rios.pdf" target="_blank" rel="noopener">el diccionario de datos</a>.${res.a_revisar ? ` El control marca ${res.a_revisar} series con «REVISAR (saltos)»: son cambios bruscos de un día a otro que conviene mirar; los datos se guardan tal como los publica SENAMHI.` : ""}</p></div>`;
  }

  // ── pestaña «Actualizar»: sube el archivo del recolector, solo lo que cambió ──
  function huella(t) {                                        // cyrb53: rápida y suficiente para saber si una pieza cambió
    let a = 0xdeadbeef, b = 0x41c6ce57;
    for (let i = 0; i < t.length; i++) { const c = t.charCodeAt(i); a = Math.imul(a ^ c, 2654435761); b = Math.imul(b ^ c, 1597334677); }
    a = Math.imul(a ^ (a >>> 16), 2246822507) ^ Math.imul(b ^ (b >>> 13), 3266489909); b = Math.imul(b ^ (b >>> 16), 2246822507) ^ Math.imul(a ^ (a >>> 13), 3266489909);
    return (4294967296 * (2097151 & b) + (a >>> 0)).toString(36);
  }
  function piezasDe(crudo) {
    const out = [], pon = (clave, valor, base) => { const texto = JSON.stringify(valor); out.push({ clave, valor, huella: huella(base === undefined ? texto : JSON.stringify(base)), peso: texto.length }); };
    ["meta", "estaciones", "zonales", "infoMeta", "fichas", "monitoreo"].forEach((k) => { if (crudo[k] && Object.keys(crudo[k]).length) pon(k, crudo[k]); });
    (crudo.graficas || []).forEach((g) => pon(`graf:${g.cod}:${g.variable}:${g.y}`, g, [g.estado, g.data]));   // la huella no mira el día de la consulta
    Object.entries(crudo.mensual || {}).forEach(([k, v]) => pon(`men:${k}`, v));
    Object.entries(crudo.infoDiaria || {}).forEach(([k, v]) => pon(`inf:${k.slice(0, 10)}:${k.slice(11)}`, v));
    return out;
  }
  async function subir(archivo, avisar) {
    avisar(`Leyendo ${archivo.name}…`, 0);
    let crudo;
    try { crudo = JSON.parse(await archivo.text()); } catch (e) { throw new Error("El archivo no es el JSON del recolector (SENAMHI_crudo_AAAA-MM-DD.json)."); }
    if (!crudo || !Array.isArray(crudo.graficas) || !crudo.meta) throw new Error("El archivo no es el JSON del recolector (SENAMHI_crudo_AAAA-MM-DD.json).");
    if (crudo.meta.prueba) throw new Error("Ese archivo es de una «Prueba rápida» (3 estaciones). Sube el de la corrida completa.");
    const dia = crudo.meta.hoy || String(crudo.generado || "").slice(0, 10);
    const piezas = piezasDe(crudo);
    crudo = null;
    avisar("Comparando con lo que ya está en la página…", 0);
    const guardado = (await api("/v1/hidrologia/crudo/indice")).piezas;
    const nuevas = piezas.filter((p) => guardado[p.clave] !== p.huella && !["meta", "fichas"].includes(p.clave));
    const siempre = piezas.filter((p) => ["meta", "fichas"].includes(p.clave) && guardado[p.clave] !== p.huella);
    const cola = nuevas.length ? [...nuevas, ...siempre] : [];           // si no cambió ningún dato, no hay nada que subir
    const total = cola.reduce((s, p) => s + p.peso, 0);
    let hecho = 0, guardadas = 0, viejas = 0;
    for (let i = 0; i < cola.length;) {
      const lote = []; let peso = 0;
      while (i < cola.length && lote.length < 600 && (peso + cola[i].peso < 900000 || !lote.length)) { peso += cola[i].peso; lote.push(cola[i++]); }
      const r = await api("/v1/hidrologia/crudo", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dia, piezas: lote.map(({ clave, valor, huella }) => ({ clave, valor, huella })) }) });
      guardadas += r.guardadas; viejas += r.omitidas_por_viejas; hecho += peso;
      avisar(`Subiendo lo nuevo: ${Math.round(100 * hecho / total)} %`, hecho / total);
    }
    avisar("Armando los archivos y el resumen…", 1);
    return { dia, piezas: piezas.length, nuevas: nuevas.length, guardadas, viejas, mb: total / 1048576, resumen: await api("/v1/hidrologia") };
  }
  async function actualizar(r, caja) {
    caja.innerHTML = `<div class="caja"><h3>Actualizar los datos de SENAMHI</h3>
        <p>SENAMHI no responde a servidores (ni a esta página, ni a Colab, ni a GitHub): solo a un navegador. Por eso la recolección corre en tu navegador y luego subes aquí el archivo que deja. Sirve para las tres regiones a la vez.</p>
        <div class="pasos">
          <div><b>1 · Abre SENAMHI</b><span>Abre <a href="${SENAMHI}" target="_blank" rel="noopener">Monitoreo Hidrológico de SENAMHI</a> en una pestaña nueva y espera a que cargue el mapa.</span></div>
          <div><b>2 · Pega el código en la consola</b><span>Este es el código (es el mismo todos los días):</span><textarea class="hid-codigo" id="hid-codigo" readonly rows="4" aria-label="Código para la consola">${esc(CONSOLA)}</textarea><button class="btn" type="button" id="hid-copiar" style="align-self:flex-start">Copiar el código</button>
            <span>En la pestaña de SENAMHI pulsa <b>F12</b>, entra a <b>Console</b>, pega con <b>Ctrl+V</b> y pulsa <b>Enter</b>. Aparece el panel abajo a la derecha: revisa las fechas y pulsa <b>Iniciar</b> (no empieza solo). La actualización diaria tarda unos 5 minutos; deja la pestaña abierta. Si Chrome no deja pegar, escribe <b>allow pasting</b>, Enter, y vuelve a pegar.</span></div>
          <div><b>3 · Sube aquí el archivo</b><span>Al terminar se descarga <b>SENAMHI_crudo_AAAA-MM-DD.json</b> (carpeta Descargas). Arrástralo al recuadro de abajo. La página compara y sube solo lo nuevo.</span></div></div>
        <label class="zona-subida" for="hid-arch" id="hid-zona"><b>Arrastra aquí SENAMHI_crudo_….json o haz clic para elegirlo</b><span>El archivo trae todo lo recolectado desde 2023 (unos 33 MB); solo viaja lo que cambió</span><input class="solo-lector" type="file" id="hid-arch" accept=".json,application/json"></label>
        <div class="hid-barra" hidden><span></span></div><div id="hid-res" aria-live="polite"></div></div>
      <details class="caja"><summary><b>Preguntas frecuentes</b></summary>
        <p><b>¿Hay algo más rápido que la consola?</b> Puedes probar un favorito: arrastra <a class="hid-fav" href="${esc(FAVORITO)}" title="Arrástrame a la barra de favoritos">Recolector SENAMHI</a> a la barra de favoritos (Ctrl+Mayús+B la muestra) y haz clic en él estando en SENAMHI. En algunos navegadores la página de SENAMHI no deja correr favoritos; si al hacer clic no aparece el panel, usa la consola.</p>
        <p><b>¿Qué fechas pongo en el panel?</b> La primera vez, las de la corrida larga: <b>Desde</b> 01/01/2020 (lo diario: hidrograma e Información Diaria) y, junto a «Información Mensual», <b>desde</b> el mes más antiguo que quieras (por ejemplo 2000-01). Después no cambies nada: el recolector recuerda lo que ya bajó y cada día solo pide lo nuevo (el año hidrológico en curso de todas las estaciones, los 3 últimos meses de la Información Mensual y la Información Diaria de hoy, de ayer y de los días que falten).</p>
        <p><b>¿Y si un día no lo hago?</b> No se pierde nada: al día siguiente recoge también los días que faltaron.</p>
        <p><b>¿Tiene que ser en la misma computadora?</b> Conviene: el avance se guarda en ese navegador. En otra computadora o tras borrar los datos de navegación, la primera vez vuelve a bajar todo (unas 4 horas); lo que ya está en la página no se pierde.</p>
        <p><b>¿Puedo subir un archivo viejo por error?</b> Sí, sin daño: la página no reemplaza una pieza por otra recolectada antes.</p>
        <p><b>¿Y el notebook de Colab?</b> Sigue sirviendo con el mismo archivo si quieres además la copia en Google Drive, pero ya no hace falta para la página.</p></details>`;
    const $ = (id) => caja.querySelector("#" + id), zona = $("hid-zona"), barra = caja.querySelector(".hid-barra"), res = $("hid-res");
    $("hid-codigo").addEventListener("focus", (ev) => ev.target.select());
    const copiar = $("hid-copiar");
    copiar.addEventListener("click", async () => { try { await navigator.clipboard.writeText(CONSOLA); copiar.textContent = "Copiado ✓ · pégalo en la consola"; } catch (e) { $("hid-codigo").focus(); copiar.textContent = "Selecciónalo arriba y cópialo con Ctrl+C"; } });
    caja.querySelector(".hid-fav").addEventListener("click", (ev) => { ev.preventDefault(); res.innerHTML = '<div class="err-box"><b>Este botón no se pulsa aquí</b><span>Arrástralo a la barra de favoritos y úsalo desde allí.</span></div>'; });
    async function procesar(archivo) {
      if (!archivo) return;
      zona.classList.add("ocupada"); barra.hidden = false; res.innerHTML = "";
      const avisar = (t, f) => { barra.firstElementChild.style.width = Math.round(f * 100) + "%"; res.innerHTML = `<p class="nota">${esc(t)}</p>`; };
      try {
        const x = await subir(archivo, avisar), s = x.resumen;
        res.innerHTML = `<div class="ok-box"><b>${x.nuevas ? "Datos actualizados" : "La página ya tenía todo lo de ese archivo"}</b><ul>
          <li>Archivo recolectado el ${dmy(x.dia)}: ${num(x.piezas, 0)} piezas, ${num(x.nuevas, 0)} nuevas o cambiadas${x.nuevas ? ` (${num(x.mb, 1)} MB subidos)` : ""}.</li>
          ${x.viejas ? `<li>${x.viejas} piezas no se tocaron porque la página ya tenía una versión más reciente.</li>` : ""}
          <li>En la página: ${num(s.filas_diario, 0)} filas diarias de ${s.estaciones_con_datos} estaciones, hasta el ${dmy(s.ultima_fecha)}; ${num(s.filas_info_diaria, 0)} de Información Diaria y ${num(s.filas_mensual, 0)} mensuales.</li>
          <li>Con datos en Loreto: ${s.por_departamento.LORETO || 0} estaciones · San Martín: ${s.por_departamento["SAN MARTIN"] || 0} · Ucayali: ${s.por_departamento.UCAYALI || 0}.</li></ul></div>`;
        ponerHasta(s);
        if (window.HIDRO.alActualizar) window.HIDRO.alActualizar();
      } catch (e) { res.innerHTML = `<div class="err-box"><b>No se pudo subir</b><span>${esc(e.message)}</span></div>`; }
      zona.classList.remove("ocupada"); barra.hidden = true; $("hid-arch").value = "";
    }
    $("hid-arch").addEventListener("change", (ev) => procesar(ev.target.files[0]));
    ["dragenter", "dragover"].forEach((t) => zona.addEventListener(t, (ev) => { ev.preventDefault(); zona.classList.add("sobre"); }));
    ["dragleave", "drop"].forEach((t) => zona.addEventListener(t, () => zona.classList.remove("sobre")));
    zona.addEventListener("drop", (ev) => { ev.preventDefault(); ev.stopPropagation(); procesar(ev.dataTransfer.files[0]); });
    api("/v1/hidrologia").then(ponerHasta).catch(() => {});
  }

  window.HIDRO = { TABS: ["Gráfico", "Descargar datos", "Actualizar"], hidrograma, navegador, peru, alerta, piezasDe,
    pintar(r, caja, pestaña) { return (pestaña === "Actualizar" ? actualizar : pestaña === "Descargar datos" ? descargas : grafico)(r, caja); } };
})();
