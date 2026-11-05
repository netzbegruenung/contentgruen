"""
Suchtestset: Suchanfragen mit den Aussagen, deren Beitraege auf sie passen. Gemessen wird
mit suche_messen.py gegen den Bestand eines Stacks; Regeln und Ergebnis in SUCHTESTSET.md.

Ein Fall passt zu einer Aussage, wenn ein Beitrag zu ihr eine brauchbare Antwort auf die
Suchanfrage ist: Wer so sucht, hat diese Behauptung gehoert und sucht eine Antwort darauf.
Eine verneinte oder gegenteilige Suchanfrage ("Windraeder schuetzen Voegel") ist eine
andere Behauptung; die Antworten auf das Gegenteil passen nicht, erwartet ist kein Treffer.

Felder:
- anfrage: so, wie sie jemand eintippt, mit Tippfehlern und Umgangssprache.
- form: stichwort (einzelne Woerter) oder satz.
- phaenomen: woran der Fall die Suche prueft (PHAENOMENE).
- erwartet: Texte der Aussagen, deren Beitraege passen; leer = kein Treffer erwartet.
- dieselbe_behauptung: Die Suchanfrage ist dieselbe Behauptung wie eine erwartete Aussage
  (Paar-Label gleich nach den Regeln in MESSSET.md). Nur diese Faelle zaehlen fuer die
  Zerfaserung: Sie sollten auf der vorhandenen Aussage landen statt eine neue anzulegen.
- quelle: seed = Aussage aus mvp/data/seed/v1.0 woertlich, dev = Suchanfrage aus der
  Entwicklungsumgebung (Messset), eigen = fuer das Suchtestset formuliert.

Keine echten Personen, keine Personendaten, keine Eingaben aus Produktion. Die erwarteten
Aussagen stammen heute aus dem Seed (Testbestand); nach dem Startbestand (#288) kommen
Faelle zu dessen Aussagen dazu. Faelle, deren Aussagen im gemessenen Bestand fehlen,
ueberspringt die Messung und nennt sie.

Neue Faelle ans Ende ihres Abschnitts, IDs fortlaufend; eine ID wechselt nie den Text.
"""

from typing import NamedTuple, Tuple

FORMEN = ("stichwort", "satz")
QUELLEN = ("seed", "dev", "eigen")
PHAENOMENE = (
    "woertlich",  # Text der Aussage
    "umformulierung",  # dieselbe Behauptung in anderen Worten
    "tippfehler",
    "umgangssprache",
    "schlagwort",  # nur Stichworte, keine Behauptung
    "frage",  # Frage zum Thema; die Antworten der Aussage passen
    "verwandt",  # selbes Thema, die Antworten passen trotzdem
    "verneinung",  # Gegenteil der Aussage, erwartet kein Treffer
    "fremd",  # Thema ohne Aussage im Bestand, erwartet kein Treffer
)


class Fall(NamedTuple):
    id: str
    anfrage: str
    form: str
    phaenomen: str
    erwartet: Tuple[str, ...]
    dieselbe_behauptung: bool
    quelle: str


# Aussagen des Seeds (mvp/data/seed/v1.0), woertlich.
VOEGEL = "Windräder töten die Vögel!"
UNZUVERLAESSIG = "Erneuerbare Energien sind total unzuverlässig!"
TEUER = "Erneuerbare Energien sind zu teuer!"
ATOM = "Wir brauchen Atomkraft statt dieser Erneuerbaren!"
HEIZUNG = "Die Grünen wollen mir meine Heizung verbieten!"
NEUBAU = "Wärmepumpen funktionieren nur im Neubau!"
VERBOT = "Die Grünen sind eine Verbotspartei!"
FLEISCH = "Die Grünen wollen uns das Fleisch verbieten!"
LAND = "Die Grünen interessieren sich nur für Großstädte, das Land ist ihnen egal!"
GENDERN = "Die Grünen wollen uns das Gendern aufzwingen!"
EU = "Die EU ist ein bürokratisches Monster, das uns nur schadet!"
EAUTO = "E-Autos sind auch nicht besser für die Umwelt!"
TEMPO = "Ein Tempolimit bringt doch nichts fürs Klima!"
VERBRENNER = "Das Verbrenner-Aus killt unsere Autoindustrie!"

KEINE: Tuple[str, ...] = ()

