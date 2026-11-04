"""
Die reservierte Kennung des Platzhalters "ehemalige Person" steht in zwei Sprachen
(Review von #270, Befund 8): im BFF, das Beta-Zugaenge mit ihr ablehnt
(ManagedUserService.cs, EhemaligePersonKennung), und im Suchdienst, der sie an die
Beitraege geloeschter Personen schreibt (anzeigename_service.py,
EHEMALIGE_PERSON_KENNUNG). Dazu das Praefix "<Kennung>-" fuer die Saetze im
Fangkorb (person_loeschen.sql, einwurf_repository.py).

Laufen die Stellen auseinander, koennte ein Beta-Zugang die Kennung des
Platzhalters tragen und an fremden Beitraegen als Autor gelten. Der Test liest
die Quelltexte, statt sie zu importieren: Die BFF-Tests laufen im .NET-Container
ohne den Suchdienst, und der Suchdienst kennt kein C#.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
BFF = WURZEL / "mvp/backend/BFF/Services/ManagedUserService.cs"
APP = WURZEL / "mvp/backend/semantic-search-service/app"
SUCHDIENST = APP / "services/anzeigename_service.py"
EINWUERFE = APP / "repositories/einwurf_repository.py"
LOESCHEN = WURZEL / "mvp/scripts/manual/person_loeschen.sql"


def _einmal(muster: str, datei: pathlib.Path) -> str:
    treffer = re.findall(muster, datei.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(treffer) == 1, f"{datei.name}: {muster} {len(treffer)}-mal gefunden"
    return treffer[0]


def _kennung_bff() -> str:
    return _einmal(r'const string EhemaligePersonKennung = "([^"]+)";', BFF)


def _kennung_suchdienst() -> str:
    return _einmal(r'^EHEMALIGE_PERSON_KENNUNG = "([^"]+)"$', SUCHDIENST)


def test_bff_und_suchdienst_reservieren_dieselbe_kennung():
    assert _kennung_bff() == _kennung_suchdienst()


def test_bff_reserviert_auch_das_praefix_der_saetze():
    assert 'EhemaligePersonKennung + "-"' in BFF.read_text(encoding="utf-8")


def test_saetze_im_fangkorb_tragen_das_reservierte_praefix():
    praefix = _kennung_suchdienst() + "-"

    loeschen = LOESCHEN.read_text(encoding="utf-8")
    assert f"'{praefix}' || gen_random_uuid()" in loeschen
    assert f"LIKE '{praefix}%'" in loeschen
    assert f'.like("{praefix}%")' in EINWUERFE.read_text(encoding="utf-8")


def test_gegenprobe_liest_eine_abweichung_als_abweichung(tmp_path):
    """Das Muster faengt die Kennung selbst, nicht irgendeinen String in der Zeile."""
    abweichend = tmp_path / "ManagedUserService.cs"
    abweichend.write_text(
        BFF.read_text(encoding="utf-8").replace(
            f'EhemaligePersonKennung = "{_kennung_bff()}"',
            'EhemaligePersonKennung = "geloeschte-person"',
        ),
        encoding="utf-8",
    )

    assert (
        _einmal(r'const string EhemaligePersonKennung = "([^"]+)";', abweichend)
        != _kennung_suchdienst()
    )
