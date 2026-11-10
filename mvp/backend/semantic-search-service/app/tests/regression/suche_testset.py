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
- quelle: seed = Aussage aus mvp/data/seed/v1.0 woertlich, start = Aussage aus dem
  Startbestand woertlich (STARTBESTAND), dev = Suchanfrage aus der Entwicklungsumgebung
  (Messset), eigen = fuer das Suchtestset formuliert.
- nur_mit: Der Fall wird nur gemessen, wenn diese Aussagen im Bestand stehen. Fuer Faelle
  ohne Erwartung, die nur an einem Bestand etwas aussagen (Verneinung einer Aussage des
  Startbestands, fremde Themen neben ihr); am Seed zaehlen sie dann nicht.
- nur_ohne: Der Fall wird nur gemessen, wenn keine dieser Aussagen im Bestand steht. Fuer
  Faelle "fremd", deren Thema der Startbestand hat (der Wolf ist am Seed fremd, am
  Startbestand nicht).
- ersatz: Erwartung fuer einen Bestand, dem eine Aussage aus erwartet fehlt (Ersatz). Fuer
  Faelle zu den zwei Seed-Aussagen, die der Startbestand nicht hat (S06 bis S09): Dort
  passen die Antworten einer anderen Aussage; dieselbe_behauptung und phaenomen koennen
  dort anders sein.
  Fehlt auch eine Aussage aus ersatz, zaehlt der Fall nicht mit.

