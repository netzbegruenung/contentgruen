#!/usr/bin/env bash
# Draft of the change list for a release: the Forgejo release to a tag (docs/DEPLOYMENT.md,
# "Updating Production"). Reads the first-parent history of main, changes nothing.
#
#   scripts/changelog.sh [VON] [BIS] > changelog.md
#
# VON: commit or tag of the previous release. Default: the last v* tag before BIS, so the
#      list for a freshly set tag needs no argument. Without any tag VON is required.
# BIS: commit or tag of the new release. Default: origin/main.
set -euo pipefail

BIS="${2:-origin/main}"
FORGE="https://git.verdigado.com/Netzbegruenung/gutgesagt"
GH="https://github.com/netzbegruenung/contentgruen"

git rev-parse --verify -q "${BIS}^{commit}" >/dev/null || { echo "Ref $BIS fehlt: erst git fetch origin --tags" >&2; exit 1; }
VON="${1:-}"
if [ -z "$VON" ]; then
  # BIS^ rather than BIS: if BIS carries the new tag itself, the previous one is wanted.
  VON="$(git describe --tags --abbrev=0 --match 'v*' "${BIS}^" 2>/dev/null)" || {
    echo "Kein Tag vor $BIS: VON angeben, z. B. scripts/changelog.sh <commit> $BIS" >&2; exit 2; }
fi
git rev-parse --verify -q "${VON}^{commit}" >/dev/null || { echo "Ref $VON fehlt: erst git fetch origin --tags" >&2; exit 1; }

bruch=(); neu=(); behoben=(); sonst=()

while IFS=$'\t' read -r sha subj; do
  if [[ $subj =~ ^Merge\ pull\ request\ \'(.*)\'\ \(#([0-9]+)\)\ from ]]; then
    # Forgejo merge commit
    titel="${BASH_REMATCH[1]}"; nr="${BASH_REMATCH[2]}"
    zeile="- ${titel} ([#${nr}](${FORGE}/pulls/${nr}))"
  elif [[ $subj =~ ^Merge\ pull\ request\ \#([0-9]+)\ from ]]; then
    # GitHub merge commit from before the move to Forgejo; the PR title is the first body line
    nr="${BASH_REMATCH[1]}"
    titel="$(git log -1 --format=%b "$sha" | sed -n '/./{p;q}')"
    zeile="- ${titel:-$subj} ([GitHub #${nr}](${GH}/pull/${nr}))"
  else
    titel="$subj"
    zeile="- ${titel} (${sha:0:8})"
  fi
  if [[ $titel =~ ^[a-z]+(\([^\)]*\))?!: ]]; then bruch+=("$zeile")
  elif [[ $titel =~ ^feat ]]; then neu+=("$zeile")
  elif [[ $titel =~ ^fix ]]; then behoben+=("$zeile")
  else sonst+=("$zeile")
  fi
done < <(git log --first-parent --reverse --format='%H%x09%s' "$VON..$BIS")

ausgabe() { local kopf="$1"; shift; [ "$#" -eq 0 ] && return 0; printf '\n## %s\n\n' "$kopf"; printf '%s\n' "$@"; }

echo "Stand: $(git rev-parse --short "$BIS") ($(git log -1 --format=%cs "$BIS")), seit $(git describe --tags --exact-match "$VON" 2>/dev/null || git rev-parse --short "$VON") ($(git log -1 --format=%cs "$VON"))"
ausgabe "Breaking Changes" "${bruch[@]+"${bruch[@]}"}"
ausgabe "Neu" "${neu[@]+"${neu[@]}"}"
ausgabe "Behoben" "${behoben[@]+"${behoben[@]}"}"
ausgabe "Sonstiges" "${sonst[@]+"${sonst[@]}"}"

# Lists files added between VON and BIS that match a pathspec, or "keine".
neue_dateien() {
  local dateien; dateien="$(git diff --name-only --diff-filter=A "$VON" "$BIS" -- "$1")"
  if [ -z "$dateien" ]; then echo " keine"; else echo; sed 's/^/  - `/; s/$/`/' <<<"$dateien"; fi
}

printf '\n## Migrationen und Betriebsschritte\n\n'
printf -- '- Datenbank-Migrationen laufen beim Start des Suchdienstes von selbst (docs/DEPLOYMENT.md, „Database migrations“). Neue Migrationen:'
neue_dateien "mvp/backend/postgres-app/migrations/*.sql"
printf -- '- Neue Skripte in `mvp/scripts/manual/` (Reihenfolge je README-Abschnitt):'
neue_dateien mvp/scripts/manual/
