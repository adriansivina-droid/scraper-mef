"""Pesca: lleva a LONG los Excel mensuales de las DIREPRO de Loreto, San Martín y Ucayali (o carga los LONG que generan
los notebooks de PESCA/). Misma lógica que PESCA/Pesca_Loreto_Long.ipynb y PESCA/Pesca_SMN_UCA_Long.ipynb (ver
PESCA/pesca.md): si cambia el criterio allá, se cambia aquí.

Se reconocen los .xlsx por sus hojas, no por el nombre (salvo el mes de San Martín, que solo viene en el nombre):
  LONG: hoja LOR_PESCA, SMN_PESCA o UCA_PESCA.
  Loreto, consumo: hojas Desemb_* · Loreto, ornamentales: hoja POR ESPECIES.
  San Martín: hoja con PROCEDENCIA, ENCABEZADO y ESPECIE · Ucayali: hojas TOTAL FRESCO, TOTAL SECOSALADO, ….
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

AVISOS = []          # avisos de la última lectura (los junta carga.py)


def _clave(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())


def _texto(v):
    return ' '.join(str(v).split())


# ─── Loreto ───
# Precio base 2007, en miles de soles por tonelada (ornamentales: miles de soles por mil unidades)
PRECIOS = {'FRESCO': 3.27504, 'SALPRESO': 3.01589, 'SECO SALADO': 2.98778, 'ORNAMENTAL': 1.0329}

# Especies del Cuadro Nº 07 (Indicadores del sector pesquero), escritas como en el cuadro; el resto va a "Otros"
ESPECIES_07 = ['Acarahuazu', 'Arahuana', 'Boquichico', 'Carachama', 'Corvina', 'Chambira', 'Chio Chio', 'Fasaco',
               'Gamitana', 'Mota', 'Lisa', 'Leguia', 'Llambina', 'Maparate', 'Palometa', 'Paco', 'Paña', 'Paiche',
               'Ractacara', 'Sabalo', 'Sardina', 'Shuyo', 'Tucunaré', 'Turushuqui', 'Yahuarachi', 'Yaraqui', 'Yulilla',
               'Zúngaro Achara', 'Zúngaro Cunchi mama', 'Zúngaro Doncella', 'Zúngaro Dorado', 'Zúngaro Manitoa',
               'Zúngaro Saltón', 'Zúngaro Tigre', 'Zúngaro Torre']

# Especies del cuadro de producción pesquera (VBP); el resto va a "Otros"
ESPECIES_CUADRO = {'Boquichico': 'Boquichico', 'Llambina': 'Llambina/Palometa', 'Palometa': 'Llambina/Palometa'}

# Nombres del crudo que el Cuadro Nº 07 escribe distinto
CORRECCIONES = {'Manitoa': 'Zúngaro Manitoa', 'Leguia': 'Leguía', 'Sabalo': 'Sábalo', 'Acarahuazu': 'Acarahuazú'}

MESES = {'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
         'SETIEMBRE': 9, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12}

LOR_HOJAS = {'DESEMBARQUE': 'desemb', 'EXTRACCION': 'extrac'}
LOR_ESTADOS = [('FRESCO', 'fres'), ('SALPRESO', 'salp'), ('SECO SALADO', 'seco')]

LOR_COLUMNAS = ['AÑO', 'MES', 'DEPARTAMENTO', 'FUENTE', 'ESTADO', 'DESTINO', 'ESPECIE', 'ESPECIE_CORREGIDA', 'ESPECIE_OK',
            'ESPECIE_CUADRO', 'UNIDAD', 'VOLUMEN', 'VBP']

# Destinos de los peces ornamentales, como en el Cuadro Nº 07, y su orden entre las columnas UNIDADES de la hoja
# POR ESPECIES (ingreso, exportación, nacional, total de egresos, stock remanente y/o mortandad)
DESTINOS = {1: 'Mercado externo', 2: 'Mercado interno', 4: 'Stock remanente y/o mortandad'}


def periodo_loreto(xls):
    """Año y mes desde el rótulo 'PERIODO : FEBRERO - 2026' de cualquier hoja."""
    for hoja in xls.sheet_names:
        d = pd.read_excel(xls, hoja, header=None, nrows=15)
        for v in d.values.ravel():
            m = re.search(r'PERIODO\s*:\s*([A-ZÁÉÍÓÚ]+)\s*-\s*(\d{4})', str(v).upper())
            if m and m.group(1) in MESES:
                return int(m.group(2)), MESES[m.group(1)]
    raise ValueError('No se encontró el rótulo PERIODO en ninguna hoja')


def buscar_hoja(xls, fuente, estado):
    pref, clave = LOR_HOJAS[fuente], dict(LOR_ESTADOS)[estado]
    hallada = [h for h in xls.sheet_names if _clave(h).startswith(pref) and clave in _clave(h)]
    if len(hallada) != 1:
        raise ValueError(f'Hoja de {fuente} {estado}: se esperaba una, se hallaron {hallada}')
    return hallada[0]


def _cuadro_loreto(xls, hoja):
    """Volumen total (t) por especie de un cuadro 'N° | Especie | localidades | Total'."""
    d = pd.read_excel(xls, hoja, header=None)
    fila = next(i for i, v in d.iloc[:, 1].items() if _clave(v) == 'especie')
    enc = [str(v).strip() for v in d.iloc[fila]]
    col_total = max(i for i, v in enumerate(enc) if _clave(v) == 'total')
    filas = []
    for _, r in d.iloc[fila + 1:].iterrows():
        esp = r.iloc[1]
        if pd.isna(esp) or _clave(esp).startswith(('nota', 'fuente', 'elaboracion')):
            break
        filas.append((str(esp).strip(), pd.to_numeric(r.iloc[col_total], errors='coerce')))
    t = pd.DataFrame(filas, columns=['ESPECIE', 'VOLUMEN']).fillna({'VOLUMEN': 0})
    es_total = t.ESPECIE.map(_clave).eq('total')
    total, t = t.loc[es_total, 'VOLUMEN'].sum(), t[~es_total]
    if abs(t.VOLUMEN.sum() - total) > 0.01:
        AVISOS.append(f'{hoja}: la suma de especies ({t.VOLUMEN.sum():.3f}) no cuadra con el Total ({total:.3f})')
    return t


def corregir(esp):
    e = ' '.join(esp.split()).title()
    return CORRECCIONES.get(e, e)


def especie_ok(esp):
    oficial = {_clave(e): e for e in ESPECIES_07}
    if _clave(esp) in oficial:
        return oficial[_clave(esp)]
    return 'Otros'


def long_ornamentales(xls):
    """Peces ornamentales de la hoja POR ESPECIES (certificados de procedencia), una fila por especie y destino."""
    hoja = next(h for h in xls.sheet_names if _clave(h) == 'porespecies')
    d = pd.read_excel(xls, hoja, header=None)
    fila = next(i for i, v in d.iloc[:, 1].items() if _clave(v).startswith('nombrecomun'))
    unid = [j for j in range(d.shape[1]) if any(_clave(v) == 'unidades' for v in d.iloc[fila:fila + 4, j])]
    filas = []
    for _, r in d.iloc[fila + 1:].iterrows():
        if _clave(r.iloc[1]) == 'total':
            break
        if pd.isna(r.iloc[1]) or pd.isna(pd.to_numeric(r.iloc[unid[0]], errors='coerce')):
            continue
        u = [pd.to_numeric(r.iloc[j], errors='coerce') for j in unid]
        u = [0 if pd.isna(x) else x for x in u]
        if abs(u[0] - u[1] - u[2] - u[4]) > 0.5:
            AVISOS.append(f'{r.iloc[1]}: ingreso ({u[0]:,.0f}) distinto de egresos + stock')
        for k, destino in DESTINOS.items():
            if u[k]:
                filas.append((destino, ' '.join(str(r.iloc[1]).split()), ' '.join(str(r.iloc[2]).split()), u[k] / 1000))
    df = pd.DataFrame(filas, columns=['DESTINO', 'ESPECIE', 'ESPECIE_CORREGIDA', 'VOLUMEN'])
    df['ESTADO'], df['UNIDAD'] = 'ORNAMENTAL', 'miles de unidades'
    df['ESPECIE_OK'] = df['ESPECIE_CUADRO'] = 'Peces ornamentales'
    df['FUENTE'] = 'Certificados de procedencia'
    return df


def long_loreto(ruta, fuente='DESEMBARQUE'):
    """LONG de un crudo de DIREPRO Loreto: el de consumo humano directo o el de peces ornamentales."""
    xls = pd.ExcelFile(ruta)
    anio, mes = periodo_loreto(xls)
    if any(_clave(h) == 'porespecies' for h in xls.sheet_names):
        df = long_ornamentales(xls)
        df['VBP'] = df.VOLUMEN * PRECIOS['ORNAMENTAL']
        df['AÑO'], df['MES'], df['DEPARTAMENTO'] = anio, mes, 'LORETO'
        return df[LOR_COLUMNAS]
    partes = []
    for estado, _ in LOR_ESTADOS:
        t = _cuadro_loreto(xls, buscar_hoja(xls, fuente, estado))
        t['ESTADO'] = estado
        partes.append(t)
    df = pd.concat(partes, ignore_index=True)
    df['ESPECIE_CORREGIDA'] = df.ESPECIE.map(corregir)
    df['ESPECIE_OK'] = df.ESPECIE_CORREGIDA.map(especie_ok)
    df['ESPECIE_CUADRO'] = df.ESPECIE_OK.map(ESPECIES_CUADRO).fillna('Otros')
    df['VBP'] = df.VOLUMEN * df.ESTADO.map(PRECIOS)
    df['AÑO'], df['MES'], df['DEPARTAMENTO'] = anio, mes, 'LORETO'
    df['FUENTE'] = 'Desembarque' if fuente == 'DESEMBARQUE' else 'Extracción'
    df['DESTINO'], df['UNIDAD'] = None, 't'
    return df[LOR_COLUMNAS]


# ─── San Martín y Ucayali ───
# Especies nuevas (que no están en el histórico): especie principal por origen en San Martín; el resto va a "Otras"
SMN_PRINCIPALES = {'Acuicultura': {'CAMARÓN': 'Camarón gigante', 'GAMITANA': 'Gamitana', 'PACO': 'Paco',
                                   'PAICHE': 'Paiche', 'TILAPIA': 'Tilapia'},
                   'Extracción de ríos': {'BOQUICHICO': 'Boquichico'}}
SMN_ORIGEN = {'ACUICULTURA CONTINENTAL': 'Acuicultura', 'CONTINENTAL': 'Extracción de ríos',
              'MARÍTIMO': 'Extracción de ríos'}
SMN_ESTADOS = {'FRESCO': 'FRESCO', 'FRESCO REFRIGERADO': 'FRESCO', 'SALPRESO': 'SALPRESO', 'SECO SALADO': 'SECO SALADO'}
SMN_COLUMNAS = ['AÑO', 'MES', 'DEPARTAMENTO', 'ORIGEN', 'ESTADO', 'ESTADO_OK', 'ESPECIE', 'ESPECIE_OK', 'VOLUMEN', 'VBP']

# Ucayali: hoja del crudo por tipo, y precio de cada tipo (el agregado y los ornamentales no llevan VBP)
UCA_HOJAS = {'FRESCO': 'totalfresco', 'SECO-SALADO': 'totalsecosalado', 'ORNAMENTAL': 'ornamentales',
             'AGREGADO': 'totaldepescado'}
UCA_PRECIOS = {'FRESCO': PRECIOS['FRESCO'], 'SECO-SALADO': PRECIOS['SECO SALADO'], 'ORNAMENTAL': 0, 'AGREGADO': 0}
UCA_COLUMNAS = ['AÑO', 'MES', 'TIPO', 'ESPECIES', 'ESPECIES_CORREGIDO', 'ESPECIES_OK', 'VOLUMEN', 'VBP']


# ─── San Martín ───
def periodo_smn(ruta):
    """Año y mes del nombre del archivo (SMN_PESCA_2026-08.xlsx): el crudo de San Martín no los trae adentro."""
    m = re.search(r'(20\d{2})[-_ ]?(0[1-9]|1[0-2])(?!\d)', Path(ruta).stem)
    if m:
        return int(m.group(1)), int(m.group(2))
    raise ValueError(f'{Path(ruta).name}: el nombre debe traer el año y el mes (por ejemplo SMN_PESCA_2026-08.xlsx)')


def long_smn(ruta, historico=None):
    """LONG de un mes desde el crudo de DIREPRO San Martín (volúmenes en kg)."""
    xls = pd.ExcelFile(ruta)
    anio, mes = periodo_smn(ruta)
    d = pd.read_excel(xls, xls.sheet_names[0])
    d.columns = [_texto(c).upper() for c in d.columns]
    mapa = {}
    if historico is not None:
        mapa = {(o, _texto(e)): ok for o, e, ok in historico[['ORIGEN', 'ESPECIE', 'ESPECIE_OK']].drop_duplicates().values}
    filas = []
    for _, r in d.iterrows():
        proc, depto, esp = _texto(r['PROCEDENCIA']).upper(), r['DEPARTAMENTO'], _texto(r['ESPECIE'])
        if proc == 'TOTAL' or pd.isna(depto) or proc not in SMN_ORIGEN:
            continue
        depto = _texto(depto).upper()
        encabezado = int(pd.to_numeric(r['ENCABEZADO'], errors='coerce') or 0) == 1
        if depto == 'SAN MARTÍN' and not encabezado:          # especies de San Martín: solo celdas con volumen
            origen, especie = SMN_ORIGEN[proc], esp
            estados = [(e, r.get(e)) for e in SMN_ESTADOS if pd.to_numeric(r.get(e), errors='coerce') > 0]
            dep = 'SAN MARTÍN'
        elif depto != 'SAN MARTÍN' and encabezado:             # lo que llega de otros departamentos: su total
            origen, especie, dep = 'Extracción de ríos', proc, 'Otros'
            estados = [(e, r.get(e)) for e in SMN_ESTADOS]
        else:
            continue
        for estado, kg in estados:
            filas.append((dep, origen, estado, especie, (pd.to_numeric(kg, errors='coerce') or 0) / 1000))
    df = pd.DataFrame(filas, columns=['DEPARTAMENTO', 'ORIGEN', 'ESTADO', 'ESPECIE', 'VOLUMEN']).fillna({'VOLUMEN': 0})
    df['ESTADO_OK'] = df.ESTADO.map(SMN_ESTADOS)
    df['ESPECIE_OK'] = [mapa.get((o, e)) or SMN_PRINCIPALES.get(o, {}).get(e.upper(), 'Otras')
                        for o, e in zip(df.ORIGEN, df.ESPECIE)]
    df['VBP'] = df.VOLUMEN * df.ESTADO_OK.map(PRECIOS) * df.DEPARTAMENTO.eq('SAN MARTÍN')
    df['AÑO'], df['MES'] = anio, mes
    nuevas = sorted({e for o, e in zip(df.ORIGEN, df.ESPECIE) if mapa and (o, e) not in mapa})
    if nuevas:
        AVISOS.append(f'Pesca San Martín: especies que no estaban en el histórico: {", ".join(nuevas)}.')
    return df[SMN_COLUMNAS]


# ─── Ucayali ───
def _cuadro_uca(xls, hoja):
    """Especie × mes de un cuadro de DIREPRO Ucayali (fila ESPECIES con las fechas AAAA-MM-01)."""
    d = pd.read_excel(xls, hoja, header=None)
    f, c = next((i, j) for i in range(15) for j in range(3) if _texto(d.iat[i, j]).upper() == 'ESPECIES')
    meses = {}
    for j, v in d.iloc[f].items():
        m = re.match(r'(20\d{2})-(\d{2})', str(v))
        if m:
            meses[j] = (int(m.group(1)), int(m.group(2)))
    filas = []
    for i in range(f + 1, len(d)):
        esp = d.iat[i, c]
        if pd.isna(esp) or _texto(esp).upper().startswith('TOTAL'):
            break
        for j, (a, m) in meses.items():
            filas.append((a, m, _texto(esp), pd.to_numeric(d.iat[i, j], errors='coerce')))
    return pd.DataFrame(filas, columns=['AÑO', 'MES', 'ESPECIES', 'VOLUMEN']).fillna({'VOLUMEN': 0})


def long_uca(ruta, historico=None):
    """LONG del año desde el crudo acumulado de DIREPRO Ucayali (toneladas; ornamentales en unidades)."""
    xls = pd.ExcelFile(ruta)
    mapa = {}
    if historico is not None:
        h = historico.assign(E=historico.ESPECIES.map(_texto))
        mapa = {(t, e): (c, ok) for t, e, c, ok in
                h[['TIPO', 'E', 'ESPECIES_CORREGIDO', 'ESPECIES_OK']].drop_duplicates(['TIPO', 'E']).values}
    partes, nuevas = [], set()
    for tipo, clave in UCA_HOJAS.items():
        hoja = next((h for h in xls.sheet_names if _clave(h) == clave), None)
        if hoja is None:
            raise ValueError(f'No se encontró la hoja de {tipo} en {Path(ruta).name}')
        t = _cuadro_uca(xls, hoja)
        if tipo == 'ORNAMENTAL':
            t = t[t.VOLUMEN != 0]
        t['TIPO'] = tipo
        defecto = lambda e: (e.title(), e.title() if tipo in ('SECO-SALADO', 'ORNAMENTAL') else 'Otros')
        pares = [mapa.get((tipo, e)) or defecto(e) for e in t.ESPECIES]
        nuevas |= {(tipo, e) for e in t.ESPECIES if mapa and (tipo, e) not in mapa}
        t['ESPECIES_CORREGIDO'], t['ESPECIES_OK'] = [p[0] for p in pares], [p[1] for p in pares]
        t['VBP'] = t.VOLUMEN * UCA_PRECIOS[tipo]
        partes.append(t)
    if nuevas:
        AVISOS.append('Pesca Ucayali: especies que no estaban en el histórico: ' + ', '.join(f'{e} ({t})' for t, e in sorted(nuevas)) + '.')
    return pd.concat(partes, ignore_index=True)[UCA_COLUMNAS]


# ─── Lectura para el API ───
BASE_DE_HOJA_LONG = {'lorpesca': 'pesca-loreto', 'smnpesca': 'pesca-san-martin', 'ucapesca': 'pesca-ucayali',
                     'pescasmn': 'pesca-san-martin', 'pescauca': 'pesca-ucayali'}   # las dos últimas: bases históricas
MES_TEXTO = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'set': 9, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}


def historico_a_long(base_id, df):
    """Las bases históricas de la sucursal (hojas PESCA_SMN 2006-2022 y PESCA_UCA 2010-2025) al formato del LONG:
    mes «Ene.»/«Feb» a número, VBP a precios de 2007 y los nombres de estado, origen y especie del crudo."""
    df = df.rename(columns=lambda c: _texto(c).upper())
    df['MES'] = [int(m) if str(m).strip().isdigit() else MES_TEXTO.get(_clave(m)[:3]) for m in df['MES']]
    df = df[df['MES'].notna()].copy()
    df['VOLUMEN'] = pd.to_numeric(df['VOLUMEN'], errors='coerce').fillna(0)
    if base_id == 'pesca-san-martin':
        df['ESTADO'] = df['ESTADO'].map(lambda e: _texto(str(e).replace(' - ', '')).upper().replace('SECO-SALADO', 'SECO SALADO'))
        df['ORIGEN'] = df['ORIGEN'].replace({'Otros': 'Extracción de ríos'})          # lo que llega de otros dptos., como en el crudo
        for c in ('ESPECIE', 'ESPECIE_OK'):
            df[c] = df[c].replace({'Camarón': 'Camarón gigante'})
        df['ESPECIE_OK'] = df['ESPECIE_OK'].replace({'Varios': 'Otras'})
        df['VBP'] = df.VOLUMEN * df.ESTADO_OK.map(PRECIOS).fillna(0) * df.DEPARTAMENTO.eq('SAN MARTÍN')
        return df[SMN_COLUMNAS]
    df['ESPECIES_CORREGIDO'] = df['ESPECIES'].map(lambda e: _texto(e).title() if str(e).isupper() else _texto(e))
    df['VBP'] = df.VOLUMEN * df.TIPO.map(UCA_PRECIOS).fillna(0)
    return df[UCA_COLUMNAS]
DEPTO = {'pesca-loreto': '16', 'pesca-san-martin': '22', 'pesca-ucayali': '25'}
COLUMNAS = {'pesca-loreto': LOR_COLUMNAS, 'pesca-san-martin': SMN_COLUMNAS, 'pesca-ucayali': UCA_COLUMNAS}
NUMERICAS = {'AÑO', 'MES', 'VOLUMEN', 'VBP'}


def reconocer(ruta):
    """(base_id, hoja del LONG o None si es un crudo) para un .xlsx de pesca; None si no es de pesca."""
    xls = pd.ExcelFile(ruta)
    hojas = {_clave(h): h for h in xls.sheet_names}
    for clave, base_id in BASE_DE_HOJA_LONG.items():
        # el crudo de San Martín también tiene una hoja SMN_PESCA: el LONG se distingue por sus columnas
        if clave in hojas and {'AÑO', 'MES', 'VOLUMEN'} <= {_texto(c).upper() for c in pd.read_excel(xls, hojas[clave], nrows=0).columns}:
            return base_id, hojas[clave]
    if 'porespecies' in hojas or sum(h.startswith('desemb') for h in hojas) >= 3:
        return 'pesca-loreto', None
    if all(c in hojas for c in UCA_HOJAS.values()):
        return 'pesca-ucayali', None
    columnas = {_texto(c).upper() for c in pd.read_excel(xls, sheet_name=0, nrows=0).columns}
    if {'PROCEDENCIA', 'ENCABEZADO', 'ESPECIE'} <= columnas:
        return 'pesca-san-martin', None
    return None


def _recortar_meses_sin_datos(df):
    """Ucayali trae los 12 meses del año; los que siguen al último mes con datos (todo en cero) no se guardan."""
    con_datos = df[df.VOLUMEN.fillna(0) != 0].groupby('AÑO').MES.max()
    return df[df.MES <= df['AÑO'].map(con_datos).fillna(0)]


def _internas(base_id, df, n_archivo):
    df = df[COLUMNAS[base_id]].copy()
    for c in df.columns:
        if c in NUMERICAS:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        else:                                   # texto siempre como texto (una columna vacía no debe volverse número)
            df[c] = [None if pd.isna(v) else str(v) for v in df[c]]
    df['AÑO'], df['MES'] = df['AÑO'].astype(int), df['MES'].astype(int)
    if base_id == 'pesca-ucayali':
        df = _recortar_meses_sin_datos(df)
    df['_anio'], df['_mes'], df['_depto'] = df['AÑO'], df['MES'], DEPTO[base_id]
    # Loreto: el consumo y los ornamentales llegan en archivos distintos y se reemplazan por separado
    df['_nivel'] = (df.ESTADO.eq('ORNAMENTAL').map({True: 'ORNAMENTAL', False: 'CONSUMO'})
                    if base_id == 'pesca-loreto' else '')
    df['_archivo'] = n_archivo
    return df


def leer(archivos, historico):
    """archivos: [(n_archivo, ruta, base_id, hoja_long)] · historico(base_id) -> LONG ya guardado en la base de datos.
    -> {base_id: DataFrame con columnas internas}, avisos. Un crudo gana a un LONG que traiga el mismo periodo."""
    AVISOS.clear()
    partes, longs = {}, {}
    for n, ruta, base_id, hoja in archivos:
        if hoja:
            df = pd.read_excel(ruta, sheet_name=hoja)
            if _clave(hoja) in ('pescasmn', 'pescauca'):
                df = historico_a_long(base_id, df)
            faltan = [c for c in COLUMNAS[base_id] if c not in df.columns]
            if faltan:
                AVISOS.append(f'{Path(ruta).name}: faltan las columnas {", ".join(faltan)}; no se cargó.')
                continue
            longs.setdefault(base_id, []).append(df)
            partes.setdefault(base_id, []).append(_internas(base_id, df, n))
    for n, ruta, base_id, hoja in archivos:
        if hoja:
            continue
        try:
            if base_id == 'pesca-loreto':
                df = long_loreto(ruta)
            else:
                previo = [historico(base_id)] + longs.get(base_id, [])
                previo = pd.concat([p for p in previo if p is not None and len(p)], ignore_index=True) if any(
                    p is not None and len(p) for p in previo) else None
                df = (long_smn if base_id == 'pesca-san-martin' else long_uca)(ruta, previo)
        except (ValueError, KeyError, StopIteration) as e:
            AVISOS.append(f'{Path(ruta).name}: no se pudo leer como crudo de pesca ({e}); se ignoró.')
            continue
        partes.setdefault(base_id, []).append(_internas(base_id, df, 100_000 + n))
    return {b: pd.concat(p, ignore_index=True) for b, p in partes.items()}, list(AVISOS)
