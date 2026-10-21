// Genera los diccionarios de datos (Word, APA 7, Arial 12, justificado, letra negra) de los archivos de DATA.
// Uso: node mk_diccionarios_docx.js   → escribe los .docx en esta misma carpeta.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, AlignmentType, BorderStyle,
  WidthType, PageNumber, LevelFormat,
} = require("docx");

const VERSION = "20 de octubre de 2026";
const FUENTE = "Arial", T = 24, NEGRO = "000000";           // 12 pt
const ANCHO = 9026;
const B = { font: FUENTE, size: T, color: NEGRO };            // se fija en cada texto (LibreOffice ignora el estilo por defecto en tablas)                                         // A4 con márgenes de 2,54 cm

// ── Bloques de texto ─────────────────────────────────────────────────────────
// Texto con *cursiva* y **negrita** sencillas.
function runs(txt, extra = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let i = 0, m;
  while ((m = re.exec(txt))) {
    if (m.index > i) out.push(new TextRun({ ...B, text: txt.slice(i, m.index), ...extra }));
    const b = m[0].startsWith("**");
    out.push(new TextRun({ ...B, text: m[0].replace(/\*/g, ""), bold: b || extra.bold, italics: !b || extra.italics }));
    i = m.index + m[0].length;
  }
  if (i < txt.length) out.push(new TextRun({ ...B, text: txt.slice(i), ...extra }));
  return out;
}
const par = (txt, o = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { line: 480, before: 0, after: 0 },
  indent: o.sinSangria ? undefined : { firstLine: 720 }, children: runs(txt),
});
const titulo = (txt) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { line: 480 }, children: [new TextRun({ ...B, text: txt, bold: true })],
});
const centrado = (txt) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: 480 }, children: runs(txt) });
const n1 = (txt) => new Paragraph({                       // APA nivel 1: centrado, negrita
  alignment: AlignmentType.CENTER, spacing: { line: 480 }, keepNext: true, children: [new TextRun({ ...B, text: txt, bold: true })],
});
const n2 = (txt) => new Paragraph({                       // APA nivel 2: a la izquierda, negrita
  alignment: AlignmentType.LEFT, spacing: { line: 480 }, keepNext: true, children: [new TextRun({ ...B, text: txt, bold: true })],
});
const vineta = (txt) => new Paragraph({
  numbering: { reference: "vinetas", level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { line: 480 }, children: runs(txt),
});
const referencia = (txt) => new Paragraph({               // sangría francesa de 0,5 pulgadas
  alignment: AlignmentType.JUSTIFIED, spacing: { line: 480 }, indent: { left: 720, hanging: 720 }, children: runs(txt),
});

// ── Tablas APA: solo líneas horizontales (arriba, bajo el encabezado y al final) ──
const SIN = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const LIN = { style: BorderStyle.SINGLE, size: 6, color: NEGRO };
function tablaAPA(num, tituloTabla, cab, filas, anchos, nota) {
  const celda = (txt, w, { cabecera = false, primera = false, ultima = false, just = false } = {}) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    borders: { top: cabecera || primera ? LIN : SIN, bottom: cabecera || ultima ? LIN : SIN, left: SIN, right: SIN },
    children: [new Paragraph({
      alignment: cabecera ? AlignmentType.CENTER : (just ? AlignmentType.JUSTIFIED : AlignmentType.LEFT),
      spacing: { line: 240 }, children: cabecera ? [new TextRun({ ...B, text: txt, bold: true })] : runs(txt),
    })],
  });
  const filasT = [new TableRow({ tableHeader: true, cantSplit: true,
    children: cab.map((c, j) => celda(c, anchos[j], { cabecera: true })) })];
  filas.forEach((f, i) => filasT.push(new TableRow({ cantSplit: true,
    children: f.map((c, j) => celda(c, anchos[j], { ultima: i === filas.length - 1, just: j === f.length - 1 })) })));
  const out = [
    new Paragraph({ spacing: { line: 480, before: 240 }, keepNext: true, children: [new TextRun({ ...B, text: `Tabla ${num}`, bold: true })] }),
    new Paragraph({ spacing: { line: 480 }, keepNext: true, children: [new TextRun({ ...B, text: tituloTabla, italics: true })] }),
    new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos, rows: filasT }),
  ];
  if (nota) out.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 480, after: 240 },
    children: [new TextRun({ ...B, text: "Nota.", italics: true }), new TextRun({ ...B, text: " " }), ...runs(nota)] }));
  else out.push(new Paragraph({ spacing: { line: 240 }, children: [] }));
  return out;
}
const tablaVariables = (num, archivo, filas, nota) =>
  tablaAPA(num, `Variables del archivo ${archivo}`, ["Variable", "Tipo y unidad", "Descripción"], filas, [3000, 1900, 4126], nota);

function documento(hijos) {
  return new Document({
    creator: "Proyecto Petróleo (scraper-mef)",
    styles: { default: { document: { run: { font: FUENTE, size: T, color: NEGRO } } } },
    numbering: { config: [{ reference: "vinetas", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }] },
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ ...B, children: [PageNumber.CURRENT] })] })] }) },
      children: hijos,
    }],
  });
}

// ── Referencias (APA 7) ──────────────────────────────────────────────────────
const URL_PP = "https://www.perupetro.com.pe";
const REF = {
  canonMun: `PERUPETRO S.A. (s. f.-a). *Canon municipalidades* [Archivos Excel «Canon por Año» por departamento]. Recuperado el 20 de octubre de 2026, de ${URL_PP}`,
  canon: `PERUPETRO S.A. (s. f.-b). *Canon y sobre canon* [Archivos Excel de determinación y de distribución del canon]. Recuperado el 20 de octubre de 2026, de ${URL_PP}`,
  estad: `PERUPETRO S.A. (s. f.-c). *Estadística petrolera* [Estadísticas anuales y mensuales de hidrocarburos en PDF]. Recuperado el 20 de octubre de 2026, de ${URL_PP}`,
  geo: "PERUPETRO S.A. (s. f.-d). *Geoportal de PERUPETRO* [Servicio WFS de lotes de contrato y cuencas sedimentarias]. Recuperado el 20 de octubre de 2026, de https://geoportal.perupetro.com.pe",
  diaria: `PERUPETRO S.A. (s. f.-e). *Producción diaria* [Reportes diarios de producción fiscalizada en PDF]. Recuperado el 20 de octubre de 2026, de ${URL_PP}`,
  mef: "Ministerio de Economía y Finanzas. (s. f.). *Consulta Amigable de Ingresos (mensual)* [Base de datos]. Recuperado el 20 de octubre de 2026, de https://apps5.mineco.gob.pe/transparenciaingresos/mensual/",
  lehner: "Lehner, B., & Grill, G. (2013). Global river hydrography and network routing: Baseline data and new approaches to study the world’s large river systems. *Hydrological Processes, 27*(15), 2171–2186. https://doi.org/10.1002/hyp.9740",
  runfola: "Runfola, D., Anderson, A., Baier, H., Crittenden, M., Dowker, E., Fuhrig, S., Goodman, S., Grimsley, G., Layko, R., Melville, G., Mulder, M., Oberman, R., Panganiban, J., Peck, A., Seitz, L., Shea, S., Slevin, H., Youngerman, R., & Hobbs, L. (2020). geoBoundaries: A global database of political administrative boundaries. *PLoS ONE, 15*(4), Artículo e0231866. https://doi.org/10.1371/journal.pone.0231866",
};
const ORDEN_REF = ["lehner", "mef", "canonMun", "canon", "estad", "geo", "diaria", "runfola"];
function referencias(claves) {
  return [n1("Referencias"), ...ORDEN_REF.filter((k) => claves.includes(k)).map((k) => referencia(REF[k]))];
}

// ── Variables comunes ────────────────────────────────────────────────────────
const V = {
  AÑO: ["AÑO", "Entero", "Año calendario del dato."],
  MES: ["MES", "Entero (1–12)", "Mes calendario (1 = enero, 12 = diciembre)."],
  FECHA: ["FECHA", "Texto, fecha dd/mm/aaaa", "Primer día del mes al que corresponde el dato (01/03/2015 = marzo de 2015). Sirve para ordenar y graficar series."],
  ZONA: ["ZONA", "Texto (código)", "Zona geográfica de PERUPETRO: NOROESTE, ZOCALO (zócalo continental, en el mar), SELVA NORTE, SELVA CENTRAL o SELVA SUR. Se toma del encabezado de la tabla del PDF o, si no lo trae, de una tabla fija por lote."],
  DEPARTAMENTO: ["DEPARTAMENTO", "Texto", "Departamento donde se ubica el lote: el que tiene la mayor parte de su área según el mapa de lotes (PP_LOTES_GEO.csv). Si el lote no tiene polígono, se asigna por la zona (SELVA NORTE → LORETO) o queda vacío."],
  DEPARTAMENTO_FUENTE: ["DEPARTAMENTO_FUENTE", "Texto (código)", "Cómo se asignó el departamento: MAPA (polígono del lote), ZONA (por la zona de PERUPETRO) o vacío."],
  OPERADOR: ["OPERADOR", "Texto", "Empresa que opera el lote según el PDF de ese año, con el nombre homologado (se corrigen nombres cortados y erratas, p. ej., PLUSPETRO → PLUSPETROL). Es el operador de ese período, no necesariamente el actual."],
  OPERADOR_ORIGINAL: ["OPERADOR_ORIGINAL", "Texto", "Nombre del operador tal como aparece en el PDF; permite auditar la homologación."],
  LOTE: ["LOTE", "Texto (código)", "Código homologado del contrato, sin la palabra «Lote» y con guion estándar (p. ej., 192, 1-AB, 8, 95, Z-2B, 31-B/D, X). Los contratos temporales conservan el sufijo (T)."],
  LOTE_HISTORICO: ["LOTE_HISTORICO", "Texto (código)", "Agrupa los contratos que corresponden al mismo campo a lo largo del tiempo (p. ej., 1-AB y 192 → 1-AB/192). No lleva el sufijo (T). Se usa para series largas y rankings."],
  LOTE_ORIGINAL: ["LOTE_ORIGINAL", "Texto", "Lote tal como aparece escrito en el PDF (p. ej., «31-C ( LGN )», «Z - 2B»); permite auditar."],
  FECHA_EXTRACCION: ["FECHA_EXTRACCION", "Texto, fecha dd/mm/aaaa", "Día en que se corrió el notebook que generó el archivo."],
};
const fuentePdfAnual = ["FUENTE", "Texto", "PDF de origen: PP_ANUAL_<edición>.pdf usado para ese año."];

