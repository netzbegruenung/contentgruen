/**
 * Willkommen und Rundgänge (#389) als Daten: Ein neuer Rundgang ist eine neue
 * Schrittliste hier, keine neue Komponente (#514 baut darauf auf).
 *
 * Gestaltung und Texte nach Variante B des Klickdummys (Entscheidung 02.11.2026).
 */

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

/** Das Fenster, das einen Rundgang anbietet: Willkommen beim ersten Besuch oder Mitmachen nach der Anmeldung. */
export interface Angebot {
  rundgang: RundgangId;
  titel: string;
  satz: string;
}

/** Dieselbe Aussage wie „Beispiel probieren“ auf der Startseite. */
export const BEISPIEL_AUSSAGE = 'Windräder töten die Vögel!';

export const WILLKOMMEN: Angebot = {
  rundgang: 'antwort-finden',
  titel: 'Schön, dass du da bist!',
  satz:
    'Gut gesagt ist eine Tauschbörse für bewährte Argumente: Gib eine Aussage aus dem Netz ein und ' +
    'finde fertige Kommentare, die andere Grüne schon erprobt haben.',
};

export const MITMACHEN_ANGEBOT: Angebot = {
  rundgang: 'mitmachen',
  titel: 'Jetzt kannst du mitmachen!',
  satz:
    'Du bist angemeldet: Du kannst Fundstücke einwerfen, im Fangkorb weiterarbeiten und eigene Beiträge ' +
    'verfassen. Der Rundgang zeigt dir in vier Schritten, wo das geht.',
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
          'Hier stehen fertige Kommentare, die auf deine Aussage antworten. Mit Kurz, Mittel und Lang ' +
          'wählst du die Länge.',
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
        text: 'War der Kommentar hilfreich? Deine Stimme zeigt anderen, welche Antworten gut ankommen.',
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
