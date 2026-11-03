"""Image-Tags fuer den Build in Woodpecker (.woodpecker/build.yaml, release.yaml, #327).

Dieselben Tags wie zuvor docker/metadata-action in der GitHub-CI, damit Deployment und
Renovate unveraendert weiterlaufen:

- push auf main (und manuell): ``main`` und ``sha-<7 Zeichen>``
- Tag ``vX.Y.Z``: ``X.Y.Z``, ``X.Y`` und ``latest``; eine Vorabversion (``v1.2.3-rc.1``)
  bekommt nur ``1.2.3-rc.1``, damit sie ``latest`` und damit Produktion nie bewegt.

``IMAGE_TAG_PRAEFIX`` setzt vor jeden Tag einen Praefix, solange Woodpecker parallel zur
GitHub-CI baut und deren Tags nicht ueberschreiben darf.

Aufruf im Pipeline-Schritt: ``python3 scripts/image_tags.py <datei>``; liest
CI_PIPELINE_EVENT, CI_COMMIT_TAG und CI_COMMIT_SHA und schreibt je Tag eine Zeile, die das
Plugin docker-buildx mit ``tags_file`` liest. Nur Standardbibliothek.
"""

import os
import re
import sys

# SemVer 2.0.0 mit fuehrendem v, wie metadata-action type=semver es annahm
SEMVER = re.compile(
    r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?P<vorab>-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def image_tags(ereignis, git_tag, commit_sha, praefix=""):
    """Die Tags fuer ein Woodpecker-Ereignis; ValueError, wenn es keine geben darf."""
    if ereignis in ("push", "manual"):
        if not commit_sha:
            raise ValueError("Commit fehlt (CI_COMMIT_SHA)")
        tags = ["main", f"sha-{commit_sha[:7]}"]
    elif ereignis == "tag":
        treffer = SEMVER.match(git_tag)
        if not treffer:
            raise ValueError(f"Tag {git_tag!r} ist keine SemVer-Version vX.Y.Z")
        version = git_tag[1:].split("+", 1)[0]
        if treffer.group("vorab"):
            tags = [version]
        else:
            tags = [version, f"{treffer.group('major')}.{treffer.group('minor')}", "latest"]
    else:
        raise ValueError(f"Ereignis {ereignis!r} baut keine Images")
    return [praefix + tag for tag in tags]


def main(argumente):
    if len(argumente) != 1:
        print("Aufruf: image_tags.py <datei>", file=sys.stderr)
        return 2
    try:
        tags = image_tags(
            os.environ.get("CI_PIPELINE_EVENT", ""),
            os.environ.get("CI_COMMIT_TAG", ""),
            os.environ.get("CI_COMMIT_SHA", ""),
            os.environ.get("IMAGE_TAG_PRAEFIX", ""),
        )
    except ValueError as fehler:
        print(f"image_tags: {fehler}", file=sys.stderr)
        return 1
    with open(argumente[0], "w", encoding="utf-8") as datei:
        datei.write("".join(f"{tag}\n" for tag in tags))
    print("Image-Tags: " + ", ".join(tags))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
