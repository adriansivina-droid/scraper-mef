// Gráficos DRAE: dibuja en SVG los gráficos de las SERIES de cada departamento con la paleta y el estilo del
// Seminario de Periodistas (BCRP, Sucursal Iquitos): Barlow, azul marino y turquesa, etiquetas de datos, sin cuadrícula
// ni eje vertical, la región en turquesa y el Perú en azul marino (línea con círculos blancos), «Otros» en gris.
// window.DRAE.svg(spec, region, {soloGrafico}) devuelve el SVG (texto); soloGrafico quita título, subtítulo y notas.
(function () {
  "use strict";
  const NAVY = "#111149", TURQ = "#72D2D5", NARANJA = "#DD6140", AMARILLO = "#FFC41D", ORO = "#D59D00", GRIS = "#CCD3DF",
        TURQ_CLARO = "#CFF0F1", MORADO = "#7030A0", TINTA = "#181818", BLANCO = "#FEFEFE";
  const PALETA = [NAVY, TURQ, NARANJA, AMARILLO, ORO, GRIS, MORADO, TURQ_CLARO];
  const FUENTE = "Barlow, 'Segoe UI', Arial, sans-serif";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const lienzo = document.createElement("canvas").getContext("2d");
  const ancho = (t, px, negrita) => { lienzo.font = `${negrita ? "600 " : ""}${px}px Barlow, Arial`; return lienzo.measureText(String(t ?? "")).width; };
  const norm = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().trim();

  // decimales según el formato del Excel («0.0», «#,##0», «0.0%»…); si no hay, 1 decimal salvo números grandes
  function decimales(serie, valores) {
    const f = serie.formato || "";
    const m = f.match(/0\.(0+)/);
    if (m) return m[1].length;
    if (/0/.test(f) && !/\./.test(f) && !/general/i.test(f)) return 0;
    const max = Math.max(...valores.filter((v) => v != null).map(Math.abs), 0);
    return max >= 1000 ? 0 : 1;
  }
  const pct = (serie) => /%/.test(serie.formato || "");
  function num(v, dec, esPct) {
    if (v == null || Number.isNaN(v)) return "";
    const x = esPct ? v * 100 : v;
    const r = Math.abs(x).toFixed(dec).split(".");
    const s = r[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ") + (dec ? "," + r[1] : "");
    return (x < 0 && +Math.abs(x).toFixed(dec) !== 0 ? "-" : "") + s + (esPct ? "%" : "");
  }

  // colores: el Perú (o nacional) en azul marino, la región en turquesa; las demás series, la paleta en orden
  function colores(series, region) {
    const R = norm(region), usados = new Set(), salida = [];
    series.forEach((s, i) => {
      const n = norm(s.nombre);
      let c = null;
      if (/^(PERU|PAIS|NACIONAL|TOTAL PAIS|PROMEDIO NACIONAL|VARIACION NACIONAL)\b/.test(n) && n.length < 30) c = NAVY;
      else if (R && n.includes(R)) c = TURQ;
      salida[i] = c; if (c) usados.add(c);
    });
    if (series.length === 1 && !salida[0]) return [TURQ];           // una sola serie: turquesa (como en el Seminario)
    let k = 0;
    return salida.map((c) => { if (c) return c; while (usados.has(PALETA[k % PALETA.length]) && k < 20) k++; const x = PALETA[k % PALETA.length]; k++; return x; });
  }
  // en una sola serie de barras por departamento: la región en naranja, el Perú en azul marino, el resto turquesa
  function colorCategoria(cat, region, base) {
    const n = norm(cat), R = norm(region);
    if (/^(PERU|PAIS|NACIONAL|PROMEDIO)\b/.test(n)) return NAVY;
    if (R && (n === R || n.startsWith(R + " ") || n.startsWith(R + "*"))) return NARANJA;
    return base;
  }

  // categorías que son fechas de Excel (número de días desde 1900): «Ene.19»
  const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"];
  function etiquetasCat(cats) {
    const nums = cats.map((c) => Number(c));
    if (cats.length > 2 && nums.every((x) => Number.isFinite(x) && x > 30000 && x < 60000)) {
      return nums.map((x) => { const d = new Date(Date.UTC(1899, 11, 30) + x * 864e5); return `${MESES[d.getUTCMonth()]}.${String(d.getUTCFullYear()).slice(2)}`; });
    }
    return cats.map((c) => String(c).replace(/\.0$/, ""));
  }
  function cabecera(g, W) {
    if (g._solo) return { svg: "", y: 14 };              // solo el gráfico: sin título ni subtítulo
    const out = [];
    let y = 22;
    const lineas = partir(g.titulo || g.hoja || "", W - 40, 14, true);
    lineas.forEach((l) => { out.push(`<text x="${W / 2}" y="${y}" text-anchor="middle" font-size="14" font-weight="600" fill="${NAVY}">${esc(l)}</text>`); y += 17; });
    if (g.subtitulo) { out.push(`<text x="${W / 2}" y="${y}" text-anchor="middle" font-size="11.5" fill="${TINTA}">${esc(g.subtitulo)}</text>`); y += 15; }
    return { svg: out.join(""), y: y + 4 };
  }
  function partir(t, max, px, negrita) {
    const palabras = String(t).split(/\s+/), lineas = [];
    let l = "";
    palabras.forEach((p) => { const c = l ? l + " " + p : p; if (ancho(c, px, negrita) > max && l) { lineas.push(l); l = p; } else l = c; });
    if (l) lineas.push(l);
    return lineas.slice(0, 3);
  }
  function leyenda(items, W, y) {
    const out = [], gap = 18, w = items.map((it) => 16 + ancho(it.nombre, 11) + gap);
    const filas = [[]]; let acc = 0;
    items.forEach((it, i) => { if (acc + w[i] > W - 40 && filas[filas.length - 1].length) { filas.push([]); acc = 0; } filas[filas.length - 1].push(i); acc += w[i]; });
    filas.forEach((f) => {
      let x = (W - f.reduce((a, i) => a + w[i], 0) + gap) / 2;
      f.forEach((i) => {
        const it = items[i];
        out.push(it.linea ? `<line x1="${x}" x2="${x + 12}" y1="${y - 4}" y2="${y - 4}" stroke="${it.color}" stroke-width="2"/><circle cx="${x + 6}" cy="${y - 4}" r="3" fill="${BLANCO}" stroke="${it.color}" stroke-width="1.5"/>`
          : `<rect x="${x}" y="${y - 9}" width="11" height="10" fill="${it.color}"/>`);
        out.push(`<text x="${x + 16}" y="${y}" font-size="11" fill="${TINTA}">${esc(it.nombre)}</text>`);
        x += w[i];
      });
      y += 16;
    });
    return { svg: out.join(""), y };
  }
  const envolver = (W, H, cuerpo) => `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Math.ceil(H)}" viewBox="0 0 ${W} ${Math.ceil(H)}" font-family="${FUENTE}" fill="${TINTA}"><rect width="100%" height="100%" fill="#fff"/>${cuerpo}</svg>`;
  function notas(g, W, y) {
    const out = [];
    (g.notas || []).slice(0, 3).forEach((n) => { out.push(`<text x="16" y="${y}" font-size="9" fill="#585859">${esc(n.length > 150 ? n.slice(0, 147) + "…" : n)}</text>`); y += 11; });
    return { svg: out.join(""), y };
  }

  // ── circular y anillo ──
  function circular(g, region) {
    const W = 560, s = g.series[0], cab = cabecera(g, W);
    const datos = g.categorias.map((c, i) => ({ nombre: c, v: s.valores[i] })).filter((d) => d.v != null && d.v > 0);
    const total = datos.reduce((a, d) => a + d.v, 0) || 1;
    const R = 105, cx = W / 2, cy = cab.y + R + 30, out = [cab.svg];
    let a = -Math.PI / 2, k = 0;
    const etq = [];
    datos.forEach((d) => {
      const frac = d.v / total, a1 = a + frac * 2 * Math.PI;
      const fill = /^otro/i.test(d.nombre) ? GRIS : PALETA[k++ % PALETA.length];
      const p0 = [cx + R * Math.cos(a), cy + R * Math.sin(a)], p1 = [cx + R * Math.cos(a1), cy + R * Math.sin(a1)];
      out.push(frac > 0.9999 ? `<circle cx="${cx}" cy="${cy}" r="${R}" fill="${fill}" stroke="${BLANCO}" stroke-width="1.5"/>`
        : `<path d="M${cx} ${cy} L${p0[0].toFixed(1)} ${p0[1].toFixed(1)} A${R} ${R} 0 ${frac > 0.5 ? 1 : 0} 1 ${p1[0].toFixed(1)} ${p1[1].toFixed(1)} Z" fill="${fill}" stroke="${BLANCO}" stroke-width="1.5"/>`);
      const am = (a + a1) / 2;
      etq.push({ d, frac, am, fill });
      a = a1;
    });
    if (g.tipo === "anillo") out.push(`<circle cx="${cx}" cy="${cy}" r="${R * 0.55}" fill="#fff"/>`);
    const dec = s.formato && /%/.test(s.formato) ? 1 : 1;
    // etiquetas: dentro las tajadas grandes; fuera, con línea guía, las pequeñas (sin encimarse)
    const fuera = { izq: [], der: [] };
    etq.forEach((e) => {
      const txt = `${num(e.frac * 100, dec)}%`;
      const cabe = ancho(e.d.nombre, 10, true) < R * 0.75 * Math.min(1, e.frac * 5);
      if (e.frac >= 0.1 && cabe && g.tipo !== "anillo") {
        const rr = R * 0.62, x = cx + rr * Math.cos(e.am), y = cy + rr * Math.sin(e.am), claro = [TURQ, AMARILLO, GRIS, TURQ_CLARO].includes(e.fill);
        out.push(`<text x="${x.toFixed(1)}" y="${(y - 2).toFixed(1)}" text-anchor="middle" font-size="10" font-weight="600" fill="${claro ? NAVY : "#fff"}">${esc(e.d.nombre.length > 18 ? e.d.nombre.slice(0, 17) + "…" : e.d.nombre)}</text><text x="${x.toFixed(1)}" y="${(y + 10).toFixed(1)}" text-anchor="middle" font-size="10" fill="${claro ? NAVY : "#fff"}">${txt}</text>`);
      } else (Math.cos(e.am) >= 0 ? fuera.der : fuera.izq).push({ ...e, txt });
    });
    let H = cy + R + 34;
    ["izq", "der"].forEach((lado) => {
      const L = fuera[lado].sort((p, q) => Math.sin(p.am) - Math.sin(q.am));
      let ultimo = -1e9;
      L.forEach((e) => {
        let y = cy + (R + 18) * Math.sin(e.am);
        y = Math.max(y, ultimo + 24); ultimo = y;
        const xe = cx + R * Math.cos(e.am), ye = cy + R * Math.sin(e.am), xt = cx + (lado === "der" ? R + 30 : -R - 30);
        out.push(`<polyline points="${xe.toFixed(1)},${ye.toFixed(1)} ${(xt + (lado === "der" ? -6 : 6)).toFixed(1)},${y.toFixed(1)} ${xt.toFixed(1)},${y.toFixed(1)}" fill="none" stroke="${TINTA}" stroke-width="0.6"/>`);
        out.push(`<text x="${(xt + (lado === "der" ? 3 : -3)).toFixed(1)}" y="${(y - 1).toFixed(1)}" font-size="10" text-anchor="${lado === "der" ? "start" : "end"}">${esc(e.d.nombre)}</text><text x="${(xt + (lado === "der" ? 3 : -3)).toFixed(1)}" y="${(y + 10).toFixed(1)}" font-size="10" font-weight="600" text-anchor="${lado === "der" ? "start" : "end"}">${e.txt}</text>`);
        H = Math.max(H, y + 24);
      });
    });
    const n = notas(g, W, H);
    return envolver(W, n.y + 6, out.join("") + n.svg);
  }

  // ── barras, líneas, áreas y combinados (eje de categorías abajo o a la izquierda) ──
  function cartesiano(g, region) {
    const series = g.series, n = g.categorias.length, horiz = g.horizontal && series.every((s) => s.tipo === "barras");
    if (horiz) return horizontal(g, region);
    const cols = colores(series, region);
    const soloLineas = series.every((s) => s.tipo !== "barras");
    const W = Math.max(620, Math.min(soloLineas ? 860 : 1100, 70 + n * (series.filter((s) => s.tipo === "barras").length > 1 ? 46 : 30)));
    const cab = cabecera(g, W);
    const cats = etiquetasCat(g.categorias);
    const largoCat = Math.max(...cats.map((c) => ancho(c, 10.5)), 0), paso = (W - 60) / Math.max(n, 1);
    const rotar = largoCat > paso - 4;
    const altoCat = rotar ? Math.min(110, largoCat * 0.98 + 8) : 18;
    const items = series.map((s, i) => ({ nombre: s.nombre, color: cols[i], linea: s.tipo === "lineas" }));
    const conLeyenda = series.length > 1 && series.some((s) => s.nombre);
    const top = cab.y + 10, altoPlot = 240, base = top + altoPlot;
    const izq = 30, der = W - 30;
    // escalas por eje (el secundario es independiente)
    const bs = series.filter((s) => s.tipo === "barras");
    const apil = !!g.apilado && bs.length > 1 && new Set(bs.map((s) => s.eje || 1)).size === 1;
    const rango = (eje) => {
      const ss = series.filter((s) => (s.eje || 1) === eje);
      if (!ss.length) return null;
      let lo = 0, hi = 0;
      if (apil && eje === 1) {
        for (let i = 0; i < n; i++) { let p = 0, q = 0; ss.filter((s) => s.tipo === "barras").forEach((s) => { const v = s.valores[i]; if (v > 0) p += v; else if (v < 0) q += v; }); hi = Math.max(hi, p); lo = Math.min(lo, q); }
        ss.filter((s) => s.tipo !== "barras").forEach((s) => s.valores.forEach((v) => { if (v != null) { hi = Math.max(hi, v); lo = Math.min(lo, v); } }));
      } else ss.forEach((s) => s.valores.forEach((v) => { if (v != null) { hi = Math.max(hi, v); lo = Math.min(lo, v); } }));
      const linea = ss.every((s) => s.tipo !== "barras");
      if (linea && lo > 0) lo = lo - (hi - lo) * 0.25;        // las líneas no tienen que partir de cero
      if (hi === lo) hi = lo + 1;
      const m = (hi - lo) * 0.12;
      return [lo < 0 || !linea ? lo - (lo < 0 ? m : 0) : lo, hi + m];
    };
    const r1 = rango(1), r2 = rango(2);
    const Y = (v, eje) => { const [lo, hi] = (eje === 2 && r2) ? r2 : r1; return base - (v - lo) / (hi - lo) * altoPlot; };
    const X = (i) => izq + paso * (i + 0.5);
    const out = [cab.svg];
    const y0 = Y(Math.max(0, r1[0]), 1);
    out.push(`<line x1="${izq}" x2="${der}" y1="${y0.toFixed(1)}" y2="${y0.toFixed(1)}" stroke="#A1A1A5" stroke-width="0.8"/>`);
    // barras
    const barras = series.map((s, i) => [s, i]).filter(([s]) => s.tipo === "barras");
    const nb = apil ? 1 : barras.length, anchoGrupo = paso * (nb > 1 ? 0.78 : 0.62), wb = anchoGrupo / Math.max(nb, 1);
    const pila = Array.from({ length: n }, () => ({ p: 0, q: 0 }));
    const etiquetas = [];
    barras.forEach(([s, si], j) => {
      const dec = decimales(s, s.valores), ep = pct(s), unaDepto = barras.length === 1 && series.length === 1;
      s.valores.forEach((v, i) => {
        if (v == null) return;
        let x0, ya, yb;
        if (apil) {
          const b0 = v >= 0 ? pila[i].p : pila[i].q; const b1 = b0 + v; if (v >= 0) pila[i].p = b1; else pila[i].q = b1;
          x0 = X(i) - anchoGrupo / 2; ya = Y(b1, s.eje); yb = Y(b0, s.eje);
        } else { x0 = X(i) - anchoGrupo / 2 + j * wb; ya = Y(v, s.eje); yb = Y(0 > r1[0] ? 0 : r1[0], s.eje); }
        const top_ = Math.min(ya, yb), h = Math.max(Math.abs(yb - ya), 0.5), w = (apil ? anchoGrupo : wb) - (nb > 1 ? 1.5 : 0);
        const fill = unaDepto ? colorCategoria(cats[i], region, cols[si]) : cols[si];
        out.push(`<rect x="${x0.toFixed(1)}" y="${top_.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" fill="${fill}"/>`);
        if (s.etiquetas || series.length <= 2) {
          const txt = num(v, dec, ep);
          if (apil) { if (h > 12) etiquetas.push(`<text x="${(x0 + w / 2).toFixed(1)}" y="${(top_ + h / 2 + 3.5).toFixed(1)}" text-anchor="middle" font-size="9" font-weight="600" fill="${[TURQ, AMARILLO, GRIS, TURQ_CLARO].includes(fill) ? NAVY : "#fff"}">${txt}</text>`); }
          else etiquetas.push(`<text x="${(x0 + w / 2).toFixed(1)}" y="${(v >= 0 ? top_ - 4 : top_ + h + 11).toFixed(1)}" text-anchor="middle" font-size="${n > 20 ? 8.5 : 9.5}" font-weight="600" fill="${TINTA}">${txt}</text>`);
        }
      });
    });
    // líneas y áreas (Perú: línea con círculos blancos y la cifra dentro)
    series.forEach((s, si) => {
      if (s.tipo === "barras") return;
      const dec = decimales(s, s.valores), ep = pct(s), pts = s.valores.map((v, i) => v == null ? null : [X(i), Y(v, s.eje)]);
      const tramos = []; let t = [];
      pts.forEach((p) => { if (p) t.push(p); else if (t.length) { tramos.push(t); t = []; } });
      if (t.length) tramos.push(t);
      tramos.forEach((tr) => {
        if (s.tipo === "area") out.push(`<path d="M${tr[0][0].toFixed(1)} ${Y(Math.max(0, r1[0]), s.eje).toFixed(1)} ${tr.map((p) => `L${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ")} L${tr[tr.length - 1][0].toFixed(1)} ${Y(Math.max(0, r1[0]), s.eje).toFixed(1)} Z" fill="${cols[si]}" fill-opacity="0.35" stroke="${cols[si]}" stroke-width="1.5"/>`);
        else out.push(`<polyline points="${tr.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ")}" fill="none" stroke="${cols[si]}" stroke-width="2" stroke-linejoin="round"/>`);
      });
      const pocos = n <= 16, circulo = pocos && g.tipo === "combinado" && s.valores.every((v) => v == null || ancho(num(v, dec, ep), 9, true) < 30);
      s.valores.forEach((v, i) => {
        if (v == null) return;
        const x = X(i), y = Y(v, s.eje), txt = num(v, dec, ep);
        if (circulo) {
          const r = Math.max(11, ancho(txt, 9, true) / 2 + 4);
          out.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${BLANCO}" stroke="${cols[si]}" stroke-width="1.6"/><text x="${x.toFixed(1)}" y="${(y + 3.2).toFixed(1)}" text-anchor="middle" font-size="9" font-weight="600" fill="${TINTA}">${txt}</text>`);
        } else if (pocos && s.tipo === "lineas") {
          out.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${BLANCO}" stroke="${cols[si]}" stroke-width="1.5"/>`);
          if (s.etiquetas || series.length <= 3) etiquetas.push(`<text x="${x.toFixed(1)}" y="${(y - 7).toFixed(1)}" text-anchor="middle" font-size="9" font-weight="600" fill="${TINTA}" paint-order="stroke" stroke="#fff" stroke-width="3">${txt}</text>`);
        } else if (i === s.valores.length - 1 || (s.etiquetas && pocos)) {
          etiquetas.push(`<text x="${(x + 4).toFixed(1)}" y="${(y - 5).toFixed(1)}" text-anchor="${i === s.valores.length - 1 ? "end" : "middle"}" font-size="9" font-weight="600" fill="${TINTA}" paint-order="stroke" stroke="#fff" stroke-width="3">${txt}</text>`);
        }
      });
    });
    out.push(...etiquetas);
    // categorías (salteadas si son demasiadas)
    const cada = rotar && n > 40 ? Math.ceil(n / 40) : 1;
    cats.forEach((c, i) => {
      if (i % cada) return;
      const x = X(i);
      out.push(rotar ? `<text transform="translate(${(x + 3).toFixed(1)},${base + 8}) rotate(-90)" text-anchor="end" font-size="10" fill="${TINTA}">${esc(c)}</text>`
        : `<text x="${x.toFixed(1)}" y="${base + 15}" text-anchor="middle" font-size="10.5" fill="${TINTA}">${esc(c)}</text>`);
    });
    let y = base + altoCat + 14;
    if (conLeyenda) { const l = leyenda(items.filter((it) => it.nombre), W, y); out.push(l.svg); y = l.y; }
    const nt = notas(g, W, y + 2);
    return envolver(W, nt.y + 6, out.join("") + nt.svg);
  }

  function horizontal(g, region) {
    const series = g.series, cols = colores(series, region), n = g.categorias.length;
    const cats = g.categorias.map((c) => String(c));
    const W = 640, cab = cabecera(g, W), etqW = Math.min(240, Math.max(...cats.map((c) => ancho(c, 10.5)), 40) + 14);
    const fh = Math.max(16, Math.min(26, 360 / Math.max(n, 1))) * Math.max(1, series.length * 0.75);
    let lo = 0, hi = 0;
    series.forEach((s) => s.valores.forEach((v) => { if (v != null) { hi = Math.max(hi, v); lo = Math.min(lo, v); } }));
    const top = cab.y + 6, izq = etqW + 6 + (lo < 0 ? 40 : 0), der = W - 60;
    if (hi === lo) hi = lo + 1;
    const X = (v) => izq + (v - lo) / (hi - lo) * (der - izq), out = [cab.svg];
    const bh = (fh - 6) / series.length;
    cats.forEach((c, i) => {
      const y = top + i * fh;
      out.push(`<text x="${etqW}" y="${(y + fh / 2 + 3.5).toFixed(1)}" text-anchor="end" font-size="10.5" fill="${TINTA}">${esc(c)}</text>`);
      series.forEach((s, j) => {
        const v = s.valores[i]; if (v == null) return;
        const dec = decimales(s, s.valores), x0 = X(Math.min(0, v)), w = Math.max(Math.abs(X(v) - X(0)), 0.5), yy = y + 3 + j * bh;
        const fill = series.length === 1 ? colorCategoria(c, region, cols[j]) : cols[j];
        out.push(`<rect x="${x0.toFixed(1)}" y="${yy.toFixed(1)}" width="${w.toFixed(1)}" height="${(bh - 1).toFixed(1)}" fill="${fill}"/>`);
        out.push(`<text x="${(v >= 0 ? x0 + w + 4 : x0 - 4).toFixed(1)}" y="${(yy + bh / 2 + 3).toFixed(1)}" text-anchor="${v >= 0 ? "start" : "end"}" font-size="9.5" font-weight="600" fill="${TINTA}">${num(v, dec, pct(s))}</text>`);
      });
    });
    out.push(`<line x1="${X(0).toFixed(1)}" x2="${X(0).toFixed(1)}" y1="${top}" y2="${top + n * fh}" stroke="#A1A1A5" stroke-width="0.8"/>`);
    let y = top + n * fh + 16;
    if (series.length > 1 && series.some((s) => s.nombre)) { const l = leyenda(series.map((s, i) => ({ nombre: s.nombre, color: cols[i] })).filter((x) => x.nombre), W, y); out.push(l.svg); y = l.y; }
    const nt = notas(g, W, y + 2);
    return envolver(W, nt.y + 6, out.join("") + nt.svg);
  }

  // opc.soloGrafico: sin título, subtítulo ni notas (para pegar en la lámina, que ya lleva su título)
  function svg(g, region, opc) {
    if (opc && opc.soloGrafico) g = { ...g, _solo: true, notas: [] };
    if (g.tipo === "circular" || g.tipo === "anillo") return circular(g, region);
    return cartesiano(g, region);
  }
  window.DRAE = { svg, PALETA, NAVY, TURQ, NARANJA, AMARILLO, GRIS };
})();
