"""Report commits without the author's Signed-off-by (Developer Certificate of Origin).

Usage: sign_off.py --base <git ref> [--repo <path>]   (commits since the branch left <ref>)
Exit code 1 if a commit lacks a Signed-off-by trailer with its author's address, 2 if the
base cannot be read, else 0. Output names commit and subject only, no addresses: the CI
report posts it into the pull request.

Not checked for now, whether that stays is open (CONTRIBUTING.md, "Developer Certificate of
Origin"): merge commits, and commits a coding agent wrote, recognised by a Co-Authored-By
trailer with an address in AGENTEN_ADRESSEN.
"""

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTEN_ADRESSEN = {"noreply@anthropic.com"}
# Fields: hash, author address, subject, sign-off values, co-author values; one record per commit
_FORMAT = (
    "%h%x1f%ae%x1f%s"
    "%x1f%(trailers:key=Signed-off-by,valueonly,separator=%x1d)"
    "%x1f%(trailers:key=Co-authored-by,valueonly,separator=%x1d)%x1e"
)


def _adressen(werte):
    """The addresses of trailer values "Name <address>", lower case."""
    adressen = set()
    for wert in werte.split("\x1d"):
        start, ende = wert.rfind("<"), wert.rfind(">")
        if 0 <= start < ende:
            adressen.add(wert[start + 1 : ende].strip().lower())
    return adressen


def ohne_sign_off(repo, base):
    """(hash, subject) of every checked commit since ``base`` without its author's sign-off."""
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--no-merges", "--abbrev=12"]
        + [f"--format={_FORMAT}", f"{base}..HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for satz in filter(str.strip, out.split("\x1e")):
        sha, autor, betreff, sign_offs, co_autoren = satz.strip("\n").split("\x1f")
        if _adressen(co_autoren) & AGENTEN_ADRESSEN:
            continue
        if autor.lower() not in _adressen(sign_offs):
            yield sha, betreff


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--repo", default=str(ROOT))
    args = parser.parse_args(argv)
    try:
        treffer = list(ohne_sign_off(args.repo, args.base))
    except subprocess.CalledProcessError as fehler:
        sys.stderr.write(
            f"Cannot list the commits since {args.base}: {fehler.stderr.strip()}\n"
        )
        return 2
    for sha, betreff in treffer:
        sys.stdout.write(f"{sha} {betreff}\n")
    if treffer:
        sys.stdout.write(
            f"{len(treffer)} commit(s) without the author's Signed-off-by: sign off with "
            "git commit -s (CONTRIBUTING.md, Developer Certificate of Origin)\n"
        )
    return 1 if treffer else 0


if __name__ == "__main__":
    sys.exit(main())
