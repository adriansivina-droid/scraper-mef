"""Copia una sola vez a la página (almacén de FISCAL/api/app/almacen.py) lo que el flujo de hidrocarburos tenía en Drive.

    python migrar_drive.py listar     # solo cuenta archivos y MB por carpeta
    python migrar_drive.py copiar     # copia DATA y CONTROL completas (con sus subcarpetas) y carga la página

Necesita la credencial de Drive (GOOGLE_APPLICATION_CREDENTIALS, en GitHub el secreto GOOGLE_DRIVE_CREDENCIAL) y
DATABASE_URL. Conserva las carpetas, los nombres y los IDs de Drive, así los notebooks siguen igual. Se puede volver a
correr: lo que ya está copiado (mismo ID y tamaño) no se vuelve a bajar. Solo lee Drive: no borra ni cambia nada allí.
"""
import io
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), "FISCAL", "api"))
from app import almacen  # noqa: E402

CARPETA = "application/vnd.google-apps.folder"


def servicio():
    from googleapiclient.discovery import build
    return build("drive", "v3", cache_discovery=False)


def hijos(drive, carpeta):
    salida, pagina = [], None
    while True:
        r = drive.files().list(q=f"'{carpeta}' in parents and trashed = false", pageSize=1000, pageToken=pagina,
                               fields="nextPageToken, files(id,name,mimeType,size,modifiedTime)",
                               supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        salida += r.get("files", [])
        pagina = r.get("nextPageToken")
        if not pagina:
            return salida


def recorrer(drive, carpeta, ruta):
    """(ruta, archivo, padre) de todo lo que cuelga de la carpeta, carpetas incluidas (antes que su contenido)."""
    for a in hijos(drive, carpeta):
        yield ruta, a, carpeta
        if a["mimeType"] == CARPETA:
            yield from recorrer(drive, a["id"], f"{ruta}/{a['name']}")


def en_disco(ruta):
    """DATA/PDF no se copia a la base (los PDF anuales de PERUPETRO: el flujo los vuelve a bajar y los guarda en su caché)."""
    return ruta.split("/")[0] == "DATA" and len(ruta.split("/")) > 1 and ruta.split("/")[1] in almacen.EN_DISCO


def bajar(drive, file_id):
    from googleapiclient.http import MediaIoBaseDownload
    fh = io.BytesIO()
    dl = MediaIoBaseDownload(fh, drive.files().get_media(fileId=file_id, supportsAllDrives=True), chunksize=50 * 1024 * 1024)
    hecho = False
    while not hecho:
        _, hecho = dl.next_chunk()
    return fh.getvalue()


def main():
    modo = (sys.argv[1] if len(sys.argv) > 1 else "listar").lower()
    if modo not in ("listar", "copiar"):
        sys.exit("Modo: listar o copiar")
    drive, t0 = servicio(), time.time()
    ya = {a["id"]: a for a in almacen.arbol()} if modo == "copiar" else {}
    lineas = [f"## Hidrocarburos · migrar desde Drive ({modo})", "", "| Carpeta | Archivos | MB |", "|---|---|---|"]
    total_mb, copiados, saltados, nativos = 0.0, 0, 0, []
    for raiz, nombre in almacen.RAICES.items():
        por_carpeta = {}
        for ruta, a, padre in recorrer(drive, raiz, nombre):
            if a["mimeType"] == CARPETA:
                if modo == "copiar":
                    almacen.crear(a["name"], padre, None, CARPETA, id_=a["id"])
                continue
            mb = int(a.get("size") or 0) / 1e6
            if en_disco(ruta):
                n, m = por_carpeta.get(ruta, (0, 0.0))[:2]
                por_carpeta[ruta] = (n + 1, m + mb, "no se copia: el flujo los vuelve a bajar de PERUPETRO (caché de GitHub)")
                continue
            n, m = por_carpeta.get(ruta, (0, 0.0))[:2]
            por_carpeta[ruta] = (n + 1, m + mb)
            total_mb += mb
            if a["mimeType"].startswith("application/vnd.google-apps."):
                nativos.append(f"{ruta}/{a['name']}")      # Docs/Hojas de Google: no se pueden bajar tal cual
                continue
            if modo == "copiar":
                if a["id"] in ya and ya[a["id"]]["kb"] == round(int(a.get("size") or 0) / 1024):
                    almacen.fijar_modificado(a["id"], a.get("modifiedTime"))   # la fecha de Drive (elige el CSV más reciente)
                    saltados += 1
                    continue
                almacen.crear(a["name"], padre, bajar(drive, a["id"]), a["mimeType"], id_=a["id"], modificado=a.get("modifiedTime"))
                copiados += 1
                print(f"  ✔ {ruta}/{a['name']} ({mb:.1f} MB)", flush=True)
        lineas += [f"| {r} | {x[0]} | {x[1]:.1f}{' · ' + x[2] if len(x) > 2 else ''} |" for r, x in sorted(por_carpeta.items())]
    lineas += ["", f"**Total a copiar: {total_mb:.1f} MB** ({(time.time() - t0) / 60:.1f} min)."]
    if nativos:
        lineas.append(f"- No se copian (documentos de Google, no archivos): {', '.join(nativos[:20])}")
    if modo == "copiar":
        lineas.append(f"- Copiados: {copiados} · ya estaban: {saltados}")
        lineas.append("- En la página: " + ", ".join(f"{k}: {v['archivos']} archivos, {v['mb']} MB comprimidos"
                                                       for k, v in almacen.resumen().items()))
        r = almacen.sincronizar(origen="migración desde Drive", todo=True)
        lineas.append("- Archivos cargados en las bases: " + ", ".join(a["nombre"] for a in r["archivos"]))
        lineas += [f"- Cargado: {b} ({x['filas']} filas, {x['periodos'][0]} a {x['periodos'][-1]})" for b, x in r["bases"].items()]
        lineas += [f"- {a}" for a in r["avisos"]]
    texto = "\n".join(lineas)
    print("\n" + texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")


if __name__ == "__main__":
    main()
