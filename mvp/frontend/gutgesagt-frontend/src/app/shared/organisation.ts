/**
 * Namen und Links der Organisation, die diese Instanz betreibt (CODING_STANDARDS.md,
 * „Organisation-neutral where it costs nothing“). Neue Texte nehmen sie von hier;
 * Bestehendes zieht nach, wenn es aus anderem Grund angefasst wird.
 *
 * Die Angaben für die Rechtstexte (voller Vereinsname, Anschrift, Vorstand) stehen in
 * `legal-entity.ts` und ändern sich nur mit den Rechtstexten; hier steht, wie die
 * Organisation im übrigen Text heißt und wo man sie erreicht.
 */
export const ORGANISATION = {
  name: 'Netzbegrünung',
  vereinsname: 'Netzbegrünung e.V.',
  url: 'https://netzbegruenung.de/',
  /**
   * Fragen und Hinweise zu Gut gesagt, neben dem Knopf „Feedback“ (Meldewege, #290).
   * ANNAHME (#430): dieselbe Adresse wie für Beta-Zugänge; eine eigene Adresse gibt es noch nicht.
   */
  kontaktMail: 'gutgesagt@netzbegruenung.de',
  /** Der Kanal zum Mitmachen. Kein Meldeweg: Fragen und Fehler gehen über Feedback oder Mail (#290). */
  chat: {
    name: 'Chatbegrünung',
    url: 'https://chatbegruenung.de/channel/GutGesagt',
  },
} as const;
