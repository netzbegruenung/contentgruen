"""
Messset Aehnlichkeit: Paare mit Kategorie und den gemessenen Scores fuer
intfloat/multilingual-e5-base (Aussagen 2026-09-17, mit neuen Texten nachgemessen
2026-10-28).

Kategorien: A identisch; B trivial abweichend (Gross/klein, Punkt/Ausrufezeichen,
Leerraum, Anfuehrungszeichen); C gleiche Behauptung, andere Worte; D verwandt, aber andere
Behauptung; E fremdes Thema. art: aussage (Formular/Seeding), suche (Suchanfragen),
kommentar. Quelle: seed = mvp/data/seed/v1.0 (Kommentare aus dem bereinigten Stand nach
#340, Aussagen zum Teil aus dem Stand davor), eigen = fuer die Messung formuliert.
Keine echten Personen, keine erfundenen Erlebnisse - es gelten die Regeln des Seeds
(mvp/data/seed/README.md).

qq = query/query (Aussagen, Suchanfragen), pp = passage/passage (Kommentare),
qp = query gegen passage (frueherer Kommentarvergleich). gleich = Entscheidung der
Dublettenpruefung mit den Schwellen aus core/config.py.
"""

# fmt: off
# Aussage, die mehrfach vorkommt
VERBOT = "Die Grünen sind eine Verbotspartei"
# Kommentare aus dem bereinigten Seed (mvp/data/seed/v1.0), die mehrfach vorkommen
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

