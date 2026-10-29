"""
Messset Aehnlichkeit: Textpaare mit Paar-Label, Kategorie und festem Train/Test-Teil.
Die Scores dazu stehen in aehnlichkeit_gemessen.py (erzeugt von aehnlichkeit_messen.py),
Labels, Grenzfall-Regeln und Split in MESSSET.md.

Paar-Label (was der Mensch entscheidet): gleich = dieselbe Behauptung; widerspricht =
beide koennen nicht zugleich stimmen; verwandt = selbes Thema, andere Behauptung, beide
koennen stimmen; fremd = anderes Thema.

Kategorie (wie der Text abweicht, seit 2026-09-17): A identisch; B trivial abweichend
(Gross/klein, Punkt/Ausrufezeichen, Leerraum, Anfuehrungszeichen); C gleiche Behauptung,
andere Worte; D verwandt oder widersprechend; E fremdes Thema. art: aussage
(Formular/Seeding), suche (Suchanfragen), kommentar, hintergrundinfo. Quelle (QUELLEN,
mehrere mit "+" in dieser Reihenfolge): seed = mvp/data/seed/v1.0 (Kommentare aus dem
bereinigten Stand nach #340, Aussagen zum Teil aus dem Stand davor), dev = Eingaben aus
der Entwicklungsumgebung (nur Paare vom 17.09.2026), eigen = fuer die Messung formuliert. Keine echten Personen, keine
erfundenen Erlebnisse - es gelten die Regeln des Seeds (mvp/data/seed/README.md). Paare
mit dem Label widerspricht duerfen falsche Zahlen enthalten: Das ist ihr Zweck.

Neue Paare ans Ende ihrer Gruppe anhaengen: Die IDs der Gruppen werden durchgezaehlt.
"""

from typing import NamedTuple

LABELS = ("gleich", "widerspricht", "verwandt", "fremd")
QUELLEN = ("seed", "dev", "eigen")
# Woran sich das Paar unterscheidet. Minimalpaare: verneinung, antonym, quantor.
PHAENOMENE = (
    "identisch",
    "trivial",
    "tippfehler",
    "wortstellung",
    "umformulierung",
    "zusatz",
    "verneinung",
    "antonym",
    "quantor",
    "skopus",
    "frage",
    "zahl",
    "mehrfachthema",
    "aspekt",
    "fremd",
)
MINIMALPAAR_PHAENOMENE = frozenset({"verneinung", "antonym", "quantor"})

# Fester Split nach Gruppe: Eine Gruppe liegt ganz in einem Teil, damit kein Text in
# Train und Test zugleich vorkommt. "alt" sind die 77 Paare, an denen die heutigen
# Schwellen gesetzt wurden - deshalb Train.
TEST_GRUPPEN = frozenset(
    {
        "wald",
        "nahverkehr",
        "ticket",
        "bio",
        "fliegen",
        "akku",
        "moor",
        "fernwaerme",
        "wolf",
        "muell",
        "hi_ausfall",
        "hi_tempo",
    }
)


class Paar(NamedTuple):
    id: str
    art: str
    kategorie: str
    label: str
    phaenomen: str
    kandidat: str
    bestand: str
    quelle: str
    gruppe: str

    @property
    def teil(self) -> str:
        return "test" if self.gruppe in TEST_GRUPPEN else "train"


def _kategorie(label: str, phaenomen: str) -> str:
    if label == "gleich":
        return {"identisch": "A", "trivial": "B"}.get(phaenomen, "C")
    return "E" if label == "fremd" else "D"


def _gruppe(art, kuerzel, gruppe, bestand, varianten, quelle="eigen"):
    """Varianten (label, phaenomen, kandidat) gegen einen Bestandstext."""
    return [
        Paar(
            f"{kuerzel}{nr:02d}",
            art,
            _kategorie(label, phaenomen),
            label,
            phaenomen,
            kandidat,
            bestand,
            quelle,
            gruppe,
        )
        for nr, (label, phaenomen, kandidat) in enumerate(varianten, start=1)
    ]


# fmt: off
# Aussage, die mehrfach vorkommt
VERBOT = "Die Grünen sind eine Verbotspartei"
# Kommentare aus dem bereinigten Seed (mvp/data/seed/v1.0), die mehrfach vorkommen
GLAS_TITEL = "Glasscheiben sind für Vögel weit gefährlicher als Windräder"
GLAS = "Vogelschutz ist wichtig, da sind wir uns einig. Die größte Gefahr sind aber Glasscheiben: Die Vogelschutzwarten schätzen 100 bis 115 Millionen tote Vögel pro Jahr in Deutschland. Wer Vögel schützen will, fängt also am Fenster an."
STANDORT = "Rotmilan und Storch sollen geschützt bleiben, das wollen wir alle. Deshalb wird vor jedem Windpark geprüft, welche Arten dort brüten und jagen. So bekommen wir beides: sauberen Strom und geschützte Vögel."
REGELN = "Selbst entscheiden wollen wir alle. Viele Regeln, die heute selbstverständlich sind, schützen unsere Freiheit: der Gurt im Auto, rauchfreie Restaurants, sauberes Trinkwasser. Die Frage ist immer, was eine Regel bringt und für wen."
WIND_SONNE = "Selbst entscheiden, woher der eigene Strom kommt, das wollen viele. Dafür braucht es vor allem weniger Hürden: einfachere Regeln für Solaranlagen, Windräder und Bürgerenergie. So entstehen neue Möglichkeiten."
REPARATUR = "Warm wohnen, ohne sich zu verschulden, das wollen wir alle. Wenn eine Heizung kaputtgeht, darf sie repariert werden. Die Vorgaben für erneuerbare Wärme gelten für neu eingebaute Heizungen."
BERATUNG = "Die Unsicherheit beim Thema Heizung verstehe ich gut. Am meisten hilft eine Energieberatung für das eigene Haus: Sie zeigt, was sich lohnt und welche Förderung es gibt. So kannst du in Ruhe entscheiden."
ALTBAU = "Im Altbau ist man zu Recht vorsichtig. Ein Feldtest des Fraunhofer ISE in bestehenden Häusern zeigt aber: Luft-Wärmepumpen machen dort aus einer Kilowattstunde Strom im Schnitt 3,3 Kilowattstunden Wärme."
TELLER = "Essen ist Privatsache, da sind wir uns einig. Wichtig ist, dass gutes Essen bezahlbar ist und Bauern davon leben können. Dafür braucht es faire Preise, klare Herkunftsangaben und Tiere, denen es gut geht."
HOF = "Wer Fleisch isst, will wissen, woher es kommt. Höfe in der Region mit guter Tierhaltung brauchen dafür faire Preise und eine klare Kennzeichnung. Das stärkt die Landwirtschaft vor Ort."
EU_ALLTAG = "Zu viel Papierkram nervt, das stimmt. Gleichzeitig sorgt die EU für Dinge, die wir täglich nutzen: Telefonieren im EU-Ausland ohne Roaming-Aufschlag und ein gemeinsames Ladekabel für Handys. Allein hätte das kein Land durchgesetzt."
TEMPOLIMIT = "Klimaschutz soll bezahlbar sein, da sind wir uns einig. Tempo 120 auf Autobahnen und 80 außerorts würden laut Umweltbundesamt 6,6 Millionen Tonnen CO2-Äquivalente im Jahr sparen und 2,8 Milliarden Liter Kraftstoff. Dafür reichen Schilder."
# Eigene Varianten von GLAS: dieselbe Behauptung in anderen Worten, und eine Kopie
# mit angehaengter Herkunft
GLAS_EIGENE_WORTE = "Mir liegt der Vogelschutz auch am Herzen. An Glasscheiben sterben in Deutschland aber geschätzt 100 bis 115 Millionen Vögel im Jahr, sagen die Vogelschutzwarten. Vogelschutz beginnt also am Fenster."
GLAS_ZUSATZ = " Quelle: Länderarbeitsgemeinschaft der Vogelschutzwarten."

