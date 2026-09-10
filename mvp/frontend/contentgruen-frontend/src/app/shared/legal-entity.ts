/**
 * Die Angaben zum Verein, die in mehr als einem Rechtstext stehen.
 *
 * Impressum und Datenschutzerklaerung nannten Anschrift, Telefon und Vorstand
 * bis hierher literal in je einem Template. Bei einem Umzug oder einem Wechsel
 * im Vorstand haette man beide finden muessen -- und die Datenschutzerklaerung
 * ist die, die man dabei vergisst. Alle drei Rechtstextkomponenten lesen die
 * Werte jetzt von hier (die Nutzungsbedingungen nur die E-Mail-Adresse);
 * geaendert wird nur noch an einer Stelle.
 *
 * Bewusst nicht hier: alles, was nur in einem der Texte vorkommt
 * (Registereintrag, MStV-Verantwortlicher, Aufsichtsbehoerde, Datenschutz-
 * beauftragter). Eine gemeinsame Datei fuer Einzelvorkommen macht die Texte
 * schwerer lesbar, ohne etwas gegen Drift zu tun.
 */
export const LEGAL_ENTITY = {
  NAME: 'NETZBEGRÜNUNG — Verein für grüne Netzkultur e. V.',
  ADRESSZUSATZ: 'c/o Max Pfeuffer',
  STRASSE: 'Heilig-Kreuz-Straße 16',
  PLZ_ORT: '86609 Donauwörth',
  LAND: 'Deutschland',
  TELEFON: '+49 906 299940-0',
  KONTAKT_MAIL: 'backoffice@netzbegruenung.de',
  VORSTAND: 'Jennifer Herbert und Korbinian Gall',
} as const;
