/* SENAMHI · recolector desde el navegador
 *
 * SENAMHI corta la conexión a los servidores en la nube (Colab, GitHub…), pero responde al navegador.
 * Este script se ejecuta en la consola del navegador, en la página de SENAMHI, y hace las mismas consultas
 * que la página (lista de estaciones, hidrograma diario, Información Diaria e Información Mensual).
 * Al terminar descarga un archivo «SENAMHI_crudo_AAAA-MM-DD.json», que se sube a la página del departamento
 * (Hidrología → Actualizar), donde se arman los CSV y el gráfico. El mismo archivo sirve en el notebook
 * HIDROLOGIA/SENAMHI_Rios.ipynb (Colab) si además se quiere la copia en Drive.
 *
 * Uso (detalle en HIDROLOGIA/senamhi_rios.md):
 *   1. Abre https://www.senamhi.gob.pe/?p=monitoreo-hidrologico
 *   2. F12 → Console → pega la línea de carga (está en el .md) y Enter.
 *   3. En el panel que aparece abajo a la derecha: «Iniciar». Deja la pestaña abierta.
 * Guarda el avance en el navegador (IndexedDB): si se corta o cierras la pestaña, al volver a cargarlo sigue
 * donde quedó. No envía nada a ningún otro sitio.
 */
