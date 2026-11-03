"""Die Image-Tags, die Woodpecker beim Build und beim Release setzt (scripts/image_tags.py).

Gleiche Tags wie bisher die GitHub-CI (docker/metadata-action), damit Deployment und
Renovate unverändert weiterlaufen (#327).
"""

import pathlib
import subprocess
import sys

import pytest

from image_tags import image_tags

SKRIPT = pathlib.Path(__file__).resolve().parents[1] / "image_tags.py"

SHA = "3523b55f0e1d2c3b4a5968778695a4b3c2d1e0f9"


class TestPushAufMain:
    def test_main_und_kurzer_commit(self):
        assert image_tags("push", "", SHA) == ["main", "sha-3523b55"]

    def test_manueller_lauf_wie_push(self):
        assert image_tags("manual", "", SHA) == ["main", "sha-3523b55"]


class TestRelease:
    def test_version_minor_und_latest(self):
        assert image_tags("tag", "v0.9.0", SHA) == ["0.9.0", "0.9", "latest"]

    def test_vorabversion_nur_mit_voller_version(self):
        # metadata-action: Vorabversionen bekommen weder X.Y noch latest
        assert image_tags("tag", "v1.2.3-rc.1", SHA) == ["1.2.3-rc.1"]

    @pytest.mark.parametrize("tag", ["v1.2", "version-1", "1.2.3", "v1.2.3.4", ""])
    def test_tag_ohne_semver_bricht_ab(self, tag):
        with pytest.raises(ValueError, match="SemVer"):
            image_tags("tag", tag, SHA)


class TestPraefix:
    def test_praefix_vor_jedem_tag(self):
        # Parallelbetrieb neben der GitHub-CI: eigene Tags, keine fremden überschreiben
        assert image_tags("tag", "v0.9.0", SHA, praefix="woodpecker-") == [
            "woodpecker-0.9.0",
            "woodpecker-0.9",
            "woodpecker-latest",
        ]


class TestAndereEreignisse:
    @pytest.mark.parametrize("ereignis", ["pull_request", "cron", ""])
    def test_bricht_ab(self, ereignis):
        with pytest.raises(ValueError, match="Ereignis"):
            image_tags(ereignis, "", SHA)

    def test_ohne_commit_bricht_ab(self):
        with pytest.raises(ValueError, match="Commit"):
            image_tags("push", "", "")


class TestAufruf:
    def test_schreibt_eine_zeile_je_tag(self, tmp_path):
        datei = tmp_path / "tags"
        umgebung = {
            "CI_PIPELINE_EVENT": "tag",
            "CI_COMMIT_TAG": "v0.9.0",
            "CI_COMMIT_SHA": SHA,
            "IMAGE_TAG_PRAEFIX": "woodpecker-",
        }
        subprocess.run(
            [sys.executable, str(SKRIPT), str(datei)],
            check=True,
            env=umgebung,
        )
        assert datei.read_text() == "woodpecker-0.9.0\nwoodpecker-0.9\nwoodpecker-latest\n"

    def test_fehler_ohne_datei(self, tmp_path):
        datei = tmp_path / "tags"
        lauf = subprocess.run(
            [sys.executable, str(SKRIPT), str(datei)],
            env={"CI_PIPELINE_EVENT": "tag", "CI_COMMIT_TAG": "kaputt", "CI_COMMIT_SHA": SHA},
            capture_output=True,
            text=True,
        )
        assert lauf.returncode != 0
        assert "SemVer" in lauf.stderr
        assert not datei.exists()