# (id, art, kategorie, kandidat, bestand, quelle, qq, pp, qp, gleich)
PAARE = [
    ("A01", "aussage", "A", 'Die Grünen sind eine Verbotspartei!', 'Die Grünen sind eine Verbotspartei!', "seed", 1.0000, 1.0000, 0.9333, True),
    ("A02", "aussage", "A", 'Windräder sind Vogel-Schredder!', 'Windräder sind Vogel-Schredder!', "seed", 1.0000, 1.0000, 0.9511, True),
    ("A03", "aussage", "A", 'Balkonsolar lohnt sich nie', 'Balkonsolar lohnt sich nie', "eigen", 1.0000, 1.0000, 0.9284, True),
    ("A04", "aussage", "A", 'Die Grünen wollen mir meine Heizung verbieten!', 'Die Grünen wollen mir meine Heizung verbieten!', "seed", 1.0000, 1.0000, 0.9368, True),
    ("A05", "aussage", "A", 'Grüne wollen das Auto verbieten', 'Grüne wollen das Auto verbieten', "eigen", 1.0000, 1.0000, 0.9069, True),
    ("A06", "aussage", "A", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Tempolimit bringt doch eh nichts fürs Klima!', "seed", 1.0000, 1.0000, 0.9267, True),
    ("B01", "aussage", "B", VERBOT, 'Die Grünen sind eine Verbotspartei!', "seed", 0.9886, 0.9830, 0.9146, True),
    ("B02", "aussage", "B", 'Deutschland kann das Klima nicht alleine retten', 'Deutschland kann das Klima nicht alleine retten!', "seed", 0.9849, 0.9851, 0.9116, True),
    ("B03", "aussage", "B", 'windräder sind vogel-schredder', 'Windräder sind Vogel-Schredder!', "seed+eigen", 0.9578, 0.9637, 0.9134, True),
    ("B04", "aussage", "B", '„Balkonsolar lohnt sich nie“', 'Balkonsolar lohnt sich nie', "eigen", 0.9272, 0.9359, 0.8720, True),
    ("B05", "aussage", "B", 'Die  Grünen lassen alle Migranten rein. ', 'Die Grünen lassen alle Migranten rein', "seed+eigen", 0.9880, 0.9851, 0.9395, True),
    ("B06", "aussage", "B", 'E-AUTOS SIND EINE TOTGEBURT!!!', 'E-Autos sind eine Totgeburt!', "seed+eigen", 0.9024, 0.9173, 0.8797, True),
    ("B07", "aussage", "B", '"Die Grünen wollen mir meine Heizung verbieten"', 'Die Grünen wollen mir meine Heizung verbieten!', "seed+eigen", 0.9796, 0.9622, 0.9255, True),
    ("B08", "aussage", "B", "Das geht's so nicht, Tempolimit ist Unsinn", 'Das geht’s so nicht, Tempolimit ist Unsinn', "eigen", 0.9980, 0.9952, 0.9265, True),
    # Frage statt Behauptung: seit die Normalisierung das Fragezeichen stehen laesst,
    # keine triviale Abweichung mehr, sondern ein eigener Satz (Kategorie D).
    ("B09", "aussage", "D", 'Wärmepumpen funktionieren nur im Neubau?', 'Wärmepumpen funktionieren nur im Neubau!', "seed+eigen", 0.9719, 0.9555, 0.9116, False),
    ("B10", "aussage", "B", 'grüne wollen das auto verbieten.', 'Grüne wollen das Auto verbieten', "eigen", 0.9622, 0.9739, 0.9185, True),
    ("C01", "aussage", "C", 'E-Autos sind auch nicht besser für die Umwelt', 'Elektroautos sind gar nicht umweltfreundlich!', "seed", 0.9497, 0.9567, 0.8947, False),
    ("C02", "aussage", "C", 'Deutschland kann das Klima nicht alleine retten', 'Deutschland kann nicht alleine das Klima retten!', "seed", 0.9799, 0.9819, 0.9078, False),
    ("C03", "aussage", "C", VERBOT, 'Die Grünen wollen immer alles verbieten', "eigen", 0.9422, 0.9315, 0.8594, False),
    ("C04", "aussage", "C", 'Windräder sind Vogel-Schredder!', 'Windkraftanlagen töten massenhaft Vögel', "eigen", 0.9100, 0.9169, 0.8673, False),
    ("C05", "aussage", "C", 'Balkonsolar lohnt sich nie', 'Balkonkraftwerke rechnen sich nicht', "eigen", 0.9170, 0.9437, 0.8734, False),
    ("C06", "aussage", "C", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Ein Tempolimit hilft dem Klima überhaupt nicht', "eigen", 0.9628, 0.9584, 0.9051, False),
    ("C07", "aussage", "C", 'Die Grünen interessieren sich nur für Großstädte, das Land ist ihnen egal!', 'Den Grünen ist der ländliche Raum egal', "eigen", 0.9068, 0.8386, 0.8923, False),
    ("C08", "aussage", "C", 'Die Grünen wollen mir meine Heizung verbieten!', 'Die Grünen wollen uns die Gasheizung wegnehmen', "eigen", 0.9578, 0.9576, 0.8972, False),
    ("C09", "aussage", "C", 'Die Grünen lassen alle Migranten rein', 'Die Grünen wollen die Grenzen für alle öffnen', "eigen", 0.9405, 0.9527, 0.8897, False),
    ("C10", "aussage", "C", 'Wärmepumpen funktionieren nur im Neubau!', 'Im Altbau taugen Wärmepumpen nichts', "eigen", 0.9284, 0.9207, 0.8793, False),
    ("C11", "aussage", "C", 'Erneuerbare Energien sind total unzuverlässig!', 'Wind und Sonne liefern keinen verlässlichen Strom', "eigen", 0.8866, 0.9030, 0.8550, False),
    ("C12", "aussage", "C", 'Die Grünen wollen uns das Fleisch verbieten', 'Die Grünen wollen uns das Schnitzel wegnehmen', "eigen", 0.9480, 0.9641, 0.8954, False),
    ("C13", "aussage", "C", 'Wärmepumpen funktionieren nur im Neubau!', 'Wärmepumpen funktionieren nicht im Altbau!', "seed", 0.9608, 0.9550, 0.9110, False),
    ("D01", "aussage", "D", 'Balkonsolar lohnt sich nie', 'Balkonkraftwerke sind nur Spielerei', "eigen", 0.8908, 0.8933, 0.8560, False),
    ("D02", "aussage", "D", 'Grüne wollen das Auto verbieten', 'Grüne wollen nur Großstädter bedienen', "eigen", 0.8926, 0.9041, 0.8358, False),
    ("D03", "aussage", "D", 'Erneuerbare Energien sind zu teuer!', 'Erneuerbare Energien sind total unzuverlässig!', "seed", 0.9574, 0.9474, 0.9060, False),
    ("D04", "aussage", "D", 'Die Grünen zerstören die Wirtschaft!', 'Die Grünen zerstören unsere Landwirtschaft!', "seed", 0.9672, 0.9677, 0.9228, False),
    ("D05", "aussage", "D", 'E-Autos sind eine Totgeburt!', 'E-Autos sind auch nicht besser für die Umwelt', "seed", 0.9172, 0.9099, 0.8619, False),
    ("D06", "aussage", "D", 'Die Grünen wollen uns das Gendern aufzwingen', 'Dieser ganze Gender-Wahnsinn muss aufhören!', "seed", 0.8954, 0.8711, 0.8544, False),
    ("D07", "aussage", "D", VERBOT, 'Die Grünen wollen uns das Fleisch verbieten', "seed", 0.9145, 0.9259, 0.8542, False),
    ("D08", "aussage", "D", 'Die Grünen wollen mir meine Heizung verbieten!', 'Die Grünen haben keine Ahnung von Wirtschaft!', "seed+eigen", 0.9038, 0.9151, 0.8523, False),
    ("D09", "aussage", "D", 'Wärmepumpen funktionieren nur im Neubau!', 'Wärmepumpen sind viel zu teuer', "eigen", 0.9160, 0.8985, 0.8548, False),
    ("D10", "aussage", "D", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Tempolimit kostet Autofahrer nur Zeit', "eigen", 0.9147, 0.9003, 0.8458, False),
    ("D11", "aussage", "D", VERBOT, 'Die Grünen sind keine Verbotspartei', "eigen", 0.9691, 0.9575, 0.8843, False),
    ("D12", "aussage", "D", 'Windräder sind Vogel-Schredder!', 'Windräder verschandeln die Landschaft', "eigen", 0.9170, 0.9076, 0.8717, False),
    ("D13", "aussage", "D", 'Die Grünen verstehen nichts vom Leben normaler Leute', 'Die Grünen interessieren sich nur für Großstädte, das Land ist ihnen egal!', "seed", 0.9021, 0.9294, 0.8554, False),
    ("D14", "aussage", "D", 'Grüne sind Kriegstreiber', 'Die Grünen kümmern sich nicht um unsere Sicherheit!', "seed", 0.9117, 0.9155, 0.8505, False),
    ("D15", "aussage", "D", 'Balkonsolar lohnt sich nie', 'Balkonsolar lohnt sich immer', "eigen", 0.9501, 0.9227, 0.8856, False),
    ("D16", "aussage", "D", 'Die Grünen zerstören die Wirtschaft!', 'Die Energiewende zerstört Arbeitsplätze!', "seed", 0.9236, 0.9278, 0.8806, False),
    ("E01", "aussage", "E", 'Balkonsolar lohnt sich nie', 'Die Grünen lassen alle Migranten rein', "seed+eigen", 0.7887, 0.8107, 0.7633, False),
    ("E02", "aussage", "E", 'Windräder sind Vogel-Schredder!', 'Dieser ganze Gender-Wahnsinn muss aufhören!', "seed", 0.8260, 0.8373, 0.7952, False),
    ("E03", "aussage", "E", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Die EU ist ein bürokratisches Monster, das uns nur schadet!', "seed", 0.8519, 0.8443, 0.8232, False),
    ("E04", "aussage", "E", 'Grüne sind Kriegstreiber', 'Wärmepumpen funktionieren nur im Neubau!', "seed", 0.7999, 0.8494, 0.7693, False),
    ("E05", "aussage", "E", 'Die Grünen wollen mir meine Heizung verbieten!', 'Blühwiese statt Rasen vor dem Rathaus', "seed+dev", 0.7978, 0.7842, 0.8034, False),
    ("E06", "aussage", "E", 'Die Grünen wollen uns das Fleisch verbieten', 'Deutschland kann das Klima nicht alleine retten', "seed", 0.8365, 0.8738, 0.7996, False),
    ("E07", "aussage", "E", 'E-Autos sind eine Totgeburt!', 'Die Grünen lassen alle Migranten rein', "seed", 0.7994, 0.8214, 0.7736, False),
    ("E08", "aussage", "E", 'Klimaschutz', VERBOT, "dev+seed", 0.8370, 0.8395, 0.7947, False),
    ("S01", "suche", "B", 'klimaschutz', 'Klimaschutz', "dev", 0.9795, 0.9460, 0.8949, True),
    ("S02", "suche", "B", 'Wärmepumpe Altbau', 'wärmepumpe altbau', "eigen", 0.9794, 0.9572, 0.9173, True),
    ("S03", "suche", "C", 'Wärmepumpe Altbau', 'Wärmepumpen im Altbau', "eigen", 0.9871, 0.9812, 0.9206, True),
    ("S04", "suche", "D", 'Tempolimit', 'Tempolimit Unfälle', "eigen", 0.8885, 0.9365, 0.8598, False),
    ("S05", "suche", "D", 'energiewende', 'Energiewende Kosten', "dev+eigen", 0.9353, 0.9591, 0.8875, False),
    ("S06", "suche", "D", 'Balkonkraftwerk', 'Balkonkraftwerk Mietwohnung erlaubt', "eigen", 0.9163, 0.9233, 0.8836, False),
    ("S07", "suche", "E", 'Tempolimit', 'Wärmepumpe Altbau', "eigen", 0.7460, 0.8441, 0.7596, False),
    ("KA1", "kommentar", "A", REGELN, REGELN, "seed", 1.0000, 1.0000, 0.9405, True),
    ("KA2", "kommentar", "A", GLAS, GLAS, "seed", 1.0000, 1.0000, 0.9547, True),
    ("KB1", "kommentar", "B", REGELN.removesuffix("."), REGELN, "seed+eigen", 0.9978, 0.9960, 0.9382, True),
    ("KB2", "kommentar", "B", GLAS.replace(" Die ", "  \nDie ").replace(" Wer ", "  \nWer "), GLAS, "seed+eigen", 1.0000, 1.0000, 0.9547, True),
    ("KB3", "kommentar", "B", ALTBAU.removesuffix(".") + "!", ALTBAU, "seed+eigen", 0.9977, 0.9990, 0.9530, True),
    ("KB4", "kommentar", "B", WIND_SONNE.lower(), WIND_SONNE, "seed+eigen", 0.9722, 0.9548, 0.9087, True),
    ("KC1", "kommentar", "C", GLAS_EIGENE_WORTE, GLAS, "eigen", 0.9791, 0.9712, 0.9260, False),
    ("KC2", "kommentar", "C", 'Freiheit wollen wir alle. Viele Regeln schützen sie sogar: der Sicherheitsgurt, der Nichtraucherschutz in Gaststätten, sauberes Leitungswasser. Entscheidend ist, wem eine Regel nützt.', REGELN, "eigen", 0.9570, 0.9638, 0.9113, False),
    ("KC3", "kommentar", "C", 'Niemand soll sich fürs Heizen verschulden. Geht eine Heizung kaputt, darf man sie reparieren lassen. Die Vorgaben zu erneuerbarer Wärme betreffen nur Heizungen, die neu eingebaut werden.', REPARATUR, "eigen", 0.9722, 0.9719, 0.9173, False),
    ("KC4", "kommentar", "C", GLAS + GLAS_ZUSATZ, GLAS, "seed+eigen", 0.9964, 0.9980, 0.9487, True),
    ("KD1", "kommentar", "D", GLAS, STANDORT, "seed", 0.8562, 0.8172, 0.8102, False),
    ("KD2", "kommentar", "D", REGELN, WIND_SONNE, "seed", 0.8773, 0.8889, 0.8251, False),
    ("KD3", "kommentar", "D", REPARATUR, BERATUNG, "seed", 0.8812, 0.8794, 0.8331, False),
    ("KD4", "kommentar", "D", BERATUNG, ALTBAU, "seed", 0.8696, 0.8593, 0.8352, False),
    ("KD5", "kommentar", "D", TELLER, HOF, "seed", 0.9043, 0.8989, 0.8525, False),
    ("KE1", "kommentar", "E", REGELN, GLAS, "seed", 0.8156, 0.7887, 0.7653, False),
    ("KE2", "kommentar", "E", EU_ALLTAG, TEMPOLIMIT, "seed", 0.8359, 0.7996, 0.7699, False),
]
# fmt: on
