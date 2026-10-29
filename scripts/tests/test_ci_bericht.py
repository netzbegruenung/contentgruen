import json

import pytest

import ci_bericht

# Als chr(), nicht als Zeichen im Quelltext: Bidi-Steuerzeichen gehoeren nicht in den Code
RTL_OVERRIDE = chr(0x202E)


def schritt(name, exit_code, ausgabe):
    return ci_bericht.Schritt(name=name, exit_code=exit_code, ausgabe=ausgabe)


def bericht(schritte, geheimnisse=()):
    return ci_bericht.bericht_erstellen(
        pipeline="42",
        pipeline_url="https://ci.example/repos/1/pipeline/42",
        commit="abc123",
        schritte=schritte,
        geheimnisse=list(geheimnisse),
    )


def test_bericht_erstellen_nennt_rote_schritte_mit_ausgabe():
    text = bericht(
        [
            schritt("lint", 0, "alles gut\n"),
            schritt("unit", 1, "FAILED tests/unit/test_x.py::test_y\n"),
        ]
    )

    assert text.startswith(
        "*Automatischer CI-Bericht (Woodpecker, Pipeline `#42`), kein Agent*"
    )
    assert "abc123" in text
    assert "https://ci.example/repos/1/pipeline/42" in text
    assert "`unit`" in text and "Exit-Code 1" in text
    assert "FAILED tests/unit/test_x.py::test_y" in text
    assert "alles gut" not in text


def test_bericht_erstellen_entfernt_secret_ansi_und_steuerzeichen():
    text = bericht(
        [
            schritt(
                "unit",
                1,
                "\x1b[31mtoken=geheim123\x1b[0m\nweiter" + RTL_OVERRIDE + "verdreht\n",
            )
        ],
        geheimnisse=["geheim123"],
    )

    assert "geheim123" not in text
    assert "token=[Secret entfernt]" in text
    assert "\x1b" not in text and RTL_OVERRIDE not in text


def test_bericht_erstellen_fortschrittszeile_zeigt_letzten_stand():
    text = bericht([schritt("frontend", 1, "10%\r50%\r100% fertig\nFEHLER\n")])

    assert "100% fertig" in text
    assert "50%" not in text


def test_bericht_erstellen_zaun_laenger_als_backticks_der_ausgabe():
    text = bericht([schritt("lint", 1, "Beispiel:\n````\ncode\n````\n")])

    assert "`````text\n" in text


def test_bericht_erstellen_nennt_abgebrochene_und_nicht_gelaufene_schritte():
    text = bericht(
        [
            schritt("python-installieren", None, "Collecting torch\n"),
            schritt("unit", None, None),
            schritt("integration", None, None),
        ]
    )

    assert "`python-installieren`: abgebrochen" in text
    assert "Nicht gelaufen: `unit`, `integration`" in text


def test_bericht_erstellen_zeigt_nur_die_letzten_80_zeilen():
    ausgabe = "".join(f"zeile {i}\n" for i in range(1, 201))

    text = bericht([schritt("unit", 1, ausgabe)])

    assert "zeile 200" in text and "zeile 121\n" in text
    assert "zeile 120\n" not in text
    assert "120 davor ausgelassen" in text


def test_bericht_erstellen_kuerzt_ueberlange_zeilen_und_schliesst_jeden_block():
    schritte = [schritt(f"s{i}", 1, "y" * 50_000 + "\nENDE\n") for i in range(7)]

    text = bericht(schritte)

    assert len(text) <= ci_bericht.MAX_ZEICHEN
    # je Schritt ein Block mit der Fehlerzeile und einer mit dem Log
    assert text.count("```text\n") == 14
    assert text.count("\n```\n") == 14
    assert text.count("</details>") == 7


def test_bericht_erstellen_bleibt_unter_der_grenze():
    lang = "".join("x" * 400 + "\n" for _ in range(80))
    schritte = [schritt(f"s{i}", 1, lang) for i in range(4)]

    text = bericht(schritte)

    assert len(text) <= ci_bericht.MAX_ZEICHEN
    assert all(f"`s{i}`" in text for i in range(4))


