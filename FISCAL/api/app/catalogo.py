"""Catálogo de bases que sirve el API: las mismas que producen los scrapers de FISCAL/ (CONTEXTO_PROYECTO §7 y §12)."""
from dataclasses import dataclass, field

DEPARTAMENTOS = {
    "01": "AMAZONAS", "02": "ÁNCASH", "03": "APURÍMAC", "04": "AREQUIPA", "05": "AYACUCHO", "06": "CAJAMARCA",
    "07": "CALLAO", "08": "CUSCO", "09": "HUANCAVELICA", "10": "HUÁNUCO", "11": "ICA", "12": "JUNÍN",
    "13": "LA LIBERTAD", "14": "LAMBAYEQUE", "15": "LIMA", "16": "LORETO", "17": "MADRE DE DIOS", "18": "MOQUEGUA",
    "19": "PASCO", "20": "PIURA", "21": "PUNO", "22": "SAN MARTÍN", "23": "TACNA", "24": "TUMBES", "25": "UCAYALI",
    "98": "EXTERIOR", "99": "SIN DEPARTAMENTO",
}

# nivel de la URL -> código MEF (el que guardan los CSV en NIVEL_GOBIERNO y el nombre corto de sus archivos)
NIVELES = {"nacional": "E", "regional": "R", "locales": "M"}
NIVEL_DE_CORTO = {"GobNacional": "E", "GobRegional": "R", "Municipalidad": "M"}
NIVEL_MEF = {"E": "E: GOBIERNO NACIONAL", "R": "R: GOBIERNOS REGIONALES", "M": "M: GOBIERNOS LOCALES"}
NIVEL_PIM = {"E": "GOBIERNO NACIONAL", "R": "GOBIERNOS REGIONALES", "M": "GOBIERNOS LOCALES"}

GRUPOS = {"inversion": "Inversión · genérica 2.6", "gasto": "Gasto total · todas las genéricas",
          "pesca": "Pesca · DIREPRO, VBP a precios de 2007",
          "empleo": "Empleo · MTPE, Planilla Electrónica",
          "hidrocarburos": "Hidrocarburos · PERUPETRO",
          "comercio": "Exportaciones e importaciones · ESTAD"}


@dataclass(frozen=True)
class Base:
    id: str
    grupo: str
    etiqueta: str            # cómo se lista dentro de su grupo
    nombre: str              # nombre único (resúmenes, avisos)
    hoja: str                # hoja del Excel (máx. 31 caracteres)
    columnas: list = field(default_factory=list)
    anchos: list = field(default_factory=list)   # anchos de columna, como PIM_Funcion.xlsx
    valor: str = "DEVENGADO"
    periodicidad: str = "mensual"
    usa_niveles: bool = True
    descripcion: str = ""
    departamentos: tuple = ()                   # si la base es de algunos departamentos (vacío: todos)
    formato_valor: str = "#,##0"
    reemplaza_periodo: bool = False             # cada carga trae la serie completa: reemplaza el periodo en todos los departamentos

    @property
    def tabla(self):
        return "base_" + self.id.replace("-", "_")


