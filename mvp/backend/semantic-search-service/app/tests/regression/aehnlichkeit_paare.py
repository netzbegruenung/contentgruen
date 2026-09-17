"""
Messset Aehnlichkeit: Paare mit Kategorie und den gemessenen Scores fuer
intfloat/multilingual-e5-base (2026-09-17).

Kategorien: A identisch; B trivial abweichend (Gross/klein, Satzzeichen, Leerraum,
Anfuehrungszeichen); C gleiche Behauptung, andere Worte; D verwandt, aber andere
Behauptung; E fremdes Thema. art: aussage (Formular/Seeding), suche (Suchanfragen),
kommentar. Quelle: seed = mvp/data/seed/v1.0, eigen = fuer die Messung formuliert.

qq = query/query (Aussagen, Suchanfragen), pp = passage/passage (Kommentare),
qp = query gegen passage (frueherer Kommentarvergleich). gleich = Entscheidung der
Dublettenpruefung mit den Schwellen aus core/config.py.
"""

# fmt: off
# Seed-Texte, die mehrfach vorkommen
VERBOT = "Die Grünen sind eine Verbotspartei"
NACHBAR = "Verstehe die Sorge total! Ging mir früher auch so. Dann hab ich gemerkt: Mein Balkonkraftwerk war verboten - jetzt erlaubt. Meine Monatskarte kostete 180€ - jetzt 49€. In unserer Straße haben schon 5 Leute Solaranlagen. Fühlt sich eher nach mehr Freiheit an, oder?"
FAKTEN = "Die CSU hat Gendern verboten. Die CDU hat Glühbirnen verboten. Söder wollte Ponys auf der Wiesn verbieten. Wir haben Solaranlagen auf Balkonen ERLAUBT. Merkste selbst, oder?"
SKEPTIKER = "Mein Schwager war auch skeptisch. Jetzt spart er 1.500€ im Jahr durchs 49€-Ticket und seine Solaranlage hat sich nach 5 Jahren amortisiert. Er sagt selbst: 'Hätte ich mal früher drauf gehört.' Manchmal sind Veränderungen echt eine Chance!"
FREIHEIT = "Kenne ich, das mit den Verboten nervt mich auch manchmal! Aber mal ehrlich: Ich freu mich, dass ich im Restaurant nicht mehr vollgequalmt werde. Und mein Nachbar spart mit seiner Wärmepumpe 800€ im Jahr - das ist doch eher ein Freiheitsgewinn, oder?"
NACHBARS_UEB = "Bei uns in der Straße hat letztens einer gemeint: 'Die Grünen verbieten mir alles!' Dann kam raus: Er kriegt 9.000€ Förderung für seine neue Heizung und sein E-Auto kann er günstiger laden als tanken. Verbote sehen anders aus, oder? 😄"
INNOVATION = "Deutschland ist Innovationsland - nicht Verbotsland. Wir haben das erste Auto erfunden, warum nicht auch die besten E-Autos bauen? 70% der Deutschen wollen mehr Klimaschutz. Das ist keine Verbotspolitik, sondern Zukunftssicherung."
KATZEN = "Verstehe die Sorge um die Vögel total - mag Tiere auch! Aber wusstest du: Meine Katze ist statistisch gefährlicher. Hauskatzen töten 100 Millionen Vögel im Jahr, Windräder unter 100.000. Sogar der NABU befürwortet Windkraft, wenn richtig geplant. Die kennen sich mit Vogelschutz aus, oder?"
DORF = "Bei uns im Dorf war das auch großes Thema! Dann hat der Förster erklärt: Durch den Klimawandel sterben hier ganze Vogelpopulationen aus - Dürre, keine Insekten mehr. Die 3 Windräder am Waldrand? Da ist in 5 Jahren kein toter Vogel gefunden worden. Jetzt sind die meisten überzeugt."
TECHNIK = "Moderne Windräder haben Radar-Systeme und schalten bei Vogelschwärmen ab. Frankreich testet sogar schwarze Rotorblätter - reduziert Kollisionen um 70%. Währenddessen: Kohlekraft macht Wälder sauer, Quecksilber vergiftet Fische. Was ist schlimmer für Vögel?"
VOGELLIEBE = "Lustiger Fakt: Die gleichen Leute, die bei Windrädern plötzlich Vogelschützer werden, hatten noch nie ein Problem mit ihrer Katze, ihrem SUV oder ihrer Glasfassade. Aber klar, beim Klimaschutz entdeckt man plötzlich sein Herz für Vögel... 🙄"

