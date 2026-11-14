"""Release-Tags nur ohne Platzhalter in DSE und Loeschkonzept (scripts/release_platzhalter.py)."""

import subprocess
import sys

import yaml

import release_platzhalter
from release_platzhalter import PLATZHALTER, WURZEL, fundstellen


def test_findet_den_platzhalter_mit_zeile(tmp_path):
    (tmp_path / "a.md").write_text(f"Kopf\nWer vor dem {PLATZHALTER} widerrufen hat\n", encoding="utf-8")
    (tmp_path / "b.html").write_text("Wer vor dem 1. Dezember 2026 widerrufen hat\n", encoding="utf-8")

    assert fundstellen(tmp_path, ("a.md", "b.html")) == [("a.md", 2)]


def test_ohne_platzhalter_nichts(tmp_path):
    (tmp_path / "a.md").write_text("Wer vor dem 1. Dezember 2026 widerrufen hat\n", encoding="utf-8")

    assert fundstellen(tmp_path, ("a.md",)) == []


def test_prueft_dse_und_loeschkonzept():
    for datei in release_platzhalter.DATEIEN:
        assert (WURZEL / datei).is_file(), datei
    assert any("datenschutz.component.html" in d for d in release_platzhalter.DATEIEN)
    assert "docs/LOESCHKONZEPT.md" in release_platzhalter.DATEIEN


def test_exit_code_folgt_dem_stand():
    lauf = subprocess.run(
        [sys.executable, str(WURZEL / "scripts/release_platzhalter.py")],
        capture_output=True, text=True, cwd=WURZEL,
    )
    assert lauf.returncode == (1 if fundstellen() else 0), lauf.stdout


def test_laeuft_in_ci_nur_bei_tags():
    ci = yaml.safe_load((WURZEL / ".woodpecker/ci.yaml").read_text())
    schritt = next(s for s in ci["steps"] if s["name"] == "release-platzhalter")

    assert schritt["when"] == [{"event": "tag"}]
    assert "python3 scripts/release_platzhalter.py" in " ".join(schritt["commands"])
