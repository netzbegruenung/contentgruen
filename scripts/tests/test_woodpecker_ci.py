"""Die Woodpecker-Pipeline (.woodpecker/ci.yaml) gegen die Dateien, die Versionen schon festlegen.

Woodpecker kann kein Dockerfile lesen; die Images stehen deshalb ein zweites Mal in der
Pipeline. Diese Tests halten beide Stellen gleich und sichern die Regeln aus docs/CI.md.
"""

import pathlib
import re

import pytest
import yaml

WURZEL = pathlib.Path(__file__).resolve().parents[2]
PIPELINE = yaml.safe_load((WURZEL / ".woodpecker" / "ci.yaml").read_text())
SCHRITTE = {s["name"]: s for s in PIPELINE["steps"]}
DIENSTE = {d["name"]: d for d in PIPELINE["services"]}
BERICHT = "ci-bericht"


def from_zeile(dockerfile, stufe=None):
    """Image aus der FROM-Zeile (der Stufe ``stufe``, sonst der ersten)."""
    for zeile in (WURZEL / dockerfile).read_text().splitlines():
        m = re.match(r"FROM\s+(\S+)(?:\s+AS\s+(\S+))?", zeile, re.IGNORECASE)
        if m and (stufe is None or m.group(2) == stufe):
            return m.group(1)
    raise AssertionError(f"keine FROM-Zeile in {dockerfile}")


PYTHON = from_zeile("mvp/backend/semantic-search-service/Dockerfile")
NODE = from_zeile("mvp/frontend/gutgesagt-frontend/Dockerfile", "build")


def compose_image(datei, dienst):
    """Image des Dienstes ``dienst`` in einer Compose-Datei oder einem GitHub-Workflow."""
    inhalt = yaml.safe_load((WURZEL / datei).read_text())
    if "jobs" in inhalt:
        dienste = {}
        for job in inhalt["jobs"].values():
            dienste.update(job.get("services", {}))
    else:
        dienste = inhalt["services"]
    return dienste[dienst]["image"]


def test_ci_laeuft_bei_pull_request_push_auf_main_tag_und_manuell():
    events = {}
    for bedingung in PIPELINE["when"]:
        art = bedingung["event"]
        for event in [art] if isinstance(art, str) else art:
            events[event] = bedingung.get("branch")

    assert events == {
        "pull_request": None,
        "push": "main",
        "tag": None,
        "manual": None,
    }


def test_ci_hat_keinen_pfadfilter_auf_workflow_ebene():
    # Ein uebersprungener Workflow meldet keinen Status, der Pflichtstatus blockiert dann den PR.
    assert all("path" not in b for b in PIPELINE["when"])


@pytest.mark.parametrize(
    "schritt, quelle",
    [
        ("python-installieren", PYTHON),
        ("lint", PYTHON),
        ("unit", PYTHON),
        ("integration", PYTHON),
        ("ci-bericht", PYTHON),
        ("retired-words", NODE),
        ("frontend", NODE),
        ("bff", from_zeile("mvp/backend/BFF/Dockerfile", "build")),
    ],
)
def test_schritt_nutzt_das_image_aus_dem_dockerfile(schritt, quelle):
    assert SCHRITTE[schritt]["image"] == quelle


@pytest.mark.parametrize(
    "quelle",
    [
        ("mvp/docker-compose.dev.yml", "qdrant"),
        ("mvp/docker-compose.local-dbs.yml", "qdrant"),
        # Der Qdrant-Dienst der GitHub-CI auf dem Spiegel
        (".github/workflows/tests-backend.yml", "qdrant"),
    ],
)
def test_qdrant_dienst_hat_ueberall_dieselbe_version(quelle):
    datei, dienst = quelle
    assert DIENSTE["qdrant"]["image"] == compose_image(datei, dienst)


def test_dienste_nutzen_die_versionen_aus_compose_und_postgres_app():
    assert DIENSTE["postgres"]["image"] == from_zeile(
        "mvp/backend/postgres-app/Dockerfile"
    )
    # Ohne absoluten Pfad startet der Qdrant-Dienst in Woodpecker nicht.
    assert DIENSTE["qdrant"]["entrypoint"] == ["/qdrant/qdrant"]


def test_integration_laeuft_im_pflichtmodus_gegen_die_dienste():
    env = SCHRITTE["integration"]["environment"]
    pg = DIENSTE["postgres"]["environment"]

    assert str(env["INTEGRATION_STACK_PFLICHT"]) == "1"
    assert env["QDRANT_URL"] == "http://qdrant:6333"
    assert env["POSTGRES_TEST_DATABASE_URL"] == (
        f"postgresql+psycopg2://{pg['POSTGRES_USER']}:{pg['POSTGRES_PASSWORD']}"
        f"@postgres:5432/{pg['POSTGRES_DB']}"
    )


def test_jeder_schritt_protokolliert_fuer_den_ci_bericht():
    for name, s in SCHRITTE.items():
        if name == BERICHT:
            continue
        befehle = " ".join(s["commands"])
        assert f"scripts/ci-protokoll.sh {name} " in befehle, name


