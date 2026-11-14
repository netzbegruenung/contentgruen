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
# Laufen nie in PR-Laeufen (Entscheidung @BanSe 14.11.), nur bei push auf main, Tag, manuell
# Nie in PR-Laeufen: integration (main, Tags, manuell), release-platzhalter (nur Tags)
NUR_MAIN = {"integration", "release-platzhalter"}


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
        ("frontend-build", NODE),
        ("frontend-installieren", NODE),
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
    # Ohne die Schritte, die nie in PRs laufen: der Bericht laeuft nur in PRs.
    andere = [n for n in SCHRITTE if n != BERICHT and n not in NUR_MAIN]
    bericht = SCHRITTE[BERICHT]

    assert list(SCHRITTE)[-1] == BERICHT
    assert namen(bericht["depends_on"]) == andere
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
        # :main wandert; ohne pull misst der Agent mit einem alten Image.
        assert schritt["pull"] is True
        assert schritt["environment"]["DOCKER_CONTAINER"] == "false"
        # Modellrevision aus dem Image, nicht was der Hub in der Nacht liefert.
        assert schritt["environment"]["HF_HUB_OFFLINE"] == "1"
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


def test_semantic_search_image_laeuft_offline_nach_dem_vorladen():
    # #578: Die Produktion nutzt nur die eingebauten Modelle, ohne Anfragen an den Hub.
    # Die ENV-Zeile steht nach dem letzten Vorlade-Schritt, sonst laedt der Build nichts.
    zeilen = (
        (WURZEL / "mvp/backend/semantic-search-service/Dockerfile")
        .read_text()
        .splitlines()
    )
    offline = [i for i, z in enumerate(zeilen) if z.strip() == "ENV HF_HUB_OFFLINE=1"]
    vorladen = [
        i
        for i, z in enumerate(zeilen)
        if "from_pretrained" in z or "SentenceTransformer(" in z
    ]
    assert len(offline) == 1 and vorladen
    assert offline[0] > max(vorladen)


def test_nachtlauf_suchtest_laeuft_auch_nach_rotem_messset():
    suchtest = NACHT_SCHRITTE["suchtest"]
    assert suchtest["depends_on"] == ["messset"]
    assert suchtest["when"] == [{"status": ["success", "failure"]}]


def test_nachtlauf_dienste_wie_in_ci():
    # Postgres (#576): Der Dienststart oeffnet die App-Datenbank (VotingService).
    # Bis auf das when der CI-Dienste (nur, wenn integration laeuft)
    ohne_when = [
        {k: v for k, v in DIENSTE[n].items() if k != "when"}
        for n in ("qdrant", "postgres")
    ]
    assert NACHT["services"] == ohne_when


def test_nachtlauf_suchtest_wartet_auf_die_dienste_und_nutzt_ihre_datenbank():
    suchtest = NACHT_SCHRITTE["suchtest"]
    pg = DIENSTE["postgres"]["environment"]

    assert suchtest["environment"]["SEMANTIC_SEARCH_APP_DATABASE_URL"] == (
        f"postgresql+psycopg2://{pg['POSTGRES_USER']}:{pg['POSTGRES_PASSWORD']}"
        f"@postgres:5432/{pg['POSTGRES_DB']}"
    )
    befehle = suchtest["commands"]
    warten = befehle.index(
        "python3 scripts/ci_dienste_warten.py qdrant:6333 postgres:5432"
    )
    assert warten < befehle.index("python -m tests.regression.nachtlauf")


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


def namen(abhaengigkeiten):
    """Die Namen in depends_on; Eintraege sind Namen oder {name, optional}."""
    return [a if isinstance(a, str) else a["name"] for a in abhaengigkeiten]


def test_frontend_schritte_teilen_ein_npm_ci():
    # Die Schritte teilen den Workspace: ein zweites npm ci loeschte node_modules des anderen.
    # npm ci laeuft in scripts/ci-installieren.sh frontend (oder dort nur ein Verweis).
    mit_npm_ci = [
        name
        for name, s in SCHRITTE.items()
        if any(
            "npm ci" in b or "ci-installieren.sh frontend" in b
            for b in s.get("commands", [])
        )
    ]
    assert mit_npm_ci == ["frontend-installieren"]
    for name in ("frontend", "frontend-build"):
        assert "frontend-installieren" in SCHRITTE[name]["depends_on"]


