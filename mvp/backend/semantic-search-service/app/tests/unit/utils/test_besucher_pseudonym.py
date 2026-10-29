"""Unit-Tests fuer das Tagespseudonym der Besucher (utils/besucher_pseudonym.py)."""

from datetime import date

import pytest
from starlette.requests import Request

from utils.besucher_pseudonym import (
    Tagesschluessel,
    besucher_merkmal,
    besucher_tagespseudonym,
)

pytestmark = pytest.mark.unit

HEUTE = date(2026, 10, 29)
MORGEN = date(2026, 10, 30)
MERKMAL = "198.51.100.5|Mozilla/5.0 (X11; Linux x86_64) Firefox/131.0"


def _anfrage(headers: dict, peer: str = "10.0.0.2") -> Request:
    return Request(
        {
            "type": "http",
            "headers": [
                (k.lower().encode("latin-1"), v.encode("latin-1"))
                for k, v in headers.items()
            ],
            "client": (peer, 12345),
        }
    )


class TestTagesschluessel:
    def test_derselbe_tag_ergibt_denselben_schluessel(self):
        schluessel = Tagesschluessel()

        assert schluessel.fuer(HEUTE) == schluessel.fuer(HEUTE)

    def test_der_naechste_tag_ergibt_einen_neuen_schluessel(self):
        schluessel = Tagesschluessel()

        assert schluessel.fuer(HEUTE) != schluessel.fuer(MORGEN)

    def test_ein_vergangener_tag_kommt_nicht_zurueck(self):
        """Nach dem Wechsel ist der alte Schluessel weg, auch fuer Nachzuegler."""
        schluessel = Tagesschluessel()
        gestern = schluessel.fuer(HEUTE)
        heute = schluessel.fuer(MORGEN)

        nachzuegler = schluessel.fuer(HEUTE)

        assert nachzuegler != gestern
        # Der Nachzuegler verdraengt den laufenden Tag nicht.
        assert schluessel.fuer(MORGEN) == heute

    def test_ein_neuer_prozess_hat_einen_anderen_schluessel(self):
        """Nicht gespeichert: nach einem Neustart ist der Schluessel ein anderer."""
        assert Tagesschluessel().fuer(HEUTE) != Tagesschluessel().fuer(HEUTE)


class TestBesucherTagespseudonym:
    def test_dasselbe_merkmal_am_selben_tag_ist_dasselbe_pseudonym(self):
        schluessel = Tagesschluessel()

        assert besucher_tagespseudonym(
            MERKMAL, HEUTE, schluessel
        ) == besucher_tagespseudonym(MERKMAL, HEUTE, schluessel)

    def test_am_naechsten_tag_ist_es_ein_anderes(self):
        schluessel = Tagesschluessel()

        assert besucher_tagespseudonym(
            MERKMAL, HEUTE, schluessel
        ) != besucher_tagespseudonym(MERKMAL, MORGEN, schluessel)

    def test_anderes_merkmal_ist_ein_anderes_pseudonym(self):
        schluessel = Tagesschluessel()

        assert besucher_tagespseudonym(
            MERKMAL, HEUTE, schluessel
        ) != besucher_tagespseudonym("198.51.100.6|Firefox", HEUTE, schluessel)

    def test_enthaelt_weder_adresse_noch_browserkennung(self):
        pseudonym = besucher_tagespseudonym(MERKMAL, HEUTE, Tagesschluessel())

        assert len(pseudonym) == 64
        assert "198.51.100.5" not in pseudonym
        assert "Firefox" not in pseudonym


class TestBesucherMerkmal:
    def test_aus_real_ip_und_user_agent(self):
        merkmal = besucher_merkmal(
            _anfrage({"X-Real-IP": "198.51.100.5", "User-Agent": "Firefox"})
        )

        assert merkmal == "198.51.100.5|Firefox"

    def test_ipv6_zaehlt_mit_seinem_64(self):
        """Datenschutz-Erweiterungen wechseln die Adresse im /64 laufend."""
        eins = besucher_merkmal(
            _anfrage({"X-Real-IP": "2001:db8:1:2::a", "User-Agent": "Firefox"})
        )
        zwei = besucher_merkmal(
            _anfrage({"X-Real-IP": "2001:db8:1:2::b", "User-Agent": "Firefox"})
        )

        assert eins == zwei == "2001:db8:1:2::/64|Firefox"

    def test_ohne_real_ip_der_peer_der_verbindung(self):
        merkmal = besucher_merkmal(_anfrage({"User-Agent": "Firefox"}, peer="10.0.0.9"))

        assert merkmal == "10.0.0.9|Firefox"

    def test_ohne_user_agent_bleibt_die_adresse(self):
        assert besucher_merkmal(_anfrage({"X-Real-IP": "198.51.100.5"})) == (
            "198.51.100.5|"
        )

    def test_eine_mitgeschickte_sitzungskennung_aendert_nichts(self):
        """Der Browser bestimmt das Merkmal nicht mehr selbst."""
        ohne = besucher_merkmal(
            _anfrage({"X-Real-IP": "198.51.100.5", "User-Agent": "Firefox"})
        )
        mit = besucher_merkmal(
            _anfrage(
                {
                    "X-Real-IP": "198.51.100.5",
                    "User-Agent": "Firefox",
                    "X-Session-Id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
                }
            )
        )

        assert ohne == mit
