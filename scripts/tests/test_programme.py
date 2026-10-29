"""programme.noetig: Ein fehlendes Programm ueberspringt in der CI, lokal ist es ein Fehler (#460)."""

import pytest

import programme


@pytest.fixture
def ohne_programm(monkeypatch):
    monkeypatch.setattr(programme.shutil, "which", lambda _: None)


def test_vorhandenes_programm_laesst_den_test_laufen(monkeypatch):
    monkeypatch.setattr(programme.shutil, "which", lambda name: f"/usr/bin/{name}")
    programme.noetig("git", env={"CI": "woodpecker"})


@pytest.mark.usefixtures("ohne_programm")
def test_fehlt_in_der_ci_ueberspringt_mit_grund():
    with pytest.raises(pytest.skip.Exception, match="git fehlt"):
        programme.noetig("git", env={"CI": "woodpecker"})


@pytest.mark.usefixtures("ohne_programm")
def test_fehlt_lokal_ist_ein_fehler():
    with pytest.raises(pytest.fail.Exception, match="git fehlt"):
        programme.noetig("git", env={})
