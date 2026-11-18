"""Release-Tags nur ohne Platzhalter und mit passendem Stand-Datum (scripts/release_platzhalter.py)."""

import datetime
import os
import subprocess
import sys

import yaml

import release_platzhalter
from release_platzhalter import PLATZHALTER, WURZEL, fundstellen, stand_daten, zu_frueh

DSE_ZEILE = "<p><strong>Stand:</strong> 18. November 2026</p>\n"


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
    umgebung = {k: v for k, v in os.environ.items() if k != "CI_COMMIT_TAG"}
    lauf = subprocess.run(
        [sys.executable, str(WURZEL / "scripts/release_platzhalter.py")],
        capture_output=True, text=True, cwd=WURZEL, env=umgebung,
    )
    assert lauf.returncode == (1 if fundstellen() else 0), lauf.stdout


def test_laeuft_in_ci_nur_bei_tags():
    ci = yaml.safe_load((WURZEL / ".woodpecker/ci.yaml").read_text())
    schritt = next(s for s in ci["steps"] if s["name"] == "release-platzhalter")

    assert schritt["when"] == [{"event": "tag"}]
    assert "python3 scripts/release_platzhalter.py" in " ".join(schritt["commands"])


def test_liest_stand_und_widerrufsdatum(tmp_path):
    (tmp_path / "a.html").write_text(DSE_ZEILE + "Wer vor dem 2. März 2026 widerrufen hat\n", encoding="utf-8")

    assert stand_daten(tmp_path, ("a.html",)) == [
        ("a.html", 1, datetime.date(2026, 11, 18)),
        ("a.html", 2, datetime.date(2026, 3, 2)),
    ]


def test_datum_vor_dem_tag_lauf_ist_rot(tmp_path):
    (tmp_path / "a.html").write_text(DSE_ZEILE.replace("18.", "17."), encoding="utf-8")

    assert zu_frueh(datetime.date(2026, 11, 18), tmp_path, ("a.html",)) == [
        "a.html:1: 17.11.2026 liegt vor dem Tag-Lauf am 18.11.2026"
    ]


def test_datum_am_oder_nach_dem_tag_lauf_ist_gruen(tmp_path):
    (tmp_path / "a.html").write_text(DSE_ZEILE, encoding="utf-8")

    assert zu_frueh(datetime.date(2026, 11, 18), tmp_path, ("a.html",)) == []
    assert zu_frueh(datetime.date(2026, 11, 17), tmp_path, ("a.html",)) == []


def test_datei_ohne_datum_ist_rot(tmp_path):
    (tmp_path / "a.md").write_text("Kein Datum hier\n", encoding="utf-8")

    assert zu_frueh(datetime.date(2026, 11, 18), tmp_path, ("a.md",)) == ["a.md: kein Stand-Datum gefunden"]


def test_stichtag_nur_bei_den_tags_der_liste(monkeypatch, capsys):
    monkeypatch.setattr(release_platzhalter, "fundstellen", lambda: [])
    monkeypatch.setattr(release_platzhalter, "zu_frueh", lambda stichtag: [f"zu frueh fuer {stichtag}"])

    assert release_platzhalter.main(["--tag", "v9.9.9", "--stichtag", "2030-01-01"]) == 0
    assert release_platzhalter.main(["--tag", "v0.9.0", "--stichtag", "2030-01-01"]) == 1
    assert "zu frueh fuer 2030-01-01" in capsys.readouterr().out


def test_rechtstexte_haben_das_datum_des_produktionstags():
    """Die echten Dateien: DSE mit Stand und Widerrufsdatum, Loeschkonzept mit Widerrufsdatum."""
    assert zu_frueh(datetime.date(2026, 11, 18)) == []
    assert {datei for datei, _, _ in stand_daten()} == set(release_platzhalter.DATEIEN)