def test_ci_bericht_kennt_alle_schritte_in_pipeline_reihenfolge():
    andere = [n for n in SCHRITTE if n != BERICHT]
    bericht = SCHRITTE[BERICHT]

    assert list(SCHRITTE)[-1] == BERICHT
    assert bericht["depends_on"] == andere
    assert bericht["commands"][-1].split()[2:] == andere


def test_ci_bericht_nur_bei_rotem_pull_request_mit_dem_secret():
    bericht = SCHRITTE[BERICHT]

    assert bericht["when"] == [{"event": "pull_request", "status": "failure"}]
    assert bericht["environment"]["FORGEJO_TOKEN"] == {
        "from_secret": "forgejo_ci_bericht_token"
    }
    # Das Konto des Tokens: nur dessen Kommentare zaehlen als voriger Bericht. Welches,
    # steht nur in ci.yaml; ohne Wert gaebe es nie den Einzeiler.
    konto = bericht["environment"]["CI_BERICHT_KONTO"]
    assert isinstance(konto, str) and konto.strip()


WIKI = yaml.safe_load((WURZEL / ".woodpecker" / "rechtstexte-wiki.yaml").read_text())


def test_wiki_seite_nach_jedem_push_auf_main():
    # Das Secret darf in keinem PR-Lauf und keinem manuellen Lauf eines Branches stehen.
    # Kein Pfadfilter: Ob sich etwas geaendert hat, prueft das Skript (rechtstexte_wiki.py).
    ((bedingung,),) = [WIKI["when"]]
    assert bedingung == {"event": "push", "branch": "main"}


def test_wiki_seite_mit_eigenem_secret_im_python_image():
    ((schritt,),) = [WIKI["steps"]]
    assert schritt["image"] == PYTHON
    assert schritt["environment"]["FORGEJO_TOKEN"] == {
        "from_secret": "forgejo_wiki_token"
    }
    assert schritt["commands"] == ["python3 scripts/rechtstexte_wiki.py"]


NACHT = yaml.safe_load((WURZEL / ".woodpecker" / "nacht.yaml").read_text())
NACHT_SCHRITTE = {s["name"]: s for s in NACHT["steps"]}
# Das Image des Semantic-Search-Service bringt das Modell mit (Modell-Cache, docs/CI.md).
SEMANTIC_SEARCH_IMAGE = (
    "git.verdigado.com/netzbegruenung-images/gutgesagt-semantic-search:main"
)


def test_nachtlauf_nur_per_cron_nachtlauf_und_manuell():
    # Kein pull_request und kein push: zu langsam fuer jeden PR, kein Pflichtstatus.
    assert NACHT["when"] == [
        {"event": "cron", "cron": "nachtlauf"},
        {"event": "manual"},
    ]


def test_nachtlauf_misst_messset_und_suchtestset_mit_dem_modell_aus_dem_image():
    assert set(NACHT_SCHRITTE) == {"messset", "suchtest"}
    for schritt in NACHT_SCHRITTE.values():
        assert schritt["image"] == SEMANTIC_SEARCH_IMAGE
        assert schritt["environment"]["DOCKER_CONTAINER"] == "false"
        assert "secrets" not in schritt and not any(
            isinstance(w, dict) and "from_secret" in w
            for w in schritt["environment"].values()
        )
    befehle = "\n".join(
        b for s in NACHT_SCHRITTE.values() for b in s["commands"]
    )
    assert "tests/regression/test_aehnlichkeit_messset.py -m langsam" in befehle
    assert "python -m tests.regression.seed_laden" in befehle
    assert "python -m tests.regression.nachtlauf" in befehle


def test_nachtlauf_suchtest_laeuft_auch_nach_rotem_messset():
    suchtest = NACHT_SCHRITTE["suchtest"]
    assert suchtest["depends_on"] == ["messset"]
    assert suchtest["when"] == [{"status": ["success", "failure"]}]


def test_nachtlauf_qdrant_wie_in_ci():
    (dienst,) = NACHT["services"]
    assert dienst == DIENSTE["qdrant"]


def test_schritte_rufen_check_sh_mit_ihrem_namen_auf():
    # Die Schritte von check.sh (SCHRITTE=...) laufen in der Pipeline je als eigener Schritt.
    check = (WURZEL / "scripts" / "check.sh").read_text()
    in_check = re.search(r'^SCHRITTE="([^"]+)"', check, re.MULTILINE).group(1).split()
    aufrufe = {
        name: re.findall(r"check\.sh --schritt (\S+)", " ".join(s["commands"]))
        for name, s in SCHRITTE.items()
    }

    assert {n: a for n, a in aufrufe.items() if a} == {n: [n] for n in in_check}


def test_check_sh_nutzt_lokal_dasselbe_bff_image():
    # Ohne CHECK_OHNE_DOCKER laeuft der BFF-Schritt im SDK-Container (scripts/check.sh)
    check = (WURZEL / "scripts" / "check.sh").read_text()
    assert re.findall(r"mcr\.microsoft\.com/dotnet/sdk\S*", check) == [
        SCHRITTE["bff"]["image"]
    ]