# Die schweren Schritte, kuerzeste zuerst: nie zwei zugleich auf dem geteilten Runner (docs/CI.md).
SCHWER = ["unit", "frontend-build", "frontend", "integration"]
VORBEREITUNG = {
    "unit": "python-installieren",
    "frontend-build": "frontend-installieren",
    "frontend": "frontend-installieren",
    "integration": "python-installieren",
}
ROT_ODER_GRUEN = ["success", "failure"]


def _muster(glob):
    """doublestar wie in Woodpecker: ** ueber Verzeichnisse, * innerhalb eines Namens."""
    teile = re.split(r"(\*\*/|/\*\*$|\*)", glob)
    ersatz = {"**/": "(?:.*/)?", "/**": "/.*", "*": "[^/]*"}
    return re.compile("".join(ersatz.get(t, re.escape(t)) for t in teile) + r"\Z")


def _bedingung_trifft(bedingung, event, dateien, status):
    arten = bedingung.get("event")
    if arten is not None and event not in (
        [arten] if isinstance(arten, str) else arten
    ):
        return False
    if status not in bedingung.get("status", ["success"]):
        return False
    pfad = bedingung.get("path")
    # Pfadfilter nur bei pull_request und push; leere Dateiliste: on_empty, Standard true
    if pfad and event in ("pull_request", "push") and dateien:
        ausnahmen = [_muster(m) for m in pfad.get("exclude", [])]
        if ausnahmen and all(any(m.match(d) for m in ausnahmen) for d in dateien):
            return False
        einschluss = [_muster(m) for m in pfad.get("include", [])]
        if einschluss and not any(m.match(d) for m in einschluss for d in dateien):
            return False
    return True


def schritte_im_lauf(event, dateien):
    """Die Schritte, die Woodpecker in die Pipeline aufnimmt (when ohne status), mit ihren
    aufgeloesten Abhaengigkeiten; wie compiler/dag.go: fehlt eine Pflicht-Abhaengigkeit,
    verwirft Woodpecker die Pipeline, eine optionale faellt weg."""
    drin = {}
    for name, s in SCHRITTE.items():
        when = s.get("when") or [{}]
        if any(
            _bedingung_trifft(
                {**b, "status": ROT_ODER_GRUEN}, event, dateien, "success"
            )
            for b in when
        ):
            drin[name] = s
    aufgeloest = {}
    for name, s in drin.items():
        abh = []
        for a in s.get("depends_on", []):
            ziel = a if isinstance(a, str) else a["name"]
            optional = isinstance(a, dict) and a.get("optional", False)
            if ziel in drin:
                abh.append(ziel)
            else:
                assert optional, f"{name}: Pflicht-Abhaengigkeit {ziel} fehlt im Lauf"
        aufgeloest[name] = abh
    return aufgeloest


def vorfahren(lauf, name):
    """Alle Schritte, auf die ``name`` im Lauf direkt oder indirekt wartet."""
    gesehen = set()
    offen = list(lauf[name])
    while offen:
        n = offen.pop()
        if n not in gesehen:
            gesehen.add(n)
            offen.extend(lauf[n])
    return gesehen


ALLE = set(SCHRITTE)
FRONTEND_GRUPPE = {"frontend-installieren", "frontend-build", "frontend"}
PR_LAEUFE = [
    # (geaenderte Dateien, Schritte, die wegfallen)
    (
        ["mvp/frontend/gutgesagt-frontend/src/app/app.component.ts"],
        {"lint", "bff"},
    ),
    (["mvp/backend/semantic-search-service/app/main.py"], FRONTEND_GRUPPE | {"bff"}),
    (["mvp/backend/postgres-app/migrations/x.sql"], FRONTEND_GRUPPE | {"bff"}),
    (["mvp/backend/BFF/Program.cs"], FRONTEND_GRUPPE | {"lint"}),
    (["scripts/tests/test_x.py", "scripts/ci_bericht.py"], FRONTEND_GRUPPE | {"bff"}),
    (
        ["mvp/frontend/gutgesagt-frontend/src/x.ts", "mvp/backend/BFF/Program.cs"],
        {"lint"},
    ),
    (
        [
            "mvp/frontend/gutgesagt-frontend/src/x.ts",
            "mvp/backend/semantic-search-service/app/x.py",
        ],
        {"bff"},
    ),
    # Gemeinsames und Unbekanntes: alles
    ([".woodpecker/ci.yaml"], set()),
    (["scripts/check.sh"], set()),
    (["scripts/ci-chromium.sh"], set()),
    (["docs/CI.md"], set()),
    (["mvp/config/x.json"], set()),
    # Eine Datei ausserhalb aller Ausnahmen genuegt fuer den vollen Lauf
    (["README.md", "mvp/frontend/gutgesagt-frontend/src/x.ts"], set()),
    # Forgejo liefert keine Dateiliste: alles (on_empty)
    ([], set()),
]


