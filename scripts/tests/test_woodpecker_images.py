"""Die Image-Builds in Woodpecker (.woodpecker/build.yaml und release.yaml, #327).

Gleiche Image-Namen wie zuvor die GitHub-CI, damit Deployment und Renovate unverändert
weiterlaufen; Pfadfilter, die alles erfassen, was ein Dockerfile ins Image kopiert; und
beide Workflows gleich gebaut, damit ein Release nicht anders baut als main.
"""

import copy
import pathlib
import re

import pytest
import yaml

WURZEL = pathlib.Path(__file__).resolve().parents[2]


def laden(name):
    return yaml.safe_load((WURZEL / ".woodpecker" / name).read_text())


BUILD = laden("build.yaml")
RELEASE = laden("release.yaml")
CI = laden("ci.yaml")
TAGS = "image-tags"

IMAGES = {
    "frontend": "gutgesagt-frontend",
    "bff": "gutgesagt-bff",
    "semantic-search": "gutgesagt-semantic-search",
    "postgres-app": "gutgesagt-postgres-app",
}


def schritte(workflow):
    return {s["name"]: s for s in workflow["steps"]}


def build_schritte(workflow):
    return {n: s for n, s in schritte(workflow).items() if n != TAGS}


def kopierte_pfade(schritt):
    """Was das Dockerfile des Schritts aus dem Build-Kontext kopiert, relativ zur Wurzel."""
    kontext = schritt["settings"]["context"]
    pfade = []
    for zeile in (WURZEL / schritt["settings"]["dockerfile"]).read_text().splitlines():
        m = re.match(r"(?:COPY|ADD)\s+(.*)", zeile, re.IGNORECASE)
        if not m or "--from" in m.group(1):
            continue
        teile = m.group(1).strip()
        if teile.startswith("["):
            quellen = yaml.safe_load(teile)[:-1]
        else:
            quellen = [q for q in teile.split()[:-1] if not q.startswith("--")]
        pfade += [f"{kontext}/{q}".rstrip("/").removesuffix("/.") for q in quellen]
    pfade.append(schritt["settings"]["dockerfile"])
    if (WURZEL / kontext / ".dockerignore").exists():
        pfade.append(f"{kontext}/.dockerignore")
    return pfade


def erfasst(pfad, muster):
    """Ob ein Muster ``dir/**`` oder ein exakter Pfad Änderungen an ``pfad`` erfasst."""
    if muster.endswith("/**"):
        basis = muster[:-3]
        return pfad == basis or pfad.startswith(basis + "/")
    return pfad == muster


@pytest.mark.parametrize("workflow", [BUILD, RELEASE], ids=["build", "release"])
class TestBeideWorkflows:
    def test_erst_nach_gruenem_ci(self, workflow):
        assert workflow["depends_on"] == ["ci"]

    def test_bauen_dieselben_images_wie_bisher(self, workflow):
        repos = {n: s["settings"]["repo"] for n, s in build_schritte(workflow).items()}
        assert repos == {n: f"git.verdigado.com/netzbegruenung-images/{i}" for n, i in IMAGES.items()}

    def test_tags_aus_dem_skript(self, workflow):
        tags = schritte(workflow)[TAGS]
        assert tags["commands"] == ["python3 scripts/image_tags.py .image-tags"]
        for schritt in build_schritte(workflow).values():
            assert schritt["depends_on"] == [TAGS]
            assert schritt["settings"]["tags_file"] == ".image-tags"
            assert "tags" not in schritt["settings"]

    def test_secrets_nur_im_plugin(self, workflow):
        # Der Tag-Schritt fuehrt Befehle aus und bekommt deshalb kein Secret
        assert "from_secret" not in str(schritte(workflow)[TAGS])
        for schritt in build_schritte(workflow).values():
            assert schritt["settings"]["username"] == {"from_secret": "registry_user"}
            assert schritt["settings"]["password"] == {"from_secret": "registry_token"}

    def test_frontend_bekommt_den_commit(self, workflow):
        args = schritte(workflow)["frontend"]["settings"]["build_args"]
        assert args["GIT_SHA"] == "${CI_COMMIT_SHA}"


