/**
 * Das Startbeispiel (#601): das erste Beispiel, das das Suchfeld auf der Startseite
 * vortippt (hinter „Beispiel ausprobieren“), und die Aussage im Rundgang „Antwort finden“. Steht nur hier.
 *
 * Wörtlich eine Aussage aus Startbestand und Seed: Die Suche findet so ihre eigene
 * Aussage (Score um 1, weit über der Schwelle von 0,82) und zeigt deren Kommentare,
 * statt eine neue Aussage anzulegen. Das prüft im Backend
 * tests/unit/test_suche_testset_aufbau.py (TestStartbeispiel). Wer das Beispiel
 * ändert, nimmt eine andere Aussage aus STARTBESTAND und SEED in
 * tests/regression/suche_testset.py.
 */
export const STARTBEISPIEL = 'Windräder töten die Vögel!';

/** Ein Hot Take im Suchfeld und die Aussage, als die die Suche ihn erkennen soll. */
export interface HotTake {
  /** So, wie das Suchfeld ihn vortippt: leicht anders formuliert als die Aussage. */
  text: string;
  /** Wörtlich eine Aussage aus Startbestand und Seed. */
  aussage: string;
}

/**
 * Typische Hot Takes, die das Suchfeld auf dem Start nacheinander eintippt (Designrunde 17.11.).
 * Jeder ist leicht anders formuliert als die Aussage, der er zugeordnet ist: Das zeigt, dass
 * die Suche nach Bedeutung findet, nicht nach Wortlaut. „Beispiel ausprobieren“ soll trotzdem genau
 * diese Aussage erkennen (am lokalen Stack geprüft, 18.11.). Die Aussagen prüft im Backend
 * tests/unit/test_suche_testset_aufbau.py (TestStartbeispiel), die Paare stehen als Fälle in
 * tests/regression/suche_testset.py. Der erste gehört zum Startbeispiel.
 */
export const HOT_TAKES: readonly HotTake[] = [
  { text: 'Windräder killen doch massenhaft Vögel!', aussage: STARTBEISPIEL },
  { text: 'Die Grünen wollen uns die Heizung wegnehmen!', aussage: 'Die Grünen wollen mir meine Heizung verbieten!' },
  { text: 'E-Autos sind auch nicht klimafreundlicher!', aussage: 'E-Autos sind auch nicht besser für die Umwelt!' },
  { text: 'Tempolimit? Bringt fürs Klima gar nichts!', aussage: 'Ein Tempolimit bringt doch nichts fürs Klima!' },
  { text: 'Wärmepumpen taugen nur für Neubauten!', aussage: 'Wärmepumpen funktionieren nur im Neubau!' },
];
