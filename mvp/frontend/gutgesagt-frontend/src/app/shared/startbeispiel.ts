/**
 * Das Startbeispiel (#601): die Aussage hinter „Beispiel probieren“ auf der Startseite
 * und im Rundgang „Antwort finden“. Steht nur hier.
 *
 * Wörtlich eine Aussage aus Startbestand und Seed: Die Suche findet so ihre eigene
 * Aussage (Score um 1, weit über der Schwelle von 0,82) und zeigt deren Kommentare,
 * statt eine neue Aussage anzulegen. Das prüft im Backend
 * tests/unit/test_suche_testset_aufbau.py (TestStartbeispiel). Wer das Beispiel
 * ändert, nimmt eine andere Aussage aus STARTBESTAND und SEED in
 * tests/regression/suche_testset.py.
 */
export const STARTBEISPIEL = 'Windräder töten die Vögel!';

/**
 * Typische Hot Takes, die das Suchfeld auf dem Start nacheinander eintippt (Designrunde 17.11.).
 * Jede wörtlich eine Aussage aus dem Startbestand, damit „Ausprobieren“ ihre Antworten zeigt.
 * Das Startbeispiel steht vorn.
 */
export const HOT_TAKES: readonly string[] = [
  STARTBEISPIEL,
  'Die Grünen wollen mir meine Heizung verbieten!',
  'E-Autos sind auch nicht besser für die Umwelt!',
  'Ein Tempolimit bringt doch nichts fürs Klima!',
  'Wärmepumpen funktionieren nur im Neubau!',
];