def test_build_und_release_bauen_gleich():
    # Bis auf Pfadfilter und Tag-Version: ein Release baut, was main gebaut hat. Ganze
    # Schritte in derselben Reihenfolge, damit auch ein zusätzlicher Schritt auffällt.
    def ohne_unterschiede(workflow):
        gleich = copy.deepcopy(workflow["steps"])
        for schritt in gleich:
            schritt.pop("when", None)
            schritt.get("settings", {}).get("build_args", {}).pop("APP_VERSION", None)
        return gleich

    assert ohne_unterschiede(BUILD) == ohne_unterschiede(RELEASE)


def test_ein_plugin_image_mit_digest():
    images = {s["image"] for w in (BUILD, RELEASE) for s in build_schritte(w).values()}
    assert len(images) == 1
    assert re.fullmatch(r"woodpeckerci/plugin-docker-buildx:[\d.]+@sha256:[0-9a-f]{64}", images.pop())


def test_tag_skript_im_python_image_der_ci():
    python = schritte(CI)["python-installieren"]["image"]
    assert schritte(BUILD)[TAGS]["image"] == python


class TestBuild:
    def test_push_und_manuell_nur_auf_main(self):
        assert BUILD["when"] == [
            {"event": "push", "branch": "main"},
            {"event": "manual", "branch": "main"},
        ]

    @pytest.mark.parametrize("name", list(IMAGES))
    def test_pfadfilter_erfasst_alles_was_das_dockerfile_kopiert(self, name):
        schritt = schritte(BUILD)[name]
        muster = schritt["when"][0]["path"]["include"]
        fehlend = [p for p in kopierte_pfade(schritt) if not any(erfasst(p, m) for m in muster)]
        assert fehlend == []

    def test_semantic_search_auch_bei_neuer_migration(self):
        # Review #331: Die Migrationen liegen im Semantic-Image
        muster = schritte(BUILD)["semantic-search"]["when"][0]["path"]["include"]
        assert "mvp/backend/postgres-app/migrations/**" in muster
        assert "mvp/.dockerignore" in muster

    @pytest.mark.parametrize("name", list(IMAGES))
    def test_aenderung_an_pipeline_oder_skript_baut_alle(self, name):
        muster = schritte(BUILD)[name]["when"][0]["path"]["include"]
        assert {".woodpecker/build.yaml", "scripts/image_tags.py"} <= set(muster)

    def test_footer_auf_main_sagt_main(self):
        # Entscheidung @BanSe 03.11. (#542): "main · <sha>" statt einer veralteten Version
        assert schritte(BUILD)["frontend"]["settings"]["build_args"]["APP_VERSION"] == "main"


class TestRelease:
    def test_nur_bei_tags_mit_v(self):
        assert RELEASE["when"] == [{"event": "tag", "ref": "refs/tags/v*"}]

    def test_baut_immer_alle_images(self):
        assert all("when" not in s for s in build_schritte(RELEASE).values())

    def test_version_im_footer_aus_dem_tag(self):
        args = schritte(RELEASE)["frontend"]["settings"]["build_args"]
        assert args["APP_VERSION"] == "${CI_COMMIT_TAG}"


class TestKopiertePfade:
    def test_semantic_search_kopiert_aus_mvp(self):
        pfade = kopierte_pfade(schritte(BUILD)["semantic-search"])
        assert "mvp/backend/postgres-app/migrations" in pfade
        assert "mvp/scripts/backup" in pfade
        assert "mvp/data" in pfade

    def test_erfasst(self):
        assert erfasst("mvp/data", "mvp/data/**")
        assert erfasst("mvp/data/x.json", "mvp/data/**")
        assert erfasst("mvp/backend/BFF", "mvp/backend/BFF/**")
        assert not erfasst("mvp/database", "mvp/data/**")
        assert erfasst("mvp/.dockerignore", "mvp/.dockerignore")
        assert not erfasst("mvp/.dockerignore", "mvp/backend/**")
