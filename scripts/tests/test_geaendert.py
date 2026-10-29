"""
check.sh --geaendert: welche Schritte eine Aenderung braucht (scripts/geaendert.py).

Jeder Test legt einen kleinen Baum mit den Pfaden des Repos unter tmp_path an.
"""

import pytest

import geaendert

FE = "mvp/frontend/gutgesagt-frontend"


@pytest.fixture
def baum(tmp_path):
    def anlegen(dateien: dict[str, str]):
        for pfad, inhalt in dateien.items():
            datei = tmp_path / pfad
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(inhalt)
        return tmp_path

    return anlegen


def test_waehlen_reine_frontend_aenderung_nur_frontend(baum):
    wurzel = baum(
        {
            f"{FE}/src/app/a/a.component.ts": "export class A {}\n",
            f"{FE}/src/app/a/a.component.spec.ts": "import { A } from './a.component';\n",
        }
    )

    auswahl = geaendert.waehlen([f"{FE}/src/app/a/a.component.ts"], wurzel)

    assert auswahl.schritte == ["retired-words", "frontend"]
    assert auswahl.specs == ["src/app/a/a.component.spec.ts"]


def test_waehlen_frontend_auch_specs_die_ueber_andere_importieren(baum):
    wurzel = baum(
        {
            f"{FE}/src/app/shared/s.service.ts": "export class S {}\n",
            f"{FE}/src/app/b/b.component.ts": "import { S } from '../shared/s.service';\n",
            f"{FE}/src/app/b/b.component.spec.ts": "import { B } from './b.component';\n",
            f"{FE}/src/app/c/c.spec.ts": "import { X } from './c';\n",
            f"{FE}/src/app/c/c.ts": "export class X {}\n",
        }
    )

    auswahl = geaendert.waehlen([f"{FE}/src/app/shared/s.service.ts"], wurzel)

    assert auswahl.specs == ["src/app/b/b.component.spec.ts"]


def test_waehlen_frontend_template_gehoert_zur_komponente(baum):
    wurzel = baum(
        {
            f"{FE}/src/app/a/a.component.ts": "export class A {}\n",
            f"{FE}/src/app/a/a.component.html": "<p></p>\n",
            f"{FE}/src/app/a/a.component.spec.ts": 'import { A } from "./a.component";\n',
        }
    )

    auswahl = geaendert.waehlen([f"{FE}/src/app/a/a.component.html"], wurzel)

    assert auswahl.specs == ["src/app/a/a.component.spec.ts"]


@pytest.mark.parametrize(
    "pfad",
    [f"{FE}/package.json", f"{FE}/src/styles.css", f"{FE}/src/app/geloescht.ts"],
)
def test_waehlen_frontend_ausserhalb_der_komponenten_alle_specs(baum, pfad):
    wurzel = baum({f"{FE}/src/app/a/a.spec.ts": "\n", f"{FE}/package.json": "{}"})

    auswahl = geaendert.waehlen([pfad], wurzel)

    assert auswahl.schritte == ["retired-words", "frontend"]
    assert auswahl.specs is None
    assert "alle Specs" in auswahl.gruende["frontend"][0]


def test_waehlen_frontend_ohne_erreichte_spec_alle_specs(baum):
    wurzel = baum({f"{FE}/src/app/a/a.ts": "export const a = 1;\n"})

    assert geaendert.waehlen([f"{FE}/src/app/a/a.ts"], wurzel).specs is None


PY = "mvp/backend/semantic-search-service"


@pytest.mark.parametrize(
    "pfad, schritte",
    [
        (f"{PY}/app/services/x.py", ["retired-words", "lint", "unit"]),
        (f"{PY}/app/tests/unit/test_x.py", ["retired-words", "lint", "unit"]),
        (f"{PY}/app/repositories/x.py", ["retired-words", "lint", "unit", "integration"]),
        (
            f"{PY}/app/infrastructure/database/models.py",
            ["retired-words", "lint", "unit", "integration"],
        ),
        (
            f"{PY}/app/tests/integration/test_x.py",
            ["retired-words", "lint", "unit", "integration"],
        ),
        (f"{PY}/requirements.txt", ["retired-words", "lint", "unit", "integration"]),
        (
            "mvp/backend/postgres-app/migrations/2026-10-30-x.sql",
            ["retired-words", "lint", "unit", "integration"],
        ),
        ("mvp/backend/BFF/Program.cs", ["retired-words", "bff"]),
        ("mvp/backend/BFF.Tests/XTests.cs", ["retired-words", "bff"]),
        ("docs/CI.md", ["retired-words"]),
        ("GLOSSARY.md", ["retired-words"]),
        ("docs/adr/0001-x.md", ["retired-words"]),
    ],
)
def test_waehlen_schritte_nach_pfad(baum, pfad, schritte):
    auswahl = geaendert.waehlen([pfad], baum({}))

    assert auswahl.schritte == schritte
    assert all(auswahl.gruende[s] for s in schritte)


