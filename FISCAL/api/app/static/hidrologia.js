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
  const COLOR = { actual: "#111149", anterior: "#2A9DA1", promedio: "#8A8FA3", banda: "#111149", rojo: "#C62828", naranja: "#EF6C00", amarillo: "#D9A400" };
  const RECOLECTOR = "https://raw.githubusercontent.com/adriansivina-droid/scraper-mef/main/HIDROLOGIA/senamhi_navegador.js";
  const SENAMHI = "https://www.senamhi.gob.pe/?p=monitoreo-hidrologico";
  // favorito: en la página de SENAMHI carga el recolector y lo pone a trabajar; en cualquier otra, lleva a SENAMHI
  // línea para la consola (F12): carga el recolector y, si hay avance guardado, empieza solo
  const CONSOLA = `window.__senamhiAuto=1;fetch('${RECOLECTOR}').then(r=>r.text()).then(eval)`;
  const FAVORITO = `javascript:(function(){if(!/senamhi\\.gob\\.pe$/.test(location.hostname)){location.href='${SENAMHI}';return}window.__senamhiAuto=1;fetch('${RECOLECTOR}').then(function(r){return r.text()}).then(eval)})()`;

  async function api(url, opciones) {
    const r = await fetch(url, opciones);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : `El servidor respondió ${r.status}.`);
    return j;
  }

  // ── alerta: los umbrales de SENAMHI son de nivel bajo (vaciante) si el rojo queda debajo del amarillo; si no, de crecida ──
  function alerta(u) {
    if (!u || u.valor == null || u.rojo == null) return null;
    const otro = u.amarillo != null ? u.amarillo : u.naranja != null ? u.naranja : u.promedio;
    const baja = otro != null ? u.rojo < otro : false;
    const pasa = (t) => t != null && (baja ? u.valor <= t : u.valor >= t);
    const nivel = pasa(u.rojo) ? "rojo" : pasa(u.naranja) ? "naranja" : pasa(u.amarillo) ? "amarillo" : "normal";
    return { nivel, baja, texto: nivel === "normal" ? "Sin alerta" : `Umbral ${nivel} ${baja ? "por nivel bajo" : "por crecida"}` };
  }
  const chip = (a) => a ? `<span class="chip hid-${a.nivel}">${esc(a.texto)}</span>` : '<span class="nota">sin umbrales</span>';

  // ── el hidrograma: año hidrológico (setiembre a agosto), año anterior, promedio histórico y umbrales ──
  function hidrograma(s) {
    const W = 920, H = 440, izq = 64, der = 96, arr = 62, aba = 40, n = s.dias, x0 = new Date(s.desde + "T00:00:00Z");
    const claves = ["actual", "anterior", "promedio", "minimo", "maximo", "rojo", "naranja", "amarillo"];
    const todos = claves.flatMap((k) => s[k]).filter((v) => v != null);
    if (!todos.length) return null;
    let lo = Math.min(...todos), hi = Math.max(...todos);
    const margen = (hi - lo || Math.abs(hi) || 1) * 0.06; lo -= margen; hi += margen;
    const paso = (() => { const b = (hi - lo) / 6, p = 10 ** Math.floor(Math.log10(b)), f = b / p; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p; })();
    const dec = paso >= 1 ? (hi - lo < 20 ? 1 : 0) : Math.min(3, Math.ceil(-Math.log10(paso)));
    const X = (i) => izq + (W - izq - der) * i / (n - 1), Y = (v) => arr + (H - arr - aba) * (1 - (v - lo) / (hi - lo));
    const camino = (vals) => { let d = "", abierto = false; vals.forEach((v, i) => { if (v == null) { abierto = false; return; } d += `${abierto ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; abierto = true; }); return d; };
    const linea = (k, extra) => { const d = camino(s[k]); return d ? `<path d="${d}" fill="none" stroke="${COLOR[k]}" stroke-linejoin="round" ${extra}/>` : ""; };
    let rejilla = "";
    for (let v = Math.ceil(lo / paso) * paso; v <= hi; v += paso) rejilla += `<line x1="${izq}" x2="${W - der}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#CCD3DF" stroke-dasharray="2 4"/><text x="${izq - 8}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${num(v, dec)}</text>`;
    let meses = "";
    for (let i = 0; i < n; i++) { const d = new Date(x0.getTime() + i * 864e5); if (d.getUTCDate() === 1) meses += `<line x1="${X(i).toFixed(1)}" x2="${X(i).toFixed(1)}" y1="${H - aba}" y2="${H - aba + 5}" stroke="#8A8FA3"/><text x="${(X(i) + (W - izq - der) / 24).toFixed(1)}" y="${H - aba + 18}" text-anchor="middle">${MES[d.getUTCMonth()]}${d.getUTCMonth() === 0 || i === 0 ? " " + d.getUTCFullYear() : ""}</text>`; }
    // banda entre el mínimo y el máximo del día
    let banda = "";
    const tramos = []; let t = null;
    s.minimo.forEach((v, i) => { if (v != null && s.maximo[i] != null) { if (!t) { t = []; tramos.push(t); } t.push(i); } else t = null; });
    tramos.forEach((t) => { if (t.length > 1) banda += `<path d="M${t.map((i) => `${X(i).toFixed(1)},${Y(s.maximo[i]).toFixed(1)}`).join("L")}L${t.slice().reverse().map((i) => `${X(i).toFixed(1)},${Y(s.minimo[i]).toFixed(1)}`).join("L")}Z" fill="${COLOR.banda}" opacity="0.13"/>`; });
    const etiquetas = [];
    const umbrales = ["rojo", "naranja", "amarillo"].map((k) => {
      const ult = s[k].filter((v) => v != null).pop();
      if (ult == null) return "";
      etiquetas.push({ y: Y(ult), k, v: ult });
      return linea(k, 'stroke-width="1.6" stroke-dasharray="7 4"');
    }).join("");
    etiquetas.sort((a, b) => a.y - b.y).forEach((e, i, l) => { if (i && e.y - l[i - 1].y < 13) e.y = l[i - 1].y + 13; });
    const rotulos = etiquetas.map((e) => `<text x="${W - der + 6}" y="${(e.y + 4).toFixed(1)}" fill="${COLOR[e.k]}" font-weight="600">${e.k[0].toUpperCase() + e.k.slice(1)} ${num(e.v, dec + 1)}</text>`).join("");
    const iUlt = s.actual.reduce((a, v, i) => v != null ? i : a, -1);
    const punto = iUlt >= 0 ? `<circle cx="${X(iUlt).toFixed(1)}" cy="${Y(s.actual[iUlt]).toFixed(1)}" r="4" fill="${COLOR.actual}" stroke="#FEFEFE" stroke-width="1.5"/>` : "";
    const a = s.año, ley = [["actual", `${a}-${a + 1}`, ""], ["anterior", `${a - 1}-${a}`, ""], ["promedio", "Promedio histórico", "5 4"]]
      .filter(([k]) => s[k].some((v) => v != null));
    let lx = izq;
    const leyenda = ley.map(([k, t, guion]) => { const g = `<line x1="${lx}" x2="${lx + 26}" y1="${arr - 16}" y2="${arr - 16}" stroke="${COLOR[k]}" stroke-width="${k === "actual" ? 3 : 2}" ${guion ? `stroke-dasharray="${guion}"` : ""}/><text x="${lx + 32}" y="${arr - 12}" fill="#181818">${esc(t)}</text>`; lx += 44 + t.length * 6.6; return g; }).join("") +
      (banda ? `<rect x="${lx}" y="${arr - 22}" width="26" height="12" fill="${COLOR.banda}" opacity="0.13"/><text x="${lx + 32}" y="${arr - 12}" fill="#181818">Mínimo y máximo del día</text>` : "");
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="Barlow, 'Segoe UI', Arial, sans-serif" font-size="12" fill="#5A5A6E" role="img" aria-label="Hidrograma de ${esc(s.estacion)}">
      <rect width="${W}" height="${H}" fill="#FEFEFE"/>
      <text x="${izq}" y="20" font-size="15" font-weight="700" fill="#111149">${esc(s.rio)} · estación ${esc(titulo(s.estacion))}</text>
      <text x="${W - 12}" y="20" text-anchor="end">${VAR[s.variable]} diario (${esc(s.unidad)}) · año hidrológico ${a}-${a + 1} · Fuente: SENAMHI</text>
      ${leyenda}${rejilla}${meses}<line x1="${izq}" x2="${W - der}" y1="${H - aba}" y2="${H - aba}" stroke="#8A8FA3"/>
      ${banda}${umbrales}${linea("promedio", 'stroke-width="1.8" stroke-dasharray="5 4"')}${linea("anterior", 'stroke-width="2"')}${linea("actual", 'stroke-width="3"')}${punto}${rotulos}</svg>`;
    return { svg, W, izq, der, n, x0, dec };
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
      caja.innerHTML = `<div class="vacio-caja"><b>${j.resumen.hay ? `SENAMHI no tiene estaciones con datos en ${esc(r.nombre)}.` : "Todavía no hay datos de SENAMHI en la página."}</b><span>${j.resumen.hay ? "Los datos de las demás regiones están en «Descargar datos»." : "Ve a la pestaña «Actualizar»: allí se sube el archivo que deja el recolector."}</span></div>`;
      return;
    }
    const e0 = st[r.cod] || (st[r.cod] = {});
    const filas = j.estaciones.flatMap((e) => Object.entries(e.variables).map(([v, d]) => ({ e, v, d })));
    const dudosas = j.estaciones.filter((e) => !e.departamento_seguro).length;
    caja.innerHTML = `<div class="caja"><h3>Situación de los ríos de ${esc(r.nombre)}</h3>
        <p>Último dato de cada estación, comparado con el mismo día del año pasado y con el promedio histórico. Haz clic en una fila para ver su gráfico.</p>
        <div class="scroll"><table class="hid-tabla"><tr><th>Río</th><th>Estación</th><th>Variable</th><th>Fecha</th><th class="n">Último dato</th><th class="n">Año anterior</th><th class="n">Promedio histórico</th><th>Alerta de SENAMHI</th></tr>
        ${filas.map(({ e, v, d }, k) => { const u = d.ultimo || {}, dif = (b) => b == null || u.valor == null ? "" : ` <small class="${u.valor - b >= 0 ? "sube" : "baja"}">${u.valor - b >= 0 ? "+" : "−"}${num(Math.abs(u.valor - b))}</small>`;
          return `<tr data-fila="${k}" tabindex="0"><td>${esc(titulo(e.rio))}</td><td><b>${esc(titulo(e.estacion))}</b>${e.departamento_seguro ? "" : " *"}</td><td>${VAR[v]} <small>(${esc(d.unidad)})</small></td><td>${dmy(u.fecha)}</td><td class="n"><b>${num(u.valor)}</b></td><td class="n">${num(u.anterior)}${dif(u.anterior)}</td><td class="n">${num(u.promedio)}${dif(u.promedio)}</td><td>${chip(alerta(u))}</td></tr>`; }).join("")}</table></div>
        <p class="nota">La diferencia en color es cuánto está el río por encima (+) o por debajo (−) de esa referencia. Los umbrales los fija SENAMHI para cada estación: en unas avisan de nivel bajo (vaciante) y en otras de crecida.${dudosas ? ` * SENAMHI no indica el departamento de esa estación: se incluye por pertenecer a la dirección zonal que atiende a ${esc(r.nombre)}.` : ""}</p></div>
      <div class="caja"><h3>Hidrograma</h3>
        <div class="fila"><label class="campo">Estación<select id="hid-est">${j.estaciones.map((e) => `<option value="${esc(e.codigo)}">${esc(titulo(e.rio))} · ${esc(titulo(e.estacion))}</option>`).join("")}</select></label>
          <label class="campo">Variable<select id="hid-var"></select></label><label class="campo">Año hidrológico (set–ago)<select id="hid-anio"></select></label></div>
        <div id="hid-graf"></div></div>`;
    const $ = (id) => caja.querySelector("#" + id), est = () => j.estaciones.find((e) => e.codigo === $("hid-est").value);
    function opciones() {
      const e = est(), vars = Object.keys(e.variables);
      if (!vars.includes(e0.v)) e0.v = vars.includes("NIVEL") ? "NIVEL" : vars[0];
      $("hid-var").innerHTML = vars.map((v) => `<option value="${v}"${v === e0.v ? " selected" : ""}>${VAR[v]} (${esc(e.variables[v].unidad)})</option>`).join("");
      const años = e.variables[e0.v].años.slice().reverse();
      if (!años.includes(e0.a)) e0.a = años[0];
      $("hid-anio").innerHTML = años.map((a) => `<option value="${a}"${a === e0.a ? " selected" : ""}>${a}-${a + 1}</option>`).join("");
    }
    async function dibujar() {
      const e = est(), g = $("hid-graf");
      e0.c = e.codigo;
      g.innerHTML = '<div class="loading"><span class="spin"></span>Dibujando…</div>';
      let s;
      try { s = await api(`/v1/hidrologia/serie?estacion=${encodeURIComponent(e.codigo)}&variable=${e0.v}&anio=${e0.a}`); }
      catch (er) { g.innerHTML = `<div class="err-box"><b>No se pudo leer la serie</b><span>${esc(er.message)}</span></div>`; return; }
      const h = hidrograma(s);
      if (!h) { g.innerHTML = '<div class="vacio-caja"><b>Sin datos en ese año.</b></div>'; return; }
      const nombre = `SENAMHI_${s.estacion}_${VAR[s.variable]}_${s.año}-${s.año + 1}`;
      g.innerHTML = `<div class="scroll"><div class="hid-lienzo">${h.svg}<i class="hid-guia" hidden></i><div class="hid-tip" hidden></div></div></div>
        <div class="fila"><button class="btn" type="button" data-a="copiar">Copiar</button><button class="btn sec" type="button" data-a="png">PNG</button><button class="btn sec" type="button" data-a="svg">SVG</button>
          <button class="btn sec" type="button" data-a="csv">Datos del gráfico (CSV)</button><span class="nota" data-msj></span></div>
        <p class="nota">Cada línea es un año hidrológico, del 1 de setiembre al 31 de agosto. El promedio histórico y los umbrales son los que publica SENAMHI para la estación.</p>`;
      const lienzo = g.querySelector(".hid-lienzo"), guia = g.querySelector(".hid-guia"), tip = g.querySelector(".hid-tip"), msj = g.querySelector("[data-msj]");
      const decir = (t, ok) => { msj.textContent = t; msj.style.color = ok ? "" : "var(--error)"; };
      lienzo.addEventListener("pointermove", (ev) => {
        const caj = lienzo.getBoundingClientRect(), k = caj.width / h.W, x = (ev.clientX - caj.left) / k;
        const i = Math.round((x - h.izq) / (h.W - h.izq - h.der) * (h.n - 1));
        if (i < 0 || i >= h.n) { guia.hidden = tip.hidden = true; return; }
        const d = new Date(h.x0.getTime() + i * 864e5), px = (h.izq + (h.W - h.izq - h.der) * i / (h.n - 1)) * k;
        const fila = (t, v, c) => v == null ? "" : `<div><i style="background:${c}"></i>${t}<b>${num(v, h.dec + 1)}</b></div>`;
        tip.innerHTML = `<b>${d.getUTCDate()} ${MES[d.getUTCMonth()]}</b>${fila(`${s.año}-${s.año + 1}`, s.actual[i], COLOR.actual)}${fila(`${s.año - 1}-${s.año}`, s.anterior[i], COLOR.anterior)}${fila("Promedio histórico", s.promedio[i], COLOR.promedio)}${s.minimo[i] != null ? `<div><i></i>Mín. y máx.<b>${num(s.minimo[i], h.dec + 1)} – ${num(s.maximo[i], h.dec + 1)}</b></div>` : ""}`;
        guia.hidden = tip.hidden = false;
        guia.style.left = px + "px";
        tip.style.left = Math.min(Math.max(px + 12, 0), caj.width - 190) + "px";
      });
      lienzo.addEventListener("pointerleave", () => { guia.hidden = tip.hidden = true; });
      const B = window.BCRP;
      g.querySelector('[data-a="copiar"]').addEventListener("click", async () => { try { await B.copiar(h.svg); decir("Copiado: pégalo en Word o PowerPoint con Ctrl+V.", true); } catch (er) { decir(er.message, false); } });
      g.querySelector('[data-a="png"]').addEventListener("click", async () => { try { await B.descargarPng(h.svg, nombre); } catch (er) { decir(er.message, false); } });
      g.querySelector('[data-a="svg"]').addEventListener("click", () => B.descargar(h.svg, nombre));
      g.querySelector('[data-a="csv"]').addEventListener("click", () => {
        const cols = [["actual", `${s.año}-${s.año + 1}`], ["anterior", `${s.año - 1}-${s.año}`], ["promedio", "PROMEDIO_HISTORICO"], ["minimo", "MINIMO"], ["maximo", "MAXIMO"], ["rojo", "UMBRAL_ROJO"], ["naranja", "UMBRAL_NARANJA"], ["amarillo", "UMBRAL_AMARILLO"]];
        const lineas = [["FECHA", ...cols.map((c) => c[1])].join(",")];
        for (let i = 0; i < s.dias; i++) { const d = new Date(h.x0.getTime() + i * 864e5); lineas.push([dmy(d.toISOString().slice(0, 10)), ...cols.map(([k]) => s[k][i] ?? "")].join(",")); }
        const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + lineas.join("\n")], { type: "text/csv" })); a.download = nombre.replace(/\s+/g, "_") + ".csv";
        document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      });
    }
    if (j.estaciones.some((e) => e.codigo === e0.c)) $("hid-est").value = e0.c;
    opciones(); dibujar();
    $("hid-est").addEventListener("change", () => { opciones(); dibujar(); });
    $("hid-var").addEventListener("change", () => { e0.v = $("hid-var").value; opciones(); dibujar(); });
    $("hid-anio").addEventListener("change", () => { e0.a = +$("hid-anio").value; dibujar(); });
    caja.querySelectorAll("[data-fila]").forEach((tr) => { const ir = () => { const f = filas[+tr.dataset.fila]; $("hid-est").value = f.e.codigo; e0.v = f.v; e0.a = null; opciones(); dibujar(); $("hid-graf").scrollIntoView({ behavior: "smooth", block: "center" }); };
      tr.addEventListener("click", ir); tr.addEventListener("keydown", (ev) => { if (ev.key === "Enter") ir(); }); });
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
    ["control", "Control de la serie diaria", "Por estación y variable: primera y última fecha, días con dato, días faltantes, saltos raros y estado (OK o REVISAR)."]];
  async function descargas(r, caja) {
    caja.innerHTML = '<div class="loading"><span class="spin"></span>Consultando…</div>';
    let res;
    try { res = await api("/v1/hidrologia"); } catch (e) { caja.innerHTML = `<div class="err-box"><b>No se pudo consultar</b><span>${esc(e.message)}</span></div>`; return; }
    ponerHasta(res);
    if (!res.hay) { caja.innerHTML = '<div class="vacio-caja"><b>Todavía no hay datos de SENAMHI en la página.</b><span>Ve a la pestaña «Actualizar»: allí se sube el archivo que deja el recolector.</span></div>'; return; }
    const u = (a, d, f) => `/v1/hidrologia/descargar?archivo=${a}${d ? "&departamento=" + d : ""}${f ? "&formato=" + f : ""}`;
    caja.innerHTML = `<div class="caja"><h3>Datos del scraper de SENAMHI</h3>
      <p>Son los mismos archivos que arma el notebook de Colab. Hay <b>${num(res.filas_diario, 0)}</b> filas diarias de <b>${res.estaciones_con_datos}</b> estaciones, <b>${num(res.filas_info_diaria, 0)}</b> de Información Diaria y <b>${num(res.filas_mensual, 0)}</b> mensuales; el último dato es del <b>${dmy(res.ultima_fecha)}</b>.</p>
      <div class="scroll"><table><tr><th>Archivo</th><th>Qué trae</th><th>Solo ${esc(r.nombre)}</th><th>Todo el país</th></tr>
      ${ARCH.map(([a, t, d]) => `<tr><td><b>${t}</b></td><td>${d}</td><td class="hid-enl"><a href="${u(a, r.cod, "xlsx")}">Excel</a> · <a href="${u(a, r.cod)}">CSV</a></td><td class="hid-enl"><a href="${u(a)}">CSV</a>${a === "diario" || a === "info-diaria" ? "" : ` · <a href="${u(a, "", "xlsx")}">Excel</a>`}</td></tr>`).join("")}</table></div>
      <div class="fila"><a class="btn" href="${u("todo", r.cod)}">Todo lo de ${esc(r.nombre)} (.zip)</a><a class="btn sec" href="${u("todo")}">Todo el país, con los controles (.zip)</a></div>
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
    ["meta", "estaciones", "zonales", "infoMeta", "fichas"].forEach((k) => { if (crudo[k] && Object.keys(crudo[k]).length) pon(k, crudo[k]); });
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
            <span>En la pestaña de SENAMHI pulsa <b>F12</b>, entra a <b>Console</b>, pega con <b>Ctrl+V</b> y pulsa <b>Enter</b>. Aparece el panel abajo a la derecha y empieza solo. Tarda unos 5 minutos; deja la pestaña abierta. Si Chrome no deja pegar, escribe <b>allow pasting</b>, Enter, y vuelve a pegar.</span></div>
          <div><b>3 · Sube aquí el archivo</b><span>Al terminar se descarga <b>SENAMHI_crudo_AAAA-MM-DD.json</b> (carpeta Descargas). Arrástralo al recuadro de abajo. La página compara y sube solo lo nuevo.</span></div></div>
        <label class="zona-subida" for="hid-arch" id="hid-zona"><b>Arrastra aquí SENAMHI_crudo_….json o haz clic para elegirlo</b><span>El archivo trae todo lo recolectado desde 2023 (unos 33 MB); solo viaja lo que cambió</span><input class="solo-lector" type="file" id="hid-arch" accept=".json,application/json"></label>
        <div class="hid-barra" hidden><span></span></div><div id="hid-res" aria-live="polite"></div></div>
      <details class="caja"><summary><b>Preguntas frecuentes</b></summary>
        <p><b>¿Hay algo más rápido que la consola?</b> Puedes probar un favorito: arrastra <a class="hid-fav" href="${esc(FAVORITO)}" title="Arrástrame a la barra de favoritos">Recolector SENAMHI</a> a la barra de favoritos (Ctrl+Mayús+B la muestra) y haz clic en él estando en SENAMHI. En algunos navegadores la página de SENAMHI no deja correr favoritos; si al hacer clic no aparece el panel, usa la consola.</p>
        <p><b>¿Qué fechas pongo en el panel?</b> Ninguna: deja «Desde 01/01/2023». El recolector recuerda lo que ya bajó y cada día solo pide lo nuevo: el año hidrológico en curso de todas las estaciones (así recoge también las correcciones que SENAMHI hace a días pasados), los 3 últimos meses de la Información Mensual y la Información Diaria de hoy, de ayer y de los días que falten.</p>
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

  window.HIDRO = { TABS: ["Gráfico", "Descargar datos", "Actualizar"], hidrograma, alerta, piezasDe,
    pintar(r, caja, pestaña) { return (pestaña === "Actualizar" ? actualizar : pestaña === "Descargar datos" ? descargas : grafico)(r, caja); } };
})();
