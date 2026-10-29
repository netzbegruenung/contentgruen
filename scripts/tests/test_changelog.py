"""scripts/changelog.sh: Änderungsliste für das Forgejo-Release aus der Merge-Historie."""

import pathlib
import subprocess

import pytest

import programme

SKRIPT = pathlib.Path(__file__).resolve().parent.parent / "changelog.sh"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path):
    programme.noetig("git")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "commit.gpgsign", "false")
    git(tmp_path, "config", "tag.gpgsign", "false")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "chore: Anfang")
    return tmp_path


def merge(repo, titel, nr):
    """Ein PR wie Forgejo ihn merged: Merge-Commit auf main mit dem PR-Titel."""
    git(repo, "checkout", "-q", "-b", f"pr{nr}")
    git(repo, "commit", "-q", "--allow-empty", "-m", titel)
    git(repo, "checkout", "-q", "main")
    git(
        repo, "merge", "-q", "--no-ff", f"pr{nr}",
        "-m", f"Merge pull request '{titel}' (#{nr}) from sb/pr{nr} into main",
    )


def changelog(repo, *args):
    return subprocess.run(
        ["bash", str(SKRIPT), *args], cwd=repo, capture_output=True, text=True
    )


def test_ohne_tag_und_ohne_von_ist_ein_aufruffehler(repo):
    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 2
    assert "Kein Tag" in ergebnis.stderr
    assert ergebnis.stdout == ""


def test_ohne_von_listet_die_prs_seit_dem_letzten_tag(repo):
    merge(repo, "feat: Alt", 1)
    git(repo, "tag", "v0.1.0")
    merge(repo, "fix(suche): Leere Treffer", 2)
    merge(repo, "feat(bild): Unterschrift", 3)

    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "Alt" not in ergebnis.stdout
    forge = "https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls"
    assert (
        "## Neu\n\n"
        f"- feat(bild): Unterschrift ([#3]({forge}/3))\n"
        "\n## Behoben\n\n"
        f"- fix(suche): Leere Treffer ([#2]({forge}/2))\n"
    ) in ergebnis.stdout


def test_ist_bis_selbst_getaggt_zaehlt_der_tag_davor(repo):
    merge(repo, "feat: Alt", 1)
    git(repo, "tag", "v0.1.0")
    merge(repo, "feat: Neu", 2)
    git(repo, "tag", "v0.2.0")

    ergebnis = changelog(repo, "v0.2.0")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "feat: Neu" in ergebnis.stdout
    assert "feat: Alt" not in ergebnis.stdout


def test_breaking_changes_und_neue_migrationen(repo):
    git(repo, "tag", "v0.1.0")
    migrationen = repo / "mvp/backend/postgres-app/migrations"
    migrationen.mkdir(parents=True)
    (migrationen / "2026-10-20_spalte.sql").write_text("SELECT 1;\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "feat(db)!: Spalte umbenannt")

    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "## Breaking Changes\n\n- feat(db)!: Spalte umbenannt (" in ergebnis.stdout
    assert "## Neu" not in ergebnis.stdout
    assert "  - `mvp/backend/postgres-app/migrations/2026-10-20_spalte.sql`" in (
        ergebnis.stdout
    )


def test_ohne_neue_migrationen_steht_keine_da(repo):
    git(repo, "tag", "v0.1.0")
    merge(repo, "docs: Anleitung", 1)

    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "## Sonstiges" in ergebnis.stdout
    assert "## Breaking Changes" not in ergebnis.stdout
    assert "Neue Migrationen: keine" in ergebnis.stdout


def test_von_als_zweites_argument_ohne_tag(repo):
    anfang = git(repo, "rev-parse", "HEAD").strip()
    merge(repo, "feat: Erstes Release", 1)

    ergebnis = changelog(repo, "main", anfang)

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "- feat: Erstes Release ([#1](" in ergebnis.stdout


def test_squash_merge_wird_als_pr_verlinkt(repo):
    git(repo, "tag", "v0.1.0")
    git(repo, "commit", "-q", "--allow-empty", "-m", "fix: Knopf (#7)")

    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 0, ergebnis.stderr
    forge = "https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls"
    assert f"## Behoben\n\n- fix: Knopf ([#7]({forge}/7))\n" in ergebnis.stdout


def test_vertauschte_argumente_sind_ein_aufruffehler(repo):
    git(repo, "tag", "v0.1.0")
    merge(repo, "feat: Neu", 1)

    ergebnis = changelog(repo, "v0.1.0", "main")

    assert ergebnis.returncode == 2
    assert "liegt nicht vor" in ergebnis.stderr
    assert ergebnis.stdout == ""


def test_prerelease_tag_ist_kein_startpunkt(repo):
    merge(repo, "feat: Alt", 1)
    git(repo, "tag", "v0.1.0")
    merge(repo, "feat: Kandidat", 2)
    git(repo, "tag", "v0.2.0-rc.1")
    merge(repo, "fix: Danach", 3)

    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "feat: Kandidat" in ergebnis.stdout
    assert "seit v0.1.0" in ergebnis.stdout


def test_getaggtes_bis_steht_mit_tag_namen_im_kopf(repo):
    git(repo, "tag", "v0.1.0")
    merge(repo, "feat: Neu", 1)
    git(repo, "tag", "v0.2.0")

    ergebnis = changelog(repo, "v0.2.0")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.startswith("Stand: v0.2.0 (")
    assert "seit v0.1.0 (" in ergebnis.stdout


def test_nur_skripte_aus_manual_gelten_als_neue_skripte(repo):
    git(repo, "tag", "v0.1.0")
    manual = repo / "mvp/scripts/manual"
    manual.mkdir(parents=True)
    (manual / "aufraeumen.py").write_text("print(1)\n")
    (manual / "beispiel.csv").write_text("a,b\n")
    (manual / "README.md").write_text("# Manual\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "feat: Aufräumskript")

    ergebnis = changelog(repo, "main")

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "  - `mvp/scripts/manual/aufraeumen.py`" in ergebnis.stdout
    assert "beispiel.csv" not in ergebnis.stdout
    assert "README.md" not in ergebnis.stdout
