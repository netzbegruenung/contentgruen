"""
Die Rechtstext-Listen liegen als eine Datei je Eintrag (#500), damit zwei PRs mit je einem
neuen Eintrag nicht mehr am Listenende kollidieren. Die Übersicht erzeugt
scripts/rechtstexte_uebersicht.py; die Tests hier prüfen sie an kleinen Bäumen und die
echte Ablage auf Vollständigkeit.
"""

import textwrap

import pytest

import rechtstexte_uebersicht as uebersicht


@pytest.fixture
def baum(tmp_path):
    def anlegen(dateien: dict[str, str]):
        for pfad, inhalt in dateien.items():
            datei = tmp_path / pfad
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(textwrap.dedent(inhalt).lstrip())
        return tmp_path

    return anlegen


# Lückenliste


def test_luecken_eine_tabelle_je_abschnitt_nach_nummer_sortiert(baum):
    wurzel = baum(
        {
            "1-impressum/README.md": """
                ## 1. Impressum

                Vorwort.
                """,
            "1-impressum/I10.md": """
                # I10

                - **Zeile:** 45
                - **Eintrag:** ✓ VR 201634
                """,
            "1-impressum/I2.md": """
                # I2

                - **Zeile:** 12
                - **Eintrag:** ✓ Straße
                """,
            "2-datenschutz/README.md": "## 2. Datenschutz\n",
            "2-datenschutz/D-N4b.md": "# D-N4b\n\n- **Vorgang:** Suche\n",
            "2-datenschutz/D-N4.md": "# D-N4\n\n- **Vorgang:** Nutzung\n",
        }
    )

    assert uebersicht.luecken(wurzel) == textwrap.dedent(
        """\
        ## 1. Impressum

        Vorwort.

        | # | Zeile | Eintrag |
        |---|---|---|
        | I2 | 12 | ✓ Straße |
        | I10 | 45 | ✓ VR 201634 |

        ## 2. Datenschutz

        | # | Vorgang |
        |---|---|
        | D-N4 | Nutzung |
        | D-N4b | Suche |
        """
    )


def test_luecken_die_ablage_ergibt_eine_uebersicht():
    """Jeder Abschnitt hat seinen Text und gleiche Felder in allen Einträgen."""
    text = uebersicht.luecken()

    assert text.startswith("## 1. IMPRESSUM")
    assert "| D-N5 | **Melde-/Moderationsfunktion** |" in text


def test_luecken_jede_nummer_ist_der_dateiname_und_kommt_nur_einmal_vor():
    nummern = []
    for abschnitt in uebersicht.abschnitte():
        for datei in uebersicht.eintraege(abschnitt):
            nummer, _ = uebersicht.eintrag(datei)
            assert nummer == datei.stem
            nummern.append(nummer)

    assert len(nummern) == len(set(nummern))
    assert {"I1", "I-A", "D1", "D-M1", "X1", "D-N13b", "O1", "P10"} <= set(nummern)


# Stände der Nutzungsbedingungen


def test_staende_neuester_zuerst_aenderungen_nach_ticket_eine_tabelle_je_feldsatz(baum):
    wurzel = baum(
        {
            "2026-10-30/stand.md": """
                # 30. Oktober 2026

                - **Zustimmung:** ja
                - **Release:** offen
                """,
            "2026-10-30/466.md": "§10: nur mit Zustimmung (#466).\n",
            "2026-10-30/393.md": "§1: KI-Vorschlag\ngestrichen (#393).\n",
            "2026-09/stand.md": "# September 2026\n\n- **im Repository:** 20c1b06b\n",
            "2026-09/neufassung.md": "Neufassung\n",
            "2026-10/stand.md": "# Oktober 2026\n\n- **im Repository:** bb0235b5\n",
            "2026-10/222.md": "Glossarbegriffe (#222)\n",
        }
    )

    assert uebersicht.staende(wurzel) == textwrap.dedent(
        """\
        | Stand | Was sich geändert hat | Zustimmung | Release |
        |---|---|---|---|
        | 30. Oktober 2026 | §1: KI-Vorschlag gestrichen (#393). §10: nur mit Zustimmung (#466). | ja | offen |

        | Stand | Was sich geändert hat | im Repository |
        |---|---|---|
        | Oktober 2026 | Glossarbegriffe (#222) | bb0235b5 |
        | September 2026 | Neufassung | 20c1b06b |
        """
    )


@pytest.mark.parametrize(
    "stand, ordner",
    [
        ("30. Oktober 2026", "2026-10-30"),
        ("1. März 2027", "2027-03-01"),
        ("Oktober 2026", "2026-10"),
    ],
)
def test_stand_als_ordner_datum_in_iso_form(stand, ordner):
    assert uebersicht.stand_als_ordner(stand) == ordner


@pytest.mark.parametrize("stand", ["Oktober", "30.10.2026", "30. Oct 2026"])
def test_stand_als_ordner_lehnt_anderes_ab(stand):
    with pytest.raises(ValueError):
        uebersicht.stand_als_ordner(stand)


def test_main_gibt_die_uebersicht_aus(capsys):
    assert uebersicht.main(["staende"]) == 0
    assert capsys.readouterr().out == uebersicht.staende()


@pytest.mark.parametrize("argv", [[], ["tabelle"], ["luecken", "staende"]])
def test_main_ohne_bekannte_art_meldet_den_aufruf(argv, capsys):
    assert uebersicht.main(argv) == 2
    assert "luecken|staende" in capsys.readouterr().err


def test_eintrag_ohne_feldzeile_ist_ein_fehler(baum):
    wurzel = baum({"I1.md": "# I1\n\nFreitext statt Feld\n"})

    with pytest.raises(ValueError, match="Feldzeile"):
        uebersicht.eintrag(wurzel / "I1.md")


def test_luecken_abschnitt_mit_abweichenden_feldern_ist_ein_fehler(baum):
    wurzel = baum(
        {
            "1-impressum/README.md": "## 1. Impressum\n",
            "1-impressum/I1.md": "# I1\n\n- **Zeile:** 11\n",
            "1-impressum/I2.md": "# I2\n\n- **Zeiel:** 12\n",
        }
    )

    with pytest.raises(ValueError, match="I2.md"):
        uebersicht.luecken(wurzel)
