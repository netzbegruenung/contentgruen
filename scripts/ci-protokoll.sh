#!/bin/sh
# Fuehrt einen Befehl eines CI-Schritts aus (.woodpecker/ci.yaml): Ausgabe ins Woodpecker-Log
# und angehaengt an .ci/<schritt>.log, Exit-Code nach .ci/<schritt>.status; endet mit dem
# Exit-Code des Befehls. Beides liest scripts/ci_bericht.py. Ohne Status-Datei gilt der
# Schritt als abgebrochen. Ein Schritt darf es mehrmals aufrufen, der letzte Status zaehlt.
# Aufruf: sh scripts/ci-protokoll.sh <schritt> <befehl> [argumente ...]
set -u
schritt=$1
shift
mkdir -p .ci
rm -f ".ci/$schritt.status"
{ "$@" 2>&1; echo $? > ".ci/$schritt.status"; } | tee -a ".ci/$schritt.log"
exit "$(cat ".ci/$schritt.status" 2>/dev/null || echo 1)"
