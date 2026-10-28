// Cuadros y gráficos con el formato de la Síntesis de Actividad Económica (BCRP, Sucursal Iquitos), en SVG para
// pegarlos en el informe: Arial, filetes horizontales, miles con espacio y decimales con coma; los gráficos, barras
// celestes con borde azul (el mismo mes de cada año, en blanco), meses «J.24 J A S … J.25», notas de fuente y elaboración.
// window.BCRP.cuadro(spec) / .anexo(spec) / .barras(spec) devuelven el SVG (texto); .descargar, .copiar, .png lo exportan.
(function () {
  "use strict";
  const FUENTE = "Arial, Helvetica, sans-serif", TINTA = "#000", AZUL = "#4F81BD", RELLENO = "#C6D9F1", GRIS = "#C0C0C0";
  const ELABORACION = "Elaboración: BCRP, Sucursal Iquitos. Departamento de Estudios Económicos.";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const lienzo = document.createElement("canvas").getContext("2d");
  const ancho = (t, px, negrita) => { lienzo.font = `${negrita ? "bold " : ""}${px}px Arial`; return lienzo.measureText(String(t ?? "")).width; };

  // números como en la síntesis: 1 215 · 2 625,0 · -89,9
  const miles = (s) => s.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  function num(v, dec = 0) {
    if (v == null || v === "" || Number.isNaN(v)) return "";
    if (typeof v === "string") return v;
    const r = Math.abs(v).toFixed(dec).split("."), s = miles(r[0]) + (dec ? "," + r[1] : "");
    return (v < 0 && +Math.abs(v).toFixed(dec) !== 0 ? "-" : "") + s;
  }
  const var1 = (v) => v == null ? "-" : num(v, 1);

  // título: «CUADRO N° 4» / «UCAYALI: PRODUCCIÓN PESQUERA» con llamada «1/» / «(Toneladas)»
  function cabecera(spec, W, y0) {
    const c = W / 2, out = [];
    let y = y0;
    if (spec.numero) { out.push(`<text x="${c}" y="${y}" text-anchor="middle" font-weight="bold" font-size="12">${esc(spec.numero)}</text>`); y += 15; }
    const tw = ancho(spec.titulo, 12, true);
    out.push(`<text x="${c}" y="${y}" text-anchor="middle" font-weight="bold" font-size="12">${esc(spec.titulo)}${spec.llamada ? `<tspan font-size="7.5" dy="-5">${esc(spec.llamada)}</tspan>` : ""}</text>`);
    y += 14;
    if (spec.unidad) { out.push(`<text x="${c}" y="${y}" text-anchor="middle" font-size="11">${esc(spec.unidad)}</text>`); y += 6; }
    return { svg: out.join(""), y, tw };
  }
  function notas(lista, x, y) {
    const out = [];
    for (const n of lista) { out.push(`<text x="${x}" y="${y}" font-size="9">${esc(n)}</text>`); y += 11; }
    return { svg: out.join(""), y };
  }
  const envolver = (W, H, cuerpo) => `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Math.ceil(H)}" viewBox="0 0 ${W} ${Math.ceil(H)}" font-family="${FUENTE}" fill="${TINTA}"><rect width="100%" height="100%" fill="#fff"/>${cuerpo}</svg>`;

  // ── Cuadro del texto: spec = {numero, titulo, llamada, unidad, cab: [[{t, span, linea}]], filas: [{c: [..], b, ind, sep, total}], notas, minCol}
  const api = { ultimo: null };                          // el último cuadro dibujado (tipo y spec), para el Excel
  function cuadro(spec) {
    api.ultimo = { tipo: "cuadro", spec };
    const F = 11, filaH = 16, pad = 8, nCols = spec.filas.reduce((m, f) => Math.max(m, f.c.length), 0);
    // anchos: la primera columna, lo que pida su texto (con sangría); las demás, el más ancho de su columna
    const w = Array.from({ length: nCols }, (_, j) => {
      let m = j ? (spec.minCol || 46) : 120;
      spec.filas.forEach((f) => { if (f.c[j] != null) m = Math.max(m, ancho(f.c[j], F, f.b) + (j ? 0 : (f.ind || 0) * 12) + pad * 2); });
      return Math.ceil(m);
    });
    spec.cab.forEach((fila) => { let j = 0; fila.forEach((h) => { const span = h.span || 1; const need = ancho(h.t, F, true) + pad * 2;
      const tiene = w.slice(j, j + span).reduce((a, b) => a + b, 0); if (need > tiene) for (let k = j; k < j + span; k++) w[k] += Math.ceil((need - tiene) / span); j += span; }); });
    const T = w.reduce((a, b) => a + b, 0), M = 16, W = T + 2 * M, xs = [M];
    w.forEach((x, j) => xs.push(xs[j] + x));
    const h = cabecera(spec, W, 18), out = [h.svg];
    let y = h.y + 6;
    out.push(`<line x1="${M}" x2="${M + T}" y1="${y}" y2="${y}" stroke="${TINTA}" stroke-width="1"/>`);
    spec.cab.forEach((fila, k) => {
      let j = 0;
      fila.forEach((c) => {
        const span = c.span || 1, x0 = xs[j], x1 = xs[j + span];
        if (c.t) out.push(`<text x="${j === 0 ? x0 + pad : (x0 + x1) / 2 + (span === 1 ? (x1 - x0) / 2 - pad : 0)}" y="${y + 12}" font-size="${F}" font-weight="bold" text-anchor="${j === 0 ? "start" : span === 1 ? "end" : "middle"}">${esc(c.t)}</text>`);
        if (c.linea) out.push(`<line x1="${x0 + 4}" x2="${x1 - 4}" y1="${y + filaH}" y2="${y + filaH}" stroke="${TINTA}" stroke-width="0.8"/>`);
        j += span;
      });
      y += filaH;
      if (k === spec.cab.length - 1) out.push(`<line x1="${M}" x2="${M + T}" y1="${y + 2}" y2="${y + 2}" stroke="${TINTA}" stroke-width="1"/>`);
    });
    y += 4;
    spec.filas.forEach((f, i) => {
      if (f.sep) y += 6;
      if (f.total) { y += 3; out.push(`<line x1="${M}" x2="${M + T}" y1="${y}" y2="${y}" stroke="${TINTA}" stroke-width="1"/>`); }
      f.c.forEach((v, j) => {
        if (v == null || v === "") return;
        out.push(`<text x="${j ? xs[j + 1] - pad : xs[0] + pad + (f.ind || 0) * 12}" y="${y + 12}" font-size="${F}"${f.b ? ' font-weight="bold"' : ""} text-anchor="${j ? "end" : "start"}">${esc(v)}</text>`);
      });
      y += filaH;
      if (i === spec.filas.length - 1) out.push(`<line x1="${M}" x2="${M + T}" y1="${y + 2}" y2="${y + 2}" stroke="${TINTA}" stroke-width="1"/>`);
    });
    const n = notas([...(spec.notas || []), ELABORACION], M + 4, y + 14);
    out.push(n.svg);
    return envolver(W, n.y + 4, out.join(""));
  }

  // ── Anexo (horizontal): cabecera gris, años arriba, separador antes y después del total, rótulos repetidos a la derecha.
  // spec = {numero, titulo, llamada, unidad, rotulo, columnas: [{etq, anio, total}], filas: [{nombre, valores, tipo}], dec, notas}
  function anexo(spec) {
    api.ultimo = { tipo: "anexo", spec };
    const F = 10, filaH = 15, pad = 6, dec = spec.dec ?? 1;
    const etqW = Math.ceil(Math.max(130, ...spec.filas.map((f) => ancho(f.nombre, F, f.tipo !== "item") + 18)));
    const cw = spec.columnas.map((c, j) => Math.ceil(Math.max(c.total ? 50 : 38, ...spec.filas.map((f) => ancho(num((f.valores || [])[j], dec), F, f.tipo !== "item") + pad * 2))));
    const T = etqW * 2 + cw.reduce((a, b) => a + b, 0), M = 14, W = T + 2 * M;
    const xs = [M + etqW];
    cw.forEach((x, j) => xs.push(xs[j] + x));
    const h = cabecera({ ...spec, numero: null }, W, 34), out = [];
    if (spec.numero) out.push(`<text x="${M}" y="16" font-weight="bold" font-size="12">${esc(spec.numero)}</text>`);
    out.push(h.svg);
    let y = h.y + 4;
    const y0 = y, cabH = filaH * 2;
    out.push(`<rect x="${M}" y="${y}" width="${T}" height="${cabH}" fill="${GRIS}"/>`);
    // años sobre sus meses; el total, en su propia columna
    const grupos = [];
    spec.columnas.forEach((c, j) => { const k = c.total ? `t${j}` : String(c.anio); if (!grupos.length || grupos[grupos.length - 1].k !== k) grupos.push({ k, t: c.total ? "Total" : String(c.anio), j0: j, j1: j }); else grupos[grupos.length - 1].j1 = j; });
    grupos.forEach((g) => out.push(`<text x="${(xs[g.j0] + xs[g.j1 + 1]) / 2}" y="${y + 11}" text-anchor="middle" font-size="${F}" font-weight="bold">${esc(g.t)}</text>`));
    spec.columnas.forEach((c, j) => out.push(`<text x="${xs[j + 1] - pad}" y="${y + filaH + 11}" text-anchor="end" font-size="${F}" font-weight="bold">${esc(c.etq)}</text>`));
    if (spec.rotulo) { out.push(`<text x="${M + etqW / 2}" y="${y + cabH / 2 + 4}" text-anchor="middle" font-size="${F}" font-weight="bold">${esc(spec.rotulo)}</text>`);
      out.push(`<text x="${M + T - etqW / 2}" y="${y + cabH / 2 + 4}" text-anchor="middle" font-size="${F}" font-weight="bold">${esc(spec.rotulo)}</text>`); }
    out.push(`<line x1="${xs[0]}" x2="${xs[xs.length - 1]}" y1="${y + filaH}" y2="${y + filaH}" stroke="${TINTA}" stroke-width="0.6"/>`);
    y += cabH + 8;
    spec.filas.forEach((f) => {
      if (f.tipo === "grupo" || f.tipo === "titulo") y += 6;
      if (f.tipo === "total") y += 4;
      const negrita = f.tipo !== "item";
      if (f.tipo === "titulo" || f.tipo === "total") out.push(`<rect x="${M}" y="${y}" width="${T}" height="${filaH}" fill="${GRIS}"/>`);
      const ind = f.tipo === "item" ? 14 : 4;
      out.push(`<text x="${M + ind}" y="${y + 11}" font-size="${F}"${negrita ? ' font-weight="bold"' : ""}>${esc(f.nombre)}</text>`);
      out.push(`<text x="${xs[xs.length - 1] + ind}" y="${y + 11}" font-size="${F}"${negrita ? ' font-weight="bold"' : ""}>${esc(f.nombre)}</text>`);
      if (f.valores) f.valores.forEach((v, j) => out.push(`<text x="${xs[j + 1] - pad}" y="${y + 11}" text-anchor="end" font-size="${F}"${negrita ? ' font-weight="bold"' : ""}>${esc(num(v, dec))}</text>`));
      y += filaH;
    });
    y += 4;
    // marco y separadores verticales: rótulos, cada año y el total
    const sep = [M, xs[0], xs[xs.length - 1], M + T];
    spec.columnas.forEach((c, j) => { if (c.total) sep.push(xs[j], xs[j + 1]); });
    [...new Set(sep)].forEach((x) => out.push(`<line x1="${x}" x2="${x}" y1="${y0}" y2="${y}" stroke="${TINTA}" stroke-width="0.8"/>`));
    out.push(`<line x1="${M}" x2="${M + T}" y1="${y0}" y2="${y0}" stroke="${TINTA}" stroke-width="0.8"/><line x1="${M}" x2="${M + T}" y1="${y0 + cabH}" y2="${y0 + cabH}" stroke="${TINTA}" stroke-width="0.8"/><line x1="${M}" x2="${M + T}" y1="${y}" y2="${y}" stroke="${TINTA}" stroke-width="0.8"/>`);
    const n = notas([...(spec.notas || []), ELABORACION], M, y + 13);
    out.push(n.svg);
    return envolver(W, n.y + 4, out.join(""));
  }

  // ── Gráfico de barras: spec = {numero, titulo, unidad, puntos: [{periodo: "Jun. 2025", valor}], dec, notas}
  const INICIAL = { Ene: "E", Feb: "F", Mar: "M", Abr: "A", May: "M", Jun: "J", Jul: "J", Ago: "A", Set: "S", Oct: "O", Nov: "N", Dic: "D" };
  function pasoBonito(rango, n = 7) {
    const bruto = rango / n, pot = 10 ** Math.floor(Math.log10(bruto || 1));
    return [1, 2, 2.5, 3, 5, 10].map((k) => k * pot).find((k) => k >= bruto) || 10 * pot;
  }
  function barras(spec) {
    api.ultimo = { tipo: "barras", spec };
    const p = spec.puntos.filter((x) => x.valor != null), dec = spec.dec ?? 1, W = 640, izq = 46, der = 12, arr = 66, abajo = 22, alto = 250;
    const ult = p.length ? p[p.length - 1].periodo.split(" ")[0].replace(".", "") : "";
    let lo = Math.min(0, ...p.map((x) => x.valor)), hi = Math.max(0, ...p.map((x) => x.valor));
    const paso = pasoBonito(hi - lo || 1);
    lo = Math.floor(lo / paso) * paso; hi = Math.ceil(hi / paso) * paso;
    if (hi - lo < paso) hi = lo + paso;
    const Y = (v) => arr + (hi - v) / (hi - lo) * alto, bw = (W - izq - der) / Math.max(p.length, 1);
    const h = cabecera(spec, W, 18), out = [h.svg];
    // eje Y con marcas cada «paso»; eje X en el cero
    for (let v = lo; v <= hi + 1e-9; v += paso) {
      out.push(`<line x1="${izq - 4}" x2="${izq}" y1="${Y(v)}" y2="${Y(v)}" stroke="#808080" stroke-width="0.8"/><text x="${izq - 7}" y="${Y(v) + 3.5}" text-anchor="end" font-size="9.5">${esc(num(v, 1))}</text>`);
    }
    out.push(`<line x1="${izq}" x2="${izq}" y1="${Y(hi)}" y2="${Y(lo)}" stroke="#808080" stroke-width="0.8"/>`);
    p.forEach((x, i) => {
      const [m, a] = x.periodo.split(" "), mm = m.replace(".", ""), resalta = mm === ult;
      const x0 = izq + i * bw + bw * 0.16, wv = bw * 0.68, yv = Y(Math.max(x.valor, 0)), hv = Math.max(Math.abs(Y(x.valor) - Y(0)), 0.8);
      out.push(`<rect x="${x0.toFixed(1)}" y="${yv.toFixed(1)}" width="${wv.toFixed(1)}" height="${hv.toFixed(1)}" fill="${resalta ? "#fff" : RELLENO}" stroke="${AZUL}" stroke-width="1"/>`);
      const ty = x.valor >= 0 ? yv - 4 : yv + hv + 10;
      out.push(`<text x="${(x0 + wv / 2).toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="middle" font-size="9">${esc(num(x.valor, dec))}</text>`);
      out.push(`<text x="${(x0 + wv / 2).toFixed(1)}" y="${Y(lo) + 14}" text-anchor="middle" font-size="9.5">${esc((INICIAL[mm] || mm[0]) + (resalta || i === 0 ? "." + a.slice(2) : ""))}</text>`);
    });
    out.push(`<line x1="${izq}" x2="${W - der}" y1="${Y(0)}" y2="${Y(0)}" stroke="#808080" stroke-width="0.8"/>`);
    const n = notas([...(spec.notas || []), ELABORACION], izq - 30, Y(lo) + abajo + 12);
    out.push(n.svg);
    return envolver(W, n.y + 4, out.join(""));
  }

  // ── Exportar ──
  const nombreArchivo = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "_").slice(0, 90) || "grafico";
  function bajar(blob, nombre) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = nombre;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  function descargar(svg, nombre) { bajar(new Blob([svg], { type: "image/svg+xml" }), nombreArchivo(nombre) + ".svg"); }
  // PNG a 3x (para pegar en Word con buena resolución)
  function png(svg, escala = 3) {
    return new Promise((ok, mal) => {
      const img = new Image(), m = svg.match(/width="(\d+)" height="(\d+)"/);
      img.onload = () => {
        const c = document.createElement("canvas");
        c.width = +m[1] * escala; c.height = +m[2] * escala;
        const g = c.getContext("2d"); g.scale(escala, escala); g.drawImage(img, 0, 0);
        c.toBlob((b) => b ? ok(b) : mal(new Error("no se pudo convertir a imagen")), "image/png");
      };
      img.onerror = () => mal(new Error("no se pudo dibujar el SVG"));
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    });
  }
  async function copiar(svg) {
    if (!navigator.clipboard || !window.ClipboardItem) throw new Error("este navegador no deja copiar imágenes; usa «Descargar»");
    await navigator.clipboard.write([new ClipboardItem({ "image/png": png(svg) })]);
  }
  async function descargarPng(svg, nombre) { bajar(await png(svg), nombreArchivo(nombre) + ".png"); }

  // Excel con el mismo formato: lo arma el servidor (POST /v1/bcrp/excel) con el tipo y los datos del cuadro
  async function excel(ultimo, nombre) {
    const r = await fetch("/v1/bcrp/excel", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...ultimo, nombre }) });
    if (!r.ok) throw new Error(`No se pudo armar el Excel (${r.status}).`);
    bajar(await r.blob(), nombreArchivo(nombre) + ".xlsx");
  }

  window.BCRP = Object.assign(api, { cuadro, anexo, barras, descargar, descargarPng, copiar, excel, num, var1, ELABORACION });
})();