# fmt: off
FAELLE = tuple(Fall(*f) for f in (
    # Energie und Klima
    ("S01", "Windräder töten die Vögel", "satz", "woertlich", (VOEGEL,), True, "seed"),
    ("S02", "Windkraftanlagen bringen massenhaft Vögel um", "satz", "umformulierung", (VOEGEL,), True, "eigen"),
    ("S03", "windrad vögel", "stichwort", "schlagwort", (VOEGEL,), False, "eigen"),
    ("S04", "Windräder töten die Vögle", "satz", "tippfehler", (VOEGEL,), True, "eigen"),
    ("S05", "Windräder schützen Vögel", "satz", "verneinung", KEINE, False, "eigen"),
    ("S06", "Erneuerbare sind unzuverläsig", "satz", "tippfehler", (UNZUVERLAESSIG,), True, "eigen"),
    ("S07", "Dunkelflaute", "stichwort", "schlagwort", (UNZUVERLAESSIG,), False, "eigen"),
    ("S08", "Wenn kein Wind weht und keine Sonne scheint, gibt es keinen Strom", "satz", "verwandt", (UNZUVERLAESSIG,), False, "eigen"),
    ("S09", "Ökostrom ist viel zu teuer", "satz", "umformulierung", (TEUER,), True, "eigen"),
    ("S10", "Atomkraft", "stichwort", "schlagwort", (ATOM,), False, "eigen"),
    ("S11", "Wir sollten wieder Atomkraftwerke bauen statt Windräder", "satz", "verwandt", (ATOM,), False, "eigen"),
    ("S12", "Heizungsverbot", "stichwort", "schlagwort", (HEIZUNG,), False, "eigen"),
    ("S13", "Die Grünen nehmen uns die Gasheizung weg", "satz", "umformulierung", (HEIZUNG,), True, "eigen"),
    ("S14", "Die Grünen wolln mir die Heizung verbiten", "satz", "tippfehler", (HEIZUNG,), True, "eigen"),
    ("S15", "Wärmepumpe Altbau", "stichwort", "schlagwort", (NEUBAU,), False, "eigen"),
    ("S16", "Wärmepumpen taugen im Altbau nichts", "satz", "umformulierung", (NEUBAU,), True, "eigen"),
    ("S17", "Lohnt sich eine Wärmepumpe im Altbau?", "satz", "frage", (NEUBAU,), False, "eigen"),
    ("S18", "Wärmepumpen funktionieren auch im Altbau", "satz", "verneinung", KEINE, False, "eigen"),
    # Gesellschaft
    ("S19", "Verbotspartei", "stichwort", "schlagwort", (VERBOT,), False, "eigen"),
    ("S20", "Die Grünen wollen ständig alles verbieten", "satz", "verwandt", (VERBOT,), False, "eigen"),
    ("S21", "Die Grünen sind keine Verbotspartei", "satz", "verneinung", KEINE, False, "eigen"),
    ("S22", "Die Grünen wollen uns das Schnitzel wegnehmen", "satz", "umgangssprache", (FLEISCH,), True, "eigen"),
    ("S23", "Fleischverbot", "stichwort", "schlagwort", (FLEISCH,), False, "eigen"),
    ("S24", "Den Grünen ist das Land egal, die machen nur Politik für die Städter", "satz", "umformulierung", (LAND,), True, "eigen"),
    ("S25", "grüne nur großstadt", "stichwort", "umgangssprache", (LAND,), False, "eigen"),
    ("S26", "Genderzwang", "stichwort", "schlagwort", (GENDERN,), False, "eigen"),
    ("S27", "Die Grünen zwingen uns zum Gendern", "satz", "umformulierung", (GENDERN,), True, "eigen"),
    ("S28", "Die EU ist ein Bürokratiemonster", "satz", "verwandt", (EU,), False, "eigen"),
    ("S29", "Brüssel regelt sogar die Krümmung der Gurken", "satz", "umgangssprache", (EU,), False, "eigen"),
    # Verkehr
    ("S30", "E-Autos sind genauso dreckig wie Verbrenner", "satz", "umgangssprache", (EAUTO,), True, "eigen"),
    ("S31", "E-Auto Ökobilanz", "stichwort", "schlagwort", (EAUTO,), False, "eigen"),
    ("S32", "Elektroautos sin auch nich besser für die Umwelt", "satz", "tippfehler", (EAUTO,), True, "eigen"),
    ("S33", "Tempolimit bringt nix", "satz", "umgangssprache", (TEMPO,), True, "eigen"),
    ("S34", "Tempolimit", "stichwort", "schlagwort", (TEMPO,), False, "dev"),
    ("S35", "Ein Tempolimit schützt das Klima", "satz", "verneinung", KEINE, False, "eigen"),
    ("S36", "Das Verbrennerverbot zerstört die deutsche Autoindustrie", "satz", "umformulierung", (VERBRENNER,), True, "eigen"),
    ("S37", "Verbrenner-Aus Arbeitsplätze", "stichwort", "schlagwort", (VERBRENNER,), False, "eigen"),
    # Themen ohne Aussage im Testbestand
    ("S38", "Der Wolf gehört nicht nach Deutschland", "satz", "fremd", KEINE, False, "eigen"),
    ("S39", "Die Rente ist nicht mehr sicher", "satz", "fremd", KEINE, False, "eigen"),
    ("S40", "Mülltrennung bringt nichts, am Ende wird eh alles verbrannt", "satz", "fremd", KEINE, False, "eigen"),
    ("S41", "Radwege", "stichwort", "fremd", KEINE, False, "eigen"),
    ("S42", "Das Deutschlandticket ist zu teuer", "satz", "fremd", KEINE, False, "eigen"),
))
# fmt: on