# (id, art, kategorie, kandidat, bestand, quelle, qq, pp, qp, gleich)
PAARE = [
    ("A01", "aussage", "A", 'Die Grünen sind eine Verbotspartei!', 'Die Grünen sind eine Verbotspartei!', "seed", 1.0000, 1.0000, 0.9333, True),
    ("A02", "aussage", "A", 'Windräder sind Vogel-Schredder!', 'Windräder sind Vogel-Schredder!', "seed", 1.0000, 1.0000, 0.9511, True),
    ("A03", "aussage", "A", 'Balkonsolar lohnt sich nie', 'Balkonsolar lohnt sich nie', "eigen", 1.0000, 1.0000, 0.9284, True),
    ("A04", "aussage", "A", 'Habeck will mir meine Heizung verbieten', 'Habeck will mir meine Heizung verbieten', "seed", 1.0000, 1.0000, 0.9312, True),
    ("A05", "aussage", "A", 'Grüne wollen das Auto verbieten', 'Grüne wollen das Auto verbieten', "eigen", 1.0000, 1.0000, 0.9069, True),
    ("A06", "aussage", "A", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Tempolimit bringt doch eh nichts fürs Klima!', "seed", 1.0000, 1.0000, 0.9267, True),
    ("B01", "aussage", "B", VERBOT, 'Die Grünen sind eine Verbotspartei!', "seed", 0.9886, 0.9830, 0.9146, True),
    ("B02", "aussage", "B", 'Deutschland kann das Klima nicht alleine retten', 'Deutschland kann das Klima nicht alleine retten!', "seed", 0.9849, 0.9851, 0.9116, True),
    ("B03", "aussage", "B", 'windräder sind vogel-schredder', 'Windräder sind Vogel-Schredder!', "seed+eigen", 0.9578, 0.9637, 0.9134, True),
    ("B04", "aussage", "B", '„Balkonsolar lohnt sich nie“', 'Balkonsolar lohnt sich nie', "eigen", 0.9272, 0.9359, 0.8720, True),
    ("B05", "aussage", "B", 'Die  Grünen lassen alle Migranten rein. ', 'Die Grünen lassen alle Migranten rein', "seed+eigen", 0.9880, 0.9851, 0.9395, True),
    ("B06", "aussage", "B", 'E-AUTOS SIND EINE TOTGEBURT!!!', 'E-Autos sind eine Totgeburt!', "seed+eigen", 0.9024, 0.9173, 0.8797, True),
    ("B07", "aussage", "B", '"Habeck will mir meine Heizung verbieten"', 'Habeck will mir meine Heizung verbieten', "seed+eigen", 0.9871, 0.9825, 0.9312, True),
    ("B08", "aussage", "B", "Das geht's so nicht, Tempolimit ist Unsinn", 'Das geht’s so nicht, Tempolimit ist Unsinn', "eigen", 0.9980, 0.9952, 0.9265, True),
    ("B09", "aussage", "B", 'Wärmepumpen funktionieren nur im Neubau?', 'Wärmepumpen funktionieren nur im Neubau!', "seed+eigen", 0.9719, 0.9555, 0.9116, True),
    ("B10", "aussage", "B", 'grüne wollen das auto verbieten.', 'Grüne wollen das Auto verbieten', "eigen", 0.9622, 0.9739, 0.9185, True),
    ("C01", "aussage", "C", 'E-Autos sind auch nicht besser für die Umwelt', 'Elektroautos sind gar nicht umweltfreundlich!', "seed", 0.9497, 0.9567, 0.8947, False),
    ("C02", "aussage", "C", 'Deutschland kann das Klima nicht alleine retten', 'Deutschland kann nicht alleine das Klima retten!', "seed", 0.9799, 0.9819, 0.9078, False),
    ("C03", "aussage", "C", VERBOT, 'Die Grünen wollen immer alles verbieten', "eigen", 0.9422, 0.9315, 0.8594, False),
    ("C04", "aussage", "C", 'Windräder sind Vogel-Schredder!', 'Windkraftanlagen töten massenhaft Vögel', "eigen", 0.9100, 0.9169, 0.8673, False),
    ("C05", "aussage", "C", 'Balkonsolar lohnt sich nie', 'Balkonkraftwerke rechnen sich nicht', "eigen", 0.9170, 0.9437, 0.8734, False),
    ("C06", "aussage", "C", 'Tempolimit bringt doch eh nichts fürs Klima!', 'Ein Tempolimit hilft dem Klima überhaupt nicht', "eigen", 0.9628, 0.9584, 0.9051, False),
    ("C07", "aussage", "C", 'Die Grünen interessieren sich nur für Großstädte, das Land ist ihnen egal!', 'Den Grünen ist der ländliche Raum egal', "eigen", 0.9068, 0.8386, 0.8923, False),
    ("C08", "aussage", "C", 'Habeck will mir meine Heizung verbieten', 'Habeck will uns die Gasheizung wegnehmen', "eigen", 0.9604, 0.9598, 0.8982, False),
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
    ("D08", "aussage", "D", 'Habeck will mir meine Heizung verbieten', 'Habeck hat keine Ahnung von Wirtschaft!', "seed", 0.8954, 0.8882, 0.8440, False),
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
    ("E05", "aussage", "E", 'Habeck will mir meine Heizung verbieten', 'Blühwiese statt Rasen vor dem Rathaus', "seed+dev", 0.7858, 0.8460, 0.7880, False),
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
    ("KA1", "kommentar", "A", NACHBAR, NACHBAR, "seed", 1.0000, 1.0000, 0.9581, True),
    ("KA2", "kommentar", "A", KATZEN, KATZEN, "seed", 1.0000, 1.0000, 0.9602, True),
    ("KB1", "kommentar", "B", 'Die CSU hat Gendern verboten. Die CDU hat Glühbirnen verboten. Söder wollte Ponys auf der Wiesn verbieten. Wir haben Solaranlagen auf Balkonen ERLAUBT. Merkste selbst, oder', FAKTEN, "seed+eigen", 0.9960, 0.9978, 0.9477, True),
    ("KB2", "kommentar", "B", 'Verstehe die Sorge um die Vögel total - mag Tiere auch! Aber wusstest du: Meine Katze ist statistisch gefährlicher.  \nHauskatzen töten 100 Millionen Vögel im Jahr, Windräder unter 100.000.  \nSogar der NABU befürwortet Windkraft, wenn richtig geplant.  \nDie kennen sich mit Vogelschutz aus, oder?', KATZEN, "seed+eigen", 1.0000, 1.0000, 0.9602, True),
    ("KB3", "kommentar", "B", 'Mein Schwager war auch skeptisch. Jetzt spart er 1.500€ im Jahr durchs 49€-Ticket und seine Solaranlage hat sich nach 5 Jahren amortisiert. Er sagt selbst: „Hätte ich mal früher drauf gehört.“ Manchmal sind Veränderungen echt eine Chance!', SKEPTIKER, "seed+eigen", 0.9992, 0.9996, 0.9486, True),
    ("KB4", "kommentar", "B", 'kenne ich, das mit den verboten nervt mich auch manchmal! aber mal ehrlich: ich freu mich, dass ich im restaurant nicht mehr vollgequalmt werde. und mein nachbar spart mit seiner wärmepumpe 800€ im jahr - das ist doch eher ein freiheitsgewinn, oder?', FREIHEIT, "seed+eigen", 0.9787, 0.9843, 0.9262, True),
    ("KC1", "kommentar", "C", 'Ich mag Vögel auch. Aber Hauskatzen töten jedes Jahr rund 100 Millionen Vögel, Windräder weniger als 100.000. Selbst der NABU unterstützt Windkraft, wenn sie gut geplant ist.', KATZEN, "eigen", 0.9686, 0.9679, 0.9391, False),
    ("KC2", "kommentar", "C", "Verbote gibt's überall: Die CSU hat das Gendern untersagt, die CDU die Glühbirne. Und wir? Wir haben Balkonsolar erlaubt. Merkste was?", FAKTEN, "eigen", 0.9497, 0.9566, 0.9297, False),
    ("KC3", "kommentar", "C", 'Früher dachte ich auch so. Aber Balkonkraftwerke sind jetzt erlaubt, das Deutschlandticket kostet 49 statt 180 Euro, und bei uns in der Straße haben fünf Nachbarn Solar aufs Dach. Klingt für mich nach mehr Freiheit.', NACHBAR, "eigen", 0.9528, 0.9455, 0.9106, False),
    ("KC4", "kommentar", "C", KATZEN + ' Quelle: NABU-Studie 2023.', KATZEN, "seed+eigen", 0.9897, 0.9968, 0.9559, True),
    ("KD1", "kommentar", "D", NACHBAR, SKEPTIKER, "seed", 0.8840, 0.8998, 0.8674, False),
    ("KD2", "kommentar", "D", KATZEN, DORF, "seed", 0.8748, 0.8722, 0.8507, False),
    ("KD3", "kommentar", "D", TECHNIK, VOGELLIEBE, "seed", 0.8813, 0.8752, 0.8654, False),
    ("KD4", "kommentar", "D", FREIHEIT, NACHBARS_UEB, "seed", 0.8932, 0.9015, 0.8564, False),
    ("KD5", "kommentar", "D", NACHBAR, FREIHEIT, "seed", 0.9133, 0.9032, 0.8710, False),
    ("KE1", "kommentar", "E", FAKTEN, KATZEN, "seed", 0.8507, 0.8294, 0.8124, False),
    ("KE2", "kommentar", "E", INNOVATION, DORF, "seed", 0.8432, 0.8213, 0.8102, False),
]
# fmt: on
