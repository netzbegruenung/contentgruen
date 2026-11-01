"""scripts/sign_off.py: Signed-off-by (DCO) in den Commits eines PRs."""

import pathlib
import subprocess
import sys

import pytest

import programme

SKRIPT = pathlib.Path(__file__).resolve().parent.parent / "sign_off.py"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path):
    """Ein Repo mit main und dem PR-Branch pr, der von main abzweigt."""
    programme.noetig("git")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "Erika Muster")
    git(tmp_path, "config", "user.email", "erika@example.org")
    git(tmp_path, "config", "commit.gpgsign", "false")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "chore: Anfang")
    git(tmp_path, "checkout", "-q", "-b", "pr")
    return tmp_path


def commit(repo, nachricht, *optionen):
    git(repo, "commit", "-q", "--allow-empty", *optionen, "-m", nachricht)


def pruefen(repo):
    return subprocess.run(
        [sys.executable, str(SKRIPT), "--base", "main", "--repo", str(repo)],
        capture_output=True,
        text=True,
    )


def test_commit_ohne_sign_off_wird_gemeldet(repo):
    commit(repo, "feat: ohne Sign-off")

    ergebnis = pruefen(repo)

    assert ergebnis.returncode == 1
    sha = git(repo, "rev-parse", "--short=12", "HEAD").strip()
    assert f"{sha} feat: ohne Sign-off" in ergebnis.stdout
    assert ergebnis.stdout.splitlines()[-1].startswith("1 commit(s) without")


def test_commit_mit_sign_off_des_autors_besteht(repo):
    commit(repo, "feat: mit Sign-off", "-s")

    ergebnis = pruefen(repo)

    assert (ergebnis.returncode, ergebnis.stdout) == (0, "")


def test_adresse_im_sign_off_ohne_ruecksicht_auf_gross_und_klein(repo):
    commit(repo, "feat: gross\n\nSigned-off-by: Erika Muster <Erika@Example.ORG>")

    assert pruefen(repo).returncode == 0


def test_sign_off_einer_anderen_person_reicht_nicht(repo):
    commit(repo, "feat: fremd\n\nSigned-off-by: Max Muster <max@example.org>")

    assert pruefen(repo).returncode == 1


def test_commits_der_basis_werden_nicht_geprueft(repo):
    git(repo, "checkout", "-q", "main")
    commit(repo, "chore: auf main ohne Sign-off")
    git(repo, "checkout", "-q", "pr")
    commit(repo, "feat: mit Sign-off", "-s")

    assert pruefen(repo).returncode == 0


def test_agenten_commits_sind_ausgenommen(repo):
    commit(
        repo,
        "feat: vom Agenten\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
    )

    assert pruefen(repo).returncode == 0


def test_menschliche_co_autoren_ersetzen_den_sign_off_nicht(repo):
    commit(repo, "feat: zu zweit\n\nCo-Authored-By: Max Muster <max@example.org>")

    assert pruefen(repo).returncode == 1


def test_unbekannte_basis_ist_ein_aufruffehler(repo):
    commit(repo, "feat: mit Sign-off", "-s")

    ergebnis = subprocess.run(
        [sys.executable, str(SKRIPT), "--base", "origin/fehlt", "--repo", str(repo)],
        capture_output=True,
        text=True,
    )

    assert ergebnis.returncode == 2
    assert "origin/fehlt" in ergebnis.stderr
    assert "Traceback" not in ergebnis.stderr


def test_merge_commits_sind_ausgenommen(repo):
    commit(repo, "feat: mit Sign-off", "-s")
    git(repo, "checkout", "-q", "main")
    commit(repo, "chore: weiter auf main", "-s")
    git(repo, "checkout", "-q", "pr")
    git(repo, "merge", "-q", "--no-ff", "main", "-m", "Merge branch 'main' into pr")

    assert pruefen(repo).returncode == 0
