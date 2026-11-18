#!/usr/bin/env bash
# Lo corre GitHub Actions («Hidrología · actualización» y «Hidrología · pasar a GitHub»): baja de la Release
# «hidrologia-datos» el historial y los JSON del recolector, corre actualizar_hidrologia.py y publica los CSV.
set -euo pipefail
TAG=hidrologia-datos
W="${RUNNER_TEMP:-/tmp}/hidro"
rm -rf "$W" && mkdir -p "$W/carpeta" "$W/json" "$W/pub"
gh release download "$TAG" -p hidrologia.sqlite -D "$W/carpeta" \
  || { echo "::error::La Release $TAG no tiene hidrologia.sqlite: corre antes «Hidrología · pasar a GitHub»"; exit 1; }
gh release download "$TAG" -p 'SENAMHI_crudo_*.json' -D "$W/json" 2>/dev/null || true
mapfile -t JSONS < <(cd "$W/json" && ls SENAMHI_crudo_*.json 2>/dev/null || true)
echo "JSON a sumar: ${#JSONS[@]} ${JSONS[*]:-}"
HIDRO_CARPETA="$W/carpeta" HIDRO_DESCARGAS="$W/json" python HIDROLOGIA/powerbi/actualizar_hidrologia.py
cp "$W"/carpeta/DATA/*.csv "$W/pub/"
for f in "$W"/carpeta/CONTROL/*.csv; do cp "$f" "$W/pub/$(basename "$f" | tr ' ' '_')"; done   # GitHub cambia los espacios
cp "$W/carpeta/LEEME.txt" "$W/carpeta/hidrologia.sqlite" "$W/pub/"
gh release upload "$TAG" "$W"/pub/* --clobber
for n in "${JSONS[@]}"; do
  [ -n "$n" ] && gh release delete-asset "$TAG" "$n" -y    # ya quedó en el historial
done
{ echo "### Hidrología"; echo; echo "JSON sumados: ${#JSONS[@]} ${JSONS[*]:-}"; echo; echo '```'; cat "$W/carpeta/LEEME.txt"; echo '```'; } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
