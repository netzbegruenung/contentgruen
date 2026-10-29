"""Report retired words in added lines.

Usage: retired_words.py --base <git ref>   (lines added since the merge base with <ref>)
       retired_words.py --staged           (lines added in the index; used by pre-commit)
Exit code 1 if a retired word appears in an added line, else 0.
A line that must keep a retired word (a link, a quote) carries the marker "retired-ok".
"""

import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIST = ROOT / "scripts" / "retired-words.txt"
# Historical and generated material keeps its original wording. CHANGELOG.md quotes the
# titles of merged pull requests as they were.
SKIP = (
    "CHANGELOG.md",
    "docs/archiv/",
    "mvp/backend/postgres-app/migrations/",
    "scripts/retired-words.txt",
    "GLOSSARY.md",
    "COPYRIGHT",
    "package-lock.json",
)


def load_rules():
    rules = []
    for line in LIST.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        pattern, _, instead = line.partition(" -> ")
        rules.append((re.compile(pattern.strip(), re.IGNORECASE), instead.strip()))
    return rules


def added_lines(args):
    if args.staged:
        cmd = ["git", "diff", "--cached", "-U0", "--no-color"]
    else:
        cmd = ["git", "diff", "-U0", "--no-color", f"{args.base}...HEAD"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    path, lineno = None, 0
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            lineno = int(re.search(r"\+(\d+)", line).group(1))
        elif line.startswith("+") and path:
            yield path, lineno, line[1:]
            lineno += 1


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--base")
    group.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    rules = load_rules()
    hits = 0
    for path, lineno, text in added_lines(args):
        if path.startswith(SKIP) or "retired-ok" in text:
            continue
        for rx, instead in rules:
            m = rx.search(text)
            if m:
                hits += 1
                sys.stdout.write(f"{path}:{lineno}: '{m.group(0)}' -> {instead}\n")
    if hits:
        sys.stdout.write(f"{hits} retired word(s) in added lines (see scripts/retired-words.txt)\n")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
