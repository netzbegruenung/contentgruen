"""
Der Neustart des nginx-Containers fuer den Webserver-Protokoll-Test (#383), ohne
Docker: Nur ein belegter Port fuehrt zu einem neuen Versuch.
"""

import subprocess

import pytest

from tests.integration import nginx


@pytest.mark.parametrize(
    ("fehler", "fehlschlaege", "starts"),
    [
        ("bind: address already in use", 1, 2),
        ("bind: address already in use", nginx.VERSUCHE, nginx.VERSUCHE),
        ("No such image", 1, 1),
    ],
)
def test_starten_neu_nur_bei_belegtem_port(monkeypatch, fehler, fehlschlaege, starts):
    """Hoechstens ``VERSUCHE`` Starts; jeder gescheiterte Container wird entfernt."""
    gestartet, entfernt = [], []

    def docker(*argumente, **_):
        gestartet.append(argumente[argumente.index("--name") + 1])
        if len(gestartet) <= fehlschlaege:
            raise RuntimeError(f"docker run: Exit 125: {fehler}")
        return "id"

    monkeypatch.setattr(nginx, "docker", docker)
    monkeypatch.setattr(nginx, "image", lambda: "nginx:alpine")
    monkeypatch.setattr(nginx, "entfernen", entfernt.append)

    if fehlschlaege >= starts:
        with pytest.raises(RuntimeError, match=fehler):
            nginx.starten("nginx.conf")
        assert entfernt == gestartet
    else:
        assert nginx.starten("nginx.conf") == gestartet[-1]
        assert entfernt == gestartet[:-1]

    assert len(gestartet) == starts
    assert len(set(gestartet)) == starts


def test_starten_entfernt_container_nach_timeout(monkeypatch):
    """Ein haengendes ``docker run`` hinterlaesst keinen Container und startet nicht neu."""
    gestartet, entfernt = [], []

    def docker(*argumente, **_):
        gestartet.append(argumente[argumente.index("--name") + 1])
        raise subprocess.TimeoutExpired("docker run", 300)

    monkeypatch.setattr(nginx, "docker", docker)
    monkeypatch.setattr(nginx, "image", lambda: "nginx:alpine")
    monkeypatch.setattr(nginx, "entfernen", entfernt.append)

    with pytest.raises(subprocess.TimeoutExpired):
        nginx.starten("nginx.conf")

    assert entfernt == gestartet and len(gestartet) == 1
