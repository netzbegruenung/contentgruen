import { Einwurf } from '../services/einwurf.service';
import { stufeInDerKette } from '../beitragskarte/karten-daten';
import { Plattform, PLATTFORMEN, plattformAusUrl } from '../shared/plattform';

/**
 * Schluessel im sessionStorage. Filter und Tab halten innerhalb der Sitzung, nicht
 * darueber hinaus - wer den Fangkorb morgen oeffnet, sieht wieder alles und
 * beginnt beim Destillieren.
 */
export const FILTER_SCHLUESSEL = 'gutgesagt.fangkorb.filter';

/**
 * Die Plattformen, die ein gespeicherter Filter ohne Angabe "bekannte" kannte -
 * so hat ihn die Version vor Threads, X und Bluesky abgelegt.
 */
const FRUEHER_BEKANNTE: ReadonlyArray<string> = ['instagram', 'youtube', 'tiktok', 'web'];

/**
 * Die beiden Tabs, die Arbeitslisten des Fangkorbs. Sie heissen nach der
 * naechsten Arbeit, nicht nach der Stufe: offene Einwuerfe liegen unter
 * "Destillieren", destillierte unter "Ausformulieren". Ausformuliertes hat keine
 * naechste Arbeit und liegt in keinem Tab; es steht unter "Meine Einwuerfe" und
 * als Herkunft am Beitrag.
 */
export type FangkorbTab = 'destillieren' | 'ausformulieren';

/** Reihenfolge, Beschriftung und die eine Zeile, die im leeren Tab steht. */
export const TABS: ReadonlyArray<{ wert: FangkorbTab; name: string; leer: string }> = [
  { wert: 'destillieren', name: 'Destillieren', leer: 'Nichts zu destillieren.' },
  { wert: 'ausformulieren', name: 'Ausformulieren', leer: 'Nichts auszuformulieren.' },
];

/**
 * Wohin der Fangkorb nach einer Handlung im Destillier-Ablauf zurueckkehrt: der
 * Tab, in dem der Einwurf jetzt liegt, oder "ausformuliert", wenn er in keinem
 * mehr liegt.
 */
export type Ruecksprung = FangkorbTab | 'ausformuliert';

/** Ausformuliertes liegt in keinem Tab; zurueck geht es in die Arbeitsliste, aus der es kam. */
export function tabNach(ruecksprung: Ruecksprung): FangkorbTab {
  return ruecksprung === 'ausformuliert' ? 'ausformulieren' : ruecksprung;
}

/**
 * Fruehere Tabs: "Erledigt" bis zur Angleichung ans Glossar, danach
 * "Ausformuliert" bis #265. Ein in der Sitzung gemerkter Wert fuehrt auf die
 * erste Arbeitsliste.
 */
const FRUEHERE_TABS: Readonly<Record<string, FangkorbTab>> = {
  erledigt: 'destillieren',
  ausformuliert: 'destillieren',
};

/** So liegt der Filter im Storage: dazu, welche Plattformen es beim Speichern gab. */
interface GespeicherterFilter extends FangkorbFilter {
  bekannte: string[];
}

export interface FangkorbFilter {
  /** Eingeblendete Plattformen, Standard alle. Einwuerfe ohne Link blendet das nie aus. */
  plattformen: Plattform[];
  /** Nur selbst Eingeworfenes. */
  nurMeine: boolean;
  /** Der offene Tab. */
  tab: FangkorbTab;
  /** Verworfenes in den Tabs mitzeigen; standardmaessig ausgeblendet. */
  verworfenSichtbar: boolean;
}

export function standardFilter(): FangkorbFilter {
  return {
    plattformen: PLATTFORMEN.map((eintrag) => eintrag.wert),
    nurMeine: false,
    tab: 'destillieren',
    verworfenSichtbar: false,
  };
}

/**
 * Ob ein Einwurf unter den Chips sichtbar ist - Plattform und "nur meine". Der
 * Tab entscheidet getrennt davon (``passtZumTab``), damit die Zaehler der anderen
 * Tabs dieselben Chips beruecksichtigen.
 *
 * Ohne bekannte eigene Kennung zeigt "nur meine" nichts an, statt stillschweigend
 * alles.
 */
export function passtZumFilter(
  einwurf: Einwurf,
  filter: FangkorbFilter,
  eigeneKennung: string | null,
): boolean {
  const plattform = plattformAusUrl(einwurf.url);
  if (plattform && !filter.plattformen.includes(plattform)) {
    return false;
  }
  if (filter.nurMeine && (!eigeneKennung || einwurf.submitted_by !== eigeneKennung)) {
    return false;
  }
  return true;
}

