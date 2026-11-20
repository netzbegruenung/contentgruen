"""
Jedes Ziel der Rundgaenge (rundgang-daten.ts) steht in der Komponente, auf deren Seite der
Schritt laeuft (Sebastian 20.11.): Wer eine Klasse umbenennt oder einen Knopf entfernt,
merkt hier, dass ein Rundgang-Schritt ins Leere zeigt. Der Rundgang findet ein fehlendes
Ziel erst im Browser nicht, und kein Spec rendert alle Seiten.

Statisch, ohne Browser: Von der Komponente der Route (`seite.pfad`, sonst der Rahmen
`app.component`) aus werden die Templates samt aller eingebetteten Komponenten (`<app-…>`)
gesammelt. Jeder Teil eines Selektors (`app-search.start-suche .search-field`) muss darin
vorkommen: das Element als Komponente im Baum, jede Klasse in einem Template dieses Baums.
Bei Alternativen (`a, b`, Desktop und Handy) muss jede vorkommen. Ob das Ziel im Browser
sichtbar ist (z. B. erst nach einer Suche), prueft das nicht; den Rendertest der
Beitragen-Seite hat contribute-view.component.spec.ts.

Grenzen: Klassen zaehlen im ganzen Baum, nicht je Element; Ziele in Dialogen und Klassen aus
`[ngClass]` oder `[class]="…"` findet er nicht und meldet sie dann (laut, nicht still).
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
APP = WURZEL / "mvp/frontend/gutgesagt-frontend/src/app"
DATEN = APP / "rundgang/rundgang-daten.ts"
ROUTEN = APP / "app.routes.ts"


def _komponenten() -> dict[str, str]:
    """Selektor -> Template-Text (templateUrl oder Inline-Template) aller Komponenten."""
    index = {}
    for ts in APP.rglob("*.ts"):
        # Specs und Test-Attrappen (*.stub.ts, testing/) tragen dieselben Selektoren
        # mit leerem Template
        attrappe = ts.name.endswith((".spec.ts", ".stub.ts"))
        if attrappe or "testing" in ts.relative_to(APP).parts:
            continue
        text = ts.read_text(encoding="utf-8")
        if "@Component(" not in text:
            continue
        for block in text.split("@Component(")[1:]:
            selektor = re.search(r"selector:\s*'([^']+)'", block)
            if not selektor:
                continue
            datei = re.search(r"templateUrl:\s*'([^']+)'", block)
            if datei:
                template = (ts.parent / datei.group(1)).read_text(encoding="utf-8")
            else:
                inline = re.search(r"template:\s*`([\s\S]*?)`", block)
                template = inline.group(1) if inline else ""
            # Klassen am eigenen Element (host: { class: '…' }) zaehlen zum Template
            host = re.search(r"host:\s*\{[^}]*?class:\s*'([^']*)'", block)
            if host:
                template += f' class="{host.group(1)}"'
            for einzel in selektor.group(1).split(","):
                index[einzel.strip()] = template
    return index


def _baum(wurzel: str, index: dict[str, str]) -> dict[str, str]:
    """Die Wurzel-Komponente und alle Komponenten, die ihr Template (rekursiv) einbettet."""
    gesehen: dict[str, str] = {}
    offen = [wurzel]
    while offen:
        selektor = offen.pop()
        if selektor in gesehen or selektor not in index:
            continue
        gesehen[selektor] = index[selektor]
        offen.extend(re.findall(r"<(app-[\w-]+)", _ohne_kommentare(index[selektor])))
    return gesehen


def _ohne_kommentare(template: str) -> str:
    return re.sub(r"<!--.*?-->", "", template, flags=re.DOTALL)


def _klassen(template: str) -> set[str]:
    template = _ohne_kommentare(template)
    klassen = set()
    for wert in re.findall(r'\bclass="([^"]*)"', template):
        klassen.update(re.sub(r"\{\{.*?\}\}", " ", wert).split())
    klassen.update(re.findall(r"\[class\.([\w-]+)\]", template))
    return klassen


def _routen_selektor(pfad: str, index: dict[str, str]) -> str:
    """Selektor der Komponente, die `pfad` zeigt (loadComponent in app.routes.ts)."""
    text = ROUTEN.read_text(encoding="utf-8")
    treffer = re.search(
        r"path:\s*'"
        + re.escape(pfad.strip("/"))
        + r"',\s*loadComponent:\s*\(\)\s*=>\s*import\('([^']+)'\)",
        text,
    )
    assert treffer, f"Keine Route fuer {pfad} in app.routes.ts"
    ts = (ROUTEN.parent / (treffer.group(1) + ".ts")).read_text(encoding="utf-8")
    return re.search(r"selector:\s*'([^']+)'", ts).group(1)


def _schritte() -> list[tuple[str, str, str | None]]:
    """(Rundgang-Titel des Schritts, Ziel, Pfad oder None) aus RUNDGAENGE."""
    text = DATEN.read_text(encoding="utf-8")
    rundgaenge = text[text.index("export const RUNDGAENGE") :]
    schritte = []
    for block in re.split(r"\n\s*\{\n\s*titel:", rundgaenge)[1:]:
        titel = re.match(r"\s*'([^']+)'", block).group(1)
        ziel = re.search(r"ziel:\s*'([^']+)'", block)
        if not ziel:
            continue
        pfad = re.search(r"seite:\s*\{\s*pfad:\s*'([^']+)'", block)
        schritte.append((titel, ziel.group(1), pfad.group(1) if pfad else None))
    return schritte


def _fehlt(ziel: str, baum: dict[str, str]) -> list[str]:
    alle_klassen = set().union(*(_klassen(t) for t in baum.values()))
    fehlend = []
    for alternative in ziel.split(","):
        for teil in alternative.split():
            element = re.match(r"^([a-z][\w-]*)", teil)
            if (
                element
                and element.group(1).startswith("app-")
                and element.group(1) not in baum
            ):
                fehlend.append(f"<{element.group(1)}> in {alternative.strip()!r}")
            for klasse in re.findall(r"\.([\w-]+)", teil):
                if klasse not in alle_klassen:
                    fehlend.append(f".{klasse} in {alternative.strip()!r}")
    return fehlend


def test_jeder_schritt_hat_ein_ziel():
    schritte = _schritte()
    # Antwort finden (5) und Selbst beitragen (5): faellt die Zahl, liest der Test die Datei falsch
    assert len(schritte) >= 10, schritte
    # Jedes `ziel:` der Rundgaenge wurde gelesen; ein Ziel in doppelten Anfuehrungszeichen,
    # als Konstante oder zusammengesetzt fiele sonst still heraus
    text = DATEN.read_text(encoding="utf-8")
    rundgaenge = text[text.index("export const RUNDGAENGE") :]
    assert len(schritte) == rundgaenge.count("ziel:"), "Ziel nicht als '…' lesbar"


def test_jedes_ziel_steht_auf_seiner_seite():
    index = _komponenten()
    fehler = []
    for titel, ziel, pfad in _schritte():
        wurzel = _routen_selektor(pfad, index) if pfad else "app-root"
        baum = _baum(wurzel, index)
        # Kopf und Menue (app.component) stehen auf jeder Seite
        baum.update(_baum("app-root", index))
        fehler += [f"{titel} ({pfad or 'Rahmen'}): {f}" for f in _fehlt(ziel, baum)]
    assert not fehler, "Rundgang-Ziele ohne Gegenstueck im Template:\n" + "\n".join(
        fehler
    )


def test_findet_ein_umbenanntes_ziel():
    """Gegenprobe: Ein Ziel, das es nicht gibt, meldet der Test."""
    index = _komponenten()
    baum = _baum("app-root", index)
    baum.update(_baum(_routen_selektor("/contribute", index), index))
    assert _fehlt(".beitraege-block", baum) == []
    # Auskommentierte Klassen zaehlen nicht
    assert ".nur-im-kommentar" not in _klassen('<!-- <p class="nur-im-kommentar"> -->')
    assert _fehlt(".gibt-es-nicht, .beitraege-block", baum) == [
        ".gibt-es-nicht in '.gibt-es-nicht'"
    ]
    assert _fehlt("app-gibt-es-nicht .beitraege-block", baum) == [
        "<app-gibt-es-nicht> in 'app-gibt-es-nicht .beitraege-block'"
    ]
