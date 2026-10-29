"""
Die Vorabpruefung der Integrationssuite: Im Pflichtmodus (``check.sh --integration``)
bricht der Lauf ab, wenn Qdrant oder PostgreSQL fehlen, statt still zu ueberspringen.

Ein Dienst, der nicht lauscht, steht hier fuer einen fehlenden Stack; Port 9
(discard) ist auf einem Entwicklungsrechner zu.
"""

import pytest

from tests.integration import postgres, stack

ZU = "http://127.0.0.1:9"


@pytest.fixture
def docker_da(monkeypatch):
    monkeypatch.setattr(postgres, "docker_verfuegbar", lambda: True)


def test_fehlende_dienste_ohne_qdrant_nennt_qdrant_und_adresse(docker_da):
    fehlend = stack.fehlende_dienste(qdrant_url=ZU, env={})

    assert len(fehlend) == 1
    assert "Qdrant" in fehlend[0] and ZU in fehlend[0]


def test_fehlende_dienste_postgres_url_nicht_erreichbar(monkeypatch):
    monkeypatch.setattr(stack, "qdrant_erreichbar", lambda url: True)
    url = "postgresql+psycopg2://app_user:x@127.0.0.1:9/gutgesagt_app"

    fehlend = stack.fehlende_dienste(env={postgres.URL_VARIABLE: url})

    assert len(fehlend) == 1
    assert "PostgreSQL" in fehlend[0] and postgres.URL_VARIABLE in fehlend[0]


def test_fehlende_dienste_ohne_url_und_ohne_docker(monkeypatch):
    monkeypatch.setattr(stack, "qdrant_erreichbar", lambda url: True)
    monkeypatch.setattr(postgres, "docker_verfuegbar", lambda: False)

    fehlend = stack.fehlende_dienste(env={})

    assert len(fehlend) == 1
    assert "PostgreSQL" in fehlend[0] and "Docker" in fehlend[0]


def test_fehlende_dienste_alles_da_ist_leer(monkeypatch, docker_da):
    monkeypatch.setattr(stack, "qdrant_erreichbar", lambda url: True)

    assert stack.fehlende_dienste(env={}) == []


@pytest.mark.parametrize(
    "env, erwartet",
    [
        ({}, False),
        ({stack.PFLICHT_VARIABLE: "1"}, True),
        ({stack.PFLICHT_VARIABLE: "0"}, False),
        ({stack.PFLICHT_VARIABLE: ""}, False),
    ],
)
def test_pflicht_nur_mit_gesetzter_variable(env, erwartet):
    assert stack.pflicht(env) is erwartet


def test_bff_pflicht_im_pflichtmodus():
    assert stack.bff_pflicht({stack.PFLICHT_VARIABLE: "1"})


def test_bff_pflicht_nicht_in_der_ci():
    assert not stack.bff_pflicht({stack.PFLICHT_VARIABLE: "1", "CI": "woodpecker"})


def test_bff_pflicht_nicht_ohne_pflichtmodus():
    assert not stack.bff_pflicht({})


def test_docker_pflicht_im_pflichtmodus():
    assert stack.docker_pflicht({stack.PFLICHT_VARIABLE: "1"})


def test_docker_pflicht_nicht_in_der_ci():
    """Der CI-Runner hat keinen Docker-Socket (docs/CI.md, #460)."""
    assert not stack.docker_pflicht({stack.PFLICHT_VARIABLE: "1", "CI": "woodpecker"})


def test_docker_pflicht_nicht_ohne_pflichtmodus():
    assert not stack.docker_pflicht({})


def test_docker_ohne_erreichbaren_daemon_fehlt(monkeypatch):
    """``docker info`` endet ohne Daemon mitunter mit Exit 0 und leerer Version (#460)."""
    monkeypatch.setattr(postgres.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(postgres, "_docker", lambda *argumente, **_: "")
    assert not postgres.docker_verfuegbar()