/**
 * Ob ein Einwurf in diesem Tab liegt.
 *
 * Verworfenes liegt im Tab der Arbeit, die an ihm noch offen waere - ohne Satz
 * unter "Destillieren", mit Satz unter "Ausformulieren" -, ist dort aber nur zu
 * sehen, wenn der Chip "verworfen" an ist: sonst taucht wieder auf, was jemand
 * weggelegt hat. So bleibt es erreichbar und laesst sich trotzdem destillieren.
 * Ausformuliertes liegt in keinem Tab, verworfen oder nicht.
 */
export function passtZumTab(
  einwurf: Einwurf,
  tab: FangkorbTab,
  verworfenSichtbar: boolean,
): boolean {
  if (einwurf.status === 'discarded' && !verworfenSichtbar) {
    return false;
  }
  const stufe = stufeInDerKette(einwurf);
  return (stufe === 'offen' && tab === 'destillieren') || (stufe === 'destilliert' && tab === 'ausformulieren');
}

/**
 * Filter und Tab dieser Sitzung lesen.
 *
 * Fehlt die Ablage, ist sie unlesbar oder ist der Storage gesperrt (privater
 * Modus), gilt der Standard. Plattformen, die es heute nicht mehr gibt, fallen
 * heraus. Plattformen, die der gespeicherte Filter noch nicht kannte, gelten als
 * eingeblendet - sonst blieben ihre Einwuerfe unsichtbar, ohne dass je jemand sie
 * abgewaehlt hat. Das frueher gespeicherte "nur offene" wird ignoriert; die Tabs
 * leisten dasselbe.
 */
export function filterLaden(): FangkorbFilter {
  try {
    const roh = sessionStorage.getItem(FILTER_SCHLUESSEL);
    if (!roh) {
      return standardFilter();
    }
    const gelesen = JSON.parse(roh) as Partial<GespeicherterFilter> | null;
    const kannte = Array.isArray(gelesen?.bekannte) ? gelesen.bekannte : FRUEHER_BEKANNTE;
    const gespeichert: string[] | null = Array.isArray(gelesen?.plattformen) ? gelesen.plattformen : null;
    return {
      plattformen: gespeichert
        ? PLATTFORMEN.map((eintrag) => eintrag.wert).filter(
            (wert) => gespeichert.includes(wert) || !kannte.includes(wert),
          )
        : standardFilter().plattformen,
      nurMeine: gelesen?.nurMeine === true,
      tab: tabAus(gelesen?.tab) ?? standardFilter().tab,
      verworfenSichtbar: gelesen?.verworfenSichtbar === true,
    };
  } catch {
    return standardFilter();
  }
}

/**
 * Den Tab merken, den der Fangkorb beim naechsten Oeffnen zeigen soll.
 *
 * Gebraucht am Ende des Destillier-Ablaufs: Wer den letzten offenen Einwurf
 * destilliert, ausformuliert oder verworfen hat, landet wieder im Fangkorb - und
 * zwar dort, wo das Ergebnis liegt, nicht in einem leeren "Destillieren".
 */
export function tabMerken(tab: FangkorbTab): void {
  filterSpeichern({ ...filterLaden(), tab });
}

/**
 * Verworfenes fuer diese Sitzung einblenden.
 *
 * Gebraucht nach dem Verwerfen: Der Einwurf liegt danach hinter einem Chip, der
 * normalerweise aus ist - ohne das hier verschwaende er vor den Augen der Person,
 * die ihn gerade weggelegt hat.
 */
export function verworfenEinblenden(): void {
  filterSpeichern({ ...filterLaden(), verworfenSichtbar: true });
}

/** Ein Tab aus Storage oder Adresse; fruehere Tabs fuehren auf die erste Arbeitsliste. */
export function tabAus(wert: unknown): FangkorbTab | null {
  if (typeof wert !== 'string') {
    return null;
  }
  const tab = TABS.find((eintrag) => eintrag.wert === wert);
  if (tab) {
    return tab.wert;
  }
  return Object.hasOwn(FRUEHERE_TABS, wert) ? FRUEHERE_TABS[wert] : null;
}

export function filterSpeichern(filter: FangkorbFilter): void {
  try {
    const gespeichert: GespeicherterFilter = {
      ...filter,
      bekannte: PLATTFORMEN.map((eintrag) => eintrag.wert),
    };
    sessionStorage.setItem(FILTER_SCHLUESSEL, JSON.stringify(gespeichert));
  } catch {
    // Ohne Storage gelten Filter und Tab eben nur, solange die Seite offen ist.
  }
}
