"""Prueba de conexión para la fase 2: ¿responde Consulta Amigable del MEF desde GitHub Actions? ¿se puede escribir en Neon?

Hace pocas consultas (las mismas de Fiscal_Scraper: encabezados, formatos de URL y claves) y no guarda nada.
Corre en .github/workflows/fiscal_prueba_mef.yml; en local: python FISCAL/automatizacion/prueba_mef.py
"""
import os
import random
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

URL_BASE = "https://apps5.mineco.gob.pe/transparencia/mensual/Navegar_6.aspx"
ENCABEZADOS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
               "Referer": "https://apps5.mineco.gob.pe/transparencia/mensual/default.aspx"}
FORMATOS = [   # los mismos de Fiscal_Scraper (BLOQUE 3)
    {"nombre": "navegador GET", "metodo": "GET", "pre": {"_tgt": "frame", "_uhc": "yes"}, "post": {"ap": "ActProy"}},
    {"nombre": "GET + ap", "metodo": "GET", "pre": {}, "post": {"ap": "ActProy"}},
    {"nombre": "POST + ap", "metodo": "POST", "pre": {}, "post": {"ap": "ActProy"}},
    {"nombre": "POST original", "metodo": "POST", "pre": {}, "post": {}},
]
CLAVES_DEPTO = {"E": ["21"], "R": ["21"], "M": ["5", "21"]}
CLAVE_GENERICA, CLAVE_MES = "24", "23"
BLOQUEO = re.compile(r"incapsula|_Incap_|request unsuccessful|captcha|access denied|imperva", re.I)

resumen = []


def anotar(texto):
    print(texto)
    resumen.append(texto)


def consultar(sesion, formato, anio, mes, nivel, depto="16"):
    p = dict(formato["pre"]); p["0"] = ""
    if mes:
        p[CLAVE_MES] = mes
    p["1"] = nivel
    for k in CLAVES_DEPTO[nivel]:
        p[k] = depto
    p[CLAVE_GENERICA] = ""
    p["y"] = anio
    p.update(formato["post"])
    t0 = time.time()
    try:
        r = sesion.request(formato["metodo"], URL_BASE, params=p, timeout=40)
    except requests.RequestException as e:
        return {"ok": False, "detalle": f"{type(e).__name__}: {e}", "seg": time.time() - t0}
    sopa = BeautifulSoup(r.content, "html.parser")
    tabla = sopa.find("table", class_="Data") is not None
    filas = sum(1 for tr in sopa.find_all("tr") if tr.find("input", attrs={"type": "radio"}))
    texto = sopa.get_text(" ", strip=True)
    bloqueo = BLOQUEO.search(r.text or "")
    detalle = f"HTTP {r.status_code} · {len(r.content):,} bytes · tabla: {'sí' if tabla else 'no'} · filas: {filas}"
    if bloqueo:
        detalle += f" · ⚠ señal de bloqueo: «{bloqueo.group(0)}»"
    if not tabla:
        detalle += f" · texto: {texto[:160]!r}"
    return {"ok": r.status_code == 200 and tabla and filas > 0, "detalle": detalle, "seg": time.time() - t0}


def probar_mef():
    hoy = date.today()
    anio, mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)   # último mes cerrado
    anotar(f"## 1. Consulta Amigable del MEF (Loreto, por genérica, {anio}-{mes:02d})")
    try:
        ip = requests.get("https://api.ipify.org", timeout=10).text
        anotar(f"IP de salida de GitHub: `{ip}`")
    except requests.RequestException:
        pass
    sesion = requests.Session()
    sesion.headers.update(ENCABEZADOS)
    try:
        r = sesion.get(ENCABEZADOS["Referer"], timeout=40)
        anotar(f"- Página de inicio: HTTP {r.status_code} · {len(r.content):,} bytes"
               + (" · ⚠ señal de bloqueo" if BLOQUEO.search(r.text or "") else ""))
    except requests.RequestException as e:
        anotar(f"- Página de inicio: ❌ {type(e).__name__}: {str(e)[:200]}")
    formato = None
    for f in FORMATOS:
        res = consultar(sesion, f, anio, mes, "E")
        anotar(f"- Formato «{f['nombre']}»: {'✅' if res['ok'] else '❌'} {res['detalle']} ({res['seg']:.1f} s)")
        time.sleep(random.uniform(0.5, 1.2))
        if res["ok"]:
            formato = f
            break
    if not formato:
        anotar("**Resultado MEF: ❌ no devolvió la tabla con ningún formato.**")
        return False
    oks = 1
    for nivel, m in [("R", mes), ("M", mes), ("E", ""), ("R", ""), ("M", "")]:
        res = consultar(sesion, formato, anio, m, nivel)
        oks += res["ok"]
        anotar(f"- Nivel {nivel} · {'mes ' + str(m) if m else 'año completo'}: {'✅' if res['ok'] else '❌'} {res['detalle']} ({res['seg']:.1f} s)")
        time.sleep(random.uniform(0.5, 1.2))
    anotar(f"**Resultado MEF: {'✅' if oks == 6 else '⚠'} {oks} de 6 consultas con tabla (formato «{formato['nombre']}»).**")
    return oks == 6


def probar_neon():
    anotar("## 2. Base de datos (Neon)")
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        anotar("**Resultado Neon: ⚠ falta el secreto DATABASE_URL.**")
        return False
    from sqlalchemy import create_engine, text
    url = re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", url)
    try:
        motor = create_engine(url, pool_pre_ping=True)
        with motor.begin() as cx:   # tabla temporal: se borra sola al cerrar la conexión
            cx.execute(text("CREATE TEMP TABLE prueba_fase2 (x INT)"))
            cx.execute(text("INSERT INTO prueba_fase2 VALUES (1)"))
            n = cx.execute(text("SELECT COUNT(*) FROM prueba_fase2")).scalar()
            tablas = cx.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'base_%'")).scalar()
        anotar(f"**Resultado Neon: ✅ conecta y escribe** (prueba: {n} fila; tablas de bases ya creadas por el API: {tablas}).")
        return True
    except Exception as e:
        anotar(f"**Resultado Neon: ❌ {type(e).__name__}: {str(e)[:200]}**")
        return False


if __name__ == "__main__":
    mef, neon = probar_mef(), probar_neon()
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write("\n".join(resumen) + "\n")
    raise SystemExit(0 if mef and neon else 1)