@pytest.mark.parametrize("dateien, weg", PR_LAEUFE)
def test_pfadfilter_bei_pull_request(dateien, weg):
    assert set(schritte_im_lauf("pull_request", dateien)) == ALLE - weg - NUR_MAIN


@pytest.mark.parametrize("dateien", [d for d, _ in PR_LAEUFE])
def test_integration_nie_im_pull_request(dateien):
    assert not set(schritte_im_lauf("pull_request", dateien)) & NUR_MAIN


@pytest.mark.parametrize("event", ["push", "tag", "manual"])
def test_integration_auf_main_mit_der_ganzen_kette(event):
    lauf = schritte_im_lauf(event, [])
    assert set(lauf["integration"]) == {"python-installieren", "unit", "frontend"}


def test_dienste_nur_wenn_integration_laeuft():
    # Qdrant und PostgreSQL braucht nur integration; in PRs starten sie gar nicht.
    integration = [
        {k: v for k, v in b.items() if k != "status"}
        for b in SCHRITTE["integration"]["when"]
    ]
    for dienst in DIENSTE.values():
        assert dienst["when"] == integration
    andere = " ".join(
        " ".join([str(s.get("environment", "")), *s["commands"]])
        for n, s in SCHRITTE.items()
        if n != "integration"
    )
    assert "qdrant" not in andere and "postgres" not in andere


@pytest.mark.parametrize("event", ["push", "tag", "manual"])
def test_push_tag_und_manuell_laufen_voll(event):
    # Auch ein Push, der nur das Frontend aendert: auf main laeuft immer alles.
    lauf = schritte_im_lauf(event, ["mvp/frontend/gutgesagt-frontend/src/x.ts"])
    nur_tag = set() if event == "tag" else {"release-platzhalter"}
    assert set(lauf) == ALLE - {"retired-words", BERICHT} - nur_tag


def test_python_installation_und_unit_laufen_immer():
    # Unit-Tests und scripts/tests/ lesen Frontend- und BFF-Dateien (docs/CI.md).
    for dateien, _ in PR_LAEUFE:
        lauf = schritte_im_lauf("pull_request", dateien)
        assert {"python-installieren", "unit", "retired-words"} <= set(lauf)


@pytest.mark.parametrize("dateien", [d for d, _ in PR_LAEUFE])
def test_schwere_schritte_laufen_in_jeder_auswahl_nacheinander(dateien):
    lauf = schritte_im_lauf("pull_request", dateien)
    schwer = [n for n in SCHWER if n in lauf]
    for i, a in enumerate(schwer):
        for b in schwer[i + 1 :]:
            assert a in vorfahren(lauf, b), (a, b)
    for name, vorbereitung in VORBEREITUNG.items():
        if name in lauf:
            assert vorbereitung in vorfahren(lauf, name), name
    # Leichte Schritte warten nie auf die Kette.
    for name in lauf:
        if name not in SCHWER and name != BERICHT:
            assert not vorfahren(lauf, name) & set(SCHWER), name


def test_kette_laeuft_nach_rotem_vorgaenger_weiter():
    # Sonst fehlten ci-bericht nach einem roten unit alle Ergebnisse dahinter, und ein frueh
    # roter leichter Schritt liesse unit ausfallen (Woodpecker: status success als Standard).
    for name in SCHWER:
        for bedingung in SCHRITTE[name]["when"]:
            assert bedingung["status"] == ROT_ODER_GRUEN, name


