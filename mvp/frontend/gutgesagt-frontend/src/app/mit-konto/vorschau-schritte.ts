/**
 * „Das erwartet dich mit Konto“ (Entscheidung Sebastian 17.11., Varianten A und B): drei
 * Bilder aus der angemeldeten Oberfläche mit je einem Satz. Eine Quelle für die
 * Vorschauseite (/mit-konto) und den Rundgang „Selbst beitragen“ ohne Konto
 * (/mit-konto?ansicht=rundgang); wer hier etwas ändert, ändert beides.
 *
 * Die Bilder liegen unter public/vorschau/ und tragen eine Version im Namen: Ein neues
 * Bild bekommt einen neuen Namen, damit kein Browser das alte aus dem Cache zeigt.
 */
export interface VorschauSchritt {
  /** Begriff aus GLOSSARY.md. */
  titel: string;
  satz: string;
  bild: string;
  /** Was auf dem Bild zu sehen ist, für Screenreader. */
  alt: string;
  breite: number;
  hoehe: number;
}

export const VORSCHAU_SCHRITTE: readonly VorschauSchritt[] = [
  {
    titel: 'Einwerfen',
    satz: 'Leg ein Fundstück in den Fangkorb: einen Link, einen Hinweis oder beides.',
    bild: 'vorschau/einwerfen-v1.webp',
    alt:
      'Formular „Schnell einwerfen“ mit einem Link und einem Hinweis für andere, ' +
      'darunter der Knopf „Einwerfen“.',
    breite: 800,
    hoehe: 670,
  },
  {
    titel: 'Ausformulieren',
    satz: 'Mach aus einem Satz einen Beitrag, den alle finden. Das Gegenlesen hilft dir dabei.',
    bild: 'vorschau/ausformulieren-v1.webp',
    alt:
      'Formular für einen Kommentar: Antwort auf „Windräder töten die Vögel!“, der Kommentartext, ' +
      'das Gegenlesen mit zwei Anmerkungen und der Titel.',
    breite: 800,
    hoehe: 909,
  },
  {
    titel: 'Bewerten',
    satz: 'Gib Beiträgen deine Stimme. Das Siegel auf der Karte zeigt die Güte, deine Stimme zählt mit.',
    bild: 'vorschau/bewerten-v1.webp',
    alt:
      'Karte eines Kommentars mit dem Siegel oben rechts, den Fassungen Kurz, Mittel und Lang ' +
      'und den Stimm-Knöpfen Daumen hoch und Daumen runter.',
    breite: 800,
    hoehe: 613,
  },
];

export const MIT_KONTO_PFAD = '/mit-konto';
/** Wohin es nach der Anmeldung geht; Angemeldete landen sofort dort. */
export const ZIEL_PARAM = 'ziel';
/** `ansicht=rundgang`: die Bildergeschichte Schritt für Schritt statt der Übersicht. */
export const ANSICHT_PARAM = 'ansicht';
/** Ziel ohne Angabe: die Beitragen-Seite, dort beginnt auch der echte Rundgang. */
export const STANDARD_ZIEL = '/contribute';

/**
 * Nur Pfade dieser App: mit einem Schrägstrich vorn, nicht zwei (sonst ein fremder Host),
 * nicht die Anmeldung und nicht die Vorschau selbst. Alles andere wird STANDARD_ZIEL.
 */
export function vorschauZiel(wert: string | null | undefined): string {
  if (!wert || !wert.startsWith('/') || wert.startsWith('//') || wert.startsWith('/\\')) return STANDARD_ZIEL;
  if (wert.startsWith('/login') || wert.startsWith(MIT_KONTO_PFAD)) return STANDARD_ZIEL;
  return wert;
}
