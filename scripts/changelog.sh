#!/usr/bin/env bash
# Draft of the change list for a release: its section in CHANGELOG.md, published as the
# Forgejo release to the tag (docs/DEPLOYMENT.md, "Releases"). Reads the first-parent history
# of main, changes nothing. Writes to stdout; the section headings move one level down:
#
#   scripts/changelog.sh [BIS] [VON] | sed 's/^## /### /'
#
# BIS: tag or commit of the new release. Default: origin/main.
# VON: tag or commit of the previous release. Default: the last v* tag before BIS, so
#      `scripts/changelog.sh v0.9.1` needs nothing else. Without any tag VON is required.
set -euo pipefail

BIS="${1:-origin/main}"
FORGE="https://git.verdigado.com/Netzbegruenung/gutgesagt"
GH="https://github.com/netzbegruenung/contentgruen"

ref_pruefen() {
  git rev-parse --verify -q "${1}^{commit}" >/dev/null || { echo "Ref $1 fehlt: erst git fetch origin --tags" >&2; exit 1; }
}

ref_pruefen "$BIS"
VON="${2:-}"
if [ -z "$VON" ]; then
  # BIS^ rather than BIS: if BIS carries the new tag itself, the previous one is wanted.
  # --exclude: a prerelease tag (v1.2.3-rc.1) is not a release to start from.
  VON="$(git describe --tags --abbrev=0 --match 'v*' --exclude '*-*' "${BIS}^" 2>/dev/null)" || {
    echo "Kein Tag vor $BIS: VON angeben, z. B. scripts/changelog.sh $BIS <commit>" >&2; exit 2; }
fi
ref_pruefen "$VON"
# Swapped or unrelated refs would yield an empty but plausible list.
git merge-base --is-ancestor "$VON" "$BIS" || {
  echo "$VON liegt nicht vor $BIS: Reihenfolge ist scripts/changelog.sh [BIS] [VON]" >&2; exit 2; }

bruch=(); neu=(); behoben=(); sonst=()

while IFS=$'\t' read -r sha subj; do
  nr=""  # set for a Forgejo PR, linked below
  if [[ $subj =~ ^Merge\ pull\ request\ \'(.*)\'\ \(#([0-9]+)\)\ from ]]; then
    # Forgejo merge commit
    titel="${BASH_REMATCH[1]}"; nr="${BASH_REMATCH[2]}"
  elif [[ $subj =~ ^Merge\ pull\ request\ \#([0-9]+)\ from ]]; then
    # GitHub merge commit from before the move to Forgejo; the PR title is the first body line
    gh_nr="${BASH_REMATCH[1]}"
    titel="$(git log -1 --format=%b "$sha" | sed -n '/./{p;q}')"
    titel="${titel:-$subj}"
    zeile="- ${titel} ([GitHub #${gh_nr}](${GH}/pull/${gh_nr}))"
  elif [[ $subj =~ ^(.*)\ \(#([0-9]+)\)$ ]]; then
    # Forgejo squash or rebase merge
    titel="${BASH_REMATCH[1]}"; nr="${BASH_REMATCH[2]}"
  else
    titel="$subj"
    zeile="- ${titel} (${sha:0:8})"
  fi
  if [ -n "$nr" ]; then zeile="- ${titel} ([#${nr}](${FORGE}/pulls/${nr}))"; fi
  if [[ $titel =~ ^[a-z]+(\([^\)]*\))?!: ]]; then bruch+=("$zeile")
  elif [[ $titel =~ ^feat ]]; then neu+=("$zeile")
  elif [[ $titel =~ ^fix ]]; then behoben+=("$zeile")
  else sonst+=("$zeile")
  fi
done < <(git log --first-parent --reverse --format='%H%x09%s' "$VON..$BIS")

ausgabe() { local kopf="$1"; shift; [ "$#" -eq 0 ] && return 0; printf '\n## %s\n\n' "$kopf"; printf '%s\n' "$@"; }

# Tag name if the commit carries one, else the short SHA.
benennen() { git describe --tags --exact-match "$1" 2>/dev/null || git rev-parse --short "$1"; }

echo "Stand: $(benennen "$BIS") ($(git log -1 --format=%cs "$BIS")), seit $(benennen "$VON") ($(git log -1 --format=%cs "$VON"))"
ausgabe "Breaking Changes" "${bruch[@]+"${bruch[@]}"}"
ausgabe "Neu" "${neu[@]+"${neu[@]}"}"
ausgabe "Behoben" "${behoben[@]+"${behoben[@]}"}"
ausgabe "Sonstiges" "${sonst[@]+"${sonst[@]}"}"

# Lists files added between VON and BIS that match the pathspecs, or "keine".
neue_dateien() {
  local dateien; dateien="$(git diff --name-only --diff-filter=A "$VON" "$BIS" -- "$@")"
  if [ -z "$dateien" ]; then echo " keine"; else echo; sed 's/^/  - `/; s/$/`/' <<<"$dateien"; fi
}

printf '\n## Migrationen und Betriebsschritte\n\n'
printf -- '- Datenbank-Migrationen laufen beim Start des Suchdienstes von selbst (docs/DEPLOYMENT.md, „Database migrations“). Neue Migrationen:'
neue_dateien "mvp/backend/postgres-app/migrations/*.sql"
printf -- '- Neue Skripte in `mvp/scripts/manual/` (Reihenfolge je README-Abschnitt):'
# Scripts only: example data and the README next to them are not operational steps.
neue_dateien 'mvp/scripts/manual/*.py' 'mvp/scripts/manual/*.sh' 'mvp/scripts/manual/*.sql'
