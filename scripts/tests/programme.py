"""
Tests, die ein Programm wie git aufrufen, verlangen es mit ``noetig``.

Das Python-Image der CI hat kein git (docs/CI.md). Dort ueberspringen sich solche
Tests sichtbar in den SKIPPED-Zeilen, wie die BFF-Tests der Integrationssuite.
Lokal ist ein fehlendes Programm ein Fehler: Sonst liefe check.sh still gruen,
ohne den Test je ausgefuehrt zu haben (#460).
"""

import os
import shutil
from typing import Mapping, Optional

import pytest


def noetig(programm: str, env: Optional[Mapping[str, str]] = None) -> None:
    env = os.environ if env is None else env
    if shutil.which(programm):
        return
    grund = f"{programm} fehlt"
    if env.get("CI"):
        pytest.skip(f"{grund} im CI-Image")
    pytest.fail(f"{grund}: lokal Pflicht, bitte installieren")