// ── Archivos ─────────────────────────────────────────────────────────────────
// util: ÚTIL, CONTROL o REDUNDANTE (para el diccionario general)
const ARCHIVOS = [
  {
    archivo: "PP_produccion_lote_mes_1994-2026.csv", tema: "Producción", util: "Útil (base principal)",
    para: "Producción fiscalizada mensual de petróleo, LGN y condensado por lote; base de las series, rankings, mapa e indicadores.",
    proposito: [
      "Este archivo es la base principal del Proyecto Petróleo. Contiene la producción fiscalizada mensual de hidrocarburos líquidos (petróleo crudo, líquidos de gas natural [LGN] y condensado) de cada lote del país, desde enero de 1994 hasta el último mes publicado por PERUPETRO S.A. (s. f.-c). *Fiscalizada* significa medida en el punto de fiscalización del contrato: es el volumen sobre el que se calculan las regalías.",
      "Sirve para construir series de producción por lote, campo, departamento u operador, comparar años y meses, elaborar rankings y calcular participaciones. Además, es el insumo del mapa de lotes (indicadores, estado de producción, historial de operadores) y del valor de la producción (PP_valor_produccion_lote_mes.csv).",
    ],
    origen: "Lo genera el notebook PP_Produccion_Lotes.ipynb a partir de las estadísticas anuales (1994–2025) y de la estadística mensual más reciente del año en curso. Los años 1994–2000 provienen de PDF escaneados, transcritos a mano y validados contra los totales impresos; desde 2001 se extraen automáticamente del PDF digital. El nombre del archivo indica el período de la corrida (<inicio>-<fin>).",
    clave: "Un lote, un producto y un mes. Clave única: AÑO + MES + LOTE + PRODUCTO.",
    vars: [V.AÑO, V.MES, V.FECHA, V.ZONA, V.DEPARTAMENTO, V.DEPARTAMENTO_FUENTE, V.OPERADOR, V.OPERADOR_ORIGINAL, V.LOTE, V.LOTE_HISTORICO, V.LOTE_ORIGINAL,
      ["PRODUCTO", "Texto (código)", "PETROLEO (crudo), LGN (líquidos de gas natural: propano, butano y gasolina natural) o CONDENSADO. No conviene sumarlos sin criterio: son mercados distintos."],
      ["BARRILES", "Decimal, barriles (bbl)", "Producción fiscalizada del mes. Un barril equivale a 42 galones (158,987 litros)."],
      ["BPD", "Decimal, barriles por día", "BARRILES ÷ días del mes, con un decimal. Permite comparar meses de distinta duración."],
      ["ESTADO_FILA", "Texto (código)", "Calidad del registro: OK (cuadra con el total del lote); IMPUTADO <MES> (ese único mes estaba en blanco en el PDF y se calculó como total anual menos los demás meses); REVISAR (no cuadra); TRANSCRITO (1994–2000)."],
      ["FUENTE", "Texto", "Archivo de origen: PP_ANUAL_<año>.pdf, PP_MENSUAL_<año>_<mes>.pdf o «TRANSCRIPCION PP_ANUAL_<año>.pdf p.N»."]],
    nota: "Si existe la estadística anual de un año, se usa la anual; para el año en curso se usa la mensual más reciente, que trae el acumulado del año.",
    refs: ["estad"],
  },
  {
    archivo: "PP_produccion_gas_lote_mes_1994-2026.csv", tema: "Producción", util: "Útil",
    para: "Producción fiscalizada mensual de gas natural por lote (MPC), 1994–hoy.",
    proposito: [
      "Contiene la producción fiscalizada mensual de gas natural de cada lote, en miles de pies cúbicos (MPC), desde enero de 1994. Proviene de la tabla «Producción fiscalizada mensual de gas natural (MPC)» de las estadísticas de PERUPETRO S.A. (s. f.-c).",
      "Sirve para analizar la producción de gas por lote y departamento (p. ej., Lote 31-C en Ucayali), para el gas acumulado de cada campo del mapa y para el historial de operadores.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, de los mismos PDF que la producción de líquidos. Los años 1994–2000 se transcribieron a mano desde los escaneos y cuadran con los totales del PDF; desde 2001 se extraen del PDF digital.",
    clave: "Un lote y un mes. Clave única: AÑO + MES + LOTE.",
    vars: [V.AÑO, V.MES, V.FECHA, V.ZONA, V.DEPARTAMENTO, V.DEPARTAMENTO_FUENTE, V.OPERADOR, V.OPERADOR_ORIGINAL, V.LOTE, V.LOTE_HISTORICO, V.LOTE_ORIGINAL,
      ["PRODUCTO", "Texto", "Siempre GAS NATURAL."],
      ["MPC", "Decimal, miles de pies cúbicos", "Gas natural fiscalizado del mes."],
      ["MMPCD", "Decimal, millones de pies cúbicos por día", "MPC ÷ días del mes ÷ 1 000, con tres decimales."],
      ["ESTADO_FILA", "Texto (código)", "OK, REVISAR o TRANSCRITO (1994–2000). Como el PDF redondea cada celda, se acepta hasta 6 MPC de diferencia entre la suma de los meses y el total del lote."],
      ["FUENTE", "Texto", "PDF de origen."]],
    nota: "Se descartan la versión en MMBTU, la producción «de campo» y los balances de gas del PDF.",
    refs: ["estad"],
  },
  {
    archivo: "PP_produccion_diaria.csv", tema: "Producción", util: "Útil",
    para: "Producción fiscalizada diaria por lote (líquidos y gas); cubre los meses aún no publicados en la estadística mensual.",
    proposito: [
      "Contiene la producción fiscalizada diaria de cada lote, de líquidos (barriles) y de gas natural (miles de pies cúbicos y millones de BTU), tomada de los reportes de la página «Producción Diaria» de PERUPETRO S.A. (s. f.-e).",
      "Sirve para seguir la producción reciente, antes de que salga la estadística mensual. El mapa la usa para completar los meses posteriores a la última estadística mensual al calcular el estado de producción de cada campo (PP_LOTES_ESTADO_PRODUCTO.csv).",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, sección «Producción diaria». El archivo se acumula: cada corrida reemplaza los meses que vuelve a leer.",
    clave: "Un día, una unidad, un producto, un lote y un operador. Clave única: FECHA + UNIDAD + PRODUCTO + LOTE + OPERADOR.",
    vars: [
      ["FECHA", "Texto, fecha dd/mm/aaaa", "Día de la producción."],
      ["AÑO", "Entero", "Año de FECHA."], ["MES", "Entero (1–12)", "Mes de FECHA."], ["DIA", "Entero (1–31)", "Día de FECHA."],
      ["FLUIDO", "Texto (código)", "LIQUIDOS o GAS NATURAL."],
      ["PRODUCTO", "Texto (código)", "PETROLEO Y CONDENSADO, LGN o GAS NATURAL."],
      ["UNIDAD", "Texto (código)", "BBL (barriles), MCF (miles de pies cúbicos), MMBTU (millones de BTU, contenido energético del gas) o M3 (metros cúbicos)."],
      ["OPERADOR", "Texto", "Empresa como figura en el encabezado del reporte diario."],
      ["LOTE_ORIGINAL", "Texto", "Lote como figura en el reporte."],
      ["LOTE", "Texto (código)", "Lote homologado (p. ej., X. → X; 192_LIC → 192)."],
      ["VALOR", "Decimal, según UNIDAD", "Producción fiscalizada del día. Algunos lotes de líquidos se fiscalizan por entregas, por lo que hay días en 0 y días con valores altos: para promedios conviene usar el mes."],
      ["FUENTE", "Texto", "PDF guardado en DATA/PDF_DIARIA."],
      ["DEPARTAMENTO", "Texto", "Departamento del lote según el mapa."]],
    refs: ["diaria"],
  },
  {
    archivo: "PP_pozos_perforados_lote_anio.csv", tema: "Actividad", util: "Útil",
    para: "Pozos perforados por lote, año y tipo (exploratorio, confirmatorio, desarrollo), 1995–hoy.",
    proposito: [
      "Registra el número de pozos perforados cada año en cada lote, según su tipo, de las tablas «Pozos exploratorios / confirmatorios / de desarrollo perforados por contrato» de las estadísticas anuales de PERUPETRO S.A. (s. f.-c).",
      "Es el indicador de actividad e inversión disponible por lote, ya que la estadística anual no publica la inversión en dólares por lote.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb. Cada anual trae 10 u 11 años; para cada año se usa la edición más reciente, porque PERUPETRO corrige algunas cifras.",
    clave: "Un año, un tipo de pozo, un lote y un operador. Clave: AÑO + TIPO + LOTE + OPERADOR.",
    vars: [
      ["AÑO", "Entero", "Año de perforación (1995–hoy)."],
      ["TIPO", "Texto (código)", "EXPLORATORIO (busca un yacimiento nuevo), CONFIRMATORIO (delimita un descubrimiento) o DESARROLLO (produce un yacimiento conocido). Hasta 2001 los confirmatorios van dentro de EXPLORATORIO; desde 2013 no se cuentan los pozos inyectores."],
      V.DEPARTAMENTO, V.OPERADOR, V.OPERADOR_ORIGINAL, V.LOTE, V.LOTE_HISTORICO,
      ["POZOS", "Entero, número de pozos", "Pozos perforados en el año."],
      fuentePdfAnual],
    nota: "Cuando un lote cambió de operador en el período, la tabla trae una fila por operador.",
    refs: ["estad"],
  },
  {
    archivo: "PP_regalias_lote_anio.csv", tema: "Fiscal", util: "Útil",
    para: "Regalías (ingresos al fisco) por lote, hidrocarburo y año, en US$, 2001–hoy.",
    proposito: [
      "Contiene las regalías pagadas al Estado por cada lote e hidrocarburo, en dólares, de las tablas «Ingresos al fisco» o «Ingreso por regalías por contrato» (2007–hoy) e «Ingresos por contratos» (2001–2006, en miles de US$, convertidos a US$) de PERUPETRO S.A. (s. f.-c).",
      "Sirve para medir el aporte fiscal directo de cada lote y empresa, y alimenta el historial de operadores del mapa (PP_operadores_lote.csv).",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, de las estadísticas anuales.",
    clave: "Un año, una modalidad, un hidrocarburo y un lote del PDF. Clave: AÑO + MODALIDAD + HIDROCARBURO + LOTE_PDF.",
    vars: [
      ["AÑO", "Entero", "Año de las regalías."],
      ["MODALIDAD", "Texto (código)", "LICENCIA (regalía) o SERVICIOS (regalía equivalente: retribución al contratista)."],
      ["HIDROCARBURO", "Texto (código)", "PETRÓLEO, LGN, GAS NATURAL o CONDENSADO."],
      V.DEPARTAMENTO, ["LOTE", "Texto (código)", "Lote homologado, sin los sufijos (T) o (TT)."], V.LOTE_HISTORICO,
      ["LOTE_PDF", "Texto", "Lote como figura en el PDF; distingue contratos del mismo lote (p. ej., I (TT) e I.)."],
      ["OPERADOR", "Texto", "Empresa que pagó, tomada de la tabla de producción del mismo anual. «VARIOS OPERADORES» si el PDF no distingue los contratos (Lote 8 en 2024)."],
      ["REGALIA_PCT", "Decimal, porcentaje", "Porcentaje de regalía; solo lo trae la edición 2007."],
      ["REGALIA_US$", "Decimal, dólares (US$)", "Monto de regalías del año."],
      fuentePdfAnual],
    refs: ["estad"],
  },
  {
    archivo: "PP_precio_canasta_lote_mes.csv", tema: "Precios", util: "Útil",
    para: "Precio de canasta de los líquidos por lote y mes (US$/bbl), 2001–hoy.",
    proposito: [
      "Contiene el precio de canasta mensual de los hidrocarburos líquidos de cada lote, en dólares por barril, de la tabla «Valor mensual del precio de canasta de hidrocarburos líquidos» de PERUPETRO S.A. (s. f.-c). Es el precio con el que se calculan las regalías.",
      "Sirve para analizar precios por lote y para valorizar la producción (PP_valor_produccion_lote_mes.csv).",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, de las estadísticas anuales. Cuando el PDF agrupa lotes («VII y V», «31B-31D / 31C») se repite el precio para cada uno; en 2001 el PDF da un solo precio para la zona NOROESTE.",
    clave: "Un año, un mes, un lote y una variante. Clave: AÑO + MES + LOTE + VARIANTE.",
    vars: [V.AÑO, V.MES, V.FECHA,
      ["LOTE", "Texto (código)", "Lote homologado (o NOROESTE en 2001)."],
      ["VARIANTE", "Texto (código)", "Vacío si el lote tiene un solo precio; P = petróleo y L = líquidos del lote Z-69; LGN = líquidos del lote Z-2B."],
      ["LOTE_PDF", "Texto", "Etiqueta tal como figura en el PDF."],
      ["PRECIO_US$_BBL", "Decimal, US$ por barril", "Precio de canasta del mes."],
      ["ESTADO", "Texto (código)", "OK (leído del PDF) o «IMPUTADO (12 × promedio − otros meses)» cuando un solo mes era ilegible y se completó con el promedio anual impreso."],
      fuentePdfAnual],
    refs: ["estad"],
  },
  {
    archivo: "PP_valor_produccion_lote_mes.csv", tema: "Producción", util: "Útil",
    para: "Valor de la producción de líquidos por lote y mes = barriles × precio de canasta (US$).",
    proposito: [
      "Calcula el valor de la producción fiscalizada de líquidos de cada lote y mes, multiplicando los barriles (PP_produccion_lote_mes) por el precio de canasta del lote (PP_precio_canasta_lote_mes).",
      "Sirve para dimensionar en dólares la producción de cada lote o departamento. Es un valor a precio de canasta, no el ingreso de la empresa.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb. Para el petróleo se usa la variante P y para el LGN o condensado la variante LGN o L, si existen; si no, el precio del lote.",
    clave: "Un lote, un producto y un mes. Clave: AÑO + MES + LOTE + PRODUCTO.",
    vars: [V.AÑO, V.MES, V.FECHA, V.DEPARTAMENTO, V.OPERADOR, V.LOTE, V.LOTE_HISTORICO,
      ["PRODUCTO", "Texto (código)", "PETROLEO, LGN o CONDENSADO."],
      ["BARRILES", "Decimal, barriles", "Producción fiscalizada del mes (de PP_produccion_lote_mes)."],
      ["PRECIO_US$_BBL", "Decimal, US$ por barril", "Precio de canasta aplicado."],
      ["VALOR_US$", "Decimal, dólares (US$)", "BARRILES × PRECIO_US$_BBL, con dos decimales."],
      ["ESTADO_PRECIO", "Texto (código)", "OK, SIN PRECIO (hay producción pero no precio en el PDF) o SIN PRODUCCION."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_contratos.csv", tema: "Empresas", util: "Útil",
    para: "Contratos vigentes, terminados y suscritos por edición: empresas socias, participación, fechas y área, 2004–hoy.",
    proposito: [
      "Reúne los cuadros «Contratos en fase de explotación / exploración» (vigentes al 31 de diciembre), «Contratos terminados» y, en 2007, «Contratos suscritos durante el año» de cada estadística anual de PERUPETRO S.A. (s. f.-c), con una fila por empresa socia.",
      "Sirve para saber qué empresas participan en cada contrato y con qué porcentaje, cuándo se firmó y cuándo vence, su modalidad y su área.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb. Se acumula en Drive por edición (2004–hoy; la edición 2001 no se lee).",
    clave: "Una edición, un estado, un lote y una empresa. Clave: EDICION + ESTADO + LOTE + EMPRESA.",
    vars: [
      ["EDICION", "Entero", "Año de la estadística anual (contratos al 31 de diciembre de ese año)."],
      ["ESTADO", "Texto (código)", "VIGENTE, TERMINADO (en el año) o SUSCRITO EN EL AÑO."],
      ["FASE", "Texto (código)", "EXPLOTACION o EXPLORACION."],
      V.DEPARTAMENTO, V.LOTE, V.LOTE_HISTORICO,
      ["OPERADOR", "Texto", "Primera empresa listada en el contrato."],
      ["EMPRESA", "Texto", "Empresa socia, como figura en el PDF."],
      ["PARTICIPACION_PCT", "Decimal, porcentaje", "Participación de la empresa en el contrato; vacío en ediciones antiguas que no la traen."],
      ["FECHA_SUSCRIPCION", "Texto, fecha dd/mm/aaaa", "Fecha de suscripción del contrato."],
      ["FECHA_TERMINO", "Texto, fecha dd/mm/aaaa", "Término o último día de vigencia; aparece desde la edición 2014."],
      ["AREA_HA", "Decimal, hectáreas", "Área del contrato."],
      ["MODALIDAD", "Texto (código)", "LICENCIA, SERVICIOS u OPERACIONES."],
      ["PAGINA", "Entero", "Página del PDF."],
      ["FUENTE", "Texto", "PDF de origen: PP_ANUAL_<edición>.pdf."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_ingresos_estado_mes.csv", tema: "Fiscal", util: "Útil",
    para: "Ingresos para el Estado por mes y modalidad de contrato (MM US$), total nacional.",
    proposito: [
      "Registra los ingresos mensuales para el Estado (regalías más regalía equivalente) del total nacional, por modalidad de contrato, tomados del «Resumen ejecutivo» de cada estadística mensual de PERUPETRO S.A. (s. f.-c).",
      "Sirve para seguir mes a mes el aporte fiscal del sector a nivel nacional.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb. PERUPETRO solo publica las estadísticas mensuales del año en curso, por lo que la serie se acumula en Drive en cada corrida.",
    clave: "Un mes y una modalidad. Clave: AÑO + MES + MODALIDAD.",
    vars: [V.AÑO, V.MES, V.FECHA,
      ["MODALIDAD", "Texto (código)", "LICENCIA, SERVICIOS o TOTAL."],
      ["INGRESO_MM_US$", "Decimal, millones de US$", "Ingresos para el Estado del mes."],
      ["FUENTE", "Texto", "PDF de origen: PP_MENSUAL_<año>_<mes>.pdf."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_canon_lote_mes.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon y sobrecanon generado por cada lote y mes (US$) y la parte de cada departamento (Excel de Determinación).",
    proposito: [
      "Contiene la determinación del canon y sobrecanon petrolero: cuánto canon generó cada lote e hidrocarburo en cada mes y cómo se reparte entre los departamentos de su zona. Proviene de los Excel «Canon Petrolero <año>» de la página Canon y Sobre Canon de PERUPETRO S.A. (s. f.-b).",
      "Sirve para responder cuánto canon aporta cada lote a cada departamento (p. ej., qué parte del canon de Ucayali proviene del Lote 95). Es el insumo de la vista «Generado por el lote» del mapa.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, sección 9. Se lee una hoja por mes y se ignoran las hojas de trabajo («Ene-2», «Abr (2)», «TOTAL») y los meses aún vacíos. Montos tal como los imprime el Excel.",
    clave: "Un mes, un lote y un hidrocarburo (fila LOTE_ITEM). Clave: AÑO + MES + ZONA + LOTE_ITEM.",
    vars: [
      ["AÑO", "Entero", "Año de producción."], ["MES", "Entero (1–12)", "Mes de producción."], V.FECHA,
      ["ZONA", "Texto", "Bloque del Excel: PIURA / TUMBES, PROVINCIA PUERTO INCA HUANUCO, LORETO / UCAYALI o CUSCO."],
      ["LOTE_ITEM", "Texto", "Fila tal como figura en el Excel (p. ej., «X-GAS», «31-C LGN (*)», «Ajustes meses anteriores (3)»)."],
      ["LOTE", "Texto (código)", "Lote sin el producto (Z1 → Z-1). Los ajustes van como AJUSTES MESES ANTERIORES."],
      ["PRODUCTO", "Texto (código)", "PETROLEO, GAS, LGN o CONDENSADO."],
      ["MODALIDAD", "Texto (código)", "LICENCIA o SERVICIOS."],
      ["UNIDAD", "Texto (código)", "BLS (barriles) o MM BTU."],
      ["VOLUMEN", "Decimal, según UNIDAD", "Volumen del mes (primera más segunda quincena)."],
      ["PRECIO_1Q", "Decimal, US$ por unidad", "Precio de canasta o valor de venta de la primera quincena."],
      ["PRECIO_2Q_MES", "Decimal, US$ por unidad", "Precio de la segunda quincena o del mes."],
      ["DEDUCCIONES_US$", "Decimal, dólares (US$)", "Suma de flete marítimo, comercialización, oleoducto y fiscalización, como los trae el Excel."],
      ["VALOR_PRODUCCION_US$", "Decimal, dólares (US$)", "Valor de la producción del lote."],
      ["CANON_TOTAL_US$", "Decimal, dólares (US$)", "Canon más sobrecanon (o participación) generado por el lote."],
      ["DEPARTAMENTO_1", "Texto", "Primer departamento de la zona (Piura, Huánuco, Loreto o Cusco)."],
      ["CANON_DEP_1_US$", "Decimal, dólares (US$)", "Parte del canon que corresponde a DEPARTAMENTO_1."],
      ["DEPARTAMENTO_2", "Texto", "Segundo departamento (Tumbes o Ucayali); vacío si la zona tiene uno solo."],
      ["CANON_DEP_2_US$", "Decimal, dólares (US$)", "Parte del canon que corresponde a DEPARTAMENTO_2."],
      ["TIPO_CAMBIO", "Decimal, soles por US$", "Tipo de cambio del Excel; 0 si aún no lo tiene."],
      ["HOJA", "Texto", "Hoja del Excel de origen."]],
    nota: "Control: la suma de los lotes de cada zona se compara con el «Subtotal» del Excel (CONTROL PP canon_excel_lectura.csv).",
    refs: ["canon"],
  },
  {
    archivo: "PP_canon_distribucion_mes.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon transferido por departamento, mes y beneficiario (S/), 1993–hoy (Excel de Distribución).",
    proposito: [
      "Contiene la distribución mensual del canon y sobrecanon petrolero de cada departamento productor entre sus beneficiarios (gobierno regional, municipalidades, universidades, institutos y otros), en soles, desde 1993. Proviene de los Excel «Canon por Año <departamento>» de la página Canon y Sobre Canon de PERUPETRO S.A. (s. f.-b).",
      "Sirve para saber cuánto recibió cada tipo de beneficiario y es la base de la serie oficial de canon por departamento (PP_canon_departamento_mes.csv y PP_canon_departamento_anio.csv).",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, sección 9. Una hoja por año; el año de la hoja manda sobre la etiqueta del mes. Para Huánuco, el canon corresponde solo a la provincia de Puerto Inca.",
    clave: "Un departamento, un mes y un beneficiario. Clave: DEPARTAMENTO + AÑO + MES + BENEFICIARIO.",
    vars: [
      ["DEPARTAMENTO", "Texto", "Departamento productor (Loreto, Ucayali, Piura, Tumbes, Huánuco o Cusco)."],
      ["AÑO", "Entero", "Año del período de pago (tomado del nombre de la hoja)."],
      ["MES", "Entero (1–12)", "Mes del período de pago."], V.FECHA,
      ["FECHA_PAGO", "Texto, fecha dd/mm/aaaa", "Mes en que se paga (enero se paga en febrero)."],
      ["BENEFICIARIO", "Texto", "Beneficiario tal como figura en el Excel."],
      ["TIPO_BENEFICIARIO", "Texto (código)", "GOBIERNO REGIONAL, INSTITUTOS, UNIVERSIDADES, IIAP, MUNICIPALIDADES o LEY 29289."],
      ["PORCENTAJE", "Texto", "Porcentaje que corresponde al beneficiario, tal como figura (p. ej., «52% », «20% - 40%»)."],
      ["MONTO_SOLES", "Decimal, soles (S/)", "Monto transferido en el mes."]],
    nota: "Control: la suma de los beneficiarios se compara con el TOTAL del Excel, con la Determinación del mismo mes y con las estadísticas en PDF.",
    refs: ["canon"],
  },
  {
    archivo: "PP_canon_municipal_mes.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon por municipalidad provincial y distrital y mes (S/): año en curso y 1993–2002.",
    proposito: [
      "Contiene el canon y sobrecanon transferido a cada municipalidad provincial y distrital, en soles. Tiene dos fuentes: (a) los Excel «Canon por Año <departamento>» de la página Canon Municipalidades de PERUPETRO S.A. (s. f.-a), que traen el año en curso para cinco departamentos (Ucayali no tiene), y (b) el detalle «Distribución por concejos» de los Excel de Distribución de 1993–2002 (PERUPETRO S.A., s. f.-b).",
      "Sirve para saber cuánto recibe cada municipalidad, en particular las de los distritos donde se ubica cada lote (vista «Municipalidades del lote» del mapa).",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, sección 9. Del Excel de Municipalidades se lee el bloque validado con la PCM (secciones GOBIERNOS LOCALES y COMUNIDADES [5 %] del D. U. 026-2010). Los meses que en el Excel aún están en 0 no se cargan. Como ese Excel solo trae el año en curso, la tabla se acumula en Drive.",
    clave: "Un departamento, un mes, una sección y una municipalidad. Clave: DEPARTAMENTO + AÑO + MES + SECCION + PROVINCIA + MUNICIPALIDAD.",
    vars: [
      ["DEPARTAMENTO", "Texto", "Departamento productor."],
      ["AÑO", "Entero", "Año del período de pago."], ["MES", "Entero (1–12)", "Mes del período de pago."], V.FECHA,
      ["FECHA_PAGO", "Texto, fecha dd/mm/aaaa", "Mes en que se paga."],
      ["SECCION", "Texto (código)", "GOBIERNOS LOCALES, COMUNIDADES (5%) o CONCEJOS MUNICIPALES (Distribución 1993–2002)."],
      ["PROVINCIA", "Texto", "Provincia a la que pertenece la municipalidad."],
      ["PORCENTAJE_PROVINCIA", "Texto", "Porcentaje de la provincia, cuando el Excel lo indica (Distribución 1993–2002)."],
      ["MUNICIPALIDAD", "Texto", "Municipalidad, sin las notas «(*)»."],
      ["NIVEL", "Texto (código)", "PROVINCIAL (la primera de cada provincia o la marcada «(Provincial)») o DISTRITAL."],
      ["MONTO_SOLES", "Decimal, soles (S/)", "Monto transferido en el mes."],
      ["FUENTE_EXCEL", "Texto", "Excel de origen."]],
    nota: "Control: la suma de municipalidades se compara con el TOTAL de su sección y con el rubro municipal de la Distribución.",
    refs: ["canonMun", "canon"],
  },
  {
    archivo: "PP_canon_nivel_gobierno_mef_anio.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon y sobrecanon petrolero recaudado por nivel de gobierno (nacional, locales, regionales), total país y por departamento, según el MEF (2003–hoy).",
    proposito: [
      "Contiene, para cada año y tipo de recurso petrolero de la Consulta Amigable de Ingresos del MEF, el monto recaudado por cada nivel de gobierno: gobierno nacional (E), gobiernos locales (M) y gobiernos regionales (R), en total país y, cuando la consulta lo permite, por departamento.",
      "Sirve para ver cómo se distribuye el canon petrolero entre niveles de gobierno antes del detalle por municipalidad (PP_canon_municipal_mef_anio.csv) y para contrastarlo con el reparto por beneficiario de PERUPETRO.",
    ],
    origen: "Notebook PP_MEF_Canon_Municipal.ipynb: navega con requests el formulario ASP.NET de la Consulta Amigable de Ingresos, como el navegador (la consulta ignora los filtros puestos en la URL). Desde 2007: fuente 5 → rubro 18 → tipos «5» y «K» de canon y sobrecanon petrolero; 2003–2006: fuente 01 → tipo «4» (petrolero) y, en 2005–2006, «0: NORMAL» (todos los canones). 2003–2004 no tienen «Nivel de Gobierno»: se registra el reparto por sector y pliego (2003: todo al Consejo Nacional de Descentralización), con NIVEL_GOBIERNO «SIN NIVEL EN LA CONSULTA · sector › pliego». Se acumula por año. Control: suma de niveles = total del tipo de recurso (CONTROL PP canon_nivel_gobierno_mef.csv).",
    clave: "Un año, un tipo de recurso, un nivel de gobierno y un departamento (o TOTAL PAÍS). Clave: AÑO + TIPO_RECURSO + NIVEL_GOBIERNO + DEPARTAMENTO.",
    vars: [V.AÑO,
      ["TIPO_RECURSO", "Texto", "Tipo de recurso del MEF (p. ej., «5: CANON Y SOBRECANON PETROLERO»); «(todos los canones)» si es el tipo NORMAL."],
      ["NIVEL_GOBIERNO", "Texto", "E: GOBIERNO NACIONAL, M: GOBIERNOS LOCALES o R: GOBIERNOS REGIONALES."],
      ["DEPARTAMENTO", "Texto", "TOTAL PAÍS o el departamento."],
      ["RECAUDADO_SOLES", "Decimal, soles (S/)", "Monto recaudado en el año."],
      ["FUENTE", "Texto", "MEF, Consulta Amigable de Ingresos (recaudado)."]],
    refs: ["mef"],
  },
  {
    archivo: "PP_canon_municipal_mef_anio.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon y sobrecanon petrolero recaudado por cada municipalidad y año según el MEF (2005–hoy); completa los años sin detalle de PERUPETRO.",
    proposito: [
      "Contiene el canon y sobrecanon petrolero que registró como recaudado cada municipalidad provincial y distrital, por año, según la Consulta Amigable de Ingresos del MEF (fuente 5, rubro 18, tipos de recurso «5: Canon y sobrecanon petrolero» y «K: Sub cuenta – Canon y sobrecanon petrolero»).",
      "Sirve para completar el canon por municipalidad de los años en los que PERUPETRO entrega el total municipal a un intermediario (CND hasta 2006, PCM desde 2007) y no publica el reparto. En 2003–2004 el MEF no tiene detalle por municipalidad; en 2005–2006 el grueso está en el tipo «0: NORMAL», que reúne todos los canones, y esas filas quedan rotuladas «(todos los canones)».",
    ],
    origen: "Notebook PP_MEF_Canon_Municipal.ipynb: navega con requests el formulario ASP.NET de la Consulta Amigable de Ingresos, como el navegador (la consulta ignora los filtros puestos en la URL). Se acumula: cada corrida reemplaza los años que vuelve a leer. Lo recaudado puede diferir de lo transferido por PERUPETRO en el mismo año por las fechas de registro; el control lo compara (CONTROL PP canon_municipal_mef.csv).",
    clave: "Un año, una municipalidad y un tipo de recurso. Clave: AÑO + DEPARTAMENTO + CODIGO + TIPO_RECURSO.",
    vars: [V.AÑO,
      ["DEPARTAMENTO", "Texto", "Departamento de la municipalidad (p. ej., LORETO)."],
      ["CODIGO", "Texto", "Código de la entidad en el MEF, tal como figura (p. ej., 06-301459)."],
      ["MUNICIPALIDAD_MEF", "Texto", "Nombre completo de la entidad en el MEF (p. ej., MUNICIPALIDAD DISTRITAL DE PUINAHUA)."],
      ["MUNICIPALIDAD", "Texto", "Nombre corto: el distrito o, en las provinciales, la capital (MAYNAS - IQUITOS → IQUITOS)."],
      ["NIVEL", "Texto (código)", "PROVINCIAL o DISTRITAL."],
      ["PROVINCIA", "Texto", "Provincia: en las provinciales, del nombre del MEF; en las distritales, de la tabla de PERUPETRO cuando existe."],
      ["TIPO_RECURSO", "Texto", "Tipo de recurso del MEF del que sale el monto: 5 o K desde 2007; 4 o «0: NORMAL (todos los canones)» en 2005–2006."],
      ["RECAUDADO_SOLES", "Decimal, soles (S/)", "Monto recaudado en el año."],
      ["FUENTE", "Texto", "MEF, Consulta Amigable de Ingresos (recaudado); en las filas NORMAL se aclara que reúne todos los canones."]],
    refs: ["mef"],
  },
  {
    archivo: "PP_canon_municipal_mef_mes.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon y sobrecanon petrolero recaudado por cada municipalidad y mes según el MEF (2005–hoy).",
    proposito: [
      "Es la versión mensual de PP_canon_municipal_mef_anio.csv: el mismo recaudado por municipalidad y tipo de recurso, abierto por mes con el botón «Mes» de la Consulta Amigable de Ingresos.",
      "Sirve para comparar mes a mes con las transferencias de PERUPETRO y ver desfases entre lo transferido y lo registrado como recaudado.",
    ],
    origen: "Notebook PP_MEF_Canon_Municipal.ipynb: navega con requests el formulario ASP.NET de la Consulta Amigable de Ingresos, como el navegador (la consulta ignora los filtros puestos en la URL). Ruta: tipo de recurso → nivel M (y gob. local) → Mes → Departamento → Municipalidad. Se genera con DETALLE = «Anual y mensual». Control: la suma de los meses es igual al total anual (CONTROL PP canon_mef_mes.csv).",
    clave: "Un año, un mes, una municipalidad y un tipo de recurso. Clave: AÑO + MES + DEPARTAMENTO + CODIGO + TIPO_RECURSO.",
    vars: [V.AÑO,
      ["MES", "Entero (1–12)", "Mes del registro de la recaudación."],
      ["DEPARTAMENTO", "Texto", "Departamento de la municipalidad."],
      ["CODIGO", "Texto", "Código de la entidad en el MEF."],
      ["MUNICIPALIDAD_MEF", "Texto", "Nombre completo de la entidad en el MEF."],
      ["MUNICIPALIDAD", "Texto", "Nombre corto: el distrito o, en las provinciales, la capital."],
      ["NIVEL", "Texto (código)", "PROVINCIAL o DISTRITAL."],
      ["PROVINCIA", "Texto", "Provincia de la municipalidad."],
      ["TIPO_RECURSO", "Texto", "Tipo de recurso del MEF (5, K, 4 o «0: NORMAL (todos los canones)»)."],
      ["RECAUDADO_SOLES", "Decimal, soles (S/)", "Monto recaudado en el mes."],
      ["FUENTE", "Texto", "MEF, Consulta Amigable de Ingresos (recaudado)."]],
    refs: ["mef"],
  },
  {
    archivo: "PP_canon_nivel_gobierno_mef_mes.csv", tema: "Fiscal (canon)", util: "Útil",
    para: "Canon y sobrecanon petrolero recaudado por nivel de gobierno y mes, total país, según el MEF (2005–hoy).",
    proposito: [
      "Es la versión mensual de PP_canon_nivel_gobierno_mef_anio.csv (total país): lo recaudado por el gobierno nacional, los gobiernos locales y los gobiernos regionales en cada mes y tipo de recurso petrolero.",
    ],
    origen: "Notebook PP_MEF_Canon_Municipal.ipynb: navega con requests el formulario ASP.NET de la Consulta Amigable de Ingresos, como el navegador (la consulta ignora los filtros puestos en la URL). Ruta: tipo de recurso → Mes → Nivel de Gobierno. Se genera con DETALLE = «Anual y mensual». Control: la suma de los meses es igual al total anual (CONTROL PP canon_mef_mes.csv).",
    clave: "Un año, un mes, un tipo de recurso y un nivel de gobierno. Clave: AÑO + MES + TIPO_RECURSO + NIVEL_GOBIERNO.",
    vars: [V.AÑO,
      ["MES", "Entero (1–12)", "Mes del registro de la recaudación."],
      ["TIPO_RECURSO", "Texto", "Tipo de recurso del MEF."],
      ["NIVEL_GOBIERNO", "Texto", "E: GOBIERNO NACIONAL, M: GOBIERNOS LOCALES o R: GOBIERNOS REGIONALES."],
      ["DEPARTAMENTO", "Texto", "TOTAL PAÍS."],
      ["RECAUDADO_SOLES", "Decimal, soles (S/)", "Monto recaudado en el mes."],
      ["FUENTE", "Texto", "MEF, Consulta Amigable de Ingresos (recaudado)."]],
    refs: ["mef"],
  },
  {
    archivo: "PP_canon_departamento_mes.csv", tema: "Fiscal (canon)", util: "Útil (serie oficial)",
    para: "Serie oficial de canon por departamento y mes (MM S/), 1993–hoy, con control contra el PDF.",
    proposito: [
      "Es la serie oficial del proyecto de canon y sobrecanon petrolero por departamento y mes, en millones de soles: suma de los beneficiarios del Excel de Distribución (PERUPETRO S.A., s. f.-b), con el valor de la estadística mensual en PDF (PERUPETRO S.A., s. f.-c) como control.",
      "Sirve para las series y comparaciones mensuales de canon por departamento (p. ej., transferencias de enero frente a diciembre).",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, sección 9 (punto 3). Un mes que ya está en el PDF pero todavía no en el Excel se toma del PDF.",
    clave: "Un departamento y un mes. Clave: AÑO + MES + DEPARTAMENTO.",
    vars: [V.AÑO, V.MES, V.FECHA,
      ["DEPARTAMENTO", "Texto", "Uno de los seis departamentos productores o TOTAL."],
      ["CANON_MM_SOLES", "Decimal, millones de soles", "Canon y sobrecanon transferido en el mes (suma de beneficiarios de la Distribución)."],
      ["CANON_PDF_MM_SOLES", "Decimal, millones de soles", "Control: el mismo mes según la estadística mensual en PDF; vacío si no hay PDF de ese mes."],
      ["FUENTE", "Texto", "Excel de Distribución «Canon por Año <departamento>» o «Estadística mensual en PDF (aún no está en el Excel)»."]],
    refs: ["canon", "estad"],
  },
  {
    archivo: "PP_canon_departamento_anio.csv", tema: "Fiscal (canon)", util: "Útil (serie oficial)",
    para: "Serie oficial de canon por departamento y año (MM S/), 1993–hoy, con control contra el PDF anual.",
    proposito: [
      "Es la serie oficial anual de canon y sobrecanon petrolero por departamento, en millones de soles: suma de los meses de PP_canon_departamento_mes.csv, con el valor de la estadística anual en PDF como control.",
      "Sirve para comparaciones anuales y para el mapa, que usa solo los años completos.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb, sección 9 (punto 3). Los departamentos o años que no están en el Excel se toman del PDF anual.",
    clave: "Un departamento y un año. Clave: AÑO + DEPARTAMENTO.",
    vars: [V.AÑO,
      ["DEPARTAMENTO", "Texto", "Uno de los seis departamentos productores o TOTAL."],
      ["CANON_MM_SOLES", "Decimal, millones de soles", "Suma de los meses del año."],
      ["MESES", "Entero (1–12)", "Número de meses sumados."],
      ["AÑO_COMPLETO", "Lógico (True/False)", "True si el año tiene 12 meses."],
      ["CANON_PDF_ANUAL", "Decimal, millones de soles", "Control: valor de la estadística anual en PDF."],
      ["FUENTE", "Texto", "Excel de Distribución o «PDF anual (no está en el Excel)»."]],
    nota: "Un año incompleto (AÑO_COMPLETO = False) no debe compararse con años completos.",
    refs: ["canon", "estad"],
  },
  {
    archivo: "PP_canon_departamento_mes_pdf.csv", tema: "Control (canon)", util: "Control",
    para: "Canon por departamento y mes según las estadísticas mensuales en PDF; sirve para validar la serie oficial.",
    proposito: [
      "Contiene el canon y sobrecanon por departamento y mes, en millones de soles, leído del «Resumen ejecutivo» de las estadísticas mensuales en PDF de PERUPETRO S.A. (s. f.-c). Hasta el 19 de octubre de 2026 se llamaba PP_canon_departamento_mes.csv.",
      "Sirve como control: se compara con la serie oficial que sale del Excel de Distribución y llena los meses que el Excel todavía no publica. No se recomienda usarlo como serie principal.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb. El PDF trae el canon con un mes de rezago (el reporte de enero trae los 12 meses del año anterior). PERUPETRO solo publica las mensuales del año en curso, por lo que la serie se acumula en Drive (2025–hoy).",
    clave: "Un departamento y un mes. Clave: AÑO + MES + DEPARTAMENTO.",
    vars: [V.AÑO, V.MES, V.FECHA,
      ["DEPARTAMENTO", "Texto", "Departamento, como en el resumen ejecutivo del PDF."],
      ["CANON_MM_SOLES", "Decimal, millones de soles", "Canon y sobrecanon del mes según el PDF."],
      ["FUENTE", "Texto", "PDF de origen: PP_MENSUAL_<año>_<mes>.pdf."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_canon_departamento_anio_pdf.csv", tema: "Control (canon)", util: "Control",
    para: "Canon por departamento y año según las estadísticas anuales en PDF; sirve para validar la serie oficial.",
    proposito: [
      "Contiene el canon y sobrecanon por departamento y año, en millones de soles corrientes, de la tabla «Distribución del canon / sobrecanon» de las estadísticas anuales de PERUPETRO S.A. (s. f.-c). Hasta el 19 de octubre de 2026 se llamaba PP_canon_departamento_anio.csv.",
      "Sirve como control de la serie oficial anual y como respaldo para los años o departamentos que no están en el Excel.",
    ],
    origen: "Notebook PP_Produccion_Lotes.ipynb. Cada anual trae series de 10 años (la edición 2001 llega a 1993); para cada año manda la edición más reciente. Cuando hay 12 meses en el PDF mensual, su suma reemplaza al valor anual y este queda en CANON_PDF_ANUAL.",
    clave: "Un departamento y un año. Clave: AÑO + DEPARTAMENTO.",
    vars: [V.AÑO,
      ["DEPARTAMENTO", "Texto", "Departamento, como en el PDF."],
      ["CANON_MM_SOLES", "Decimal, millones de soles", "Canon y sobrecanon del año."],
      ["CANON_PDF_ANUAL", "Decimal, millones de soles", "Valor impreso en el anual cuando fue reemplazado por la suma mensual."],
      ["FUENTE", "Texto", "PP_ANUAL_<edición>.pdf o «SUMA MENSUAL (…)»."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_operadores_lote.csv", tema: "Empresas", util: "Útil",
    para: "Quién operó cada lote y en qué años, con su producción y regalías en ese período.",
    proposito: [
      "Reconstruye el historial de operadores de cada lote a partir de la producción fiscalizada de líquidos y gas: una fila por lote, operador y período continuo de años con producción.",
      "Sirve para responder quién opera un lote y desde cuándo (también en contratos ya terminados), y cuánto produjo y pagó en regalías cada empresa en su período. Alimenta la pestaña Empresas del mapa.",
    ],
    origen: "Lo genera el notebook del mapa (PP_Mapa_Lotes.ipynb y PP_Mapa_Lotes_Plus.ipynb) a partir de PP_produccion_lote_mes, PP_produccion_gas_lote_mes y PP_regalias_lote_anio. Un año sin producción corta el período.",
    clave: "Un lote, un operador y un período. Clave: LOTE + OPERADOR + AÑO_INICIO.",
    vars: [V.DEPARTAMENTO,
      ["CAMPO", "Texto", "Campo al que pertenece el lote (lotes que comparten polígono, p. ej., 1-AB/192)."],
      V.LOTE, ["OPERADOR", "Texto", "Empresa operadora (nombre homologado)."],
      ["AÑO_INICIO", "Entero", "Primer año del período con producción."],
      ["AÑO_FIN", "Entero", "Último año del período con producción."],
      ["AÑOS_CON_PRODUCCION", "Entero", "Número de años del período."],
      ["LIQUIDOS_BBL", "Entero, barriles", "Producción de líquidos del operador en el período."],
      ["GAS_MPC", "Entero, miles de pies cúbicos", "Producción de gas natural del operador en el período."],
      ["REGALIAS_US$", "Decimal, dólares (US$)", "Regalías pagadas por ese operador en el período."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_LOTES_GEO.csv", tema: "Geografía", util: "Útil",
    para: "Una fila por lote con su ubicación (departamento, provincias, distritos), cuenca, distancias, áreas protegidas, comunidades y producción acumulada.",
    proposito: [
      "Reúne las variables geográficas de cada lote de contrato calculadas sobre su polígono: departamentos, provincias y distritos que ocupa, cuenca sedimentaria, área, distancias al oleoducto, a Iquitos y a ríos grandes, superposición con áreas naturales protegidas y comunidades nativas, además de la producción acumulada y los indicadores de producción del campo.",
      "Sirve para asignar cada lote a su departamento en las demás tablas, para el reparto del canon entre distritos y para la caracterización territorial de los lotes.",
    ],
    origen: "Notebook del mapa (PP_Mapa_Lotes.ipynb y PP_Mapa_Lotes_Plus.ipynb). Polígonos del geoportal de PERUPETRO S.A. (s. f.-d) para los contratos vigentes y de la capa de INGEMMET de enero de 2019 para los lotes antiguos; límites administrativos de geoBoundaries (Runfola et al., 2020); ríos de HydroRIVERS (Lehner & Grill, 2013). Las capas usadas en cada corrida quedan en CONTROL PP mapa capas.csv.",
    clave: "Un lote. Clave única: LOTE.",
    vars: [V.FECHA_EXTRACCION,
      ["LOTE", "Texto (código)", "Mismo código que en las tablas de producción."],
      ["GEOMETRIA_DE", "Texto", "Lote(s) del mapa cuyo polígono se usó; igual a LOTE salvo equivalencias (1-AB → 192; 31-B/D → 31-B+31-D)."],
      ["LOTE_MAPA", "Texto", "Nombre del lote en la capa (p. ej., LOTE_XCV = 95)."],
      ["OPERADOR_MAPA", "Texto", "Operador del contrato vigente según el geoportal."],
      ["ESTADO_MAPA", "Texto", "Fase del contrato según el geoportal (EXPLORACIÓN o EXPLOTACIÓN)."],
      ["TIPO_CONTRATO", "Texto", "LICENCIA o SERVICIOS, según el geoportal."],
      ["F_SUSCRIPCION", "Texto, fecha", "Fecha de suscripción según el geoportal."],
      ["CAPA", "Texto", "Capa de la que salió el polígono."],
      ["FUENTE_POLIGONO", "Texto", "Fuente del polígono (geoportal de PERUPETRO o INGEMMET 2019)."],
      ["DEPARTAMENTO", "Texto", "Departamento con la mayor parte del área del lote."],
      ["DEPARTAMENTO_PCT", "Decimal, porcentaje (0–100)", "Porcentaje del área del lote en ese departamento."],
      ["DEPARTAMENTO_DETALLE", "Texto", "Reparto completo por departamento (p. ej., «LORETO 67,7%; UCAYALI 32,3%»)."],
      ["DEPARTAMENTO_N", "Entero", "Número de departamentos que toca el lote."],
      ["PROVINCIA_DETALLE", "Texto", "Porcentaje del área del lote en cada provincia: «DEP|PROV 61.0%; …»."],
      ["DISTRITO_DETALLE", "Texto", "Porcentaje del área del lote en cada distrito: «DEP|PROV|DIST 36.0%; …». Se usa para el canon de las municipalidades del lote."],
      ["ZOCALO", "Texto (SI/NO)", "SI para lotes mayormente en el mar (menos del 50 % de su área en tierra)."],
      ["CUENCA", "Texto", "Cuenca sedimentaria (Marañón, Ucayali, Talara, etc.)."],
      ["CUENCA_PCT", "Decimal, porcentaje", "Porcentaje del lote en esa cuenca."],
      ["AREA_KM2", "Decimal, km²", "Superficie del lote (proyección equivalente de Sudamérica, ESRI:102033)."],
      ["LAT", "Decimal, grados", "Latitud de un punto interior del lote (WGS84)."],
      ["LON", "Decimal, grados", "Longitud de un punto interior del lote (WGS84)."],
      ["DIST_OLEODUCTO_KM", "Decimal, km", "Distancia mínima del lote al Oleoducto Norperuano; 0 si lo cruza."],
      ["DIST_IQUITOS_KM", "Decimal, km", "Distancia mínima del lote a Iquitos."],
      ["DIST_RIO_GRANDE_KM", "Decimal, km", "Distancia desde el punto interior al río más cercano con caudal medio de al menos 5 000 m³/s (caudal modelado de HydroRIVERS). Aproxima el acceso fluvial; no es una medida oficial de navegabilidad."],
      ["DIST_RIO_1000_KM", "Decimal, km", "Misma distancia para ríos de al menos 1 000 m³/s (afluentes)."],
      ["DIST_RIO_5000_KM", "Decimal, km", "Misma distancia para ríos de al menos 5 000 m³/s (ríos troncales)."],
      ["DIST_RIO_20000_KM", "Decimal, km", "Misma distancia para ríos de al menos 20 000 m³/s (Amazonas o tramos bajos)."],
      ["RIO_CERCANO", "Texto", "Nombre del río grande más cercano."],
      ["ANP_PCT", "Decimal, porcentaje", "Porcentaje del lote dentro de áreas naturales protegidas."],
      ["ANP_DETALLE", "Texto", "Áreas naturales protegidas que toca el lote."],
      ["CCNN_DENTRO_N", "Entero", "Número de comunidades nativas dentro del lote."],
      ["CCNN_5KM_N", "Entero", "Número de comunidades nativas a menos de 5 km del lote."],
      ["CCNN_DENTRO", "Texto", "Nombres de las comunidades nativas dentro del lote (hasta 40)."],
      ["CAMPO", "Texto", "Campo al que pertenece el polígono (lotes que lo comparten, p. ej., 1-AB/192). Los indicadores de producción de esta tabla son del campo."],
      ["PETROLEO_ACUM_MMBBL", "Decimal, millones de barriles", "Petróleo acumulado del lote en la base de producción."],
      ["PETROLEO_ACUM_CAMPO_MMBBL", "Decimal, millones de barriles", "Petróleo acumulado de todos los contratos del campo."],
      ["GAS_ACUM_CAMPO_BCF", "Decimal, miles de millones de pies cúbicos", "Gas natural acumulado del campo."],
      ["ESTADO_PRODUCCION … OPERADORES", "Varios", "Indicadores de producción del campo, con la misma definición que en PP_LOTES_INDICADORES.csv."]],
    refs: ["geo", "runfola", "lehner", "estad"],
  },
  {
    archivo: "PP_LOTES_INDICADORES.csv", tema: "Producción", util: "Útil",
    para: "Una fila por lote con producción: estado, pico, producción actual, declinación, paralizaciones y operadores.",
    proposito: [
      "Resume en indicadores la trayectoria productiva de cada lote de la base de producción, tenga o no polígono en el mapa. Los indicadores se calculan sobre todos los líquidos fiscalizados (petróleo, LGN y condensado).",
      "Sirve para caracterizar los lotes (si están en producción o paralizados, cuándo tuvieron su pico, cuánto declinan, cuánto duró su paralización más larga y quién los operó).",
    ],
    origen: "Notebook del mapa, a partir de PP_produccion_lote_mes.",
    clave: "Un lote. Clave única: LOTE.",
    vars: [V.FECHA_EXTRACCION,
      ["LOTE", "Texto (código)", "Lote de producción."],
      ["CAMPO", "Texto", "Campo al que pertenece el lote."],
      ["DEPARTAMENTO", "Texto", "Departamento del lote (del mapa o, si no tiene polígono, de la base de producción)."],
      ["TIENE_POLIGONO", "Texto (SI/NO)", "Si el lote se ubicó en el mapa (directamente o por equivalencia)."],
      ["PETROLEO_ACUM_MMBBL", "Decimal, millones de barriles", "Petróleo acumulado en la base."],
      ["LIQUIDOS_ACUM_MMBBL", "Decimal, millones de barriles", "Líquidos acumulados (petróleo, LGN y condensado)."],
      ["ESTADO_PRODUCCION", "Texto (código)", "EN PRODUCCIÓN (produjo en los últimos 12 meses de la base); PARALIZADO (produjo antes, no en los últimos 12 meses); SUCEDIDO POR … (el contrato terminó y el campo siguió con otro lote); SIN PRODUCCIÓN REGISTRADA."],
      ["PRODUCTO_PRINCIPAL", "Texto (código)", "Producto con más barriles acumulados (PETROLEO, LGN o CONDENSADO)."],
      ["PRIMERA_PRODUCCION", "Texto, mm/aaaa", "Primer mes con producción; «≤01/1994» si ya producía al inicio de la base."],
      ["ULTIMA_PRODUCCION", "Texto, mm/aaaa", "Último mes con producción."],
      ["BPD_ACTUAL", "Entero, barriles por día", "Producción promedio de los últimos 12 meses de la base."],
      ["PICO_AÑO", "Entero", "Año completo de mayor producción diaria."],
      ["PICO_BPD", "Entero, barriles por día", "Producción diaria promedio de ese año."],
      ["DECLINACION_ANUAL_5A_PCT", "Decimal, porcentaje anual", "Variación anual compuesta de la producción diaria en cinco años, entre dos años completos «normales» (máximo dos meses sin producción). Negativo = declina; vacío si no hay dos años normales."],
      ["DECLINACION_PERIODO", "Texto", "Años usados para la declinación (p. ej., 2019–2024)."],
      ["MESES_SIN_PRODUCCION", "Entero", "Meses con 0 barriles desde la primera producción hasta el final de la base; no cuentan los meses en que el campo produjo con otro contrato."],
      ["PARALIZACION_MAX_MESES", "Entero, meses", "Racha más larga de meses consecutivos sin producción."],
      ["PARALIZACION_MAX_DESDE", "Texto, mm/aaaa", "Mes en que empezó esa racha."],
      ["OPERADORES", "Texto", "Empresas que operaron el lote con producción, con sus años y en orden (p. ej., «OCCIDENTAL (1994–2000) → PLUSPETROL (2001–2015)»)."]],
    refs: ["estad"],
  },
  {
    archivo: "PP_LOTES_ESTADO_PRODUCTO.csv", tema: "Producción", util: "Útil",
    para: "Estado actual de cada campo por producto (petróleo, LGN/condensado, gas): en producción o paralizado, última producción y nivel actual.",
    proposito: [
      "Indica, para cada campo y cada producto por separado (petróleo, LGN y condensado, gas natural), si está en producción, paralizado o sin producción, cuál fue su último mes con producción y su producción diaria promedio reciente.",
      "Sirve para saber, por ejemplo, si un campo sigue produciendo gas aunque haya dejado de producir LGN. Es la tabla que muestra el mapa en la ficha de cada lote, disponible para usarla fuera del mapa.",
    ],
    origen: "Notebook del mapa, a partir de la producción mensual de líquidos y gas; los meses posteriores a la última estadística mensual se completan con los reportes diarios (PP_produccion_diaria.csv).",
    clave: "Un campo. Clave única: CAMPO.",
    vars: [V.FECHA_EXTRACCION,
      ["CAMPO", "Texto", "Campo (lotes que comparten polígono)."],
      ["ESTADO_PETROLEO", "Texto (código)", "EN PRODUCCIÓN (produjo en los últimos 12 meses con datos), PARALIZADO (produjo antes) o SIN PRODUCCIÓN (nunca)."],
      ["ULTIMA_PRODUCCION_PETROLEO", "Texto, mm/aaaa", "Último mes con producción de petróleo."],
      ["ACTUAL_PETROLEO_BPD", "Decimal, barriles por día", "Promedio diario de los últimos 12 meses con datos."],
      ["ESTADO_LGN_CONDENSADO", "Texto (código)", "Igual que ESTADO_PETROLEO, para LGN y condensado."],
      ["ULTIMA_PRODUCCION_LGN_CONDENSADO", "Texto, mm/aaaa", "Último mes con producción de LGN o condensado."],
      ["ACTUAL_LGN_CONDENSADO_BPD", "Decimal, barriles por día", "Promedio diario de los últimos 12 meses con datos."],
      ["ESTADO_GAS", "Texto (código)", "Igual que ESTADO_PETROLEO, para gas natural."],
      ["ULTIMA_PRODUCCION_GAS", "Texto, mm/aaaa", "Último mes con producción de gas."],
      ["ACTUAL_GAS_MMPCD", "Decimal, millones de pies cúbicos por día", "Promedio diario de los últimos 12 meses con datos."]],
    nota: "Cuando el estado es SIN PRODUCCIÓN, la última producción y el valor actual quedan vacíos.",
    refs: ["estad", "diaria"],
  },
];

// ── Diccionario de un archivo ────────────────────────────────────────────────
function docArchivo(a) {
  const base = a.archivo.replace(/\.csv$/, "");
  const h = [
    titulo(`Diccionario de datos: ${a.archivo}`), centrado("Proyecto Petróleo"), centrado(`Versión del ${VERSION}`),
    n1("Propósito del archivo"), ...a.proposito.map((t) => par(t)),
    n2("Origen y actualización"), par(a.origen),
    n2("Unidad de observación"), par(a.clave),
    n2("Formato"), par("Archivo CSV separado por comas, codificado en UTF-8 con BOM (se abre directamente en Excel con tildes correctas) y con punto decimal. Una celda vacía significa sin dato."),
    n1("Variables"),
    par(`La Tabla 1 describe cada variable (columna) del archivo, en el orden en que aparecen.`),
    ...tablaVariables(1, a.archivo, a.vars, a.nota),
    ...referencias(a.refs),
  ];
  return [base, documento(h)];
}

// ── Diccionario general ──────────────────────────────────────────────────────
function docGeneral() {
  const h = [
    titulo("Diccionario general de los archivos de la carpeta DATA"), centrado("Proyecto Petróleo"), centrado(`Versión del ${VERSION}`),
    n1("Propósito"),
    par("Este documento describe para qué sirve cada archivo de datos que los notebooks del Proyecto Petróleo guardan en la carpeta DATA de Google Drive, indica si es útil, de control o redundante, y remite al diccionario de variables de cada uno, que lleva el mismo nombre del archivo. Las fuentes son las estadísticas, los Excel de canon, los reportes diarios y el geoportal de PERUPETRO S.A. (s. f.-a, s. f.-b, s. f.-c, s. f.-d, s. f.-e), además de capas geográficas públicas (Lehner & Grill, 2013; Runfola et al., 2020)."),
    n1("Archivos y su utilidad"),
    par("La Tabla 1 lista los archivos de la carpeta DATA. *Útil* indica un archivo de análisis; *control*, un archivo que sirve para validar otro; *redundante*, un archivo cuyo contenido ya está en otro."),
    ...tablaAPA(1, "Archivos de la carpeta DATA, contenido y utilidad", ["Archivo", "Utilidad", "Para qué sirve"],
      [...ARCHIVOS.map((a) => [a.archivo, a.util, a.para]),
        ["PP_produccion_lote_mes_2026-2026.csv", "Redundante", "Subconjunto de PP_produccion_lote_mes_1994-2026.csv creado por una corrida solo de 2026."],
        ["PP_produccion_gas_lote_mes_2026-2026.csv", "Redundante", "Subconjunto de PP_produccion_gas_lote_mes_1994-2026.csv creado por una corrida solo de 2026."]],
      [3700, 1700, 3626],
      "Cada archivo útil o de control tiene su propio diccionario de variables (Word) con el mismo nombre."),
    n1("Archivos redundantes"),
    par("Los archivos PP_produccion_lote_mes_2026-2026.csv y PP_produccion_gas_lote_mes_2026-2026.csv se crean cuando el notebook de producción se corre solo para 2026. Tienen las mismas variables que los archivos 1994-2026 y sus filas ya están contenidas en ellos, siempre que la corrida 1994-2026 sea igual o posterior. El mapa siempre usa el archivo de mayor cobertura (1994-2026)."),
    par("Antes de borrarlos conviene comparar su fecha de modificación en Drive: si el archivo 2026-2026 es más reciente que el 1994-2026, este último no tiene los últimos meses publicados y debe volver a correrse el notebook de producción con el período 1994-2026."),
    n1("Cómo se relacionan los archivos"),
    vineta("**Por lote:** LOTE (o LOTE_HISTORICO para series largas) une la producción, el gas, la producción diaria, los pozos, las regalías, la canasta, el valor de la producción, los contratos, el canon por lote y las tablas del mapa."),
    vineta("**Por departamento y mes:** DEPARTAMENTO + AÑO + MES une la producción agregada con el canon mensual."),
    vineta("**Por campo:** CAMPO agrupa los lotes que comparten polígono (p. ej., 1-AB y 192) en las tablas del mapa."),
    vineta("**Canon:** la serie oficial por departamento (PP_canon_departamento_mes y _anio) sale de PP_canon_distribucion_mes; los archivos _pdf la validan; PP_canon_lote_mes explica de qué lote proviene y PP_canon_municipal_mes a qué municipalidad llega."),
    n1("Convenciones"),
    ...tablaAPA(2, "Unidades y convenciones de los archivos", ["Término", "Tipo", "Significado"], [
      ["bbl", "Unidad", "Barril estadounidense = 42 galones = 158,987 litros."],
      ["BPD", "Unidad", "Barriles por día calendario (barriles del mes ÷ días del mes)."],
      ["MPC, MMPCD, BCF", "Unidad (gas)", "Miles de pies cúbicos; millones de pies cúbicos por día; miles de millones de pies cúbicos."],
      ["MM S/, MM US$", "Unidad", "Millones de soles corrientes; millones de dólares."],
      ["Fechas", "Texto", "Formato dd/mm/aaaa. En los datos mensuales, FECHA es el día 01 del mes."],
      ["Codificación", "Archivo", "CSV en UTF-8 con BOM, separador coma y punto decimal."],
      ["Celda vacía", "—", "Sin dato."],
    ], [2300, 1600, 5126]),
    ...referencias(ORDEN_REF),
  ];
  return ["00_Diccionario_general_DATA", documento(h)];
}

(async () => {
  const dir = __dirname;
  const docs = [docGeneral(), ...ARCHIVOS.map(docArchivo)];
  for (const [nombre, d] of docs) {
    fs.writeFileSync(path.join(dir, `${nombre}.docx`), await Packer.toBuffer(d));
  }
  console.log(`ok: ${docs.length} documentos en ${dir}`);
})();
