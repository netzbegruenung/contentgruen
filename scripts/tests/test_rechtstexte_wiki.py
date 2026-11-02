"""
Die Übersicht der Rechtstext-Ablage im Wiki (#503): Nach jedem Merge auf main schreibt
scripts/rechtstexte_wiki.py die Seite neu. Geprüft gegen einen lokalen Stand-in für Forgejo.
"""

import base64
import json
import socket

import pytest

import rechtstexte_uebersicht as uebersicht
import rechtstexte_wiki as wiki

SEITE = "/api/v1/repos/Org/repo/wiki/page/Rechtstexte-%C3%9Cbersicht"
NEU = "/api/v1/repos/Org/repo/wiki/new"
MAIN = "/api/v1/repos/Org/repo/branches/main"
COMMIT = "abc1234def5678"


class _Forgejo:
    """Antwortet auf GET der Seite mit ``get_status`` und ``inhalt``, auf GET von main mit
    dem Kopf ``kopf``, merkt sich POST/PATCH und antwortet darauf mit ``status``.
    Fehlerantworten enthalten den Token, wie Forgejo es tut."""

    def __init__(self, get_status, status, kopf=COMMIT, inhalt="alter Stand"):
        import http.server
        import threading

        forgejo = self
        self.abrufe = []
        self.schreiben = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def _antworten(self, code, antwort=b'{"message": "token geheim123"}'):
                self.send_response(code)
                self.send_header("Content-Length", str(len(antwort)))
                self.end_headers()
                self.wfile.write(antwort)
                self.close_connection = True

            def do_GET(self):
                forgejo.abrufe.append((self.path, self.headers["Authorization"]))
                if self.path == MAIN:
                    # kopf=None: Antwort ohne Commit, wie bei einer kaputten Antwort
                    roh = {} if kopf is None else {"commit": {"id": kopf}}
                    self._antworten(200, json.dumps(roh).encode())
                elif get_status == 200:
                    roh = base64.b64encode(inhalt.encode()).decode()
                    self._antworten(200, json.dumps({"content_base64": roh}).encode())
                else:
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
            "CI_COMMIT_SHA": COMMIT,
        }


@pytest.fixture
def forgejo():
    gestartet = []

    def starten(get_status=200, status=200, **kwargs):
        gestartet.append(_Forgejo(get_status, status, **kwargs))
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

    assert f.abrufe == [(MAIN, "token geheim123"), (SEITE, "token geheim123")]
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


def test_main_unveraenderte_tabellen_werden_nicht_geschrieben(forgejo, capsys):
    # Die meisten Pushes auf main beruehren die Ablage nicht: kein neuer Wiki-Commit.
    f = forgejo(inhalt="Kopf eines frueheren Commits\n\n" + uebersicht.seite())

    assert wiki.main(f.env()) == 0

    assert f.schreiben == []
    assert "unveraendert" in capsys.readouterr().out


def test_main_aelterer_lauf_schreibt_nicht(forgejo, capsys):
    # Zwei Merges kurz nacheinander: Der Lauf zum aelteren Commit darf die Seite des
    # neueren nicht ueberschreiben, auch wenn er zuletzt fertig wird.
    f = forgejo(kopf="fff9999neuer")

    assert wiki.main(f.env()) == 0

    assert f.abrufe == [(MAIN, "token geheim123")] and f.schreiben == []
    assert "nicht mehr der Kopf von main" in capsys.readouterr().out


def test_main_kopf_von_main_nicht_lesbar_ist_rot(forgejo, capsys):
    f = forgejo(kopf=None)

    assert wiki.main(f.env()) == 1

    assert f.schreiben == []
    assert "Kopf von main lesen" in capsys.readouterr().err


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
    # Ein eben freigegebener Port: Dort lauscht sicher nichts.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {
        "FORGEJO_TOKEN": "geheim123",
        "CI_FORGE_URL": f"http://127.0.0.1:{port}",
        "CI_REPO_OWNER": "Org",
        "CI_REPO_NAME": "repo",
        "CI_COMMIT_SHA": "abc1234",
    }

    assert wiki.main(env) == 1

    assert "fehlgeschlagen" in capsys.readouterr().err
