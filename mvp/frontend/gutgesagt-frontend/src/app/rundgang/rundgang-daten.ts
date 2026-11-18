/**
 * Willkommen und Rundgänge (#389) als Daten: Ein neuer Rundgang ist eine neue
 * Schrittliste hier, keine neue Komponente (#514 baut darauf auf).
 *
 * Gestaltung und Texte nach Variante B des Klickdummys (Entscheidung 02.11.2026).
 */

import { STARTBEISPIEL } from '../shared/startbeispiel';
import { VORSCHAU_SCHRITTE } from '../mit-konto/vorschau-schritte';
import { HOME_HINWEIS_SCHLUESSEL, MITMACHEN_SCHLUESSEL, WILLKOMMEN_SCHLUESSEL } from './rundgang-merker';

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
  /**
   * Text, den der Schritt in das Eingabefeld im Ziel schreibt, wenn es leer ist: ein
   * Beispiel zum Ausprobieren. Was jemand schon eingetippt hat, bleibt stehen.
   */
  vorbelegen?: string;
}

export type RundgangId = 'antwort-finden' | 'mitmachen';

export interface Rundgang {
  id: RundgangId;
  /** Name für Screenreader, etwa „Rundgang Antwort finden“. */
  name: string;
  /** Kurzname in Hilfe und Menü, etwa „Antwort finden“ (#644). */
  titel: string;
  schritte: RundgangSchritt[];
}

/**
 * Wie Hilfe und Menü einen Rundgang nennen: Kurzname und Schrittzahl, damit man vorher
 * sieht, was er zeigt und wie lang er ist (#644).
 */
export function rundgangBeschriftung(id: RundgangId, angemeldet = true): string {
  const r = RUNDGAENGE[id];
  // Ohne Konto ist Selbst beitragen die Bildergeschichte aus VORSCHAU_SCHRITTE (17.11.)
  if (id === 'mitmachen' && !angemeldet) return `${r.titel} (${VORSCHAU_SCHRITTE.length} Bilder)`;
  return `${r.titel} (${r.schritte.length} Schritte)`;
}

/** Was der Neu-Punkt an „Beitragen“ bedeutet, als Tooltip und für Screenreader (#644). */
export const NEU_HINWEIS = 'Neu: so geht Beitragen';

/**
 * Das Band, das einen Rundgang anbietet (#587): Willkommen auf Startseite und
 * Treffern, Mitmachen, sobald jemand zum ersten Mal auf Beitragen ankommt (seit #644 nicht im Fangkorb).
 */
export interface Angebot {
  /** Ohne Rundgang ist das Band nur ein Hinweis mit „Ausblenden“ (Home-Bildschirm). */
  rundgang?: RundgangId;
  /** Unter diesem Schlüssel merkt sich der Browser, dass das Angebot beantwortet wurde. */
  schluessel: string;
  titel: string;
  satz: string;
  /** Hinter dem Satz das Teilen-Symbol von iOS und danach dieser Text. */
  nachTeilenSymbol?: string;
  /** Bild links im Band; ohne Angabe der Wegweiser. */
  bild?: string;
  /** Seiten (Pfadanfang), auf denen das Band steht. */
  seiten: string[];
  /** Beschriftung der beiden Knöpfe: Rundgang starten bzw. ausblenden. */
  ja?: string;
  nein: string;
  /** Name des Ausblenden-Knopfs für Screenreader, wenn „nein“ allein nicht reicht. */
  neinLabel?: string;
  /** Erster Schritt des Rundgangs, wenn er aus dem Band startet. */
  ab: number;
  /**
   * Die Seite stellt das Band selbst in ihren Inhalt (app-rundgang-band ort="start"),
   * statt dass es ueber dem Inhalt steht.
   */
  imInhalt?: boolean;
  /**
   * Eine schlanke Zeile statt des Kastens: Titel, Rundgang als Link, Satz und ein
   * Schliessen-Kreuz (Persona-Runde 18.11.). Nur fuer kurze Saetze.
   */
  schlank?: boolean;
  /** Der Knopf „ja“ öffnet den Installieren-Dialog des Browsers statt eines Rundgangs. */
  installieren?: boolean;
}

export const WILLKOMMEN: Angebot = {
  rundgang: 'antwort-finden',
  schluessel: WILLKOMMEN_SCHLUESSEL,
  // Eine Zeile statt Kasten (Persona-Runde 18.11.): Vielbeschaeftigte am Handy wollen zuerst
  // suchen; was Gut gesagt ist, zeigt der Rundgang selbst.
  titel: 'Neu hier?',
  satz: 'Ein Konto brauchst du nicht',
  schlank: true,
  // Ohne Konto vollwertig: Gespräch am Stand, am Familientisch, am Stammtisch (14.11.)
  // Nur die Startseite: über den Treffern schob das Band mobil Suchfeld und Treffer weg (#599)
  seiten: ['/search'],
  // Dort unter dem Suchfeld: darüber stand das Suchfeld mobil erst bei y 489 von 844
  // (Nutzerführung 13.11.)
  imInhalt: true,
  // Mit Dauer: Ungeduldige ueberspringen Rundgaenge sonst (Ersteindruck-Test 14.11.)
  ja: 'Rundgang (1 Min.)',
  nein: 'Ausblenden',
  neinLabel: 'Willkommen ausblenden',
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
  // Nur auf Beitragen: Im Fangkorb stand es zusaetzlich und sagte dasselbe wie der
  // Neu-Punkt im Kopf (#644).
  seiten: ['/contribute'],
  ja: 'Zeig mir’s',
  nein: 'Nein danke',
  ab: 1,
};

