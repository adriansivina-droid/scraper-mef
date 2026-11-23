"""Zip simple de «Ríos del Perú» (SENAMHI) para bajar y graficar: dos Excel (nivel y caudal diario, y estaciones) y un LEEME.txt corto.

Se escribe por filas (xlsxwriter en modo constant_memory): la serie diaria llega a cientos de miles de filas.
"""
import csv
import os
import zipfile
from datetime import datetime

import xlsxwriter

MAX_FILAS_EXCEL = 1_048_575                      # una hoja de Excel admite 1 048 576 filas, una es el encabezado
DECIMALES = {"VALOR", "MINIMO", "MAXIMO", "PROM_HISTORICO", "UMBRAL_ROJO", "UMBRAL_NARANJA", "UMBRAL_AMARILLO", "LATITUD", "LONGITUD"}
FECHAS = {"FECHA"}

# (clave de hidrologia.ARCHIVOS, archivo, columnas que se dejan)
PAQUETE = [
    ("diario", "Nivel_y_caudal_diario.xlsx",
     ["COD_ESTACION", "ESTACION", "RIO", "VARIABLE", "UNIDAD", "FECHA", "VALOR", "MINIMO", "MAXIMO", "PROM_HISTORICO",
      "UMBRAL_ROJO", "UMBRAL_NARANJA", "UMBRAL_AMARILLO", "DATO_DUDOSO"]),
    ("estaciones", "Estaciones.xlsx",
     ["COD_ESTACION", "ESTACION", "RIO", "DEPARTAMENTO", "DIRECCION_ZONAL", "VARIABLES_CON_DATOS", "LATITUD", "LONGITUD"]),
]


def _celda(col, v):
    if v == "":
        return None
    if col in DECIMALES:
        try:
            return float(v)
        except ValueError:
            return v
    if col in FECHAS:
        try:
            return datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            return v
    return v


def _excel(csv_ruta, destino, columnas):
    """Un CSV → un .xlsx de una sola hoja «Datos» (con «Datos 2», … si pasa del máximo de filas). Devuelve las filas escritas."""
    libro = xlsxwriter.Workbook(destino, {"constant_memory": True, "strings_to_numbers": False, "strings_to_formulas": False, "strings_to_urls": False})
    cab = libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#111149"})
    fecha = libro.add_format({"num_format": "dd/mm/yyyy"})
    escritas, hoja, fila_h = 0, None, 0
    with open(csv_ruta, encoding="utf-8-sig", newline="") as f:
        lector = csv.reader(f)
        encabezado = next(lector)
        idx = [encabezado.index(c) for c in columnas if c in encabezado]
        nombres = [encabezado[i] for i in idx]

        def nueva():
            h = libro.add_worksheet("Datos" if escritas == 0 else f"Datos {escritas // MAX_FILAS_EXCEL + 1}")
            for j, c in enumerate(nombres):
                h.write(0, j, c, cab)
                h.set_column(j, j, 28 if c in ("ESTACION", "RIO") else 16 if c in ("FECHA", "VARIABLES_CON_DATOS", "DIRECCION_ZONAL") else 14, fecha if c in FECHAS else None)
            h.freeze_panes(1, 0)
            return h
        for fila in lector:
            if hoja is None or fila_h > MAX_FILAS_EXCEL:
                if hoja is not None:
                    hoja.autofilter(0, 0, fila_h - 1, len(nombres) - 1)
                hoja = nueva(); fila_h = 1
            for j, i in enumerate(idx):
                x = _celda(nombres[j], fila[i])
                if x is None:
                    continue
                hoja.write_datetime(fila_h, j, x, fecha) if isinstance(x, datetime) else hoja.write(fila_h, j, x)
            fila_h += 1; escritas += 1
    if hoja is None:
        hoja = nueva(); fila_h = 1
    hoja.autofilter(0, 0, max(fila_h - 1, 1), len(nombres) - 1)
    libro.close()
    return escritas


def leeme(hoy_txt, resumen, desde_txt=""):
    r = resumen or {}
    ult = r.get("ultima_fecha") or ""
    ult = f"{ult[8:10]}/{ult[5:7]}/{ult[:4]}" if ult else ""
    return f"""NIVEL Y CAUDAL DE LOS RÍOS DEL PERÚ (SENAMHI) · {hoy_txt}

Nivel y caudal diario de las estaciones de SENAMHI{f", {desde_txt}" if desde_txt else ""}{f", hasta el {ult}" if ult else ""}.

ARCHIVOS
  Nivel_y_caudal_diario.xlsx   Una fila por estación, variable y día.
  Estaciones.xlsx              Una fila por estación: río, departamento y coordenadas.

PARA HACER UN GRÁFICO
  Filtra Nivel_y_caudal_diario.xlsx por ESTACION y por VARIABLE (NIVEL o CAUDAL), y grafica FECHA contra VALOR.

COLUMNAS
  COD_ESTACION      Código de la estación (texto). Une los dos archivos.
  ESTACION, RIO     Nombre de la estación y del río.
  VARIABLE          NIVEL o CAUDAL.
  UNIDAD            m.s.n.m o m (nivel); m3/s (caudal).
  FECHA             Día del dato.
  VALOR             Valor del día. Vacío = sin dato.
  MINIMO, MAXIMO    Mínimo y máximo del día (no todas las filas los traen).
  PROM_HISTORICO    Promedio histórico de SENAMHI para ese día del año.
  UMBRAL_ROJO, UMBRAL_NARANJA, UMBRAL_AMARILLO   Umbrales de alerta de la estación, en la unidad del valor.
  DATO_DUDOSO       «SI» = pico aislado imposible en un río. No se borró: decide si lo excluyes.
  DEPARTAMENTO, DIRECCION_ZONAL, LATITUD, LONGITUD   Ubicación (departamento solo en las estaciones principales).
  VARIABLES_CON_DATOS   Qué variables tiene la estación.

Fuente: SENAMHI, Monitoreo Hidrológico. Datos en tiempo casi real, sujetos a revisión.
"""


def armar_paquete(carpeta_csv, destino, resumen, hoy_txt, archivos, desde_txt=""):
    """Escribe en «destino» (.zip) el paquete. «archivos»: {clave: nombre del CSV}. Devuelve {clave: filas}."""
    base = f"SENAMHI_Rios_del_Peru_{datetime.strptime(hoy_txt, '%d/%m/%Y'):%Y-%m-%d}"
    tmp = destino + ".d"
    os.makedirs(tmp, exist_ok=True)
    filas = {}
    try:
        for clave, archivo, columnas in PAQUETE:
            ruta = os.path.join(carpeta_csv, archivos[clave])
            if os.path.exists(ruta):
                filas[clave] = _excel(ruta, os.path.join(tmp, archivo), columnas)
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.writestr(f"{base}/LEEME.txt", "﻿" + leeme(hoy_txt, resumen, desde_txt))
            for _, archivo, _c in PAQUETE:
                if os.path.exists(os.path.join(tmp, archivo)):
                    z.write(os.path.join(tmp, archivo), f"{base}/{archivo}")
    finally:
        for n in os.listdir(tmp):
            os.remove(os.path.join(tmp, n))
        os.rmdir(tmp)
    return filas
