"""Arma los archivos de descarga. El Excel copia el formato de PIM_Funcion.xlsx: una hoja plana por base, encabezados
centrados en la fila 1, montos con separador de miles y los mismos anchos de columna."""
import io
import zipfile

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment

from .catalogo import BASES


def excel(tablas):
    """tablas: {base_id: DataFrame} en el orden del catálogo -> bytes del .xlsx. En modo de solo escritura (va directo a
    un archivo temporal): con el modo normal, 180 mil filas (DEV Función·Municipalidad, 25 departamentos, dos años)
    pasaban de 450 MB y Render reiniciaba el servicio (502)."""
    wb = Workbook(write_only=True)
    centro = Alignment(horizontal="center")
    for base_id, df in tablas.items():
        b = BASES[base_id]
        ws = wb.create_sheet(b.hoja)
        for i, ancho in enumerate(b.anchos):                  # los anchos van antes de la primera fila
            ws.column_dimensions[chr(65 + i)].width = ancho
        cab = []
        for c in b.columnas:
            celda = WriteOnlyCell(ws, value=c)
            celda.alignment = centro
            cab.append(celda)
        ws.append(cab)
        j = b.columnas.index(b.valor)
        for fila in df.itertuples(index=False):
            fila = list(fila)
            v = fila[j]
            celda = WriteOnlyCell(ws, value=None if v is None or (isinstance(v, float) and v != v) else v)
            celda.number_format = b.formato_valor
            fila[j] = celda
            ws.append([None if (isinstance(x, float) and x != x) else x for x in fila[:j]] + [celda] + fila[j + 1:])
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def zip_csv(tablas, nombre_de):
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for base_id, df in tablas.items():
            z.writestr(nombre_de(base_id), csv(df))
    return salida.getvalue()
