"""Tests der Skripte unter scripts/ (CI-Bericht, Woodpecker-Pipeline); laufen in scripts/check.sh."""

import pathlib
import sys

SKRIPTE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKRIPTE))
