"""Genera HIDROCARBUROS/PP_MEF_Canon_Municipal.ipynb (python3 mk_nb_mef.py <salida.ipynb>).
El notebook embebe lector_mef_url.py (lectura por URL con requests, como los scrapers de FISCAL/)."""
import json, os, sys
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lector_mef_url.py"), encoding="utf-8") as fh:
    lector = fh.read()

md = """# 🏛️ MEF · Canon y sobrecanon petrolero recaudado por cada municipalidad (2005–hoy)

PERUPETRO publica el canon **por municipalidad** solo en 1993–2002 (Excel de Distribución) y el año en curso (Excel de Canon Municipalidades). Desde 2003 entrega el total municipal a un intermediario (CND hasta 2006; PCM desde 2007), que hace el reparto. Este notebook completa los años que faltan con el **MEF – Consulta Amigable de Ingresos** (`apps5.mineco.gob.pe/transparenciaingresos/mensual/`), monto **recaudado** por cada municipalidad.

**Cómo lee la consulta:** igual que los scrapers de `FISCAL/` (gasto): la ruta va **en la URL** (`Navegar_N.aspx?…&0=&10=<fuente>&11=<tipo>&…&y=AAAA`), con `requests`, sin navegador. La primera clave vacía es la que se lista. Claves conocidas por el `exportUrl` de la página: 10 fuente, 11 tipo de recurso, 2 sector; las demás (rubro, nivel de gobierno, departamento, municipalidad) **se descubren solas** probando claves y leyendo la cabecera de la tabla, y cada filtro se valida con el breadcrumb.

- **Desde 2007**: fuente 5 (Recursos determinados) → rubro 18 → tipos «5: Canon y sobrecanon petrolero» y «K: Sub cuenta – …» (se suman) → gobiernos locales → departamento → municipalidad.
- **2005–2006**: fuente 01 (Canon y sobrecanon) → tipo de recurso; el detalle municipal solo está en «0: NORMAL», que reúne **todos** los canones. Con `SI_NO_HAY_PETROLERO = "Usar NORMAL"` se toma ese tipo y queda rotulado «todos los canones» en el CSV y en el mapa.
- **2003–2004**: sin detalle por municipalidad (el canon petrolero municipal figura a nombre del Consejo Nacional de Descentralización).
- **Resultado:** `DATA/PP_canon_municipal_mef_anio.csv` y `CONTROL/CONTROL PP canon_municipal_mef.csv` (suma de municipalidades vs. total del departamento en el MEF, y vs. el total municipal de PERUPETRO: *recaudado* y *transferido* pueden diferir por fechas de registro).

**Bloque 1** importa las librerías. **Bloque 2** descarga y controla."""

b1 = """#@title Bloque 1 · Librerías { display-mode: "form" }
import importlib
for m in ("requests", "bs4", "pandas"):
    importlib.import_module(m)
print("✅ Librerías listas")
"""