def test_ci_begrenzt_worker_und_speicher_der_schweren_schritte():
    assert SCHRITTE["unit"]["environment"]["CHECK_WORKER"] == "2"
    assert SCHRITTE["frontend-build"]["environment"]["NG_BUILD_MAX_WORKERS"] == "2"
    assert SCHRITTE["frontend"]["environment"]["CHECK_OHNE_SOURCEMAPS"] == "1"
    check = (WURZEL / "scripts" / "check.sh").read_text()
    # Lokal bleiben vier Worker und die Source-Maps.
    assert '-n "${CHECK_WORKER:-4}"' in check
    assert "${CHECK_OHNE_SOURCEMAPS:+--source-map=false}" in check


# CI-Images (Dockerfile.ci, .woodpecker/ci-image.yaml, scripts/ci-installieren.sh; docs/CI.md,
# "CI images").
CI_IMAGE = yaml.safe_load((WURZEL / ".woodpecker" / "ci-image.yaml").read_text())
CI_IMAGE_SCHRITTE = {s["name"]: s for s in CI_IMAGE["steps"]}
CI_IMAGE_ZIELE = {"ci-python": "gutgesagt-ci-python", "ci-node": "gutgesagt-ci-node"}
INSTALLIEREN = WURZEL / "scripts" / "ci-installieren.sh"


def dockerfile_ci_stufen():
    """Je Stufe von Dockerfile.ci: Basis-Image und die kopierten Quellen."""
    stufen, aktuell = {}, None
    for zeile in (
        (WURZEL / "Dockerfile.ci").read_text().replace("\\\n", " ").splitlines()
    ):
        m = re.match(r"FROM\s+(\S+)\s+AS\s+(\S+)", zeile, re.IGNORECASE)
        if m:
            aktuell = m.group(2)
            stufen[aktuell] = {"basis": m.group(1), "kopiert": [], "text": ""}
            continue
        if aktuell is None:
            continue
        stufen[aktuell]["text"] += zeile + "\n"
        m = re.match(r"COPY\s+(.*)", zeile, re.IGNORECASE)
        if m:
            stufen[aktuell]["kopiert"] += [
                q for q in m.group(1).split()[:-1] if not q.startswith("--")
            ]
    return stufen


STUFEN = dockerfile_ci_stufen()


def test_dockerfile_ci_baut_auf_den_images_der_dienste():
    # Dieselben Basis-Images wie die Schritte ohne CI-Image: gleiche Python- und Node-Version.
    assert set(STUFEN) == set(CI_IMAGE_ZIELE)
    assert STUFEN["ci-python"]["basis"] == PYTHON
    assert STUFEN["ci-node"]["basis"] == NODE


def test_dockerignore_laesst_genau_durch_was_dockerfile_ci_kopiert():
    zeilen = (WURZEL / "Dockerfile.ci.dockerignore").read_text().splitlines()
    regeln = [z for z in zeilen if z.strip() and not z.startswith("#")]
    assert regeln[0] == "*"
    durch = {r.removeprefix("!") for r in regeln[1:]}
    kopiert = {q for s in STUFEN.values() for q in s["kopiert"]}
    assert durch == kopiert
    assert all((WURZEL / q).is_file() for q in kopiert)


def test_ci_python_bringt_die_modelle_der_integrationstests_mit():
    # Die Modelle aus core/config.py, die standardmaessig laden; der Bestaetiger (aus) nicht.
    config = (
        WURZEL / "mvp/backend/semantic-search-service/app/core/config.py"
    ).read_text()

    def modell(name):
        return re.search(rf'^{name} = "([^"]+)"', config, re.MULTILINE).group(1)

    text = STUFEN["ci-python"]["text"]
    assert f"'{modell('EMBEDDING_MODELL')}'" in text
    assert f"'{modell('NLI_MODELL')}'" in text
    assert modell("NLI_BESTAETIGER_MODELL") not in text
    assert "ENV HF_HOME=/opt/ci/huggingface" in text
    # Ohne Offline-Modus laedt ein Lauf ein fehlendes Modell nach, statt rot zu werden.
    assert not re.search(
        r"^ENV.*HF_HUB_OFFLINE", (WURZEL / "Dockerfile.ci").read_text(), re.MULTILINE
    )


def test_ci_image_baut_nach_push_auf_main_woechentlich_und_manuell():
    assert CI_IMAGE["when"] == [
        {"event": "push", "branch": "main"},
        {"event": "cron", "cron": "ci-image"},
        {"event": "manual", "branch": "main"},
    ]