@pytest.mark.parametrize(
    "pfad", ["scripts/check.sh", ".woodpecker/ci.yaml", "mvp/docker-compose.dev.yml"]
)
def test_waehlen_skripte_pipeline_und_unbekanntes_alles(baum, pfad):
    auswahl = geaendert.waehlen([pfad], baum({}))

    assert auswahl.schritte == geaendert.SCHRITTE
    assert auswahl.specs is None
    assert pfad in auswahl.gruende["bff"][0]


def test_waehlen_frontend_datei_die_ein_python_test_liest_auch_unit(baum):
    wurzel = baum(
        {
            f"{FE}/src/app/shared/meldegruende.ts": "export const M = [];\n",
            f"{PY}/app/tests/unit/test_m.py": 'Q = "src/app/shared/meldegruende.ts"\n',
            "scripts/tests/test_b.py": 'B = FE / "public/avatars"\n',
            f"{FE}/public/avatars/a.png": "",
        }
    )

    for pfad, test in [
        (f"{FE}/src/app/shared/meldegruende.ts", "test_m.py"),
        (f"{FE}/public/avatars/a.png", "test_b.py"),
    ]:
        auswahl = geaendert.waehlen([pfad], wurzel)

        assert auswahl.schritte == ["retired-words", "unit", "frontend"]
        assert test in auswahl.gruende["unit"][0]


def test_waehlen_doku_die_ein_integrationstest_liest_auch_integration(baum):
    wurzel = baum(
        {f"{PY}/app/tests/integration/test_n.py": 'K = "nginx.protokoll.conf"\n'}
    )

    auswahl = geaendert.waehlen([f"{FE}/nginx.protokoll.conf"], wurzel)

    assert "integration" in auswahl.schritte


def test_main_gibt_schritte_und_specs_fuer_check_sh_aus(baum, monkeypatch, capsys):
    wurzel = baum(
        {
            f"{FE}/src/app/a/a.component.ts": "export class A {}\n",
            f"{FE}/src/app/a/a.component.spec.ts": "import { A } from './a.component';\n",
        }
    )
    monkeypatch.setattr(geaendert, "WURZEL", wurzel)
    monkeypatch.setattr(
        geaendert,
        "geaenderte_pfade",
        lambda basis: [f"{FE}/src/app/a/a.component.ts", "docs/CI.md"],
    )

    assert geaendert.main(["--base", "origin/main"]) == 0

    ausgabe = capsys.readouterr()
    assert ausgabe.out.splitlines() == [
        "schritte retired-words frontend",
        "spec src/app/a/a.component.spec.ts",
    ]
    assert "2 geaenderte Dateien gegenueber origin/main" in ausgabe.err
    assert "frontend: 1 Specs zu 1 geaenderten Dateien" in ausgabe.err
    assert "lint: ausgelassen" in ausgabe.err


def test_main_ohne_aenderung_nur_retired_words(monkeypatch, capsys):
    monkeypatch.setattr(geaendert, "geaenderte_pfade", lambda basis: [])

    assert geaendert.main([]) == 0

    assert capsys.readouterr().out == "schritte retired-words\n"


def test_waehlen_erwaehnung_ohne_zeichenkette_ist_kein_lesen(baum):
    wurzel = baum(
        {
            f"{PY}/app/tests/unit/test_m.py": (
                '"""Die Schwellen in core/config.py."""\nP = "app/shared/andere.ts"\n'
            ),
        }
    )

    for pfad in [f"{FE}/src/app/shared/x.ts", f"{FE}/src/core/config.py"]:
        assert "unit" not in geaendert.waehlen([pfad], wurzel).schritte


def test_waehlen_wartungsskript_unit_und_wer_es_liest(baum):
    wurzel = baum(
        {f"{PY}/app/tests/integration/test_l.py": 'S = M / "manual/person_loeschen.sql"\n'}
    )

    auswahl = geaendert.waehlen(["mvp/scripts/manual/person_loeschen.sql"], wurzel)

    assert auswahl.schritte == ["retired-words", "unit", "integration"]
