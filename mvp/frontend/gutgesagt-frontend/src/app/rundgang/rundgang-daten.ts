/**
 * Willkommen und Rundgänge (#389) als Daten: Ein neuer Rundgang ist eine neue
 * Schrittliste hier, keine neue Komponente (#514 baut darauf auf).
 *
 * Gestaltung und Texte nach Variante B des Klickdummys (Entscheidung 02.11.2026).
 */

import { MITMACHEN_SCHLUESSEL, WILLKOMMEN_SCHLUESSEL } from './rundgang-merker';

/** Ein Wert, der sich zwischen breitem Kopf (Desktop) und mobilem Kopf unterscheidet. */
export type JeGeraet<T> = T | { desktop: T; mobil: T };

export function jeGeraet<T>(wert: JeGeraet<T>, mobil: boolean): T {
  if (wert && typeof wert === 'object' && 'desktop' in wert && 'mobil' in wert) {
    return mobil ? wert.mobil : wert.desktop;
  }
  return wert as T;
}

export interface RundgangSchritt {
  titel: string;
  text: JeGeraet<string>;
  /**
   * CSS-Selektor des Elements, auf das der Schritt zeigt. Mehrere durch Komma: Der
   * Rundgang nimmt das erste sichtbare, so deckt ein Selektor Desktop- und mobilen
   * Kopf ab.
   */
  ziel: string;
  /** Seite, auf der das Ziel steht; ohne Angabe bleibt der Rundgang, wo er ist. */
  seite?: { pfad: string; query?: Record<string, string> };
}

export type RundgangId = 'antwort-finden' | 'mitmachen';

export interface Rundgang {
  id: RundgangId;
  /** Name für Screenreader, etwa „Rundgang Antwort finden“. */
  name: string;
  schritte: RundgangSchritt[];
}

/**
 * Das Band, das einen Rundgang anbietet (#587): Willkommen auf Startseite und
 * Treffern, Mitmachen, sobald jemand zum ersten Mal auf Beitragen oder Fangkorb ankommt.
 */
export interface Angebot {
  rundgang: RundgangId;
  /** Unter diesem Schlüssel merkt sich der Browser, dass das Angebot beantwortet wurde. */
  schluessel: string;
  titel: string;
  satz: string;
  /** Seiten (Pfadanfang), auf denen das Band steht. */
  seiten: string[];
  /** Beschriftung der beiden Knöpfe: Rundgang starten bzw. ausblenden. */
  ja: string;
  nein: string;
  /** Erster Schritt des Rundgangs, wenn er aus dem Band startet. */
  ab: number;
}

/** Dieselbe Aussage wie „Beispiel probieren“ auf der Startseite. */
export const BEISPIEL_AUSSAGE = 'Windräder töten die Vögel!';

export const WILLKOMMEN: Angebot = {
  rundgang: 'antwort-finden',
  schluessel: WILLKOMMEN_SCHLUESSEL,
  titel: 'Schön, dass du da bist!',
  satz:
    'Gut gesagt ist eine Tauschbörse für bewährte Argumente. Der Rundgang zeigt dir in fünf Schritten, ' +
    'wie du zu einer Aussage aus dem Netz eine erprobte Antwort findest.',
  // Nur die Startseite: über den Treffern schob das Band mobil Suchfeld und Treffer weg (#599)
  seiten: ['/search'],
  ja: 'Rundgang starten',
  nein: 'Ausblenden',
  ab: 0,
};

export const MITMACHEN_ANGEBOT: Angebot = {
  rundgang: 'mitmachen',
  schluessel: MITMACHEN_SCHLUESSEL,
  titel: 'Kurz zeigen, wie Beitragen geht?',
  satz: 'Drei Schritte: Fundstücke einwerfen, im Fangkorb weiterarbeiten und deine Beiträge im Blick behalten.',
  // Wer hier ist, hat „Beitragen“ schon gefunden: Der Rundgang beginnt beim Einwerfen.
  // Nicht auf /einwerfen: Das ist ein Formular (oft per Teilen schon gefüllt), und der
  // Rundgang spielt auf /contribute; „Zeig mir’s“ würde den Einwurf verwerfen.
  seiten: ['/contribute', '/fangkorb'],
  ja: 'Zeig mir’s',
  nein: 'Nein danke',
  ab: 1,
};

export const RUNDGAENGE: Record<RundgangId, Rundgang> = {
  'antwort-finden': {
    id: 'antwort-finden',
    name: 'Rundgang Antwort finden',
    schritte: [
      {
        titel: 'Aussage eingeben',
        text: 'Kopiere einen Post hier hinein oder tippe die Aussage ein, auf die du antworten willst.',
        ziel: 'app-search.start-suche .search-field',
        seite: { pfad: '/search' },
      },
      {
        titel: 'Passende Treffer',
        text:
          'Hier stehen Kommentare, die auf deine Aussage antworten. Mit Kurz, Mittel und Lang ' +
          'wählst du die Fassung.',
        ziel: 'app-beitragskarte',
        seite: { pfad: '/result', query: { searchQuery: BEISPIEL_AUSSAGE } },
      },
      {
        titel: 'Kommentar kopieren',
        text:
          '„Kopieren“ legt den Kommentar in deine Zwischenablage. Dann musst du ihn nur noch unter dem ' +
          'Post einfügen.',
        ziel: 'app-beitragskarte .kopieren-knopf',
        seite: { pfad: '/result', query: { searchQuery: BEISPIEL_AUSSAGE } },
      },
      {
        titel: 'Abstimmen',
        text:
          'War der Kommentar hilfreich? Angemeldet zeigt deine Stimme anderen, welche Kommentare gut ' +
          'ankommen.',
        ziel: 'app-beitragskarte .stimmen',
        seite: { pfad: '/result', query: { searchQuery: BEISPIEL_AUSSAGE } },
      },
      {
        titel: 'Jederzeit wieder',
        text: {
          desktop: 'In der Hilfe steht alles Wichtige. Dort startest du diesen Rundgang jederzeit neu.',
          mobil: 'Im Menü findest du die Hilfe. Dort startest du diesen Rundgang jederzeit neu.',
        },
        ziel: '.hilfe-knopf, .mobile-header .menu-button',
        seite: { pfad: '/search' },
      },
    ],
  },
  mitmachen: {
    id: 'mitmachen',
    name: 'Rundgang Mitmachen',
    schritte: [
      {
        titel: 'Beitragen',
        text: 'Hier geht es zu allem, womit du mitmachst: einwerfen, weiterarbeiten und Beiträge verfassen.',
        ziel: '.beitragen-knopf, .mobile-header .contribute-button',
      },
      {
        titel: 'Einwerfen',
        text:
          'Ein Link, ein Hinweis oder beides: Wirf ein Fundstück in den Fangkorb, ohne es schon ' +
          'auszuarbeiten.',
        ziel: '.einwerfen-block',
        seite: { pfad: '/contribute' },
      },
      {
        titel: 'Fangkorb',
        text:
          'Im Fangkorb liegen die Einwürfe aller. Destilliere einen zu einem Satz oder formuliere einen ' +
          'Satz zum Beitrag aus.',
        ziel: '.fangkorb-block',
        seite: { pfad: '/contribute' },
      },
      {
        titel: 'Meine Beiträge',
        text:
          'Hier siehst du, was du eingestellt hast und wie oft es genutzt wurde. Den Rundgang startest du ' +
          'jederzeit wieder über die Hilfe.',
        ziel: '.beitraege-block',
        seite: { pfad: '/contribute' },
      },
    ],
  },
};