def test_bericht_erstellen_klappt_log_ein_und_zeigt_fehlerzeilen_sichtbar():
    ausgabe = (
        "".join(f"zeile {i}\n" for i in range(30))
        + "FAILED tests/test_a.py::test_eins - assert 1 == 2\n"
        + "ERROR tests/test_b.py - ImportError\n"
        + "=== 1 failed, 1 error in 3.21s ===\n"
    )

    text = bericht([schritt("unit", 1, ausgabe)])

    sichtbar, log = text.split("<details><summary>Log unit</summary>", 1)
    assert "FAILED tests/test_a.py::test_eins" in sichtbar
    assert "ERROR tests/test_b.py" in sichtbar
    assert "zeile 3\n" not in sichtbar
    log = log.split("</details>", 1)[0]
    assert "zeile 3\n" in log and "=== 1 failed, 1 error" in log


def test_bericht_erstellen_ohne_failed_zeilen_zeigt_die_zusammenfassungszeile():
    ausgabe = "Executed 300 of 300 (2 FAILED) (4.1 secs / 3.9 secs)\n\n"
    ausgabe = "Kompiliere ...\n" + ausgabe

    text = bericht([schritt("frontend", 1, ausgabe)])

    sichtbar = text.split("<details>", 1)[0]
    assert "Executed 300 of 300 (2 FAILED)" in sichtbar
    assert "Kompiliere" not in sichtbar


def test_bericht_erstellen_traegt_unsichtbaren_fingerabdruck():
    schritte = [schritt("unit", 1, "FAILED test_x\n")]

    text = bericht(schritte)

    assert ci_bericht.fingerabdruck_lesen(text) == ci_bericht.fingerabdruck(
        schritte, []
    )
    assert "<!-- ci-bericht " in text


def test_fingerabdruck_ignoriert_laufzeiten_zeitstempel_und_log():
    erster = [
        schritt(
            "unit",
            1,
            "lauf 1\n2026-10-29T10:00:01Z FAILED test_x - in 0.52s\n"
            "=== 1 failed in 3.21s (0:00:03) ===\n",
        ),
        schritt("lint", 0, "ok\n"),
    ]
    zweiter = [
        schritt(
            "unit",
            1,
            "lauf 2, anderes Log\n2026-10-29T11:42:17Z FAILED test_x - in 0.61s\n"
            "=== 1 failed in 4.08s (0:00:04) ===\n",
        ),
        schritt("lint", 0, "anders, aber gruen\n"),
    ]

    assert ci_bericht.fingerabdruck(erster, []) == ci_bericht.fingerabdruck(zweiter, [])


def test_fingerabdruck_unterscheidet_fehlerzeilen_schritte_und_exit_code():
    basis = ci_bericht.fingerabdruck([schritt("unit", 1, "FAILED test_x\n")], [])

    assert basis != ci_bericht.fingerabdruck(
        [schritt("unit", 1, "FAILED test_y\n")], []
    )
    assert basis != ci_bericht.fingerabdruck(
        [schritt("lint", 1, "FAILED test_x\n")], []
    )
    assert basis != ci_bericht.fingerabdruck(
        [schritt("unit", 2, "FAILED test_x\n")], []
    )
    assert basis != ci_bericht.fingerabdruck(
        [schritt("unit", 1, "FAILED test_x\n"), schritt("bff", 1, "Failed!\n")], []
    )


def test_unveraendert_erstellen_ist_ein_einzeiler_mit_verweis():
    text = ci_bericht.unveraendert_erstellen(
        pipeline="43",
        pipeline_url="https://ci.example/43",
        commit="def456",
        fingerabdruck="f00",
        voriger_url="https://forge.example/pr/7#issuecomment-9",
    )

    sichtbar = text.split("<!--", 1)[0].strip()
    assert "\n" not in sichtbar
    assert "Unverändert rot" in sichtbar
    assert "`#43`" in sichtbar and "`def456`" in sichtbar
    assert "https://forge.example/pr/7#issuecomment-9" in sichtbar
    assert ci_bericht.fingerabdruck_lesen(text) == "f00"


