import ci_bericht


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
        [schritt("unit", 1, "\x1b[31mtoken=geheim123\x1b[0m\nweiter‮verdreht\n")],
        geheimnisse=["geheim123"],
    )

    assert "geheim123" not in text
    assert "token=[Secret entfernt]" in text
    assert "\x1b" not in text and "‮" not in text


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


def test_bericht_erstellen_bleibt_unter_der_grenze():
    lang = "".join("x" * 400 + "\n" for _ in range(80))
    schritte = [schritt(f"s{i}", 1, lang) for i in range(4)]

    text = bericht(schritte)

    assert len(text) <= ci_bericht.MAX_ZEICHEN
    assert all(f"`s{i}`" in text for i in range(4))


class _Forgejo:
    """Lokaler Stand-in fuer die Kommentar-API: merkt sich Anfragen, antwortet mit status."""

    def __init__(self, status):
        import http.server
        import threading

        forgejo = self
        self.anfragen = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                laenge = int(self.headers["Content-Length"])
                forgejo.anfragen.append(
                    (self.path, self.headers["Authorization"], self.rfile.read(laenge))
                )
                antwort = b'{"message": "token geheim123 ungueltig"}'
                self.send_response(status)
                self.send_header("Content-Length", str(len(antwort)))
                self.end_headers()
                self.wfile.write(antwort)

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


def _protokoll(tmp_path, name, status, log):
    (tmp_path / f"{name}.log").write_text(log)
    if status is not None:
        (tmp_path / f"{name}.status").write_text(f"{status}\n")


def test_main_kommentiert_rote_schritte_in_den_pr(tmp_path, capsys):
    import json

    _protokoll(tmp_path, "lint", 0, "ok\n")
    _protokoll(tmp_path, "unit", 1, "FAILED test_x\n")
    forgejo = _Forgejo(201)
    try:
        code = ci_bericht.main(["lint", "unit", "bff"], forgejo.env(), tmp_path)
    finally:
        forgejo.server.shutdown()

    assert code == 0
    ((pfad, auth, body),) = forgejo.anfragen
    assert pfad == "/api/v1/repos/Org/repo/issues/7/comments"
    assert auth == "token geheim123"
    text = json.loads(body)["body"]
    assert "FAILED test_x" in text and "Nicht gelaufen: `bff`" in text
    assert "HTTP 201" in capsys.readouterr().out


def test_main_meldet_bei_abgelehnter_anfrage_nur_den_status(tmp_path, capsys):
    _protokoll(tmp_path, "unit", 1, "FAILED\n")
    forgejo = _Forgejo(401)
    try:
        code = ci_bericht.main(["unit"], forgejo.env(), tmp_path)
    finally:
        forgejo.server.shutdown()

    ausgabe = capsys.readouterr()
    assert code == 1
    assert "HTTP 401" in ausgabe.err
    assert "geheim123" not in ausgabe.err + ausgabe.out


def test_main_ohne_token_sendet_nichts(tmp_path, capsys):
    _protokoll(tmp_path, "unit", 1, "FAILED\n")
    forgejo = _Forgejo(201)
    try:
        code = ci_bericht.main(["unit"], forgejo.env(token=""), tmp_path)
    finally:
        forgejo.server.shutdown()

    assert code == 0
    assert forgejo.anfragen == []
    assert "kein CI-Bericht" in capsys.readouterr().out
