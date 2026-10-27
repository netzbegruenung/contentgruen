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
    return yaml.safe_load((WURZEL / datei).read_text())["services"][dienst]["image"]


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


def test_dienste_nutzen_die_versionen_aus_compose_und_postgres_app():
    assert DIENSTE["qdrant"]["image"] == compose_image(
        "mvp/docker-compose.dev.yml", "qdrant"
    )
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