BASES = {b.id: b for b in [
    Base("inv-dev-funcion", "inversion", "Devengado por función", "Inversión por función", "INV Funciones",
         ["AÑO", "MES", "NIVEL_GOBIERNO", "DEPARTAMENTO", "ENTIDAD", "FUNCION", "DEVENGADO"], [8, 12, 24, 16, 28, 50, 13],
         descripcion="Devengado de la genérica 2.6 por mes, departamento (Meta), nivel de gobierno y función. "
                     "En locales es la suma de las municipalidades."),
    Base("inv-dev-municipalidad", "inversion", "Devengado por municipalidad", "Inversión por municipalidad", "INV Municipalidades",
         ["AÑO", "MES", "DEPARTAMENTO", "FUNCION", "MUNICIPALIDAD", "DEVENGADO"], [9.7, 12, 20, 54.6, 52, 14],
         usa_niveles=False, descripcion="Devengado de la genérica 2.6 por mes, función y municipalidad."),
    Base("inv-dev-fuente", "inversion", "Devengado por fuente de financiamiento", "Inversión por fuente", "INV Fuentes",
         ["AÑO", "MES", "NIVEL_GOBIERNO", "DEPARTAMENTO", "GENERICA", "COD_FUENTE", "FUENTE", "DEVENGADO"], [9.7, 12, 26, 20, 10, 12, 44, 14],
         descripcion="Devengado de la genérica 2.6 por mes, nivel de gobierno y fuente de financiamiento."),
    Base("inv-pim-funcion", "inversion", "PIM por función", "PIM por función", "PIM Funciones",
         ["AÑO", "DEPARTAMENTO", "NIVEL DE GOBIERNO", "FUNCION", "PIM"], [9.7, 41.6, 23.6, 54.6, 12.3],
         valor="PIM", periodicidad="anual", descripcion="PIM anual de la genérica 2.6 por departamento, nivel de gobierno y función."),
    Base("inv-pim-municipalidad", "inversion", "PIM por municipalidad", "PIM por municipalidad", "PIM Municipalidades",
         ["AÑO", "DEPARTAMENTO", "FUNCION", "MUNICIPALIDAD", "PIM"], [9.7, 41.6, 54.6, 52, 12.3],
         valor="PIM", periodicidad="anual", usa_niveles=False, descripcion="PIM anual de la genérica 2.6 por función y municipalidad."),
    Base("gasto-dev-generica", "gasto", "Devengado por genérica (incluye la deuda desglosada)", "Gasto por genérica", "GASTO Genéricas",
         ["AÑO", "MES", "NIVEL_GOBIERNO", "DEPARTAMENTO", "COD_GENERICA", "GENERICA", "DESGLOSE", "DEVENGADO"], [8, 12, 24, 16, 14, 46, 24, 14],
         descripcion="Devengado de todas las genéricas. La 2.8 Servicio de la deuda viene en AMORTIZACIÓN e INTERESES Y "
                     "COMISIONES, así la suma de la hoja sigue siendo el gasto total."),
    Base("gasto-dev-fuente", "gasto", "Devengado por fuente de financiamiento", "Gasto por fuente", "GASTO Fuentes",
         ["AÑO", "MES", "NIVEL_GOBIERNO", "DEPARTAMENTO", "GENERICA", "COD_FUENTE", "FUENTE", "DEVENGADO"], [9.7, 12, 26, 20, 10, 12, 44, 14],
         descripcion="Devengado total (todas las genéricas) por mes, nivel de gobierno y fuente de financiamiento."),
    # Proyectos detrás de las variaciones (FISCAL/Fiscal_Proyectos.ipynb, en GitHub Actions tras el scraper del MEF)
    Base("inv-proyectos", "inversion", "Proyectos detrás de las variaciones", "Proyectos de inversión", "PROYECTOS",
         ["AÑO", "MES", "DEPARTAMENTO", "NIVEL_GOBIERNO", "DIFERENCIA_NIVEL", "MES_CONSULTADO", "N_FUNCION", "FUNCION", "ANTERIOR",
          "ACTUAL", "DIFERENCIA_FUNCION", "N_PROYECTO", "CODIGO", "PROYECTO", "DEVENGADO", "PCT_FUNCION"],
         [8, 6, 16, 22, 16, 12, 8, 40, 14, 14, 14, 8, 12, 80, 14, 10], departamentos=("16", "22", "25"),
         descripcion="Por departamento y nivel: las 5 funciones que más explican la variación de la inversión del mes contra el "
                     "mismo mes del año anterior y sus 5 proyectos con mayor devengado (Consulta Amigable, nivel proyecto)."),
    # Pesca (PESCA/pesca.md): el LONG de cada región, con sus columnas; VBP en miles de soles de 2007
    Base("pesca-loreto", "pesca", "Loreto · desembarque y peces ornamentales", "Pesca Loreto", "PESCA Loreto",
         ["AÑO", "MES", "DEPARTAMENTO", "FUENTE", "ESTADO", "DESTINO", "ESPECIE", "ESPECIE_CORREGIDA", "ESPECIE_OK",
          "ESPECIE_CUADRO", "UNIDAD", "VOLUMEN", "VBP"], [8, 6, 12, 26, 14, 28, 30, 30, 22, 20, 18, 12, 12],
         valor="VBP", usa_niveles=False, departamentos=("16",), formato_valor="#,##0.000",
         descripcion="DIREPRO Loreto: desembarque por estado y especie (t) y peces ornamentales por destino (miles de unidades)."),
    Base("pesca-san-martin", "pesca", "San Martín · producción por origen y estado", "Pesca San Martín", "PESCA San Martín",
         ["AÑO", "MES", "DEPARTAMENTO", "ORIGEN", "ESTADO", "ESTADO_OK", "ESPECIE", "ESPECIE_OK", "VOLUMEN", "VBP"],
         [8, 6, 14, 20, 22, 14, 22, 18, 12, 12], valor="VBP", usa_niveles=False, departamentos=("22",), formato_valor="#,##0.000",
         descripcion="DIREPRO San Martín: volumen (t) por origen, estado y especie; lo que llega de otros departamentos va como Otros."),
    Base("pesca-ucayali", "pesca", "Ucayali · desembarque y peces ornamentales", "Pesca Ucayali", "PESCA Ucayali",
         ["AÑO", "MES", "TIPO", "ESPECIES", "ESPECIES_CORREGIDO", "ESPECIES_OK", "VOLUMEN", "VBP"],
         [8, 6, 14, 30, 30, 22, 12, 12], valor="VBP", usa_niveles=False, departamentos=("25",), formato_valor="#,##0.000",
         descripcion="DIREPRO Ucayali: desembarque fresco, seco salado y total (t) y peces ornamentales (unidades)."),
    # Empleo (EMPLEO/empleo.md): trabajadores asalariados privados formales por región y actividad
    Base("empleo", "empleo", "Trabajadores asalariados privados formales", "Empleo", "EMPLEO",
         ["AÑO", "MES", "REGIÓN", "ACTIVIDAD_ECONOMICA", "EMPLEO"], [8, 6, 20, 24, 12], valor="EMPLEO", usa_niveles=False,
         descripcion="MTPE (PLAME y T-Registro): trabajadores asalariados privados formales por mes, región y actividad económica."),
    # Hidrocarburos (HIDROCARBUROS/perupetro_produccion.md): los CSV que el flujo diario deja en Drive (DATA)
    Base("hidro-produccion", "hidrocarburos", "Producción fiscalizada por lote", "Producción de hidrocarburos", "HIDROCARBUROS",
         ["AÑO", "MES", "DEPARTAMENTO", "ZONA", "OPERADOR", "LOTE", "LOTE_HISTORICO", "PRODUCTO", "UNIDAD", "VOLUMEN", "PROMEDIO_DIARIO", "FUENTE"],
         [8, 6, 18, 14, 28, 10, 14, 14, 10, 14, 14, 34], valor="VOLUMEN", usa_niveles=False, reemplaza_periodo=True,
         descripcion="PERUPETRO: petróleo, LGN y condensado (barriles) y gas natural (MPC) fiscalizados por mes, lote y operador. "
                     "Los meses que la estadística mensual aún no publica salen de la producción diaria."),
    Base("hidro-canon", "hidrocarburos", "Canon y sobrecanon petrolero transferido", "Canon petrolero", "CANON PETROLERO",
         ["AÑO", "MES", "DEPARTAMENTO", "CANON_MM_SOLES"], [8, 6, 18, 16], valor="CANON_MM_SOLES", usa_niveles=False,
         reemplaza_periodo=True, formato_valor="#,##0.00",
         descripcion="PERUPETRO: canon y sobrecanon petrolero transferido a cada departamento por mes (millones de soles)."),
    # Exportaciones (EXPORT/info_export.md): el ESTAD de cada región, en largo; FOB en miles de US$
    Base("expo-estad", "comercio", "Exportaciones por grupo de productos (ESTAD)", "Exportaciones", "EXPORTACIONES",
         ["AÑO", "MES", "DEPARTAMENTO", "ORDEN", "NIVEL", "TIPO", "GRUPO", "RUBRO", "FOB"], [8, 6, 14, 8, 10, 30, 28, 32, 12],
         valor="FOB", usa_niveles=False, departamentos=("16", "22", "25"),
         descripcion="ESTAD de Loreto (15.Export), San Martín (14.XLS) y Ucayali (15.XLS): exportaciones FOB por mes y fila del "
                     "cuadro (total, tipo, grupo y producto), en miles de US$."),
    Base("impo-estad", "comercio", "Importaciones por uso o destino (ESTAD, aduana de Iquitos)", "Importaciones", "IMPORTACIONES",
         ["AÑO", "MES", "DEPARTAMENTO", "ORDEN", "NIVEL", "TIPO", "GRUPO", "RUBRO", "FOB"], [8, 6, 14, 8, 10, 30, 28, 34, 12],
         valor="FOB", usa_niveles=False, departamentos=("16",),
         descripcion="ESTAD de Loreto (16.Import): importaciones FOB por la aduana de Iquitos según uso o destino económico, "
                     "en miles de US$."),
    # Base mensual de SUNAT procesada en la página (sunat_expo.py): una fila por declaración, con su estado
    Base("expo-sunat", "comercio", "Base mensual de exportaciones (detalle por declaración)", "Exportaciones · base mensual", "BASE MENSUAL",
         ["AÑO", "MES", "DEPARTAMENTO", "RUC", "EMPRESA", "PARTIDA", "DESCRIPCION", "PRODUCTO", "TIPO", "CATEGORIA",
          "TIPO_ESTAD", "RUBRO_ESTAD", "COD_PAIS", "PAIS", "CONTINENTE", "COD_ADUANA", "ADUANA", "FECHA_EMBARQUE", "KILOS",
          "CANTIDAD", "UNIDAD", "BORRAR_PARA", "ESTADO", "MOTIVO", "FOB_USD", "FOB"],
         [8, 6, 14, 13, 40, 12, 50, 28, 28, 28, 28, 26, 8, 20, 12, 8, 20, 10, 10, 10, 8, 14, 11, 40, 14, 10],
         valor="FOB", usa_niveles=False, departamentos=("16", "22", "25"),
         descripcion="Base mensual de exportaciones con los diccionarios de ANUAL_PRO (producto, categoría, país, aduana, empresa) y el "
                     "estado de cada fila: ok (entra a los cuadros), verificar, borrar o clasificar. FOB en miles de US$ "
                     "(ROUND por fila, como la hoja ORIGEN); FOB_USD sin redondear."),
    # Base mensual de importaciones por la aduana de Iquitos (sunat_impo.py)
    Base("impo-base", "comercio", "Base mensual de importaciones (aduana de Iquitos, detalle)", "Importaciones · base mensual", "BASE MENSUAL IMPO",
         ["AÑO", "MES", "DEPARTAMENTO", "ADUANA", "RUC", "EMPRESA", "PARTIDA", "PRODUCTO", "COD_CUODE", "TIPO", "CATEGORIA",
          "DESC_CUODE", "RUBRO_ESTAD", "COD_PAIS", "PAIS", "CONTINENTE", "KILOS", "FLETE", "SEGURO", "CIF", "ESTADO", "MOTIVO",
          "FOB_USD", "FOB"],
         [8, 6, 12, 8, 13, 40, 12, 32, 9, 20, 32, 34, 30, 8, 18, 12, 10, 10, 10, 12, 11, 30, 12, 10],
         valor="FOB", usa_niveles=False, departamentos=("16",),
         descripcion="Importaciones de la aduana de Iquitos con la clasificación del proyecto ANUAL_PRO - IMPORTACIONES (CUODE o "
                     "partida manual), empresa, producto y país. FOB en miles de US$ (ROUND por fila, como el CUADRO 16)."),
]}

# columnas internas para filtrar (no salen en las descargas)
INTERNAS = ["_anio", "_mes", "_depto", "_nivel"]
