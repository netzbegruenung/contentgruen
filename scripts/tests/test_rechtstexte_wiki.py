"""
Die Übersicht der Rechtstext-Ablage im Wiki (#503): Nach jedem Merge auf main schreibt
scripts/rechtstexte_wiki.py die Seite neu. Geprüft gegen einen lokalen Stand-in für Forgejo.
"""

import base64
import json

import pytest

import rechtstexte_uebersicht as uebersicht
import rechtstexte_wiki as wiki

SEITE = "/api/v1/repos/Org/repo/wiki/page/Rechtstexte-%C3%9Cbersicht"
NEU = "/api/v1/repos/Org/repo/wiki/new"


class _Forgejo:
    """Antwortet auf GET mit ``get_status``, merkt sich POST/PATCH und antwortet darauf
    mit ``status``. Fehlerantworten enthalten den Token, wie Forgejo es tut."""

    def __init__(self, get_status, status):
        import http.server
        import threading

        forgejo = self
        self.abrufe = []
        self.schreiben = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def _antworten(self, code):
                antwort = b'{"message": "token geheim123"}'
                self.send_response(code)
                self.send_header("Content-Length", str(len(antwort)))
                self.end_headers()
                self.wfile.write(antwort)
                self.close_connection = True

            def do_GET(self):
                forgejo.abrufe.append((self.path, self.headers["Authorization"]))
                self._antworten(get_status)

            def _schreiben(self):
                laenge = int(self.headers["Content-Length"])
                forgejo.schreiben.append(
                    (
                        self.command,
                        self.path,
                        self.headers["Authorization"],
                        json.loads(self.rfile.read(laenge)),
                    )
                )
                self._antworten(status)

            do_POST = do_PATCH = _schreiben

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def env(self, token="geheim123"):
        return {
            "FORGEJO_TOKEN": token,
            "CI_FORGE_URL": self.url + "/",
            "CI_REPO_OWNER": "Org",
            "CI_REPO_NAME": "repo",
            "CI_COMMIT_SHA": "abc1234def5678",
        }


@pytest.fixture
def forgejo():
    gestartet = []

    def starten(get_status=200, status=200):
        gestartet.append(_Forgejo(get_status, status))
        return gestartet[-1]

    yield starten
    for f in gestartet:
        f.server.shutdown()


def _inhalt(daten):
    return base64.b64decode(daten["content_base64"]).decode()


@pytest.mark.parametrize(
    "titel, pfad",
    [
        # So legt Forgejo 17 die Seite an und so findet GET sie wieder (wiki_path.go)
        ("Rechtstexte Übersicht", "Rechtstexte-%C3%9Cbersicht"),
        ("Home", "Home"),
    ],
)
def test_seitenpfad_wie_forgejo_ihn_aus_dem_titel_bildet(titel, pfad):
    assert wiki.seitenpfad(titel) == pfad


def test_seitenpfad_lehnt_titel_mit_bindestrich_ab():
    # Forgejo haengte ".-" an; GET mit dem Titel faende die Seite nie wieder.
    with pytest.raises(ValueError):
        wiki.seitenpfad("Rechtstexte-Uebersicht")


def test_main_vorhandene_seite_wird_mit_der_uebersicht_ueberschrieben(forgejo, capsys):
    f = forgejo(get_status=200, status=200)

    assert wiki.main(f.env()) == 0

    assert f.abrufe == [(SEITE, "token geheim123")]
    ((methode, pfad, auth, daten),) = f.schreiben
    assert (methode, pfad, auth) == ("PATCH", SEITE, "token geheim123")
    assert daten["title"] == "Rechtstexte Übersicht"
    assert "abc1234" in daten["message"]
    inhalt = _inhalt(daten)
    assert inhalt.endswith(uebersicht.seite())
    kopf = inhalt.removesuffix(uebersicht.seite())
    # Woher die Seite kommt und wo man sie ändert
    assert f"{f.url}/Org/repo/src/commit/abc1234def5678/docs/rechtstexte-luecken" in kopf
    assert "docs/nutzungsbedingungen-staende" in kopf
    assert "Nicht hier bearbeiten" in kopf
    assert "HTTP 200" in capsys.readouterr().out


def test_main_fehlende_seite_wird_angelegt(forgejo):
    f = forgejo(get_status=404, status=201)

    assert wiki.main(f.env()) == 0

    ((methode, pfad, _, daten),) = f.schreiben
    assert (methode, pfad) == ("POST", NEU)
    assert daten["title"] == "Rechtstexte Übersicht"
    assert _inhalt(daten).endswith(uebersicht.seite())


def test_main_abgelehntes_schreiben_meldet_nur_den_status(forgejo, capsys):
    f = forgejo(get_status=200, status=403)

    assert wiki.main(f.env()) == 1

    ausgabe = capsys.readouterr()
    assert "HTTP 403" in ausgabe.err
    assert "geheim123" not in ausgabe.out + ausgabe.err


@pytest.mark.parametrize("get_status", [401, 500])
def test_main_seite_nicht_lesbar_schreibt_nichts(forgejo, capsys, get_status):
    f = forgejo(get_status=get_status)

    assert wiki.main(f.env()) == 1

    assert f.schreiben == []
    ausgabe = capsys.readouterr()
    assert f"HTTP {get_status}" in ausgabe.err
    assert "geheim123" not in ausgabe.out + ausgabe.err


def test_main_ohne_token_ist_rot_und_sendet_nichts(forgejo, capsys):
    f = forgejo()

    assert wiki.main(f.env(token="")) == 1

    assert f.abrufe == [] and f.schreiben == []
    assert "forgejo_wiki_token" in capsys.readouterr().err


def test_main_forgejo_nicht_erreichbar_ist_rot(capsys):
    env = {
        "FORGEJO_TOKEN": "geheim123",
        "CI_FORGE_URL": "http://127.0.0.1:9",
        "CI_REPO_OWNER": "Org",
        "CI_REPO_NAME": "repo",
        "CI_COMMIT_SHA": "abc1234",
    }

    assert wiki.main(env) == 1

    assert "fehlgeschlagen" in capsys.readouterr().err