(() => {
  'use strict';
  if (window.__senamhiRecolector) { window.__senamhiRecolector.mostrar(); return; }

  const VERSION = 6;
  const B = location.origin;
  const U = {
    mapa: B + '/mapas/mapa-monitoreohidro/mapa-monitoreo.php',
    estaciones: B + '/mapas/mapa-monitoreohidro/include/ajaxEstaciones.php',
    idesep: B + '/mapas/mapa-monitoreohidro/include/ajaxIdesep.php',
    grafica: B + '/mapas/mapa-monitoreohidro/include/mnt-grafica-new.php',
    mensual: B + '/include/ajax-informacion-mensual.php',
    infoDiaria: B + '/include/ajax-informacion-diaria.php',
  };
  const GEO = 'https://idesep.senamhi.gob.pe:443/geoserver/g_dbphisis';
  const BBOX_PERU = '-9602936.74,-2128006.87,-7090910.24,73379.55';
  const HORAS = ['00:00', '06:00', '12:00', '18:00'];
  const SERIES = ['datoActual', 'datoAnterior', 'minimo', 'maximo', 'promHistorico', 'rojo', 'naranja', 'amarillo'];
  const PAUSA_MS = 300;
  const PRUEBA_ESTACIONES = ['240001', '240111', '240103'];

  // ── utilidades ────────────────────────────────────────────────────────────
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
  const p2 = (n) => String(n).padStart(2, '0');
  const iso = (d) => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
  function hoyLima() {                       // fecha de Lima (UTC-5), como objeto Date «local»
    const t = new Date(Date.now() - 5 * 3600 * 1000);
    return new Date(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate());
  }
  const anioHidrologico = (d) => (d.getMonth() + 1 >= 9 ? d.getFullYear() : d.getFullYear() - 1);
  const deIso = (t) => { const [a, m, d] = t.split('-').map(Number); return new Date(a, m - 1, d); };

  // ── almacén local (IndexedDB) ─────────────────────────────────────────────
  let db;
  function abrirDb() {
    return new Promise((ok, mal) => {
      const r = indexedDB.open('senamhi_recolector', 1);
      r.onupgradeneeded = () => r.result.createObjectStore('kv');
      r.onsuccess = () => { db = r.result; ok(); };
      r.onerror = () => mal(r.error);
    });
  }
  function tx(modo, fn) {
    return new Promise((ok, mal) => {
      const t = db.transaction('kv', modo);
      const r = fn(t.objectStore('kv'));
      t.oncomplete = () => ok(r && r.result);
      t.onerror = () => mal(t.error);
    });
  }
  const leer = (k) => tx('readonly', (s) => s.get(k));
  const guardar = (k, v) => tx('readwrite', (s) => s.put(v, k));
  const borrarTodo = () => tx('readwrite', (s) => s.clear());
  function todo() {                           // {clave: valor} de todo el almacén
    return new Promise((ok, mal) => {
      const out = {};
      const t = db.transaction('kv', 'readonly');
      const c = t.objectStore('kv').openCursor();
      c.onsuccess = () => { const cur = c.result; if (cur) { out[cur.key] = cur.value; cur.continue(); } };
      t.oncomplete = () => ok(out);
      t.onerror = () => mal(t.error);
    });
  }

  // ── consultas ─────────────────────────────────────────────────────────────
  let pausado = false, detenido = false, consultas = 0, fallos = 0;
  async function pedir(url, cuerpo, intentos = 4) {
    for (let i = 1; i <= intentos; i++) {
      while (pausado && !detenido) await dormir(300);
      if (detenido) throw new Error('detenido');
      const ctl = new AbortController();
      const reloj = setTimeout(() => ctl.abort(), 60000);
      try {
        const r = await fetch(url, {
          method: cuerpo ? 'POST' : 'GET', body: cuerpo || undefined, credentials: 'same-origin',
          headers: { 'X-Requested-With': 'XMLHttpRequest' }, signal: ctl.signal,
        });
        clearTimeout(reloj);
        if (r.ok) { consultas++; const t = await r.text(); await dormir(PAUSA_MS); return t; }
      } catch (e) { clearTimeout(reloj); }
      if (i < intentos) await dormir(1000 * 2 ** i);
    }
    fallos++;
    return null;
  }
  const form = (o) => { const f = new FormData(); for (const k in o) f.append(k, o[k]); return f; };
  const json = (t) => { try { return JSON.parse(t); } catch (e) { return undefined; } };

  /** «var data = {...};» del HTML del hidrograma → objeto, o null. */
  function varData(html) {
    const m = /var\s+data\s*=\s*/.exec(html || '');
    if (!m) return null;
    let i = m.index + m[0].length, nivel = 0, enTexto = false, escape = false;
    const ini = i;
    for (; i < html.length; i++) {
      const c = html[i];
      if (enTexto) { if (escape) escape = false; else if (c === '\\') escape = true; else if (c === '"') enTexto = false; continue; }
      if (c === '"') enTexto = true;
      else if (c === '{' || c === '[') nivel++;
      else if (c === '}' || c === ']') { nivel--; if (nivel === 0) { i++; break; } }
    }
    return json(html.slice(ini, i)) || null;
  }

  /** Hidrograma compacto: primera fecha, días y cada serie como lista de valores (sin repetir las fechas). */
  function compactar(d) {
    const fh = (d.fechaHora || []).map(Number);
    const out = { codEstacion: d.codEstacion, nomEstacion: d.nomEstacion, nomRio: d.nomRio, variable: d.variable,
                  unidad: d.unidad, fechaHora: fh };
    for (const s of SERIES) {
      if (!Array.isArray(d[s])) continue;
      const m = new Map(d[s].map((par) => [Number(par[0]), par[1]]));
      out[s] = fh.map((t) => (m.has(t) ? m.get(t) : null));
    }
    return out;
  }

  async function fichaEstacion(cod, coord) {
    const base = `${GEO}/wms?service=WMS&request=GetFeatureInfo&version=1.1.1&layers=g_dbphisis%3Aestaciones_monitoreo` +
      `&styles=&format=image%2Fpng&transparent=true&cql_filter=id%20IN%20('estaciones_monitoreo.${cod}')` +
      `&info_format=application%2Fjson&query_layers=g_dbphisis%3Aestaciones_monitoreo`;
    const urls = [`${base}&width=1&height=1&srs=EPSG%3A3857&bbox=${BBOX_PERU}&X=0&Y=0`];
    if (coord) {                                 // segundo intento: un recuadro pequeño centrado en la estación
      const [x, y] = coord;
      urls.push(`${base}&width=101&height=101&srs=EPSG%3A4326&bbox=${x - 0.02},${y - 0.02},${x + 0.02},${y + 0.02}&X=50&Y=50`);
    }
    for (const u of urls) {
      const d = json(await pedir(U.idesep, form({ url: u }), 2));
      if (d && d.id) return d;
    }
    return null;
  }

  async function leerWfs() {
    const q = `${GEO}/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=g_dbphisis:estaciones_monitoreo` +
      `&outputFormat=application/json&srsName=EPSG:4326`;
    let d = json(await pedir(U.idesep, form({ url: q }), 1));
    if (!(d && d.features)) {
      try { d = await (await fetch(q.replace(':443', ''))).json(); } catch (e) { d = null; }
    }
    return d && d.features ? d : null;
  }

  // ── recolección ───────────────────────────────────────────────────────────
  let estado = 'listo', detalle = '', hecho = 0, total = 0;
  async function recolectar(cfg) {
    const HOY = hoyLima(), AH_HOY = anioHidrologico(HOY), hoyIso = iso(HOY);
    const DESDE = deIso(cfg.desdeFecha), HASTA = deIso(cfg.hastaFecha) > HOY ? HOY : deIso(cfg.hastaFecha);
    if (DESDE > HASTA) throw new Error('La fecha «Desde» es posterior a «Hasta»');
    const AH_MIN = anioHidrologico(DESDE);
    // la Información Mensual puede empezar antes que lo diario (por ejemplo, mensual desde 2000 y diario desde 2020)
    const M_DESDE = cfg.mensualDesde && deIso(cfg.mensualDesde + '-01') < DESDE ? deIso(cfg.mensualDesde + '-01') : DESDE;
    await guardar('meta', { version: VERSION, desde: DESDE.getFullYear(), desdeFecha: iso(DESDE), hastaFecha: iso(HASTA),
                            mensualDesde: iso(M_DESDE).slice(0, 7), prueba: cfg.prueba, hoy: hoyIso, origen: B, variables: cfg.variables, horas: cfg.horas });

    // 1. estaciones
    estado = 'Estaciones'; pintar();
    let lista = json(await pedir(U.estaciones, form({ cod_zonal: '-1' })));
    if (!Array.isArray(lista) || !lista.length) throw new Error('SENAMHI no respondió la lista de estaciones');
    await guardar('estaciones', lista);
    // la lista que pinta el mapa de SENAMHI: coordenadas, dirección zonal y color de alerta de cada estación
    try {
      const html = await pedir(U.mapa, null, 2), m = /var\s+listaMonitoreo\s*=\s*/.exec(html || '');
      if (m) { const ini = m.index + m[0].length, l = json(html.slice(ini, html.indexOf('];', ini) + 1)); if (Array.isArray(l) && l.length) await guardar('monitoreo', l); }
    } catch (e) { /* sin la lista del mapa se usan las coordenadas guardadas en la página */ }
    // dirección zonal de cada estación (el mismo filtro «Dirección Zonal» del mapa); se pide una sola vez
    let zonales = await leer('zonales');
    if (!zonales) {
      zonales = {};
      for (let z = 1; z <= 13; z++) {
        detalle = `dirección zonal ${z}`; pintar();
        let l = json(await pedir(U.estaciones, form({ cod_zonal: p2(z) }), 2));
        if (!Array.isArray(l) || !l.length) l = json(await pedir(U.estaciones, form({ cod_zonal: String(z) }), 2));
        for (const e of Array.isArray(l) ? l : []) zonales[String(e.codEstacion)] = p2(z);
      }
      // si el filtro no distingue (todas las listas iguales), no sirve: no se guarda
      const n = Object.keys(zonales).length;
      if (n && new Set(Object.values(zonales)).size > 1) await guardar('zonales', zonales); else zonales = null;
    }
    const wfs = (await leer('wfs')) || (await leerWfs());
    if (wfs) await guardar('wfs', wfs);
    const coord = {};
    for (const f of (wfs && wfs.features) || []) {
      const p = f.properties || {}, g = f.geometry || {};
      const cod = String(p.cod_estacion || p.codEstacion || p.id || String(f.id || '').split('.').pop());
      if (g.type === 'Point') coord[cod] = g.coordinates;
    }
    if (cfg.prueba) lista = lista.filter((e) => PRUEBA_ESTACIONES.includes(String(e.codEstacion)));

    // plan aproximado para la barra de avance
    const dias = [];
    if (cfg.infoDiaria) {
      for (let d = new Date(DESDE); d <= HASTA; d.setDate(d.getDate() + 1)) dias.push(new Date(d));
      if (cfg.prueba) dias.splice(2);
    }
    const meses = [];
    if (cfg.mensual) {
      for (let a = M_DESDE.getFullYear(), m = M_DESDE.getMonth() + 1; a < HASTA.getFullYear() || (a === HASTA.getFullYear() && m <= HASTA.getMonth() + 1); m === 12 ? (a++, m = 1) : m++) meses.push([a, m]);
    }
    if (!cfg.hidrograma) lista = [];
    total = lista.length * (1 + cfg.variables.length) + meses.length + dias.length * cfg.horas.length;
    hecho = 0;

    // 2. hidrograma diario por estación (mismo orden y mismas reglas que el notebook)
    estado = 'Hidrograma'; pintar();
    let historiaOk = (await leer('historiaOk')), pruebas = [];
    if (historiaOk === undefined) historiaOk = null;
    for (const e of lista) {
      const cod = String(e.codEstacion);
      detalle = `${e.nomEstacion} (${cod})`;
      let ficha = await leer('ficha:' + cod);
      if (!ficha || ficha.dia !== hoyIso) {
        ficha = { dia: hoyIso, f: await fichaEstacion(cod, coord[cod]) };
        await guardar('ficha:' + cod, ficha);
      }
      hecho++; pintar();
      const fhActual = (ficha.f && ficha.f.fecha_hora) || `${hoyIso} 06:00:00`;
      const opcion = (ficha.f && ficha.f.variable_opcion) || 'N';
      for (const v of cfg.variables) {
        let y = AH_HOY;
        while (true) {
          const actual = y === AH_HOY;
          const fh = actual ? fhActual : `${y + 1}-08-31 06:00:00`;
          const clave = `graf:${cod}:${v}:${actual ? 'actual' : y}`;
          let g = await leer(clave);
          if (g && actual && g.estado === 'OK') y = g.y;
          if (!g || (actual && g.dia !== hoyIso) || g.estado === 'SIN RESPUESTA' || g.estado === 'NO MIDE') {
            const html = await pedir(U.grafica, new URLSearchParams({ rbtVariable: v, fecha_hora: fh, btnTipo: 'D',
                                                                       variable_opcion: opcion, id: cod }));
            const d = varData(html);
            const ini = d && d.fechaHora && d.fechaHora.length ? Number(d.fechaHora[0]) : null;
            let esperado = Date.UTC(y, 8, 1);
            // estación sin datos recientes: la consulta «actual» devuelve su último año hidrológico; se acepta ese año
            if (actual && ini !== null && ini !== esperado && new Date(ini).getUTCMonth() === 8 && new Date(ini).getUTCDate() === 1) {
              esperado = ini; y = new Date(ini).getUTCFullYear();
            }
            const conDatos = d && SERIES.slice(0, 2).some((s) => (d[s] || []).some((par) => par[1] !== null && par[1] > -999));
            const otraVar = d && String(d.variable || v).toUpperCase() !== v;
            const disp = html && /rbtVariableN/.test(html) ? { NIVEL: !/id=["']rbtVariableN["'][^>]*\bdisabled/i.test(html), CAUDAL: !/id=["']rbtVariableC["'][^>]*\bdisabled/i.test(html) } : null;
            // SENAMHI no deja elegir esa variable en su página: lo que devuelve se guarda igual, marcado «no publicado»; la página
            // lo deja aparte (archivo propio) y no lo usa en el mapa, las alertas ni los gráficos
            const noPublicado = !!disp && disp[v] === false;
            g = { dia: hoyIso, cod, variable: v, opcion, y, fh,
                  estado: html === null ? 'SIN RESPUESTA' : (!conDatos || otraVar) ? 'SIN DATOS' : ini === esperado ? 'OK' : 'DEVOLVIO OTRO AÑO',
                  inicio: ini, data: d && ini === esperado && conDatos && !otraVar ? compactar(d) : null, ...(disp ? { disp } : {}), ...(noPublicado ? { noPublicado } : {}) };
            // muestra del formulario (para ver qué variable_opcion usa cada estación), solo en unas pocas
            if (html && (opcion !== 'N' || PRUEBA_ESTACIONES.includes(cod)) && actual) {
              const i0 = html.indexOf('<form'), i1 = html.indexOf('</form>');
              if (i0 >= 0 && i1 > i0) g.formulario = html.slice(i0, i1 + 7).replace(/\s+/g, ' ').slice(0, 4000);
            }
            await guardar(clave, g);
          }
          if (g.estado !== 'OK' && actual) break;                 // la estación no tiene esta variable
          if (actual) y = g.y;
          if (!actual) {
            if (historiaOk === null) {
              pruebas.push(g.estado === 'OK');
              if (pruebas.some(Boolean)) historiaOk = true;
              else if (pruebas.length >= 3) historiaOk = false;
              if (historiaOk !== null) await guardar('historiaOk', historiaOk);
            }
            if (g.estado !== 'OK') break;
          }
          if (y - 1 <= AH_MIN || historiaOk === false) break;
          y -= 2;
        }
        hecho++; pintar();
      }
    }

    // 3. Información Mensual
    estado = 'Información Mensual'; pintar();
    for (const [a, m] of meses) {
      const k = `men:${a}-${p2(m)}`;
      const reciente = (HOY.getFullYear() - a) * 12 + (HOY.getMonth() + 1 - m) <= 2;
      detalle = `${p2(m)}/${a}`;
      if (reciente || !(await leer(k))) {
        const d = json(await pedir(U.mensual, form({ fecha: `${a}-${p2(m)}` })));
        if (d) await guardar(k, d.content || []);
      }
      hecho++; pintar();
    }

    // 4. Información Diaria (lo más largo): por cada consulta se guardan solo las estaciones con dato
    estado = 'Información Diaria'; pintar();
    const metaEst = (await leer('infoMeta')) || {};
    let sinGuardar = 0;
    for (const d of dias) {
      const f = iso(d), reciente = (HOY - d) / 864e5 < 2;
      for (const h of cfg.horas) {
        const k = `inf:${f}:${h}`;
        detalle = `${f} ${h}`;
        if (reciente || !(await leer(k))) {
          const r = json(await pedir(U.infoDiaria, form({ fecha: f, hora: h })));
          if (r && Array.isArray(r.content)) {
            const filas = [];
            for (const x of r.content) {
              const cod = String(x.codEsta);
              if (!metaEst[cod]) {
                metaEst[cod] = { nomEsta: x.nomEsta, cuerpoAgua: x.cuerpoAgua, nomCuenca: x.nomCuenca, nomDepa: x.nomDepa,
                                 nomSector: x.nomSector, uniHidrografica: x.uniHidrografica, codZonal: x.codZonal,
                                 uniAnomalia: x.uniAnomalia };
                sinGuardar++;
              }
              if (x.dato !== null && x.dato !== undefined && Number(x.dato) > -999) {
                filas.push([cod, x.dato, x.datAnomalia, x.tendencia, x.umbralRojo, x.unidad, x.uniAnomalia]);
              }
            }
            await guardar(k, [r.content.length, filas]);
            if (sinGuardar) { await guardar('infoMeta', metaEst); sinGuardar = 0; }
          }
        }
        hecho++; if (hecho % 5 === 0) pintar();
      }
    }
    estado = 'Terminado'; detalle = ''; pintar();
  }

  // ── archivo de salida ─────────────────────────────────────────────────────
  async function exportar() {
    const t = await todo();
    const out = { version: VERSION, generado: new Date().toISOString(), meta: t.meta || {}, estaciones: t.estaciones || [],
                  wfs: t.wfs || null, zonales: t.zonales || null, monitoreo: t.monitoreo || null, historiaOk: t.historiaOk === undefined ? null : t.historiaOk,
                  fichas: {}, graficas: [], mensual: {}, infoMeta: t.infoMeta || {}, infoDiaria: {} };
    for (const k in t) {
      if (k.startsWith('ficha:')) out.fichas[k.slice(6)] = t[k].f;
      else if (k.startsWith('graf:')) out.graficas.push(t[k]);
      else if (k.startsWith('men:')) out.mensual[k.slice(4)] = t[k];
      else if (k.startsWith('inf:')) out.infoDiaria[k.slice(4, 14) + ' ' + k.slice(15)] = t[k];
    }
    const blob = new Blob([JSON.stringify(out)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `SENAMHI_crudo_${(t.meta && t.meta.hoy) || iso(hoyLima())}${t.meta && t.meta.prueba ? '_prueba' : ''}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
    return { nombre: a.download, mb: (blob.size / 1048576).toFixed(1), out };
  }

  // ── panel ─────────────────────────────────────────────────────────────────
  const caja = document.createElement('div');
  caja.id = 'senamhi-recolector';
  caja.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;width:340px;background:#fff;color:#1a1a1a;' +
    'border:2px solid #0b3c8c;border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.3);font:13px/1.4 Arial,sans-serif;padding:12px';
  caja.innerHTML =
    '<div style="font-weight:bold;color:#0b3c8c;margin-bottom:6px">SENAMHI · recolector de niveles y caudales</div>' +
    '<div id="sr-opciones">' +
    '<label>Desde <input id="sr-desde" type="date" value="2023-01-01"></label> ' +
    '<label>hasta <input id="sr-hasta" type="date"></label><br>' +
    '<div style="color:#555;font-size:11px;margin:2px 0 4px">Lo ya descargado no se vuelve a pedir. Para actualizar, basta poner «Desde» unos días atrás.</div>' +
    '<label><input id="sr-prueba" type="checkbox"> Prueba rápida (3 estaciones y 2 días, ~1 min)</label><br>' +
    '<label><input id="sr-hidro" type="checkbox" checked> Hidrograma diario (todas las estaciones)</label><br>' +
    '<label><input id="sr-caudal" type="checkbox" checked> Caudal, además del nivel</label><br>' +
    '<label><input id="sr-diaria" type="checkbox" checked> Información Diaria (4 horas por día; es lo más largo)</label><br>' +
    '<label><input id="sr-mensual" type="checkbox" checked> Información Mensual</label> <label style="font-size:11px">desde <input id="sr-mdesde" type="month" title="Vacío = desde la misma fecha que lo diario"></label></div>' +
    '<div id="sr-estado" style="margin:8px 0 4px">Listo. Deja esta pestaña abierta mientras trabaja.</div>' +
    '<div style="background:#e3e8f0;border-radius:4px;height:10px;overflow:hidden"><div id="sr-barra" style="background:#0b3c8c;height:10px;width:0"></div></div>' +
    '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' +
    '<button id="sr-iniciar">Iniciar</button><button id="sr-pausa" disabled>Pausar</button>' +
    '<button id="sr-bajar">Descargar archivo</button><button id="sr-borrar" title="Borra lo guardado en este navegador">Empezar de cero</button>' +
    '<button id="sr-cerrar">Ocultar</button></div>';
  document.body.appendChild(caja);
  const $ = (id) => caja.querySelector('#' + id);
  let t0 = 0;
  function pintar() {
    const pct = total ? Math.min(100, (100 * hecho) / total) : 0;
    $('sr-barra').style.width = pct.toFixed(1) + '%';
    let resta = '';
    if (t0 && hecho > 20 && hecho < total) {
      const min = ((Date.now() - t0) / hecho) * (total - hecho) / 60000;
      resta = ` · faltan ~${min < 1 ? '1' : min.toFixed(0)} min`;
    }
    $('sr-estado').textContent = `${estado}${detalle ? ' · ' + detalle : ''} · ${pct.toFixed(0)}%${resta}` +
      (fallos ? ` · ${fallos} sin respuesta` : '') + (pausado ? ' · EN PAUSA' : '');
  }
  let corriendo = false;
  $('sr-iniciar').onclick = async () => {
    if (corriendo) return;
    corriendo = true; detenido = false; pausado = false; fallos = 0; t0 = Date.now();
    $('sr-iniciar').disabled = true; $('sr-pausa').disabled = false;
    const cfg = { desdeFecha: $('sr-desde').value || '2023-01-01', hastaFecha: $('sr-hasta').value || iso(hoyLima()),
                  prueba: $('sr-prueba').checked, hidrograma: $('sr-hidro').checked,
                  variables: $('sr-caudal').checked ? ['NIVEL', 'CAUDAL'] : ['NIVEL'],
                  infoDiaria: $('sr-diaria').checked, mensual: $('sr-mensual').checked, mensualDesde: $('sr-mdesde').value || '', horas: HORAS };
    try {
      await recolectar(cfg);
      const r = await exportar();
      $('sr-estado').textContent = `✅ Terminado. Se descargó ${r.nombre} (${r.mb} MB)` +
        (fallos ? ` · ${fallos} consultas sin respuesta: pulsa «Iniciar» otra vez para reintentarlas.` : '. Súbelo en la página: Hidrología → Actualizar.');
    } catch (e) {
      $('sr-estado').textContent = '⚠️ ' + (e && e.message ? e.message : e) + '. Lo ya descargado quedó guardado: pulsa «Iniciar» para seguir.';
    }
    corriendo = false; $('sr-iniciar').disabled = false; $('sr-pausa').disabled = true;
  };
  $('sr-pausa').onclick = () => { pausado = !pausado; $('sr-pausa').textContent = pausado ? 'Continuar' : 'Pausar'; pintar(); };
  $('sr-bajar').onclick = async () => { const r = await exportar(); $('sr-estado').textContent = `Se descargó ${r.nombre} (${r.mb} MB) con lo reunido hasta ahora.`; };
  $('sr-borrar').onclick = async () => {
    if (corriendo) { $('sr-estado').textContent = 'Primero espera a que termine o pulsa «Pausar».'; return; }
    if (confirm('¿Borrar todo lo que este navegador ya descargó de SENAMHI y empezar de cero?')) { await borrarTodo(); $('sr-estado').textContent = 'Borrado. Pulsa «Iniciar».'; }
  };
  $('sr-cerrar').onclick = () => { caja.style.display = 'none'; };
  window.addEventListener('beforeunload', (e) => { if (corriendo) { e.preventDefault(); e.returnValue = ''; } });

  window.__senamhiRecolector = { mostrar: () => { caja.style.display = 'block'; }, exportar, varData, compactar,
                                 detener: () => { detenido = true; } };
  abrirDb().then(async () => {
    const m = await leer('meta');
    $('sr-hasta').value = iso(hoyLima());
    if (m) {
      if (m.desdeFecha) $('sr-desde').value = m.desdeFecha;
      if (m.mensualDesde && m.mensualDesde < (m.desdeFecha || '').slice(0, 7)) $('sr-mdesde').value = m.mensualDesde;
      $('sr-estado').textContent = `Hay un avance guardado (desde ${m.desdeFecha || m.desde}${m.prueba ? ', prueba' : ''}). «Iniciar» sigue donde quedó.`;
    }
  }).catch((e) => { $('sr-estado').textContent = '⚠️ No se pudo abrir el almacén del navegador: ' + e; });
})();
