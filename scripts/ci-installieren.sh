#!/bin/sh
# Vorbereitung der CI-Schritte python-installieren und frontend-installieren (.woodpecker/ci.yaml),
# mit --nachpruefen auch der Schritte danach.
# Die CI-Images (Dockerfile.ci) bringen die Pakete schon mit, dazu unter /opt/ci die
# Pruefsumme der Dateien, aus denen sie gebaut wurden: Dockerfile.ci selbst (Basis-Image,
# Python- und Node-Version) und die Lockfiles. Stimmt sie mit dem Checkout
# ueberein, wird nur verknuepft; sonst (ein PR aendert requirements.txt oder package-lock.json,
# das Image ist alt, oder der Schritt laeuft im blanken python- bzw. node-Image) installiert
# der Schritt wie bisher. Kein PR wird rot, weil ein Image nicht passt (docs/CI.md, "CI images").
#
# python:   venv mit --system-site-packages unter mvp/backend/semantic-search-service/venv; die
#           Pakete liegen im Image systemweit, pip installiert nur, was davon abweicht.
# frontend: node_modules des Frontends als Verweis auf /opt/ci/node_modules, sonst npm ci
#           (--prefer-offline: aus dem npm-Cache des Images, was dort schon liegt).
# --pruefsumme python|frontend gibt die Pruefsumme aus; Dockerfile.ci schreibt sie so ins Image.
# --nachpruefen python|frontend: fuer spaetere Schritte (unit, lint, integration,
#           frontend-build, frontend). Jeder Schritt zieht :latest selbst; wurde dazwischen ein neues Image
#           gepusht, passt es vielleicht nicht mehr. Dann pip nachinstallieren bzw. den Verweis
#           durch npm ci ersetzen. Passt es, kostet das nur die Pruefsumme. Nur in Schritten,
#           die nie zugleich laufen (die Kette der schweren Schritte), sonst schrieben zwei
#           Schritte zugleich in venv bzw. node_modules.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=$ROOT/mvp/backend/semantic-search-service
FE=$ROOT/mvp/frontend/gutgesagt-frontend
CI_DIR=${CI_IMAGE_DIR:-/opt/ci}

dateien() {
  case "$1" in
    # Dockerfile.ci zuerst: Hebt ein PR die Python- oder Node-Version, passt das alte Image
    # nicht mehr, auch wenn die Lockfiles gleich bleiben.
    python) echo "$ROOT/Dockerfile.ci $PY/requirements.txt" ;;
    frontend) echo "$ROOT/Dockerfile.ci $FE/package.json $FE/package-lock.json" ;;
    *) echo "Unbekannt: $1 (python oder frontend)" >&2; exit 2 ;;
  esac
}

pruefsumme() {
  liste=$(dateien "$1")
  for d in $liste; do [ -f "$d" ] || { echo "Fehlt: $d" >&2; exit 1; }; done
  # shellcheck disable=SC2086
  cat $liste | sha256sum | cut -d' ' -f1
}

# Wahr, wenn das Image die Pakete genau dieser Dateien mitbringt
vorinstalliert() {
  [ -f "$CI_DIR/$1.sha256" ] && [ "$(cat "$CI_DIR/$1.sha256")" = "$(pruefsumme "$1")" ]
}

grund() {
  if [ -f "$CI_DIR/$1.sha256" ]; then
    echo "CI-Image passt nicht zum Checkout ($(dateien "$1" | sed "s|$ROOT/||g") geaendert oder Image alt): installiere wie ohne Image"
  else
    echo "Kein CI-Image (keine $CI_DIR/$1.sha256): installiere alles"
  fi
}

case "${1:-}" in
  --pruefsumme) pruefsumme "${2:-}" ;;
  python)
    python -m venv --system-site-packages "$PY/venv"
    if vorinstalliert python; then
      echo "Python-Pakete aus dem CI-Image, requirements.txt unveraendert"
    else
      grund python
      "$PY/venv/bin/pip" install -q --no-cache-dir -r "$PY/requirements.txt"
    fi ;;
  frontend)
    if vorinstalliert frontend; then
      rm -rf "$FE/node_modules"
      ln -s "$CI_DIR/node_modules" "$FE/node_modules"
      echo "node_modules aus dem CI-Image, package.json und package-lock.json unveraendert"
    else
      grund frontend
      npm ci --prefix "$FE" --prefer-offline --no-audit --no-fund
    fi ;;
  --nachpruefen)
    case "${2:-}" in
      python)
        if ! vorinstalliert python; then
          echo "Image dieses Schritts passt nicht zu requirements.txt: pip prueft nach"
          "$PY/venv/bin/pip" install -q --no-cache-dir -r "$PY/requirements.txt"
        fi ;;
      frontend)
        # Ein echtes node_modules stammt aus npm ci und haengt nicht am Image.
        if [ -L "$FE/node_modules" ] && ! vorinstalliert frontend; then
          echo "Image dieses Schritts passt nicht zu package-lock.json: npm ci statt Verweis"
          rm -f "$FE/node_modules"
          npm ci --prefix "$FE" --prefer-offline --no-audit --no-fund
        fi ;;
      *) echo "Unbekannt: ${2:-} (python oder frontend)" >&2; exit 2 ;;
    esac ;;
  *) echo "Aufruf: ci-installieren.sh python|frontend|--pruefsumme <art>|--nachpruefen <art>" >&2; exit 2 ;;
esac
