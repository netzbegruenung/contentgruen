import socket

import ci_dienste_warten


def test_main_meldet_erreichbare_dienste(capsys):
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]

        assert ci_dienste_warten.main([f"127.0.0.1:{port}"]) == 0

    assert "Erreichbar: 127.0.0.1:" in capsys.readouterr().out


def test_main_bricht_nach_dem_zeitlimit_ab(monkeypatch, capsys):
    monkeypatch.setattr(ci_dienste_warten, "WARTEN_S", 0)
    monkeypatch.setattr(ci_dienste_warten, "erreichbar", lambda adresse: False)

    assert ci_dienste_warten.main(["qdrant:6333"]) == 1
    assert "Nicht erreichbar nach 0 s: qdrant:6333" in capsys.readouterr().out


def test_main_ohne_adressen_ist_ein_aufruffehler(capsys):
    assert ci_dienste_warten.main([]) == 2
    assert "Aufruf:" in capsys.readouterr().out