b2 = '''#@title Bloque 2 · Descargar y controlar { display-mode: "form" }
ANIO_INICIO = 2003  #@param {type:"integer"}
ANIO_FIN = 2026  #@param {type:"integer"}
SI_NO_HAY_PETROLERO = "Usar NORMAL (todos los canones)"  #@param ["Usar NORMAL (todos los canones)", "Dejar sin dato"]
DEPARTAMENTO = "16: LORETO"  #@param ["TODOS", "16: LORETO", "25: UCAYALI", "20: PIURA", "24: TUMBES", "10: HUANUCO", "08: CUSCO"]
import os, re, unicodedata, pandas as pd
from datetime import date
DRIVE_FOLDER_ID = "1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq"            # DATA
DRIVE_FOLDER_CONTROL_ID = "1TKjS2Wjpnf26oladjhqstmN5c9Irq-Aj"    # CONTROL
FUENTE = "MEF, Consulta Amigable de Ingresos (recaudado)"
ruta_local = "/content/pp_mef"; os.makedirs(ruta_local, exist_ok=True)

# ── Google Drive ──
from google.colab import auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
auth.authenticate_user()
drive = build("drive", "v3", cache_discovery=False)
def archivos_en(folder_id):
    out, token = {}, None
    while True:
        r = drive.files().list(q=f"'{folder_id}' in parents and trashed = false", fields="nextPageToken, files(id,name)",
                               pageSize=1000, pageToken=token, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        out.update({f["name"]: f["id"] for f in r.get("files", [])})
        token = r.get("nextPageToken")
        if not token:
            return out
def subir(ruta_archivo, folder_id, existentes, mime="text/csv"):
    nombre = os.path.basename(ruta_archivo)
    media = MediaFileUpload(ruta_archivo, mimetype=mime, resumable=True)
    if nombre in existentes:
        drive.files().update(fileId=existentes[nombre], media_body=media, supportsAllDrives=True).execute()
    else:
        existentes[nombre] = drive.files().create(body={"name": nombre, "parents": [folder_id]}, media_body=media,
                                                  fields="id", supportsAllDrives=True).execute()["id"]
def bajar(nombre, existentes):
    if nombre not in existentes:
        return None
    p = os.path.join(ruta_local, nombre)
    with open(p, "wb") as fh:
        dl = MediaIoBaseDownload(fh, drive.files().get_media(fileId=existentes[nombre], supportsAllDrives=True)); hecho = False
        while not hecho:
            _, hecho = dl.next_chunk()
    return pd.read_csv(p, encoding="utf-8-sig")
datos_drive, control_drive = archivos_en(DRIVE_FOLDER_ID), archivos_en(DRIVE_FOLDER_CONTROL_ID)

''' + lector + '''

def norm_may(t):
    return re.sub(r"\\s+", " ", unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()).strip().upper()
TODOS = DEPARTAMENTO.strip().upper() == "TODOS"
# referencias de PERUPETRO (si existen en DATA): total municipal por departamento y año, y provincia de cada municipalidad
dist_pp = bajar("PP_canon_distribucion_mes.csv", datos_drive)
mun_pp = bajar("PP_canon_municipal_mes.csv", datos_drive)
pp_mun = (dist_pp[dist_pp["TIPO_BENEFICIARIO"] == "MUNICIPALIDADES"].assign(_D=dist_pp["DEPARTAMENTO"].map(norm_may))
          .groupby(["_D", "AÑO"])["MONTO_SOLES"].sum().to_dict() if dist_pp is not None else {})
prov_de = ({norm_may(m): norm_may(p) for m, p in zip(mun_pp["MUNICIPALIDAD"], mun_pp["PROVINCIA"]) if isinstance(p, str)}
           if mun_pp is not None else {})

m = MEFIngresosURL(log=print)
print("🔎 Calibrando la consulta…")
if not m.calibrar(min(ANIO_FIN, date.today().year)):
    raise SystemExit("❌ Ninguna variante de URL trajo la tabla de fuentes de financiamiento: el MEF cambió la página o bloqueó la consulta.")
filas, ctrl = [], []
for anio in range(ANIO_INICIO, ANIO_FIN + 1):
    etq_dep = "TODOS" if TODOS else norm_may(DEPARTAMENTO.split(":", 1)[1])
    ruta, tipos, err = m.ruta_tipos(anio)
    if err:
        print(f"⚠️ {anio}: {err}"); ctrl.append({"AÑO": anio, "DEPARTAMENTO": etq_dep, "ESTADO": f"ERROR: {err}"}); continue
    resultados = []                                     # [(tipo, ruta hasta departamento, página de departamentos)]
    motivos = []
    for t in [t for t in tipos if re.search("PETROLER", t[1], re.I)]:
        r, pdep, e = m.hasta_departamentos(anio, ruta, t)
        if r: resultados.append((t, r, pdep))
        else: motivos.append(f"{t[1]}: {e}")
    usa_normal = False
    if not resultados and SI_NO_HAY_PETROLERO.startswith("Usar") and anio < 2007:
        t0 = next((t for t in tipos if re.match(r"^0:\\s*NORMAL", t[1], re.I)), None)
        if t0:
            r, pdep, e = m.hasta_departamentos(anio, ruta, t0)
            if r: resultados, usa_normal = [(t0, r, pdep)], True
            else: motivos.append(f"{t0[1]}: {e}")
    if not resultados:
        msg = "SIN DETALLE MUNICIPAL (" + "; ".join(motivos or ["sin tipo de recurso petrolero"]) + ")"
        print(f"ℹ️ {anio}: {msg}"); ctrl.append({"AÑO": anio, "DEPARTAMENTO": etq_dep, "ESTADO": msg}); continue
    if TODOS:
        deps = sorted({(c, e) for _, _, pdep in resultados for c, e, v in pdep.filas if (v or 0) > 0})
    else:
        cod = DEPARTAMENTO.split(":")[0].strip()
        deps = [(cod, DEPARTAMENTO)]
    for cod_d, etq in deps:
        DEP = norm_may(etq.split(":", 1)[1] if ":" in etq else etq)
        suma = tot = 0.0; n = 0; detalle = []
        for t, r, pdep in resultados:
            dep = next(((c, e, v) for c, e, v in pdep.filas if c.lstrip("0") == cod_d.lstrip("0")), None)
            if dep is None:
                detalle.append(f"{t[1]}: sin {DEP}"); continue
            fs, total, e = m.municipalidades(anio, r, dep)
            if fs is None:
                detalle.append(f"{t[1]}: {e}"); continue
            for c, et, v in fs:
                if not re.search("MUNICIPALIDAD", et, re.I):
                    continue
                codigo, nivel, mu, prov = nombre_municipalidad(et)
                filas.append({"AÑO": anio, "DEPARTAMENTO": DEP, "CODIGO": codigo, "MUNICIPALIDAD_MEF": et.split(":", 1)[1].strip(),
                              "MUNICIPALIDAD": mu, "NIVEL": nivel, "PROVINCIA": prov or prov_de.get(norm_may(mu), ""),
                              "TIPO_RECURSO": t[1] + (" (todos los canones)" if usa_normal else ""), "RECAUDADO_SOLES": round(v, 2),
                              "FUENTE": FUENTE + (" · tipo NORMAL: todos los canones, no solo el petrolero" if usa_normal else "")})
                suma += v; n += 1
            tot += total or 0.0
            detalle.append(f"{t[1]}: S/ {total or 0:,.0f}")
        ref = pp_mun.get((DEP, anio))
        ctrl.append({"AÑO": anio, "DEPARTAMENTO": DEP, "TIPOS": " | ".join(detalle), "MUNICIPALIDADES": n,
                     "SUMA_MUNICIPALIDADES": round(suma, 2), "TOTAL_DEPARTAMENTO_MEF": round(tot, 2), "DIF": round(suma - tot, 2),
                     "PERUPETRO_MUNICIPAL": round(ref, 2) if ref else None, "MEF_SOBRE_PERUPETRO": round(suma / ref, 4) if ref else None,
                     "ESTADO": ("OK" if n and abs(suma - tot) <= max(1, n) else "REVISAR" if n else "SIN MUNICIPALIDADES")})
        print(f"{'✅' if n else 'ℹ️'} {anio} · {DEP}: {n} municipalidades · S/ {suma/1e6:,.2f} millones"
              + (" (todos los canones)" if usa_normal else "") + (f" · PERUPETRO S/ {ref/1e6:,.2f} millones" if ref else ""))
print("Claves usadas:", m.claves, "· página Navegar_", m.pagina)

# ── Guardar (se acumula: cada corrida reemplaza los departamentos y años que vuelve a leer) ──
nuevo = pd.DataFrame(filas)
previo = bajar("PP_canon_municipal_mef_anio.csv", datos_drive)
if previo is not None and len(nuevo):
    leidos = set(zip(nuevo["DEPARTAMENTO"], nuevo["AÑO"]))
    previo = previo[[(d, a) not in leidos for d, a in zip(previo["DEPARTAMENTO"], previo["AÑO"])]]
    nuevo = pd.concat([previo, nuevo], ignore_index=True)
elif previo is not None:
    nuevo = previo
if len(nuevo):
    nuevo = nuevo.sort_values(["DEPARTAMENTO", "AÑO", "NIVEL", "MUNICIPALIDAD", "TIPO_RECURSO"], ascending=[True, True, False, True, True])
    p = os.path.join(ruta_local, "PP_canon_municipal_mef_anio.csv"); nuevo.to_csv(p, index=False, encoding="utf-8-sig")
    subir(p, DRIVE_FOLDER_ID, datos_drive)
c = pd.DataFrame(ctrl); c.insert(0, "FECHA_EXTRACCION", date.today().strftime("%d/%m/%Y"))
previo_c = bajar("CONTROL PP canon_municipal_mef.csv", control_drive)
if previo_c is not None:
    leidos_c = set(zip(c["DEPARTAMENTO"], c["AÑO"]))
    c = pd.concat([previo_c[[(d, a) not in leidos_c for d, a in zip(previo_c["DEPARTAMENTO"], previo_c["AÑO"])]], c],
                  ignore_index=True).sort_values(["AÑO", "DEPARTAMENTO"])
p = os.path.join(ruta_local, "CONTROL PP canon_municipal_mef.csv"); c.to_csv(p, index=False, encoding="utf-8-sig")
subir(p, DRIVE_FOLDER_CONTROL_ID, control_drive)
print(f"\\n☁️ DATA/PP_canon_municipal_mef_anio.csv ({len(nuevo)} filas) · CONTROL/CONTROL PP canon_municipal_mef.csv")
display(c[c["AÑO"].between(ANIO_INICIO, ANIO_FIN)].drop(columns=["FECHA_EXTRACCION"]))
'''

cells = [{"cell_type": "markdown", "metadata": {}, "source": md}]
for s in (b1, b2):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s})
nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"}},
      "cells": cells}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(nb, fh, ensure_ascii=False, indent=1)
print("ok", sys.argv[1])