# Die 77 Paare vom 2026-09-17 (Kategorie von Hand, Label seit #390).
# (id, art, kategorie, label, phaenomen, kandidat, bestand, quelle)
_ALT = [
    ("A01", "aussage", "A", "gleich", "identisch", 'Die Grünen sind eine Verbotspartei!', 'Die Grünen sind eine Verbotspartei!', "seed"),
    ("A02", "aussage", "A", "gleich", "identisch", 'Windräder sind Vogel-Schredder!', 'Windräder sind Vogel-Schredder!', "seed"),
    ("A03", "aussage", "A", "gleich", "identisch", 'Balkonsolar lohnt sich nie', 'Balkonsolar lohnt sich nie', "eigen"),
    ("A04", "aussage", "A", "gleich", "identisch", 'Die Grünen wollen mir meine Heizung verbieten!', 'Die Grünen wollen mir meine Heizung verbieten!', "seed"),
    ("A05", "aussage", "A", "gleich", "identisch", 'Grüne wollen das Auto verbieten', 'Grüne wollen das Auto verbieten', "eigen"),
    ("A06", "aussage", "A", "gleich", "identisch", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Tempolimit bringt doch eh nichts fürs Klima!', "seed"),
    ("B01", "aussage", "B", "gleich", "trivial", VERBOT, 'Die Grünen sind eine Verbotspartei!', "seed"),
    ("B02", "aussage", "B", "gleich", "trivial", 'Deutschland kann das Klima nicht alleine retten', 'Deutschland kann das Klima nicht alleine retten!', "seed"),
    ("B03", "aussage", "B", "gleich", "trivial", 'windräder sind vogel-schredder', 'Windräder sind Vogel-Schredder!', "seed+eigen"),
    ("B04", "aussage", "B", "gleich", "trivial", '„Balkonsolar lohnt sich nie“', 'Balkonsolar lohnt sich nie', "eigen"),
    ("B05", "aussage", "B", "gleich", "trivial", 'Die  Grünen lassen alle Migranten rein. ', 'Die Grünen lassen alle Migranten rein', "seed+eigen"),
    ("B06", "aussage", "B", "gleich", "trivial", 'E-AUTOS SIND EINE TOTGEBURT!!!', 'E-Autos sind eine Totgeburt!', "seed+eigen"),
    ("B07", "aussage", "B", "gleich", "trivial", '"Die Grünen wollen mir meine Heizung verbieten"', 'Die Grünen wollen mir meine Heizung verbieten!', "seed+eigen"),
    ("B08", "aussage", "B", "gleich", "trivial", "Das geht's so nicht, Tempolimit ist Unsinn", 'Das geht’s so nicht, Tempolimit ist Unsinn', "eigen"),
    # Frage statt Behauptung: seit die Normalisierung das Fragezeichen stehen laesst,
    # keine triviale Abweichung mehr, sondern ein eigener Satz (Kategorie D).
    ("B09", "aussage", "D", "verwandt", "frage", 'Wärmepumpen funktionieren nur im Neubau?', 'Wärmepumpen funktionieren nur im Neubau!', "seed+eigen"),
    ("B10", "aussage", "B", "gleich", "trivial", 'grüne wollen das auto verbieten.', 'Grüne wollen das Auto verbieten', "eigen"),
    ("C01", "aussage", "C", "gleich", "umformulierung", 'E-Autos sind auch nicht besser für die Umwelt', 'Elektroautos sind gar nicht umweltfreundlich!', "seed"),
    ("C02", "aussage", "C", "gleich", "skopus", 'Deutschland kann das Klima nicht alleine retten', 'Deutschland kann nicht alleine das Klima retten!', "seed"),
    ("C03", "aussage", "C", "gleich", "umformulierung", VERBOT, 'Die Grünen wollen immer alles verbieten', "eigen"),
    ("C04", "aussage", "C", "gleich", "umformulierung", 'Windräder sind Vogel-Schredder!', 'Windkraftanlagen töten massenhaft Vögel', "eigen"),
    ("C05", "aussage", "C", "gleich", "umformulierung", 'Balkonsolar lohnt sich nie', 'Balkonkraftwerke rechnen sich nicht', "eigen"),
    ("C06", "aussage", "C", "gleich", "umformulierung", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Ein Tempolimit hilft dem Klima überhaupt nicht', "eigen"),
    ("C07", "aussage", "D", "verwandt", "mehrfachthema", 'Die Grünen interessieren sich nur für Großstädte, das Land ist ihnen egal!', 'Den Grünen ist der ländliche Raum egal', "eigen"),
    ("C08", "aussage", "C", "gleich", "umformulierung", 'Die Grünen wollen mir meine Heizung verbieten!', 'Die Grünen wollen uns die Gasheizung wegnehmen', "eigen"),
    ("C09", "aussage", "C", "gleich", "umformulierung", 'Die Grünen lassen alle Migranten rein', 'Die Grünen wollen die Grenzen für alle öffnen', "eigen"),
    ("C10", "aussage", "C", "gleich", "umformulierung", 'Wärmepumpen funktionieren nur im Neubau!', 'Im Altbau taugen Wärmepumpen nichts', "eigen"),
    ("C11", "aussage", "C", "gleich", "umformulierung", 'Erneuerbare Energien sind total unzuverlässig!', 'Wind und Sonne liefern keinen verlässlichen Strom', "eigen"),
    ("C12", "aussage", "C", "gleich", "umformulierung", 'Die Grünen wollen uns das Fleisch verbieten', 'Die Grünen wollen uns das Schnitzel wegnehmen', "eigen"),
    ("C13", "aussage", "C", "gleich", "umformulierung", 'Wärmepumpen funktionieren nur im Neubau!', 'Wärmepumpen funktionieren nicht im Altbau!', "seed"),
    ("D01", "aussage", "D", "verwandt", "aspekt", 'Balkonsolar lohnt sich nie', 'Balkonkraftwerke sind nur Spielerei', "eigen"),
    ("D02", "aussage", "D", "verwandt", "aspekt", 'Grüne wollen das Auto verbieten', 'Grüne wollen nur Großstädter bedienen', "eigen"),
    ("D03", "aussage", "D", "verwandt", "aspekt", 'Erneuerbare Energien sind zu teuer!', 'Erneuerbare Energien sind total unzuverlässig!', "seed"),
    ("D04", "aussage", "D", "verwandt", "aspekt", 'Die Grünen zerstören die Wirtschaft!', 'Die Grünen zerstören unsere Landwirtschaft!', "seed"),
    ("D05", "aussage", "D", "verwandt", "aspekt", 'E-Autos sind eine Totgeburt!', 'E-Autos sind auch nicht besser für die Umwelt', "seed"),
    ("D06", "aussage", "D", "verwandt", "aspekt", 'Die Grünen wollen uns das Gendern aufzwingen', 'Dieser ganze Gender-Wahnsinn muss aufhören!', "seed"),
    ("D07", "aussage", "D", "verwandt", "aspekt", VERBOT, 'Die Grünen wollen uns das Fleisch verbieten', "seed"),
    ("D08", "aussage", "D", "verwandt", "aspekt", 'Die Grünen wollen mir meine Heizung verbieten!', 'Die Grünen haben keine Ahnung von Wirtschaft!', "seed+eigen"),
    ("D09", "aussage", "D", "verwandt", "aspekt", 'Wärmepumpen funktionieren nur im Neubau!', 'Wärmepumpen sind viel zu teuer', "eigen"),
    ("D10", "aussage", "D", "verwandt", "aspekt", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Tempolimit kostet Autofahrer nur Zeit', "eigen"),
    ("D11", "aussage", "D", "widerspricht", "verneinung", VERBOT, 'Die Grünen sind keine Verbotspartei', "eigen"),
    ("D12", "aussage", "D", "verwandt", "aspekt", 'Windräder sind Vogel-Schredder!', 'Windräder verschandeln die Landschaft', "eigen"),
    ("D13", "aussage", "D", "verwandt", "aspekt", 'Die Grünen verstehen nichts vom Leben normaler Leute', 'Die Grünen interessieren sich nur für Großstädte, das Land ist ihnen egal!', "seed"),
    ("D14", "aussage", "D", "verwandt", "aspekt", 'Grüne sind Kriegstreiber', 'Die Grünen kümmern sich nicht um unsere Sicherheit!', "seed"),
    ("D15", "aussage", "D", "widerspricht", "quantor", 'Balkonsolar lohnt sich nie', 'Balkonsolar lohnt sich immer', "eigen"),
    ("D16", "aussage", "D", "verwandt", "aspekt", 'Die Grünen zerstören die Wirtschaft!', 'Die Energiewende zerstört Arbeitsplätze!', "seed"),
    ("E01", "aussage", "E", "fremd", "fremd", 'Balkonsolar lohnt sich nie', 'Die Grünen lassen alle Migranten rein', "seed+eigen"),
    ("E02", "aussage", "E", "fremd", "fremd", 'Windräder sind Vogel-Schredder!', 'Dieser ganze Gender-Wahnsinn muss aufhören!', "seed"),
    ("E03", "aussage", "E", "fremd", "fremd", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Die EU ist ein bürokratisches Monster, das uns nur schadet!', "seed"),
    ("E04", "aussage", "E", "fremd", "fremd", 'Grüne sind Kriegstreiber', 'Wärmepumpen funktionieren nur im Neubau!', "seed"),
    ("E05", "aussage", "E", "fremd", "fremd", 'Die Grünen wollen mir meine Heizung verbieten!', 'Blühwiese statt Rasen vor dem Rathaus', "seed+dev"),
    ("E06", "aussage", "E", "fremd", "fremd", 'Die Grünen wollen uns das Fleisch verbieten', 'Deutschland kann das Klima nicht alleine retten', "seed"),
    ("E07", "aussage", "E", "fremd", "fremd", 'E-Autos sind eine Totgeburt!', 'Die Grünen lassen alle Migranten rein', "seed"),
    ("E08", "aussage", "E", "fremd", "fremd", 'Klimaschutz', VERBOT, "seed+dev"),
    ("S01", "suche", "B", "gleich", "trivial", 'klimaschutz', 'Klimaschutz', "dev"),
    ("S02", "suche", "B", "gleich", "trivial", 'Wärmepumpe Altbau', 'wärmepumpe altbau', "eigen"),
    ("S03", "suche", "C", "gleich", "umformulierung", 'Wärmepumpe Altbau', 'Wärmepumpen im Altbau', "eigen"),
    ("S04", "suche", "D", "verwandt", "aspekt", 'Tempolimit', 'Tempolimit Unfälle', "eigen"),
    ("S05", "suche", "D", "verwandt", "aspekt", 'energiewende', 'Energiewende Kosten', "dev+eigen"),
    ("S06", "suche", "D", "verwandt", "aspekt", 'Balkonkraftwerk', 'Balkonkraftwerk Mietwohnung erlaubt', "eigen"),
    ("S07", "suche", "E", "fremd", "fremd", 'Tempolimit', 'Wärmepumpe Altbau', "eigen"),
    ("KA1", "kommentar", "A", "gleich", "identisch", REGELN, REGELN, "seed"),
    ("KA2", "kommentar", "A", "gleich", "identisch", GLAS, GLAS, "seed"),
    ("KB1", "kommentar", "B", "gleich", "trivial", REGELN.removesuffix("."), REGELN, "seed+eigen"),
    ("KB2", "kommentar", "B", "gleich", "trivial", GLAS.replace(" Die ", "  \nDie ").replace(" Wer ", "  \nWer "), GLAS, "seed+eigen"),
    ("KB3", "kommentar", "B", "gleich", "trivial", ALTBAU.removesuffix(".") + "!", ALTBAU, "seed+eigen"),
    ("KB4", "kommentar", "B", "gleich", "trivial", WIND_SONNE.lower(), WIND_SONNE, "seed+eigen"),
    ("KC1", "kommentar", "C", "gleich", "umformulierung", GLAS_EIGENE_WORTE, GLAS, "eigen"),
    ("KC2", "kommentar", "C", "gleich", "umformulierung", 'Freiheit wollen wir alle. Viele Regeln schützen sie sogar: der Sicherheitsgurt, der Nichtraucherschutz in Gaststätten, sauberes Leitungswasser. Entscheidend ist, wem eine Regel nützt.', REGELN, "eigen"),
    ("KC3", "kommentar", "C", "gleich", "umformulierung", 'Niemand soll sich fürs Heizen verschulden. Geht eine Heizung kaputt, darf man sie reparieren lassen. Die Vorgaben zu erneuerbarer Wärme betreffen nur Heizungen, die neu eingebaut werden.', REPARATUR, "eigen"),
    ("KC4", "kommentar", "C", "gleich", "zusatz", GLAS + GLAS_ZUSATZ, GLAS, "seed+eigen"),
    ("KD1", "kommentar", "D", "verwandt", "aspekt", GLAS, STANDORT, "seed"),
    ("KD2", "kommentar", "D", "verwandt", "aspekt", REGELN, WIND_SONNE, "seed"),
    ("KD3", "kommentar", "D", "verwandt", "aspekt", REPARATUR, BERATUNG, "seed"),
    # KD4 liegt an zwei verschiedenen Aussagen (Heizung, Waermepumpe), die uebrigen
    # KD-Paare je an derselben.
    ("KD4", "kommentar", "D", "verwandt", "aspekt", BERATUNG, ALTBAU, "seed"),
    ("KD5", "kommentar", "D", "verwandt", "aspekt", TELLER, HOF, "seed"),
    ("KE1", "kommentar", "E", "fremd", "fremd", REGELN, GLAS, "seed"),
    ("KE2", "kommentar", "E", "fremd", "fremd", EU_ALLTAG, TEMPOLIMIT, "seed"),
]

# fmt: off
# Aussage-Gruppen: ein Bestandstext, gegen den die Varianten gemessen werden.
# (label, phaenomen, kandidat)
_AUSSAGE_GRUPPEN = [
    ("VB", "verbot", VERBOT, [
        ("gleich", "wortstellung", "Eine Verbotspartei sind die Grünen"),
        ("gleich", "tippfehler", "Die Grünen sind eine Verbotspartie"),
        ("gleich", "umformulierung", "Die Grünen wollen ständig alles verbieten"),
        ("widerspricht", "verneinung", "Es stimmt nicht, dass die Grünen eine Verbotspartei sind"),
        ("widerspricht", "verneinung", "Die Grünen sind alles andere als eine Verbotspartei"),
        ("widerspricht", "antonym", "Die Grünen sind eine Freiheitspartei"),
        ("widerspricht", "quantor", "Die Grünen wollen nie etwas verbieten"),
        ("verwandt", "quantor", "Manche Grüne wollen viel verbieten"),
        ("verwandt", "frage", "Sind die Grünen eine Verbotspartei?"),
        ("verwandt", "aspekt", "Die Grünen wollen höhere Steuern"),
        ("verwandt", "mehrfachthema", "Die Grünen sind eine Verbotspartei und wollen höhere Steuern"),
        ("fremd", "fremd", "Der Supermarkt hat bis 22 Uhr offen"),
        ("widerspricht", "antonym", "Die Grünen sind eine liberale Partei, die wenig verbietet"),
        ("widerspricht", "verneinung", "Die Grünen sind gar keine Verbotspartei"),
    ]),
    ("WI", "wind", "Windräder töten Vögel", [
        ("gleich", "wortstellung", "Vögel werden von Windrädern getötet"),
        ("gleich", "tippfehler", "Windräder töten Vögl"),
        ("gleich", "umformulierung", "Windkraft bringt Vögel um"),
        ("widerspricht", "verneinung", "Windräder töten keine Vögel"),
        ("widerspricht", "verneinung", "Windräder töten Vögel nicht"),
        ("widerspricht", "quantor", "Kein Windrad tötet jemals einen Vogel"),
        ("verwandt", "quantor", "Manche Windräder töten Vögel"),
        ("verwandt", "quantor", "Alle Windräder töten Vögel"),
        ("verwandt", "skopus", "Windräder töten nicht nur Vögel"),
        ("verwandt", "frage", "Töten Windräder Vögel?"),
        ("verwandt", "aspekt", "Windräder sind zu laut"),
        ("verwandt", "mehrfachthema", "Windräder töten Vögel und verschandeln die Landschaft"),
        ("fremd", "fremd", "Brot ist in den letzten Jahren teurer geworden"),
        ("widerspricht", "antonym", "Windräder schützen Vögel"),
        ("widerspricht", "verneinung", "Niemals tötet ein Windrad einen Vogel"),
    ]),
    ("BS", "balkon", "Balkonsolar lohnt sich nie", [
        ("gleich", "tippfehler", "Balkonsolar lont sich nie"),
        ("gleich", "wortstellung", "Nie lohnt sich Balkonsolar"),
        ("gleich", "umformulierung", "Ein Balkonkraftwerk zahlt sich nie aus"),
        ("widerspricht", "quantor", "Balkonsolar lohnt sich manchmal"),
        ("widerspricht", "quantor", "Balkonsolar lohnt sich fast immer"),
        ("widerspricht", "quantor", "Balkonsolar lohnt sich selten"),
        ("widerspricht", "antonym", "Balkonsolar rechnet sich schnell"),
        ("widerspricht", "verneinung", "Es stimmt nicht, dass sich Balkonsolar nie lohnt"),
        ("verwandt", "quantor", "Balkonsolar lohnt sich nicht immer"),
        ("verwandt", "frage", "Lohnt sich Balkonsolar?"),
        ("verwandt", "aspekt", "Balkonsolar ist in Mietwohnungen verboten"),
        ("fremd", "fremd", "Im Winter sollte man öfter lüften"),
        ("widerspricht", "antonym", "Balkonsolar zahlt sich aus"),
        ("widerspricht", "verneinung", "Balkonsolar lohnt sich doch"),
    ]),
    ("WP", "waermepumpe", "Wärmepumpen funktionieren nur im Neubau", [
        ("gleich", "tippfehler", "Wärmepumpen funktionieren nur im Neubua"),
        ("gleich", "umformulierung", "Wärmepumpen taugen nur für neue Häuser"),
        ("gleich", "wortstellung", "Nur im Neubau funktionieren Wärmepumpen"),
        ("widerspricht", "skopus", "Wärmepumpen funktionieren nicht nur im Neubau"),
        ("widerspricht", "antonym", "Wärmepumpen funktionieren auch im Altbau"),
        ("widerspricht", "quantor", "Wärmepumpen funktionieren in jedem Haus"),
        ("widerspricht", "verneinung", "Wärmepumpen funktionieren im Neubau nicht"),
        ("verwandt", "aspekt", "Im Neubau arbeiten Wärmepumpen meist effizienter"),
        ("verwandt", "frage", "Funktionieren Wärmepumpen nur im Neubau?"),
        ("verwandt", "aspekt", "Wärmepumpen sind zu laut für Reihenhäuser"),
        ("fremd", "fremd", "Der Euro hat das Reisen in Europa einfacher gemacht"),
        ("widerspricht", "antonym", "Wärmepumpen funktionieren nur im Altbau"),
        ("widerspricht", "verneinung", "Wärmepumpen funktionieren nirgends"),
    ]),
    ("TL", "tempo", "Ein Tempolimit bringt nichts fürs Klima", [
        ("gleich", "tippfehler", "Ein Tempolimt bringt nichts fürs Klima"),
        ("gleich", "wortstellung", "Fürs Klima bringt ein Tempolimit nichts"),
        ("gleich", "umformulierung", "Ein Tempolimit ist für den Klimaschutz nutzlos"),
        ("widerspricht", "quantor", "Ein Tempolimit bringt etwas fürs Klima"),
        ("widerspricht", "quantor", "Ein Tempolimit bringt viel fürs Klima"),
        ("widerspricht", "verneinung", "Es stimmt nicht, dass ein Tempolimit nichts fürs Klima bringt"),
        ("widerspricht", "verneinung", "Ein Tempolimit bringt nicht nichts fürs Klima"),
        ("verwandt", "frage", "Bringt ein Tempolimit etwas fürs Klima?"),
        ("verwandt", "aspekt", "Ein Tempolimit macht die Autobahn sicherer"),
        ("verwandt", "mehrfachthema", "Ein Tempolimit bringt nichts fürs Klima und kostet nur Zeit"),
        ("fremd", "fremd", "Kinder brauchen mehr Sportunterricht"),
        ("widerspricht", "antonym", "Ein Tempolimit schadet dem Klima"),
        ("widerspricht", "verneinung", "Nicht nichts bringt ein Tempolimit fürs Klima"),
    ]),
    ("EA", "eauto", "E-Autos sind schlechter für die Umwelt als Verbrenner", [
        ("gleich", "umformulierung", "Verbrenner sind besser für die Umwelt als E-Autos"),
        ("gleich", "tippfehler", "E-Autos sind schlechter für die Umwelt als Verbrener"),
        ("gleich", "umformulierung", "Elektroautos schaden der Umwelt mehr als Benziner und Diesel"),
        ("widerspricht", "antonym", "E-Autos sind besser für die Umwelt als Verbrenner"),
        ("widerspricht", "wortstellung", "Verbrenner sind schlechter für die Umwelt als E-Autos"),
        ("widerspricht", "verneinung", "E-Autos sind nicht schlechter für die Umwelt als Verbrenner"),
        ("verwandt", "quantor", "Manche E-Autos sind schlechter für die Umwelt als Verbrenner"),
        ("verwandt", "frage", "Sind E-Autos schlechter für die Umwelt als Verbrenner?"),
        ("verwandt", "aspekt", "E-Autos sind zu teuer"),
        ("verwandt", "aspekt", "Für E-Autos gibt es zu wenige Ladesäulen"),
        ("fremd", "fremd", "Der Stadtpark braucht mehr Bänke"),
        ("widerspricht", "antonym", "E-Autos sind umweltfreundlicher als Verbrenner"),
        ("gleich", "verneinung", "E-Autos sind nicht besser für die Umwelt als Verbrenner, sondern schlechter"),
    ]),
    ("FL", "fleisch", "Die Grünen wollen uns das Fleisch verbieten", [
        ("gleich", "tippfehler", "Die Grünen wollen uns das Fleich verbieten"),
        ("gleich", "wortstellung", "Das Fleisch wollen uns die Grünen verbieten"),
        ("gleich", "umformulierung", "Die Grünen wollen, dass niemand mehr Fleisch essen darf"),
        ("widerspricht", "verneinung", "Die Grünen wollen uns das Fleisch nicht verbieten"),
        ("widerspricht", "quantor", "Die Grünen wollen niemandem das Fleisch verbieten"),
        ("widerspricht", "quantor", "Kein Grüner will Fleisch verbieten"),
        ("verwandt", "quantor", "Einige Grüne wollen Fleisch verbieten"),
        ("verwandt", "aspekt", "Die Grünen wollen Fleisch teurer machen"),
        ("verwandt", "frage", "Wollen die Grünen uns das Fleisch verbieten?"),
        ("verwandt", "aspekt", "Die Grünen wollen einen Veggie-Tag in Kantinen"),
        ("fremd", "fremd", "Handys gehören nicht in den Unterricht"),
        ("widerspricht", "antonym", "Die Grünen wollen uns das Fleisch erlauben"),
        ("widerspricht", "verneinung", "Kein Grüner will uns das Fleisch verbieten"),
    ]),
    ("EE", "erneuerbar", "Erneuerbare Energien sind zu teuer", [
        ("gleich", "tippfehler", "Erneuerbare Energein sind zu teuer"),
        ("gleich", "umformulierung", "Strom aus Wind und Sonne kostet zu viel"),
        ("gleich", "wortstellung", "Zu teuer sind erneuerbare Energien"),
        ("widerspricht", "antonym", "Erneuerbare Energien sind günstig"),
        ("widerspricht", "antonym", "Erneuerbare Energien sind preiswert"),
        ("widerspricht", "verneinung", "Erneuerbare Energien sind nicht zu teuer"),
        ("verwandt", "quantor", "Manche erneuerbaren Energien sind zu teuer"),
        ("widerspricht", "quantor", "Keine erneuerbare Energie ist zu teuer"),
        ("verwandt", "frage", "Sind erneuerbare Energien zu teuer?"),
        ("verwandt", "aspekt", "Erneuerbare Energien brauchen zu viel Fläche"),
        ("fremd", "fremd", "Im Sommer sollte man viel Wasser trinken"),
        ("widerspricht", "antonym", "Erneuerbare Energien sind zu billig"),
        ("gleich", "verneinung", "Erneuerbare Energien sind nicht bezahlbar"),
    ]),
    ("HZ", "heizung", "Die Grünen wollen mir meine Heizung verbieten", [
        ("gleich", "tippfehler", "Die Grünen wollen mir meine Heitzung verbieten"),
        ("gleich", "wortstellung", "Meine Heizung wollen mir die Grünen verbieten"),
        ("gleich", "umformulierung", "Die Grünen wollen mir vorschreiben, dass meine Heizung raus muss"),
        ("widerspricht", "verneinung", "Die Grünen wollen mir meine Heizung nicht verbieten"),
        ("widerspricht", "quantor", "Niemand will mir meine Heizung verbieten"),
        ("verwandt", "quantor", "Die Grünen wollen alle Heizungen verbieten"),
        ("verwandt", "aspekt", "Die Grünen wollen neue Ölheizungen verbieten"),
        ("verwandt", "frage", "Wollen die Grünen mir meine Heizung verbieten?"),
        ("verwandt", "mehrfachthema", "Die Grünen wollen mir meine Heizung und mein Auto verbieten"),
        ("fremd", "fremd", "Der Bäcker im Ort macht nächsten Monat zu"),
        ("widerspricht", "antonym", "Die Grünen wollen mir meine Heizung lassen"),
        ("widerspricht", "verneinung", "Die Grünen wollen mir nichts an meiner Heizung verbieten"),
    ]),
    ("EU", "eu", "Die EU schadet Deutschland", [
        ("gleich", "tippfehler", "Die EU schadet Deutchland"),
        ("gleich", "umformulierung", "Deutschland nimmt durch die EU Schaden"),
        ("gleich", "umformulierung", "Die Europäische Union ist schlecht für Deutschland"),
        ("widerspricht", "antonym", "Die EU nützt Deutschland"),
        ("widerspricht", "verneinung", "Die EU schadet Deutschland nicht"),
        ("verwandt", "wortstellung", "Deutschland schadet der EU"),
        ("verwandt", "quantor", "Die EU schadet Deutschland manchmal"),
        ("verwandt", "frage", "Schadet die EU Deutschland?"),
        ("verwandt", "aspekt", "Die EU macht zu viele Vorschriften"),
        ("fremd", "fremd", "Hunde sollten im Wald an die Leine"),
        ("widerspricht", "antonym", "Die EU hilft Deutschland"),
        ("widerspricht", "verneinung", "Die EU schadet Deutschland keineswegs"),
    ]),
    ("AT", "atom", "Der Atomausstieg war ein Fehler", [
        ("gleich", "tippfehler", "Der Atomaustieg war ein Fehler"),
        ("gleich", "umformulierung", "Es war falsch, aus der Atomkraft auszusteigen"),
        ("gleich", "wortstellung", "Ein Fehler war der Atomausstieg"),
        ("widerspricht", "antonym", "Der Atomausstieg war richtig"),
        ("widerspricht", "verneinung", "Der Atomausstieg war kein Fehler"),
        ("widerspricht", "verneinung", "Der Atomausstieg war nicht falsch"),
        ("verwandt", "aspekt", "Atomkraftwerke sind zu teuer"),
        ("verwandt", "aspekt", "Wir sollten neue Atomkraftwerke bauen"),
        ("verwandt", "frage", "War der Atomausstieg ein Fehler?"),
        ("verwandt", "mehrfachthema", "Der Atomausstieg und der Kohleausstieg waren Fehler"),
        ("fremd", "fremd", "Die Schulen brauchen mehr Lehrkräfte"),
        ("widerspricht", "antonym", "Der Atomausstieg war ein Erfolg"),
        ("gleich", "verneinung", "Der Atomausstieg war nicht richtig"),
    ]),
    ("DB", "bahn", "Die Bahn ist immer unpünktlich", [
        ("gleich", "tippfehler", "Die Bahn ist imer unpünktlich"),
        ("gleich", "quantor", "Die Bahn kommt nie pünktlich"),
        ("gleich", "wortstellung", "Immer ist die Bahn unpünktlich"),
        ("widerspricht", "antonym", "Die Bahn ist immer pünktlich"),
        ("widerspricht", "quantor", "Die Bahn ist nie unpünktlich"),
        ("widerspricht", "quantor", "Die Bahn ist meistens pünktlich"),
        ("verwandt", "quantor", "Die Bahn ist oft unpünktlich"),
        ("widerspricht", "verneinung", "Die Bahn ist nicht immer unpünktlich"),
        ("verwandt", "frage", "Warum ist die Bahn so unpünktlich?"),
        ("verwandt", "aspekt", "Bahnfahren ist zu teuer"),
        ("fremd", "fremd", "Tomaten wachsen auch im Kübel"),
        ("widerspricht", "antonym", "Die Bahn ist stets pünktlich"),
        ("widerspricht", "verneinung", "Die Bahn ist niemals unpünktlich"),
    ]),
    ("KW", "klimawandel", "Der Klimawandel ist menschengemacht", [
        ("gleich", "tippfehler", "Der Klimawandel ist menschgemacht"),
        ("gleich", "umformulierung", "Der Mensch verursacht den Klimawandel"),
        ("gleich", "wortstellung", "Menschengemacht ist der Klimawandel"),
        ("widerspricht", "verneinung", "Der Klimawandel ist nicht menschengemacht"),
        ("widerspricht", "quantor", "Der Klimawandel hat nur natürliche Ursachen"),
        ("widerspricht", "quantor", "Der Mensch hat keinen Anteil am Klimawandel"),
        ("widerspricht", "verneinung", "Den Klimawandel gibt es nicht"),
        ("verwandt", "quantor", "Der Klimawandel ist teilweise menschengemacht"),
        ("verwandt", "frage", "Ist der Klimawandel menschengemacht?"),
        ("verwandt", "aspekt", "Der Klimawandel macht Hitzesommer häufiger"),
        ("fremd", "fremd", "Fußball ist der beliebteste Sport in Deutschland"),
        ("widerspricht", "antonym", "Der Klimawandel ist natürlichen Ursprungs"),
        ("gleich", "verneinung", "Der Klimawandel ist nicht natürlichen Ursprungs"),
    ]),
    ("SP", "strompreis", "Die Energiewende macht den Strom teurer", [
        ("gleich", "tippfehler", "Die Energiewnde macht den Strom teurer"),
        ("gleich", "umformulierung", "Wegen der Energiewende steigen die Strompreise"),
        ("gleich", "wortstellung", "Den Strom macht die Energiewende teurer"),
        ("widerspricht", "antonym", "Die Energiewende macht den Strom billiger"),
        ("widerspricht", "antonym", "Die Energiewende senkt die Strompreise"),
        ("widerspricht", "verneinung", "Die Energiewende macht den Strom nicht teurer"),
        ("verwandt", "aspekt", "Die Energiewende macht den Strom kurzfristig teurer"),
        ("verwandt", "aspekt", "Die Energiewende kostet Arbeitsplätze"),
        ("verwandt", "frage", "Macht die Energiewende den Strom teurer?"),
        ("verwandt", "mehrfachthema", "Die Energiewende macht den Strom teurer und unsicherer"),
        ("fremd", "fremd", "Viele Vereine suchen Ehrenamtliche"),
        ("widerspricht", "antonym", "Die Energiewende macht den Strom günstiger"),
        ("widerspricht", "verneinung", "Durch die Energiewende wird der Strom nicht teurer"),
    ]),
    ("LR", "land", "Den Grünen ist der ländliche Raum egal", [
        ("gleich", "tippfehler", "Den Grünen ist der ländlche Raum egal"),
        ("gleich", "umformulierung", "Die Grünen kümmern sich nicht um die Dörfer"),
        ("gleich", "wortstellung", "Der ländliche Raum ist den Grünen egal"),
        ("widerspricht", "verneinung", "Den Grünen ist der ländliche Raum nicht egal"),
        ("widerspricht", "antonym", "Den Grünen ist der ländliche Raum wichtig"),
        ("verwandt", "quantor", "Manchen Grünen ist der ländliche Raum egal"),
        ("widerspricht", "quantor", "Keinem Grünen ist der ländliche Raum egal"),
        ("verwandt", "frage", "Ist den Grünen der ländliche Raum egal?"),
        ("verwandt", "aspekt", "Auf dem Land fehlen Hausärzte"),
        ("fremd", "fremd", "Kaffee schmeckt frisch gemahlen am besten"),
        ("widerspricht", "antonym", "Den Grünen liegt der ländliche Raum am Herzen"),
        ("widerspricht", "verneinung", "Der ländliche Raum ist den Grünen keineswegs egal"),
    ]),
    ("CO", "co2preis", "Der CO2-Preis trifft vor allem Menschen mit wenig Geld", [
        ("gleich", "tippfehler", "Der CO2-Preis trift vor allem Menschen mit wenig Geld"),
        ("gleich", "umformulierung", "Unter dem CO2-Preis leiden besonders Geringverdiener"),
        ("gleich", "wortstellung", "Vor allem Menschen mit wenig Geld trifft der CO2-Preis"),
        ("widerspricht", "antonym", "Der CO2-Preis trifft vor allem Menschen mit viel Geld"),
        ("widerspricht", "verneinung", "Der CO2-Preis trifft Menschen mit wenig Geld nicht besonders"),
        ("verwandt", "quantor", "Der CO2-Preis trifft alle"),
        ("verwandt", "aspekt", "Das Klimageld gleicht den CO2-Preis aus"),
        ("verwandt", "frage", "Wen trifft der CO2-Preis?"),
        ("verwandt", "aspekt", "Der CO2-Preis macht Tanken teurer"),
        ("fremd", "fremd", "Die Stadtbibliothek hat jetzt auch sonntags offen"),
        ("widerspricht", "antonym", "Der CO2-Preis trifft vor allem Reiche"),
        ("widerspricht", "verneinung", "Der CO2-Preis trifft nicht vor allem Menschen mit wenig Geld"),
    ]),
    ("KO", "kohle", "Wir brauchen Kohlekraftwerke für eine sichere Stromversorgung", [
        ("gleich", "tippfehler", "Wir brauchen Kohlekraftwerke für eine sichere Stromversorung"),
        ("gleich", "verneinung", "Ohne Kohlekraftwerke ist die Stromversorgung nicht sicher"),
        ("gleich", "wortstellung", "Für eine sichere Stromversorgung brauchen wir Kohlekraftwerke"),
        ("widerspricht", "verneinung", "Wir brauchen keine Kohlekraftwerke für eine sichere Stromversorgung"),
        ("widerspricht", "verneinung", "Auch ohne Kohlekraftwerke ist die Stromversorgung sicher"),
        ("verwandt", "aspekt", "Kohlekraftwerke schaden dem Klima"),
        ("verwandt", "quantor", "Wir brauchen noch einige Jahre Kohlekraftwerke für eine sichere Stromversorgung"),
        ("verwandt", "frage", "Brauchen wir Kohlekraftwerke für eine sichere Stromversorgung?"),
        ("fremd", "fremd", "Die Sommerferien sind zu lang"),
        ("widerspricht", "antonym", "Kohlekraftwerke gefährden eine sichere Stromversorgung"),
        ("widerspricht", "verneinung", "Für eine sichere Stromversorgung brauchen wir keine Kohlekraftwerke"),
    ]),
    ("RW", "radweg", "Radwege nehmen Autofahrern den Platz weg", [
        ("gleich", "tippfehler", "Radwege nehmen Autofahern den Platz weg"),
        ("gleich", "umformulierung", "Für Radwege wird den Autos die Straße weggenommen"),
        ("gleich", "wortstellung", "Den Autofahrern nehmen Radwege den Platz weg"),
        ("widerspricht", "verneinung", "Radwege nehmen Autofahrern keinen Platz weg"),
        ("verwandt", "wortstellung", "Autofahrer nehmen Radwegen den Platz weg"),
        ("verwandt", "quantor", "Manche Radwege nehmen Autofahrern den Platz weg"),
        ("verwandt", "aspekt", "Radwege machen den Verkehr sicherer"),
        ("verwandt", "frage", "Nehmen Radwege Autofahrern den Platz weg?"),
        ("fremd", "fremd", "Die Gemeinde baut ein neues Hallenbad"),
        ("widerspricht", "antonym", "Radwege schaffen Autofahrern Platz"),
        ("widerspricht", "verneinung", "Radwege nehmen Autofahrern nicht den Platz weg"),
    ]),
    ("GN", "gendern", "Die Grünen wollen allen das Gendern vorschreiben", [
        ("gleich", "tippfehler", "Die Grünen wollen allen das Gendern vorschrieben"),
        ("gleich", "umformulierung", "Die Grünen wollen das Gendern für alle zur Pflicht machen"),
        ("widerspricht", "quantor", "Die Grünen wollen niemandem das Gendern vorschreiben"),
        ("widerspricht", "verneinung", "Die Grünen wollen das Gendern nicht vorschreiben"),
        ("widerspricht", "skopus", "Die Grünen wollen nicht allen das Gendern vorschreiben"),
        ("verwandt", "quantor", "Die Grünen wollen Behörden das Gendern vorschreiben"),
        ("verwandt", "frage", "Wollen die Grünen allen das Gendern vorschreiben?"),
        ("verwandt", "aspekt", "Gendern macht Texte schwer lesbar"),
        ("fremd", "fremd", "Im Herbst fallen die Blätter"),
        ("widerspricht", "antonym", "Die Grünen wollen allen das Gendern freistellen"),
        ("widerspricht", "verneinung", "Die Grünen schreiben niemandem das Gendern vor"),
    ]),
    ("WS", "wasserstoff", "Wasserstoff ist die Lösung für alle Heizungen", [
        ("gleich", "tippfehler", "Wasserstof ist die Lösung für alle Heizungen"),
        ("gleich", "umformulierung", "Jede Heizung lässt sich am besten mit Wasserstoff betreiben"),
        ("widerspricht", "quantor", "Wasserstoff ist für keine Heizung die Lösung"),
        ("verwandt", "quantor", "Wasserstoff ist die Lösung für manche Heizungen"),
        ("widerspricht", "skopus", "Wasserstoff ist nicht die Lösung für alle Heizungen"),
        ("widerspricht", "skopus", "Wasserstoff ist für alle Heizungen nicht die Lösung"),
        ("verwandt", "aspekt", "Wasserstoff ist knapp und teuer"),
        ("verwandt", "frage", "Ist Wasserstoff die Lösung für alle Heizungen?"),
        ("fremd", "fremd", "Der Marktplatz soll im Sommer einen Brunnen bekommen"),
        ("widerspricht", "antonym", "Wasserstoff ist für alle Heizungen ungeeignet"),
        ("widerspricht", "verneinung", "Wasserstoff ist keine Lösung für Heizungen"),
    ]),
    ("IN", "insekten", "Pestizide sind schuld am Insektensterben", [
        ("gleich", "tippfehler", "Pestizide sind schuld am Insektenstreben"),
        ("gleich", "umformulierung", "Das Insektensterben wird von Pestiziden verursacht"),
        ("widerspricht", "verneinung", "Pestizide sind nicht schuld am Insektensterben"),
        ("widerspricht", "verneinung", "Am Insektensterben haben Pestizide keine Schuld"),
        ("verwandt", "quantor", "Pestizide sind mitschuld am Insektensterben"),
        ("verwandt", "quantor", "Pestizide sind allein schuld am Insektensterben"),
        ("verwandt", "aspekt", "Blühstreifen helfen den Insekten"),
        ("verwandt", "frage", "Sind Pestizide schuld am Insektensterben?"),
        ("fremd", "fremd", "Der Wochenmarkt findet jetzt samstags statt"),
        ("widerspricht", "antonym", "Pestizide sind unschuldig am Insektensterben"),
        ("widerspricht", "verneinung", "Pestizide tragen keine Schuld am Insektensterben"),
    ]),
    # Test-Gruppen (TEST_GRUPPEN): neue Bestandstexte, die im Train-Teil nicht vorkommen.
    ("WA", "wald", "Windräder im Wald zerstören die Natur", [
        ("gleich", "tippfehler", "Windräder im Wald zerstören die Natru"),
        ("gleich", "umformulierung", "Windkraft im Wald macht die Natur kaputt"),
        ("gleich", "wortstellung", "Die Natur zerstören Windräder im Wald"),
        ("widerspricht", "verneinung", "Windräder im Wald zerstören die Natur nicht"),
        ("widerspricht", "antonym", "Windräder im Wald schonen die Natur"),
        ("verwandt", "quantor", "Manche Windräder im Wald zerstören die Natur"),
        ("widerspricht", "quantor", "Kein Windrad im Wald zerstört die Natur"),
        ("verwandt", "frage", "Zerstören Windräder im Wald die Natur?"),
        ("verwandt", "aspekt", "Für Windräder im Wald werden Bäume gefällt"),
        ("verwandt", "mehrfachthema", "Windräder im Wald zerstören die Natur und stören die Anwohner"),
        ("fremd", "fremd", "Im Rathaus gibt es zu wenige Termine"),
        ("widerspricht", "antonym", "Windräder im Wald schützen die Natur"),
        ("widerspricht", "verneinung", "Windräder im Wald zerstören keine Natur"),
    ]),
    ("NV", "nahverkehr", "Der Nahverkehr auf dem Land ist zu schlecht", [
        ("gleich", "tippfehler", "Der Nahverkehr auf dem Land ist zu schlect"),
        ("gleich", "umformulierung", "Busse und Bahnen auf dem Land taugen nichts"),
        ("gleich", "wortstellung", "Auf dem Land ist der Nahverkehr zu schlecht"),
        ("widerspricht", "antonym", "Der Nahverkehr auf dem Land ist gut"),
        ("widerspricht", "verneinung", "Der Nahverkehr auf dem Land ist nicht zu schlecht"),
        ("verwandt", "quantor", "Der Nahverkehr ist überall zu schlecht"),
        ("verwandt", "aspekt", "Der Nahverkehr in der Stadt ist zu schlecht"),
        ("verwandt", "frage", "Ist der Nahverkehr auf dem Land zu schlecht?"),
        ("verwandt", "aspekt", "Busfahren auf dem Land ist zu teuer"),
        ("fremd", "fremd", "Kartoffeln lagert man am besten dunkel"),
        ("widerspricht", "antonym", "Der Nahverkehr auf dem Land ist ausgezeichnet"),
        ("gleich", "verneinung", "Der Nahverkehr auf dem Land ist nicht gut genug"),
    ]),
    ("DT", "ticket", "Das Deutschlandticket ist zu teuer", [
        ("gleich", "tippfehler", "Das Deutschlandtiket ist zu teuer"),
        ("gleich", "umformulierung", "Das Deutschlandticket kostet zu viel"),
        ("gleich", "wortstellung", "Zu teuer ist das Deutschlandticket"),
        ("widerspricht", "antonym", "Das Deutschlandticket ist günstig"),
        ("widerspricht", "antonym", "Das Deutschlandticket ist zu billig"),
        ("widerspricht", "verneinung", "Das Deutschlandticket ist nicht zu teuer"),
        ("verwandt", "quantor", "Für manche ist das Deutschlandticket zu teuer"),
        ("widerspricht", "quantor", "Für niemanden ist das Deutschlandticket zu teuer"),
        ("verwandt", "frage", "Ist das Deutschlandticket zu teuer?"),
        ("verwandt", "aspekt", "Das Deutschlandticket nützt auf dem Dorf wenig"),
        ("fremd", "fremd", "Zahnseide sollte man täglich benutzen"),
        ("widerspricht", "antonym", "Das Deutschlandticket ist preiswert"),
        ("widerspricht", "verneinung", "Das Deutschlandticket ist keineswegs zu teuer"),
    ]),
    ("BI", "bio", "Bio-Lebensmittel sind gesünder", [
        ("gleich", "tippfehler", "Bio-Lebensmitel sind gesünder"),
        ("gleich", "umformulierung", "Bio-Essen ist besser für die Gesundheit"),
        ("gleich", "wortstellung", "Gesünder sind Bio-Lebensmittel"),
        ("widerspricht", "verneinung", "Bio-Lebensmittel sind nicht gesünder"),
        ("widerspricht", "antonym", "Bio-Lebensmittel sind ungesünder"),
        ("verwandt", "quantor", "Manche Bio-Lebensmittel sind gesünder"),
        ("widerspricht", "quantor", "Kein Bio-Lebensmittel ist gesünder"),
        ("verwandt", "aspekt", "Bio-Lebensmittel sind zu teuer"),
        ("verwandt", "frage", "Sind Bio-Lebensmittel gesünder?"),
        ("verwandt", "mehrfachthema", "Bio-Lebensmittel sind gesünder und besser fürs Klima"),
        ("fremd", "fremd", "Die Brücke wird im Sommer saniert"),
        ("widerspricht", "antonym", "Bio-Lebensmittel sind schädlicher"),
        ("gleich", "verneinung", "Bio-Lebensmittel sind nicht ungesünder, sondern gesünder"),
    ]),
    ("FB", "fliegen", "Fliegen ist billiger als Bahnfahren", [
        ("gleich", "tippfehler", "Fliegen ist biliger als Bahnfahren"),
        ("gleich", "umformulierung", "Bahnfahren ist teurer als Fliegen"),
        ("widerspricht", "wortstellung", "Bahnfahren ist billiger als Fliegen"),
        ("widerspricht", "antonym", "Fliegen ist teurer als Bahnfahren"),
        ("widerspricht", "verneinung", "Fliegen ist nicht billiger als Bahnfahren"),
        ("verwandt", "quantor", "Fliegen ist oft billiger als Bahnfahren"),
        ("widerspricht", "quantor", "Fliegen ist nie billiger als Bahnfahren"),
        ("verwandt", "frage", "Ist Fliegen billiger als Bahnfahren?"),
        ("verwandt", "aspekt", "Kerosin ist von der Energiesteuer befreit"),
        ("fremd", "fremd", "Viele Kinder können nicht schwimmen"),
        ("widerspricht", "antonym", "Fliegen kostet mehr als Bahnfahren"),
        ("widerspricht", "verneinung", "Fliegen ist keineswegs billiger als Bahnfahren"),
    ]),
    ("AK", "akku", "Akkus von E-Autos halten nicht lange", [
        ("gleich", "tippfehler", "Akkus von E-Autos halten nich lange"),
        ("gleich", "umformulierung", "Die Batterie eines Elektroautos ist schnell kaputt"),
        ("gleich", "wortstellung", "Nicht lange halten die Akkus von E-Autos"),
        ("widerspricht", "verneinung", "Akkus von E-Autos halten lange"),
        ("widerspricht", "antonym", "Akkus von E-Autos halten ein Autoleben lang"),
        ("widerspricht", "verneinung", "Es stimmt nicht, dass Akkus von E-Autos nicht lange halten"),
        ("verwandt", "quantor", "Manche Akkus von E-Autos halten nicht lange"),
        ("verwandt", "skopus", "Nicht alle Akkus von E-Autos halten lange"),
        ("verwandt", "frage", "Wie lange halten Akkus von E-Autos?"),
        ("verwandt", "aspekt", "Akkus von E-Autos lassen sich recyceln"),
        ("fremd", "fremd", "Der Chor sucht neue Stimmen"),
        ("widerspricht", "antonym", "Akkus von E-Autos sind langlebig"),
        ("gleich", "verneinung", "Akkus von E-Autos sind nicht langlebig"),
    ]),
    ("MO", "moor", "Moore speichern viel CO2", [
        ("gleich", "tippfehler", "Moore speicher viel CO2"),
        ("gleich", "umformulierung", "In Mooren ist viel Kohlenstoff gebunden"),
        ("gleich", "wortstellung", "Viel CO2 speichern Moore"),
        ("widerspricht", "verneinung", "Moore speichern kein CO2"),
        ("widerspricht", "antonym", "Moore speichern wenig CO2"),
        ("verwandt", "quantor", "Manche Moore speichern viel CO2"),
        ("verwandt", "aspekt", "Trockengelegte Moore geben CO2 ab"),
        ("verwandt", "frage", "Speichern Moore viel CO2?"),
        ("verwandt", "aspekt", "Moore sollten wieder vernässt werden"),
        ("fremd", "fremd", "Das Stadtfest ist dieses Jahr im August"),
        ("widerspricht", "antonym", "Moore speichern kaum CO2"),
        ("widerspricht", "verneinung", "Moore speichern nicht viel CO2"),
    ]),
    ("FW", "fernwaerme", "Fernwärme ist teurer als eine Gasheizung", [
        ("gleich", "tippfehler", "Fernwärme ist teuerer als eine Gasheizung"),
        ("gleich", "umformulierung", "Eine Gasheizung ist günstiger als Fernwärme"),
        ("widerspricht", "wortstellung", "Eine Gasheizung ist teurer als Fernwärme"),
        ("widerspricht", "antonym", "Fernwärme ist billiger als eine Gasheizung"),
        ("widerspricht", "verneinung", "Fernwärme ist nicht teurer als eine Gasheizung"),
        ("verwandt", "quantor", "Fernwärme ist manchmal teurer als eine Gasheizung"),
        ("widerspricht", "quantor", "Fernwärme ist nie teurer als eine Gasheizung"),
        ("verwandt", "frage", "Ist Fernwärme teurer als eine Gasheizung?"),
        ("verwandt", "aspekt", "Fernwärme gibt es nur in Städten"),
        ("fremd", "fremd", "Der Spielplatz bekommt eine neue Rutsche"),
        ("widerspricht", "antonym", "Fernwärme ist günstiger als eine Gasheizung"),
        ("widerspricht", "verneinung", "Fernwärme ist keineswegs teurer als eine Gasheizung"),
    ]),
    ("WO", "wolf", "Der Wolf ist eine Gefahr für Weidetiere", [
        ("gleich", "tippfehler", "Der Wolf ist eine Gefahr für Weidetire"),
        ("gleich", "umformulierung", "Wölfe bedrohen Schafe und Rinder auf der Weide"),
        ("gleich", "wortstellung", "Eine Gefahr für Weidetiere ist der Wolf"),
        ("widerspricht", "verneinung", "Der Wolf ist keine Gefahr für Weidetiere"),
        ("widerspricht", "antonym", "Für Weidetiere ist der Wolf ungefährlich"),
        ("verwandt", "aspekt", "Der Wolf ist eine Gefahr für Menschen"),
        ("verwandt", "quantor", "Einzelne Wölfe sind eine Gefahr für Weidetiere"),
        ("verwandt", "frage", "Ist der Wolf eine Gefahr für Weidetiere?"),
        ("verwandt", "aspekt", "Herdenschutzzäune halten Wölfe ab"),
        ("fremd", "fremd", "Die Grundschule bekommt eine Mensa"),
        ("widerspricht", "antonym", "Der Wolf ist für Weidetiere harmlos"),
        ("widerspricht", "verneinung", "Der Wolf ist für Weidetiere nicht gefährlich"),
    ]),
    ("MU", "muell", "Mülltrennung bringt nichts", [
        ("gleich", "tippfehler", "Mültrennung bringt nichts"),
        ("gleich", "umformulierung", "Müll zu trennen ist sinnlos"),
        ("gleich", "wortstellung", "Nichts bringt die Mülltrennung"),
        ("widerspricht", "quantor", "Mülltrennung bringt etwas"),
        ("widerspricht", "quantor", "Mülltrennung bringt viel"),
        ("widerspricht", "verneinung", "Mülltrennung ist nicht sinnlos"),
        ("verwandt", "aspekt", "Getrennter Müll wird am Ende doch zusammengekippt"),
        ("verwandt", "frage", "Bringt Mülltrennung etwas?"),
        ("verwandt", "aspekt", "Plastikmüll wird oft ins Ausland gebracht"),
        ("fremd", "fremd", "Der Zug nach Hamburg fällt heute aus"),
        ("widerspricht", "antonym", "Mülltrennung lohnt sich"),
        ("widerspricht", "verneinung", "Es stimmt nicht, dass Mülltrennung nichts bringt"),
    ]),
]

# Hintergrundinfos: Bestandstexte aus dem Seed (statements_with_generictexts), geprueft
# wird wie im Dienst der Text der Hintergrundinfo (passage/passage).
HI_KOSTEN = "Das Fraunhofer ISE vergleicht regelmäßig die Stromgestehungskosten neuer Kraftwerke in Deutschland. In der Ausgabe von 2024 liegen Freiflächen-Photovoltaik und Windenergie an Land bei 4,1 bis 9,2 Cent pro Kilowattstunde. Auch Photovoltaik mit Batteriespeicher ist danach günstiger als neue konventionelle Kraftwerke."
HI_ANTEIL = "Laut Umweltbundesamt deckten erneuerbare Energien 2024 54,4 Prozent des Bruttostromverbrauchs in Deutschland."
HI_AUSFALL = "Die Bundesnetzagentur misst jedes Jahr, wie lange die Stromversorgung im Schnitt unterbrochen ist. Für 2023 lag die durchschnittliche Unterbrechung bei 12,8 Minuten je Letztverbraucher. Gezählt werden ungeplante Unterbrechungen, die länger als drei Minuten dauern."
HI_JAZ = "Das Fraunhofer ISE misst Wärmepumpen in bestehenden Wohngebäuden. Nach den Zwischenergebnissen von 2024 erreichen 22 Außenluft-Wärmepumpen eine mittlere Jahresarbeitszahl von 3,3, mit einer Spanne von 2,4 bis 4,0. Aus einer Kilowattstunde Strom entstehen also im Schnitt 3,3 Kilowattstunden Wärme."
HI_TEMPO = "Das Umweltbundesamt hat für das Jahr 2024 berechnet, was ein Tempolimit von 120 km/h auf Autobahnen und 80 km/h außerorts bringt: 6,6 Millionen Tonnen CO2-Äquivalente und rund 2,8 Milliarden Liter Kraftstoff weniger. Allein der direkte Effekt der niedrigeren Geschwindigkeit spart sofort 4,9 Millionen Tonnen."
HI_GLAS = "Die Länderarbeitsgemeinschaft der Vogelschutzwarten schätzt, dass in Deutschland jedes Jahr 100 bis 115 Millionen Vögel an Glasscheiben und Glasfassaden sterben. Die Zahl ist eine Hochrechnung, keine Zählung."

_HINTERGRUND_GRUPPEN = [
    ("HK", "hi_kosten", HI_KOSTEN, [
        ("gleich", "trivial", HI_KOSTEN.lower()),
        ("gleich", "umformulierung", "Neue Solarparks und Windräder an Land erzeugen Strom für 4,1 bis 9,2 Cent je Kilowattstunde, so die Kostenstudie 2024 des Fraunhofer ISE. Selbst Solarstrom mit Batteriespeicher ist günstiger als Strom aus neuen konventionellen Kraftwerken."),
        ("widerspricht", "zahl", HI_KOSTEN.replace("4,1 bis 9,2", "14,1 bis 19,2")),
        ("widerspricht", "verneinung", HI_KOSTEN.replace("Auch Photovoltaik mit Batteriespeicher ist danach günstiger", "Photovoltaik mit Batteriespeicher ist danach aber nicht günstiger")),
        ("verwandt", "aspekt", "Was Strom aus neuen Gaskraftwerken kostet, hängt stark davon ab, wie viele Stunden im Jahr sie laufen und wie teuer CO2-Zertifikate sind."),
        ("fremd", "fremd", "Ein Mischwald bindet über Jahrzehnte Kohlenstoff im Holz und im Boden. Wie viel, hängt von Alter, Baumarten und Standort ab."),
    ]),
    ("HA", "hi_anteil", HI_ANTEIL, [
        ("gleich", "trivial", HI_ANTEIL.removesuffix(".")),
        ("gleich", "umformulierung", "2024 kamen 54,4 Prozent des in Deutschland verbrauchten Stroms aus erneuerbaren Quellen, so das Umweltbundesamt."),
        ("gleich", "zusatz", HI_ANTEIL + " Quelle: Umweltbundesamt, Erneuerbare Energien in Zahlen."),
        ("widerspricht", "zahl", HI_ANTEIL.replace("54,4", "45,4")),
        ("widerspricht", "verneinung", "Laut Umweltbundesamt deckten erneuerbare Energien 2024 nicht einmal die Hälfte des Bruttostromverbrauchs in Deutschland."),
        ("verwandt", "zahl", HI_ANTEIL.replace("2024", "2014")),
        ("verwandt", "aspekt", "Laut Umweltbundesamt kam 2024 der größte Teil des erneuerbaren Stroms in Deutschland aus Windenergie."),
        ("fremd", "fremd", "Die Wohnfläche pro Kopf ist in Deutschland in den letzten Jahrzehnten gestiegen."),
    ]),
    ("HU", "hi_ausfall", HI_AUSFALL, [
        ("gleich", "identisch", HI_AUSFALL),
        ("gleich", "trivial", HI_AUSFALL.replace(". ", ".  ")),
        ("gleich", "umformulierung", "Im Jahr 2023 war der Strom in Deutschland pro Kunde im Schnitt nur 12,8 Minuten weg. Das zeigt die jährliche Auswertung der Bundesnetzagentur, die ungeplante Ausfälle ab drei Minuten Dauer zählt."),
        ("widerspricht", "zahl", HI_AUSFALL.replace("12,8 Minuten", "128 Minuten")),
        ("widerspricht", "verneinung", HI_AUSFALL.replace("Gezählt werden ungeplante", "Nicht gezählt werden ungeplante")),
        ("verwandt", "aspekt", "Die Bundesnetzagentur wertet auch aus, wie oft die Stromversorgung in einem Jahr unterbrochen ist, getrennt nach Nieder- und Mittelspannung."),
        ("fremd", "fremd", "Im Berufsverkehr sitzt in einem Auto im Schnitt kaum mehr als eine Person."),
    ]),
    ("HJ", "hi_jaz", HI_JAZ, [
        ("gleich", "trivial", HI_JAZ.removesuffix(".") + "!"),
        ("gleich", "umformulierung", "Im Feldtest des Fraunhofer ISE in bestehenden Wohngebäuden kommen 22 Luft-Wärmepumpen auf eine mittlere Jahresarbeitszahl von 3,3 (Spanne 2,4 bis 4,0). Eine Kilowattstunde Strom wird so im Schnitt zu 3,3 Kilowattstunden Wärme."),
        ("widerspricht", "zahl", HI_JAZ.replace("3,3", "1,3")),
        ("verwandt", "zahl", HI_JAZ.replace("2024", "2020")),
        ("verwandt", "aspekt", "Erdwärmepumpen erreichen im Feldtest des Fraunhofer ISE in der Regel höhere Jahresarbeitszahlen als Luft-Wärmepumpen."),
        ("fremd", "fremd", "Wer mit dem Fahrrad zur Arbeit fährt, bewegt sich im Alltag, ohne extra Zeit für Sport einzuplanen."),
    ]),
    ("HT", "hi_tempo", HI_TEMPO, [
        ("gleich", "umformulierung", "Ein Tempolimit von 120 km/h auf Autobahnen und 80 km/h außerorts würde laut Umweltbundesamt jährlich 6,6 Millionen Tonnen CO2-Äquivalente einsparen, dazu rund 2,8 Milliarden Liter Kraftstoff. Schon die geringere Geschwindigkeit allein bringt sofort 4,9 Millionen Tonnen."),
        ("gleich", "zusatz", HI_TEMPO + " Quelle: Umweltbundesamt."),
        ("widerspricht", "zahl", HI_TEMPO.replace("6,6 Millionen", "0,6 Millionen")),
        ("verwandt", "zahl", HI_TEMPO.replace("120 km/h", "130 km/h")),
        ("verwandt", "aspekt", "Ein Tempolimit auf Autobahnen senkt nach Studien auch die Zahl schwerer Unfälle."),
        ("fremd", "fremd", "Ein Liter Leitungswasser kostet in Deutschland meist weniger als einen Cent."),
    ]),
    ("HG", "hi_glas", HI_GLAS, [
        ("gleich", "trivial", HI_GLAS.lower()),
        ("gleich", "umformulierung", "An Glasscheiben und Glasfassaden sterben in Deutschland jährlich geschätzt 100 bis 115 Millionen Vögel. Das ist eine Hochrechnung der Vogelschutzwarten der Länder, keine Zählung."),
        ("widerspricht", "zahl", HI_GLAS.replace("100 bis 115 Millionen", "100 bis 115 Tausend")),
        ("widerspricht", "wortstellung", HI_GLAS.replace("Die Zahl ist eine Hochrechnung, keine Zählung.", "Die Zahl ist eine Zählung, keine Hochrechnung.")),
        ("verwandt", "aspekt", "Markierungen auf großen Glasflächen machen die Scheiben für Vögel sichtbar und verringern Kollisionen."),
        ("fremd", "fremd", "In Deutschland gibt es über zehntausend Gemeinden."),
    ]),
]
# fmt: on

PAARE = [
    *(Paar(*zeile, gruppe="alt") for zeile in _ALT),
    *(
        paar
        for kuerzel, gruppe, bestand, varianten in _AUSSAGE_GRUPPEN
        for paar in _gruppe("aussage", kuerzel, gruppe, bestand, varianten)
    ),
    *(
        paar
        for kuerzel, gruppe, bestand, varianten in _HINTERGRUND_GRUPPEN
        for paar in _gruppe(
            "hintergrundinfo", kuerzel, gruppe, bestand, varianten, "seed+eigen"
        )
    ),
]