Keine echten Personen, keine Personendaten, keine Eingaben aus Produktion. Die erwarteten
Aussagen stammen aus dem Seed (Testbestand, S01 bis S42) und aus dem Startbestand (#288,
ab S43). Faelle, deren Aussagen im gemessenen Bestand fehlen, ueberspringt die Messung und
nennt sie: Am Seed zaehlen die Faelle zum Startbestand nicht mit. Die Faelle zu den zwei
Seed-Aussagen, die der Startbestand nicht hat, zaehlen dort mit ihrem Ersatz (#606).

Neue Faelle ans Ende ihres Abschnitts, IDs fortlaufend; eine ID wechselt nie den Text.
"""

from typing import NamedTuple, Optional, Tuple

from utils.text_normalisierung import text_normalisiert

FORMEN = ("stichwort", "satz")
QUELLEN = ("seed", "start", "dev", "eigen")
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


class Ersatz(NamedTuple):
    """Erwartung eines Falls fuer einen Bestand, dem eine Aussage aus erwartet fehlt."""

    erwartet: Tuple[str, ...]
    dieselbe_behauptung: bool
    phaenomen: Optional[str] = None  # None = wie im Fall


class Fall(NamedTuple):
    id: str
    anfrage: str
    form: str
    phaenomen: str
    erwartet: Tuple[str, ...]
    dieselbe_behauptung: bool
    quelle: str
    nur_mit: Tuple[str, ...] = ()
    nur_ohne: Tuple[str, ...] = ()
    ersatz: Optional[Ersatz] = None


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

SEED = (
    VOEGEL, UNZUVERLAESSIG, TEUER, ATOM, HEIZUNG, NEUBAU, VERBOT,
    FLEISCH, LAND, GENDERN, EU, EAUTO, TEMPO, VERBRENNER,
)  # fmt: skip

# Aussagen des Startbestands (#288), woertlich, soweit sie nicht schon oben stehen. Die
# uebrigen zwoelf Aussagen des Startbestands sind die des Seeds (ohne UNZUVERLAESSIG und
# TEUER); STARTBESTAND fuehrt alle 30.
DUNKELFLAUTE = (
    "Erneuerbare sind total unzuverlässig, bei Dunkelflaute gibt es keinen Strom."
)
CHINA = "Deutschland allein kann das Klima nicht retten, schau dir China an."
WOHLSTAND = "Klimaschutz kostet uns Wohlstand und Arbeitsplätze."
CO2PREIS = "Der CO2-Preis macht Heizen und Tanken für normale Leute unbezahlbar."
BALKON = "Balkonsolar lohnt sich nicht."
MIETER = "Die Energiewende bezahlen am Ende die Mieter."
TICKET = "Das Deutschlandticket ist zu teuer und nützt auf dem Dorf nichts."
LANDWIRTE = "Die Grünen behandeln Landwirte wie Kriminelle."
BIO = "Bio ist nur was für Reiche."
WOLF = "Der Wolf gehört nicht nach Deutschland."
INSEKTEN = "Am Insektensterben sind nicht die Pestizide schuld."
AKADEMIKER = "Die Grünen machen Politik nur für Akademiker in der Stadt."
RENTE = "Die Rente ist nicht mehr sicher, und ihr gebt das Geld fürs Klima aus."
BUERGERGELD = "Mit Bürgergeld lohnt sich Arbeiten nicht mehr."
FLUECHTLINGE = "Flüchtlinge wollen gar nicht arbeiten."
MIGRANTEN = "Migranten machen unsere Städte unsicher."
KLIMAKLEBER = "Klimakleber schaden dem Klimaschutz mehr, als sie nützen."
MEINUNG = "Man darf ja gar nichts mehr sagen."

STARTBESTAND = (
    VOEGEL, DUNKELFLAUTE, ATOM, CHINA, WOHLSTAND,
    HEIZUNG, NEUBAU, CO2PREIS, BALKON, MIETER,
    EAUTO, VERBRENNER, TEMPO, TICKET, LAND,
    FLEISCH, LANDWIRTE, BIO, WOLF, INSEKTEN,
    VERBOT, AKADEMIKER, RENTE, EU, BUERGERGELD,
    FLUECHTLINGE, MIGRANTEN, GENDERN, KLIMAKLEBER, MEINUNG,
)  # fmt: skip

KEINE: Tuple[str, ...] = ()

# fmt: off
FAELLE = tuple(Fall(*f) for f in (
    # Energie und Klima
    ("S01", "Windräder töten die Vögel", "satz", "woertlich", (VOEGEL,), True, "seed"),
    ("S02", "Windkraftanlagen bringen massenhaft Vögel um", "satz", "umformulierung", (VOEGEL,), True, "eigen"),
    ("S03", "windrad vögel", "stichwort", "schlagwort", (VOEGEL,), False, "eigen"),
    ("S04", "Windräder töten die Vögle", "satz", "tippfehler", (VOEGEL,), True, "eigen"),
    ("S05", "Windräder schützen Vögel", "satz", "verneinung", KEINE, False, "eigen"),
    # S06 bis S09: Der Startbestand hat UNZUVERLAESSIG und TEUER nicht; dort passen die
    # Antworten zu DUNKELFLAUTE bzw. die zu ATOM (Kosten: Sonne und Wind guenstiger als
    # neue Atomkraftwerke). "Ökostrom ist zu teuer" ist eine andere Behauptung als ATOM.
    ("S06", "Erneuerbare sind unzuverläsig", "satz", "tippfehler", (UNZUVERLAESSIG,), True, "eigen", KEINE, KEINE, Ersatz((DUNKELFLAUTE,), True)),
    ("S07", "Dunkelflaute", "stichwort", "schlagwort", (UNZUVERLAESSIG,), False, "eigen", KEINE, KEINE, Ersatz((DUNKELFLAUTE,), False)),
    ("S08", "Wenn kein Wind weht und keine Sonne scheint, gibt es keinen Strom", "satz", "verwandt", (UNZUVERLAESSIG,), False, "eigen", KEINE, KEINE, Ersatz((DUNKELFLAUTE,), False)),
    ("S09", "Ökostrom ist viel zu teuer", "satz", "umformulierung", (TEUER,), True, "eigen", KEINE, KEINE, Ersatz((ATOM,), False, "verwandt")),
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
    # Themen ohne Aussage im Testbestand; Wolf, Rente und Deutschlandticket hat der
    # Startbestand (nur_ohne), dort zaehlen S76 ff.
    ("S38", "Der Wolf gehört nicht nach Deutschland", "satz", "fremd", KEINE, False, "eigen", KEINE, (WOLF,)),
    ("S39", "Die Rente ist nicht mehr sicher", "satz", "fremd", KEINE, False, "eigen", KEINE, (RENTE,)),
    ("S40", "Mülltrennung bringt nichts, am Ende wird eh alles verbrannt", "satz", "fremd", KEINE, False, "eigen"),
    ("S41", "Radwege", "stichwort", "fremd", KEINE, False, "eigen"),
    ("S42", "Das Deutschlandticket ist zu teuer", "satz", "fremd", KEINE, False, "eigen", KEINE, (TICKET,)),
    # Startbestand (#288): Klima und Energie
    ("S43", "Erneuerbare sind total unzuverlässig, bei Dunkelflaute gibt es keinen Strom", "satz", "woertlich", (DUNKELFLAUTE,), True, "start"),
    ("S44", "Dunkelflaute Blackout", "stichwort", "schlagwort", (DUNKELFLAUTE,), False, "eigen"),
    ("S45", "Erneurbare sind unzuverlässig, bei Flaute gibts keinen Strom", "satz", "tippfehler", (DUNKELFLAUTE,), True, "eigen"),
    ("S46", "Wenn kein Wind weht und die Sonne nicht scheint, gehen bei uns die Lichter aus", "satz", "umgangssprache", (DUNKELFLAUTE,), True, "eigen"),
    ("S47", "Deutschland allein kann das Klima nicht retten, schau dir China an", "satz", "woertlich", (CHINA,), True, "start"),
    ("S48", "Deutschland kann die Welt nicht alleine retten, China stößt viel mehr aus", "satz", "umformulierung", (CHINA,), True, "eigen"),
    ("S49", "China CO2", "stichwort", "schlagwort", (CHINA,), False, "eigen"),
    ("S50", "Was bringt unser Klimaschutz, wenn China jede Woche ein Kohlekraftwerk baut", "satz", "verwandt", (CHINA,), False, "eigen"),
    ("S51", "Klimaschutz kostet uns unseren Wohlstand und unsere Jobs", "satz", "umformulierung", (WOHLSTAND,), True, "eigen"),
    ("S52", "Klimaschutz vernichtet Arbeitsplätze", "satz", "verwandt", (WOHLSTAND,), False, "eigen"),
    ("S53", "Klimaschutz Wirtschaft Jobs", "stichwort", "schlagwort", (WOHLSTAND,), False, "eigen"),
    # Startbestand: Wohnen und Heizen
    ("S54", "Der CO2-Preis macht Heizen und Tanken für normale Leute unbezahlbar", "satz", "woertlich", (CO2PREIS,), True, "start"),
    ("S55", "Wegen dem CO2 Preis kann sich keiner mehr Sprit und Heizöl leisten", "satz", "umgangssprache", (CO2PREIS,), True, "eigen"),
    ("S56", "CO2-Steuer", "stichwort", "schlagwort", (CO2PREIS,), False, "eigen"),
    ("S57", "Wird Tanken durch den CO2-Preis noch teurer?", "satz", "frage", (CO2PREIS,), False, "eigen"),
    ("S58", "Ein Balkonkraftwerk lohnt sich nicht", "satz", "umformulierung", (BALKON,), True, "eigen"),
    ("S59", "Balkonkraftwerk", "stichwort", "schlagwort", (BALKON,), False, "eigen"),
    ("S60", "Lohnt sich ein Balkonkraftwerk?", "satz", "frage", (BALKON,), False, "eigen"),
    ("S61", "Balkonsolar lont sich nich", "satz", "tippfehler", (BALKON,), True, "eigen"),
    ("S62", "Balkonsolar lohnt sich", "satz", "verneinung", KEINE, False, "eigen", (BALKON,)),
    ("S63", "Die Mieter zahlen am Ende die Energiewende", "satz", "umformulierung", (MIETER,), True, "eigen"),
    ("S64", "Heizungstausch Mieterhöhung", "stichwort", "schlagwort", (MIETER,), False, "eigen"),
    ("S65", "Die Sanierung zahlen dann wieder wir Mieter mit höherer Miete", "satz", "verwandt", (MIETER,), False, "eigen"),
    ("S66", "Die Mietpreisbremse funktioniert nicht", "satz", "fremd", KEINE, False, "eigen", (MIETER,)),
    # Startbestand: Verkehr und Land
    ("S67", "Das Deutschlandticket ist zu teuer und nützt auf dem Dorf nichts", "satz", "woertlich", (TICKET,), True, "start"),
    ("S68", "Deutschlandticket Dorf", "stichwort", "schlagwort", (TICKET,), False, "eigen"),
    ("S69", "Was soll ich mit dem Deutschlandticket, bei uns fährt eh kein Bus", "satz", "umgangssprache", (TICKET,), False, "eigen"),
    ("S70", "Die Bahn ist immer zu spät", "satz", "fremd", KEINE, False, "eigen", (TICKET,)),
    ("S71", "Die Grünen machen nur Politik für Studierte aus der Stadt", "satz", "umformulierung", (AKADEMIKER, LAND), True, "eigen"),
    ("S72", "Akademikerpartei", "stichwort", "schlagwort", (AKADEMIKER,), False, "eigen"),
    ("S73", "Grün wählen doch nur Lehrer und Studenten", "satz", "umgangssprache", (AKADEMIKER,), False, "eigen"),
    # Startbestand: Landwirtschaft und Ernährung
    ("S74", "Die Grünen behandeln Bauern wie Verbrecher", "satz", "umformulierung", (LANDWIRTE,), True, "eigen"),
    ("S75", "Bauernproteste", "stichwort", "schlagwort", (LANDWIRTE,), False, "eigen"),
    ("S76", "Wölfe haben in Deutschland nichts verloren", "satz", "umformulierung", (WOLF,), True, "eigen"),
    ("S77", "Wolf Weidetiere", "stichwort", "schlagwort", (WOLF,), False, "eigen"),
    ("S78", "Der Wolf reißt unsere Schafe, der muss weg", "satz", "umgangssprache", (WOLF,), False, "eigen"),
    ("S79", "Bio ist nur was für Reiche", "satz", "woertlich", (BIO,), True, "start"),
    ("S80", "Bio können sich nur Reiche leisten", "satz", "umformulierung", (BIO,), True, "eigen"),
    ("S81", "Bio zu teuer", "stichwort", "schlagwort", (BIO,), False, "eigen"),
    ("S82", "Bio ist für alle bezahlbar", "satz", "verneinung", KEINE, False, "eigen", (BIO,)),
    ("S83", "Am Insektensterben sind nicht die Pestizide schuld", "satz", "woertlich", (INSEKTEN,), True, "start"),
    ("S84", "Insektensterben Glyphosat", "stichwort", "schlagwort", (INSEKTEN,), False, "eigen"),
    ("S85", "Die Bienen sterben wegen der Varroamilbe, nicht wegen Pflanzenschutzmitteln", "satz", "verwandt", (INSEKTEN,), False, "eigen"),
    ("S86", "Pestizide sind schuld am Insektensterben", "satz", "verneinung", KEINE, False, "eigen", (INSEKTEN,)),
    # Startbestand: Soziales, Wirtschaft, Staat
    ("S87", "Für die Rente ist kein Geld da, aber fürs Klima schon", "satz", "umformulierung", (RENTE,), True, "eigen"),
    ("S88", "Rente Klimaschutz", "stichwort", "schlagwort", (RENTE,), False, "eigen"),
    ("S89", "Die Schuldenbremse muss bleiben", "satz", "fremd", KEINE, False, "eigen", (RENTE,)),
    ("S90", "Mit Bürgergeld lohnt sich Arbeiten nicht mehr", "satz", "woertlich", (BUERGERGELD,), True, "start"),
    ("S91", "Wer arbeitet, ist der Dumme, das Bürgergeld gibts fürs Nichtstun", "satz", "umgangssprache", (BUERGERGELD,), True, "eigen"),
    ("S92", "Bürgergeld", "stichwort", "schlagwort", (BUERGERGELD,), False, "eigen"),
    ("S93", "Mit Bürgergled lohnt sich Arbeit nicht mehr", "satz", "tippfehler", (BUERGERGELD,), True, "eigen"),
    # Startbestand: Gesellschaft und Migration
    ("S94", "Flüchtlinge haben keinen Bock zu arbeiten", "satz", "umgangssprache", (FLUECHTLINGE,), True, "eigen"),
    ("S95", "Geflüchtete Arbeit", "stichwort", "schlagwort", (FLUECHTLINGE,), False, "eigen"),
    ("S96", "Flüchtlinge wollen arbeiten, dürfen aber oft nicht", "satz", "verneinung", KEINE, False, "eigen", (FLUECHTLINGE,)),
    ("S97", "Ausländer machen unsere Städte unsicher", "satz", "umformulierung", (MIGRANTEN,), True, "eigen"),
    ("S98", "Migration Kriminalität", "stichwort", "schlagwort", (MIGRANTEN,), False, "eigen"),
    ("S99", "Seit so viele Flüchtlinge da sind, traut man sich abends nicht mehr raus", "satz", "verwandt", (MIGRANTEN,), False, "eigen"),
    ("S100", "Klimakleber schaden dem Klimaschutz mehr, als sie nützen", "satz", "woertlich", (KLIMAKLEBER,), True, "start"),
    ("S101", "Klimakleber", "stichwort", "schlagwort", (KLIMAKLEBER,), False, "eigen"),
    ("S102", "Die Klebeaktionen der Letzten Generation schaden dem Klimaschutz nur", "satz", "umformulierung", (KLIMAKLEBER,), True, "eigen"),
    ("S103", "Man darf ja gar nichts mehr sagen", "satz", "woertlich", (MEINUNG,), True, "start"),
    ("S104", "In diesem Land darf man seine Meinung nicht mehr sagen", "satz", "umformulierung", (MEINUNG,), True, "eigen"),
    ("S105", "Meinungsfreiheit", "stichwort", "schlagwort", (MEINUNG,), False, "eigen"),
    ("S106", "Cancel Culture", "stichwort", "umgangssprache", (MEINUNG,), False, "eigen"),
))
# fmt: on


def am_seed_gemessen(fall: Fall) -> bool:
    """
    Zaehlt der Fall am Seed mit (wie gemessen() in suche_messen.py)? Die Faelle zum
    Startbestand nicht: So bleibt das Soll des naechtlichen Laufs, der am Seed misst.
    """
    seed = {text_normalisiert(t) for t in SEED}
    benoetigt = {text_normalisiert(t) for t in fall.erwartet + fall.nur_mit}
    return benoetigt <= seed and not seed & {
        text_normalisiert(t) for t in fall.nur_ohne
    }