class _Forgejo:
    """Lokaler Stand-in fuer die Kommentar-API: liefert ``kommentare`` auf GET (oder
    ``get_status``), merkt sich POSTs und antwortet darauf mit ``status``."""

    def __init__(self, status, kommentare=(), get_status=200):
        import http.server
        import threading

        forgejo = self
        self.anfragen = []
        self.abrufe = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def _antworten(self, code, antwort):
                self.send_response(code)
                self.send_header("Content-Length", str(len(antwort)))
                self.end_headers()
                self.wfile.write(antwort)

            def do_GET(self):
                forgejo.abrufe.append((self.path, self.headers["Authorization"]))
                if get_status != 200:
                    self._antworten(get_status, b'{"message": "token geheim123"}')
                else:
                    self._antworten(200, json.dumps(list(kommentare)).encode())

            def do_POST(self):
                laenge = int(self.headers["Content-Length"])
                forgejo.anfragen.append(
                    (self.path, self.headers["Authorization"], self.rfile.read(laenge))
                )
                self._antworten(status, b'{"message": "token geheim123 ungueltig"}')

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
            "CI_COMMIT_PULL_REQUEST": "7",
            "CI_COMMIT_SHA": "abc123",
            "CI_PIPELINE_NUMBER": "42",
            "CI_PIPELINE_URL": "https://ci.example/42",
        }


@pytest.fixture
def forgejo_mit_status():
    """Startet je Aufruf einen lokalen Stand-in; raeumt danach ab."""
    gestartet = []

    def starten(status, **kwargs):
        gestartet.append(_Forgejo(status, **kwargs))
        return gestartet[-1]

    yield starten
    for forgejo in gestartet:
        forgejo.server.shutdown()


def _protokoll(tmp_path, name, status, log):
    (tmp_path / f"{name}.log").write_text(log)
    if status is not None:
        (tmp_path / f"{name}.status").write_text(f"{status}\n")


def test_main_kommentiert_rote_schritte_in_den_pr(tmp_path, capsys, forgejo_mit_status):
    _protokoll(tmp_path, "lint", 0, "ok\n")
    _protokoll(tmp_path, "unit", 1, "FAILED test_x\n")
    forgejo = forgejo_mit_status(201)

    code = ci_bericht.main(["lint", "unit", "bff"], forgejo.env(), tmp_path)

    assert code == 0
    ((pfad, auth, body),) = forgejo.anfragen
    assert pfad == "/api/v1/repos/Org/repo/issues/7/comments"
    assert auth == "token geheim123"
    text = json.loads(body)["body"]
    assert "FAILED test_x" in text and "Nicht gelaufen: `bff`" in text
    assert "HTTP 201" in capsys.readouterr().out


def test_main_meldet_bei_abgelehnter_anfrage_nur_den_status(
    tmp_path, capsys, forgejo_mit_status
):
    _protokoll(tmp_path, "unit", 1, "FAILED\n")
    forgejo = forgejo_mit_status(401)

    code = ci_bericht.main(["unit"], forgejo.env(), tmp_path)

    ausgabe = capsys.readouterr()
    assert code == 1
    assert "HTTP 401" in ausgabe.err
    assert "geheim123" not in ausgabe.err + ausgabe.out


def test_main_ohne_token_sendet_nichts(tmp_path, capsys, forgejo_mit_status):
    _protokoll(tmp_path, "unit", 1, "FAILED\n")
    forgejo = forgejo_mit_status(201)

    code = ci_bericht.main(["unit"], forgejo.env(token=""), tmp_path)

    assert code == 0
    assert forgejo.anfragen == []
    assert "kein CI-Bericht" in capsys.readouterr().out