/**
 * Nur auf iPhone und iPad in Safari (14.11.2026): Dort bietet der Browser das Installieren
 * nicht von selbst an. Erst wenn der Vermerk für Willkommen oder Mitmachen im Speicher
 * steht, nicht nach Willkommen oder Mitmachen im selben Besuch; einmal ausgeblendet,
 * kommt es nicht wieder.
 */
export const HOME_ANGEBOT: Angebot = {
  schluessel: HOME_HINWEIS_SCHLUESSEL,
  titel: 'Gut gesagt als App',
  // Ab iOS 26 kann „Teilen“ im Menü „···“ liegen
  satz: 'Tippe in Safari auf Teilen',
  // Geschütztes Leerzeichen: „auf“ und „···“ bleiben in einer Zeile
  nachTeilenSymbol: '(oder erst auf ···) und dann auf „Zum Home-Bildschirm“.',
  bild: 'marke/apple-touch-icon-180.png',
  // Wie das Willkommen nur auf der Startseite unter dem Suchfeld, nicht über Treffern (#599)
  seiten: ['/search'],
  imInhalt: true,
  nein: 'Ausblenden',
  neinLabel: 'Hinweis ausblenden',
  ab: 0,
};

/**
 * Dasselbe Band für Chrome und Edge auf Android und Computer (18.11.2026), nur wenn der
 * Browser das Installieren anbietet (`beforeinstallprompt`): mit echtem Knopf statt
 * Anleitung. Gleicher Vermerk wie HOME_ANGEBOT, gleiche Regeln.
 */
export const APP_INSTALLIEREN_ANGEBOT: Angebot = {
  schluessel: HOME_HINWEIS_SCHLUESSEL,
  titel: 'Gut gesagt als App',
  satz: 'Mit eigenem Symbol öffnest du Gut gesagt mit einem Tipp, ohne Adressleiste.',
  bild: 'marke/apple-touch-icon-180.png',
  seiten: ['/search'],
  imInhalt: true,
  installieren: true,
  ja: 'Installieren',
  nein: 'Ausblenden',
  neinLabel: 'Hinweis ausblenden',
  ab: 0,
};

export const RUNDGAENGE: Record<RundgangId, Rundgang> = {
  'antwort-finden': {
    id: 'antwort-finden',
    name: 'Rundgang Antwort finden',
    titel: 'Antwort finden',
    schritte: [
      {
        titel: 'Aussage eingeben',
        text:
          'Füge den Text ein, auf den du antworten willst – einen Post oder Kommentar –, oder tippe die Aussage ein. ' +
          `Probier’s mit „${STARTBEISPIEL}“: Die nächsten Schritte zeigen die Treffer dazu.`,
        ziel: 'app-search.start-suche .search-field',
        seite: { pfad: '/search' },
        // Dieselbe Aussage suchen die Schritte 2 bis 4 (#601)
        vorbelegen: STARTBEISPIEL,
      },
      {
        titel: 'Passende Treffer',
        text:
          'Hier stehen Kommentare, die auf deine Aussage antworten. Mit Kurz, Mittel und Lang ' +
          'wählst du die Fassung. Das Siegel oben rechts zeigt die Güte: Je weiter der Daumen nach oben ' +
          'zeigt, desto besser ist der Kommentar formuliert und bewertet. Ein Klick oder Tipp darauf erklärt es.',
        // Sätze zum Siegel: es fiel nicht auf und erklärte sich nicht selbst (Ersteindruck-Test 14.11.);
        // kürzer als der Absatz #siegel auf der Über-Seite, sagt aber dasselbe (Güte aus Regeln und Stimmen)
        ziel: 'app-beitragskarte',
        seite: { pfad: '/result', query: { searchQuery: STARTBEISPIEL } },
      },
      {
        titel: 'Kommentar kopieren',
        text:
          '„Kopieren“ legt den Kommentar in deine Zwischenablage. Dann musst du ihn nur noch unter dem ' +
          'Post einfügen.',
        ziel: 'app-beitragskarte .kopieren-knopf',
        seite: { pfad: '/result', query: { searchQuery: STARTBEISPIEL } },
      },
      {
        titel: 'Abstimmen',
        text:
          'War der Kommentar hilfreich? Angemeldet zeigt deine Stimme anderen, welche Kommentare gut ' +
          'ankommen.',
        ziel: 'app-beitragskarte .stimmen',
        seite: { pfad: '/result', query: { searchQuery: STARTBEISPIEL } },
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
    name: 'Rundgang Selbst beitragen',
    titel: 'Selbst beitragen',
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