def test_ci_image_wartet_auf_ci_und_build():
    # Nie zugleich mit den schweren Schritten; optional, weil ein Cron-Lauf beide nicht hat.
    assert CI_IMAGE["depends_on"] == [
        {"name": "ci", "optional": True},
        {"name": "build", "optional": True},
    ]


def test_dockerfile_ci_schreibt_wohin_das_skript_liest():
    # Ein Tippfehler hier ergaebe stillen Dauer-Rueckfall ohne rotes Signal.
    skript = INSTALLIEREN.read_text()
    assert "CI_DIR=${CI_IMAGE_DIR:-/opt/ci}" in skript
    assert '"$CI_DIR/$1.sha256"' in skript
    assert '"$CI_DIR/node_modules"' in skript
    assert "--pruefsumme python > /opt/ci/python.sha256" in STUFEN["ci-python"]["text"]
    node = STUFEN["ci-node"]["text"]
    assert "--pruefsumme frontend > /opt/ci/frontend.sha256" in node
    assert "node_modules /opt/ci/node_modules" in node


def test_ci_image_wie_die_image_builds():
    # Plugin, Registry und Secrets wie build.yaml; nur die Build-Schritte sehen das Secret.
    build = yaml.safe_load((WURZEL / ".woodpecker" / "build.yaml").read_text())
    plugin = {s["image"] for s in build["steps"] if "settings" in s}
    tags = CI_IMAGE_SCHRITTE["ci-image-tags"]
    assert tags["image"] == PYTHON
    assert "from_secret" not in str(tags)
    for ziel, repo in CI_IMAGE_ZIELE.items():
        schritt = CI_IMAGE_SCHRITTE[ziel]
        einstellungen = schritt["settings"]
        assert {schritt["image"]} == plugin
        assert (
            einstellungen["repo"] == f"git.verdigado.com/netzbegruenung-images/{repo}"
        )
        assert einstellungen["registry"] == "git.verdigado.com"
        assert einstellungen["dockerfile"] == "Dockerfile.ci"
        assert einstellungen["context"] == "."
        assert einstellungen["target"] == ziel
        assert einstellungen["username"] == {"from_secret": "registry_user"}
        assert einstellungen["password"] == {"from_secret": "registry_token"}
        art = ziel.removeprefix("ci-")
        assert einstellungen["tags_file"] == f".ci-tags-{art}"


def test_ci_image_tags_latest_und_pruefsumme():
    befehle = CI_IMAGE_SCHRITTE["ci-image-tags"]["commands"]
    for art, quelle in (("python", "python"), ("node", "frontend")):
        summe = f"sh scripts/ci-installieren.sh --pruefsumme {quelle} > .ci-summe-{art}"
        tags = [
            f"printf 'latest\\n' > .ci-tags-{art}",
            f"cut -c1-12 .ci-summe-{art} >> .ci-tags-{art}",
        ]
        # Keine Pipe hinter der Pruefsumme: ihr Fehler machte den Schritt sonst nicht rot.
        assert befehle.index(summe) < befehle.index(tags[0]) < befehle.index(tags[1])


def test_ci_image_baut_die_beiden_images_nacheinander():
    node = CI_IMAGE_SCHRITTE["ci-node"]
    assert node["depends_on"] == [
        "ci-image-tags",
        {"name": "ci-python", "optional": True},
    ]
    # Nicht nach rotem ci-image-tags: dann fehlte die Tag-Datei.
    assert "status" not in node["when"][0]


@pytest.mark.parametrize("ziel", list(CI_IMAGE_ZIELE))
def test_ci_image_pfadfilter_erfasst_was_das_image_liest(ziel):
    muster = set(CI_IMAGE_SCHRITTE[ziel]["when"][0]["path"]["include"])
    noetig = set(STUFEN[ziel]["kopiert"]) | {
        "Dockerfile.ci",
        "Dockerfile.ci.dockerignore",
        ".woodpecker/ci-image.yaml",
    }
    assert noetig <= muster
    # Der Tag-Schritt laeuft, sobald einer der beiden Build-Schritte laeuft.
    tags = set(CI_IMAGE_SCHRITTE["ci-image-tags"]["when"][0]["path"]["include"])
    assert muster <= tags