def _kommentar(nr, body):
    return {
        "id": nr,
        "body": body,
        "html_url": f"https://forge.example/pr/7#issuecomment-{nr}",
    }


def _gesendet(forgejo):
    ((pfad, _, body),) = forgejo.anfragen
    assert pfad == "/api/v1/repos/Org/repo/issues/7/comments"
    return json.loads(body)["body"]


def test_main_liest_vorher_die_kommentare_des_prs(tmp_path, forgejo_mit_status):
    _protokoll(tmp_path, "unit", 1, "FAILED test_x\n")
    forgejo = forgejo_mit_status(201)

    ci_bericht.main(["unit"], forgejo.env(), tmp_path)

    assert forgejo.abrufe == [
        ("/api/v1/repos/Org/repo/issues/7/comments", "token geheim123")
    ]


def test_main_gleicher_fehler_wie_letzter_bericht_postet_nur_einen_einzeiler(
    tmp_path, capsys, forgejo_mit_status
):
    _protokoll(tmp_path, "unit", 1, "lange Ausgabe\nFAILED test_x - in 0.5s\n")
    voriger = ci_bericht.bericht_erstellen(
        "41",
        "https://ci.example/41",
        "aaa111",
        [schritt("unit", 1, "andere Ausgabe\nFAILED test_x - in 0.7s\n")],
        [],
    )
    forgejo = forgejo_mit_status(
        201, kommentare=[_kommentar(1, "Mensch: schau mal"), _kommentar(5, voriger)]
    )

    code = ci_bericht.main(["unit"], forgejo.env(), tmp_path)

    assert code == 0
    text = _gesendet(forgejo)
    assert "Unverändert rot" in text and "issuecomment-5" in text
    assert "lange Ausgabe" not in text and "<details>" not in text
    assert "unverändert" in capsys.readouterr().out


def test_main_vergleicht_nur_mit_dem_letzten_bericht(tmp_path, forgejo_mit_status):
    _protokoll(tmp_path, "unit", 1, "FAILED test_x\n")
    gleich = ci_bericht.bericht_erstellen(
        "40", "u", "a", [schritt("unit", 1, "FAILED test_x\n")], []
    )
    anders = ci_bericht.bericht_erstellen(
        "41", "u", "b", [schritt("unit", 1, "FAILED test_y\n")], []
    )
    forgejo = forgejo_mit_status(
        201, kommentare=[_kommentar(1, gleich), _kommentar(2, anders)]
    )

    ci_bericht.main(["unit"], forgejo.env(), tmp_path)

    text = _gesendet(forgejo)
    assert "<details><summary>Log unit</summary>" in text


def test_main_folgt_auf_einen_einzeiler_wieder_ein_einzeiler(
    tmp_path, forgejo_mit_status
):
    _protokoll(tmp_path, "unit", 1, "FAILED test_x\n")
    fp = ci_bericht.fingerabdruck([schritt("unit", 1, "FAILED test_x\n")], [])
    einzeiler = ci_bericht.unveraendert_erstellen("41", "u", "b", fp, "https://x/3")
    forgejo = forgejo_mit_status(201, kommentare=[_kommentar(4, einzeiler)])

    ci_bericht.main(["unit"], forgejo.env(), tmp_path)

    assert "Unverändert rot" in _gesendet(forgejo)


def test_main_kommentare_nicht_lesbar_postet_den_vollen_bericht(
    tmp_path, capsys, forgejo_mit_status
):
    _protokoll(tmp_path, "unit", 1, "FAILED test_x\n")
    forgejo = forgejo_mit_status(201, get_status=401)

    code = ci_bericht.main(["unit"], forgejo.env(), tmp_path)

    assert code == 0
    assert "<details><summary>Log unit</summary>" in _gesendet(forgejo)
    ausgabe = capsys.readouterr()
    assert "HTTP 401" in ausgabe.err
    assert "geheim123" not in ausgabe.err + ausgabe.out
