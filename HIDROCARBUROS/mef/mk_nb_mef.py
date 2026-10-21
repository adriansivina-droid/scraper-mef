"""Genera HIDROCARBUROS/PP_MEF_Canon_Municipal.ipynb (python3 mk_nb_mef.py <salida.ipynb>).
El notebook embebe lector_mef.py (navega el formulario ASP.NET con requests, como el navegador)."""
import json, os, sys
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lector_mef.py"), encoding="utf-8") as fh:
    lector = fh.read()

md = """# 🏛️ MEF · Canon y sobrecanon petrolero recaudado por cada municipalidad (2005–hoy)

PERUPETRO publica el canon **por municipalidad** solo en 1993–2002 (Excel de Distribución) y el año en curso (Excel de Canon Municipalidades). Desde 2003 entrega el total municipal a un intermediario (CND hasta 2006; PCM desde 2007), que hace el reparto. Este notebook completa los años que faltan con el **MEF – Consulta Amigable de Ingresos** (`apps5.mineco.gob.pe/transparenciaingresos/mensual/`), monto **recaudado** por cada municipalidad.

**Cómo lee la consulta:** la consulta de ingresos funciona con botones: elegir una fila y pulsar la dimensión siguiente envía el formulario de la página (postback ASP.NET). Los filtros puestos en la URL, incluida la de «Exportar», se ignoran (probado con `Navegar_1` y `Navegar_6`, 2026). El notebook hace lo mismo que el navegador, con `requests` y sin navegador: abre `default.aspx?y=AAAA`, toma el marco `Navegar_N.aspx` del año y en cada paso envía el formulario con la fila elegida y el botón (Rubro, Tipo de Recurso, Nivel de Gobierno, Gob.Loc./Mancom., Departamento, Municipalidad). Cada paso se valida con el historial (breadcrumb) y la cabecera de la tabla. Los montos salen del valor exacto de cada fila (con céntimos).

- **Desde 2007**: fuente 5 (Recursos determinados) → rubro 18 → tipos «5: Canon y sobrecanon petrolero» y «K: Sub cuenta – …» (se suman) → gobiernos locales → departamento → municipalidad.
- **2005–2006**: fuente 01 (Canon y sobrecanon) → tipo de recurso; el detalle municipal solo está en «0: NORMAL», que reúne **todos** los canones. Con `SI_NO_HAY_PETROLERO = "Usar NORMAL"` se toma ese tipo y queda rotulado «todos los canones» en el CSV y en el mapa.
- **2003–2004**: sin detalle por municipalidad (el canon petrolero municipal figura a nombre del Consejo Nacional de Descentralización).
- **Primero, la distribución por nivel de gobierno**: para cada año y tipo de recurso petrolero, lo recaudado por el gobierno nacional (E), los gobiernos locales (M) y los gobiernos regionales (R), en total país y por departamento → `DATA/PP_canon_nivel_gobierno_mef_anio.csv` (control: suma de niveles = total del tipo de recurso, en `CONTROL/CONTROL PP canon_nivel_gobierno_mef.csv`).
- **Después, el detalle por municipalidad** (nivel M). **Resultado:** `DATA/PP_canon_municipal_mef_anio.csv` y `CONTROL/CONTROL PP canon_municipal_mef.csv` (suma de municipalidades vs. total del departamento en el MEF, y vs. el total municipal de PERUPETRO: *recaudado* y *transferido* pueden diferir por fechas de registro).

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

m = MEFIngresos(log=print)
if not m.preparar(min(ANIO_FIN, date.today().year)):
    raise SystemExit("❌ No se pudo abrir la consulta (ver el mensaje de arriba): el MEF cambió la página o bloqueó la consulta.")
filas, ctrl, niv_filas, ctrl_niv = [], [], [], []

def registrar_niveles(anio, ruta, t, normal=False):
    """Distribución del tipo de recurso por nivel de gobierno (E, M, R): total país y por departamento."""
    etq_t = t[1] + (" (todos los canones)" if normal else "")
    fuente = FUENTE + (" · tipo NORMAL: todos los canones, no solo el petrolero" if normal else "")
    r_t, pn, e = m.niveles(anio, ruta, t)
    if e:
        ctrl_niv.append({"AÑO": anio, "TIPO_RECURSO": etq_t, "ESTADO": f"ERROR: {e}"}); return
    suma = sum(v for _, _, v in pn.filas)
    sin_dep = []
    for c, et, v in pn.filas:
        niv_filas.append({"AÑO": anio, "TIPO_RECURSO": etq_t, "NIVEL_GOBIERNO": et, "DEPARTAMENTO": "TOTAL PAÍS",
                          "RECAUDADO_SOLES": round(v, 2), "FUENTE": fuente})
        _, pdep, e2 = m.departamentos_de_nivel(anio, r_t, (c, et, v))
        if pdep is None:
            sin_dep.append(f"{et}: {e2}"); continue
        for cd, ed, vd in pdep.filas:
            niv_filas.append({"AÑO": anio, "TIPO_RECURSO": etq_t, "NIVEL_GOBIERNO": et,
                              "DEPARTAMENTO": norm_may(ed.split(":", 1)[1] if ":" in ed else ed),
                              "RECAUDADO_SOLES": round(vd, 2), "FUENTE": fuente})
    ctrl_niv.append({"AÑO": anio, "TIPO_RECURSO": etq_t, "NIVELES": " | ".join(f"{et}: S/ {v:,.0f}" for _, et, v in pn.filas),
                     "SUMA_NIVELES": round(suma, 2), "TOTAL_TIPO": round(t[2], 2), "DIF": round(suma - t[2], 2),
                     "SIN_DETALLE_DEPARTAMENTO": "; ".join(sin_dep),
                     "ESTADO": "OK" if abs(suma - t[2]) <= max(1, len(pn.filas)) else "REVISAR"})
    print(f"   🏛️ {anio} · {etq_t}: " + " · ".join(f"{et.split(':', 1)[-1].strip().title()} S/ {v/1e6:,.2f} millones" for _, et, v in pn.filas))

for anio in range(ANIO_INICIO, ANIO_FIN + 1):
    etq_dep = "TODOS" if TODOS else norm_may(DEPARTAMENTO.split(":", 1)[1])
    ruta, tipos, err = m.ruta_tipos(anio)
    if err:
        print(f"⚠️ {anio}: {err}"); ctrl.append({"AÑO": anio, "DEPARTAMENTO": etq_dep, "ESTADO": f"ERROR: {err}"}); continue
    resultados = []                                     # [(tipo, ruta hasta departamento, página de departamentos)]
    motivos = []
    for t in [t for t in tipos if re.search("PETROLER", t[1], re.I)]:   # 1) distribución por nivel de gobierno
        registrar_niveles(anio, ruta, t)
    for t in [t for t in tipos if re.search("PETROLER", t[1], re.I)]:   # 2) municipalidades (nivel M)
        r, pdep, e = m.hasta_departamentos(anio, ruta, t)
        if r: resultados.append((t, r, pdep))
        else: motivos.append(f"{t[1]}: {e}")
    usa_normal = False
    if not resultados and SI_NO_HAY_PETROLERO.startswith("Usar") and anio < 2007:
        t0 = next((t for t in tipos if re.match(r"^0:\\s*NORMAL", t[1], re.I)), None)
        if t0:
            r, pdep, e = m.hasta_departamentos(anio, ruta, t0)
            if r:
                resultados, usa_normal = [(t0, r, pdep)], True
                registrar_niveles(anio, ruta, t0, normal=True)
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
print(f"Última página usada: Navegar_{m.pagina}.aspx")

# ── Distribución por nivel de gobierno (se acumula por año) ──
nv = pd.DataFrame(niv_filas)
previo_nv = bajar("PP_canon_nivel_gobierno_mef_anio.csv", datos_drive)
if previo_nv is not None and len(nv):
    nv = pd.concat([previo_nv[~previo_nv["AÑO"].isin(set(nv["AÑO"]))], nv], ignore_index=True)
elif previo_nv is not None:
    nv = previo_nv
if len(nv):
    nv = nv.sort_values(["AÑO", "TIPO_RECURSO", "NIVEL_GOBIERNO", "DEPARTAMENTO"],
                        key=lambda s: s.map(lambda x: ("0" if x == "TOTAL PAÍS" else "1") + str(x)) if s.name == "DEPARTAMENTO" else s)
    p = os.path.join(ruta_local, "PP_canon_nivel_gobierno_mef_anio.csv"); nv.to_csv(p, index=False, encoding="utf-8-sig")
    subir(p, DRIVE_FOLDER_ID, datos_drive)
cn = pd.DataFrame(ctrl_niv)
if len(cn):
    cn.insert(0, "FECHA_EXTRACCION", date.today().strftime("%d/%m/%Y"))
    previo_cn = bajar("CONTROL PP canon_nivel_gobierno_mef.csv", control_drive)
    if previo_cn is not None:
        cn = pd.concat([previo_cn[~previo_cn["AÑO"].isin(set(cn["AÑO"]))], cn], ignore_index=True).sort_values(["AÑO", "TIPO_RECURSO"])
    p = os.path.join(ruta_local, "CONTROL PP canon_nivel_gobierno_mef.csv"); cn.to_csv(p, index=False, encoding="utf-8-sig")
    subir(p, DRIVE_FOLDER_CONTROL_ID, control_drive)
    print(f"☁️ DATA/PP_canon_nivel_gobierno_mef_anio.csv ({len(nv)} filas) · CONTROL/CONTROL PP canon_nivel_gobierno_mef.csv")
    display(cn[cn["AÑO"].between(ANIO_INICIO, ANIO_FIN)].drop(columns=["FECHA_EXTRACCION"]))

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