def test_installationsschritte_nutzen_das_ci_image_skript():
    assert SCHRITTE["python-installieren"]["commands"] == [
        "sh scripts/ci-protokoll.sh python-installieren sh scripts/ci-installieren.sh python"
    ]
    assert SCHRITTE["frontend-installieren"]["commands"] == [
        "sh scripts/ci-protokoll.sh frontend-installieren sh scripts/ci-installieren.sh frontend"
    ]


def _baum(tmp_path):
    """Kopie des Skripts mit Lockfiles und Attrappen fuer python, npm (sie protokollieren)."""
    (tmp_path / "scripts").mkdir()
    skript = tmp_path / "scripts" / "ci-installieren.sh"
    skript.write_text(INSTALLIEREN.read_text())
    py = tmp_path / "mvp/backend/semantic-search-service"
    fe = tmp_path / "mvp/frontend/gutgesagt-frontend"
    py.mkdir(parents=True)
    fe.mkdir(parents=True)
    (py / "requirements.txt").write_text("ruff==1\n")
    (fe / "package.json").write_text("{}\n")
    (fe / "package-lock.json").write_text("{}\n")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    protokoll = tmp_path / "protokoll"
    # python -m venv ... legt eine pip-Attrappe an; npm protokolliert nur
    (bin_ / "python").write_text(
        "#!/bin/sh\n"
        f'echo "python $*" >> {protokoll}\n'
        'eval "ziel=\\${$#}"; mkdir -p "$ziel/bin"\n'
        f'printf \'#!/bin/sh\\necho "pip $*" >> {protokoll}\\n\' > "$ziel/bin/pip"\n'
        'chmod +x "$ziel/bin/pip"\n'
    )
    (bin_ / "npm").write_text(f'#!/bin/sh\necho "npm $*" >> {protokoll}\n')
    for datei in bin_.iterdir():
        datei.chmod(0o755)
    image = tmp_path / "opt-ci"
    image.mkdir()
    return skript, image, protokoll, fe


def _lauf(skript, image, *argumente):
    import os
    import subprocess

    umgebung = {
        **os.environ,
        "PATH": f"{skript.parents[1] / 'bin'}:{os.environ['PATH']}",
        "CI_IMAGE_DIR": str(image),
    }
    return subprocess.run(
        ["sh", str(skript), *argumente],
        env=umgebung,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_pruefsumme_haengt_an_den_lockfiles(tmp_path):
    skript, image, _, fe = _baum(tmp_path)
    vorher = _lauf(skript, image, "--pruefsumme", "frontend")
    assert re.fullmatch(r"[0-9a-f]{64}\n", vorher)
    assert _lauf(skript, image, "--pruefsumme", "frontend") == vorher
    (fe / "package-lock.json").write_text('{"neu": 1}\n')
    assert _lauf(skript, image, "--pruefsumme", "frontend") != vorher


def test_passendes_image_verknuepft_nur(tmp_path):
    skript, image, protokoll, fe = _baum(tmp_path)
    for art in ("python", "frontend"):
        (image / f"{art}.sha256").write_text(_lauf(skript, image, "--pruefsumme", art))

    _lauf(skript, image, "python")
    _lauf(skript, image, "frontend")

    befehle = protokoll.read_text().splitlines()
    venv = f"{tmp_path}/mvp/backend/semantic-search-service/venv"
    assert befehle == [f"python -m venv --system-site-packages {venv}"]
    assert (fe / "node_modules").is_symlink()
    assert (fe / "node_modules").readlink() == image / "node_modules"


@pytest.mark.parametrize("image_alt", [True, False], ids=["image-alt", "ohne-image"])
def test_sonst_installiert_der_schritt_wie_ohne_image(tmp_path, image_alt):
    skript, image, protokoll, fe = _baum(tmp_path)
    if image_alt:
        (image / "python.sha256").write_text("alt\n")
        (image / "frontend.sha256").write_text("alt\n")

    ausgabe = _lauf(skript, image, "python") + _lauf(skript, image, "frontend")

    befehle = protokoll.read_text().splitlines()
    assert befehle[1] == (
        f"pip install -q --no-cache-dir -r {tmp_path}"
        "/mvp/backend/semantic-search-service/requirements.txt"
    )
    assert befehle[2] == f"npm ci --prefix {fe} --prefer-offline --no-audit --no-fund"
    assert not (fe / "node_modules").exists()
    assert ("passt nicht" in ausgabe) is image_alt
