import json, sys
import os
lector = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lector_mef.py")).read()
md = """# 🏛️ MEF · Canon y sobrecanon petrolero recaudado por cada municipalidad (2005–hoy)

PERUPETRO publica el canon **por municipalidad** solo en 1993–2002 (Excel de Distribución) y el año en curso (Excel de Canon Municipalidades). Desde 2003 entrega el total municipal a un intermediario (CND hasta 2006; PCM desde 2007), que hace el reparto. Este notebook completa los años que faltan con el **MEF – Consulta Amigable de Ingresos** (`apps5.mineco.gob.pe/transparenciaingresos/mensual/`), monto **recaudado** por cada municipalidad:

**Ruta:** Fuente 5 (Recursos determinados) → Rubro 18 → Tipo de recurso con «PETROLERO» (5: Canon y sobrecanon petrolero y, en años recientes, K: Sub cuenta – Canon y sobrecanon petrolero; se suman) → Nivel de gobierno M → Departamento 16: Loreto → Municipalidad.

- La consulta funciona con *postbacks* de ASP.NET (no se puede armar por URL), así que se maneja un **navegador real** (Playwright) con pausas, como lo haría una persona.
- **Desde 2007** la consulta es homogénea (fuente 5 → rubro 18 → tipos petroleros 5 y K).
- **2005–2006**: otra clasificación (fuente 01 Canon y sobrecanon → tipo de recurso, sin rubro) y el detalle por municipalidad solo está en el tipo «0: NORMAL», que reúne **todos** los canones (no solo el petrolero). Con `SI_NO_HAY_PETROLERO = "Usar NORMAL"` (opción por defecto) se toma ese tipo cuando el petrolero no llega a gobiernos locales; queda rotulado «todos los canones» en el CSV y en el mapa.
- **2003–2004**: sin detalle por municipalidad (el canon petrolero municipal figura a nombre del Consejo Nacional de Descentralización); quedan en el control con el motivo.
- **Resultado:** `DATA/PP_canon_municipal_mef_anio.csv` y `CONTROL/CONTROL PP canon_municipal_mef.csv` (suma de municipalidades vs. total de Loreto en el MEF, y vs. el total municipal de PERUPETRO del mismo año: *recaudado* y *transferido* pueden diferir por fechas de registro).
- El mapa (`PP_Mapa_Lotes_Plus.ipynb`) lo usa para los años sin detalle de PERUPETRO y lo rotula con su fuente.

**Bloque 1** instala el navegador (1–2 min). **Bloque 2** descarga y controla."""
b1 = """#@title Bloque 1 · Instalar el navegador (Playwright + Chromium) { display-mode: "form" }
!pip -q install playwright
!playwright install --with-deps chromium > /dev/null 2>&1 && echo "✅ Chromium listo"
"""
b2 = '''#@title Bloque 2 · Descargar y controlar { display-mode: "form" }
ANIO_INICIO = 2003  #@param {type:"integer"}
ANIO_FIN = 2026  #@param {type:"integer"}
SI_NO_HAY_PETROLERO = "Usar NORMAL (todos los canones)"  #@param ["Usar NORMAL (todos los canones)", "Dejar sin dato"]
DEPARTAMENTO = "16: LORETO"  #@param ["TODOS", "16: LORETO", "25: UCAYALI", "20: PIURA", "24: TUMBES", "10: HUANUCO", "08: CUSCO"]
import os, re, time, asyncio, unicodedata, pandas as pd
from datetime import date
DRIVE_FOLDER_ID = "1dOOcsVyw915yKg6BzSdICVfCpYTiyeaq"            # DATA
DRIVE_FOLDER_CONTROL_ID = "1TKjS2Wjpnf26oladjhqstmN5c9Irq-Aj"    # CONTROL
BASE = "https://apps5.mineco.gob.pe/transparenciaingresos/mensual"
FUENTE = "MEF, Consulta Amigable de Ingresos (recaudado)"
ruta = "/content/pp_mef"; os.makedirs(ruta, exist_ok=True)

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
def subir(ruta_local, folder_id, existentes, mime="text/csv"):
    nombre = os.path.basename(ruta_local)
    media = MediaFileUpload(ruta_local, mimetype=mime, resumable=True)
    if nombre in existentes:
        drive.files().update(fileId=existentes[nombre], media_body=media, supportsAllDrives=True).execute()
    else:
        existentes[nombre] = drive.files().create(body={"name": nombre, "parents": [folder_id]}, media_body=media,
                                                  fields="id", supportsAllDrives=True).execute()["id"]
def bajar(nombre, existentes):
    if nombre not in existentes:
        return None
    p = os.path.join(ruta, nombre)
    with open(p, "wb") as fh:
        dl = MediaIoBaseDownload(fh, drive.files().get_media(fileId=existentes[nombre], supportsAllDrives=True)); hecho = False
        while not hecho:
            _, hecho = dl.next_chunk()
    return pd.read_csv(p, encoding="utf-8-sig")
datos_drive, control_drive = archivos_en(DRIVE_FOLDER_ID), archivos_en(DRIVE_FOLDER_CONTROL_ID)

''' + lector + '''

def norm(t):
    return re.sub(r"\\s+", " ", unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()).strip().upper()
TODOS = DEPARTAMENTO.strip().upper() == "TODOS"      # todos los departamentos que el MEF muestre con canon petrolero municipal
# referencias de PERUPETRO (si existen en DATA): total municipal por año y provincia de cada municipalidad distrital
dist_pp = bajar("PP_canon_distribucion_mes.csv", datos_drive)
mun_pp = bajar("PP_canon_municipal_mes.csv", datos_drive)
pp_mun = (dist_pp[dist_pp["TIPO_BENEFICIARIO"] == "MUNICIPALIDADES"].assign(_D=dist_pp["DEPARTAMENTO"].map(norm))
          .groupby(["_D", "AÑO"])["MONTO_SOLES"].sum().to_dict() if dist_pp is not None else {})
prov_de = ({norm(m): norm(p) for m, p in zip(mun_pp["MUNICIPALIDAD"], mun_pp["PROVINCIA"]) if isinstance(p, str)}
           if mun_pp is not None else {})

from playwright.async_api import async_playwright
filas, ctrl = [], []
async def correr():
    async with async_playwright() as p:
        nav = await p.chromium.launch()
        pg = await (await nav.new_context(locale="es-PE", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")).new_page()
        m = MEFIngresos(pg, BASE, pausa=1.5)
        for anio in range(ANIO_INICIO, ANIO_FIN + 1):
            for intento in (1, 2):
                try:
                    tipos = await m.tipos_petroleros(anio)
                    usa_normal = False
                    if SI_NO_HAY_PETROLERO.startswith("Usar") and anio < 2007:
                        # hasta 2006 el tipo petrolero puede no llegar a gobiernos locales (2003–2004: va al CND);
                        # en 2005–2006 el detalle municipal está en «0: NORMAL», que reúne todos los canones
                        con_m = False
                        for etq, _, esq in tipos:
                            ds, _r = await m.departamentos(anio, "^" + re.escape(etq.split(":")[0].strip()) + r":\\s", esq)
                            if ds:
                                con_m = True; break
                        if not con_m:
                            tn = await m.tipos_petroleros(anio, r"^0:\\s*NORMAL")
                            if tn:
                                tipos, usa_normal = tn, True
                    if not tipos:
                        ctrl.append({"AÑO": anio, "DEPARTAMENTO": "TODOS" if TODOS else DEPARTAMENTO, "ESTADO": "SIN TIPO DE RECURSO PETROLERO EN EL RUBRO 18 (¿detalle a nombre del CND?)"})
                        print(f"ℹ️ {anio}: sin tipo de recurso petrolero en el rubro 18"); break
                    if TODOS:                                  # departamentos con recaudado en algún tipo petrolero
                        deps = {}
                        for etq, _, esq in tipos:
                            ds, _r = await m.departamentos(anio, "^" + re.escape(etq.split(":")[0].strip()) + r":\\s", esq)
                            for d_, v_ in ds:
                                deps[d_.split(":")[0].strip()] = d_
                        objetivos = sorted(deps.values())
                    else:
                        objetivos = [DEPARTAMENTO]
                    for dep_etq in objetivos:
                        cod_d, DEP = dep_etq.split(":", 1)[0].strip(), norm(dep_etq.split(":", 1)[1])
                        suma = tot = 0.0; n = 0; detalle = []
                        for etq, rec_nac, esq in tipos:
                            cod_t = etq.split(":")[0].strip()
                            fs, total, recorrido = await m.municipalidades(anio, "^" + re.escape(cod_t) + r":\\s", r"^" + re.escape(cod_d) + r":", esq)
                            if fs is None:
                                detalle.append(f"{etq}: {' > '.join(recorrido)}"); continue
                            for f in fs:
                                if not re.search("MUNICIPALIDAD", f["etiqueta"], re.I):
                                    continue
                                cod, nivel, mu, prov = nombre_municipalidad(f["etiqueta"])
                                filas.append({"AÑO": anio, "DEPARTAMENTO": DEP, "CODIGO": cod, "MUNICIPALIDAD_MEF": f["etiqueta"].split(":", 1)[1].strip(),
                                              "MUNICIPALIDAD": mu, "NIVEL": nivel, "PROVINCIA": prov or prov_de.get(norm(mu), ""),
                                              "TIPO_RECURSO": etq + (" (todos los canones)" if usa_normal else ""), "RECAUDADO_SOLES": f["recaudado"] or 0.0,
                                              "FUENTE": FUENTE + (" · tipo NORMAL: todos los canones, no solo el petrolero" if usa_normal else "")})
                                suma += f["recaudado"] or 0.0; n += 1
                            tot += total or 0.0
                            detalle.append(f"{etq}: S/ {total or 0:,.0f}")
                        ref = pp_mun.get((DEP, anio))
                        ctrl.append({"AÑO": anio, "DEPARTAMENTO": DEP, "TIPOS": " | ".join(detalle), "MUNICIPALIDADES": n,
                                     "SUMA_MUNICIPALIDADES": round(suma, 2), "TOTAL_DEPARTAMENTO_MEF": round(tot, 2), "DIF": round(suma - tot, 2),
                                     "PERUPETRO_MUNICIPAL": round(ref, 2) if ref else None,
                                     "MEF_SOBRE_PERUPETRO": round(suma / ref, 4) if ref else None,
                                     "ESTADO": ("OK" if n and abs(suma - tot) <= 1 else "REVISAR" if n else "SIN MUNICIPALIDADES")})
                        print(f"{'✅' if n else 'ℹ️'} {anio} · {DEP}: {n} municipalidades · S/ {suma/1e6:,.2f} millones" + (f" · PERUPETRO S/ {ref/1e6:,.2f} millones" if ref else ""))
                    if not objetivos:
                        ctrl.append({"AÑO": anio, "DEPARTAMENTO": "TODOS" if TODOS else DEPARTAMENTO, "ESTADO": "SIN DEPARTAMENTOS CON CANON PETROLERO MUNICIPAL"})
                        print(f"ℹ️ {anio}: sin departamentos con canon petrolero en gobiernos locales")
                    break
                except Exception as e:
                    print(f"⚠️ {anio} intento {intento}: {type(e).__name__}: {str(e)[:160]}")
                    try:
                        png = os.path.join(ruta, f"CONTROL PP mef_error_{anio}.png"); await pg.screenshot(path=png, full_page=True)
                        subir(png, DRIVE_FOLDER_CONTROL_ID, control_drive, mime="image/png")
                    except Exception:
                        pass
                    if intento == 2:
                        ctrl.append({"AÑO": anio, "DEPARTAMENTO": "TODOS" if TODOS else DEPARTAMENTO, "ESTADO": f"ERROR: {type(e).__name__}: {str(e)[:150]}"})
                    await asyncio.sleep(10)
        await nav.close()
await correr()

# ── Guardar (se acumula: cada corrida reemplaza los años que vuelve a leer) ──
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
    p = os.path.join(ruta, "PP_canon_municipal_mef_anio.csv"); nuevo.to_csv(p, index=False, encoding="utf-8-sig")
    subir(p, DRIVE_FOLDER_ID, datos_drive)
c = pd.DataFrame(ctrl); c.insert(0, "FECHA_EXTRACCION", date.today().strftime("%d/%m/%Y"))
previo_c = bajar("CONTROL PP canon_municipal_mef.csv", control_drive)
if previo_c is not None:
    leidos_c = set(zip(c["DEPARTAMENTO"], c["AÑO"]))
    c = pd.concat([previo_c[[(d, a) not in leidos_c for d, a in zip(previo_c["DEPARTAMENTO"], previo_c["AÑO"])]], c],
                  ignore_index=True).sort_values(["AÑO", "DEPARTAMENTO"])
p = os.path.join(ruta, "CONTROL PP canon_municipal_mef.csv"); c.to_csv(p, index=False, encoding="utf-8-sig")
subir(p, DRIVE_FOLDER_CONTROL_ID, control_drive)
print(f"\\n☁️ DATA/PP_canon_municipal_mef_anio.csv ({len(nuevo)} filas) · CONTROL/CONTROL PP canon_municipal_mef.csv")
display(c[c["AÑO"].between(ANIO_INICIO, ANIO_FIN)].drop(columns=["FECHA_EXTRACCION"]))
'''
cells = [{"cell_type": "markdown", "metadata": {}, "source": md}]
for s in (b1, b2):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s})
nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"}}, "cells": cells}
json.dump(nb, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print("ok", sys.argv[1])
